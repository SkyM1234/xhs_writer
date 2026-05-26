# 小红书写作风格向量库使用指南

## 概述

本项目使用 ChromaDB 向量库和 Qwen Embedding 模型来检索最匹配的小红书写作风格，替代了原有的参考笔记内容，提高了内容的原创性和风格的系统性。

## 架构说明

### 1. 风格数据源
- **文件位置**: `backend/data/style/xiaohongshu_20_styles.json`
- **内容**: 20种小红书写作风格，每种风格包含：
  - 风格名称
  - 特点
  - 适合内容
  - 文案结构
  - 示例

### 2. 向量库构建
- **脚本位置**: `backend/scripts/build_style_vectordb.py`
- **向量库位置**: `backend/data/vectordb/styles/`
- **Embedding 模型**: Qwen `text-embedding-v1`

### 3. 风格检索服务
- **服务位置**: `backend/app/services/style_retrieval_service.py`
- **功能**: 根据关键词、人设、痛点、情绪点检索最匹配的写作风格

### 4. 集成到文案生成
- **节点**: `copywriter_node` (backend/app/agents/nodes.py)
- **改进**:
  - ✅ 删除了完整的参考笔记内容（避免抄袭）
  - ✅ 保留了爆款模式分析（话题切入点、情绪共鸣点、标签策略）
  - ✅ 加入了 RAG 检索的写作风格指导

## 使用步骤

### 步骤 1: 安装依赖

```bash
cd backend
pip install chromadb>=0.4.22
```

### 步骤 2: 配置 API Key

在环境变量或配置文件中设置 Qwen API Key：

```bash
# 方式1：设置 QWEN_API_KEY（推荐）
export QWEN_API_KEY="your_qwen_api_key"

# 方式2：如果已有 LLM_API_KEY，会自动降级使用
export LLM_API_KEY="your_qwen_api_key"
```

### 步骤 3: 构建向量库

**首次使用前必须运行此脚本**：

```bash
cd backend
python scripts/build_style_vectordb.py
```

**预期输出**：
```
✅ 加载了 20 种写作风格
✅ 准备了 20 个文档
🔄 正在生成 20 个文本的向量...
✅ 向量生成完成，维度：1536
🔄 初始化 ChromaDB，路径：.../data/vectordb/styles
✅ 创建集合：xiaohongshu_styles
✅ 添加了 20 个文档到向量库
✅ 向量库构建完成！共 20 个文档
🎉 向量库构建成功！
```

### 步骤 4: 启动应用

向量库构建完成后，正常启动应用即可：

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 工作流程

1. **用户输入**: 关键词、人设、痛点等
2. **热点分析**: 分析爆款笔记的话题切入点、情绪共鸣点、标签策略
3. **风格检索**: 根据用户输入，从向量库检索最匹配的写作风格
4. **文案生成**: 结合爆款模式 + 检索风格 + LLM 生成原创内容

## 维护指南

### 更新风格库

1. 编辑 `backend/data/style/xiaohongshu_20_styles.json`
2. 重新运行 `python scripts/build_style_vectordb.py`
3. 重启应用

### 调整检索数量

在 `copywriter_node` 中修改 `top_k` 参数：

```python
retrieved_styles = style_retrieval_service.retrieve_style(
    keywords=keywords,
    persona=persona,
    pain_points=pain_points_list,
    emotion_triggers=emotion_list,
    top_k=2  # 检索前2个最匹配的风格
)
```

## 技术细节

- **Embedding 模型**: Qwen `text-embedding-v1` (1536维)
- **向量数据库**: ChromaDB (持久化存储)
- **检索方式**: 余弦相似度
- **降级策略**: 检索失败时使用默认风格（实用干货风）
