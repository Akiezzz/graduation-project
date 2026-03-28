"""
数据导出命令

将推荐系统所需的数据导出为 CSV 格式，用于离线评估。
"""

import csv
import os
from datetime import datetime, timezone
from django.core.management.base import BaseCommand
from django.conf import settings

from user.models import User
from product.models import Product
from recommendation.models import UserBehavior


class Command(BaseCommand):
    help = '导出推荐系统离线评估数据（interactions.csv, products.csv, users.csv）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default='recommendation/offline/data',
            help='导出目录路径（默认：recommendation/offline/data）',
        )
        parser.add_argument(
            '--train-test-split',
            type=str,
            default=None,
            help='训练集/测试集切分时间点（格式：YYYY-MM-DD，默认使用当前时间）',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10000,
            help='分批导出大小（默认：10000）',
        )

    def handle(self, *args, **options):
        output_dir = options['output_dir']
        split_date_str = options['train_test_split']
        batch_size = options['batch_size']

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        # 解析切分时间点
        if split_date_str:
            try:
                split_date = datetime.strptime(split_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            except ValueError:
                self.stdout.write(self.style.ERROR(f'Invalid date format: {split_date_str}. Use YYYY-MM-DD.'))
                return
        else:
            split_date = datetime.now(tz=timezone.utc)

        self.stdout.write(f'开始导出数据到 {output_dir}')
        self.stdout.write(f'训练集/测试集切分点：{split_date.strftime("%Y-%m-%d %H:%M:%S")}')

        # 导出 interactions.csv
        interactions_file = os.path.join(output_dir, 'interactions.csv')
        self.export_interactions(interactions_file, split_date, batch_size)
        self.stdout.write(self.style.SUCCESS(f'[OK] interactions.csv 导出完成'))

        # 导出 products.csv
        products_file = os.path.join(output_dir, 'products.csv')
        self.export_products(products_file)
        self.stdout.write(self.style.SUCCESS(f'[OK] products.csv 导出完成'))

        # 导出 users.csv
        users_file = os.path.join(output_dir, 'users.csv')
        self.export_users(users_file)
        self.stdout.write(self.style.SUCCESS(f'[OK] users.csv 导出完成'))

        # 导出元数据
        meta_file = os.path.join(output_dir, 'metadata.json')
        self.export_metadata(meta_file, split_date)
        self.stdout.write(self.style.SUCCESS(f'[OK] metadata.json 导出完成'))

        self.stdout.write(self.style.SUCCESS('所有数据导出完成！'))

    def export_interactions(self, filepath, split_date, batch_size):
        """导出用户-商品交互记录"""
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'user_id', 'product_id', 'behavior_type', 'score', 'timestamp', 'is_train'
            ])

            # 分批查询，避免内存溢出
            offset = 0
            while True:
                behaviors = UserBehavior.objects.select_related(
                    'user', 'product'
                ).order_by('created_at')[offset:offset + batch_size]

                if not behaviors:
                    break

                for behavior in behaviors:
                    is_train = 1 if behavior.created_at < split_date else 0
                    writer.writerow([
                        behavior.user_id,
                        behavior.product_id,
                        behavior.behavior_type,
                        behavior.score,
                        behavior.created_at.isoformat(),
                        is_train,
                    ])

                offset += batch_size
                self.stdout.write(f'  已导出 {offset} 条交互记录...', ending='\r')

    def export_products(self, filepath):
        """导出商品元数据"""
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'product_id', 'name', 'keywords', 'description', 'category_id',
                'price', 'stock', 'sales', 'is_active', 'created_at'
            ])

            products = Product.objects.all().iterator()
            for product in products:
                category_id = product.category_id if product.category else None
                writer.writerow([
                    product.id,
                    product.name,
                    product.keywords or '',
                    product.description or '',
                    category_id or '',
                    str(product.price),
                    product.stock,
                    product.sales,
                    1 if product.is_active else 0,
                    product.created_at.isoformat(),
                ])

    def export_users(self, filepath):
        """导出用户列表"""
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['user_id', 'username', 'date_joined'])

            users = User.objects.all().iterator()
            for user in users:
                writer.writerow([
                    user.id,
                    user.username,
                    user.date_joined.isoformat() if user.date_joined else '',
                ])

    def export_metadata(self, filepath, split_date):
        """导出元数据（JSON 格式）"""
        import json

        total_interactions = UserBehavior.objects.count()
        total_products = Product.objects.count()
        total_users = User.objects.count()
        train_interactions = UserBehavior.objects.filter(created_at__lt=split_date).count()
        test_interactions = total_interactions - train_interactions

        metadata = {
            'split_date': split_date.isoformat(),
            'total_users': total_users,
            'total_products': total_products,
            'total_interactions': total_interactions,
            'train_interactions': train_interactions,
            'test_interactions': test_interactions,
            'exported_at': datetime.now().isoformat(),
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
