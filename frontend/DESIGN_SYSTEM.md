# 小红书内容生成工作流 - 设计系统

## 产品类型
**专业工具类 SaaS Dashboard** - 工作流可视化平台

## 设计风格
**主风格**: Glassmorphism + Dark Mode (OLED)  
**辅助风格**: Minimalism, Dimensional Layering

### 为什么选择这个风格？
- **Glassmorphism**: 现代感强，适合专业工具，毛玻璃效果提供层次感
- **Dark Mode**: 减少眼疲劳，适合长时间使用，节能（OLED）
- **Minimalism**: 保持界面清晰，不干扰工作流程
- **Dimensional Layering**: 通过深度和阴影展示节点层级关系

---

## 配色方案

### 主色调（Dark Mode）
```css
--bg-primary: #0F172A      /* 深色背景 - Slate 900 */
--bg-secondary: #1E293B    /* 次级背景 - Slate 800 */
--bg-tertiary: #334155     /* 三级背景 - Slate 700 */

--text-primary: #F8FAFC    /* 主文本 - Slate 50 */
--text-secondary: #CBD5E1  /* 次级文本 - Slate 300 */
--text-muted: #64748B      /* 弱化文本 - Slate 500 */

--border-primary: #334155  /* 主边框 - Slate 700 */
--border-secondary: #475569 /* 次级边框 - Slate 600 */
```

### 功能色
```css
--primary: #3B82F6        /* 主色 - Blue 500 */
--primary-hover: #2563EB  /* 主色悬停 - Blue 600 */
--primary-light: #60A5FA  /* 主色浅色 - Blue 400 */

--success: #22C55E        /* 成功 - Green 500 */
--warning: #F59E0B        /* 警告 - Amber 500 */
--error: #EF4444          /* 错误 - Red 500 */
--info: #06B6D4           /* 信息 - Cyan 500 */
```

### 节点状态色
```css
--node-pending: #64748B   /* 等待 - Slate 500 */
--node-running: #3B82F6   /* 运行中 - Blue 500 */
--node-completed: #22C55E /* 完成 - Green 500 */
--node-error: #EF4444     /* 错误 - Red 500 */
--node-warning: #F59E0B   /* 警告 - Amber 500 */
```

### 玻璃态效果
```css
--glass-bg: rgba(30, 41, 59, 0.7)     /* 毛玻璃背景 */
--glass-border: rgba(255, 255, 255, 0.1) /* 毛玻璃边框 */
--glass-blur: 12px                     /* 背景模糊度 */
```

---

## 字体系统

### 字体族
```css
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
```

### 字体大小
```css
--text-xs: 0.75rem    /* 12px */
--text-sm: 0.875rem   /* 14px */
--text-base: 1rem     /* 16px */
--text-lg: 1.125rem   /* 18px */
--text-xl: 1.25rem    /* 20px */
--text-2xl: 1.5rem    /* 24px */
--text-3xl: 1.875rem  /* 30px */
--text-4xl: 2.25rem   /* 36px */
```

### 字重
```css
--font-normal: 400
--font-medium: 500
--font-semibold: 600
--font-bold: 700
```

---

## 间距系统

```css
--spacing-1: 0.25rem   /* 4px */
--spacing-2: 0.5rem    /* 8px */
--spacing-3: 0.75rem   /* 12px */
--spacing-4: 1rem      /* 16px */
--spacing-5: 1.25rem   /* 20px */
--spacing-6: 1.5rem    /* 24px */
--spacing-8: 2rem      /* 32px */
--spacing-10: 2.5rem   /* 40px */
--spacing-12: 3rem     /* 48px */
--spacing-16: 4rem     /* 64px */
```

---

## 圆角系统

```css
--radius-sm: 0.375rem  /* 6px */
--radius-md: 0.5rem    /* 8px */
--radius-lg: 0.75rem   /* 12px */
--radius-xl: 1rem      /* 16px */
--radius-2xl: 1.5rem   /* 24px */
--radius-full: 9999px  /* 完全圆形 */
```

---

## 阴影系统

```css
--shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
--shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
--shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
--shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
--shadow-2xl: 0 25px 50px -12px rgba(0, 0, 0, 0.25);

/* 玻璃态阴影 */
--shadow-glass: 0 8px 32px 0 rgba(0, 0, 0, 0.37);

/* 节点卡片阴影 */
--shadow-node: 0 4px 12px rgba(0, 0, 0, 0.15);
--shadow-node-hover: 0 8px 24px rgba(0, 0, 0, 0.25);
```

---

## 动画系统

### 过渡时长
```css
--duration-fast: 150ms
--duration-normal: 200ms
--duration-slow: 300ms
--duration-slower: 500ms
```

### 缓动函数
```css
--ease-in: cubic-bezier(0.4, 0, 1, 1)
--ease-out: cubic-bezier(0, 0, 0.2, 1)
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1)
```

---

## 组件规范

### 按钮
- 高度: 40px (md), 36px (sm), 48px (lg)
- 内边距: 16px 24px (md)
- 圆角: 8px
- 字重: 500 (medium)

### 输入框
- 高度: 40px
- 内边距: 12px 16px
- 圆角: 8px
- 边框: 1px solid

### 卡片
- 内边距: 24px
- 圆角: 12px
- 背景: 玻璃态效果
- 边框: 1px solid glass-border

### 节点卡片
- 最小宽度: 200px
- 内边距: 16px
- 圆角: 12px
- 状态指示器: 左侧 4px 宽色条

---

## 可访问性要求

✅ **对比度**: 文本至少 4.5:1（WCAG AA）  
✅ **焦点状态**: 3px 蓝色外边框  
✅ **触摸目标**: 最小 44x44px  
✅ **键盘导航**: 支持 Tab 键顺序  
✅ **屏幕阅读器**: 使用语义化 HTML 和 ARIA 标签
