"""
数据库模型定义
"""
from sqlalchemy import Column, Integer, Text, String, BigInteger, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class XhsCreator(Base):
    """小红书创作者表"""
    __tablename__ = 'xhs_creator'
    
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(255), comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    ip_location = Column(Text, comment='IP地址位置')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    desc = Column(Text, comment='描述')
    gender = Column(Text, comment='性别')
    follows = Column(Text, comment='关注数')
    fans = Column(Text, comment='粉丝数')
    interaction = Column(Text, comment='互动数')
    follows_num = Column(Integer, default=0, comment='关注数（数值）')
    fans_num = Column(Integer, default=0, index=True, comment='粉丝数（数值）')
    interaction_num = Column(Integer, default=0, index=True, comment='互动数（数值）')
    tag_list = Column(Text, comment='标签列表')


class XhsNote(Base):
    """小红书笔记表"""
    __tablename__ = 'xhs_note'
    
    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(255), comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    ip_location = Column(Text, comment='IP地址位置')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    note_id = Column(String(255), index=True, comment='笔记ID')
    type = Column(Text, comment='笔记类型')
    title = Column(Text, comment='笔记标题')
    desc = Column(Text, comment='笔记描述')
    video_url = Column(Text, comment='视频URL')
    time = Column(BigInteger, index=True, comment='笔记时间戳')
    last_update_time = Column(BigInteger, comment='笔记最后更新时间戳')
    liked_count = Column(Text, comment='点赞数')
    collected_count = Column(Text, comment='收藏数')
    comment_count = Column(Text, comment='评论数')
    share_count = Column(Text, comment='分享数')
    liked_count_num = Column(Integer, default=0, index=True, comment='点赞数（数值）')
    collected_count_num = Column(Integer, default=0, index=True, comment='收藏数（数值）')
    comment_count_num = Column(Integer, default=0, index=True, comment='评论数（数值）')
    share_count_num = Column(Integer, default=0, comment='分享数（数值）')
    image_list = Column(Text, comment='图片列表')
    video_url = Column(Text, comment='视频URL')
    local_media_path = Column(Text, comment='本地媒体文件路径（JSON格式）')
    tag_list = Column(Text, comment='标签列表')
    note_url = Column(Text, comment='笔记URL')
    source_keyword = Column(Text, default='', comment='来源关键词')
    xsec_token = Column(Text, comment='Xsec Token')
    media_description = Column(Text, comment='图片/视频的文字描述（VL模型生成）')
    media_summary = Column(Text, comment='图片/视频内容总结（LLM生成）')
    media_analysis_status = Column(String(50), default='pending', comment='媒体分析状态: pending/processing/completed/failed')


class XhsNoteComment(Base):
    """小红书笔记评论表"""
    __tablename__ = 'xhs_note_comment'

    id = Column(Integer, primary_key=True, comment='主键ID')
    user_id = Column(String(255), comment='用户ID')
    nickname = Column(Text, comment='用户昵称')
    avatar = Column(Text, comment='用户头像')
    ip_location = Column(Text, comment='IP地址位置')
    add_ts = Column(BigInteger, comment='添加时间戳')
    last_modify_ts = Column(BigInteger, comment='最后修改时间戳')
    comment_id = Column(String(255), index=True, comment='评论ID')
    create_time = Column(BigInteger, index=True, comment='评论创建时间戳')
    note_id = Column(String(255), comment='笔记ID')
    content = Column(Text, comment='评论内容')
    sub_comment_count = Column(Integer, comment='子评论数')
    pictures = Column(Text, comment='图片')
    parent_comment_id = Column(String(255), comment='父评论ID')
    like_count = Column(Text, comment='点赞数')


class PendingTask(Base):
    """待处理任务表"""
    __tablename__ = 'pending_task'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')
    task_id = Column(String(255), unique=True, index=True, nullable=False, comment='任务ID（UUID）')
    task_type = Column(String(50), nullable=False, comment='任务类型: title_selection/human_review')
    status = Column(String(50), nullable=False, comment='任务状态: waiting_title_selection/waiting_human_review')
    keywords = Column(Text, comment='关键词列表（JSON）')
    title_candidates = Column(Text, comment='标题候选列表（JSON）')
    draft_content = Column(Text, comment='草稿内容')
    editor_feedback = Column(Text, comment='编辑反馈（JSON）')
    created_at = Column(BigInteger, nullable=False, comment='创建时间戳（毫秒）')
    updated_at = Column(BigInteger, nullable=False, comment='更新时间戳（毫秒）')

    def to_dict(self):
        """转换为字典"""
        import json
        return {
            'id': self.id,
            'task_id': self.task_id,
            'task_type': self.task_type,
            'status': self.status,
            'keywords': json.loads(self.keywords) if self.keywords else [],
            'title_candidates': json.loads(self.title_candidates) if self.title_candidates else [],
            'draft_content': self.draft_content,
            'editor_feedback': json.loads(self.editor_feedback) if self.editor_feedback else None,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
