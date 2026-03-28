"""
Redis 缓存服务模块

提供用户行为的实时缓存功能，提升推荐系统响应速度。
所有 Redis 操作均包含异常处理，Redis 不可用时自动降级。
"""

import json
import logging
from datetime import datetime
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


def get_redis_connection():
    """
    获取 Redis 连接（通过 Django cache）

    Returns:
        cache: Django cache 对象，Redis 不可用时返回默认缓存
    """
    return cache


def get_behavior_cache_key(user_id):
    """获取用户行为缓存键"""
    prefix = settings.RECOMMENDATION_CACHE.get('BEHAVIOR_CACHE_PREFIX', 'behavior')
    return f"{prefix}:{user_id}"


def push_recent_behavior(user_id, product_id, behavior_type, score):
    """
    追加用户近期行为到 Redis 列表

    Args:
        user_id: 用户 ID
        product_id: 商品 ID
        behavior_type: 行为类型 (view/cart/order/review)
        score: 行为权重分数

    Returns:
        bool: 是否成功写入 Redis
    """
    try:
        cache = get_redis_connection()
        key = get_behavior_cache_key(user_id)

        # 构建行为记录 JSON
        behavior_data = {
            'product_id': product_id,
            'behavior_type': behavior_type,
            'score': score,
            'timestamp': datetime.now().isoformat(),
        }

        # 使用 Redis LPUSH 追加到列表头部
        cache.lpush(key, json.dumps(behavior_data))

        # 保留最近 N 条记录（从配置读取）
        max_size = settings.RECOMMENDATION_CACHE.get('BEHAVIOR_LIST_SIZE', 100)
        cache.ltrim(key, 0, max_size - 1)

        # 设置过期时间（7天）
        cache.persist(key)  # 移除过期时间限制，由 LTRIM 控制
        return True

    except Exception as e:
        # Redis 不可用时静默失败，回退到 DB
        logger.warning(f"Redis 写入失败，回退到 DB: {e}")
        return False


def get_recent_behaviors(user_id, limit=None):
    """
    从 Redis 读取用户近期行为列表

    Args:
        user_id: 用户 ID
        limit: 返回记录数量限制，None 时返回全部

    Returns:
        list: 行为记录列表，格式为 [{product_id, behavior_type, score, timestamp}, ...]
              Redis 不可用时返回空列表
    """
    try:
        cache = get_redis_connection()
        key = get_behavior_cache_key(user_id)

        # 从 Redis 列表读取数据
        if limit:
            behaviors_json = cache.lrange(key, 0, limit - 1)
        else:
            behaviors_json = cache.lrange(key, 0, -1)

        # 解析 JSON
        behaviors = []
        for behavior_json in behaviors_json:
            try:
                behavior = json.loads(behavior_json)
                behaviors.append(behavior)
            except json.JSONDecodeError:
                continue

        return behaviors

    except Exception as e:
        # Redis 不可用时返回空列表
        logger.warning(f"Redis 读取失败: {e}")
        return []


def clear_user_behaviors(user_id):
    """
    清除用户行为缓存

    Args:
        user_id: 用户 ID

    Returns:
        bool: 是否成功清除
    """
    try:
        cache = get_redis_connection()
        key = get_behavior_cache_key(user_id)
        cache.delete(key)
        return True

    except Exception as e:
        logger.warning(f"Redis 清除失败: {e}")
        return False


def cache_recommendations(user_id, recommendations, source, timeout=None):
    """
    缓存用户的推荐结果

    Args:
        user_id: 用户 ID
        recommendations: 推荐商品 ID 列表
        source: 推荐来源 (itemcf/popular/mixed)
        timeout: 缓存过期时间（秒），默认使用配置

    Returns:
        bool: 是否成功缓存
    """
    try:
        cache = get_redis_connection()
        prefix = settings.RECOMMENDATION_CACHE.get('RECOMMENDATION_CACHE_PREFIX', 'recommendations')
        key = f"{prefix}:{user_id}"

        if timeout is None:
            timeout = settings.RECOMMENDATION_CACHE.get('RECOMMENDATION_CACHE_TIMEOUT', 600)

        data = {
            'product_ids': recommendations,
            'source': source,
        }

        cache.set(key, json.dumps(data), timeout)
        return True

    except Exception as e:
        logger.warning(f"推荐结果缓存失败: {e}")
        return False


def get_cached_recommendations(user_id):
    """
    获取缓存的推荐结果

    Args:
        user_id: 用户 ID

    Returns:
        dict: {product_ids: [...], source: '...'} 或 None（未命中）
    """
    try:
        cache = get_redis_connection()
        prefix = settings.RECOMMENDATION_CACHE.get('RECOMMENDATION_CACHE_PREFIX', 'recommendations')
        key = f"{prefix}:{user_id}"

        data_json = cache.get(key)
        if data_json:
            return json.loads(data_json)
        return None

    except Exception as e:
        logger.warning(f"读取推荐缓存失败: {e}")
        return None


def clear_recommendation_cache(user_id=None):
    """
    清除推荐缓存

    Args:
        user_id: 用户 ID，None 时清除所有推荐缓存

    Returns:
        bool: 是否成功清除
    """
    try:
        cache = get_redis_connection()
        prefix = settings.RECOMMENDATION_CACHE.get('RECOMMENDATION_CACHE_PREFIX', 'recommendations')

        if user_id:
            key = f"{prefix}:{user_id}"
            cache.delete(key)
        else:
            # 清除所有推荐缓存（需要扫描键，慎用）
            keys = cache.keys(f"{prefix}:*")
            if keys:
                cache.delete_many(keys)

        return True

    except Exception as e:
        logger.warning(f"清除推荐缓存失败: {e}")
        return False
