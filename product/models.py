from django.db import models


class Category(models.Model):
    name = models.CharField('分类名', max_length=50)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, verbose_name='父分类')

    class Meta:
        verbose_name = '商品分类'
        verbose_name_plural = '商品分类'

    def __str__(self):
        return self.name


class Product(models.Model):
    """商品模型"""
    PRODUCT_STATUS_CHOICES = [
        ('active', '销售中'),
        ('inactive', '已下架'),
        ('violated', '违规下架'),
    ]

    # 所属店铺
    store = models.ForeignKey('store.Store', on_delete=models.CASCADE, verbose_name='店铺', related_name='products', null=True, blank=True)

    # 基本信息
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='分类')
    name = models.CharField('商品名称', max_length=200)
    keywords = models.CharField('关键词', max_length=255, blank=True)
    description = models.TextField('商品描述', blank=True)

    # 价格和库存
    price = models.DecimalField('价格', max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField('库存', default=0)

    # 图片
    image = models.ImageField('商品图片', upload_to='products/', blank=True)

    # 状态管理
    is_active = models.BooleanField('快速上下架', default=True, help_text='用于快速切换商品上下架状态')
    product_status = models.CharField('商品状态', max_length=20, choices=PRODUCT_STATUS_CHOICES, default='active', db_index=True, help_text='active:销售中, inactive:商家下架, violated:管理员强制下架')

    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    sales = models.PositiveIntegerField('销量', default=0)

    class Meta:
        verbose_name = '商品'
        verbose_name_plural = '商品'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', verbose_name='商品')
    user = models.ForeignKey('user.User', on_delete=models.CASCADE, verbose_name='用户')
    rating = models.PositiveSmallIntegerField('评分', choices=[(i, i) for i in range(1, 6)])
    content = models.TextField('评价内容', blank=True)
    created_at = models.DateTimeField('评价时间', auto_now_add=True)

    class Meta:
        verbose_name = '商品评价'
        verbose_name_plural = '商品评价'
