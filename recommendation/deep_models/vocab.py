"""
词汇表管理

用于构建和管理中文文本的词汇表。
"""

import jieba
from collections import Counter


class Vocabulary:
    """词汇表类"""

    PAD_TOKEN = '<PAD>'
    UNK_TOKEN = '<UNK>'

    def __init__(self, min_freq=1):
        """
        初始化词汇表

        Args:
            min_freq: 最小词频阈值，低于此频率的词将被过滤
        """
        self.min_freq = min_freq
        self.word2idx = {}
        self.idx2word = {}
        self.word_freq = Counter()

        # 预留特殊标记
        self.PAD_IDX = 0
        self.UNK_IDX = 1
        self.word2idx[self.PAD_TOKEN] = self.PAD_IDX
        self.word2idx[self.UNK_TOKEN] = self.UNK_IDX
        self.idx2word[self.PAD_IDX] = self.PAD_TOKEN
        self.idx2word[self.UNK_IDX] = self.UNK_TOKEN

    def build_vocab_from_texts(self, texts):
        """
        从文本列表构建词汇表

        Args:
            texts: 文本列表 [str, ...]
        """
        # 分词并统计词频
        for text in texts:
            words = jieba.lcut(text)
            self.word_freq.update(words)

        # 构建词汇表（过滤低频词）
        idx = 2  # 从 2 开始，0 和 1 已被特殊标记占用
        for word, freq in self.word_freq.items():
            if freq >= self.min_freq:
                if word not in self.word2idx:
                    self.word2idx[word] = idx
                    self.idx2word[idx] = word
                    idx += 1

    def encode(self, text):
        """
        将文本编码为索引序列

        Args:
            text: 输入文本

        Returns:
            list: 索引列表 [int, ...]
        """
        words = jieba.lcut(text)
        return [self.word2idx.get(word, self.UNK_IDX) for word in words]

    def decode(self, indices):
        """
        将索引序列解码为文本

        Args:
            indices: 索引列表 [int, ...]

        Returns:
            str: 解码后的文本
        """
        words = [self.idx2word.get(idx, self.UNK_TOKEN) for idx in indices]
        return ''.join(words)

    def __len__(self):
        return len(self.word2idx)

    def save(self, filepath):
        """保存词汇表到文件"""
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'word2idx': self.word2idx,
                'idx2word': self.idx2word,
                'word_freq': dict(self.word_freq),
            }, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, filepath):
        """从文件加载词汇表"""
        import json
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        vocab = cls()
        vocab.word2idx = {int(k): v for k, v in data['word2idx'].items()} if isinstance(next(iter(data['word2idx'])), int) else data['word2idx']
        vocab.idx2word = {int(k): v for k, v in data['idx2word'].items()} if isinstance(next(iter(data['idx2word'])), int) else data['idx2word']
        # 修正键类型
        if not isinstance(next(iter(vocab.word2idx)), str):
            vocab.word2idx = {str(k): v for k, v in vocab.word2idx.items()}
            vocab.idx2word = {str(k): v for k, v in vocab.idx2word.items()}
        vocab.word_freq = Counter(data['word_freq'])
        return vocab
