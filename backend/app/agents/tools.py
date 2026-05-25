"""
Agent 使用的工具函数
"""
from typing import List, Dict
import re

def select_content_angle(persona: str, keyword: str, emotion_triggers: list, pain_points: list) -> str:
    """根据人设和情绪点选择内容角度"""
    import random

    # 角度模板库
    angle_templates = {
        '专业分享者': [
            f'从专业角度深度解析{keyword}',
            f'系统化梳理{keyword}的核心要点',
            f'专业人士的{keyword}实战经验',
            f'{keyword}的底层逻辑和方法论'
        ],
        '新手小白': [
            f'新手视角：我是如何掌握{keyword}的',
            f'零基础学{keyword}的完整路径',
            f'小白踩坑后总结的{keyword}经验',
            f'从零到一学{keyword}的真实记录'
        ],
        '生活博主': [
            f'日常生活中的{keyword}小技巧',
            f'用{keyword}提升生活品质',
            f'分享我的{keyword}日常实践',
            f'{keyword}让生活更美好的N种方式'
        ],
        '职场达人': [
            f'职场必备的{keyword}技能',
            f'{keyword}助力职场进阶',
            f'高效职场人的{keyword}秘诀',
            f'用{keyword}提升职场竞争力'
        ],
        '学习博主': [
            f'高效学习{keyword}的方法',
            f'{keyword}学习路线图',
            f'我的{keyword}学习心得',
            f'如何快速掌握{keyword}'
        ]
    }

    # 根据情绪点调整角度
    if '焦虑' in emotion_triggers or '避坑' in ''.join(pain_points):
        return f'{keyword}避坑指南：少走弯路的关键经验'
    elif '好奇' in emotion_triggers or '惊喜' in emotion_triggers:
        return f'你不知道的{keyword}秘密'
    elif '实用' in emotion_triggers or '干货' in emotion_triggers:
        return angle_templates.get(persona, [f'从{persona}的角度分享{keyword}经验'])[0]

    # 默认从模板库随机选择
    templates = angle_templates.get(persona, [f'从{persona}的角度分享{keyword}经验'])
    return random.choice(templates)


def infer_target_audience(keywords: list, pain_points: list) -> str:
    """根据关键词和痛点推断目标受众"""
    pain_points_str = ''.join(pain_points).lower()
    keywords_str = ''.join(keywords).lower()

    # 新手相关
    if any(word in pain_points_str for word in ['新手', '不知道', '入门', '零基础', '怎么开始']):
        return '刚接触该领域的新手用户'

    # 效率相关
    if any(word in pain_points_str for word in ['效率', '时间', '快速', '速成']):
        return '追求效率提升的进阶用户'

    # 避坑相关
    if any(word in pain_points_str for word in ['避坑', '错误', '失败', '踩坑']):
        return '想要避免常见错误的学习者'

    # 职场相关
    if any(word in keywords_str for word in ['职场', '工作', '面试', '简历']):
        return '职场人士和求职者'

    # 学习相关
    if any(word in keywords_str for word in ['学习', '考试', '备考', '提升']):
        return '自我提升的学习者'

    # 生活相关
    if any(word in keywords_str for word in ['生活', '日常', '家居', '美食']):
        return '注重生活品质的用户'

    return '对该主题感兴趣的所有用户'


def generate_hook(keyword: str, emotion_triggers: list, pain_points: list) -> str:
    """根据情绪点和痛点生成内容钩子"""
    import random

    # 钩子模板库
    hook_templates = {
        '好奇': [
            f'你真的了解{keyword}吗？',
            f'{keyword}背后的秘密',
            f'关于{keyword}的3个冷知识',
            f'{keyword}的真相可能和你想的不一样'
        ],
        '焦虑': [
            f'不懂{keyword}会吃大亏',
            f'{keyword}避坑指南',
            f'别再在{keyword}上浪费时间了',
            f'这些{keyword}误区90%的人都中招'
        ],
        '实用': [
            f'{keyword}的核心技巧',
            f'最实用的{keyword}方法',
            f'{keyword}速成指南',
            f'掌握{keyword}的关键要点'
        ],
        '惊喜': [
            f'没想到{keyword}还能这样玩',
            f'{keyword}的神仙操作',
            f'这个{keyword}技巧绝了',
            f'{keyword}的高级玩法'
        ],
        '共鸣': [
            f'关于{keyword}，说说我的真实经历',
            f'{keyword}路上的那些坑',
            f'我的{keyword}心路历程',
            f'{keyword}让我明白的道理'
        ]
    }

    # 根据主要情绪点选择钩子
    main_emotion = emotion_triggers[0] if emotion_triggers else '实用'

    # 匹配情绪点
    for emotion_key in hook_templates.keys():
        if emotion_key in main_emotion:
            return random.choice(hook_templates[emotion_key])

    # 根据痛点生成钩子
    if pain_points:
        first_pain = pain_points[0]
        if '不知道' in first_pain or '怎么' in first_pain:
            return f'解决{keyword}的核心问题'
        elif '效率' in first_pain or '时间' in first_pain:
            return f'10分钟掌握{keyword}精髓'
        elif '错误' in first_pain or '避坑' in first_pain:
            return f'{keyword}避坑指南'

    # 默认钩子
    return random.choice(hook_templates['实用'])

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
        最多 3 个标题的列表
    """
    import re

    text = llm_response.strip()
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]

    titles = []
    i = 0

    # 匹配 "标题X（类型）：" 或 "标题X："
    header_re = re.compile(r"^(?:标题\s*)?([1-3一二三])\s*(?:[（(][^）)]*[）)])?\s*[：:]\s*(.*)$")
    # 匹配 "1. xxx" 或 "1、xxx"
    num_re = re.compile(r"^[1-3][\\.、）\)]\s*(.+)$")

    while i < len(lines) and len(titles) < 3:
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
        if not re.match(r"^标题\s*[1-3一二三]\s*(?:[（(][^）)]*[）)])?\s*[：:]?$", line):
            titles.append(line)

        i += 1

    # 清理可能残留的 "标题1（利益型）："
    cleaned = []
    for t in titles:
        t = re.sub(r"^标题\s*[1-3一二三]\s*(?:[（(][^）)]*[）)])?\s*[：:]?\s*", "", t).strip()
        if t and t not in cleaned:
            cleaned.append(t)

    return cleaned[:3]