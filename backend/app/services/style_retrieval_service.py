"""
小红书写作风格检索服务

使用 ChromaDB 向量库检索最匹配的写作风格
支持向量检索 + LLM Rerank 混合策略
"""
from pathlib import Path
from typing import Optional, List, Dict
import chromadb
from chromadb.config import Settings
from openai import OpenAI
from app.core.config import settings
from app.core.logger import logger
import os
import json


class StyleRetrievalService:
    """写作风格检索服务"""

    def __init__(self):
        self.chroma_client: Optional[chromadb.ClientAPI] = None
        self.collection = None
        self.qwen_client: Optional[OpenAI] = None
        self._initialized = False
    
    def initialize(self):
        """初始化向量库和 Qwen 客户端"""
        if self._initialized:
            return

        try:
            # 初始化 Qwen Embedding 客户端
            self.qwen_client = OpenAI(
                api_key=os.getenv("QWEN_API_KEY"), 
                base_url=settings.LLM_BASE_URL or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            
            # 初始化 ChromaDB
            vectordb_path = Path(__file__).parent.parent.parent / "data" / "vectordb" / "styles"
            
            if not vectordb_path.exists():
                logger.warning(f"⚠️ 向量库路径不存在: {vectordb_path}")
                logger.warning("⚠️ 请先运行 scripts/build_style_vectordb.py 构建向量库")
                return
            
            self.chroma_client = chromadb.PersistentClient(
                path=str(vectordb_path),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # 获取集合
            self.collection = self.chroma_client.get_collection(name="xiaohongshu_styles")
            
            logger.info(f"✅ 风格向量库初始化成功，共 {self.collection.count()} 个风格")
            self._initialized = True
            
        except Exception as e:
            logger.error(f"❌ 风格向量库初始化失败: {e}")
            self._initialized = False
    
    def _get_query_embedding(self, query_text: str) -> List[float]:
        """生成查询文本的向量"""
        try:
            response = self.qwen_client.embeddings.create(
                model=settings.LLM_EMBEDDING_MODEL,
                input=[query_text]
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"❌ 查询向量生成失败: {e}")
            raise
    
    def retrieve_style(
        self,
        keywords: List[str],
        persona: str,
        pain_points: List[str],
        emotion_triggers: List[str],
        top_k: int = 1,
        recall_k: int = 5,
        query_text: Optional[str] = None,
        selected_title: Optional[str] = None
    ) -> List[Dict]:
        """
        检索最匹配的写作风格（同步版本，使用模板化 query）

        Args:
            keywords: 关键词列表
            persona: 人设角度
            pain_points: 用户痛点
            emotion_triggers: 情绪触发点
            top_k: 最终返回前 k 个最匹配的风格
            recall_k: 向量召回阶段返回的候选数量（用于诊断和后续 rerank）
            query_text: 可选，外部传入已构造好的查询文本（如 LLM 改写后的结果）；
                        为空时使用内置优化模板
            selected_title: 可选，已选定的笔记标题（风格强信号）

        Returns:
            风格列表，每个风格包含 metadata 和相似度分数
        """
        # 确保已初始化
        if not self._initialized:
            self.initialize()

        # 如果初始化失败，返回空列表
        if not self._initialized or not self.collection:
            logger.warning("⚠️ 向量库未初始化，无法检索风格")
            return []

        try:
            # 优先使用外部传入的 query_text；否则用优化模板
            if not query_text:
                query_text = self._build_query_text(
                    keywords=keywords,
                    persona=persona,
                    pain_points=pain_points,
                    emotion_triggers=emotion_triggers,
                    selected_title=selected_title,
                )

            logger.info(f"🔍 检索写作风格，查询：{query_text[:120]}...")

            # 生成查询向量
            query_embedding = self._get_query_embedding(query_text)

            # 召回阶段（multi-vector）：
            # 由于每条风格被拆成 N 个视角 doc，需拉更多原始 doc 才能保证 top-k 风格被覆盖。
            # 经验值：原始召回数 = recall_k * 4（覆盖 4 个视角）+ 缓冲 4 条
            raw_recall = max(recall_k, top_k) * 4 + 4
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=raw_recall
            )

            # 解析原始 doc 级结果
            raw_hits = self._parse_query_results(results)

            # 按 style_id 聚合（max 策略）：同一风格的多个视角 doc，只保留最高相似度
            all_styles = self._aggregate_by_style(raw_hits)

            # ===== 可观测性：打印聚合后的召回分布 =====
            self._log_retrieval_distribution(all_styles)

            # 仅返回 top_k
            return all_styles[:top_k]

        except Exception as e:
            logger.error(f"❌ 风格检索失败: {e}")
            return []

    def _build_query_text(
        self,
        keywords: List[str],
        persona: str,
        pain_points: List[str],
        emotion_triggers: List[str],
        selected_title: Optional[str] = None,
    ) -> str:
        """
        构造检索 query 文本（模板兜底，方案 A）

        - keywords 只出现 1 次，避免重复 token 拉平向量
        - 砍掉"小红书内容""引发共鸣"等对所有风格都成立的废话
        - 选定标题（若有）作为风格的最强信号置于第一行
        """
        keywords_str = "、".join(keywords) if keywords else "通用话题"
        pain_points_str = "、".join(pain_points) if pain_points else "实用技巧"
        emotion_str = "、".join(emotion_triggers) if emotion_triggers else "干货分享"

        lines = []
        # 标题语感是风格最强信号，优先放最前
        if selected_title:
            lines.append(f"已定标题：{selected_title}")
        lines.append(f"选题：{keywords_str}")
        lines.append(f"人设：{persona}")
        lines.append(f"用户痛点：{pain_points_str}")
        lines.append(f"情绪基调：{emotion_str}")
        if selected_title:
            lines.append("期望表达：能匹配上述标题语感、情绪与人设的写作风格")
        else:
            lines.append("期望表达：能匹配上述情绪与人设的写作风格")
        return "\n".join(lines)

    def _parse_query_results(self, results: dict) -> List[Dict]:
        """
        解析 ChromaDB 查询结果，构造原始 doc 级命中列表

        每个元素代表一个被命中的 doc（multi-vector 下同一风格可能出现多次），
        保留 style_id 和 view 字段，供 _aggregate_by_style 后续聚合。
        """
        hits: List[Dict] = []
        if not (results and results.get('metadatas') and len(results['metadatas']) > 0):
            return hits

        for i, metadata in enumerate(results['metadatas'][0]):
            distance = results['distances'][0][i] if results.get('distances') else 0
            # cosine distance ∈ [0, 2]，相似度 = 1 - distance ∈ [-1, 1]
            similarity = 1 - distance
            hits.append({
                'style_id': metadata.get('style_id'),
                'view': metadata.get('view', 'holistic'),  # 兼容旧索引（无 view 字段）
                'style_name': metadata['style_name'],
                'features': metadata['features'],
                'suitable_content': metadata['suitable_content'],
                'structure': metadata['structure'],
                'example': metadata['example'],
                'similarity_score': similarity,
            })
        return hits

    def _aggregate_by_style(self, raw_hits: List[Dict]) -> List[Dict]:
        """
        按 style_id 聚合 multi-vector 命中结果（max 策略）

        同一风格的多个视角 doc，只保留相似度最高的那个，并附带：
          - hit_views: 该风格被命中了哪些视角
          - best_view: 最高相似度对应的视角
          - view_scores: 每个视角的相似度（用于精细诊断）

        Returns:
            聚合后的风格列表（按 max similarity 降序）
        """
        if not raw_hits:
            return []

        # 按 style_id 分组
        grouped: Dict = {}
        for hit in raw_hits:
            sid = hit.get('style_id')
            if sid is None:
                # 兼容旧索引：没有 style_id 时用 style_name 当 key
                sid = f"name:{hit['style_name']}"

            if sid not in grouped:
                # 第一次见到该风格，初始化聚合记录
                grouped[sid] = {
                    'style_id': hit.get('style_id'),
                    'style_name': hit['style_name'],
                    'features': hit['features'],
                    'suitable_content': hit['suitable_content'],
                    'structure': hit['structure'],
                    'example': hit['example'],
                    'similarity_score': hit['similarity_score'],
                    'best_view': hit['view'],
                    'hit_views': [hit['view']],
                    'view_scores': {hit['view']: hit['similarity_score']},
                }
            else:
                agg = grouped[sid]
                # 记录视角命中
                if hit['view'] not in agg['hit_views']:
                    agg['hit_views'].append(hit['view'])
                # 同视角重复命中时也保留较高分
                prev = agg['view_scores'].get(hit['view'], -1.0)
                if hit['similarity_score'] > prev:
                    agg['view_scores'][hit['view']] = hit['similarity_score']
                # 更新 max
                if hit['similarity_score'] > agg['similarity_score']:
                    agg['similarity_score'] = hit['similarity_score']
                    agg['best_view'] = hit['view']

        # 按聚合后的 max 相似度降序
        return sorted(grouped.values(), key=lambda x: x['similarity_score'], reverse=True)

    def _log_retrieval_distribution(self, styles: List[Dict]) -> None:
        """打印召回分布与区分度指标，方便诊断 RAG 质量（multi-vector 友好）"""
        if not styles:
            logger.warning("⚠️ 召回结果为空")
            return

        logger.info(f"📊 聚合后召回 {len(styles)} 个候选风格（按相似度降序）：")
        for idx, s in enumerate(styles, 1):
            best_view = s.get('best_view', '-')
            hit_views = s.get('hit_views', [])
            views_str = "/".join(hit_views) if hit_views else "-"
            logger.info(
                f"  [{idx}] {s['style_name']:<20} "
                f"sim={s['similarity_score']:.4f}  "
                f"best_view={best_view:<9} hit={views_str}"
            )

        # 区分度指标
        if len(styles) >= 2:
            top1 = styles[0]['similarity_score']
            top2 = styles[1]['similarity_score']
            gap_12 = top1 - top2
            spread = top1 - styles[-1]['similarity_score']
            logger.info(
                f"📐 区分度：top1-top2 gap = {gap_12:.4f}  |  "
                f"top1-top{len(styles)} spread = {spread:.4f}"
            )
            if gap_12 < 0.02:
                logger.warning(
                    f"⚠️ top1/top2 区分度过低（gap={gap_12:.4f}），"
                    f"建议触发 LLM rerank 以提升选择准确度"
                )

    async def retrieve_style_with_rerank(
        self,
        keywords: List[str],
        persona: str,
        pain_points: List[str],
        emotion_triggers: List[str],
        top_k: int = 1,
        recall_k: int = 5,
        rerank_gap_threshold: float = 0.03,
        force_rerank: bool = False,
        use_llm_rewrite: bool = True,
        selected_title: Optional[str] = None
    ) -> List[Dict]:
        """
        检索 + 自适应 LLM Rerank（推荐入口）

        完整链路：
        1. （可选）LLM 把选题信息改写成聚焦风格诉求的 query
        2. 向量召回 recall_k 个候选
        3. 若 top1/top2 区分度足够（gap >= 阈值）且非强制 rerank，直接返回向量 top_k
        4. 否则走 LLM rerank，让 LLM 在候选中选最合适的

        Args:
            keywords: 关键词列表
            persona: 人设角度
            pain_points: 用户痛点
            emotion_triggers: 情绪触发点
            top_k: 最终返回前 k 个
            recall_k: 向量召回候选数（默认 5）
            rerank_gap_threshold: top1-top2 分差阈值，低于此值触发 rerank
            force_rerank: 强制走 rerank（用于调试或质量优先场景）
            use_llm_rewrite: 是否启用 LLM 改写 query（默认 True，失败自动降级到模板）
            selected_title: 已选定的笔记标题（风格强信号），传入后参与 query 构造与 rerank

        Returns:
            风格列表（已带 rerank_reason 字段）
        """
        # ===== 构造查询文本=====
        query_text = None
        if use_llm_rewrite:
            query_text = await self._rewrite_query_with_llm(
                keywords=keywords,
                persona=persona,
                pain_points=pain_points,
                emotion_triggers=emotion_triggers,
                selected_title=selected_title,
            )
        # 改写失败或未启用：retrieve_style 内部会用 _build_query_text 兜底

        # ===== 向量召回 =====
        candidates = self.retrieve_style(
            keywords=keywords,
            persona=persona,
            pain_points=pain_points,
            emotion_triggers=emotion_triggers,
            top_k=recall_k,  # 注意：这里拿 recall_k 个，rerank 才有意义
            recall_k=recall_k,
            query_text=query_text,
            selected_title=selected_title,
        )

        if not candidates:
            return []

        # 判断是否需要 rerank
        need_rerank = force_rerank
        if not need_rerank and len(candidates) >= 2:
            gap = candidates[0]['similarity_score'] - candidates[1]['similarity_score']
            need_rerank = gap < rerank_gap_threshold

        if not need_rerank:
            logger.info(f"✅ 向量检索区分度足够，跳过 rerank，直接返回 top{top_k}")
            return candidates[:top_k]

        # 触发 LLM rerank
        logger.info(f"🤖 触发 LLM rerank，候选数={len(candidates)}")
        reranked = await self._llm_rerank(
            candidates=candidates,
            keywords=keywords,
            persona=persona,
            pain_points=pain_points,
            emotion_triggers=emotion_triggers,
            selected_title=selected_title,
        )
        return reranked[:top_k] if reranked else candidates[:top_k]

    async def _rewrite_query_with_llm(
        self,
        keywords: List[str],
        persona: str,
        pain_points: List[str],
        emotion_triggers: List[str],
        selected_title: Optional[str] = None,
    ) -> Optional[str]:
        """
        使用 LLM 把选题信息改写为聚焦"风格诉求"的查询文本

        Returns:
            改写后的 query 文本；失败时返回 None，由调用方降级到模板
        """
        from app.core.llm import llm_client

        keywords_str = "、".join(keywords) if keywords else "未指定"
        pain_points_str = "、".join(pain_points) if pain_points else "未指定"
        emotion_str = "、".join(emotion_triggers) if emotion_triggers else "未指定"

        system_prompt = """你是一位小红书写作风格分析专家。

你的任务：把用户的选题信息（含已定标题）改写成一段精准描述"该选题需要什么写作风格"的查询语句，用于在风格库中检索最匹配的写作风格。

改写原则：
1. 聚焦"风格诉求"，而不是"内容主题"。例如不要写"这是一篇关于减脂的内容"，而要写"需要一种结构清晰、信息密度高的实用攻略型表达"
2. 已定标题（如有）是风格的最强信号——优先从标题语感、句式、情绪基调中提取风格特征词，再结合关键词/人设/痛点/情绪做整合
3. 主动产出风格关键词。可参考的风格特征词：结构清晰、信息密度高、真诚推荐、细节描述、反差、反套路、戳心、温暖、抓马、叙事感、人物冲突、视觉对比、揭秘、爆点、模板清单、收藏型、平替、性价比、踩坑避雷、人设感、AIGC感、情境代入、人格分裂、打脸
4. 不要使用"小红书内容""引发共鸣""吸引用户"等对所有风格都成立的废话
5. 输出 60-120 字之间，紧凑、信息密集

只输出改写后的查询文本，不要任何前缀、解释或 markdown 标记。"""

        # 标题作为最强信号优先列出
        title_line = f"- 已定标题：{selected_title}\n" if selected_title else ""
        user_prompt = f"""# 选题信息
{title_line}- 关键词：{keywords_str}
- 人设：{persona}
- 用户痛点：{pain_points_str}
- 情绪诉求：{emotion_str}

# 任务
请改写为一段聚焦写作风格诉求的查询文本（60-120字）。"""

        try:
            response = await llm_client.chat_with_system(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=1000,
                model=settings.LLM_MODEL,
            )

            # 清洗：去除 markdown、引号、多余空白
            rewritten = response.strip().strip('"').strip("'").strip("`").strip()

            # 长度合理性校验（避免 LLM 输出过短或过长）
            if not rewritten or len(rewritten) < 20:
                logger.warning(f"⚠️ LLM 改写输出过短，降级使用模板：{rewritten!r}")
                return None
            if len(rewritten) > 400:
                logger.warning(f"⚠️ LLM 改写输出过长（{len(rewritten)}字），截断")
                rewritten = rewritten[:400]

            logger.info(f"✏️ LLM query 改写成功：{rewritten}")
            return rewritten

        except Exception as e:
            logger.warning(f"⚠️ LLM query 改写失败，降级使用模板：{e}")
            return None

    async def _llm_rerank(
        self,
        candidates: List[Dict],
        keywords: List[str],
        persona: str,
        pain_points: List[str],
        emotion_triggers: List[str],
        selected_title: Optional[str] = None,
    ) -> List[Dict]:
        """
        使用 LLM 对召回候选做精排

        让 LLM 阅读完整的风格描述（特点+适合内容+示例），结合选题
        信息（含已定标题）选出最合适的 1 个，并给出排序后的全部候选。

        Returns:
            重排后的候选列表（带 rerank_reason 和 rerank_score）；
            失败时返回空列表，调用方需自行降级到向量结果。
        """
        from app.core.llm import llm_client

        # 构造候选清单（编号从 1 开始，避免和 0-index 混淆）
        candidate_lines = []
        for idx, c in enumerate(candidates, 1):
            candidate_lines.append(
                f"[{idx}] {c['style_name']}\n"
                f"    特点: {c['features']}\n"
                f"    适合内容: {c['suitable_content']}\n"
                f"    示例: {c['example']}\n"
                f"    向量相似度: {c['similarity_score']:.3f}"
            )
        candidates_text = "\n\n".join(candidate_lines)

        keywords_str = "、".join(keywords) if keywords else "未指定"
        pain_points_str = "、".join(pain_points) if pain_points else "未指定"
        emotion_str = "、".join(emotion_triggers) if emotion_triggers else "未指定"

        system_prompt = """你是一位资深小红书内容策略师，擅长为不同选题匹配最合适的写作风格。

你的任务：在给定的候选风格中，选出最适合当前选题的写作风格。

判断标准（按重要性排序）：
1. 已定标题（如有）的语感与情绪基调，是判断风格的最强信号——优先匹配标题口吻
2. 风格的"适合内容"是否覆盖当前选题领域
3. 风格的"特点"是否匹配目标情绪与人设调性
4. 风格的表达方式是否能有效解决用户痛点
5. 优先选择区分度高、辨识度强的风格，避免选择"什么都沾一点"的泛化风格

注意：向量相似度仅供参考，不要被它主导判断；语义匹配优先于数值。"""

        # 标题作为最强信号优先列出
        title_line = f"- 已定标题：{selected_title}\n" if selected_title else ""
        user_prompt = f"""# 当前选题信息
{title_line}- 关键词：{keywords_str}
- 人设：{persona}
- 用户痛点：{pain_points_str}
- 情绪诉求：{emotion_str}

# 候选风格（共 {len(candidates)} 个）
{candidates_text}

# 任务
请从以上候选中选出最合适的 1 个，并对全部候选给出排序。

输出严格按 JSON 格式，不要带 markdown 代码块：
{{
  "best_index": <最佳候选编号，1~{len(candidates)}>,
  "reason": "<选择该风格的核心理由，30字以内>",
  "ranking": [<按推荐度从高到低排列的候选编号列表>]
}}"""

        try:
            response = await llm_client.chat_with_system(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,  # 精排追求稳定，降温
                max_tokens=1000,
                model=settings.LLM_MODEL,
            )

            # 解析 JSON（兼容 markdown 包裹）
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                logger.warning(f"⚠️ LLM rerank 输出无法解析为 JSON，降级使用向量排序")
                return []

            parsed = json.loads(json_match.group(0))
            best_idx = parsed.get('best_index')
            reason = parsed.get('reason', '')
            ranking = parsed.get('ranking', [])

            # 校验
            n = len(candidates)
            if not isinstance(best_idx, int) or not (1 <= best_idx <= n):
                logger.warning(f"⚠️ LLM 返回的 best_index 无效: {best_idx}")
                return []

            # 构造重排序结果
            valid_ranking = [i for i in ranking if isinstance(i, int) and 1 <= i <= n]
            # 把 best_idx 放在最前
            if best_idx in valid_ranking:
                valid_ranking.remove(best_idx)
            valid_ranking.insert(0, best_idx)
            # 补齐遗漏的候选
            for i in range(1, n + 1):
                if i not in valid_ranking:
                    valid_ranking.append(i)

            reranked = []
            for rank_pos, cand_idx in enumerate(valid_ranking):
                c = dict(candidates[cand_idx - 1])  # 浅拷贝
                c['rerank_position'] = rank_pos + 1
                # 给最佳候选附带理由
                if cand_idx == best_idx:
                    c['rerank_reason'] = reason
                reranked.append(c)

            logger.info(
                f"✅ LLM rerank 完成：top1=[{best_idx}] {reranked[0]['style_name']}  "
                f"理由：{reason}"
            )
            return reranked

        except Exception as e:
            logger.error(f"❌ LLM rerank 失败，降级使用向量排序: {e}")
            return []

    def get_default_style(self) -> Dict:
        """获取默认风格（实用干货风）"""
        return {
            'style_name': '实用干货风 / 教程型',
            'features': '结构清晰 + 信息密度高 + 可保存转发',
            'suitable_content': '职场技能、APP推荐、生活技巧、自媒体运营等',
            'structure': '标题：数字+关键词，制造收藏欲\n\n内容：步骤清晰，图文并茂\n\n结尾：引导点赞/关注/保存',
            'example': '「普通人也能做的自媒体3大变现路径（附资源+工具推荐）」 新手入门必看！我就是这样月入过万的👇',
            'similarity_score': 0.0
        }


# 全局单例
style_retrieval_service = StyleRetrievalService()
