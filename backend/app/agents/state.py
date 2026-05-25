"""
LangGraph State 定义
"""
from typing import TypedDict, List, Dict, Optional, Annotated
from operator import add


class GraphState(TypedDict):
    """工作流状态管理"""
    
    # ===== 输入 =====
    keywords: List[str]  # 用户输入的主题关键词
    topic_words: List[str] # 用户输入的话题关键词
    account_persona: Optional[str]  # 账号人设
    
    # ===== 爬虫配置 =====
    target_count: int  # 目标采集笔记数量
    min_comments: int  # 最小评论数
    min_likes: int  # 最小点赞数
    min_favorites: int  # 最小收藏数
    days: int  # 查询最近几天的数据
    
    # ===== 数据采集层 =====
    raw_trends: List[Dict]  # 原始热点数据
    analyzed_templates: List[Dict]  # 分析后的爆款模板
    llm_analysis: Optional[Dict]  # LLM深度分析结果

    # ===== 内容生产层 =====
    strategy: Optional[Dict]  # 选题策略方案
    title_candidates: List[str]  # 候选标题列表（3个）
    selected_title: Optional[str]  # 用户选择的标题
    draft_content: Optional[str]  # 文案初稿
    retrieved_styles: Optional[List[Dict]]  # RAG检索到的写作风格（缓存，避免重复检索）
    
    # ===== 质量控制层 =====
    compliance_report: Optional[Dict]  # 合规检查报告
    editor_feedback: Optional[Dict]  # 编辑反馈意见
    iteration_count: int  # 迭代次数
    human_decision: Optional[str]  # 人工审核决策 (approve/reject)
    human_feedback: Optional[str]  # 人工审核的详细反馈意见
    
    # ===== 视觉层 =====
    image_prompts: List[str]  # 图片生成提示词
    image_urls: List[str]  # 生成的图片URL
    image_local_paths: List[str]  # 图片本地路径
    
    # ===== 最终输出 =====
    final_post: Optional[Dict]  # 最终内容
    status: str  # draft / reviewing / approved / rejected / waiting_human

    # ===== 流程控制 =====
    messages: Annotated[List[str], add]  # 流程日志消息
    error: Optional[str]  # 错误信息

    # ===== 错误管理=====
    error_detail: Optional[Dict]  # 详细错误信息
    error_history: List[Dict]  # 错误历史记录
    degraded_nodes: List[str]  # 降级运行的节点列表
    retry_count: Dict[str, int]  # 各节点重试次数