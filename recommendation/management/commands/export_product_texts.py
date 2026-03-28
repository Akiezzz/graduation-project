"""
导出商品文本数据命令

为深度学习模型准备商品文本数据。
"""

import csv
import os
from pathlib import Path
from django.core.management.base import BaseCommand

from product.models import Product


class Command(BaseCommand):
    help = '导出商品文本数据（用于深度学习模型训练）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-file',
            type=str,
            default='recommendation/offline/data/product_texts.csv',
            help='输出文件路径（默认：recommendation/offline/data/product_texts.csv）',
        )

    def handle(self, *args, **options):
        output_file = options['output_file']

        # 创建输出目录
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        self.stdout.write(f'开始导出商品文本数据到 {output_file}')

        # 导出商品文本
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['product_id', 'name', 'keywords', 'description', 'text'])

            products = Product.objects.all().iterator()
            total = 0

            for product in products:
                # 合并文本
                text_parts = [product.name]
                if product.keywords:
                    text_parts.append(product.keywords)
                if product.description:
                    text_parts.append(product.description)
                combined_text = ' '.join(text_parts)

                writer.writerow([
                    product.id,
                    product.name,
                    product.keywords or '',
                    product.description or '',
                    combined_text,
                ])

                total += 1

                if total % 1000 == 0:
                    self.stdout.write(f'  已导出 {total} 个商品...', ending='\r')

        self.stdout.write(self.style.SUCCESS(f'\n[OK] 导出完成，共 {total} 个商品'))
