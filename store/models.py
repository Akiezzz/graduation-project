"""
店铺模型

商家申请开店的核心模型，包含店铺审核流程。
"""

from django.db import models
from django.conf import settings


class Store(models.Model):
    """店铺模型

    用户申请开设店铺，审核通过后自动成为商家角色。
    """

    STATUS_CHOICES = [
        ('pending', '待审核'),
        ('active', '正常营业'),
        ('disabled', '已禁用'),
        ('rejected', '已拒绝'),
    ]

    # 基本信息
    name = models.CharField('店铺名称', max_length=100)
    description = models.TextField('店铺简介', blank=True)
    logo = models.ImageField('店铺Logo', upload_to='store_logos/', blank=True)

    # 联系信息
    contact_person = models.CharField('联系人', max_length=50)
    contact_phone = models.CharField('联系电话', max_length=20)
    license_number = models.CharField('营业执照号', max_length=50, unique=True)

    # 状态管理
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')

    # 关联关系
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='店主',
        related_name='owned_store'
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='审核人',
        related_name='reviewed_stores'
    )

    # 时间戳
    created_at = models.DateTimeField('申请时间', auto_now_add=True)
    reviewed_at = models.DateTimeField('审核时间', null=True, blank=True)

    class Meta:
        verbose_name = '店铺'
        verbose_name_plural = '店铺'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def is_active(self):
        """店铺是否正常营业"""
        return self.status == 'active'

    @property
    def is_pending(self):
        """店铺是否待审核"""
        return self.status == 'pending'
