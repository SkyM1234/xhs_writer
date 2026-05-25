"""
LangGraph 核心流程定义
"""
from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import aiosqlite

from .state import GraphState
from .nodes import (
    trend_collector_node,
    trend_analyzer_node,
    strategist_node,
    title_lab_node,
    copywriter_node,
    visual_designer_node,
    compliance_checker_node,
    chief_editor_node,
    human_review_node,
    finalize_node
)
from app.core.logger import logger


def should_pass_compliance(state: GraphState) -> Literal["chief_editor", "copywriter"]:
    """路由函数：判断合规检查是否通过"""
    compliance_report = state.get('compliance_report', {})
    iteration_count = state.get('iteration_count', 0)

    # 如果迭代次数超过3次，强制失败（避免无限循环）
    if iteration_count >= 3:
        logger.warning(f"⚠️ 合规检查迭代次数超过3次，强制失败")
        return "chief_editor"  # 进入终审，由人工决定

    # 检查合规是否通过
    passed = compliance_report.get('passed', False)

    if passed:
        logger.info(f"✅ 合规检查通过，进入终审编辑")
        return "chief_editor"  # 合规通过，进入终审
    else:
        logger.info(f"❌ 合规检查不通过，回退到文案创作")
        return "copywriter"  # 合规不通过，直接重写


def should_continue_editing(state: GraphState) -> Literal["copywriter", "human_review", "visual_designer"]:
    """路由函数：判断终审后的流程"""
    editor_feedback = state.get('editor_feedback', {})
    iteration_count = state.get('iteration_count', 0)

    # 获取评分（默认为 0）
    score = editor_feedback.get('score', 0)

    # 如果迭代次数超过3次，强制进入人工审核（避免无限循环）
    if iteration_count >= 3:
        logger.warning(f"⚠️ 终审迭代次数超过3次，强制进入人工审核")
        return "human_review"

    # 根据评分决定流程
    if score >= 90:
        # 90分以上，直接进入视觉设计
        logger.info(f"✅ 评分 {score} >= 90，直接进入视觉设计")
        return "visual_designer"
    elif score >= 80:
        # 80-90分，需要人工确认
        logger.info(f"⏸️ 评分 {score} 在80-90之间，需要人工审核")
        return "human_review"
    else:
        # 80分以下，直接重写
        logger.info(f"❌ 评分 {score} < 80，回退到文案创作")
        return "copywriter"


def should_continue_after_human_review(state: GraphState) -> Literal["copywriter", "visual_designer"]:
    """路由函数：人工审核后的流程"""
    human_decision = state.get('human_decision')

    # 只有在真正有决策时才输出日志，避免在中断前输出误导性日志
    if human_decision == 'approve':
        logger.info(f"✅ 人工审核通过，进入视觉设计")
        return "visual_designer"  # 人工通过，进入视觉设计
    elif human_decision == 'reject':
        logger.info(f"❌ 人工审核拒绝，回退到文案创作")
        return "copywriter"  # 人工不通过，回到写手重新生成
    else:
        # 第一次进入（中断前），human_decision 为 None，不输出日志
        return "copywriter"  # 默认路径（实际不会执行，因为会在 human_review 节点中断）


def create_workflow() -> StateGraph:
    """创建完整的工作流"""
    
    # 创建状态图
    workflow = StateGraph(GraphState)
    
    # ===== 添加节点 =====
    
    # 数据层
    workflow.add_node("trend_collector", trend_collector_node)
    workflow.add_node("trend_analyzer", trend_analyzer_node)
    
    # 内容生产层
    workflow.add_node("strategist", strategist_node)
    workflow.add_node("title_lab", title_lab_node)
    workflow.add_node("copywriter", copywriter_node)
    workflow.add_node("visual_designer", visual_designer_node)
    
    # 质量控制层
    workflow.add_node("compliance_checker", compliance_checker_node)
    workflow.add_node("chief_editor", chief_editor_node)
    workflow.add_node("human_review", human_review_node)

    # 最终输出
    workflow.add_node("finalize", finalize_node)
    
    # ===== 定义流程 =====
    
    # 设置入口点
    workflow.set_entry_point("trend_collector")
    
    # 数据采集流程
    workflow.add_edge("trend_collector", "trend_analyzer")
    workflow.add_edge("trend_analyzer", "strategist")
    
    # 内容生产流程
    workflow.add_edge("strategist", "title_lab")
    workflow.add_edge("title_lab", "copywriter")

    # 文案生成后进入合规检查
    workflow.add_edge("copywriter", "compliance_checker")

    # 合规检查后的条件路由
    workflow.add_conditional_edges(
        "compliance_checker",
        should_pass_compliance,
        {
            "chief_editor": "chief_editor",  # 合规通过，进入终审
            "copywriter": "copywriter"       # 合规不通过，直接重写
        }
    )

    # 终审后的条件路由
    workflow.add_conditional_edges(
        "chief_editor",
        should_continue_editing,
        {
            "copywriter": "copywriter",          # 80分以下，回到写手重新生成
            "human_review": "human_review",      # 80-90分，进入人工审核
            "visual_designer": "visual_designer" # 90分以上，直接进入视觉设计
        }
    )

    # 人工审核后的条件路由
    workflow.add_conditional_edges(
        "human_review",
        should_continue_after_human_review,
        {
            "copywriter": "copywriter",          # 人工不通过，回到写手
            "visual_designer": "visual_designer" # 人工通过，进入视觉设计
        }
    )
    
    # 视觉设计完成后进入最终输出
    workflow.add_edge("visual_designer", "finalize")
    
    # 最终输出后结束
    workflow.add_edge("finalize", END)
    
    return workflow


# ===== 全局 checkpointer 和连接管理 =====
_checkpointer = None
_db_conn = None


async def get_checkpointer():
    """获取全局 checkpointer 实例"""
    global _checkpointer, _db_conn
    if _checkpointer is None:
        from pathlib import Path
        db_path = Path(__file__).parent.parent.parent / "checkpoints" / "aiosqlitesaver.db"

        # 创建异步 SQLite 连接
        _db_conn = await aiosqlite.connect(str(db_path))
        _checkpointer = AsyncSqliteSaver(_db_conn)

    return _checkpointer


async def close_checkpointer():
    """关闭 checkpointer 和数据库连接"""
    global _checkpointer, _db_conn
    if _db_conn:
        await _db_conn.close()
        _db_conn = None
        _checkpointer = None


def create_app():
    """创建可执行的应用（同步版本，用于单例）"""
    workflow = create_workflow()
    app = workflow.compile()

    # 注意：这里不能直接创建 AsyncSqliteSaver
    # 需要在异步上下文中创建
    # 暂时返回 None，实际使用时通过 get_app_async() 获取
    return app


async def get_app_async():
    """获取带有 checkpointer 的应用实例（异步版本）"""
    workflow = create_workflow()
    checkpointer = await get_checkpointer()

    # 编译工作流
    # interrupt_after: 在指定节点执行完后自动中断，等待外部输入
    # - title_lab: 等待用户选择标题
    # - human_review: 等待人工审核决策
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_after=["title_lab", "human_review"]
    )

    return app

def display_agent_graph(app):
    try:
        # 获取 PNG 二进制数据
        png_data = app.get_graph(xray=True).draw_png()

        # 将数据写入文件
        with open("agent_review_graph.png", "wb") as f:
            f.write(png_data)

        logger.info("图表已成功保存为 agent_review_graph.png，请在当前目录下查看。")

    except Exception as e:
        logger.error(f"Graphviz 渲染失败: {e}")
        # ... fallback 到 Mermaid ...
        logger.info(app.get_graph(xray=True).draw_mermaid())

if __name__ == "__main__":
    agent_app = create_app()
    display_agent_graph(agent_app)