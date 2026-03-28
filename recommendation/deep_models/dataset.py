"""
PyTorch Dataset 类

用于加载和处理推荐系统的训练数据。
"""

import torch
from torch.utils.data import Dataset
import pandas as pd
import random


class RecommendationDataset(Dataset):
    """
    推荐系统训练数据集

    输入：
    - 用户行为序列
    - 候选商品文本

    输出：
    - 推荐分数（0/1，表示是否交互）
    """

    def __init__(
        self,
        interactions_df,
        products_df,
        vocab,
        max_seq_len=50,
        max_text_len=128,
        num_negatives=3
    ):
        """
        初始化数据集

        Args:
            interactions_df: 交互记录 DataFrame（user_id, product_id, score, timestamp, is_train）
            products_df: 商品信息 DataFrame（product_id, text）
            vocab: 词汇表对象
            max_seq_len: 用户行为序列最大长度
            max_text_len: 文本最大长度
            num_negatives: 负样本数量
        """
        self.interactions_df = interactions_df[interactions_df['is_train'] == 1].copy()
        self.products_df = products_df
        self.vocab = vocab
        self.max_seq_len = max_seq_len
        self.max_text_len = max_text_len
        self.num_negatives = num_negatives

        # 构建用户行为序列
        self.user_sequences = self._build_user_sequences()

        # 构建用户交互的商品集合（用于负采样）
        self.user_interacted_products = self._build_user_interacted_sets()

        # 构建商品文本索引
        self.product_texts = self._build_product_texts()

        # 获取所有商品 ID（用于负采样）
        self.all_product_ids = set(products_df['product_id'].unique())

    def _build_user_sequences(self):
        """为每个用户构建行为序列"""
        user_sequences = {}

        # 按用户和时间排序
        sorted_df = self.interactions_df.sort_values(['user_id', 'timestamp'])

        for user_id in sorted_df['user_id'].unique():
            user_data = sorted_df[sorted_df['user_id'] == user_id]

            # 构建序列
            sequence = []
            for _, row in user_data.iterrows():
                sequence.append({
                    'product_id': int(row['product_id']),
                    'behavior_type': row['behavior_type'],
                    'score': float(row['score']),
                    'timestamp': row['timestamp'],
                })

            # 只保留最近的 N 条
            user_sequences[user_id] = sequence[-self.max_seq_len:]

        return user_sequences

    def _build_user_interacted_sets(self):
        """为每个用户构建交互商品集合"""
        interacted_sets = {}

        for user_id in self.interactions_df['user_id'].unique():
            user_products = self.interactions_df[
                self.interactions_df['user_id'] == user_id
            ]['product_id'].values
            interacted_sets[user_id] = set(user_products)

        return interacted_sets

    def _build_product_texts(self):
        """为每个商品构建文本编码"""
        product_texts = {}

        for _, row in self.products_df.iterrows():
            product_id = int(row['product_id'])
            text = row['text']

            # 编码文本
            encoded = self.vocab.encode(text)

            # 截断或填充
            if len(encoded) > self.max_text_len:
                encoded = encoded[:self.max_text_len]
            else:
                encoded = encoded + [self.vocab.PAD_IDX] * (self.max_text_len - len(encoded))

            product_texts[product_id] = torch.tensor(encoded, dtype=torch.long)

        return product_texts

    def _encode_behavior_type(self, behavior_type):
        """将行为类型编码为索引"""
        behavior_map = {
            'view': 0,
            'cart': 1,
            'order': 2,
            'review': 3,
        }
        return behavior_map.get(behavior_type, 0)

    def __len__(self):
        return len(self.user_sequences)

    def __getitem__(self, idx):
        """
        获取一个训练样本

        Returns:
            dict: {
                'user_sequence': {product_ids, behavior_types, scores},
                'candidate_texts': {input_ids},
                'label': 0 or 1
            }
        """
        # 随机选择一个用户
        user_id = list(self.user_sequences.keys())[idx]
        sequence = self.user_sequences[user_id]
        interacted_products = self.user_interacted_products.get(user_id, set())

        # 随机选择一个正样本
        if len(interacted_products) > 0:
            pos_product_id = random.choice(list(interacted_products))
        else:
            # 如果没有交互记录，随机选一个商品
            pos_product_id = random.choice(list(self.all_product_ids))

        # 随机选择负样本
        neg_product_id = random.choice(list(self.all_product_ids - interacted_products))

        # 随机选择正样本或负样本
        is_positive = random.random() < 0.5
        if is_positive:
            candidate_product_id = pos_product_id
            label = 1
        else:
            candidate_product_id = neg_product_id
            label = 0

        # 编码用户序列
        product_ids = []
        behavior_types = []
        scores = []

        for item in sequence:
            product_ids.append(item['product_id'])
            behavior_types.append(self._encode_behavior_type(item['behavior_type']))
            scores.append(item['score'])

        # 填充序列到 max_seq_len
        seq_len = len(product_ids)
        if seq_len < self.max_seq_len:
            product_ids += [0] * (self.max_seq_len - seq_len)
            behavior_types += [0] * (self.max_seq_len - seq_len)
            scores += [0.0] * (self.max_seq_len - seq_len)

        # 获取候选商品文本
        candidate_text = self.product_texts.get(
            candidate_product_id,
            torch.zeros(self.max_text_len, dtype=torch.long)
        )

        return {
            'user_sequence': {
                'product_ids': torch.tensor(product_ids, dtype=torch.long),
                'behavior_types': torch.tensor(behavior_types, dtype=torch.long),
                'scores': torch.tensor(scores, dtype=torch.float),
            },
            'candidate_texts': {
                'input_ids': candidate_text.unsqueeze(0),  # [1, max_text_len]
            },
            'label': torch.tensor(label, dtype=torch.float),
        }
