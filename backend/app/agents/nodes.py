"""
LangGraph Agent 节点实现
"""
from typing import Dict
from pathlib import Path
import json
from .state import GraphState
from .tools import (
    calculate_heat_score,
    check_sensitive_words,
    extract_title_pattern,
    format_content_with_emoji,
    extract_tags,
    calculate_quality_score,
    parse_title_candidates,
    build_image_prompt_from_json,
    build_default_titles,
    download_images_to_outputs,
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


async def _emit_node_failure(task_id: str, node_id: str, node_name: str, error_msg: str):
    """统一发送节点失败信号，确保前端能将节点标记为 error 状态"""
    if task_id:
        await ws_manager.send_node_error(task_id, node_id, node_name, error_msg)


async def _emit_node_complete(task_id: str, node_id: str, node_name: str, output: dict = None):
    """统一发送节点完成信号（适用于成功与降级路径）"""
    if task_id:
        await ws_manager.send_node_complete(task_id, node_id, node_name, output or {})


async def _emit_node_start(task_id: str, node_id: str, node_name: str):
    """统一发送节点开始信号"""
    if task_id:
        await ws_manager.send_node_start(task_id, node_id, node_name)


# 当回退到 copywriter 时需要在前端重置的下游节点
# 用作常量，避免和前端逻辑漂移
_NODES_TO_RESET_AFTER_COPYWRITER = [
    'compliance_checker', 'chief_editor', 'human_review', 'visual_designer', 'finalize'
]


async def _emit_nodes_reset_after_copywriter(task_id: str):
    """当工作流回退到 copywriter 时，发送下游节点重置消息"""
    if task_id:
        await ws_manager.send_nodes_reset(task_id, _NODES_TO_RESET_AFTER_COPYWRITER)


# ===== 数据层 Agent =====

async def trend_collector_node(state: GraphState) -> Dict:
    """热点采集员 - 抓取小红书热榜数据"""
    task_id = _get_task_id(state)
    logger.info(f"🔍 [trend_collector] task_id = {task_id}")

    # 发送节点开始信号
    if task_id:
        logger.debug(f"📤 [trend_collector] 发送 node_start 到 task_id={task_id}")
        await _emit_node_start(task_id, "trend_collector", "热点采集")
    else:
        logger.warning(f"⚠️ [trend_collector] task_id 为空，无法发送 WebSocket 消息")

    try:
        # ===== 数据验证 =====
        keywords = state.get('keywords')
        if not keywords or len(keywords) == 0:
            await _emit_node_failure(task_id, "trend_collector", "热点采集", '缺少关键词，无法采集数据')
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
                    await _emit_node_failure(task_id, "trend_collector", "热点采集", '数据采集失败：数据库无数据且爬虫失败')
                    return {
                        'status': 'failed',
                        'error': '数据采集失败：数据库无数据且爬虫失败',
                        'raw_trends': [],
                        'messages': messages + ['❌ 无法获取任何数据，请检查网络连接或稍后重试']
                    }

                messages.append(f'⚠️ 使用现有数据，共 {final_count} 条笔记')
                # 降级也算"完成"，要发送 node_complete 让前端节点变绿（带降级标记）
                degraded_titles = [n['title'] for n in all_notes]
                await _emit_node_complete(task_id, "trend_collector", "热点采集", {
                    "notes_count": final_count,
                    "titles": degraded_titles,
                    "degraded": True
                })
                return {
                    'raw_trends': all_notes,
                    'status': 'degraded',
                    'degraded_nodes': add_degraded_node(state, 'trend_collector'),
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
            await _emit_node_failure(task_id, "trend_collector", "热点采集", '数据采集失败：未获取到任何笔记')
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
        await _emit_node_complete(task_id, "trend_collector", "热点采集", {
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

        await _emit_node_failure(task_id, "trend_collector", "热点采集", f'热点采集失败：{str(e)}')

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
    await _emit_node_start(task_id, "trend_analyzer", "热点分析")

    try:
        raw_trends = state.get('raw_trends') or []
        keywords = state.get('keywords') or []

        if not raw_trends:
            # 没有数据无法分析，标记为失败让工作流终止
            await _emit_node_failure(task_id, "trend_analyzer", "热点分析", '没有热点数据可供分析')
            return {
                'status': 'failed',
                'error': '没有热点数据可供分析',
                'analyzed_templates': [],
                'messages': ['❌ 热点分析失败：没有热点数据可供分析']
            }

        # 基础数据处理：计算热度评分和提取模式
        basic_templates = []
        for item in raw_trends:
            heat_score = calculate_heat_score(item)
            title_pattern = extract_title_pattern(item.get('title', ''))

            template = {
                'title': item.get('title', ''),
                'content': item.get('content', ''),
                'pattern': title_pattern,
                'heat_score': heat_score,
                'tags': item.get('tags', []) or [],
                'engagement': {
                    'likes': item.get('likes', 0),
                    'favorites': item.get('favorites', 0),
                    'comments': item.get('comments', 0)
                },
                'media_summary': item.get('media_summary') or '',
                'media_description': item.get('media_description') or '',
            }
            basic_templates.append(template)

        # 按热度排序，进行深度分析
        basic_templates.sort(key=lambda x: x['heat_score'], reverse=True)
        top_notes = basic_templates
        # Top-K 爆款原文参考（供下游 copywriter / title_lab 做 few-shot）
        top_references = basic_templates[:3]

        # 默认降级用的 llm_analysis
        default_llm_analysis = {
            "pain_points": [],
            "emotion_triggers": [],
            "hot_tags": [],
            "visual_patterns": [],
            "key_insights": "LLM 分析未生效，使用基础分析"
        }

        # 使用 LLM 进行深度分析
        try:
            # 构建分析提示词（包含媒体总结）
            notes_summary = "\n\n".join([
                f"【笔记{i+1}】\n"
                f"标题：{note['title']}\n"
                f"内容：{note['content']}\n"
                f"媒体总结：{note.get('media_summary', '无')}\n"
                f"标签：{', '.join(note['tags'])}\n"
                f"互动数据：👍{note['engagement']['likes']} 💾{note['engagement']['favorites']} 💬{note['engagement']['comments']}"
                for i, note in enumerate(top_notes)
            ])

            system_prompt = """你是一位资深的小红书内容分析师，擅长从爆款笔记中提取成功模式。

你的任务是分析这些高互动笔记，提取出可复用的爆款特征。

请从以下维度进行分析：
1. **话题切入点**：用户关注的痛点、需求、场景
2. **情绪共鸣点**：引发共鸣的情绪类型（焦虑、好奇、惊喜等）
3. **标签策略**：高频标签、标签组合模式
4. **视觉表达模式**：图片/视频的呈现方式、构图风格、视觉元素（基于媒体总结分析）

请以 JSON 格式输出分析结果，格式如下：
{
  "pain_points": ["时间不够", "效率低下", "不知道怎么开始"],
  "emotion_triggers": ["焦虑", "好奇", "惊喜"],
  "hot_tags": ["干货分享", "实用技巧", "新手必看"],
  "visual_patterns": ["对比图", "步骤拆解", "实拍场景", "数据可视化"],
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
                temperature=0.3,
                max_tokens=2000,
                model=settings.LLM_MODEL
            )

            # 解析 LLM 返回的 JSON
            try:
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', llm_response, re.DOTALL)
                if json_match:
                    llm_analysis = json.loads(json_match.group(1))
                else:
                    llm_analysis = json.loads(llm_response)
            except json.JSONDecodeError:
                # JSON 解析失败，记录降级
                log_error('trend_analyzer_parse', ValueError('LLM 返回 JSON 解析失败'), state)
                llm_analysis = dict(default_llm_analysis)
                llm_analysis['key_insights'] = "LLM 分析结果解析失败"

            # 发送节点完成信号
            await _emit_node_complete(task_id, "trend_analyzer", "热点分析", {
                "template_count": len(basic_templates),
                "key_insights": llm_analysis.get("key_insights", "")
            })

            return {
                'analyzed_templates': basic_templates,
                'llm_analysis': llm_analysis,
                'top_references': top_references,
                'messages': [
                    f'✅ 热点分析完成，共分析 {len(basic_templates)} 个模板',
                    f'📊 LLM 深度分析：{llm_analysis.get("key_insights", "已完成")[:50]}...'
                ]
            }

        except Exception as e:
            # LLM 调用失败，降级到基础分析（仍标记为完成，因为有基础模板可用）
            log_error('trend_analyzer_llm', e, state)
            error_history = add_error_to_history(state, 'trend_analyzer', e)
            degraded_nodes = add_degraded_node(state, 'trend_analyzer')

            await _emit_node_complete(task_id, "trend_analyzer", "热点分析", {
                "template_count": len(basic_templates),
                "key_insights": "LLM 失败，使用基础分析",
                "degraded": True
            })

            return {
                'analyzed_templates': basic_templates,
                'llm_analysis': default_llm_analysis,
                'top_references': top_references,
                'status': 'degraded',
                'error_history': error_history,
                'degraded_nodes': degraded_nodes,
                'messages': [
                    f'✅ 热点分析完成（基础模式），提取 {len(basic_templates)} 个模板',
                    f'⚠️ LLM 分析失败: {str(e)}'
                ]
            }

    except Exception as e:
        # 顶层兜底：节点本身崩溃
        error_detail = log_error('trend_analyzer', e, state)
        error_history = add_error_to_history(state, 'trend_analyzer', e)

        await _emit_node_failure(task_id, "trend_analyzer", "热点分析", f'热点分析失败：{str(e)}')

        return {
            'status': 'failed',
            'error': f'热点分析失败：{str(e)}',
            'error_detail': error_detail,
            'error_history': error_history,
            'analyzed_templates': [],
            'messages': [f'❌ 热点分析失败：{str(e)}']
        }


# ===== 内容生产层 Agent =====

async def strategist_node(state: GraphState) -> Dict:
    """选题策划师 - 确定内容策略（利用 LLM 分析结果）"""
    task_id = _get_task_id(state)

    # 发送节点开始信号
    await _emit_node_start(task_id, "strategist", "选题策划")

    try:
        # ===== 数据验证 =====
        keywords = state.get('keywords')
        if not keywords or len(keywords) == 0:
            await _emit_node_failure(task_id, "strategist", "选题策划", '缺少关键词，无法制定内容策略')
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
        emotion_triggers = llm_analysis.get('emotion_triggers', ['实用', '干货', '避坑'])
        key_insights = llm_analysis.get('key_insights', '')
        hot_tags = llm_analysis.get('hot_tags', [])
        visual_patterns = llm_analysis.get('visual_patterns', [])

        # 构建策略
        strategy = {
            'persona': persona,
            'emotion_triggers': emotion_triggers if emotion_triggers else ['实用', '干货', '避坑'],
            'keywords': keywords,
            'keywords_str': keywords_str,
            'pain_points': pain_points if pain_points else [],
            'llm_insights': key_insights if key_insights else '',
            'hot_tags': hot_tags if hot_tags else [],
            'visual_patterns': visual_patterns if visual_patterns else []  # 透传视觉模式给下游节点
        }

        # 发送节点完成信号
        await _emit_node_complete(task_id, "strategist", "选题策划", {
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

        await _emit_node_failure(task_id, "strategist", "选题策划", f'选题策划失败：{str(e)}')

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
    await _emit_node_start(task_id, "title_lab", "标题生成")

    # ===== 稳健性校验 =====
    # keywords 是关键依赖：缺失直接 failed，下游无法使用兜底标题
    keywords = state.get('keywords') or []
    if not keywords:
        await _emit_node_failure(task_id, "title_lab", "标题生成", '缺少关键词，无法生成标题')
        return {
            'status': 'failed',
            'error': '缺少关键词，无法生成标题',
            'messages': ['❌ 标题生成失败：未提供关键词']
        }

    # strategy 是软依赖：缺失则用最小可用上下文降级
    strategy = state.get('strategy')
    strategy_missing = not strategy
    if strategy_missing:
        log_error('title_lab_strategy_missing',
                  ValueError('state.strategy 为空，使用关键词降级生成标题'), state)
        strategy = {
            'persona': '专业分享者',
            'pain_points': [],
            'llm_insights': '',
            'hot_tags': [],
            'keywords_str': '、'.join(keywords),
        }

    # 使用主关键词（第一个）
    main_keyword = keywords[0]
    keywords_str = strategy.get('keywords_str') or '、'.join(keywords)

    # 从策略中获取信息
    pain_points = strategy.get('pain_points', []) or []
    llm_insights = strategy.get('llm_insights', '') or ''
    hot_tags = strategy.get('hot_tags', []) or []

    try:
        # 构建标题生成提示词
        pain_points_desc = "；".join(pain_points) if pain_points else "效率低、不知道怎么做、容易出错"
        llm_insights_desc = llm_insights if llm_insights else "无"
        hot_tags_desc = "、".join(hot_tags) if hot_tags else "无"

        # ===== 构建 Top-K 爆款标题参考（few-shot） =====
        top_references = state.get('top_references', [])
        title_references_section = ""
        if top_references:
            ref_titles = []
            for i, ref in enumerate(top_references, 1):
                t = ref.get('title', '').strip()
                if not t:
                    continue
                eng = ref.get('engagement', {})
                ref_titles.append(
                    f"{i}. {t}（👍{eng.get('likes', 0)} 💾{eng.get('favorites', 0)}）"
                )
            if ref_titles:
                title_references_section = (
                    "\n\n爆款标题参考（仅学习其结构与情绪钩子，禁止照抄）：\n"
                    + "\n".join(ref_titles)
                )

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

⚠️ 爆款参考使用规则：
- 如果用户消息中包含"爆款标题参考"，仅用于学习其结构、情绪钩子和切入角度
- **严禁照抄原标题用词或句式**，必须自己创作

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
爆款笔记热门标签：{hot_tags_desc}{title_references_section}

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

            title_candidates = build_default_titles(main_keyword)

            # 发送节点完成信号
            await _emit_node_complete(task_id, "title_lab", "标题生成", {
                "titles": title_candidates,
                "degraded": True
            })

            result = {
                'title_candidates': title_candidates,
                'status': 'degraded',
                'error_history': error_history,
                'degraded_nodes': degraded_nodes,
                'messages': [
                    f'✅ 标题生成完成（降级模式），共 {len(title_candidates)} 个候选标题',
                    f'⚠️ LLM 返回标题不足，使用默认标题'
                ]
            }
            if strategy_missing:
                result['strategy'] = strategy
                result['messages'].append('⚠️ strategy 缺失，已使用关键词兜底策略')
            return result

        # 发送节点完成信号
        await _emit_node_complete(task_id, "title_lab", "标题生成", {
            "titles": title_candidates
        })

        result = {
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
        if strategy_missing:
            # 把兜底 strategy 写回 state，避免下游 copywriter 再次空读
            result['strategy'] = strategy
            result['status'] = 'degraded'
            result['error_history'] = add_error_to_history(state, 'title_lab', ValueError('strategy 缺失，使用兜底'))
            result['degraded_nodes'] = add_degraded_node(state, 'title_lab')
            result['messages'].append('⚠️ strategy 缺失，已使用关键词兜底策略')
        return result

    except Exception as e:
        # LLM 调用失败，使用降级方案（默认标题）
        log_error('title_lab', e, state)
        error_history = add_error_to_history(state, 'title_lab', e)
        degraded_nodes = add_degraded_node(state, 'title_lab')

        title_candidates = build_default_titles(main_keyword)

        # 发送节点完成信号
        await _emit_node_complete(task_id, "title_lab", "标题生成", {
            "titles": title_candidates,
            "degraded": True
        })

        result = {
            'title_candidates': title_candidates,
            'status': 'degraded',
            'error_history': error_history,
            'degraded_nodes': degraded_nodes,
            'messages': [
                f'✅ 标题生成完成（降级模式），共 {len(title_candidates)} 个候选标题',
                f'⚠️ LLM 生成失败，使用默认标题: {str(e)}'
            ]
        }
        if strategy_missing:
            result['strategy'] = strategy
            result['messages'].append('⚠️ strategy 缺失，已使用关键词兜底策略')
        return result


async def copywriter_node(state: GraphState) -> Dict:
    """爆款写手 - 使用 LLM 生成正文内容"""
    task_id = _get_task_id(state)

    # 发送节点开始信号
    await _emit_node_start(task_id, "copywriter", "文案创作")

    try:
        # 验证必需字段
        keywords = state.get('keywords')
        if not keywords or len(keywords) == 0:
            await _emit_node_failure(task_id, "copywriter", "文案创作", '缺少关键词，无法生成内容')
            return {
                'status': 'failed',
                'error': '缺少关键词，无法生成内容',
                'messages': ['❌ 文案生成失败：未提供关键词']
            }

        strategy = state.get('strategy')
        if not strategy:
            await _emit_node_failure(task_id, "copywriter", "文案创作", '缺少选题策略，无法生成内容')
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
                await _emit_node_failure(task_id, "copywriter", "文案创作", '未找到可用的标题')
                return {
                    'status': 'failed',
                    'error': '未找到可用的标题',
                    'messages': ['❌ 文案生成失败：未找到可用的标题，请先生成标题候选']
                }
            selected_title = title_candidates[0]

        # ===== 获取数据 =====
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
        emotion_triggers = strategy.get('emotion_triggers', ['实用', '干货', '避坑'])

        pain_points_desc = "\n".join([f"- {p}" for p in pain_points]) if pain_points else "- 不知道怎么开始\n- 容易出错\n- 效率低下"
        emotion_triggers_desc = "、".join(emotion_triggers) if emotion_triggers else "实用、干货、避坑"

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
            emotion_triggers_list = emotion_triggers if isinstance(emotion_triggers, list) else []
            
            # 召回 5 个候选；当 top1/top2 区分度不足（gap < 0.05）时自动触发 LLM rerank
            retrieved_styles = await style_retrieval_service.retrieve_style_with_rerank(
                keywords=keywords,
                persona=persona,
                pain_points=pain_points_list,
                emotion_triggers=emotion_triggers_list,
                top_k=1,
                recall_k=5,
                rerank_gap_threshold=0.05,
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

        # ===== 构建 Top-K 爆款原文参考（few-shot） =====
        top_references = state.get('top_references', [])
        references_section = ""
        if top_references:
            ref_blocks = []
            for i, ref in enumerate(top_references, 1):
                ref_title = ref.get('title', '')
                ref_content = (ref.get('content') or '').strip()
                # 控制单篇截断，避免 token 过多
                if len(ref_content) > 300:
                    ref_content = ref_content[:300] + '...'
                ref_media = (ref.get('media_summary') or '').strip()
                if len(ref_media) > 100:
                    ref_media = ref_media[:100] + '...'
                eng = ref.get('engagement', {})

                block_lines = [
                    f"【爆款参考{i}】",
                    f"标题：{ref_title}",
                    f"正文节选：{ref_content}",
                ]
                if ref_media:
                    block_lines.append(f"媒体表达：{ref_media}")
                block_lines.append(
                    f"互动数据：👍{eng.get('likes', 0)} 💾{eng.get('favorites', 0)} 💬{eng.get('comments', 0)}"
                )
                ref_blocks.append("\n".join(block_lines))

            references_section = (
                "\n\n以下是该主题下的爆款笔记参考，用于学习它们的写作风格、叙事节奏和情绪表达：\n\n"
                + "\n\n".join(ref_blocks)
                + "\n\n⚠️ 重要：仅参考其表达感觉与节奏，不要直接照抄原文用词或结构。"
            )

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

⚠️ 爆款参考使用规则（重要）：
- 如果用户消息中包含"爆款参考"，仅用于学习其写作风格、叙事节奏、情绪表达
- **严禁照抄原文用词、句式或结构**，必须用自己的表达重新创作
- 提取参考笔记的"感觉"（语气、切入点、节奏），而不是"内容"

请写一篇自然流畅的小红书内容。"""

        user_prompt = f"""标题：{selected_title}

关键词：{keywords_str}
人设角度：{strategy.get('persona', '专业分享者')}
情绪点：{emotion_triggers_desc}

用户痛点：
{pain_points_desc}

{style_guidance}{references_section}{feedback_section}

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
        await _emit_node_complete(task_id, "copywriter", "文案创作", {
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

        await _emit_node_failure(task_id, "copywriter", "文案创作", f'文案生成失败：{str(e)}')

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
    await _emit_node_start(task_id, "visual_designer", "视觉设计")

    try:
        # ===== 数据验证 =====
        keywords = state.get('keywords')
        if not keywords or len(keywords) == 0:
            await _emit_node_failure(task_id, "visual_designer", "视觉设计", '缺少关键词，无法生成图片')
            return {
                'status': 'failed',
                'error': '缺少关键词，无法生成图片',
                'messages': ['❌ 图片生成失败：未提供关键词']
            }

        title = state.get('selected_title', '')
        draft_content = state.get('draft_content', '')
        strategy = state.get('strategy', {})
        visual_patterns = strategy.get('visual_patterns', [])

        # 使用主关键词（第一个）
        keywords_str = "、".join(keywords)

        # ===== 第一步：使用 LLM 生成结构化的图片提示词 =====
        # 通过结构化 JSON 输出强制 LLM 给出具体可视化的细节，避免泛泛的形容词
        system_prompt = """你是一位专业的小红书视觉设计师。你的任务是为给定的笔记内容生成一份**结构化、可落地**的图片描述。

核心要求：
1. **从正文中提取具体物体**：必须从正文里找出 3-6 个可以画出来的具体物品/场景，不要用宽泛的概念词（如"学习用品"、"美食"、"生活方式"）
2. **场景细节具体化**：写清楚"什么物品 + 怎么摆放 + 在什么环境里"，不要写"一个 XX 的场景"
3. **风格必须从下方非写实白名单中选择一个**（详见"弱模型适配规则"）
4. **色彩用具体色名**：写明 3-5 个具体颜色名称（中文+色名），不要写"温暖色调"这种模糊描述
5. **光线要写清来源、方向、色温**：哪个方向射来 / 是直射还是漫反射 / 暖色还是冷色
6. **构图必须简单化**：避免复杂透视

⚠️ 严禁使用以下空话：高质量、精致、温馨、治愈、氛围感、有质感、唯美、文艺、小清新（这些词无法转化为具体画面）

⚠️ 严禁套用任何固定题材：你必须紧扣【正文】里出现的物品和场景来构造画面。如果正文讲的是健身就画健身相关物品，讲护肤就画护肤相关物品，以此类推。

⚠️ **弱模型适配规则（最重要！）**：
当前生图模型能力有限，对真实场景容易出 bug（畸形手指、伪文字、扭曲人脸、复杂透视错乱）。请严格遵守以下规则：

【风格白名单】style 字段必须从下列**非写实风格**中选择一个：
- 扁平化矢量插画（flat illustration）
- 简约线条插画（minimal line art）
- 水彩手绘（watercolor）
- 童趣手绘风（hand-drawn cute）
- 国风工笔/水墨（Chinese ink wash）
- 像素风（pixel art）
- 几何抽象（geometric abstract）
- 拼贴艺术（collage art）

【style 字段禁用项】严禁出现：摄影、半写实、写实、photorealistic、4K、电影感、cinematic、超写实、HDR

【主体规则】
- subject 必须是**物品 / 抽象图形 / 风景**，**严禁画人**（包括：人物、人脸、肖像、人体、半身像、剪影、背影）
- 严禁画**动物特写、宠物**（毛发难以处理）
- 严禁出现**手部、手指**的特写或近景
- 严禁画**文字、汉字、英文、招牌、书页文字、logo**

【构图规则】
- 严禁要求复杂透视（建筑透视、街景透视、深景纵深）
- 严禁多人物互动场景、人群场景
- 主体保持单一或少量（≤3 个主体）

【色彩规则】
- color_palette 用 3-5 个低饱和度色块（莫兰迪色系优先）
- 严禁要求复杂渐变、玻璃反射、镜面反射、液体反光

输出格式：严格按以下 JSON 输出。每个字段必须紧扣正文具体内容，**禁止照抄下方占位符里的任何词语**：
```json
{
  "subject": "<画面核心主体的描述：必须是物品/抽象图形/风景，严禁画人或动物，写明物体的形态、状态、相对位置>",
  "scene": "<场景环境的具体描述：包括位置、周围物品、桌面/地面/背景的材质和颜色，避免复杂透视>",
  "composition": "<构图方式 + 主体在画面中的位置 + 留白比例>",
  "lighting": "<光线来源（自然光/灯光）+ 方向 + 强度（直射/漫反射）+ 色温（冷/暖/中性），优先柔和漫反射>",
  "color_palette": "<3-5 个具体颜色名称（建议莫兰迪色系），用顿号分隔，低饱和度>",
  "style": "<必须从非写实风格白名单中选择一个，并简要说明视觉调性>",
  "mood": "<1-3 个情绪关键词，紧扣正文情感>",
  "texture_details": "<画面中重点物体的材质与质感细节，避免玻璃/镜面/液体反射>"
}
```

不要添加任何解释或前缀，直接输出 JSON。"""

        # 构建爆款视觉模式参考（如果有）
        visual_pattern_hint = ""
        if visual_patterns:
            visual_pattern_hint = (
                f"\n【爆款视觉模式参考】{', '.join(visual_patterns)}"
                f"\n请在 style 或 composition 字段中体现上述模式（但不要照搬）。"
            )

        user_prompt = f"""请为以下小红书笔记生成配图描述：

【标题】{title}

【正文】{draft_content[:800]}{'...' if len(draft_content) > 800 else ''}

【关键词】{keywords_str}{visual_pattern_hint}

要求：
1. **subject 和 scene 必须使用正文里实际出现的物品/场景**，不要凭空想象题材
2. 八个字段全部填充，每个字段都要具体到能让画师/AI直接动手画
3. 避免文字、人脸、品牌logo等元素
4. 色彩柔和自然，饱和度适中

直接输出 JSON："""

        # 调用 LLM 生成提示词
        llm_response = await llm_client.chat_with_system(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.85,  # 略高，鼓励具体细节的多样性
            max_tokens=1500,
            model=settings.LLM_MODEL,
        )

        # ===== 解析 JSON 并拼装提示词 =====
        optimized_prompt = build_image_prompt_from_json(llm_response)

        # 负面提示词（弱模型适配：堆叠所有易翻车元素）
        negative_prompt = (
            # 人物相关（弱模型最易翻车）
            "人, 人物, 人脸, 肖像, 人体, 半身像, 全身, 剪影, 背影, "
            "眼睛, 嘴巴, 鼻子, 牙齿, 表情, "
            "手, 手指, 手部特写, 脚, 脚趾, 四肢, "
            # 动物相关
            "动物, 宠物, 毛发, 皮毛, 羽毛, 动物面部, "
            # 文字相关
            "文字, 汉字, 中文, 英文, 字母, 数字, 招牌, 书页文字, 标题文字, "
            "水印, 标志, logo, 品牌标识, 印章, 二维码, "
            # 反射/液体（光影易混乱）
            "玻璃反射, 镜面, 镜子, 镜像, 水面倒影, 液体反光, 水珠, "
            # 复杂场景（透视易错）
            "复杂建筑, 街景透视, 城市鸟瞰, 复杂机械, 齿轮, 电路, "
            "人群, 多人物, 拥挤场景, "
            # 真实感关键词（强行拉回到风格化）
            "photorealistic, 超写实, 写实摄影, photography, realistic, "
            "4K, 8K, HDR, 电影感, cinematic, 真实质感, 真实皮肤, "
            # 通用质量缺陷
            "低质量, 模糊, 噪点, 颗粒感, 失焦, "
            "变形, 畸形, 多余肢体, 比例错误, 解剖错误, "
            "过度饱和, 过度鲜艳, 颜色失真, 色带, 色偏"
        )


        # ===== 第二步：调用图片生成 API =====
        from app.services.image_generation_service import image_generation_service

        try:
            # 弱模型适配：在末尾追加强风格化锚点，把整体推离写实区间
            # 这些 token 被生图模型识别为"非真实图像"信号，能稳定避免畸形手指/伪文字等问题
            full_prompt = (
                f"{optimized_prompt}；"
                "整体小红书风格，画面干净不杂乱，扁平插画质感，无文字，无人物，低饱和度配色"
            )

            image_urls = await image_generation_service.generate_image(
                prompt=full_prompt,
                negative_prompt=negative_prompt,
                size=settings.IMAGE_SIZE,
                n=settings.IMAGE_COUNT
            )

            # ===== 第三步：下载图片到目标目录 =====
            local_paths = await download_images_to_outputs(image_urls, keywords, task_id)

            # 发送节点完成信号
            await _emit_node_complete(task_id, "visual_designer", "视觉设计", {
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
            # 图片生成失败，但提示词生成成功 → 降级（图片是非关键资产，可没有图）
            logger.warning(f"⚠️ 图片生成失败: {img_error}")
            error_history = add_error_to_history(state, 'visual_designer', img_error)
            degraded_nodes = add_degraded_node(state, 'visual_designer')

            await _emit_node_complete(task_id, "visual_designer", "视觉设计", {
                "image_prompt": optimized_prompt,
                "image_count": 0,
                "degraded": True
            })

            return {
                'image_prompts': [optimized_prompt],
                'image_urls': [],
                'image_local_paths': [],
                'status': 'degraded',
                'error_history': error_history,
                'degraded_nodes': degraded_nodes,
                'messages': [
                    f'✅ 图片提示词生成完成',
                    f'⚠️ 图片生成失败: {str(img_error)}',
                    f'💡 提示词: {optimized_prompt}'
                ]
            }

    except Exception as e:
        # 顶层异常：提示词构建/调用失败，使用默认提示词降级
        log_error('visual_designer', e, state)
        error_history = add_error_to_history(state, 'visual_designer', e)
        degraded_nodes = add_degraded_node(state, 'visual_designer')

        # 尝试使用默认提示词生成图片
        default_prompt = f"小红书风格封面图，主题：{keywords_str if keywords else '生活分享'}，简约清新，温暖色调，卡通风格"

        try:
            from app.services.image_generation_service import image_generation_service

            image_urls = await image_generation_service.generate_image(
                prompt=default_prompt,
                size=settings.IMAGE_SIZE,
                n=1
            )

            # 下载图片到目标目录（失败自动返回空列表）
            local_paths = await download_images_to_outputs(image_urls, keywords, task_id)
            
            await _emit_node_complete(task_id, "visual_designer", "视觉设计", {
                "image_prompt": default_prompt,
                "image_count": len(image_urls),
                "degraded": True
            })

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
            # 完全失败：提示词和图片都没有，但视觉是非关键路径，仍降级前进，让 finalize 处理空图
            log_error('visual_designer_fallback', fallback_error, state)
            error_history = add_error_to_history(state, 'visual_designer', fallback_error)

            await _emit_node_complete(task_id, "visual_designer", "视觉设计", {
                "image_prompt": default_prompt,
                "image_count": 0,
                "degraded": True
            })

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
    await _emit_node_start(task_id, "compliance_checker", "合规检查")

    try:
        # ===== 数据验证 =====
        draft_content = state.get('draft_content')
        if not draft_content:
            await _emit_node_failure(task_id, "compliance_checker", "合规检查", '缺少草稿内容，无法进行合规检查')
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
        await _emit_node_complete(task_id, "compliance_checker", "合规检查", {
            "passed": compliance_report['passed']
        })

        # 如果合规不通过，发送节点重置消息（将回退到文案创作）
        if not compliance_report['passed']:
            await _emit_nodes_reset_after_copywriter(task_id)

        return {
            'compliance_report': compliance_report,
            'status': 'compliance_passed' if compliance_report['passed'] else 'compliance_failed',
            'messages': [f'✅ 合规检查完成，风险等级：{compliance_report["overall_risk"]}']
        }

    except Exception as e:
        # 捕获所有未预期的错误
        log_error('compliance_checker', e, state)
        error_history = add_error_to_history(state, 'compliance_checker', e)

        # 合规检查失败，使用降级方案（跳过检查但警告），仍发 node_complete 让前端节点变绿
        degraded_nodes = add_degraded_node(state, 'compliance_checker')

        await _emit_node_complete(task_id, "compliance_checker", "合规检查", {
            "passed": True,
            "degraded": True
        })

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
    await _emit_node_start(task_id, "chief_editor", "终审编辑")

    try:
        # ===== 数据验证 =====
        draft_content = state.get('draft_content')
        if not draft_content:
            await _emit_node_failure(task_id, "chief_editor", "终审编辑", '缺少草稿内容，无法进行终审')
            return {
                'status': 'failed',
                'error': '缺少草稿内容，无法进行终审',
                'messages': ['❌ 终审失败：未找到草稿内容']
            }

        compliance_report = state.get('compliance_report')
        if not compliance_report:
            await _emit_node_failure(task_id, "chief_editor", "终审编辑", '缺少合规检查报告，无法进行终审')
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
        await _emit_node_complete(task_id, "chief_editor", "终审编辑", {
            "score": quality_score,
            "status": new_status,
            "title": title  # 添加标题字段，供前端显示
        })

        # 如果评分不通过，发送节点重置消息（回退到文案创作）
        if new_status == 'review_failed':
            await _emit_nodes_reset_after_copywriter(task_id)

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

        await _emit_node_failure(task_id, "chief_editor", "终审编辑", f'终审评估失败：{str(e)}')

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
    await _emit_node_start(task_id, "human_review", "人工审核")

    try:
        # ===== 数据验证 =====
        editor_feedback = state.get('editor_feedback', {})
        if not editor_feedback:
            await _emit_node_failure(task_id, "human_review", "人工审核", '缺少编辑反馈，无法进行人工审核')
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
        await _emit_node_complete(task_id, "human_review", "人工审核", {
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

        await _emit_node_failure(task_id, "human_review", "人工审核", f'人工审核节点失败：{str(e)}')

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
    await _emit_node_start(task_id, "finalize", "最终输出")

    try:
        # ===== 数据验证 =====
        draft_content = state.get('draft_content')
        if not draft_content:
            await _emit_node_failure(task_id, "finalize", "最终输出", '缺少草稿内容，无法生成最终输出')
            return {
                'status': 'failed',
                'error': '缺少草稿内容，无法生成最终输出',
                'messages': ['❌ 最终输出失败：未找到草稿内容']
            }

        selected_title = state.get('selected_title')
        if not selected_title:
            await _emit_node_failure(task_id, "finalize", "最终输出", '缺少标题，无法生成最终输出')
            return {
                'status': 'failed',
                'error': '缺少标题，无法生成最终输出',
                'messages': ['❌ 最终输出失败：未找到标题']
            }

        keywords = state.get('keywords')
        if not keywords:
            await _emit_node_failure(task_id, "finalize", "最终输出", '缺少关键词，无法生成最终输出')
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

        await _emit_node_complete(task_id, "finalize", "最终输出", {
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

        await _emit_node_failure(task_id, "finalize", "最终输出", f'最终输出失败：{str(e)}')

        return {
            'status': 'failed',
            'error': f'最终输出失败：{str(e)}',
            'error_detail': error_detail,
            'error_history': error_history,
            'messages': [f'❌ 最终输出失败：{str(e)}']
        }
