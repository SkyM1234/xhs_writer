"""
LangGraph Agent 节点实现
"""
from typing import Dict
import json
from .state import GraphState
from .tools import (
    calculate_heat_score,
    check_sensitive_words,
    extract_title_pattern,
    format_content_with_emoji,
    extract_tags,
    calculate_quality_score,
    parse_title_candidates
)
from .error_handling import (
    add_error_to_history,
    add_degraded_node,
    log_error
)
from app.core.llm import llm_client
from app.core.websocket_manager import ws_manager
from app.core.logger import logger
from app.core.config import settings


# ===== 辅助函数 =====

def _get_task_id(state: GraphState) -> str:
    """从 state 中提取 task_id"""
    messages_list = state.get('messages', [])
    for msg in messages_list:
        if isinstance(msg, str) and msg.startswith('TASK_ID:'):
            return msg.replace('TASK_ID:', '').strip()
    return None


# ===== 数据层 Agent =====

async def trend_collector_node(state: GraphState) -> Dict:
    """热点采集员 - 抓取小红书热榜数据"""
    task_id = _get_task_id(state)
    logger.info(f"🔍 [trend_collector] task_id = {task_id}")

    # 发送节点开始信号
    if task_id:
        logger.debug(f"📤 [trend_collector] 发送 node_start 到 task_id={task_id}")
        await ws_manager.send_node_start(task_id, "trend_collector", "热点采集")
    else:
        logger.warning(f"⚠️ [trend_collector] task_id 为空，无法发送 WebSocket 消息")

    try:
        # ===== 数据验证 =====
        keywords = state.get('keywords')
        if not keywords or len(keywords) == 0:
            return {
                'status': 'failed',
                'error': '缺少关键词，无法采集数据',
                'messages': ['❌ 热点采集失败：未提供关键词']
            }

        # 目标采集数量（可以从state中获取，默认20）
        target_count = state.get('target_count', 20)

        # 构建查询配置对象（避免重复传递参数）
        query_config = {
            'keywords': keywords,
            'topic_words': state.get('topic_words', []),
            'min_comments': state.get('min_comments', 0),
            'min_likes': state.get('min_likes', 0),
            'min_favorites': state.get('min_favorites', 0),
            'days': state.get('days', 7)  # 查询最近7天的数据
        }

        # 使用真实爬虫
        from app.services.xhs_crawler_service import xhs_crawler_service

        messages = []

        # 先从数据库查询现有数据
        try:
            db_notes = await xhs_crawler_service.get_recent_notes_from_db(
                **query_config,
                limit=target_count
            )
            messages.append(f'📊 从数据库查询到 {len(db_notes)} 条笔记')
        except Exception as db_error:
            # 数据库查询失败
            logger.error(f"❌ 数据库查询失败: {db_error}")
            db_notes = []
            messages.append(f'⚠️ 数据库查询失败，将尝试直接爬取: {str(db_error)}')

        # 检查是否满足目标数量
        if len(db_notes) >= target_count:
            all_notes = db_notes[:target_count]
            messages.append(f'✅ 数据库中已有足够笔记（{len(db_notes)}条），无需爬取')
        else:
            # 数量不足，启动爬虫
            need_count = target_count - len(db_notes)
            messages.append(f'⚠️ 数据不足，需要爬取 {need_count} 条笔记')
            messages.append(f'🕷️ 启动爬虫（爬虫将自动翻页直到获取足够数据）...')

            logger.debug(f"[DEBUG] 数据库笔记数: {len(db_notes)}, 目标数量: {target_count}, 需要爬取: {need_count}")

            try:
                crawled_count = await xhs_crawler_service.crawl_notes(
                    **query_config,
                    target_count=need_count
                )
                messages.append(f'✅ 爬虫完成，新增 {crawled_count} 条笔记')
                logger.debug(f"[DEBUG] 爬虫完成，新增 {crawled_count} 条笔记")
            except Exception as e:
                log_error('trend_collector_crawler', e, state)
                messages.append(f'❌ 爬虫执行失败: {str(e)}')
                # 即使爬虫失败，也使用已有数据
                all_notes = db_notes
                final_count = len(all_notes)

                if final_count == 0:
                    # 完全没有数据
                    return {
                        'status': 'failed',
                        'error': '数据采集失败：数据库无数据且爬虫失败',
                        'raw_trends': [],
                        'messages': messages + ['❌ 无法获取任何数据，请检查网络连接或稍后重试']
                    }

                messages.append(f'⚠️ 使用现有数据，共 {final_count} 条笔记')
                return {
                    'raw_trends': all_notes,
                    'status': 'degraded',
                    'messages': messages
                }

            # 爬虫完成后，重新查询数据库获取所有数据
            try:
                all_notes = await xhs_crawler_service.get_recent_notes_from_db(
                    **query_config,
                    limit=target_count
                )
            except Exception as db_error:
                # 重新查询失败，使用之前的数据
                logger.error(f"❌ 重新查询数据库失败: {db_error}")
                all_notes = db_notes
                messages.append(f'⚠️ 重新查询失败，使用之前的数据')

        # 最终结果
        final_count = len(all_notes)
        if final_count == 0:
            return {
                'status': 'failed',
                'error': '数据采集失败：未获取到任何笔记',
                'raw_trends': [],
                'messages': messages + ['❌ 未获取到任何笔记，请调整筛选条件或关键词']
            }

        if final_count < target_count:
            messages.append(f'⚠️ 最终采集 {final_count} 条笔记，未达到目标 {target_count} 条')
        else:
            messages.append(f'✅ 热点采集完成，共 {final_count} 条笔记')
        
        notes_titles = [item['title'] for item in all_notes]

        # 发送节点完成信号
        if task_id:
            await ws_manager.send_node_complete(task_id, "trend_collector", "热点采集", {
                "notes_count": final_count, 
                "titles": notes_titles
            })

        return {
            'raw_trends': all_notes,
            'messages': messages
        }

    except Exception as e:
        # 捕获所有未预期的错误
        error_detail = log_error('trend_collector', e, state)
        error_history = add_error_to_history(state, 'trend_collector', e)

        return {
            'status': 'failed',
            'error': f'热点采集失败：{str(e)}',
            'error_detail': error_detail,
            'error_history': error_history,
            'raw_trends': [],
            'messages': [f'❌ 热点采集失败：{str(e)}']
        }

async def trend_analyzer_node(state: GraphState) -> Dict:
    """热点分析师 - 使用 LLM 深度分析爆款特征"""
    task_id = _get_task_id(state)

    # 发送节点开始信号
    if task_id:
        await ws_manager.send_node_start(task_id, "trend_analyzer", "热点分析")

    raw_trends = state['raw_trends']
    keywords = state['keywords']

    if not raw_trends:
        return {
            'analyzed_templates': [],
            'messages': ['⚠️ 没有热点数据可供分析']
        }

    # 基础数据处理：计算热度评分和提取模式
    basic_templates = []
    for item in raw_trends:
        heat_score = calculate_heat_score(item)
        title_pattern = extract_title_pattern(item['title'])

        template = {
            'title': item['title'],
            'content': item.get('content', ''),
            'pattern': title_pattern,
            'heat_score': heat_score,
            'tags': item['tags'],
            'engagement': {
                'likes': item['likes'],
                'favorites': item['favorites'],
                'comments': item['comments']
            }
        }
        basic_templates.append(template)

    # 按热度排序，进行深度分析
    basic_templates.sort(key=lambda x: x['heat_score'], reverse=True)
    top_notes = basic_templates

    # 使用 LLM 进行深度分析
    try:
        # 构建分析提示词
        notes_summary = "\n\n".join([
            f"【笔记{i+1}】\n标题：{note['title']}\n内容：{note['content']}\n标签：{', '.join(note['tags'])}\n互动数据：👍{note['engagement']['likes']} 💾{note['engagement']['favorites']} 💬{note['engagement']['comments']}"
            for i, note in enumerate(top_notes)
        ])

        system_prompt = """你是一位资深的小红书内容分析师，擅长从爆款笔记中提取成功模式。

你的任务是分析这些高互动笔记，提取出可复用的爆款特征。

请从以下维度进行分析：
1. **话题切入点**：用户关注的痛点、需求、场景
2. **情绪共鸣点**：引发共鸣的情绪类型（焦虑、好奇、惊喜等）
3. **标签策略**：高频标签、标签组合模式

请以 JSON 格式输出分析结果，格式如下：
{
  "pain_points": ["时间不够", "效率低下", "不知道怎么开始"],
  "emotion_triggers": ["焦虑", "好奇", "惊喜"],
  "hot_tags": ["干货分享", "实用技巧", "新手必看"],
  "key_insights": "这批笔记的核心成功要素是..."
}"""

        user_prompt = f"""关键词：{', '.join(keywords)}

以下是 {len(top_notes)} 篇高互动笔记：

{notes_summary}

请深度分析这些爆款笔记的成功模式。"""

        # 调用 LLM
        llm_response = await llm_client.chat_with_system(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,  # 降低温度，提高分析的稳定性
            max_tokens=2000,
            model=settings.LLM_MODEL
        )

        # 解析 LLM 返回的 JSON
        try:
            # 提取 JSON 部分（可能包含在 markdown 代码块中）
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', llm_response, re.DOTALL)
            if json_match:
                llm_analysis = json.loads(json_match.group(1))
            else:
                # 尝试直接解析
                llm_analysis = json.loads(llm_response)
        except json.JSONDecodeError:
            # JSON 解析失败，使用基础分析
            llm_analysis = {
                "pain_points": [],
                "emotion_triggers": [],
                "hot_tags": [],
                "key_insights": "LLM 分析结果解析失败"
            }

        # 发送节点完成信号
        if task_id:
            await ws_manager.send_node_complete(task_id, "trend_analyzer", "热点分析", {
                "template_count": len(basic_templates), 
                "key_insights": llm_analysis["key_insights"]
            })

        return {
            'analyzed_templates': basic_templates,
            'llm_analysis': llm_analysis,
            'messages': [
                f'✅ 热点分析完成，共分析 {len(basic_templates)} 个模板',
                f'📊 LLM 深度分析：{llm_analysis.get("key_insights", "已完成")[:50]}...'
            ]
        }

    except Exception as e:
        # LLM 调用失败，降级到基础分析
        llm_analysis = {
                "pain_points": [],
                "emotion_triggers": [],
                "hot_tags": [],
                "key_insights": "LLM 分析结果解析失败"
            }
        return {
            'analyzed_templates': basic_templates,
            'llm_analysis': llm_analysis,
            'messages': [
                f'✅ 热点分析完成（基础模式），提取 {len(basic_templates)} 个模板',
                f'⚠️ LLM 分析失败: {str(e)}'
            ]
        }


# ===== 内容生产层 Agent =====

async def strategist_node(state: GraphState) -> Dict:
    """选题策划师 - 确定内容策略（利用 LLM 分析结果）"""
    task_id = _get_task_id(state)

    # 发送节点开始信号
    if task_id:
        await ws_manager.send_node_start(task_id, "strategist", "选题策划")

    try:
        # ===== 数据验证 =====
        keywords = state.get('keywords')
        if not keywords or len(keywords) == 0:
            return {
                'status': 'failed',
                'error': '缺少关键词，无法制定内容策略',
                'messages': ['❌ 选题策划失败：未提供关键词']
            }

        persona = state.get('account_persona', '')
        if not persona or len(persona.strip()) == 0:
            persona = '专业分享者'

        keywords_str = "、".join(keywords)

        # 从state中获取 LLM 分析结果
        llm_analysis = state.get('llm_analysis', {})
        pain_points = llm_analysis.get('pain_points', [])
        emotion_triggers = llm_analysis.get('emotion_triggers', ['实用'])
        key_insights = llm_analysis.get('key_insights', '')
        hot_tags = llm_analysis.get('hot_tags', [])

        # 构建策略
        strategy = {
            'persona': persona,
            'emotion_point': '；'.join(emotion_triggers) if emotion_triggers else '实用、干货、避坑',
            'keywords': keywords,
            'keywords_str': keywords_str,
            'pain_points': pain_points if pain_points else [],
            'llm_insights': key_insights if key_insights else '',
            'hot_tags': hot_tags
        }

        # 发送节点完成信号
        if task_id:
            await ws_manager.send_node_complete(task_id, "strategist", "选题策划", {
                "keywords": keywords_str,
                "llm_insights": key_insights
            })

        return {
            'strategy': strategy,
            'messages': [
                f'✅ 选题策划完成，关键词：{keywords_str}',
                f'💡 核心洞察：{strategy["llm_insights"][:50]}...' if strategy["llm_insights"] else ''
            ]
        }

    except Exception as e:
        # 捕获所有未预期的错误
        error_detail = log_error('strategist', e, state)
        error_history = add_error_to_history(state, 'strategist', e)

        return {
            'status': 'failed',
            'error': f'选题策划失败：{str(e)}',
            'error_detail': error_detail,
            'error_history': error_history,
            'messages': [f'❌ 选题策划失败：{str(e)}']
        }


async def title_lab_node(state: GraphState) -> Dict:
    """标题实验室 - 使用 LLM 生成5个候选标题"""
    task_id = _get_task_id(state)

    # 发送节点开始信号
    if task_id:
        await ws_manager.send_node_start(task_id, "title_lab", "标题生成")
    
    # 从state中获取 LLM 分析结果
    keywords = state['keywords']
    strategy = state['strategy']

    # 使用主关键词（第一个）
    main_keyword = keywords[0] if keywords else "主题"
    keywords_str = strategy.get('keywords_str', main_keyword)

    # 从策略中获取信息
    pain_points = strategy.get('pain_points', [])
    llm_insights = strategy.get('llm_insights', '')
    hot_tags = strategy.get('hot_tags', [])

    try:
        # 构建标题生成提示词
        pain_points_desc = "；".join(pain_points) if pain_points else "效率低、不知道怎么做、容易出错"
        llm_insights_desc = llm_insights if llm_insights else "无"
        hot_tags_desc = "、".join(hot_tags) if hot_tags else "无"

        system_prompt = """你是一位小红书爆款标题专家，擅长创作高点击率的标题。

小红书标题的黄金法则：
1. 长度控制在15-25字
2. 包含核心关键词
3. 制造情绪钩子（好奇、焦虑、惊喜、利益、共鸣）
4. 避免标题党和夸张表述

请生成5个不同角度的标题，每个标题要：
- 符合小红书平台调性
- 针对用户痛点
- 有明确的情绪钩子
- 包含关键词
- 体现不同的切入角度或表达方式

输出格式（纯文本，每行一个标题，不要添加编号、类型标签或任何前缀）：
第一个标题
第二个标题
第三个标题
第四个标题
第五个标题"""

        user_prompt = f"""关键词：{keywords_str}
用户痛点：{pain_points_desc}
人设角度：{strategy.get('persona', '专业分享者')}

爆款笔记核心洞察：{llm_insights_desc}
爆款笔记热门标签：{hot_tags_desc}

请生成5个不同角度的小红书标题，每个标题从不同维度切入（如：实用价值、情感共鸣、反常识、故事化等），让用户有多样化的选择。"""

        # 调用 LLM
        llm_response = await llm_client.chat_with_system(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.8,  # 提高温度增加创意性
            max_tokens=500,
            model=settings.LLM_MODEL
        )

        # 解析标题（健壮解析，兼容多种 LLM 输出格式）
        title_candidates = parse_title_candidates(llm_response)

        # 如果解析失败，使用降级方案（默认标题）
        if len(title_candidates) < 5:
            log_error('title_lab_parse', ValueError(f'LLM 返回的标题数量不足：期望5个，实际{len(title_candidates)}个'), state)
            error_history = add_error_to_history(state, 'title_lab', ValueError('标题解析失败'))
            degraded_nodes = add_degraded_node(state, 'title_lab')

            title_candidates = [
                f'🔥{main_keyword}必看！这些技巧让你少走弯路',
                f'没想到{main_keyword}还能这样玩？我震惊了',
                f'关于{main_keyword}，你真的了解吗？',
                f'{main_keyword}避坑指南！新手必看',
                f'超实用！{main_keyword}的正确打开方式'
            ]

            # 发送节点完成信号
            if task_id:
                await ws_manager.send_node_complete(task_id, "title_lab", "标题生成", {
                    "titles": title_candidates
                })

            return {
                'title_candidates': title_candidates,
                'status': 'degraded',
                'error_history': error_history,
                'degraded_nodes': degraded_nodes,
                'messages': [
                    f'✅ 标题生成完成（降级模式），共 {len(title_candidates)} 个候选标题',
                    f'⚠️ LLM 返回标题不足，使用默认标题'
                ]
            }

        # 发送节点完成信号
        if task_id:
            await ws_manager.send_node_complete(task_id, "title_lab", "标题生成", {
                "titles": title_candidates
            })

        return {
            'title_candidates': title_candidates,
            'status': 'waiting_human',
            'messages': [
                f'✅ 标题生成完成，共 {len(title_candidates)} 个候选标题',
                f'📝 标题1: {title_candidates[0][:30]}...',
                f'📝 标题2: {title_candidates[1][:30]}...',
                f'📝 标题3: {title_candidates[2][:30]}...',
                f'📝 标题4: {title_candidates[3][:30]}...',
                f'📝 标题5: {title_candidates[4][:30]}...'
            ]
        }

    except Exception as e:
        # LLM 调用失败，使用降级方案（默认标题）
        log_error('title_lab', e, state)
        error_history = add_error_to_history(state, 'title_lab', e)
        degraded_nodes = add_degraded_node(state, 'title_lab')

        title_candidates = [
            f'🔥{main_keyword}必看！这些技巧让你少走弯路',
            f'没想到{main_keyword}还能这样玩？我震惊了',
            f'关于{main_keyword}，你真的了解吗？',
            f'{main_keyword}避坑指南！新手必看',
            f'超实用！{main_keyword}的正确打开方式'
        ]

        # 发送节点完成信号
        if task_id:
            await ws_manager.send_node_complete(task_id, "title_lab", "标题生成", {
                "titles": title_candidates
            })

        return {
            'title_candidates': title_candidates,
            'status': 'degraded',
            'error_history': error_history,
            'degraded_nodes': degraded_nodes,
            'messages': [
                f'✅ 标题生成完成（降级模式），共 {len(title_candidates)} 个候选标题',
                f'⚠️ LLM 生成失败，使用默认标题: {str(e)}'
            ]
        }


async def copywriter_node(state: GraphState) -> Dict:
    """爆款写手 - 使用 LLM 生成正文内容"""
    task_id = _get_task_id(state)

    # 发送节点开始信号
    if task_id:
        await ws_manager.send_node_start(task_id, "copywriter", "文案创作")

    try:
        # 验证必需字段
        keywords = state.get('keywords')
        if not keywords or len(keywords) == 0:
            return {
                'status': 'failed',
                'error': '缺少关键词，无法生成内容',
                'messages': ['❌ 文案生成失败：未提供关键词']
            }

        strategy = state.get('strategy')
        if not strategy:
            return {
                'status': 'failed',
                'error': '缺少选题策略，无法生成内容',
                'messages': ['❌ 文案生成失败：选题策略缺失']
            }

        # 验证标题
        selected_title = state.get('selected_title')
        if not selected_title:
            # 尝试使用第一个候选标题
            title_candidates = state.get('title_candidates', [])
            if not title_candidates or len(title_candidates) == 0:
                return {
                    'status': 'failed',
                    'error': '未找到可用的标题',
                    'messages': ['❌ 文案生成失败：未找到可用的标题，请先生成标题候选']
                }
            selected_title = title_candidates[0]

        # ===== 获取数据 =====
        templates = state.get('analyzed_templates', [])
        iteration_count = state.get('iteration_count', 0)

        # 获取反馈信息
        editor_feedback = state.get('editor_feedback', {})
        human_feedback = state.get('human_feedback')
        compliance_report = state.get('compliance_report', {})

        # 使用主关键词（第一个）
        main_keyword = keywords[0] if keywords else "主题"
        keywords_str = strategy.get('keywords_str', main_keyword)

        # 从state中获取 LLM 分析结果
        pain_points = strategy.get('pain_points', [])
        emotion_triggers = strategy.get('emotion_point', '实用、干货')

        pain_points_desc = "\n".join([f"- {p}" for p in pain_points]) if pain_points else "- 不知道怎么开始\n- 容易出错\n- 效率低下"

        # ===== 使用 RAG 检索写作风格（向量召回 + 自适应 LLM Rerank）=====
        # 检查是否已有缓存的风格检索结果（避免重复检索）
        retrieved_styles = state.get('retrieved_styles')

        if not retrieved_styles:
            # 首次执行，进行风格检索
            from app.services.style_retrieval_service import style_retrieval_service

            # 初始化风格检索服务
            style_retrieval_service.initialize()

            # 检索最匹配的写作风格
            persona = strategy.get('persona', '专业分享者')
            pain_points_list = pain_points if isinstance(pain_points, list) else []
            emotion_list = emotion_triggers.split('、') if isinstance(emotion_triggers, str) else []

            # 召回 5 个候选；当 top1/top2 区分度不足（gap < 0.03）时自动触发 LLM rerank
            retrieved_styles = await style_retrieval_service.retrieve_style_with_rerank(
                keywords=keywords,
                persona=persona,
                pain_points=pain_points_list,
                emotion_triggers=emotion_list,
                top_k=1,
                recall_k=5,
                rerank_gap_threshold=0.03,
                selected_title=selected_title,  # 标题是风格最强信号，参与 query 改写与 rerank
            )

            logger.info(f"✅ 首次执行风格检索，结果已缓存")
        else:
            logger.info(f"♻️ 使用缓存的风格检索结果，避免重复调用")

        # 构建风格指导内容
        style_guidance = ""
        if retrieved_styles:
            style = retrieved_styles[0]
            sim = style.get('similarity_score', 0.0)
            rerank_reason = style.get('rerank_reason')

            # rerank 命中：信任 LLM 选择，直接使用 top1
            # 未触发 rerank：说明向量区分度足够，也直接使用 top1
            extra_note = f"（LLM精排理由：{rerank_reason}）" if rerank_reason else ""
            style_guidance = f"""
推荐写作风格：{style['style_name']} (向量相似度: {sim:.2f}){extra_note}

风格特点：{style['features']}

适合内容：{style['suitable_content']}

文案结构：
{style['structure']}"""
        else:
            # 检索完全失败：降级到默认风格
            logger.warning("⚠️ 风格检索无结果，使用默认风格")
            default_style = style_retrieval_service.get_default_style()
            style_guidance = f"""
推荐写作风格：{default_style['style_name']} (默认)

风格特点：{default_style['features']}

适合内容：{default_style['suitable_content']}

文案结构：
{default_style['structure']}"""

        # 构建反馈信息（如果是重新生成）
        feedback_section = ""
        if iteration_count > 0:
            feedback_parts = []

            # 添加编辑反馈
            if editor_feedback:
                score = editor_feedback.get('score', 0)
                suggestions = editor_feedback.get('suggestions', [])
                if suggestions:
                    feedback_parts.append(f"编辑评分：{score}分")
                    feedback_parts.append("编辑建议：")
                    feedback_parts.extend([f"- {s}" for s in suggestions])

            # 添加人工反馈（优先级最高）
            if human_feedback:
                feedback_parts.append(f"\n人工审核意见：{human_feedback}")

            # 添加合规问题
            if not compliance_report.get('passed', True):
                issues = compliance_report.get('issues', [])
                if issues:
                    feedback_parts.append("\n⚠️ 合规问题：")
                    feedback_parts.extend([f"- {issue}" for issue in issues])

            if feedback_parts:
                feedback_section = f"""

⚠️ 这是第 {iteration_count + 1} 次生成，请根据以下反馈进行改进：

{chr(10).join(feedback_parts)}

请针对以上问题进行优化，生成更好的内容。"""

        system_prompt = """你是一位小红书博主，正在分享自己的真实经验和心得。

写作要点：
1. 像和朋友聊天一样自然表达，不要太正式或模板化
2. 开头可以用自己的经历或观察切入，引起共鸣
3. 内容要有实际价值，分享具体的方法、技巧或避坑经验
4. 适当用emoji点缀（5-10个），但不要过度使用
5. 可以用数字、符号来组织内容，但要自然融入，不要刻意分点
6. 最后加上3-5个相关话题标签

注意事项：
- 保持真实感，避免套路化的表达
- 字数300-500字左右，不要太长
- 不要有广告和引流信息
- 语气轻松但不浮夸

⚠️ 真实性要求（重要）：
- **禁止虚构人际关系**：不要编造"我朋友"、"我亲戚"、"我认识的人"、"我同事"、"我室友"等虚构人物
- **使用第一人称直接经验**：用"我自己"、"我发现"、"我试过"、"我的经验"等直接表达
- **客观表达替代**：如需引用案例，使用"很多人"、"常见的情况是"、"网上经常看到"等客观表达
- **聚焦方法论**：直接分享干货、技巧、步骤，不需要通过他人故事来包装
- **可验证性**：内容应基于可验证的事实、方法、现象，而非虚构的个人故事

请写一篇自然流畅的小红书内容。"""

        user_prompt = f"""标题：{selected_title}

关键词：{keywords_str}
人设角度：{strategy.get('persona', '专业分享者')}
情绪点：{emotion_triggers}

用户痛点：
{pain_points_desc}

{style_guidance}{feedback_section}

请生成一篇小红书内容（包含正文、标签）。"""

        # 调用 LLM
        llm_response = await llm_client.chat_with_system(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=2000,
            model=settings.LLM_MODEL
        )

        # 确保包含标签
        if '#' not in llm_response:
            # 生成标签
            tags = " ".join([f"#{kw}" for kw in keywords]) + " #干货分享 #实用技巧 #新手必看"
            draft_content = f"{llm_response.strip()}\n\n{tags}"
        else:
            draft_content = llm_response.strip()

        # 添加 Emoji（如果不足）
        draft_content = format_content_with_emoji(draft_content)

        # 发送节点完成信号（包含完整的 draft_content）
        if task_id:
            await ws_manager.send_node_complete(task_id, "copywriter", "文案创作", {
                "content_length": len(draft_content),
                "title": selected_title,
                "draft_content": draft_content  # 添加完整内容
            })

        return {
            'draft_content': draft_content,
            'selected_title': selected_title,
            'retrieved_styles': retrieved_styles,  # 缓存风格检索结果
            'human_decision': None,  # 清除人工审核决策，准备下次审核
            'human_feedback': None,  # 清除人工反馈
            'messages': [
                f'✅ 文案生成完成，字数：{len(draft_content)}',
                f'📝 使用了 LLM 深度分析的爆款模式'
            ]
        }

    except Exception as e:
        # LLM 生成失败，直接报错，不使用降级方案
        error_detail = log_error('copywriter', e, state)
        error_history = add_error_to_history(state, 'copywriter', e)

        return {
            'status': 'failed',
            'error': f'文案生成失败：{str(e)}',
            'error_detail': error_detail,
            'error_history': error_history,
            'messages': [f'❌ 文案生成失败：{str(e)}']
        }


async def visual_designer_node(state: GraphState) -> Dict:
    """视觉导演 - 生成图片提示词并生成图片"""
    task_id = _get_task_id(state)

    # 发送节点开始信号
    if task_id:
        await ws_manager.send_node_start(task_id, "visual_designer", "视觉设计")

    try:
        # ===== 数据验证 =====
        keywords = state.get('keywords')
        if not keywords or len(keywords) == 0:
            return {
                'status': 'failed',
                'error': '缺少关键词，无法生成图片',
                'messages': ['❌ 图片生成失败：未提供关键词']
            }

        title = state.get('selected_title', '')
        draft_content = state.get('draft_content', '')

        # 使用主关键词（第一个）
        keywords_str = "、".join(keywords)

        # ===== 第一步：使用 LLM 生成优化的图片提示词 =====
        system_prompt = """你是一位专业的小红书视觉设计师，擅长为不同主题内容生成多样化、高质感的配图提示词。

核心原则：
1. **深度理解内容主题**：仔细分析标题和内容，提取核心场景和情感
2. **场景多样化**：根据主题选择最合适的场景类型
   - 学习类：图书馆、自习室、笔记特写、知识图谱等
   - 生活类：居家场景、户外风景、物品特写等
   - 情感类：自然风光、抽象意境、色彩氛围等
   - 美食类：食物特写、餐桌布置、烹饪场景等
   - 旅行类：风景、建筑、街景等
3. **视觉风格灵活选择**：根据内容主题和情感选择最合适的风格
   - 插画风格：适合教程、指南类内容，简洁清晰
   - 扁平化设计：适合概念、流程类内容，现代简约
   - 水彩风格：适合情感、生活类内容，柔和温暖
   - 简约风格：适合专业、严肃类内容，干净利落
   - 半写实风格：适合美食、旅行类内容，真实感强
4. **色彩情感化**：根据内容情感选择合适的色调
   - 温暖色调（米色、浅橙、暖黄）：温馨、治愈、舒适
   - 冷静色调（浅蓝、薄荷绿、灰白）：专业、理性、清爽
   - 清新色调（嫩绿、天蓝、乳白）：活力、自然、轻松
   - 沉稳色调（深蓝、墨绿、棕灰）：成熟、可靠、高级
5. **色彩饱和度控制**：避免过度鲜艳，使用柔和自然的色彩，饱和度适中

输出要求：
直接输出一句完整的图片描述，包含：画面主体、场景环境、视觉风格、色彩氛围、光线效果、构图方式。
不要添加任何解释或前缀。
"""

        user_prompt = f"""请为以下小红书内容生成配图提示词：

【标题】{title}

【内容】{draft_content[:800]}{'...' if len(draft_content) > 800 else ''}


【关键词】{keywords_str}

要求：
1. 根据内容主题和情感，自主选择最合适的视觉风格（插画、扁平化、水彩、简约、半写实等）
2. 深入理解内容主题，选择最贴合的场景类型
3. 画面要与内容主题强相关，能直观传达核心信息
4. 色彩柔和自然，饱和度适中，避免过度鲜艳
5. 根据内容情感选择合适的色调（温暖、冷静、清新、沉稳等）
6. 避免文字、人脸、品牌logo等敏感元素
7. 适合作为小红书封面图使用

直接输出图片提示词："""

        # 调用 LLM 生成提示词
        llm_response = await llm_client.chat_with_system(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.8,  # 提高创造性
            max_tokens=1000,
            model=settings.LLM_MODEL,
        )

        # 清理提示词
        optimized_prompt = llm_response.strip().strip('"').strip("'")

        # 负面提示词（避免不想要的元素）
        negative_prompt = "文字，水印，logo，人脸，低质量，模糊，噪点，变形，过度饱和，过度鲜艳"


        # ===== 第二步：调用图片生成 API =====
        from app.services.image_generation_service import image_generation_service
        from app.utils.image_downloader import image_downloader
        from pathlib import Path

        try:
            # 构建完整的提示词，强调质量和自然感
            full_prompt = f"{optimized_prompt}, 高质量, 精致细节, 柔和色彩, 自然光线, 构图优美, 小红书风格"

            image_urls = await image_generation_service.generate_image(
                prompt=full_prompt,
                negative_prompt=negative_prompt,
                size=settings.IMAGE_SIZE,
                n=settings.IMAGE_COUNT
            )

            # ===== 第三步：下载图片到目标目录 =====
            local_paths = []
            if image_urls:
                try:
                    # 创建目标目录：data/outputs/{关键词}_{task_id}/images/
                    main_keyword = keywords[0] if keywords else "content"
                    output_dir = Path(__file__).parent.parent.parent / "data" / "outputs" / f"{main_keyword}_{task_id}"
                    images_dir = output_dir / "images"
                    images_dir.mkdir(parents=True, exist_ok=True)

                    # 生成文件名前缀（使用第一个关键词）
                    prefix = keywords[0] if keywords else "image"
                    # 批量下载图片到目标目录
                    local_paths = await image_downloader.download_images(
                        image_urls,
                        prefix=prefix,
                        target_dir=str(images_dir)
                    )

                    if local_paths:
                        logger.info(f"✅ 图片已下载到: {images_dir}, 共 {len(local_paths)} 张")
                    else:
                        logger.warning(f"⚠️ 图片下载失败，但保留了在线 URL")
                except Exception as download_error:
                    logger.warning(f"⚠️ 图片下载失败: {download_error}")
                    # 下载失败不影响整体流程，继续使用在线 URL

            # 发送节点完成信号
            if task_id:
                await ws_manager.send_node_complete(task_id, "visual_designer", "视觉设计", {
                    "image_prompt": optimized_prompt,
                    "image_count": len(image_urls)
                })

            return {
                'image_prompts': [optimized_prompt],
                'image_urls': image_urls,
                'image_local_paths': local_paths,  # 新增：本地路径
                'messages': [
                    f'✅ 图片提示词生成完成',
                    f'✅ 图片生成成功，共 {len(image_urls)} 张',
                    f'✅ 图片已下载到本地，共 {len(local_paths)} 张' if local_paths else '⚠️ 图片下载失败，使用在线 URL'
                ]
            }

        except Exception as img_error:
            # 图片生成失败，但提示词生成成功
            logger.warning(f"⚠️ 图片生成失败: {img_error}")
            return {
                'image_prompts': [optimized_prompt],
                'image_urls': [],
                'image_local_paths': [],
                'messages': [
                    f'✅ 图片提示词生成完成',
                    f'⚠️ 图片生成失败: {str(img_error)}',
                    f'💡 提示词: {optimized_prompt}'
                ]
            }

    except Exception as e:
        # 捕获所有未预期的错误
        log_error('visual_designer', e, state)
        error_history = add_error_to_history(state, 'visual_designer', e)

        # 使用降级方案（默认提示词）
        degraded_nodes = add_degraded_node(state, 'visual_designer')

        # 尝试使用默认提示词生成图片
        default_prompt = f"小红书风格封面图，主题：{keywords_str if keywords else '生活分享'}，简约清新，温暖色调，卡通风格"

        try:
            from app.services.image_generation_service import image_generation_service
            from app.utils.image_downloader import image_downloader
            from pathlib import Path

            image_urls = await image_generation_service.generate_image(
                prompt=default_prompt,
                size=settings.IMAGE_SIZE,
                n=1
            )

            # 下载图片到目标目录
            local_paths = []
            if image_urls:
                try:
                    # 创建目标目录
                    main_keyword = keywords[0] if keywords else "content"
                    output_dir = Path(__file__).parent.parent.parent / "data" / "outputs" / f"{main_keyword}_{task_id}"
                    images_dir = output_dir / "images"
                    images_dir.mkdir(parents=True, exist_ok=True)

                    prefix = keywords[0] if keywords else "image"
                    local_paths = await image_downloader.download_images(
                        image_urls,
                        prefix=prefix,
                        target_dir=str(images_dir)
                    )
                except Exception as download_error:
                    logger.warning(f"⚠️ 图片下载失败: {download_error}")

            return {
                'image_prompts': [default_prompt],
                'image_urls': image_urls,
                'image_local_paths': local_paths,
                'status': 'degraded',
                'error_history': error_history,
                'degraded_nodes': degraded_nodes,
                'messages': [
                    f'⚠️ 提示词优化失败，使用默认提示词: {str(e)}',
                    f'✅ 图片生成成功（使用默认提示词）',
                    f'✅ 图片已下载到本地' if local_paths else '⚠️ 图片下载失败'
                ]
            }
        except Exception as fallback_error:
            # 完全失败
            return {
                'image_prompts': [default_prompt],
                'image_urls': [],
                'image_local_paths': [],
                'status': 'degraded',
                'error_history': error_history,
                'degraded_nodes': degraded_nodes,
                'messages': [
                    f'⚠️ 提示词优化失败: {str(e)}',
                    f'⚠️ 图片生成失败: {str(fallback_error)}',
                    f'💡 默认提示词: {default_prompt}'
                ]
            }


# ===== 质量控制层 Agent =====

async def compliance_checker_node(state: GraphState) -> Dict:
    """合规审查员 - 检查违禁词和平台规则"""
    task_id = _get_task_id(state)

    # 发送节点开始信号
    if task_id:
        await ws_manager.send_node_start(task_id, "compliance_checker", "合规检查")

    try:
        # ===== 数据验证 =====
        draft_content = state.get('draft_content')
        if not draft_content:
            return {
                'status': 'failed',
                'error': '缺少草稿内容，无法进行合规检查',
                'messages': ['❌ 合规检查失败：未找到草稿内容']
            }

        title = state.get('selected_title', '')

        # 检查标题和正文
        title_check = check_sensitive_words(title) if title else {'passed': True, 'risk_level': 'low', 'issues': []}
        content_check = check_sensitive_words(draft_content)

        compliance_report = {
            'title_check': title_check,
            'content_check': content_check,
            'overall_risk': 'high' if title_check.get('risk_level') == 'high' or content_check.get('risk_level') == 'high' else content_check.get('risk_level', 'low'),
            'passed': title_check.get('passed', True) and content_check.get('passed', True),
            'suggestions': [],
            'issues': []
        }

        # 收集问题
        if title_check.get('issues'):
            compliance_report['issues'].extend([f'标题: {issue}' for issue in title_check['issues']])
        if content_check.get('issues'):
            compliance_report['issues'].extend([f'内容: {issue}' for issue in content_check['issues']])

        if not compliance_report['passed']:
            compliance_report['suggestions'].append('请移除敏感词后重新生成')

        # 发送节点完成信号
        if task_id:
            await ws_manager.send_node_complete(task_id, "compliance_checker", "合规检查", {
                "passed": compliance_report['passed']
            })

            # 如果合规不通过，发送节点重置消息（将回退到文案创作）
            if not compliance_report['passed']:
                nodes_to_reset = ['compliance_checker', 'chief_editor', 'human_review', 'visual_designer', 'finalize']
                await ws_manager.send_nodes_reset(task_id, nodes_to_reset)

        return {
            'compliance_report': compliance_report,
            'status': 'compliance_passed' if compliance_report['passed'] else 'compliance_failed',
            'messages': [f'✅ 合规检查完成，风险等级：{compliance_report["overall_risk"]}']
        }

    except Exception as e:
        # 捕获所有未预期的错误
        log_error('compliance_checker', e, state)
        error_history = add_error_to_history(state, 'compliance_checker', e)

        # 合规检查失败，使用降级方案（跳过检查但警告）
        degraded_nodes = add_degraded_node(state, 'compliance_checker')

        return {
            'compliance_report': {
                'title_check': {'passed': True, 'risk_level': 'unknown', 'issues': []},
                'content_check': {'passed': True, 'risk_level': 'unknown', 'issues': []},
                'overall_risk': 'unknown',
                'passed': True,  # 降级：允许通过但标记为未检查
                'suggestions': [],
                'issues': []
            },
            'status': 'degraded',
            'error_history': error_history,
            'degraded_nodes': degraded_nodes,
            'messages': [
                f'⚠️ 合规检查失败，已跳过检查: {str(e)}',
                f'⚠️ 请人工审核内容是否符合平台规范'
            ]
        }


async def chief_editor_node(state: GraphState) -> Dict:
    """终审编辑 - 综合评估内容质量"""
    task_id = _get_task_id(state)

    # 发送节点开始信号
    if task_id:
        await ws_manager.send_node_start(task_id, "chief_editor", "终审编辑")

    try:
        # ===== 数据验证 =====
        draft_content = state.get('draft_content')
        if not draft_content:
            return {
                'status': 'failed',
                'error': '缺少草稿内容，无法进行终审',
                'messages': ['❌ 终审失败：未找到草稿内容']
            }

        compliance_report = state.get('compliance_report')
        if not compliance_report:
            return {
                'status': 'failed',
                'error': '缺少合规检查报告，无法进行终审',
                'messages': ['❌ 终审失败：合规检查报告缺失']
            }

        # ===== 获取数据 =====
        title = state.get('selected_title', '')
        iteration_count = state.get('iteration_count', 0)
        keywords = state.get('keywords', [])

        # ===== 规则打分 =====
        content_dict = {
            'title': title,
            'content': draft_content,
            'tags': extract_tags(draft_content)
        }
        rule_score = calculate_quality_score(content_dict)
        logger.info(f"📊 规则打分: {rule_score}")

        # ===== LLM 打分 =====
        llm_score = None
        llm_feedback_text = ""

        try:
            # 构建 LLM 评分提示词
            system_prompt = """你是一位资深的小红书内容审核专家，负责评估内容质量。

评分维度（总分100分）：
1. **标题吸引力**（20分）：是否有钩子、是否包含关键词、是否符合平台调性
2. **内容价值**（30分）：是否有实用信息、是否解决用户痛点、是否有独特见解
3. **结构完整性**（20分）：开头、正文、结尾是否完整，逻辑是否清晰
4. **表达自然度**（20分）：语言是否自然流畅，是否过度套路化
5. **互动潜力**（10分）：是否容易引发评论、点赞、收藏

请以 JSON 格式输出评分结果：
{
  "score": 85,
  "strengths": ["标题有吸引力", "内容实用"],
  "weaknesses": ["结尾略显生硬"],
  "suggestions": ["可以在结尾增加互动引导"]
}"""

            user_prompt = f"""请评估以下小红书内容：

【标题】
{title}

【正文】
{draft_content[:800]}{'...' if len(draft_content) > 800 else ''}

【关键词】
{', '.join(keywords)}

请给出客观评分和改进建议。"""

            # 调用 LLM（使用评分模型）
            llm_response = await llm_client.chat_with_system(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,  # 降低温度，提高评分稳定性
                max_tokens=1000,
                model=settings.LLM_JUDAGE_MODEL  # 使用评分模型
            )

            # 解析 LLM 返回的 JSON
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', llm_response, re.DOTALL)
            if json_match:
                llm_result = json.loads(json_match.group(1))
            else:
                llm_result = json.loads(llm_response)

            llm_score = llm_result.get('score', 0)

            # 构建 LLM 反馈文本
            strengths = llm_result.get('strengths', [])
            weaknesses = llm_result.get('weaknesses', [])
            suggestions = llm_result.get('suggestions', [])

            feedback_parts = []
            if strengths:
                feedback_parts.append(f"优点：{', '.join(strengths)}")
            if weaknesses:
                feedback_parts.append(f"不足：{', '.join(weaknesses)}")
            if suggestions:
                feedback_parts.append(f"建议：{', '.join(suggestions)}")

            llm_feedback_text = "; ".join(feedback_parts)
            logger.info(f"🤖 LLM 打分: {llm_score}")
            logger.info(f"💬 LLM 反馈: {llm_feedback_text}")

        except Exception as llm_error:
            # LLM 打分失败，降级到纯规则打分
            logger.warning(f"⚠️ LLM 打分失败，降级到规则打分: {llm_error}")
            llm_score = None

        # ===== 加权计算最终分数 =====
        if llm_score is not None:
            # 规则打分 40% + LLM 打分 60%
            quality_score = int(rule_score * 0.4 + llm_score * 0.6)
            score_method = "混合评分"
            logger.info(f"⚖️ 最终评分: {quality_score} (规则{rule_score}*0.4 + LLM{llm_score}*0.6)")
        else:
            # 降级：仅使用规则打分
            quality_score = rule_score
            score_method = "规则评分"
            logger.info(f"⚖️ 最终评分: {quality_score} (仅规则打分)")

        # 判断是否通过（80分以上才考虑通过）
        passed = quality_score >= 80 and compliance_report.get('passed', False)

        feedback = {
            'score': quality_score,  # 添加 score 字段用于路由判断
            'quality_score': quality_score,
            'rule_score': rule_score,  # 保留规则分数
            'llm_score': llm_score,  # 保留 LLM 分数
            'score_method': score_method,  # 评分方法
            'passed': passed,
            'iteration': iteration_count + 1,
            'suggestions': []
        }

        # 添加建议
        if not passed:
            if quality_score < 80:
                feedback['suggestions'].append(f'内容质量评分 {quality_score}（{score_method}），需要优化')
            if llm_feedback_text:
                feedback['suggestions'].append(f'AI 反馈：{llm_feedback_text}')
            if not compliance_report.get('passed', False):
                feedback['suggestions'].extend(compliance_report.get('suggestions', []))

        # 根据评分设置状态
        if quality_score >= 90:
            new_status = 'approved'  # 90分以上直接通过
        elif quality_score >= 80:
            new_status = 'pending_human_review'  # 80-90分待人工审核
        else:
            new_status = 'review_failed'  # 80分以下继续修改

        # 发送节点完成信号
        if task_id:
            await ws_manager.send_node_complete(task_id, "chief_editor", "终审编辑", {
                "score": quality_score,
                "status": new_status,
                "title": title  # 添加标题字段，供前端显示
            })

            # 如果评分不通过，发送节点重置消息（回退到文案创作）
            if new_status == 'review_failed':
                nodes_to_reset = ['compliance_checker', 'chief_editor', 'human_review', 'visual_designer', 'finalize']
                await ws_manager.send_nodes_reset(task_id, nodes_to_reset)

        return {
            'editor_feedback': feedback,  # 改为直接存储字典，方便路由函数使用
            'status': new_status,
            'iteration_count': iteration_count + 1,
            'messages': [f'✅ 终审完成，评分：{quality_score}，状态：{new_status}']
        }

    except Exception as e:
        # 捕获所有未预期的错误
        error_detail = log_error('chief_editor', e, state)
        error_history = add_error_to_history(state, 'chief_editor', e)

        return {
            'status': 'failed',
            'error': f'终审评估失败：{str(e)}',
            'error_detail': error_detail,
            'error_history': error_history,
            'messages': [f'❌ 终审评估失败：{str(e)}']
        }


async def human_review_node(state: GraphState) -> Dict:
    """人工审核节点 - 等待人工确认

    注意：此节点在 interrupt_after 中，执行完后会自动中断
    - 第一次执行：返回等待状态，工作流中断
    - 第二次执行（从 API 恢复）：检查 human_decision，继续流程
    """

    task_id = _get_task_id(state)
    # 发送节点开始信号
    if task_id:
        await ws_manager.send_node_start(task_id, "human_review", "人工审核")

    try:
        # ===== 数据验证 =====
        editor_feedback = state.get('editor_feedback', {})
        if not editor_feedback:
            return {
                'status': 'failed',
                'error': '缺少编辑反馈，无法进行人工审核',
                'messages': ['❌ 人工审核失败：编辑反馈缺失']
            }

        score = editor_feedback.get('score', 0)
        title = state.get('selected_title', '')  # 获取标题

        # 检查是否已经有人工决策
        human_decision = state.get('human_decision')

        # 发送节点完成信号
        if task_id:
            await ws_manager.send_node_complete(task_id, "human_review", "人工审核", {
                "score": score,
                "status": "waiting_human_review" if not human_decision else "human_reviewed",
                "title": title  # 添加标题字段
            })

        if not human_decision:
            # 第一次进入此节点，返回等待状态
            # 工作流会在此节点后中断（因为在 interrupt_after 中）
            logger.info(f"⏸️ 内容评分 {score}，等待人工审核确认（工作流将中断）")
            return {
                'status': 'waiting_human_review',
                'messages': [f'⏸️ 内容评分 {score}，等待人工审核确认']
            }
        else:
            # 已有人工决策，继续流程
            logger.info(f"✅ 人工审核完成: {human_decision}")
            return {
                'status': 'human_reviewed',
                'messages': [f'✅ 人工审核完成: {human_decision}']
            }

    except Exception as e:
        # 捕获所有未预期的错误
        error_detail = log_error('human_review', e, state)
        error_history = add_error_to_history(state, 'human_review', e)

        return {
            'status': 'failed',
            'error': f'人工审核节点失败：{str(e)}',
            'error_detail': error_detail,
            'error_history': error_history,
            'messages': [f'❌ 人工审核节点失败：{str(e)}']
        }


async def finalize_node(state: GraphState) -> Dict:
    """最终输出节点 - 整理最终内容"""
    task_id = _get_task_id(state)

    # 发送节点开始信号
    if task_id:
        await ws_manager.send_node_start(task_id, "finalize", "最终输出")

    try:
        # ===== 数据验证 =====
        draft_content = state.get('draft_content')
        if not draft_content:
            return {
                'status': 'failed',
                'error': '缺少草稿内容，无法生成最终输出',
                'messages': ['❌ 最终输出失败：未找到草稿内容']
            }

        selected_title = state.get('selected_title')
        if not selected_title:
            return {
                'status': 'failed',
                'error': '缺少标题，无法生成最终输出',
                'messages': ['❌ 最终输出失败：未找到标题']
            }

        keywords = state.get('keywords')
        if not keywords:
            return {
                'status': 'failed',
                'error': '缺少关键词，无法生成最终输出',
                'messages': ['❌ 最终输出失败：关键词缺失']
            }

        iteration_count = state.get('iteration_count', 0)
        editor_feedback = state.get('editor_feedback', {})

        final_post = {
            'title': selected_title,
            'content': draft_content,
            'tags': extract_tags(draft_content),
            'image_prompts': state.get('image_prompts', []),
            'image_urls': state.get('image_urls', []),
            'image_local_paths': state.get('image_local_paths', []),  # 新增：本地路径
            'quality_score': editor_feedback.get('quality_score', 0),
            'iteration_count': iteration_count,
            'keywords': keywords
        }

        # ===== 保存笔记到文件系统 =====
        try:
            from pathlib import Path
            import json
            from datetime import datetime

            # 创建保存目录：data/outputs/{关键词}_{task_id}/
            main_keyword = keywords[0] if keywords else "content"
            output_dir = Path(__file__).parent.parent.parent / "data" / "outputs" / f"{main_keyword}_{task_id}"
            output_dir.mkdir(parents=True, exist_ok=True)

            # 保存笔记内容为 JSON
            note_file = output_dir / "note.json"
            with open(note_file, 'w', encoding='utf-8') as f:
                json.dump(final_post, f, ensure_ascii=False, indent=2)

            # 保存笔记内容为 TXT（方便阅读）
            txt_file = output_dir / "note.txt"
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(f"标题：\n{selected_title}\n\n")
                f.write(f"正文：\n{draft_content}\n\n")
                f.write(f"标签：\n{' '.join(['#' + tag for tag in final_post['tags']])}\n\n")
                f.write(f"质量评分：{final_post['quality_score']}\n")
                f.write(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

            # 图片已经在 visual_designer_node 中直接保存到目标目录，无需复制
            logger.info(f"✅ 笔记已保存到: {output_dir}")
            final_post['saved_path'] = str(output_dir)

        except Exception as save_error:
            logger.warning(f"⚠️ 笔记保存失败: {save_error}")
            # 保存失败不影响整体流程

        # 发送节点完成信号（发送完整的 final_post）
        # 将本地图片路径转换为前端可访问的 URL（/outputs/...）
        local_image_urls = []
        for local_path in final_post.get('image_local_paths', []):
            try:
                p = Path(local_path)
                # 找到 outputs 目录之后的相对路径
                parts = p.parts
                outputs_idx = next((i for i, part in enumerate(parts) if part == 'outputs'), None)
                if outputs_idx is not None:
                    relative = '/'.join(parts[outputs_idx + 1:])
                    local_image_urls.append(f"/outputs/{relative}")
            except Exception:
                pass

        # 优先使用在线 URL（直接可访问），本地路径作为备选
        display_images = final_post['image_urls'] if final_post['image_urls'] else local_image_urls

        if task_id:
            await ws_manager.send_node_complete(task_id, "finalize", "最终输出", {
                "title": final_post['title'],
                "content": final_post['content'],
                "tags": final_post['tags'],
                "images": display_images,
                "local_images": local_image_urls,
                "saved_path": final_post.get('saved_path', '')
            })

        return {
            'final_post': final_post,
            'status': 'completed',
            'messages': [
                '🎉 内容生成完成！',
                f'📁 笔记已保存到: {final_post.get("saved_path", "未保存")}'
            ]
        }

    except Exception as e:
        # 捕获所有未预期的错误
        error_detail = log_error('finalize', e, state)
        error_history = add_error_to_history(state, 'finalize', e)

        return {
            'status': 'failed',
            'error': f'最终输出失败：{str(e)}',
            'error_detail': error_detail,
            'error_history': error_history,
            'messages': [f'❌ 最终输出失败：{str(e)}']
        }
