# 新闻H的MCP配置

## 推荐的新闻抓取MCP服务

### 1. Web搜索MCP (必需)
**功能：** 实时搜索AI相关新闻和信息
**推荐配置：**
```json
{
  "mcpServers": {
    "web-search": {
      "command": "npx",
      "args": ["-y", "@anthropic/web-search-mcp"],
      "env": {
        "SEARCH_API_KEY": "your-search-api-key"
      }
    }
  }
}
```

**支持的搜索源：**
- 主流科技媒体（TechCrunch、The Verge、36氪等）
- AI专业网站（OpenAI、Google AI、Microsoft Research等）
- 官方公告和财报
- 行业研究报告

### 2. 文件系统MCP (必需)
**功能：** 保存新闻简报到本地文件
**配置：**
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@anthropic/filesystem-mcp"],
      "env": {
        "ALLOWED_DIRECTORIES": "/Users/heyuxian/Desktop/claude-test/daily_news"
      }
    }
  }
}
```

### 3. 飞书推送（Webhook 方式）
**功能：** 推送新闻简报到飞书
**方式：** 通过飞书自定义机器人 Webhook 直接 POST，无需 MCP。
**配置：** Webhook URL 已内置在推送脚本中（`scripts/send_daily_feishu.py`）。

## 新闻抓取策略

### 搜索关键词
**核心关键词：**
- AI、人工智能、机器学习、深度学习
- OpenAI、ChatGPT、GPT、Claude、Gemini
- AI芯片、GPU、TPU、NPU
- AI应用、AI Agent、AI工具

**过滤条件：**
- 时间范围：最近24小时
- 语言：中文优先，英文补充
- 来源：可信媒体和官方渠道

### 搜索频率
- **日常模式：** 每天早上8:00-9:00
- **紧急模式：** 重大AI新闻时实时更新
- **手动模式：** 用户主动要求时

### 内容质量控制
- ✅ 信息来源可靠
- ✅ 新闻时效性强
- ✅ 内容与AI相关
- ✅ 对Helen有价值
- ❌ 排除广告和软文
- ❌ 排除过时信息
- ❌ 排除低质量内容

## 使用示例

### 启动新闻抓取
```
用户：早上好
AI：早上好，Helen！我是新闻H，正在为你获取今日AI新闻...
[调用Web搜索MCP获取新闻]
[调用文件系统MCP保存简报]
[询问是否发送到飞书]
```

### 手动刷新新闻
```
用户：帮我看看有没有最新的AI新闻
AI：好的，Helen！我马上为你搜索最新的AI新闻...
[调用Web搜索MCP获取最新新闻]
[更新新闻简报]
```

## 故障处理

### MCP服务不可用
- **Web搜索失败：** 使用缓存的新闻数据
- **文件保存失败：** 显示在聊天中，稍后手动保存
- **飞书推送失败：** 提醒用户检查网络和权限

### 数据质量问题
- **新闻过时：** 重新搜索最新信息
- **来源不可靠：** 过滤并重新搜索
- **内容重复：** 去重并补充新内容

---
*配置版本：v1.0*
*最后更新：2026-04-07*
