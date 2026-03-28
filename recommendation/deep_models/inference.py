"""
深度模型推理服务

提供在线推理服务，集成到 Django 推荐系统中。
"""

import os
import torch
from pathlib import Path

from .hybrid import HybridRecommendationModel
from .vocab import Vocabulary
from ..services import get_user_sequence, get_product_features


class DeepModelManager:
    """
    深度学习模型管理器（单例模式）

    负责加载模型、提供推理接口
    """

    _instance = None
    _model = None
    _vocab = None
    _device = None
    _model_loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DeepModelManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化模型管理器"""
        if not self._model_loaded:
            self._device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self._load_model()

    def _load_model(self):
        """加载模型和词汇表"""
        try:
            # 模型文件路径
            model_dir = Path(__file__).parent.parent / 'models'
            model_path = model_dir / 'hybrid_model.pth'
            vocab_path = model_dir / 'vocab.json'

            # 检查模型文件是否存在
            if not model_path.exists() or not vocab_path.exists():
                print(f"深度模型文件不存在，跳过加载: {model_dir}")
                return

            # 加载词汇表
            self._vocab = Vocabulary.load(vocab_path)

            # 加载模型
            self._model = HybridRecommendationModel.load_model(
                model_path,
                device=self._device
            )
            self._model.eval()

            self._model_loaded = True
            print(f"深度模型加载成功，设备: {self._device}")

        except Exception as e:
            print(f"深度模型加载失败: {e}")
            self._model_loaded = False

    def predict(self, user_id, candidate_product_ids, limit=8):
        """
        为用户生成推荐列表

        Args:
            user_id: 用户 ID
            candidate_product_ids: 候选商品 ID 列表
            limit: 返回推荐数量

        Returns:
            list: 推荐商品 ID 列表，按分数降序排列
        """
        if not self._model_loaded or self._model is None:
            # 模型未加载，返回空列表
            return []

        try:
            # 1. 获取用户行为序列
            sequence = get_user_sequence(user_id, max_length=50)

            if len(sequence) < 3:
                # 行为序列太短，无法有效预测
                return []

            # 2. 获取商品特征
            product_features = get_product_features(candidate_product_ids)

            if len(product_features) == 0:
                return []

            # 3. 编码数据
            user_sequence_encoded = self._encode_user_sequence(sequence)
            candidate_texts_encoded = self._encode_candidate_texts(
                [pid for pid in candidate_product_ids if pid in product_features]
            )

            if len(candidate_texts_encoded) == 0:
                return []

            # 4. 推理
            with torch.no_grad():
                scores = self._model(
                    user_sequence=user_sequence_encoded,
                    candidate_texts=candidate_texts_encoded
                )

            # 5. 排序并返回 Top-K
            scores = scores.cpu().numpy()[0]  # [num_candidates]
            candidate_ids = [pid for pid in candidate_product_ids if pid in product_features]

            # 按分数降序排序
            ranked = sorted(zip(candidate_ids, scores), key=lambda x: x[1], reverse=True)
            top_k = [pid for pid, _ in ranked[:limit]]

            return top_k

        except Exception as e:
            print(f"深度模型推理失败: {e}")
            return []

    def _encode_user_sequence(self, sequence):
        """编码用户行为序列"""
        max_seq_len = self._model.max_seq_len

        product_ids = []
        behavior_types = []
        scores = []

        behavior_map = {'view': 0, 'cart': 1, 'order': 2, 'review': 3}

        for item in sequence[:max_seq_len]:
            product_ids.append(item['product_id'])
            behavior_types.append(behavior_map.get(item['behavior_type'], 0))
            scores.append(item['score'])

        # 填充
        seq_len = len(product_ids)
        if seq_len < max_seq_len:
            product_ids += [0] * (max_seq_len - seq_len)
            behavior_types += [0] * (max_seq_len - seq_len)
            scores += [0.0] * (max_seq_len - seq_len)

        return {
            'product_ids': torch.tensor([product_ids], dtype=torch.long).to(self._device),
            'behavior_types': torch.tensor([behavior_types], dtype=torch.long).to(self._device),
            'scores': torch.tensor([scores], dtype=torch.float).to(self._device),
        }

    def _encode_candidate_texts(self, product_ids):
        """编码候选商品文本"""
        max_text_len = self._model.max_text_len
        product_features = get_product_features(product_ids)

        encoded = []
        for pid in product_ids:
            feat = product_features.get(pid)
            if feat:
                indices = self._vocab.encode(feat['text'])
            else:
                indices = []
            # 截断或填充到 max_text_len
            indices = indices[:max_text_len]
            indices += [self._vocab.PAD_IDX] * (max_text_len - len(indices))
            encoded.append(indices)

        input_ids = torch.tensor([encoded], dtype=torch.long).to(self._device)
        return {'input_ids': input_ids}

    def is_model_loaded(self):
        """检查模型是否已加载"""
        return self._model_loaded


# 全局单例
_deep_model_manager = None


def get_deep_model_manager():
    """获取深度模型管理器单例"""
    global _deep_model_manager
    if _deep_model_manager is None:
        _deep_model_manager = DeepModelManager()
    return _deep_model_manager
