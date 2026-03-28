from django.test import TestCase
from django.contrib.auth import get_user_model

from merchant.models import Merchant
from product.models import Product
from order.models import Cart, CartItem, Order


class OrderFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='buyer', password='pass123456')
        merchant_user = get_user_model().objects.create_user(username='merchant', password='pass123456')
        self.merchant = Merchant.objects.create(user=merchant_user, shop_name='测试店铺', is_approved=True)
        self.product = Product.objects.create(
            merchant=self.merchant,
            name='测试商品',
            price='100.00',
            stock=10,
            sales=0,
            is_active=True,
        )
        self.client.force_login(self.user)

    def test_checkout_success_updates_stock_and_clears_cart(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        response = self.client.post('/order/checkout/', {'address': '上海市静安区', 'remark': '测试下单'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.filter(user=self.user).count(), 1)
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.status, 'pending')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)
        self.assertEqual(self.product.sales, 2)
        self.assertEqual(cart.items.count(), 0)

    def test_checkout_insufficient_stock_creates_no_order(self):
        self.product.stock = 1
        self.product.save(update_fields=['stock'])

        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        response = self.client.post('/order/checkout/', {'address': '上海市静安区'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.filter(user=self.user).count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)
        self.assertEqual(cart.items.count(), 1)

    def test_api_pay_order_success(self):
        order = Order.objects.create(user=self.user, status='pending', address='上海市静安区', total_price='100.00')

        response = self.client.post(f'/api/orders/{order.id}/pay/')

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')

    def test_api_pay_non_pending_order_fails(self):
        order = Order.objects.create(user=self.user, status='paid', address='上海市静安区', total_price='100.00')

        response = self.client.post(f'/api/orders/{order.id}/pay/')

        self.assertEqual(response.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
