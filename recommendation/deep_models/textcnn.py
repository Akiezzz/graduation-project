"""
TextCNN 模型

用于从商品文本（name + keywords + description）中提取特征。
基于卷积神经网络的文本分类模型，通过多尺度卷积核捕捉文本特征。
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class TextCNN(nn.Module):
    """
    TextCNN 文本编码器

    架构：
    - 嵌入层：将词索引转换为词向量
    - 卷积层：多尺度卷积（kernel_sizes=[2,3,4,5]）
    - 池化层：Max-over-time pooling
    - 全连接层：输出固定维度特征
    """

    def __init__(
        self,
        vocab_size,
        embed_dim=128,
        num_filters=100,
        kernel_sizes=[2, 3, 4, 5],
        output_dim=256,
        dropout=0.2,
        padding_idx=0
    ):
        """
        初始化 TextCNN 模型

        Args:
            vocab_size: 词汇表大小
            embed_dim: 词向量维度
            num_filters: 每种卷积核的滤波器数量
            kernel_sizes: 卷积核尺寸列表
            output_dim: 输出特征维度
            dropout: Dropout 概率
            padding_idx: Padding 标记的索引
        """
        super(TextCNN, self).__init__()

        self.vocab_size = vocab_size
        self.embed_dim = embed_dim
        self.num_filters = num_filters
        self.kernel_sizes = kernel_sizes
        self.output_dim = output_dim

        # 嵌入层
        self.embedding = nn.Embedding(
            vocab_size,
            embed_dim,
            padding_idx=padding_idx
        )

        # 多尺度卷积层
        self.convs = nn.ModuleList([
            nn.Conv1d(embed_dim, num_filters, kernel_size)
            for kernel_size in kernel_sizes
        ])

        # Dropout
        self.dropout = nn.Dropout(dropout)

        # 全连接层
        self.fc = nn.Linear(len(kernel_sizes) * num_filters, output_dim)

    def forward(self, x):
        """
        前向传播

        Args:
            x: 输入文本索引，shape [batch_size, seq_len]

        Returns:
            torch.Tensor: 文本特征，shape [batch_size, output_dim]
        """
        # 嵌入: [batch_size, seq_len, embed_dim]
        embedded = self.embedding(x)

        # 转置以适应 Conv1d: [batch_size, embed_dim, seq_len]
        embedded = embedded.permute(0, 2, 1)

        # 多尺度卷积 + 激活 + 池化
        conv_outputs = []
        for conv in self.convs:
            # 卷积: [batch_size, num_filters, seq_len - kernel_size + 1]
            conv_out = F.relu(conv(embedded))

            # Max-over-time pooling: [batch_size, num_filters]
            pooled = F.max_pool1d(conv_out, conv_out.size(2)).squeeze(2)
            conv_outputs.append(pooled)

        # 拼接所有卷积核的输出: [batch_size, len(kernel_sizes) * num_filters]
        cat = torch.cat(conv_outputs, dim=1)

        # Dropout
        cat = self.dropout(cat)

        # 全连接层: [batch_size, output_dim]
        output = self.fc(cat)

        return output

    def get_embedding_weight(self):
        """获取词向量矩阵"""
        return self.embedding.weight.data
