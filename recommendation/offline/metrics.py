"""
推荐系统评估指标

实现常见的推荐系统评估指标：
- Precision@K: 精确率，推荐列表中相关商品的比例
- Recall@K: 召回率，相关商品被推荐的比例
- F1@K: F1 分数，精确率和召回率的调和平均
"""

from collections import defaultdict


def precision_at_k(recommended, relevant, k):
    """
    计算 Precision@K

    Precision@K = |Recommended ∩ Relevant| / K

    Args:
        recommended: 推荐列表 [item_id, ...]
        relevant: 相关商品集合 {item_id, ...}
        k: Top-K 中的 K

    Returns:
        float: Precision@K 值 [0, 1]
    """
    if k == 0:
        return 0.0

    top_k = set(recommended[:k])
    relevant_set = set(relevant)

    hits = len(top_k & relevant_set)
    return hits / k


def recall_at_k(recommended, relevant, k):
    """
    计算 Recall@K

    Recall@K = |Recommended ∩ Relevant| / |Relevant|

    Args:
        recommended: 推荐列表 [item_id, ...]
        relevant: 相关商品集合 {item_id, ...}
        k: Top-K 中的 K

    Returns:
        float: Recall@K 值 [0, 1]
    """
    if not relevant:
        return 0.0

    top_k = set(recommended[:k])
    relevant_set = set(relevant)

    hits = len(top_k & relevant_set)
    return hits / len(relevant_set)


def f1_at_k(recommended, relevant, k):
    """
    计算 F1@K

    F1@K = 2 * Precision@K * Recall@K / (Precision@K + Recall@K)

    Args:
        recommended: 推荐列表 [item_id, ...]
        relevant: 相关商品集合 {item_id, ...}
        k: Top-K 中的 K

    Returns:
        float: F1@K 值 [0, 1]
    """
    precision = precision_at_k(recommended, relevant, k)
    recall = recall_at_k(recommended, relevant, k)

    if precision + recall == 0:
        return 0.0

    return 2 * precision * recall / (precision + recall)


def evaluate_model(model, test_data, k=10):
    """
    评估推荐模型在测试集上的表现

    Args:
        model: 推荐模型实例（需实现 recommend 方法）
        test_data: 测试数据，格式为 {user_id: set([relevant_product_id, ...])}
        k: Top-K 中的 K

    Returns:
        dict: {
            'precision': float,
            'recall': float,
            'f1': float,
            'num_users': int,
            'num_users_with_recommendations': int,
            'per_user_metrics': {user_id: {'precision', 'recall', 'f1'}, ...}
        }
    """
    total_precision = 0.0
    total_recall = 0.0
    total_f1 = 0.0
    num_users = 0
    num_users_with_recommendations = 0

    per_user_metrics = {}

    for user_id, relevant_items in test_data.items():
        if not relevant_items:
            continue

        # 获取用户历史商品（用于排除）
        user_history = model.user_items.get(user_id, {}).keys()

        # 生成推荐
        recommended = model.recommend(user_id, k=k, exclude_product_ids=list(user_history))

        if not recommended:
            continue

        # 计算指标
        precision = precision_at_k(recommended, relevant_items, k)
        recall = recall_at_k(recommended, relevant_items, k)
        f1 = f1_at_k(recommended, relevant_items, k)

        total_precision += precision
        total_recall += recall
        total_f1 += f1
        num_users += 1
        num_users_with_recommendations += 1

        per_user_metrics[user_id] = {
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'num_recommended': len(recommended),
            'num_relevant': len(relevant_items),
        }

    if num_users == 0:
        return {
            'precision': 0.0,
            'recall': 0.0,
            'f1': 0.0,
            'num_users': 0,
            'num_users_with_recommendations': 0,
            'per_user_metrics': {},
        }

    avg_precision = total_precision / num_users
    avg_recall = total_recall / num_users
    avg_f1 = total_f1 / num_users

    return {
        'precision': avg_precision,
        'recall': avg_recall,
        'f1': avg_f1,
        'num_users': num_users,
        'num_users_with_recommendations': num_users_with_recommendations,
        'per_user_metrics': per_user_metrics,
    }


def compare_algorithms(results_dict, k=10):
    """
    对比多个算法的评估结果

    Args:
        results_dict: {algorithm_name: {precision, recall, f1, ...}, ...}
        k: Top-K 中的 K

    Returns:
        dict: 对比结果，包含最佳算法和排序
    """
    comparison = []

    for algo_name, metrics in results_dict.items():
        comparison.append({
            'algorithm': algo_name,
            'precision': metrics['precision'],
            'recall': metrics['recall'],
            'f1': metrics['f1'],
            'num_users': metrics['num_users'],
        })

    # 按 F1 分数降序排序
    comparison.sort(key=lambda x: x['f1'], reverse=True)

    return {
        'k': k,
        'rankings': comparison,
        'best_by_precision': max(comparison, key=lambda x: x['precision']),
        'best_by_recall': max(comparison, key=lambda x: x['recall']),
        'best_by_f1': max(comparison, key=lambda x: x['f1']),
    }


def format_evaluation_results(results, algo_name):
    """
    格式化评估结果输出

    Args:
        results: evaluate_model 返回的结果字典
        algo_name: 算法名称

    Returns:
        str: 格式化的结果字符串
    """
    lines = [
        f"【{algo_name}】评估结果 (@{results.get('k', 'N/A')})",
        f"  Precision@K: {results['precision']:.4f}",
        f"  Recall@K:    {results['recall']:.4f}",
        f"  F1@K:        {results['f1']:.4f}",
        f"  用户数量:    {results['num_users']}",
    ]
    return '\n'.join(lines)
