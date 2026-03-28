"""
混合推荐模型

结合 TextCNN 商品编码器和 Transformer 用户序列建模器的混合推荐模型。
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

from .textcnn import TextCNN
from .transformer import UserSequenceTransformer


class HybridRecommendationModel(nn.Module):
    """
    混合推荐模型

    架构：
    - TextCNN: 将商品文本编码为向量
    - Transformer: 将用户行为序列编码为兴趣向量
    - MLP: 融合用户和商品特征，计算推荐分数
    """

    def __init__(
        self,
        vocab_size,
        num_products,
        num_behavior_types=4,
        embed_dim=128,
        num_filters=100,
        kernel_sizes=[2, 3, 4, 5],
        d_model=256,
        nhead=4,
        num_transformer_layers=2,
        dropout=0.2,
        max_seq_len=50,
        max_text_len=128
    ):
        """
        初始化混合推荐模型

        Args:
            vocab_size: 词汇表大小
            num_products: 商品总数
            num_behavior_types: 行为类型数量
            embed_dim: 词向量维度
            num_filters: TextCNN 每种卷积核的滤波器数量
            kernel_sizes: TextCNN 卷积核尺寸列表
            d_model: Transformer 模型维度
            nhead: 多头注意力头数
            num_transformer_layers: Transformer 层数
            dropout: Dropout 概率
            max_seq_len: 用户行为序列最大长度
            max_text_len: 文本最大长度
        """
        super(HybridRecommendationModel, self).__init__()

        self.vocab_size = vocab_size
        self.num_products = num_products
        self.d_model = d_model
        self.max_seq_len = max_seq_len
        self.max_text_len = max_text_len

        # TextCNN: 商品文本编码器
        self.textcnn = TextCNN(
            vocab_size=vocab_size,
            embed_dim=embed_dim,
            num_filters=num_filters,
            kernel_sizes=kernel_sizes,
            output_dim=d_model,
            dropout=dropout
        )

        # Transformer: 用户序列建模器
        self.user_transformer = UserSequenceTransformer(
            num_products=num_products,
            product_embed_dim=d_model,
            num_behavior_types=num_behavior_types,
            behavior_embed_dim=32,
            d_model=d_model,
            nhead=nhead,
            num_layers=num_transformer_layers,
            dropout=dropout,
            max_seq_len=max_seq_len
        )

        # MLP: 推荐分数计算
        hidden_dim = d_model * 2
        self.mlp = nn.Sequential(
            nn.Linear(d_model * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1),
        )

    def forward(self, user_sequence, candidate_texts):
        """
        前向传播

        Args:
            user_sequence: 用户行为序列字典
                - product_ids: [batch_size, seq_len]
                - behavior_types: [batch_size, seq_len]
                - scores: [batch_size, seq_len]
            candidate_texts: 候选商品文本
                - input_ids: [batch_size, num_candidates, text_len]
                - mask: [batch_size, num_candidates, text_len]

        Returns:
            torch.Tensor: 推荐分数，[batch_size, num_candidates]
        """
        # 1. 提取用户兴趣表示
        user_embedding = self.user_transformer(
            product_ids=user_sequence['product_ids'],
            behavior_types=user_sequence['behavior_types'],
            scores=user_sequence['scores'],
            mask=user_sequence.get('mask')
        )  # [batch_size, d_model]

        batch_size = user_embedding.size(0)
        num_candidates = candidate_texts['input_ids'].size(1)

        # 2. 提取候选商品特征
        # 展平候选商品维度: [batch_size * num_candidates, text_len]
        candidate_input_ids = candidate_texts['input_ids'].view(
            batch_size * num_candidates, -1
        )

        # TextCNN 编码: [batch_size * num_candidates, d_model]
        candidate_embeddings = self.textcnn(candidate_input_ids)

        # 恢复形状: [batch_size, num_candidates, d_model]
        candidate_embeddings = candidate_embeddings.view(
            batch_size, num_candidates, self.d_model
        )

        # 3. 计算推荐分数
        # 扩展用户嵌入: [batch_size, num_candidates, d_model]
        user_embedding_expanded = user_embedding.unsqueeze(1).expand(
            batch_size, num_candidates, self.d_model
        )

        # 拼接用户和商品特征: [batch_size, num_candidates, d_model * 2]
        combined = torch.cat([user_embedding_expanded, candidate_embeddings], dim=-1)

        # 展平以通过 MLP: [batch_size * num_candidates, d_model * 2]
        combined_flat = combined.view(batch_size * num_candidates, -1)

        # MLP 计算分数: [batch_size * num_candidates, 1]
        scores = self.mlp(combined_flat)

        # 恢复形状: [batch_size, num_candidates]
        scores = scores.view(batch_size, num_candidates)

        # Sigmoid 激活
        scores = torch.sigmoid(scores).squeeze(-1)

        return scores

    def compute_product_embeddings(self, product_texts_dict):
        """
        计算所有商品的 TextCNN 嵌入（用于缓存和加速推理）

        Args:
            product_texts_dict: {product_id: input_ids_tensor}

        Returns:
            torch.Tensor: 商品嵌入矩阵，[num_products, d_model]
        """
        self.eval()
        with torch.no_grad():
            embeddings = []
            for product_id in sorted(product_texts_dict.keys()):
                input_ids = product_texts_dict[product_id].unsqueeze(0)
                embed = self.textcnn(input_ids)
                embeddings.append(embed)

            embeddings = torch.cat(embeddings, dim=0)
        return embeddings

    def save_model(self, filepath):
        """保存模型"""
        torch.save({
            'model_state_dict': self.state_dict(),
            'model_config': {
                'vocab_size': self.vocab_size,
                'num_products': self.num_products,
                'd_model': self.d_model,
                'max_seq_len': self.max_seq_len,
                'max_text_len': self.max_text_len,
            }
        }, filepath)

    @classmethod
    def load_model(cls, filepath, device='cpu'):
        """加载模型"""
        checkpoint = torch.load(filepath, map_location=device)
        config = checkpoint['model_config']

        model = cls(**config)
        model.load_state_dict(checkpoint['model_state_dict'])
        model.to(device)

        return model
