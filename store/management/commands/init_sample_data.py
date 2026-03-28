"""
初始化示例商家和商品数据

创建3个示例商家账户，每个商家关联一个已审核的店铺，每个店铺包含5-10个示例商品。
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from store.models import Store
from product.models import Product, Category

User = get_user_model()


class Command(BaseCommand):
    help = '创建示例商家、店铺和商品数据'

    def handle(self, *args, **options):
        # 创建或获取示例分类
        electronics, _ = Category.objects.get_or_create(
            name='电子产品',
            defaults={'parent': None}
        )
        clothing, _ = Category.objects.get_or_create(
            name='服装鞋帽',
            defaults={'parent': None}
        )
        home, _ = Category.objects.get_or_create(
            name='家居用品',
            defaults={'parent': None}
        )
        food, _ = Category.objects.get_or_create(
            name='食品生鲜',
            defaults={'parent': None}
        )

        # 示例商家数据
        merchants_data = [
            {
                'username': 'merchant1',
                'email': 'merchant1@example.com',
                'password': 'demo123456',
                'store_name': '科技数码专营店',
                'description': '专注3C数码产品，正品保证，全国联保',
                'contact_person': '张三',
                'contact_phone': '13800138001',
                'license_number': 'LICENSE_001',
                'products': [
                    {'name': 'iPhone 15 Pro 256GB', 'price': 7999, 'stock': 50, 'category': electronics, 'keywords': '苹果 手机 5G', 'description': '搭载A17 Pro芯片，钛金属边框，48MP主摄'},
                    {'name': 'MacBook Air M3 13寸', 'price': 8999, 'stock': 30, 'category': electronics, 'keywords': '苹果 笔记本 轻薄本', 'description': 'M3芯片，8核CPU，10核GPU，16GB内存'},
                    {'name': 'AirPods Pro 2', 'price': 1899, 'stock': 100, 'category': electronics, 'keywords': '苹果 蓝牙耳机 降噪', 'description': '主动降噪，通透模式，MagSafe充电盒'},
                    {'name': 'iPad Air 5', 'price': 4799, 'stock': 40, 'category': electronics, 'keywords': '苹果 平板 M1', 'description': 'M1芯片，10.9英寸Liquid视网膜屏'},
                    {'name': 'Apple Watch Series 9', 'price': 2999, 'stock': 60, 'category': electronics, 'keywords': '苹果 智能手表', 'description': 'S9芯片，全天候视网膜显示屏'},
                    {'name': 'Sony WH-1000XM5', 'price': 2499, 'stock': 80, 'category': electronics, 'keywords': '索尼 头戴式耳机 降噪', 'description': '行业领先降噪，30小时续航'},
                ]
            },
            {
                'username': 'merchant2',
                'email': 'merchant2@example.com',
                'password': 'demo123456',
                'store_name': '时尚潮流服饰',
                'description': '引领潮流，品质生活，原创设计',
                'contact_person': '李四',
                'contact_phone': '13800138002',
                'license_number': 'LICENSE_002',
                'products': [
                    {'name': '纯棉基础T恤', 'price': 99, 'stock': 200, 'category': clothing, 'keywords': 'T恤 纯棉 圆领', 'description': '100%纯棉，舒适透气，多色可选'},
                    {'name': '复古牛仔裤男', 'price': 199, 'stock': 150, 'category': clothing, 'keywords': '牛仔裤 复古 直筒', 'description': '经典水洗工艺，宽松直筒版型'},
                    {'name': '运动跑鞋', 'price': 399, 'stock': 80, 'category': clothing, 'keywords': '跑鞋 运动 透气', 'description': '飞织鞋面，橡胶大底，减震耐磨'},
                    {'name': '连帽卫衣女', 'price': 159, 'stock': 120, 'category': clothing, 'keywords': '卫衣 连帽 加绒', 'description': '宽松版型，内里加绒，保暖舒适'},
                    {'name': '休闲工装裤', 'price': 179, 'stock': 100, 'category': clothing, 'keywords': '工装裤 多口袋 休闲', 'description': '耐磨面料，多口袋设计，实用时尚'},
                ]
            },
            {
                'username': 'merchant3',
                'email': 'merchant3@example.com',
                'password': 'demo123456',
                'store_name': '品质生活馆',
                'description': '精选好货，品质生活，健康至上',
                'contact_person': '王五',
                'contact_phone': '13800138003',
                'license_number': 'LICENSE_003',
                'products': [
                    {'name': '进口智利车厘子', 'price': 99, 'stock': 50, 'category': food, 'keywords': '车厘子 樱桃 进口', 'description': '智利空运，果径28-30mm，甜度高'},
                    {'name': '有机蔬菜礼盒', 'price': 79, 'stock': 100, 'category': food, 'keywords': '蔬菜 有机 礼盒', 'description': '8种有机蔬菜，当日采摘，新鲜直达'},
                    {'name': '乳胶枕', 'price': 299, 'stock': 60, 'category': home, 'keywords': '枕头 乳胶 保健', 'description': '天然乳胶，透气防螨，护颈助眠'},
                    {'name': '记忆棉床垫', 'price': 1599, 'stock': 30, 'category': home, 'keywords': '床垫 记忆棉 独立袋', 'description': '5cm记忆棉，独立袋装弹簧，承托均匀'},
                    {'name': '负离子吹风机', 'price': 399, 'stock': 80, 'category': home, 'keywords': '吹风机 负离子 护发', 'description': '1800W大功率，千万级负离子，快速干发'},
                    {'name': '智能保温杯', 'price': 129, 'stock': 150, 'category': home, 'keywords': '保温杯 智能 温度显示', 'description': '316不锈钢，LED温度显示，24小时保温'},
                    {'name': '进口红酒礼盒', 'price': 299, 'stock': 40, 'category': food, 'keywords': '红酒 法国 礼盒', 'description': '法国AOC级，双支礼盒装，木塞包装'},
                ]
            },
        ]

        created_users = 0
        created_stores = 0
        created_products = 0

        for data in merchants_data:
            # 创建用户
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'phone': data['contact_phone'],
                }
            )
            if created:
                user.set_password(data['password'])
                user.save()
                created_users += 1
                self.stdout.write(f'[OK] 创建用户: {data["username"]} (密码: {data["password"]})')
            else:
                self.stdout.write(f'  用户已存在: {data["username"]}')

            # 创建店铺
            store, created = Store.objects.get_or_create(
                owner=user,
                defaults={
                    'name': data['store_name'],
                    'description': data['description'],
                    'contact_person': data['contact_person'],
                    'contact_phone': data['contact_phone'],
                    'license_number': data['license_number'],
                    'status': 'active',
                    'reviewed_at': timezone.now(),
                }
            )
            if created:
                created_stores += 1
                self.stdout.write(f'[OK] 创建店铺: {data["store_name"]}')
            else:
                self.stdout.write(f'  店铺已存在: {data["store_name"]}')

            # 创建商品
            for prod_data in data['products']:
                product, created = Product.objects.get_or_create(
                    store=store,
                    name=prod_data['name'],
                    defaults={
                        'category': prod_data['category'],
                        'price': prod_data['price'],
                        'stock': prod_data['stock'],
                        'product_status': 'active',
                        'is_active': True,
                        'keywords': prod_data['keywords'],
                        'description': prod_data['description'],
                    }
                )
                if created:
                    created_products += 1
                    self.stdout.write(f'  [OK] 创建商品: {prod_data["name"]} - {prod_data["price"]}元')
                else:
                    self.stdout.write(f'    商品已存在: {prod_data["name"]}')

        # 统计信息
        total_stores = Store.objects.count()
        total_products = Product.objects.count()

        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write(f'创建用户: {created_users} 个')
        self.stdout.write(f'创建店铺: {created_stores} 个（总计 {total_stores} 个）')
        self.stdout.write(f'创建商品: {created_products} 个（总计 {total_products} 个）')
        self.stdout.write('=' * 60)
        self.stdout.write('')
        self.stdout.write('示例账户信息：')
        for data in merchants_data:
            self.stdout.write(f'  {data["username"]} / {data["password"]} - {data["store_name"]}')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('[DONE] 示例数据创建完成！'))
