# 小红书数据爬取脚本使用指南

## 概述

本目录包含独立的小红书数据爬取脚本，可以独立于主应用运行，用于批量采集数据到数据库。

## 脚本说明

### 1. `crawl_xhs_data.py` - 单次爬取脚本

用于执行单次爬取任务，支持命令行参数配置。

**基础用法：**

```bash
# 进入 backend 目录
cd backend

# 基础爬取（必须指定关键词）
python scripts/crawler/crawl_xhs_data.py -k "Python编程,机器学习"

# 带过滤条件
python scripts/crawler/crawl_xhs_data.py -k "Python编程" -t "教程,入门" --min-likes 100 --min-comments 10

# 指定数量和时间范围
python scripts/crawler/crawl_xhs_data.py -k "AI绘画" -n 50 --days 30
```

**参数说明：**

| 参数 | 简写 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--keywords` | `-k` | ✅ | - | 搜索关键词，多个用逗号分隔 |
| `--topic-words` | `-t` | ❌ | 空 | 话题词，标题或正文需包含其中之一 |
| `--count` | `-n` | ❌ | 20 | 目标爬取数量 |
| `--min-likes` | - | ❌ | 0 | 最小点赞数 |
| `--min-comments` | - | ❌ | 0 | 最小评论数 |
| `--min-favorites` | - | ❌ | 0 | 最小收藏数 |
| `--days` | - | ❌ | 0 | 时间范围（天数），0表示不限制 |

**示例：**

```bash
# 爬取Python相关笔记，要求点赞100+，评论20+，最近30天
python scripts/crawler/crawl_xhs_data.py \
  -k "Python编程" \
  -t "教程,学习,入门" \
  --min-likes 100 \
  --min-comments 20 \
  --days 30 \
  -n 50
```

### 2. `crawl_xhs_batch.py` - 批量爬取脚本

从配置文件读取多个任务，批量执行爬取。

**基础用法：**

```bash
# 使用默认配置文件（crawl_config.json）
python scripts/crawler/crawl_xhs_batch.py

# 使用自定义配置文件
python scripts/crawler/crawl_xhs_batch.py -c my_config.json

# 设置任务间延迟时间（默认10秒）
python scripts/crawler/crawl_xhs_batch.py --delay 30
```

**参数说明：**

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--config` | `-c` | `crawl_config.json` | 配置文件路径 |
| `--delay` | - | 10 | 任务间延迟时间（秒） |

### 3. `crawl_config.json` - 批量爬取配置文件

配置文件示例：

```json
{
  "tasks": [
    {
      "name": "Python编程相关",
      "keywords": ["Python编程", "Python教程"],
      "topic_words": ["入门", "教程", "学习"],
      "min_likes": 50,
      "min_comments": 10,
      "min_favorites": 20,
      "days": 30,
      "count": 30
    },
    {
      "name": "AI绘画相关",
      "keywords": ["AI绘画", "Midjourney"],
      "topic_words": ["教程", "作品"],
      "min_likes": 100,
      "min_comments": 20,
      "min_favorites": 50,
      "days": 7,
      "count": 50
    }
  ]
}
```

**配置字段说明：**

- `name`: 任务名称（用于日志显示）
- `keywords`: 搜索关键词列表（必需）
- `topic_words`: 话题词列表（可选）
- `min_likes`: 最小点赞数（默认0）
- `min_comments`: 最小评论数（默认0）
- `min_favorites`: 最小收藏数（默认0）
- `days`: 时间范围天数（0表示不限制）
- `count`: 目标爬取数量（默认20）

## 数据库配置

脚本使用 `app/core/config.py` 中的数据库配置：

```python
MYSQL_HOST: str = "localhost"
MYSQL_PORT: int = 3306
MYSQL_USER: str = "root"
MYSQL_PASSWORD: str = "your_password"
MYSQL_DATABASE: str = "xhs_crawler"
```

确保数据库已创建并可访问。

## 数据存储

爬取的数据存储在 `xhs_note` 表中，包含以下字段：

- 笔记基本信息：`note_id`, `title`, `desc`, `type`
- 作者信息：`user_id`, `nickname`, `avatar`, `ip_location`
- 互动数据：`liked_count`, `collected_count`, `comment_count`, `share_count`
- 时间信息：`time`, `last_update_time`
- 其他：`image_list`, `tag_list`, `note_url`, `source_keyword`

## 注意事项

1. **首次运行**：需要手动登录小红书账号（浏览器会自动打开）
2. **登录状态**：登录信息会保存在 `browser_data/xhs_user_data_dir` 目录
3. **爬取速度**：建议设置合理的任务间延迟，避免触发反爬
4. **数据去重**：相同 `note_id` 的笔记会自动更新而不是重复插入
5. **过滤条件**：所有过滤条件在爬虫端实时应用，只保存符合条件的笔记
6. **中断恢复**：可以使用 Ctrl+C 中断爬取，已爬取的数据会保存

## 开发说明

脚本依赖的核心模块：

- `app.services.xhs_crawler_service.XhsCrawlerService`: 爬虫服务封装
- `app.database.models.XhsNote`: 数据库模型
- `app.core.config.settings`: 配置管理
- `app.core.logger.logger`: 日志管理

如需扩展功能，可以修改 `XhsCrawlerService` 类或创建新的脚本。
