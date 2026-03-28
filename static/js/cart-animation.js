(function() {
    'use strict';

    // 获取 CSRF token
    function getCsrfToken() {
        const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
        return cookie ? cookie.trim().split('=')[1] : '';
    }

    // 购物车数量管理
    const cart = {
        count: 0,
        badge: null,
        floatBtn: null,

        init() {
            this.floatBtn = document.querySelector('.cart-float-btn');
            this.badge = document.querySelector('.cart-badge');
            this.fetchCount();
        },

        async fetchCount() {
            try {
                const res = await fetch('/api/cart/count/', { credentials: 'same-origin' });
                const data = await res.json();
                this.count = data.count || 0;
                this.updateBadge();
            } catch(e) {}
        },

        updateBadge() {
            if (!this.badge) return;
            this.badge.textContent = this.count;
            this.badge.style.display = this.count > 0 ? 'flex' : 'none';
        },

        increment() {
            this.count++;
            this.updateBadge();
        },

        bounce() {
            if (!this.floatBtn) return;
            this.floatBtn.classList.remove('bouncing');
            void this.floatBtn.offsetWidth;
            this.floatBtn.classList.add('bouncing');
        }
    };

    // 抛物线动画（requestAnimationFrame + 二次贝塞尔曲线）
    function flyToCart(btn, onDone) {
        const floatBtn = document.querySelector('.cart-float-btn');
        if (!floatBtn) { onDone(); return; }

        const s = btn.getBoundingClientRect();
        const e = floatBtn.getBoundingClientRect();

        // 起点：按钮中心
        const x0 = s.left + s.width / 2;
        const y0 = s.top + s.height / 2;
        // 终点：悬浮按钮中心
        const x1 = e.left + e.width / 2;
        const y1 = e.top + e.height / 2;
        // 控制点：水平中点，垂直向上150px（形成抛物线顶点）
        const cx = (x0 + x1) / 2;
        const cy = Math.min(y0, y1) - 150;

        // 创建飞行元素
        const el = document.createElement('div');
        el.style.cssText = `position:fixed;width:40px;height:40px;border-radius:50%;background:#1677ff;
            display:flex;align-items:center;justify-content:center;z-index:9999;pointer-events:none;
            box-shadow:0 4px 12px rgba(22,119,255,0.4);`;
        el.innerHTML = '<svg viewBox="0 0 24 24" style="width:22px;height:22px;fill:#fff"><path d="M7 18c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm10 0c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zM5.2 4l.94 2H20l-1.68 8.39c-.16.81-.87 1.61-1.72 1.61H8.1c-.86 0-1.56-.8-1.72-1.61L5.2 4z"/></svg>';

        // 尝试用商品图片
        const img = btn.querySelector('img') || btn.closest('.product-card')?.querySelector('img');
        if (img) {
            el.style.background = 'none';
            el.style.boxShadow = 'none';
            el.innerHTML = `<img src="${img.src}" style="width:40px;height:40px;object-fit:cover;border-radius:50%;border:2px solid #1677ff;">`;
        }

        document.body.appendChild(el);

        const duration = 700;
        const start = performance.now();

        function step(now) {
            const t = Math.min((now - start) / duration, 1);
            // 二次贝塞尔曲线
            const mt = 1 - t;
            const x = mt * mt * x0 + 2 * mt * t * cx + t * t * x1;
            const y = mt * mt * y0 + 2 * mt * t * cy + t * t * y1;
            const scale = 1 - t * 0.7; // 逐渐缩小

            el.style.left = (x - 20) + 'px';
            el.style.top = (y - 20) + 'px';
            el.style.transform = `scale(${scale})`;
            el.style.opacity = t > 0.8 ? (1 - t) * 5 : 1;

            if (t < 1) {
                requestAnimationFrame(step);
            } else {
                document.body.removeChild(el);
                onDone();
            }
        }

        requestAnimationFrame(step);
    }

    // 绑定加入购物车按钮
    function bindButtons() {
        document.querySelectorAll('a[href*="/order/cart/add/"]').forEach(btn => {
            btn.addEventListener('click', function(e) {
                if (window.location.pathname.startsWith('/order/cart')) return;
                e.preventDefault();

                flyToCart(btn, () => {
                    cart.increment();
                    cart.bounce();
                });

                // 发 GET 请求（add_to_cart 是 GET 视图）
                fetch(btn.href, {
                    credentials: 'same-origin',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                }).then(r => r.json()).then(data => {
                    if (data.cart_count !== undefined) {
                        cart.count = data.cart_count;
                        cart.updateBadge();
                    }
                }).catch(() => {});
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => { cart.init(); bindButtons(); });
    } else {
        cart.init();
        bindButtons();
    }
})();
