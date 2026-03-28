"""
店铺权限装饰器
"""

from functools import wraps
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Store


def store_owner_required():
    """验证用户是否为店铺所有者

    用法：
        @store_owner_required()
        def view_func(request, store):
            # store 参数会自动注入
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 从 URL 参数获取 store_id 或 pk
            store_id = kwargs.get('store_id') or kwargs.get('pk')
            if not store_id:
                messages.error(request, '缺少店铺ID')
                return redirect('store_dashboard')

            store = get_object_or_404(Store, pk=store_id)

            # 检查权限
            if store.owner != request.user:
                messages.error(request, '您没有权限访问此店铺')
                return redirect('/')

            # 移除 URL 参数，注入 store 对象
            kwargs.pop('store_id', None)
            kwargs.pop('pk', None)
            kwargs['store'] = store
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
