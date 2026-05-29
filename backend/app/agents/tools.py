"""
Agent 使用的工具函数
"""
from typing import List, Dict
import re
import json
from app.core.logger import logger

def extract_keywords(text: str) -> List[str]:
    """从文本中提取关键词"""
    # 简单实现，实际可以使用 jieba 等分词工具
    words = re.findall(r'[\u4e00-\u9fa5]+', text)
    return [w for w in words if len(w) >= 2]


def calculate_heat_score(item: Dict) -> int:
    """计算热度评分"""
    likes = item.get('likes', 0)
    favorites = item.get('favorites', 0)
    comments = item.get('comments', 0)
    
    # 加权计算：点赞*1 + 收藏*2 + 评论*3
    score = likes * 1 + favorites * 2 + comments * 3
    return score


def check_sensitive_words(text: str) -> Dict:
    """检查敏感词"""
    # 简化版敏感词库
    sensitive_words = [
        '广告', '推广', '代购', '微信', 'VX', 'wx',
        '加我', '私信', '链接', '下单', '购买'
    ]
    
    found_words = []
    for word in sensitive_words:
        if word in text:
            found_words.append(word)
    
    risk_level = 'high' if len(found_words) > 3 else 'medium' if len(found_words) > 0 else 'low'
    
    return {
        'found_words': found_words,
        'count': len(found_words),
        'risk_level': risk_level,
        'passed': len(found_words) == 0
    }


def extract_title_pattern(title: str) -> str:
    """提取标题模式"""
    if '?' in title or '？' in title:
        return 'question'
    elif '!' in title or '！' in title:
        return 'exclamation'
    elif any(word in title for word in ['必看', '必备', '推荐', '干货']):
        return 'benefit'
    elif any(word in title for word in ['竟然', '居然', '没想到', '原来']):
        return 'surprise'
    else:
        return 'normal'


def format_content_with_emoji(content: str) -> str:
    """为内容添加 Emoji"""
    emoji_map = {
        '重点': '✨',
        '注意': '⚠️',
        '推荐': '👍',
        '技巧': '💡',
        '经验': '📝',
        '分享': '🎁',
        '总结': '📌',
        '建议': '💭'
    }
    
    formatted = content
    for keyword, emoji in emoji_map.items():
        if keyword in formatted:
            formatted = formatted.replace(keyword, f"{emoji}{keyword}")
    
    return formatted


def extract_tags(content: str, max_tags: int = 10) -> List[str]:
    """从内容中提取标签"""
    # 提取 # 标签
    tags = re.findall(r'#([^\s#]+)', content)
    
    # 如果没有标签，从内容中提取关键词
    if not tags:
        keywords = extract_keywords(content)
        tags = keywords[:max_tags]
    
    return tags[:max_tags]


def calculate_quality_score(content: Dict) -> int:
    """计算内容质量评分（多维度评估）"""
    score = 100

    title = content.get('title', '')
    body = content.get('content', '')
    tags = content.get('tags', [])

    # 标题质量检查（权重：18分）
    # 标题长度检查（10-30字最佳）
    if len(title) < 10:
        score -= 10
    elif len(title) > 30:
        score -= 5

    # 标题是否包含Emoji
    title_emoji_count = len(re.findall(r'[\U0001F300-\U0001F9FF]', title))
    if title_emoji_count == 0:
        score -= 3
    elif title_emoji_count > 3:
        score -= 2

    # 标题是否有吸引力词汇（放宽要求，不只是情绪钩子）
    attractive_words = ['必看', '必备', '推荐', '干货', '没想到', '竟然', '居然', '原来', '震惊', '绝了', '太', '超', '实用', '避坑', '技巧', '经验', '分享']
    has_attraction = any(word in title for word in attractive_words)
    if not has_attraction:
        score -= 5

    # 正文长度检查（权重：15分）
    if len(body) < 100:
        score -= 15
    elif len(body) < 200:
        score -= 8
    elif len(body) > 1000:
        score -= 10
    elif len(body) > 800:
        score -= 5

    # Emoji 使用检查（权重：5分）
    emoji_count = len(re.findall(r'[\U0001F300-\U0001F9FF]', body))
    if emoji_count == 0:
        score -= 5
    elif emoji_count < 3:
        score -= 3
    elif emoji_count > 15:
        score -= 5

    # 段落结构检查（权重：6分）
    paragraphs = [p.strip() for p in body.split('\n\n') if p.strip()]
    if len(paragraphs) < 2:
        score -= 6

    # 标签检查（权重：8分）
    if len(tags) < 3:
        score -= 8
    elif len(tags) < 5:
        score -= 3
    elif len(tags) > 10:
        score -= 2

    # 6. 内容组织检查（权重：12分）
    # 检查是否有内容组织方式（可以是分点、数字、或其他组织形式）
    # 放宽要求：不强制要求emoji数字，普通数字、符号都可以
    has_numbering = bool(re.search(r'[1-9]️⃣|[一二三四五六七八九十]、|\d+[\.\、]|[•\-\*]', body))
    if not has_numbering:
        score -= 6  # 降低扣分，因为不是必须的

    # 检查是否有段落标记或emoji点缀（但不强制要求【】这种模板化标记）
    has_visual_elements = bool(re.search(r'[✨💡📌🔥⚠️👍💭🎯]', body))
    if not has_visual_elements:
        score -= 3

    # 互动引导检查（权重：3分）
    # 放宽要求：不强制要求行动号召，自然结尾也可以
    cta_words = ['点赞', '收藏', '关注', '评论', '分享', '留言', '互动', '转发', '有用', '帮助']
    has_cta = any(word in body for word in cta_words)
    if not has_cta:
        score -= 3 

    # 自然表达检查（权重：10分）
    # 检查是否有自然的口语化表达，但不过度使用网络用语
    colloquial_words = ['真的', '超级', '特别', '太', '啦', '呀', '吧', '哦', '嘛', '挺', '蛮', '还']
    colloquial_count = sum(1 for word in colloquial_words if word in body)

    if colloquial_count == 0:
        score -= 5  # 完全没有口语化

    # 过度网络用语检查（姐妹、宝子等）
    internet_slang = ['姐妹', '宝子', '集美', 'uu']
    slang_count = sum(1 for word in internet_slang if word in body)

    if slang_count > 3:
        score -= 5  # 过度使用网络用语，不自然


    # 内容丰富度检查（权重：4分）
    # 检查句子数量
    sentences = re.split(r'[。！？\n]', body)
    sentence_count = len([s for s in sentences if len(s.strip()) > 5])
    if sentence_count < 5:
        score -= 4

    return max(0, min(100, score))

def parse_title_candidates(llm_response: str) -> list[str]:
    """
    解析 LLM 生成的标题候选，兼容多种输出格式

    支持格式：
    - 标题1（利益型）：xxx
    - 标题1（利益型）：\nxxx
    - 标题1：xxx
    - 1. xxx
    - 每行一个标题

    Returns:
        最多 5 个标题的列表
    """
    import re

    text = llm_response.strip()
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]

    titles = []
    i = 0

    # 匹配 "标题X（类型）：" 或 "标题X："
    header_re = re.compile(r"^(?:标题\s*)?([1-5一二三四五])\s*(?:[（(][^）)]*[）)])?\s*[：:]\s*(.*)$")
    # 匹配 "1. xxx" 或 "1、xxx"
    num_re = re.compile(r"^[1-5][\\.、）\)]\s*(.+)$")

    while i < len(lines) and len(titles) < 5:
        line = lines[i]

        # 尝试匹配标题头格式
        m = header_re.match(line)
        if m:
            rest = m.group(2).strip()
            if rest:
                # 同行有标题内容
                titles.append(rest)
            else:
                # 下一行是真标题
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # 防止下一行仍然是 header
                    if not header_re.match(next_line) and not num_re.match(next_line):
                        titles.append(next_line)
                        i += 1
            i += 1
            continue

        # 尝试匹配编号格式
        m2 = num_re.match(line)
        if m2:
            titles.append(m2.group(1).strip())
            i += 1
            continue

        # 兜底：过滤明显的标签行
        if not re.match(r"^标题\s*[1-5一二三四五]\s*(?:[（(][^）)]*[）)])?\s*[：:]?$", line):
            titles.append(line)

        i += 1

    # 清理可能残留的 "标题1（利益型）："
    cleaned = []
    for t in titles:
        t = re.sub(r"^标题\s*[1-5一二三四五]\s*(?:[（(][^）)]*[）)])?\s*[：:]?\s*", "", t).strip()
        if t and t not in cleaned:
            cleaned.append(t)

    return cleaned[:5]



def build_image_prompt_from_json(llm_response: str) -> str:
    """
    解析 visual_designer 的 LLM JSON 输出，按权重拼装成丰富的图片提示词。

    分段写入主体/场景/构图/光线/色彩/风格/氛围/质感，让模型有更多
    具体锚点去生成，避免泛泛的相似图。

    Args:
        llm_response: LLM 原始返回（可能包含 markdown 代码块包裹的 JSON）

    Returns:
        拼装后的中文 prompt 字符串。解析失败时返回清理后的原始文本作为兜底。
    """
    import re

    raw = llm_response.strip()

    # 先尝试从 markdown 代码块中提取 JSON
    parsed = None
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
    candidates = []
    if json_match:
        candidates.append(json_match.group(1))
    candidates.append(raw)
    # 再尝试取首个 { 到末尾 } 之间的子串
    first_brace = raw.find('{')
    last_brace = raw.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidates.append(raw[first_brace:last_brace + 1])

    for cand in candidates:
        try:
            parsed = json.loads(cand)
            break
        except (json.JSONDecodeError, ValueError):
            continue

    if not isinstance(parsed, dict):
        # 解析失败，降级使用原始文本（去除引号和代码块）
        logger.warning("⚠️ visual_designer JSON 解析失败，降级使用原始文本作为提示词")
        return raw.strip('`').strip('"').strip("'")

    # 按顺序拼装，主体和场景放最前（生图模型对前面的 token 更敏感）
    sections = [
        ('主体', parsed.get('subject')),
        ('场景', parsed.get('scene')),
        ('构图', parsed.get('composition')),
        ('光线', parsed.get('lighting')),
        ('色彩', parsed.get('color_palette')),
        ('风格', parsed.get('style')),
        ('氛围', parsed.get('mood')),
        ('质感', parsed.get('texture_details')),
    ]
    parts = [f"{label}：{str(value).strip()}" for label, value in sections if value]
    prompt = "；".join(parts)

    if not prompt:
        logger.warning("⚠️ visual_designer JSON 字段全为空，降级使用原始文本")
        return raw.strip('`').strip('"').strip("'")

    return prompt


def build_default_titles(main_keyword: str) -> list:
    """构建降级用的默认候选标题（5 个）"""
    return [
        f'🔥{main_keyword}必看！这些技巧让你少走弯路',
        f'没想到{main_keyword}还能这样玩？我震惊了',
        f'关于{main_keyword}，你真的了解吗？',
        f'{main_keyword}避坑指南！新手必看',
        f'超实用！{main_keyword}的正确打开方式',
    ]


async def download_images_to_outputs(image_urls: list, keywords: list, task_id: str) -> list:
    """把图片 URL 列表下载到 data/outputs/{keyword}_{task_id}/images/ 下，返回本地路径列表

    任意环节失败都只返回空列表，不抛异常（图片是非关键资产）。
    """
    if not image_urls:
        return []

    try:
        from pathlib import Path
        from app.utils.image_downloader import image_downloader

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
        if local_paths:
            logger.info(f"✅ 图片已下载到: {images_dir}, 共 {len(local_paths)} 张")
        else:
            logger.warning(f"⚠️ 图片下载返回空列表")
        return local_paths or []
    except Exception as download_error:
        logger.warning(f"⚠️ 图片下载失败: {download_error}")
        return []