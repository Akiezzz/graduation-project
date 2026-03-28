"""
模型训练器

提供深度推荐模型的训练、验证和评估功能。
"""

import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from tqdm import tqdm
import json


class ModelTrainer:
    """
    深度推荐模型训练器

    负责模型的训练循环、验证、保存和加载
    """

    def __init__(
        self,
        model,
        train_dataset,
        val_dataset=None,
        batch_size=128,
        learning_rate=1e-3,
        num_epochs=50,
        device='cpu',
        model_save_dir='recommendation/models',
        early_stopping_patience=5
    ):
        """
        初始化训练器

        Args:
            model: 待训练的模型
            train_dataset: 训练数据集
            val_dataset: 验证数据集（可选）
            batch_size: 批大小
            learning_rate: 学习率
            num_epochs: 训练轮数
            device: 设备（'cpu' 或 'cuda'）
            model_save_dir: 模型保存目录
            early_stopping_patience: 早停耐心值
        """
        self.model = model.to(device)
        self.train_dataset = train_dataset
        self.val_dataset = val_dataset
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.num_epochs = num_epochs
        self.device = device
        self.model_save_dir = model_save_dir
        self.early_stopping_patience = early_stopping_patience

        # 创建模型保存目录
        os.makedirs(model_save_dir, exist_ok=True)

        # 初始化训练组件
        self.criterion = nn.BCELoss()
        self.optimizer = optim.AdamW(model.parameters(), lr=learning_rate)
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='min', factor=0.5, patience=2, verbose=True
        )

        # 训练历史
        self.history = {
            'train_loss': [],
            'val_loss': [],
            'val_auc': [],
        }

        # 最佳模型跟踪
        self.best_val_loss = float('inf')
        self.best_epoch = 0
        self.patience_counter = 0

    def train_epoch(self, dataloader):
        """训练一个 epoch"""
        self.model.train()
        total_loss = 0.0
        num_batches = 0

        progress_bar = tqdm(dataloader, desc='Training')
        for batch in progress_bar:
            self.optimizer.zero_grad()

            # 前向传播
            user_sequence = batch['user_sequence']
            candidate_texts = batch['candidate_texts']
            labels = batch['label']

            # 将数据移到设备
            for key in user_sequence:
                user_sequence[key] = user_sequence[key].to(self.device)
            for key in candidate_texts:
                candidate_texts[key] = candidate_texts[key].to(self.device)
            labels = labels.to(self.device)

            # 模型预测
            predictions = self.model(user_sequence, candidate_texts)

            # 计算损失
            loss = self.criterion(predictions, labels)

            # 反向传播
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()
            num_batches += 1

            progress_bar.set_postfix({'loss': f'{loss.item():.4f}'})

        avg_loss = total_loss / num_batches
        return avg_loss

    def validate(self, dataloader):
        """验证模型"""
        self.model.eval()
        total_loss = 0.0
        num_batches = 0

        all_predictions = []
        all_labels = []

        with torch.no_grad():
            for batch in tqdm(dataloader, desc='Validating'):
                user_sequence = batch['user_sequence']
                candidate_texts = batch['candidate_texts']
                labels = batch['label']

                # 将数据移到设备
                for key in user_sequence:
                    user_sequence[key] = user_sequence[key].to(self.device)
                for key in candidate_texts:
                    candidate_texts[key] = candidate_texts[key].to(self.device)
                labels = labels.to(self.device)

                # 模型预测
                predictions = self.model(user_sequence, candidate_texts)

                # 计算损失
                loss = self.criterion(predictions, labels)
                total_loss += loss.item()
                num_batches += 1

                # 收集预测和标签
                all_predictions.extend(predictions.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())

        avg_loss = total_loss / num_batches

        # 计算 AUC
        try:
            from sklearn.metrics import roc_auc_score
            auc = roc_auc_score(all_labels, all_predictions)
        except:
            auc = 0.0

        return avg_loss, auc

    def train(self):
        """完整训练流程"""
        # 创建数据加载器
        train_loader = DataLoader(
            self.train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=0
        )

        val_loader = None
        if self.val_dataset is not None:
            val_loader = DataLoader(
                self.val_dataset,
                batch_size=self.batch_size,
                shuffle=False,
                num_workers=0
            )

        print(f'开始训练，共 {self.num_epochs} 个 epoch')
        print(f'训练集样本数：{len(self.train_dataset)}')
        if self.val_dataset:
            print(f'验证集样本数：{len(self.val_dataset)}')
        print(f'设备：{self.device}')

        for epoch in range(self.num_epochs):
            print(f'\n=== Epoch {epoch + 1}/{self.num_epochs} ===')

            # 训练
            train_loss = self.train_epoch(train_loader)
            self.history['train_loss'].append(train_loss)

            print(f'Train Loss: {train_loss:.4f}')

            # 验证
            if val_loader is not None:
                val_loss, val_auc = self.validate(val_loader)
                self.history['val_loss'].append(val_loss)
                self.history['val_auc'].append(val_auc)

                print(f'Val Loss: {val_loss:.4f}, AUC: {val_auc:.4f}')

                # 学习率调度
                self.scheduler.step(val_loss)

                # 保存最佳模型
                if val_loss < self.best_val_loss:
                    self.best_val_loss = val_loss
                    self.best_epoch = epoch
                    self.patience_counter = 0

                    # 保存模型
                    model_path = os.path.join(self.model_save_dir, 'hybrid_model.pth')
                    self.model.save_model(model_path)
                    print(f'[OK] 保存最佳模型（epoch {epoch + 1}）')
                else:
                    self.patience_counter += 1

                # 早停
                if self.patience_counter >= self.early_stopping_patience:
                    print(f'\n早停触发，最佳 epoch: {self.best_epoch + 1}')
                    break
            else:
                # 无验证集时保存最后一个 epoch
                if epoch == self.num_epochs - 1:
                    model_path = os.path.join(self.model_save_dir, 'hybrid_model.pth')
                    self.model.save_model(model_path)

        # 保存训练历史
        history_path = os.path.join(self.model_save_dir, 'training_history.json')
        with open(history_path, 'w') as f:
            json.dump(self.history, f, indent=2)

        print('\n训练完成！')
        print(f'最佳验证损失：{self.best_val_loss:.4f}（epoch {self.best_epoch + 1}）')
