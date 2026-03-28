from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    phone = models.CharField('手机号', max_length=20, blank=True)
    avatar = models.ImageField('头像', upload_to='avatars/', blank=True)
    address = models.TextField('默认地址', blank=True)

    @property
    def store_profile(self):
        """用户拥有的店铺（如果有）"""
        return getattr(self, 'owned_store', None)

    @property
    def is_store_owner(self):
        """用户是否为店铺所有者（已审核通过）"""
        return bool(self.store_profile and self.store_profile.is_active)

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'
