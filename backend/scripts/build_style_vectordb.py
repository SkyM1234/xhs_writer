"""
构建小红书写作风格向量库

使用 ChromaDB 和 Qwen Embedding 模型将 20 种写作风格转换为向量库
"""
import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import chromadb
from chromadb.config import Settings
from openai import OpenAI
from app.core.config import settings
from app.core.logger import logger
import os


def load_styles_from_json(json_path: str) -> list:
    """从 JSON 文件加载写作风格数据"""
    with open(json_path, 'r', encoding='utf-8') as f:
        styles = json.load(f)
    logger.info(f"✅ 加载了 {len(styles)} 种写作风格")
    return styles


def create_style_documents(styles: list) -> tuple[list[str], list[dict], list[str]]:
    """
    将风格数据转换为 multi-vector 文档格式

    每条风格拆成 4 个视角（聚焦语义信号，便于按 style_id 聚合检索）：
      - feature   : 风格名称 + 特点          → 调性匹配
      - scenario  : 适合内容                 → 话题/领域匹配
      - example   : 示例                     → 语感/真实文案匹配
      - holistic  : 全字段拼接               → 长 query 鲁棒兜底

    metadata 中带 style_id，用于检索后按风格聚合（max 策略）。

    Returns:
        documents: 用于 embedding 的文本列表
        metadatas: 元数据列表（含 style_id, view 字段）
        ids: 文档 ID 列表（格式：style_{编号}_{view}）
    """
    documents: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []

    for style in styles:
        style_id = style['编号']
        style_name = style['风格名称']
        features = style['特点']
        suitable_content = style['适合内容']
        structure = style['文案结构']
        example = style['示例']

        # 公共 metadata（每个 doc 都带完整风格信息，便于检索后直接使用）
        base_meta = {
            'style_id': style_id,
            'style_name': style_name,
            'features': features,
            'suitable_content': suitable_content,
            'structure': structure,
            'example': example,
        }

        # ===== 视角 1：feature（调性）=====
        feature_doc = (
            f"风格：{style_name}\n"
            f"调性特点：{features}"
        )
        documents.append(feature_doc)
        metadatas.append({**base_meta, 'view': 'feature'})
        ids.append(f"style_{style_id}_feature")

        # ===== 视角 2：scenario（领域/话题）=====
        scenario_doc = (
            f"风格：{style_name}\n"
            f"适合内容：{suitable_content}"
        )
        documents.append(scenario_doc)
        metadatas.append({**base_meta, 'view': 'scenario'})
        ids.append(f"style_{style_id}_scenario")

        # ===== 视角 3：example（语感）=====
        example_doc = (
            f"风格：{style_name}\n"
            f"典型表达：{example}"
        )
        documents.append(example_doc)
        metadatas.append({**base_meta, 'view': 'example'})
        ids.append(f"style_{style_id}_example")

        # ===== 视角 4：holistic（兜底）=====
        holistic_doc = (
            f"风格名称：{style_name}\n"
            f"特点：{features}\n"
            f"适合内容：{suitable_content}\n"
            f"文案结构：{structure}\n"
            f"示例：{example}"
        )
        documents.append(holistic_doc)
        metadatas.append({**base_meta, 'view': 'holistic'})
        ids.append(f"style_{style_id}_holistic")

    return documents, metadatas, ids


def get_qwen_embeddings(texts: list[str], client: OpenAI, batch_size: int = 25) -> list[list[float]]:
    """
    使用 Qwen Embedding 模型生成向量（分批调用）

    Args:
        texts: 文本列表
        client: OpenAI 客户端（兼容 Qwen API）
        batch_size: 单批大小（符合 Qwen 限制）

    Returns:
        embeddings: 向量列表（顺序与输入对齐）
    """
    logger.info(f"🔄 正在生成 {len(texts)} 个文本的向量（batch_size={batch_size}）...")

    all_embeddings: list[list[float]] = []
    total = len(texts)
    try:
        for start in range(0, total, batch_size):
            batch = texts[start:start + batch_size]
            logger.info(f"  📦 批次 {start // batch_size + 1}: 处理 {len(batch)} 条 ({start + 1}-{start + len(batch)}/{total})")
            response = client.embeddings.create(
                model=settings.LLM_EMBEDDING_MODEL,
                input=batch
            )
            all_embeddings.extend(item.embedding for item in response.data)

        logger.info(f"✅ 向量生成完成，共 {len(all_embeddings)} 条，维度：{len(all_embeddings[0])}")
        return all_embeddings

    except Exception as e:
        logger.error(f"❌ 向量生成失败: {e}")
        raise


def build_vectordb(
    styles_json_path: str,
    db_path: str,
    collection_name: str = "xiaohongshu_styles"
):
    """
    构建向量库
    
    Args:
        styles_json_path: 风格 JSON 文件路径
        db_path: 向量库保存路径
        collection_name: 集合名称
    """
    logger.info("🚀 开始构建小红书写作风格向量库...")
    
    # 加载风格数据
    styles = load_styles_from_json(styles_json_path)
    
    # 转换为文档格式
    documents, metadatas, ids = create_style_documents(styles)
    logger.info(f"✅ 准备了 {len(documents)} 个文档")
    
    # 初始化 Qwen Embedding 客户端

    qwen_client = OpenAI(
        api_key=os.getenv("QWEN_API_KEY"), # 从环境变量获取获取 API 密钥
        base_url=settings.LLM_BASE_URL or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    
    # 生成向量
    embeddings = get_qwen_embeddings(documents, qwen_client)
    
    # 初始化 ChromaDB
    logger.info(f"🔄 初始化 ChromaDB，路径：{db_path}")
    chroma_client = chromadb.PersistentClient(
        path=db_path,
        settings=Settings(anonymized_telemetry=False)
    )
    
    # 创建或获取集合（删除旧集合）
    try:
        chroma_client.delete_collection(name=collection_name)
        logger.info(f"🗑️ 删除旧集合：{collection_name}")
    except Exception:
        pass
    
    collection = chroma_client.create_collection(
        name=collection_name,
        metadata={
            "description": "小红书20种写作风格向量库",
            "hnsw:space": "cosine"  # 使用余弦相似度
        }
    )
    logger.info(f"✅ 创建集合：{collection_name}")
    
    # 7. 添加文档到集合
    collection.add(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )
    logger.info(f"✅ 添加了 {len(documents)} 个文档到向量库")
    
    # 8. 验证
    count = collection.count()
    logger.info(f"✅ 向量库构建完成！共 {count} 个文档")
    
    return collection


if __name__ == "__main__":
    # 配置路径
    styles_json = project_root / "data" / "style" / "xiaohongshu_20_styles.json"
    vectordb_path = project_root / "data" / "vectordb" / "styles"
    
    # 确保目录存在
    vectordb_path.mkdir(parents=True, exist_ok=True)
    
    # 构建向量库
    try:
        build_vectordb(
            styles_json_path=str(styles_json),
            db_path=str(vectordb_path),
            collection_name="xiaohongshu_styles"
        )
        logger.info("🎉 向量库构建成功！")
    except Exception as e:
        logger.error(f"❌ 向量库构建失败: {e}")
        raise
