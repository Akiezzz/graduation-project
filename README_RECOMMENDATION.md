# 推荐系统模块使用指南

本模块提供完整的个性化推荐功能，包括实时推荐、Redis 缓存、离线评估等。

## 目录

- [快速开始](#快速开始)
- [Redis 配置](#redis-配置)
- [在线推荐](#在线推荐)
- [离线评估](#离线评估)
- [API 接口](#api-接口)
- [扩展新算法](#扩展新算法)

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 Redis

参见下方的 [Redis 配置](#redis-配置) 章节。

### 3. 数据迁移

```bash
python manage.py migrate
```

### 4. 启动服务

```bash
python manage.py runserver
```

---

## Redis 配置

### Windows 本地安装

1. **下载 Redis for Windows**
   - 访问：https://github.com/microsoftarchive/redis/releases
   - 下载 `.msi` 安装包并安装

2. **启动 Redis 服务**
   ```bash
   # 方式1：安装为 Windows 服务
   redis-server --service-install

   # 方式2：直接启动
   redis-server
   ```

3. **验证 Redis 运行**
   ```bash
   redis-cli ping
   # 输出：PONG
   ```

### Docker 安装（推荐）

```bash
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

### 配置环境变量（可选）

在项目根目录创建 `.env` 文件：

```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### Redis 降级机制

如果 Redis 不可用，系统会自动回退到数据库查询，功能不受影响，仅性能略降。

---

## 在线推荐

### 工作原理

1. **行为埋点**
   - 用户浏览商品：`view` (score=1)
   - 加入购物车：`cart` (score=2)
   - 提交订单：`order` (score=4)
   - 发表评价：`review` (score=3)

2. **推荐算法**
   - **ItemCF（个性化）**：基于物品协同过滤，使用用户近期行为
   - **Popular（兜底）**：按销量推荐热门商品
   - **Mixed（混合）**：ItemCF + Popular 补充

3. **缓存策略**
   - Redis 实时缓存用户近期行为（最近 100 条）
   - 推荐结果缓存 10 分钟

### 前端集成示例

在商品详情页显示推荐：

```javascript
fetch('/api/recommendations/?limit=6&scene=detail', {
  credentials: 'same-origin'
})
  .then(res => res.json())
  .then(data => {
    data.items.forEach(item => {
      console.log(`${item.name} - ${item.reason}`);
    });
  });
```

---

## 离线评估

### 1. 导出数据

将数据库中的交互记录导出为 CSV 格式：

```bash
python manage.py export_recommendation_data \
  --output-dir recommendation/offline/data \
  --train-test-split 2026-03-27
```

**参数说明：**
- `--output-dir`：导出目录（默认：`recommendation/offline/data`）
- `--train-test-split`：训练集/测试集切分时间点（默认：当前时间）
- `--batch-size`：分批导出大小（默认：10000）

**输出文件：**
- `interactions.csv`：用户-商品交互记录
- `products.csv`：商品元数据
- `users.csv`：用户列表
- `metadata.json`：数据集元信息

### 2. 运行评估

使用导出的数据评估不同算法的性能：

```bash
python manage.py evaluate_recommendations \
  --data-dir recommendation/offline/data \
  --k 10 \
  --algorithms popular,itemcf \
  --output-dir recommendation/offline/results
```

**参数说明：**
- `--data-dir`：数据目录
- `--k`：Top-K 中的 K 值（默认：10）
- `--algorithms`：要评估的算法，逗号分隔（默认：`popular,itemcf`）
- `--output-dir`：结果输出目录

**输出文件：**
- `results/evaluation_results.json`：评估结果（JSON 格式）

### 3. 解读评估结果

评估指标说明：

- **Precision@K**：精确率，推荐列表中相关商品的比例
  - 公式：`|Recommended ∩ Relevant| / K`
  - 取值范围：[0, 1]，越大越好

- **Recall@K**：召回率，相关商品被推荐的比例
  - 公式：`|Recommended ∩ Relevant| / |Relevant|`
  - 取值范围：[0, 1]，越大越好

- **F1@K**：F1 分数，精确率和召回率的调和平均
  - 公式：`2 * P * R / (P + R)`
  - 取值范围：[0, 1]，越大越好

**相关商品定义**：测试集中用户实际交互的商品（行为权重 >= 2，即 cart/order/review）

示例输出：

```
算法对比：
按 F1@10 排名：
  1. ItemCF       F1=0.1234, P=0.1456, R=0.1067
  2. Popular      F1=0.0567, P=0.0789, R=0.0456

最佳算法（F1）：ItemCF
```

---

## API 接口

### 获取推荐列表

**请求：**
```
GET /api/recommendations/?limit=8&scene=detail
```

**响应：**
```json
{
  "source": "itemcf",
  "items": [
    {
      "id": 1,
      "name": "示例商品",
      "price": "99.99",
      "image": "/media/products/image.jpg",
      "reason": "基于您的兴趣推荐"
    }
  ]
}
```

**参数：**
- `limit`：返回商品数量（1-20，默认：8）
- `scene`：场景标识（可选，用于统计）

**source 取值：**
- `itemcf`：完全个性化推荐
- `popular`：热门商品推荐
- `mixed`：混合推荐

---

## 扩展新算法

### 1. 实现基线算法

在 `recommendation/offline/baselines.py` 中添加新算法：

```python
class MyCustomBaseline(BaseBaseline):
    def __init__(self, train_data, products_data):
        super().__init__(train_data, products_data)
        # 初始化算法

    def recommend(self, user_id, k=10, exclude_product_ids=None):
        # 实现推荐逻辑
        return recommendations[:k]
```

### 2. 注册到评估命令

修改 `recommendation/management/commands/evaluate_recommendations.py`：

```python
if 'mycustom' in algorithms:
    models['MyCustom'] = MyCustomBaseline(train_data, products_data)
```

### 3. 运行评估

```bash
python manage.py evaluate_recommendations --algorithms mycustom
```

---

## 常见问题

### Q: Redis 连接失败怎么办？

A: 系统会自动降级到数据库查询，功能不受影响。检查 Redis 是否启动：

```bash
redis-cli ping
```

### Q: 如何清除所有推荐缓存？

A: 重启 Redis 或运行：

```python
from recommendation.cache import clear_recommendation_cache
clear_recommendation_cache(user_id=None)  # 清除全部
```

### Q: 离线评估数据量太大怎么办？

A: 使用 `--batch-size` 参数分批导出：

```bash
python manage.py export_recommendation_data --batch-size 5000
```

### Q: 如何调整推荐缓存时间？

A: 修改 `settings.py` 中的 `RECOMMENDATION_CACHE`：

```python
RECOMMENDATION_CACHE = {
    'RECOMMENDATION_CACHE_TIMEOUT': 1200,  # 20分钟
}
```

---

## 深度学习推荐（P3 阶段）

### 架构概览

P3 阶段引入了基于深度学习的推荐模型，结合协同过滤和深度学习方法：

- **TextCNN**：从商品文本（name + keywords + description）提取特征
- **Transformer**：对用户行为序列建模，捕获兴趣演化
- **Hybrid Model**：融合两种特征进行个性化推荐

### 模型组件

#### 1. 数据接口

**get_user_sequence**：提取用户行为序列
```python
from recommendation.services import get_user_sequence

sequence = get_user_sequence(user_id=1, max_length=50)
# 返回：[{'product_id': int, 'behavior_type': str, 'score': float, 'timestamp': datetime}, ...]
```

**get_product_features**：批量获取商品文本特征
```python
from recommendation.services import get_product_features

features = get_product_features(product_ids=[1, 2, 3])
# 返回：{product_id: {'name': str, 'keywords': str, 'description': str, 'text': str}, ...}
```

#### 2. 模型架构

**TextCNN** (`recommendation/deep_models/textcnn.py`)
- 输入：商品文本序列 [batch_size, seq_len]
- 输出：商品特征向量 [batch_size, 256]
- 特点：多尺度卷积核捕捉不同粒度的文本特征

**Transformer** (`recommendation/deep_models/transformer.py`)
- 输入：用户行为序列 [product_id, behavior_type, score]
- 输出：用户兴趣表示 [batch_size, 256]
- 特点：自注意力机制建模用户兴趣演化

**Hybrid Model** (`recommendation/deep_models/hybrid.py`)
- 融合用户兴趣和商品特征
- MLP 输出推荐分数
- 支持 batch 推理

#### 3. 模型文件结构

```
recommendation/deep_models/
├── __init__.py           # 模块导出
├── vocab.py              # 词汇表管理
├── textcnn.py            # TextCNN 模型
├── transformer.py        # Transformer 模型
├── hybrid.py             # 混合推荐模型
├── dataset.py            # PyTorch Dataset
├── inference.py          # 推理服务
└── README.md             # 模型文档
```

### 模型训练（待实现）

#### 准备训练数据

```bash
# 1. 导出商品文本数据
python manage.py export_product_texts --output-dir recommendation/offline/data

# 2. 使用 P2 的导出命令生成交互数据
python manage.py export_recommendation_data --train-test-split 2026-03-27
```

#### 训练模型

训练命令和参数待实现，基本流程：

1. 构建词汇表
2. 加载训练数据
3. 初始化模型
4. 训练循环
5. 验证和保存最佳模型

### 在线推理（基础框架）

深度模型推理服务已实现基础框架（`recommendation/deep_models/inference.py`）：

```python
from recommendation.deep_models.inference import get_deep_model_manager

# 获取模型管理器
manager = get_deep_model_manager()

# 检查模型是否加载
if manager.is_model_loaded():
    # 生成推荐
    recommendations = manager.predict(
        user_id=1,
        candidate_product_ids=[1, 2, 3, 4, 5],
        limit=8
    )
```

**注意**：当前实现为框架代码，完整的训练和推理流程需要进一步开发：

- 实现 `recommendation/management/commands/train_deep_model.py` 训练命令
- 实现 `recommendation/deep_models/trainer.py` 训练器
- 实现商品文本缓存机制
- 优化推理性能

### 依赖安装

```bash
pip install torch==2.0.1 torchtext==0.15.2 jieba==0.42.1 tqdm==4.66.1
```

或使用 requirements.txt：

```bash
pip install -r requirements.txt
```

### 配置选项

在 `settings.py` 中添加：

```python
# 深度学习模型配置
DEEP_MODEL_ENABLED = True  # 是否启用深度模型
DEEP_MODEL_PATH = 'recommendation/models/hybrid_model.pth'
VOCAB_PATH = 'recommendation/models/vocab.json'
```

### 当前状态

✅ 已完成：
- 数据接口实现（get_user_sequence, get_product_features）
- TextCNN、Transformer、Hybrid 模型架构
- PyTorch Dataset 类
- 推理服务基础框架

⚠️ 待完成：
- 模型训练流程
- 商品文本预计算和缓存
- 性能优化和批处理
- 完整的测试用例

### 论文写作支持

本模块提供了完整的深度学习推荐系统实现，可用于毕业论文的算法章节：

- **第 3 章**：系统架构设计
- **第 4 章**：TextCNN 文本特征提取
- **第 5 章**：Transformer 用户序列建模
- **第 6 章**：实验与评估

关键算法伪代码和数学公式已在代码注释中提供。

---

## 技术支持

如有问题，请查看：
- Django 官方文档：https://docs.djangoproject.com/
- Redis 文档：https://redis.io/docs/
- django-redis 文档：https://github.com/jazzband/django-redis
- PyTorch 文档：https://pytorch.org/docs/
