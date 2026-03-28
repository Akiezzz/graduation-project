"""
Transformer 用户序列建模器

使用 Transformer 编码器对用户行为序列进行建模，捕获用户的兴趣演化。
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F


class PositionalEncoding(nn.Module):
    """正弦位置编码"""

    def __init__(self, d_model, max_len=5000):
        """
        Args:
            d_model: 模型维度
            max_len: 最大序列长度
        """
        super(PositionalEncoding, self).__init__()

        # 计算位置编码
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))

        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # [1, max_len, d_model]

        self.register_buffer('pe', pe)

    def forward(self, x):
        """
        Args:
            x: [batch_size, seq_len, d_model]
        Returns:
            [batch_size, seq_len, d_model]
        """
        return x + self.pe[:, :x.size(1), :]


class UserSequenceTransformer(nn.Module):
    """
    用户行为序列 Transformer 模型

    输入：用户行为序列 [product_id, behavior_type, score]
    输出：用户兴趣表示向量
    """

    def __init__(
        self,
        num_products,
        product_embed_dim=256,
        num_behavior_types=4,
        behavior_embed_dim=32,
        d_model=256,
        nhead=4,
        num_layers=2,
        dim_feedforward=512,
        dropout=0.1,
        max_seq_len=50
    ):
        """
        初始化 Transformer 模型

        Args:
            num_products: 商品总数
            product_embed_dim: 商品嵌入维度（应与 TextCNN 输出维度一致）
            num_behavior_types: 行为类型数量（view, cart, order, review）
            behavior_embed_dim: 行为类型嵌入维度
            d_model: Transformer 模型维度
            nhead: 多头注意力头数
            num_layers: Transformer 层数
            dim_feedforward: 前馈网络隐藏层维度
            dropout: Dropout 概率
            max_seq_len: 最大序列长度
        """
        super(UserSequenceTransformer, self).__init__()

        self.product_embed_dim = product_embed_dim
        self.num_behavior_types = num_behavior_types

        # 商品嵌入层（使用预训练的 TextCNN 特征或随机初始化）
        self.product_embedding = nn.Embedding(
            num_products,
            product_embed_dim,
            padding_idx=0
        )

        # 行为类型嵌入
        self.behavior_embedding = nn.Embedding(
            num_behavior_types,
            behavior_embed_dim
        )

        # 输入投影层：将商品嵌入 + 行为嵌入投影到 d_model
        input_dim = product_embed_dim + behavior_embed_dim + 1  # +1 for score
        self.input_projection = nn.Linear(input_dim, d_model)

        # 位置编码
        self.pos_encoder = PositionalEncoding(d_model, max_seq_len)

        # Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers
        )

        # Dropout
        self.dropout = nn.Dropout(dropout)

    def forward(self, product_ids, behavior_types, scores, mask=None):
        """
        前向传播

        Args:
            product_ids: 商品 ID 序列，[batch_size, seq_len]
            behavior_types: 行为类型序列，[batch_size, seq_len]
            scores: 行为分数序列，[batch_size, seq_len]
            mask: 注意力掩码，[batch_size, seq_len]，True 表示屏蔽

        Returns:
            torch.Tensor: 用户兴趣表示，[batch_size, d_model]
        """
        # 商品嵌入: [batch_size, seq_len, product_embed_dim]
        product_embeds = self.product_embedding(product_ids)

        # 行为类型嵌入: [batch_size, seq_len, behavior_embed_dim]
        behavior_embeds = self.behavior_embedding(behavior_types)

        # 分数归一化并扩展维度: [batch_size, seq_len, 1]
        scores_norm = scores.unsqueeze(-1) / 4.0  # 归一化到 [0, 1]

        # 拼接所有特征: [batch_size, seq_len, input_dim]
        combined = torch.cat([product_embeds, behavior_embeds, scores_norm], dim=-1)

        # 投影到 d_model: [batch_size, seq_len, d_model]
        x = self.input_projection(combined)

        # 位置编码
        x = self.pos_encoder(x)

        # Dropout
        x = self.dropout(x)

        # Transformer Encoder
        # 注意：mask 的 True 表示屏蔽位置
        if mask is not None:
            # 转换 mask 格式（TransformerEncoder 需要 key_padding_mask）
            x = self.transformer_encoder(x, src_key_padding_mask=mask)
        else:
            x = self.transformer_encoder(x)

        # 取最后一个有效时间步的输出作为用户表示
        # 简化处理：直接取最后一个位置
        user_embedding = x[:, -1, :]  # [batch_size, d_model]

        return user_embedding

    def set_product_embeddings(self, embeddings):
        """
        设置商品嵌入矩阵（用于加载 TextCNN 预训练特征）

        Args:
            embeddings: 预训练的商品嵌入，[num_products, product_embed_dim]
        """
        self.product_embedding.weight.data.copy_(embeddings)
