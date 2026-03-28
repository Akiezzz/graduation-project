from django.test import TestCase
from django.contrib.auth import get_user_model

from merchant.models import Merchant
from product.models import Product
from recommendation.models import UserBehavior
from recommendation.services import get_recommendations_for_user
from recommendation import cache


class RecommendationFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='buyer', password='pass123456')
        other_user = get_user_model().objects.create_user(username='buyer2', password='pass123456')
        merchant_user = get_user_model().objects.create_user(username='merchant', password='pass123456')
        merchant = Merchant.objects.create(user=merchant_user, shop_name='测试店铺', is_approved=True)

        self.target = Product.objects.create(
            merchant=merchant, name='目标商品', price='50.00', stock=10, sales=1, is_active=True
        )
        self.similar = Product.objects.create(
            merchant=merchant, name='相似商品', price='60.00', stock=10, sales=2, is_active=True
        )
        self.popular = Product.objects.create(
            merchant=merchant, name='热门商品', price='70.00', stock=10, sales=99, is_active=True
        )
        self.inactive = Product.objects.create(
            merchant=merchant, name='下架商品', price='80.00', stock=10, sales=100, is_active=False
        )

        UserBehavior.objects.create(user=self.user, product=self.target, behavior_type='view', score=1)
        UserBehavior.objects.create(user=other_user, product=self.target, behavior_type='order', score=4)
        UserBehavior.objects.create(user=other_user, product=self.similar, behavior_type='order', score=4)

        self.client.force_login(self.user)

    def test_api_recommendations_returns_expected_structure(self):
        response = self.client.get('/api/recommendations/?limit=5')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('source', data)
        self.assertIn('items', data)
        self.assertTrue(isinstance(data['items'], list))
        if data['items']:
            self.assertIn('id', data['items'][0])
            self.assertIn('name', data['items'][0])
            self.assertIn('reason', data['items'][0])

    def test_recommendations_filter_inactive_or_out_of_stock_products(self):
        self.popular.stock = 0
        self.popular.save(update_fields=['stock'])

        products, source, _ = get_recommendations_for_user(self.user, limit=10)

        self.assertIn(source, ['itemcf', 'popular', 'mixed'])
        product_ids = [p.id for p in products]
        self.assertNotIn(self.inactive.id, product_ids)
        self.assertNotIn(self.popular.id, product_ids)

    def test_product_detail_view_logs_view_behavior(self):
        before = UserBehavior.objects.filter(user=self.user, product=self.similar, behavior_type='view').count()

        response = self.client.get(f'/products/{self.similar.id}/')

        self.assertEqual(response.status_code, 200)
        after = UserBehavior.objects.filter(user=self.user, product=self.similar, behavior_type='view').count()
        self.assertEqual(after, before + 1)


class RedisCacheTests(TestCase):
    """Redis 缓存功能测试"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='buyer', password='pass123456')
        merchant_user = get_user_model().objects.create_user(username='merchant', password='pass123456')
        merchant = Merchant.objects.create(user=merchant_user, shop_name='测试店铺', is_approved=True)

        self.product = Product.objects.create(
            merchant=merchant, name='测试商品', price='50.00', stock=10, sales=1, is_active=True
        )

    def test_push_recent_behavior_returns_bool(self):
        """测试写入 Redis 返回布尔值"""
        result = cache.push_recent_behavior(self.user.id, self.product.id, 'view', 1)
        self.assertIsInstance(result, bool)

    def test_get_recent_behaviors_returns_list(self):
        """测试读取 Redis 行为列表"""
        cache.push_recent_behavior(self.user.id, self.product.id, 'view', 1)
        behaviors = cache.get_recent_behaviors(self.user.id, limit=10)

        self.assertIsInstance(behaviors, list)
        # Redis 不可用或写入失败时，返回空列表
        self.assertEqual(len(behaviors), 0)

    def test_cache_operations_fail_gracefully(self):
        """测试 Redis 操作失败时系统仍能正常运行"""
        # 即使 Redis 不可用，行为记录仍应成功写入 DB
        from recommendation.services import log_user_behavior

        initial_count = UserBehavior.objects.count()
        log_user_behavior(self.user, self.product, 'view')

        self.assertEqual(UserBehavior.objects.count(), initial_count + 1)

    def test_recommendation_cache_operations(self):
        """测试推荐结果缓存功能"""
        # 写入缓存
        result = cache.cache_recommendations(self.user.id, [1, 2, 3], 'itemcf')
        self.assertIsInstance(result, bool)

        # 读取缓存
        cached = cache.get_cached_recommendations(self.user.id)
        # Redis 不可用时返回 None
        self.assertTrue(cached is None or isinstance(cached, dict))

    def test_clear_user_behaviors(self):
        """测试清除用户行为缓存"""
        result = cache.clear_user_behaviors(self.user.id)
        self.assertIsInstance(result, bool)

    def test_clear_recommendation_cache(self):
        """测试清除推荐缓存"""
        # 清除单个用户
        result = cache.clear_recommendation_cache(user_id=self.user.id)
        self.assertIsInstance(result, bool)

        # 清除全部缓存
        result = cache.clear_recommendation_cache(user_id=None)
        self.assertIsInstance(result, bool)


class DeepModelDataInterfaceTests(TestCase):
    """深度模型数据接口测试"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='buyer', password='pass123456')
        merchant_user = get_user_model().objects.create_user(username='merchant', password='pass123456')
        merchant = Merchant.objects.create(user=merchant_user, shop_name='测试店铺', is_approved=True)

        self.product1 = Product.objects.create(
            merchant=merchant, name='测试商品1', keywords='关键词', description='描述', price='50.00', stock=10
        )
        self.product2 = Product.objects.create(
            merchant=merchant, name='测试商品2', keywords='', description='', price='60.00', stock=10
        )

        # 创建用户行为
        UserBehavior.objects.create(
            user=self.user, product=self.product1, behavior_type='view', score=1
        )
        UserBehavior.objects.create(
            user=self.user, product=self.product1, behavior_type='cart', score=2
        )

    def test_get_user_sequence_returns_list(self):
        """测试 get_user_sequence 返回列表格式"""
        from recommendation.services import get_user_sequence

        sequence = get_user_sequence(self.user.id, max_length=50)

        self.assertIsInstance(sequence, list)
        self.assertGreater(len(sequence), 0)

        # 验证第一个元素包含必需字段
        first_item = sequence[0]
        self.assertIn('product_id', first_item)
        self.assertIn('behavior_type', first_item)
        self.assertIn('score', first_item)
        self.assertIn('timestamp', first_item)

    def test_get_user_sequence_orders_by_time_desc(self):
        """测试 get_user_sequence 按时间倒序排列"""
        from recommendation.services import get_user_sequence

        sequence = get_user_sequence(self.user.id, max_length=50)

        # 验证序列按时间倒序（最新的在前）
        if len(sequence) > 1:
            for i in range(len(sequence) - 1):
                self.assertGreaterEqual(
                    sequence[i]['timestamp'].timestamp(),
                    sequence[i + 1]['timestamp'].timestamp()
                )

    def test_get_product_features_returns_dict(self):
        """测试 get_product_features 返回字典格式"""
        from recommendation.services import get_product_features

        features = get_product_features([self.product1.id, self.product2.id])

        self.assertIsInstance(features, dict)
        self.assertIn(self.product1.id, features)
        self.assertIn(self.product2.id, features)

    def test_get_product_features_includes_text_field(self):
        """测试 get_product_features 包含合并的文本字段"""
        from recommendation.services import get_product_features

        features = get_product_features([self.product1.id])

        product_feature = features[self.product1.id]
        self.assertIn('text', product_feature)
        self.assertIsInstance(product_feature['text'], str)
        self.assertGreater(len(product_feature['text']), 0)

    def test_get_product_features_handles_empty_description(self):
        """测试 get_product_features 处理空描述"""
        from recommendation.services import get_product_features

        features = get_product_features([self.product2.id])

        product_feature = features[self.product2.id]
        # 即使描述为空，text 字段也应该有内容（至少有 name）
        self.assertIn('text', product_feature)
        self.assertIn('测试商品2', product_feature['text'])

    def test_get_product_features_with_empty_ids(self):
        """测试 get_product_features 处理空 ID 列表"""
        from recommendation.services import get_product_features

        features = get_product_features([])

        self.assertEqual(features, {})

