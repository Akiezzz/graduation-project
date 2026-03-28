from django.db import models
from django.conf import settings
from product.models import Product


class BrowseHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='用户')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='商品')
    viewed_at = models.DateTimeField('浏览时间', auto_now=True)

    class Meta:
        verbose_name = '浏览历史'
        verbose_name_plural = '浏览历史'
        ordering = ['-viewed_at']
        unique_together = ('user', 'product')


class UserBehavior(models.Model):
    BEHAVIOR_VIEW = 'view'
    BEHAVIOR_CART = 'cart'
    BEHAVIOR_ORDER = 'order'
    BEHAVIOR_REVIEW = 'review'

    BEHAVIOR_CHOICES = [
        (BEHAVIOR_VIEW, '浏览'),
        (BEHAVIOR_CART, '加购'),
        (BEHAVIOR_ORDER, '下单'),
        (BEHAVIOR_REVIEW, '评价'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='用户')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='商品')
    behavior_type = models.CharField('行为类型', max_length=20, choices=BEHAVIOR_CHOICES)
    score = models.PositiveSmallIntegerField('行为权重', default=1)
    created_at = models.DateTimeField('行为时间', auto_now_add=True)

    class Meta:
        verbose_name = '用户行为'
        verbose_name_plural = '用户行为'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['product', 'created_at']),
            models.Index(fields=['behavior_type']),
        ]
