from pydantic import BaseModel, Field
from typing import List, Optional

class NoteItem(BaseModel):
    title: str = Field(..., description="笔记标题")
    content: str = Field(..., description="笔记正文内容")
    likes: int = Field(default=0, description="点赞数")
    favorites: int = Field(default=0, description="收藏数")
    comments: int = Field(default=0, description="评论数")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    author: Optional[str] = Field(default=None, description="作者昵称")
    publish_time: Optional[str] = Field(default=None, description="发布时间")
    url: Optional[str] = Field(default=None, description="笔记链接")
    content_type: Optional[str] = Field(default=None, description="内容类型（图文/视频）")
    keyword_used: Optional[str] = Field(default=None, description="匹配的关键词")

class SearchCrawlRequest(BaseModel):
    keywords: List[str] = Field(..., min_length=1, description="搜索关键词列表，至少填一个")
    topic_words: List[str] = Field(default_factory=list, description="话题词列表，正文/标题至少包含其中一个；为空则不过滤")
    min_comments: int = Field(0, ge=0, description="评论数最小值（>=）")
    min_likes: int = Field(0, ge=0, description="点赞数最小值（>=）")
    min_favorites: int = Field(0, ge=0, description="收藏数最小值（>=）")
    target_count: int = Field(20, ge=1, description="目标采集条数")
    days: int = Field(7, ge=1, description="查询最近几天的数据")
    content_type: str = "图文"

class SearchCrawlResponse(BaseModel):
    target_count: int = Field(..., description="目标采集数量")
    count: int = Field(..., description="实际采集到的笔记数量")
    used_keywords: List[str] = Field(..., description="使用的关键词列表")
    items: List[NoteItem] = Field(..., description="笔记列表")

