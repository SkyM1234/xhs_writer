# 图片/视频分析 - 保底逻辑实现

## 功能说明

实现了**在线URL优先 + 本地文件保底**的双重保障机制，确保即使在线URL失效后仍能分析图片/视频。

## 实现原理

### 1. 数据库字段

新增 `local_media_path` 字段（TEXT类型），存储本地文件路径的JSON格式：

```json
{
  "images": [
    "/path/to/image1.jpg",
    "/path/to/image2.jpg"
  ],
  "video": "/path/to/video.mp4"
}
```

### 2. 分析流程

```
尝试在线URL分析
  ↓
成功？
  ├─ 是 → 返回结果
  └─ 否 → 检查本地文件
       ↓
    本地文件存在？
      ├─ 是 → 使用本地文件分析
      └─ 否 → 返回失败
```

### 3. 核心方法

#### 图片分析（带保底）
```python
await vision_analysis_service.analyze_image_with_fallback(
    image_url="https://...",
    local_path="/path/to/image.jpg",  # 可选
    context="笔记内容"
)
```

#### 视频分析（带保底）
```python
await vision_analysis_service.analyze_video_with_fallback(
    video_url="https://...",
    local_path="/path/to/video.mp4",  # 可选
    context="笔记内容"
)
```

#### 批量图片分析（带保底）
```python
await vision_analysis_service.analyze_images_batch_with_fallback(
    image_urls=["https://...", "https://..."],
    local_paths=["/path/1.jpg", "/path/2.jpg"],  # 可选
    context="笔记内容",
    max_images=9
)
```

## 使用场景

### 场景1：在线URL正常
```
1. 尝试URL分析 → 成功
2. 返回结果
```
**日志**：
```
✅ 图片分析成功: https://...
```

### 场景2：在线URL失效，有本地文件
```
1. 尝试URL分析 → 失败
2. 检测到本地文件存在
3. 使用本地文件分析 → 成功
4. 返回结果
```
**日志**：
```
⚠️ URL分析失败: Connection timeout
🔄 降级使用本地文件: /path/to/image.jpg
✅ 本地图片分析成功: /path/to/image.jpg
```

### 场景3：在线URL失效，无本地文件
```
1. 尝试URL分析 → 失败
2. 本地文件不存在
3. 返回失败
```
**日志**：
```
⚠️ URL分析失败: Connection timeout
⚠️ 本地文件不存在: /path/to/image.jpg
❌ 笔记 xxx 媒体分析失败: URL分析失败且无可用本地文件
```

## 配置要求

### 1. 数据库迁移

```bash
cd backend
python scripts/migrate_add_media_fields.py
```

确保添加了 `local_media_path` 字段。

### 2. MediaCrawler配置

确保启用图片/视频下载：

```python
# backend/app/utils/MediaCrawler_XHS/config/base_config.py
ENABLE_GET_MEIDAS = True  # 必须为 True
```

### 3. 本地文件路径

MediaCrawler默认保存路径：
- 图片：`backend/app/utils/MediaCrawler_XHS/data/xhs/images/`
- 视频：`backend/app/utils/MediaCrawler_XHS/data/xhs/videos/`

## 优势对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| **仅在线URL** | 性能好、实现简单 | URL失效后无法分析 |
| **仅本地文件** | 可靠性高 | 占用存储、需要下载 |
| **在线URL + 本地保底** ⭐ | 兼顾性能和可靠性 | 实现稍复杂 |

## 性能影响

- **正常情况**（URL有效）：无额外开销
- **降级情况**（URL失效）：
  - 额外时间：URL超时时间（约5-10秒）
  - 本地文件读取：约1-2秒
  - 总计：比纯URL慢6-12秒

## 注意事项

1. **本地文件路径**：
   - 需要MediaCrawler正确保存文件
   - 路径需要在 `local_media_path` 字段中正确记录

2. **存储空间**：
   - 启用本地保存会占用磁盘空间
   - 建议定期清理旧文件

3. **URL优先**：
   - 始终优先使用URL（性能更好）
   - 只在URL失败时才用本地文件

4. **错误处理**：
   - URL和本地文件都失败时，标记为 `failed`
   - 可以使用 `--reanalyze` 重新分析

## 测试验证

### 测试1：正常URL
```bash
# 应该使用URL分析，不触发保底逻辑
python scripts/analyze_media.py --limit 1
```

### 测试2：模拟URL失效
```python
# 修改代码，强制URL失败
# 验证是否自动降级到本地文件
```

### 测试3：无本地文件
```bash
# 删除本地文件
# 验证错误处理是否正确
```

## 未来优化

1. **智能选择**：
   - 检测URL响应速度
   - 如果URL很慢，直接用本地文件

2. **缓存机制**：
   - 记录URL失效状态
   - 下次直接用本地文件

3. **并行尝试**：
   - 同时尝试URL和本地文件
   - 使用先返回的结果

4. **自动修复**：
   - 定期检查失败的笔记
   - 尝试重新分析

## 完成状态

✅ 数据库模型添加 `local_media_path` 字段
✅ 视觉分析服务实现保底方法
✅ 爬虫服务集成保底逻辑
✅ 数据库迁移脚本更新
✅ 文档完善

**保底逻辑已完整实现！**
