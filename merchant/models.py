from django.db import models
from django.conf import settings


class Merchant(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='用户')
    shop_name = models.CharField('店铺名称', max_length=100)
    description = models.TextField('店铺描述', blank=True)
    logo = models.ImageField('店铺Logo', upload_to='shop_logos/', blank=True)
    is_approved = models.BooleanField('已审核', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '商家'
        verbose_name_plural = '商家'

    def __str__(self):
        return self.shop_name
