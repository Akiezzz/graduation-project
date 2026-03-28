from django.db import models
from django.conf import settings
from product.models import Product


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='用户')

    class Meta:
        verbose_name = '购物车'
        verbose_name_plural = '购物车'


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name='购物车')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='商品')
    quantity = models.PositiveIntegerField('数量', default=1)

    class Meta:
        verbose_name = '购物车商品'
        verbose_name_plural = '购物车商品'
        unique_together = ('cart', 'product')


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', '待付款'),
        ('paid', '已付款'),
        ('shipped', '已发货'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='用户')
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    address = models.TextField('收货地址')
    total_price = models.DecimalField('总价', max_digits=12, decimal_places=2)
    created_at = models.DateTimeField('下单时间', auto_now_add=True)
    remark = models.CharField('备注', max_length=200, blank=True)

    class Meta:
        verbose_name = '订单'
        verbose_name_plural = '订单'

    def __str__(self):
        return f'Order#{self.pk}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='订单')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='商品')
    quantity = models.PositiveIntegerField('数量')
    price = models.DecimalField('单价', max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = '订单商品'
        verbose_name_plural = '订单商品'
