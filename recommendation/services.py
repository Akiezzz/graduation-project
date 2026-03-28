import math
from collections import defaultdict

from django.db.models import Sum

from product.models import Product
from .models import UserBehavior
from . import cache


BEHAVIOR_SCORE_MAP = {
    UserBehavior.BEHAVIOR_VIEW: 1,
    UserBehavior.BEHAVIOR_CART: 2,
    UserBehavior.BEHAVIOR_ORDER: 4,
    UserBehavior.BEHAVIOR_REVIEW: 3,
}


def log_user_behavior(user, product, behavior_type, score=None):
    """
    记录用户行为（双写：Redis + DB）

    Args:
        user: 用户对象
        product: 商品对象
        behavior_type: 行为类型
        score: 行为权重，None 时使用默认映射
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return

    behavior_score = score if score is not None else BEHAVIOR_SCORE_MAP.get(behavior_type, 1)

    # 先写 Redis（异步，失败时静默降级）
    cache.push_recent_behavior(user.id, product.id, behavior_type, behavior_score)

    # 后写 DB（确保持久化）
    UserBehavior.objects.create(
        user=user,
        product=product,
        behavior_type=behavior_type,
        score=behavior_score,
    )

    # 清除该用户的推荐缓存
    cache.clear_recommendation_cache(user.id)


def _active_product_queryset(exclude_product_ids=None):
    qs = Product.objects.filter(is_active=True, stock__gt=0)
    if exclude_product_ids:
        qs = qs.exclude(pk__in=exclude_product_ids)
    return qs


def get_popular_recommendations(limit=8, exclude_product_ids=None):
    return list(_active_product_queryset(exclude_product_ids).order_by('-sales', '-created_at')[:limit])


def get_itemcf_recommendations(user, limit=8, exclude_product_ids=None):
    """
    基于物品协同过滤的个性化推荐
    优先从 Redis 读取用户近期行为，提升响应速度

    Args:
        user: 用户对象
        limit: 返回商品数量
        exclude_product_ids: 排除的商品 ID 列表

    Returns:
        list: 推荐商品列表
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return []

    # 优先从 Redis 读取近期行为
    recent_behaviors = cache.get_recent_behaviors(user.id, limit=200)
    redis_user_items = {}
    if recent_behaviors:
        for behavior in recent_behaviors:
            pid = behavior['product_id']
            score = behavior['score']
            if pid in redis_user_items:
                redis_user_items[pid] += score
            else:
                redis_user_items[pid] = score

    # 如果 Redis 数据不足，从 DB 补充
    if len(redis_user_items) < 10:
        db_behaviors = UserBehavior.objects.filter(user=user)
        for behavior in db_behaviors:
            pid = behavior.product_id
            score = behavior.score
            if pid in redis_user_items:
                redis_user_items[pid] += score
            else:
                redis_user_items[pid] = score

    target_items = redis_user_items
    if not target_items:
        return []

    # 构建全量用户-物品交互矩阵
    interactions = list(
        UserBehavior.objects.values('user_id', 'product_id').annotate(weight=Sum('score'))
    )
    if not interactions:
        return []

    user_items = defaultdict(dict)
    for row in interactions:
        user_items[row['user_id']][row['product_id']] = float(row['weight'])

    seen_products = set(target_items.keys())
    if exclude_product_ids:
        seen_products.update(exclude_product_ids)

    candidate_scores = defaultdict(float)
    target_size = len(target_items)

    for other_user_id, other_items in user_items.items():
        if other_user_id == user.id:
            continue
        overlap = set(target_items.keys()) & set(other_items.keys())
        if not overlap:
            continue
        similarity = len(overlap) / math.sqrt(target_size * len(other_items))
        if similarity <= 0:
            continue
        for product_id, weight in other_items.items():
            if product_id in seen_products:
                continue
            candidate_scores[product_id] += similarity * weight

    if not candidate_scores:
        return []

    ranked_ids = [pid for pid, _ in sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)[:limit * 3]]
    products = list(_active_product_queryset(seen_products).filter(pk__in=ranked_ids))
    product_map = {p.id: p for p in products}

    ordered = []
    for pid in ranked_ids:
        product = product_map.get(pid)
        if product:
            ordered.append(product)
        if len(ordered) >= limit:
            break
    return ordered


def get_recommendations_for_user(user, limit=8, exclude_product_ids=None):
    """
    获取用户推荐结果（带缓存）

    Args:
        user: 用户对象
        limit: 返回商品数量
        exclude_product_ids: 排除的商品 ID 列表

    Returns:
        tuple: (商品列表, 推荐来源, 个性化商品ID集合)
    """
    # 尝试从缓存读取
    if user and getattr(user, 'is_authenticated', False):
        cached = cache.get_cached_recommendations(user.id)
        if cached:
            cached_ids = cached.get('product_ids', [])[:limit]
            cached_source = cached.get('source', 'popular')
            products = list(Product.objects.filter(
                id__in=cached_ids,
                is_active=True,
                stock__gt=0
            ))

            # 按缓存顺序排序
            product_map = {p.id: p for p in products}
            ordered = []
            for pid in cached_ids:
                if pid in product_map:
                    ordered.append(product_map[pid])

            if ordered:
                personalized_ids = set(ordered[:limit]) if cached_source in ['itemcf', 'mixed'] else set()
                return ordered[:limit], cached_source, personalized_ids

    # 缓存未命中，执行推荐逻辑
    extra_exclude = set(exclude_product_ids or [])

    if not user or not getattr(user, 'is_authenticated', False):
        popular = get_popular_recommendations(limit=limit, exclude_product_ids=extra_exclude)
        return popular, 'popular', set()

    user_seen = set(UserBehavior.objects.filter(user=user).values_list('product_id', flat=True))
    user_seen.update(extra_exclude)

    personalized = get_itemcf_recommendations(user, limit=limit, exclude_product_ids=user_seen)
    personalized_ids = {p.id for p in personalized}

    # 尝试用深度模型对候选商品重排序
    try:
        from recommendation.deep_models.inference import get_deep_model_manager
        manager = get_deep_model_manager()
        if manager.is_model_loaded():
            # 取 ItemCF 候选 + 热门补充作为候选池
            candidate_pool_ids = list(personalized_ids)
            if len(candidate_pool_ids) > 0:
                deep_ranked = manager.predict(user.id, candidate_pool_ids, limit=limit)
                if deep_ranked:
                    deep_products = list(Product.objects.filter(id__in=deep_ranked, is_active=True, stock__gt=0))
                    deep_map = {p.id: p for p in deep_products}
                    personalized = [deep_map[pid] for pid in deep_ranked if pid in deep_map]
                    personalized_ids = {p.id for p in personalized}
    except Exception:
        pass

    if len(personalized) >= limit:
        result = personalized[:limit]
        cache.cache_recommendations(user.id, [p.id for p in result], 'itemcf')
        return result, 'itemcf', personalized_ids

    supplement = get_popular_recommendations(
        limit=limit - len(personalized),
        exclude_product_ids=user_seen | personalized_ids,
    )
    merged = personalized + supplement

    if personalized and supplement:
        source = 'mixed'
    elif personalized:
        source = 'itemcf'
    else:
        source = 'popular'

    result = merged[:limit]
    # 缓存结果
    cache.cache_recommendations(user.id, [p.id for p in result], source)

    return result, source, personalized_ids


# ========== 为深度模型预留的接口（P3 阶段实现） ==========

def get_user_sequence(user_id, max_length=50):
    """
    获取用户行为序列（为 Transformer 模型预留）

    Args:
        user_id: 用户 ID
        max_length: 最大序列长度

    Returns:
        list: 行为序列，格式为 [{'product_id': int, 'behavior_type': str, 'score': float, 'timestamp': datetime}, ...]
              按时间倒序排列（最新的在前）
    """
    # 优先从 Redis 读取
    redis_behaviors = cache.get_recent_behaviors(user_id, limit=max_length)
    if redis_behaviors:
        return redis_behaviors[:max_length]

    # Redis 未命中，从 DB 读取
    from .models import UserBehavior
    behaviors = UserBehavior.objects.filter(
        user_id=user_id
    ).select_related('product').order_by('-created_at')[:max_length]

    sequence = []
    for behavior in behaviors:
        sequence.append({
            'product_id': behavior.product_id,
            'behavior_type': behavior.behavior_type,
            'score': float(behavior.score),
            'timestamp': behavior.created_at,
        })

    return sequence


def get_product_features(product_ids):
    """
    批量获取商品特征（为 Transformer + TextCNN 模型预留）

    Args:
        product_ids: 商品 ID 列表或集合

    Returns:
        dict: {product_id: {'product_id': int, 'name': str, 'keywords': str, 'description': str, 'category_id': int, 'text': str}, ...}
    """
    if not product_ids:
        return {}

    # 批量查询商品
    products = Product.objects.filter(
        id__in=product_ids
    ).only('id', 'name', 'keywords', 'description', 'category_id')

    features = {}
    for product in products:
        # 合并文本字段
        text_parts = [product.name]
        if product.keywords:
            text_parts.append(product.keywords)
        if product.description:
            text_parts.append(product.description)
        combined_text = ' '.join(text_parts)

        features[product.id] = {
            'product_id': product.id,
            'name': product.name,
            'keywords': product.keywords or '',
            'description': product.description or '',
            'category_id': product.category_id if product.category else None,
            'text': combined_text,
        }

    return features
