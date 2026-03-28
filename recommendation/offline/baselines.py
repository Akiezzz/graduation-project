"""
基线推荐算法实现

提供离线评估用的基线算法，包括：
- PopularBaseline: 基于销量的热门推荐
- ItemCFBaseline: 基于物品协同过滤的个性化推荐
"""

import math
import csv
from collections import defaultdict
from pathlib import Path


class BaseBaseline:
    """基线算法基类"""

    def __init__(self, train_data, products_data):
        """
        Args:
            train_data: 训练集交互记录，格式为 [(user_id, product_id, score), ...]
            products_data: 商品数据，格式为 {product_id: {name, price, stock, sales, ...}}
        """
        self.train_data = train_data
        self.products_data = products_data

    def recommend(self, user_id, k=10, exclude_product_ids=None):
        """
        为用户生成 Top-K 推荐列表

        Args:
            user_id: 用户 ID
            k: 推荐数量
            exclude_product_ids: 排除的商品 ID 列表

        Returns:
            list: 推荐商品 ID 列表，按相关性降序排列
        """
        raise NotImplementedError


class PopularBaseline(BaseBaseline):
    """
    热门推荐基线

    按商品销量降序推荐，不考虑用户个性化。
    """

    def __init__(self, train_data, products_data):
        super().__init__(train_data, products_data)

        # 预计算商品热度（销量）
        self.product_popularity = {}
        for pid, product in products_data.items():
            self.product_popularity[pid] = product.get('sales', 0)

    def recommend(self, user_id, k=10, exclude_product_ids=None):
        """返回最热门的 K 个商品"""
        exclude = set(exclude_product_ids or [])

        # 按销量降序排序
        sorted_products = sorted(
            self.product_popularity.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # 过滤排除的商品
        recommendations = [pid for pid, _ in sorted_products if pid not in exclude]

        return recommendations[:k]


class ItemCFBaseline(BaseBaseline):
    """
    物品协同过滤基线

    基于用户-物品交互矩阵，计算物品相似度，生成个性化推荐。
    """

    def __init__(self, train_data, products_data):
        super().__init__(train_data, products_data)

        # 构建用户-物品交互矩阵
        self.user_items = defaultdict(dict)
        for user_id, product_id, score in train_data:
            self.user_items[user_id][product_id] = score

        # 预计算物品相似度矩阵
        self.item_similarity = self._compute_item_similarity()

    def _compute_item_similarity):
        """
        计算物品相似度矩阵

        使用余弦相似度：
            sim(i, j) = |U_i ∩ U_j| / sqrt(|U_i| * |U_j|)

        Returns:
            dict: {item_id: {similar_item_id: similarity, ...}}
        """
        # 构建物品-用户倒排索引
        item_users = defaultdict(set)
        for user_id, items in self.user_items.items():
            for item_id in items.keys():
                item_users[item_id].add(user_id)

        # 计算相似度
        similarity = defaultdict(dict)
        for item_i, users_i in item_users.items():
            for item_j, users_j in item_users.items():
                if item_i == item_j:
                    continue

                # 计算共同用户数
                common_users = users_i & users_j
                if not common_users:
                    continue

                # 余弦相似度
                sim = len(common_users) / math.sqrt(len(users_i) * len(users_j))
                if sim > 0:
                    similarity[item_i][item_j] = sim

        return similarity

    def recommend(self, user_id, k=10, exclude_product_ids=None):
        """
        为用户生成 Top-K 推荐列表

        算法流程：
        1. 获取用户历史交互物品
        2. 对每个历史物品，找出相似物品
        3. 聚合相似物品的推荐分数
        4. 按分数降序返回 Top-K
        """
        exclude = set(exclude_product_ids or [])

        # 获取用户历史物品
        user_history = self.user_items.get(user_id, {})
        if not user_history:
            # 无历史记录，返回空列表
            return []

        # 计算候选物品的推荐分数
        candidate_scores = defaultdict(float)
        for hist_item, score in user_history.items():
            # 获取与历史物品相似的物品
            similar_items = self.item_similarity.get(hist_item, {})
            for similar_item, similarity in similar_items.items():
                if similar_item in exclude or similar_item in user_history:
                    continue
                # 推荐分数 = 相似度 × 用户对历史物品的评分
                candidate_scores[similar_item] += similarity * score

        # 按分数降序排序
        sorted_candidates = sorted(
            candidate_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [item_id for item_id, _ in sorted_candidates[:k]]


def load_train_data(data_dir):
    """
    加载训练数据

    Args:
        data_dir: 数据目录路径

    Returns:
        tuple: (train_data, products_data)
            - train_data: [(user_id, product_id, score), ...]
            - products_data: {product_id: {name, price, stock, sales, ...}}
    """
    data_dir = Path(data_dir)

    # 加载交互记录（仅训练集）
    train_data = []
    interactions_file = data_dir / 'interactions.csv'
    with open(interactions_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['is_train'] == '1':  # 仅训练集
                train_data.append((
                    int(row['user_id']),
                    int(row['product_id']),
                    float(row['score']),
                ))

    # 加载商品数据
    products_data = {}
    products_file = data_dir / 'products.csv'
    with open(products_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = int(row['product_id'])
            products_data[pid] = {
                'name': row['name'],
                'keywords': row['keywords'],
                'description': row['description'],
                'category_id': int(row['category_id']) if row['category_id'] else None,
                'price': float(row['price']),
                'stock': int(row['stock']),
                'sales': int(row['sales']),
                'is_active': row['is_active'] == '1',
            }

    return train_data, products_data


def load_test_data(data_dir):
    """
    加载测试数据

    Args:
        data_dir: 数据目录路径

    Returns:
        dict: {user_id: set([relevant_product_id, ...])}
               relevant 定义为测试集中用户实际交互的商品（score >= 2）
    """
    data_dir = Path(data_dir)
    test_data = defaultdict(set)

    interactions_file = data_dir / 'interactions.csv'
    with open(interactions_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['is_train'] == '0':  # 仅测试集
                user_id = int(row['user_id'])
                product_id = int(row['product_id'])
                score = float(row['score'])

                # 定义相关商品：score >= 2（cart/order/review）
                if score >= 2:
                    test_data[user_id].add(product_id)

    return test_data
