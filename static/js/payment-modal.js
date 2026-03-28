/**
 * 付款成功模态框
 *
 * 功能：
 * 1. 提交订单后弹出模态框
 * 2. 显示成功图标和动画
 * 3. 2.5秒后自动跳转到订单详情页
 */

(function() {
    'use strict';

    /**
     * 显示付款成功模态框
     * @param {string} orderId - 订单ID
     */
    function showPaymentSuccess(orderId) {
        // 创建模态框覆盖层
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.innerHTML = `
            <div class="payment-success-modal">
                <div class="success-icon">
                    <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M18 26L6 14M6 14L14 6M6 14H42" stroke="white" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" transform="translate(10, 14) rotate(45 24 24)"/>
                    </svg>
                </div>
                <h2 class="success-title">付款成功！</h2>
                <p class="success-subtitle">订单正在处理中，即将跳转...</p>
            </div>
        `;

        document.body.appendChild(overlay);

        // 强制重绘
        overlay.offsetHeight;

        // 激活模态框（触发淡入动画）
        overlay.classList.add('active');

        // 2.5秒后跳转到订单详情页
        setTimeout(() => {
            window.location.href = `/order/orders/${orderId}/`;
        }, 2500);
    }

    /**
     * 监听表单提交
     * 在订单创建成功后显示模态框
     */
    function listenToOrderSubmit() {
        const checkoutForm = document.querySelector('form[action*="/order/checkout/"]');
        if (!checkoutForm) return;

        checkoutForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = new FormData(checkoutForm);

            try {
                const response = await fetch(checkoutForm.action, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin'
                });

                if (response.ok) {
                    const data = await response.json();
                    if (data.success && data.order_id) {
                        showPaymentSuccess(data.order_id);
                    } else if (data.redirect) {
                        // 如果后端返回重定向URL，直接跳转
                        window.location.href = data.redirect;
                    } else {
                        // 出错时显示错误信息
                        alert(data.message || '订单提交失败，请重试');
                    }
                } else {
                    alert('订单提交失败，请重试');
                }
            } catch (error) {
                console.error('提交订单失败:', error);
                // 降级处理：直接提交表单
                checkoutForm.submit();
            }
        });
    }

    // 页面加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', listenToOrderSubmit);
    } else {
        listenToOrderSubmit();
    }

    // 导出全局函数供其他脚本调用
    window.showPaymentSuccess = showPaymentSuccess;

})();
