"""
错误处理工具函数
"""
import traceback


def log_error(node_name: str, error: Exception, state: dict = None) -> dict:
    """
    记录错误详情
    
    Args:
        node_name: 节点名称
        error: 异常对象
        state: 当前状态（可选）
    
    Returns:
        错误详情字典
    """
    error_detail = {
        'node': node_name,
        'error_type': type(error).__name__,
        'message': str(error),
        'traceback': traceback.format_exc()
    }
    
    # 打印详细错误日志
    print(f"❌ {node_name} 错误详情:")
    print(f"   类型: {error_detail['error_type']}")
    print(f"   消息: {error_detail['message']}")
    print(f"   堆栈:\n{error_detail['traceback']}")
    
    return error_detail


def create_error_response(node_name: str, error: Exception, error_level: str = 'failed') -> dict:
    """
    创建统一的错误响应
    
    Args:
        node_name: 节点名称
        error: 异常对象
        error_level: 错误级别 ('failed' 或 'degraded')
    
    Returns:
        错误响应字典
    """
    error_detail = log_error(node_name, error)
    
    return {
        'status': error_level,
        'error': f'{node_name} 失败：{str(error)}',
        'error_detail': error_detail,
        'messages': [f'❌ {node_name} 失败：{str(error)}']
    }


def add_error_to_history(state: dict, node_name: str, error: Exception) -> list:
    """
    将错误添加到历史记录
    
    Args:
        state: 当前状态
        node_name: 节点名称
        error: 异常对象
    
    Returns:
        更新后的错误历史列表
    """
    error_history = state.get('error_history', [])
    
    error_record = {
        'node': node_name,
        'error_type': type(error).__name__,
        'message': str(error)
    }
    
    error_history.append(error_record)
    return error_history


def add_degraded_node(state: dict, node_name: str) -> list:
    """
    记录降级运行的节点
    
    Args:
        state: 当前状态
        node_name: 节点名称
    
    Returns:
        更新后的降级节点列表
    """
    degraded_nodes = state.get('degraded_nodes', [])
    
    if node_name not in degraded_nodes:
        degraded_nodes.append(node_name)
    
    return degraded_nodes
