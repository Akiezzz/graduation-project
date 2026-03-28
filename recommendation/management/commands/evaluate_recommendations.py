"""
推荐系统离线评估命令

使用导出的数据评估不同推荐算法的性能。
"""

import json
import os
from pathlib import Path
from django.core.management.base import BaseCommand

from recommendation.offline.baselines import (
    load_train_data,
    load_test_data,
    PopularBaseline,
    ItemCFBaseline,
)
from recommendation.offline.metrics import (
    evaluate_model,
    compare_algorithms,
)


class Command(BaseCommand):
    help = '离线评估推荐算法（Popular / ItemCF），输出 Precision@K / Recall@K / F1@K'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data-dir',
            type=str,
            default='recommendation/offline/data',
            help='数据目录路径（默认：recommendation/offline/data）',
        )
        parser.add_argument(
            '--k',
            type=int,
            default=10,
            help='Top-K 中的 K 值（默认：10）',
        )
        parser.add_argument(
            '--algorithms',
            type=str,
            default='popular,itemcf',
            help='要评估的算法列表，逗号分隔（默认：popular,itemcf）',
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='recommendation/offline/results',
            help='结果输出目录（默认：recommendation/offline/results）',
        )

    def handle(self, *args, **options):
        data_dir = options['data_dir']
        k = options['k']
        algorithms_str = options['algorithms']
        output_dir = options['output_dir']

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        self.stdout.write(f'开始离线评估，K={k}')
        self.stdout.write(f'数据目录：{data_dir}')

        # 加载数据
        self.stdout.write('\n加载数据...')
        train_data, products_data = load_train_data(data_dir)
        test_data = load_test_data(data_dir)

        self.stdout.write(f'  训练集交互记录：{len(train_data)}')
        self.stdout.write(f'  测试集用户数：{len(test_data)}')
        self.stdout.write(f'  商品数量：{len(products_data)}')

        # 解析要评估的算法
        algorithms = [algo.strip() for algo in algorithms_str.split(',')]
        self.stdout.write(f'\n评估算法：{", ".join(algorithms)}')

        # 初始化算法
        models = {}
        if 'popular' in algorithms:
            self.stdout.write('\n初始化 PopularBaseline...')
            models['Popular'] = PopularBaseline(train_data, products_data)
        if 'itemcf' in algorithms:
            self.stdout.write('初始化 ItemCFBaseline...')
            models['ItemCF'] = ItemCFBaseline(train_data, products_data)

        if not models:
            self.stdout.write(self.style.ERROR('没有有效的算法可评估'))
            return

        # 评估各算法
        results = {}
        for algo_name, model in models.items():
            self.stdout.write(f'\n评估 {algo_name}...')
            metrics = evaluate_model(model, test_data, k=k)
            metrics['k'] = k
            results[algo_name] = metrics

            # 输出结果
            self.stdout.write(f'  Precision@{k}: {metrics["precision"]:.4f}')
            self.stdout.write(f'  Recall@{k}:    {metrics["recall"]:.4f}')
            self.stdout.write(f'  F1@{k}:        {metrics["f1"]:.4f}')
            self.stdout.write(f'  用户数量：      {metrics["num_users"]}')

        # 对比算法
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('算法对比：')
        comparison = compare_algorithms(results, k=k)

        self.stdout.write(f'\n按 F1@{k} 排名：')
        for i, rank in enumerate(comparison['rankings'], 1):
            self.stdout.write(
                f"  {i}. {rank['algorithm']:12s} "
                f"F1={rank['f1']:.4f}, "
                f"P={rank['precision']:.4f}, "
                f"R={rank['recall']:.4f}"
            )

        self.stdout.write(f"\n最佳算法（F1）：{comparison['best_by_f1']['algorithm']}")

        # 保存结果到 JSON
        results_file = os.path.join(output_dir, 'evaluation_results.json')
        save_results(results_file, results, comparison, data_dir, k)
        self.stdout.write(self.style.SUCCESS(f'\n结果已保存到：{results_file}'))

        self.stdout.write(self.style.SUCCESS('\n评估完成！'))


def save_results(filepath, results, comparison, data_dir, k):
    """保存评估结果到 JSON 文件"""
    output = {
        'metadata': {
            'data_dir': data_dir,
            'k': k,
            'num_algorithms': len(results),
        },
        'algorithms': results,
        'comparison': {
            'rankings': comparison['rankings'],
            'best_by_precision': comparison['best_by_precision'],
            'best_by_recall': comparison['best_by_recall'],
            'best_by_f1': comparison['best_by_f1'],
        },
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
