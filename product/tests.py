from django.test import TestCase
from django.contrib.auth import get_user_model

from merchant.models import Merchant
from order.models import Order, OrderItem
from product.models import Product, ProductReview


class ProductReviewPermissionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='buyer', password='pass123456')
        merchant_user = get_user_model().objects.create_user(username='merchant', password='pass123456')
        merchant = Merchant.objects.create(user=merchant_user, shop_name='测试店铺', is_approved=True)
        self.product = Product.objects.create(
            merchant=merchant,
            name='可评价商品',
            price='88.00',
            stock=20,
            sales=0,
            is_active=True,
        )
        self.client.force_login(self.user)

    def test_api_review_rejected_without_completed_order(self):
        response = self.client.post(
            f'/api/products/{self.product.id}/reviews/',
            {'rating': 5, 'content': '很好'},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(ProductReview.objects.filter(product=self.product, user=self.user).count(), 0)

    def test_api_review_allowed_with_completed_order(self):
        order = Order.objects.create(user=self.user, status='completed', address='上海市静安区', total_price='88.00')
        OrderItem.objects.create(order=order, product=self.product, quantity=1, price='88.00')

        response = self.client.post(
            f'/api/products/{self.product.id}/reviews/',
            {'rating': 4, 'content': '不错'},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(ProductReview.objects.filter(product=self.product, user=self.user).count(), 1)
