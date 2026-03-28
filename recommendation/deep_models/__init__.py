"""
深度学习推荐模型

本模块包含基于深度学习的推荐系统实现：
- TextCNN: 商品文本特征提取
- Transformer: 用户行为序列建模
- Hybrid: 混合推荐模型

注意：需要安装 PyTorch 才能使用本模块。
pip install torch==1.13.1 torchtext==0.14.1 jieba tqdm
"""

# 尝试导入深度学习模型
try:
    import torch

    from .textcnn import TextCNN
    from .transformer import UserSequenceTransformer
    from .hybrid import HybridRecommendationModel

    __all__ = [
        'TextCNN',
        'UserSequenceTransformer',
        'HybridRecommendationModel',
    ]

    TORCH_AVAILABLE = True

except ImportError:
    # PyTorch 未安装时提供占位符
    __all__ = []

    TORCH_AVAILABLE = False

    class TextCNN:
        """PyTorch 未安装时的占位符"""
        pass

    class UserSequenceTransformer:
        """PyTorch 未安装时的占位符"""
        pass

    class HybridRecommendationModel:
        """PyTorch 未安装时的占位符"""
        pass

