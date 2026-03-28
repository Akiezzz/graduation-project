"""
训练深度推荐模型命令

用于训练基于 TextCNN + Transformer 的混合推荐模型。
"""

import os
import pandas as pd
from pathlib import Path
from django.core.management.base import BaseCommand

# 检查 PyTorch 是否可用
try:
    import torch
    from recommendation.deep_models.vocab import Vocabulary
    from recommendation.deep_models.hybrid import HybridRecommendationModel
    from recommendation.deep_models.dataset import RecommendationDataset
    from recommendation.deep_models.trainer import ModelTrainer
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class Command(BaseCommand):
    help = '训练深度推荐模型（TextCNN + Transformer）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data-dir',
            type=str,
            default='recommendation/offline/data',
            help='数据目录路径（默认：recommendation/offline/data）',
        )
        parser.add_argument(
            '--model-dir',
            type=str,
            default='recommendation/models',
            help='模型保存目录（默认：recommendation/models）',
        )
        parser.add_argument(
            '--epochs',
            type=int,
            default=50,
            help='训练轮数（默认：50）',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=128,
            help='批大小（默认：128）',
        )
        parser.add_argument(
            '--lr',
            type=float,
            default=1e-3,
            help='学习率（默认：1e-3）',
        )
        parser.add_argument(
            '--max-seq-len',
            type=int,
            default=50,
            help='用户行为序列最大长度（默认：50）',
        )
        parser.add_argument(
            '--max-text-len',
            type=int,
            default=128,
            help='文本最大长度（默认：128）',
        )
        parser.add_argument(
            '--no-train',
            action='store_true',
            help='仅构建词汇表，不训练模型',
        )

    def handle(self, *args, **options):
        if not TORCH_AVAILABLE:
            self.stdout.write(self.style.ERROR('PyTorch 未安装，无法训练模型'))
            self.stdout.write('请运行：pip install torch==1.13.1 torchtext==0.14.1 jieba tqdm')
            return

        data_dir = options['data_dir']
        model_dir = options['model_dir']
        epochs = options['epochs']
        batch_size = options['batch_size']
        lr = options['lr']
        max_seq_len = options['max_seq_len']
        max_text_len = options['max_text_len']
        no_train = options['no_train']

        self.stdout.write('=' * 60)
        self.stdout.write('深度推荐模型训练')
        self.stdout.write('=' * 60)

        # 1. 加载数据
        self.stdout.write('\n[1/5] 加载数据...')
        interactions_file = os.path.join(data_dir, 'interactions.csv')
        products_file = os.path.join(data_dir, 'products.csv')
        product_texts_file = os.path.join(data_dir, 'product_texts.csv')

        # 检查文件是否存在
        if not os.path.exists(interactions_file):
            self.stdout.write(self.style.ERROR(f'文件不存在：{interactions_file}'))
            self.stdout.write('请先运行：python manage.py export_recommendation_data')
            return

        if not os.path.exists(product_texts_file):
            self.stdout.write(self.style.WARNING(f'文件不存在：{product_texts_file}'))
            self.stdout.write('尝试使用 products.csv...')
            if not os.path.exists(products_file):
                self.stdout.write(self.style.ERROR(f'文件不存在：{products_file}'))
                self.stdout.write('请先运行：python manage.py export_product_texts')
                return
            product_texts_file = products_file

        # 读取数据
        interactions_df = pd.read_csv(interactions_file)
        product_texts_df = pd.read_csv(product_texts_file)

        self.stdout.write(f'  交互记录：{len(interactions_df)}')
        self.stdout.write(f'  商品数量：{len(product_texts_df)}')

        # 2. 构建词汇表
        self.stdout.write('\n[2/5] 构建词汇表...')
        vocab = Vocabulary(min_freq=2)
        vocab.build_vocab_from_texts(product_texts_df['text'].tolist())

        self.stdout.write(f'  词汇表大小：{len(vocab)}')

        # 保存词汇表
        vocab_path = os.path.join(model_dir, 'vocab.json')
        os.makedirs(model_dir, exist_ok=True)
        vocab.save(vocab_path)
        self.stdout.write(self.style.SUCCESS(f'  [OK] 词汇表已保存：{vocab_path}'))

        if no_train:
            self.stdout.write(self.style.SUCCESS('\n词汇表构建完成（--no-train 模式）'))
            return

        # 3. 创建数据集
        self.stdout.write('\n[3/5] 创建数据集...')

        # 分割训练集和验证集
        train_df = interactions_df[interactions_df['is_train'] == 1].copy()
        val_df = interactions_df[interactions_df['is_train'] == 0].copy()

        if len(val_df) == 0:
            # 如果没有测试集，从训练集分割
            from sklearn.model_selection import train_test_split
            train_df, val_df = train_test_split(train_df, test_size=0.2, random_state=42)

        train_dataset = RecommendationDataset(
            interactions_df=train_df,
            products_df=product_texts_df,
            vocab=vocab,
            max_seq_len=max_seq_len,
            max_text_len=max_text_len,
            num_negatives=3
        )

        val_dataset = RecommendationDataset(
            interactions_df=val_df,
            products_df=product_texts_df,
            vocab=vocab,
            max_seq_len=max_seq_len,
            max_text_len=max_text_len,
            num_negatives=3
        )

        self.stdout.write(f'  训练集大小：{len(train_dataset)}')
        self.stdout.write(f'  验证集大小：{len(val_dataset)}')

        # 4. 初始化模型
        self.stdout.write('\n[4/5] 初始化模型...')

        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        num_products = product_texts_df['product_id'].nunique()

        model = HybridRecommendationModel(
            vocab_size=len(vocab),
            num_products=num_products,
            num_behavior_types=4,
            embed_dim=128,
            num_filters=100,
            kernel_sizes=[2, 3, 4, 5],
            d_model=256,
            nhead=4,
            num_transformer_layers=2,
            dropout=0.2,
            max_seq_len=max_seq_len,
            max_text_len=max_text_len
        )

        self.stdout.write(f'  设备：{device}')
        self.stdout.write(f'  模型参数量：{sum(p.numel() for p in model.parameters()):,}')

        # 5. 训练模型
        self.stdout.write('\n[5/5] 开始训练...')

        trainer = ModelTrainer(
            model=model,
            train_dataset=train_dataset,
            val_dataset=val_dataset,
            batch_size=batch_size,
            learning_rate=lr,
            num_epochs=epochs,
            device=device,
            model_save_dir=model_dir,
            early_stopping_patience=5
        )

        trainer.train()

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('训练完成！'))
        self.stdout.write(self.style.SUCCESS(f'模型已保存到：{model_dir}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
