# 联网搜索功能使用说明

## 功能概述

本模块提供联网搜索功能，使用 Metaso API 进行网页搜索，并将搜索结果与用户问题一起发送给大模型，实现基于实时网络信息的问答。

## 配置

### 1. 设置 API Key

在项目根目录的 `.env` 文件中添加：

```env
METASO_API_KEY=mk-your-api-key-here
```

### 2. 安装依赖

无需额外安装依赖，使用 Python 标准库即可。

## API 接口

### 1. 独立搜索接口

**端点**: `POST /api/web_search`

**请求参数**:
```json
{
  "query": "搜索关键词",
  "max_results": 5  // 可选，默认 5
}
```

**响应示例**:
```json
{
  "success": true,
  "formatted_text": "以下是联网搜索到的相关信息：\n\n【结果 1】\n标题: ...\n来源: ...\n摘要: ...\n\n",
  "raw_data": [
    {
      "title": "标题",
      "url": "网址",
      "snippet": "摘要",
      "summary": "详细摘要"
    }
  ],
  "query": "搜索关键词"
}
```

### 2. 检查功能状态

**端点**: `GET /api/web_search/status`

**响应示例**:
```json
{
  "available": true,
  "api_key_configured": true
}
```

### 3. 集成到聊天流式接口

**端点**: `POST /api/chat_stream`

**请求参数**（在原有参数基础上添加）:
```json
{
  "message": "用户问题",
  "enable_web_search": true,  // 启用联网搜索
  "web_search_query": "自定义搜索关键词",  // 可选，不填则使用用户消息作为搜索词
  "model": "qwen-plus",
  "provider_id": "qwen",
  // ... 其他参数
}
```

## 前端集成示例

### JavaScript 示例

```javascript
// 1. 独立搜索
async function searchWeb(query) {
  const response = await fetch('/api/web_search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      query: query,
      max_results: 5
    })
  });
  
  const result = await response.json();
  
  if (result.success) {
    console.log('搜索结果:', result.formatted_text);
    console.log('原始数据:', result.raw_data);
  } else {
    console.error('搜索失败:', result.error);
  }
}

// 2. 带联网搜索的聊天
async function chatWithWebSearch(message, enableSearch = true) {
  const response = await fetch('/api/chat_stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      message: message,
      enable_web_search: enableSearch,
      model: 'qwen-plus',
      provider_id: 'qwen',
      session_id: getCurrentSessionId()
    })
  });
  
  // 处理流式响应
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    console.log('收到回复:', chunk);
    // 更新 UI
  }
}

// 3. 检查功能状态
async function checkWebSearchStatus() {
  const response = await fetch('/api/web_search/status');
  const status = await response.json();
  
  if (status.available && status.api_key_configured) {
    console.log('联网搜索功能可用');
  } else {
    console.log('联网搜索功能不可用');
  }
}
```

### HTML 示例

```html
<!-- 添加联网搜索开关 -->
<div class="search-toggle">
  <label>
    <input type="checkbox" id="enableWebSearch" />
    启用联网搜索
  </label>
</div>

<!-- 自定义搜索关键词（可选） -->
<div class="search-query" style="display: none;">
  <input type="text" id="webSearchQuery" placeholder="自定义搜索关键词（可选）" />
</div>

<script>
// 监听开关变化
document.getElementById('enableWebSearch').addEventListener('change', function(e) {
  const queryInput = document.querySelector('.search-query');
  queryInput.style.display = e.target.checked ? 'block' : 'none';
});

// 发送消息时包含联网搜索参数
async function sendMessage() {
  const message = document.getElementById('userInput').value;
  const enableWebSearch = document.getElementById('enableWebSearch').checked;
  const webSearchQuery = document.getElementById('webSearchQuery').value;
  
  const requestData = {
    message: message,
    enable_web_search: enableWebSearch,
    model: getSelectedModel(),
    provider_id: getSelectedProvider(),
    session_id: getCurrentSessionId()
  };
  
  // 如果有自定义搜索词，添加到请求中
  if (enableWebSearch && webSearchQuery) {
    requestData.web_search_query = webSearchQuery;
  }
  
  const response = await fetch('/api/chat_stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestData)
  });
  
  // 处理响应...
}
</script>
```

## 工作流程

1. **用户发送消息** → 前端设置 `enable_web_search: true`
2. **后端接收请求** → 检测到启用联网搜索
3. **执行网络搜索** → 调用 Metaso API 搜索相关信息
4. **格式化搜索结果** → 将搜索结果格式化为文本
5. **增强用户消息** → 将搜索结果添加到用户消息前面
6. **调用大模型** → 将增强后的消息发送给大模型
7. **返回回复** → 大模型基于搜索结果和用户问题生成回答

## 搜索结果格式

搜索结果会被格式化为以下格式后发送给大模型：

```
以下是联网搜索到的相关信息：

【结果 1】
标题: Python 3.12 正式发布
来源: https://www.python.org/downloads/
摘要: Python 3.12 是 Python 编程语言的最新主要版本...

【结果 2】
标题: Python 3.12 新特性详解
来源: https://docs.python.org/3.12/whatsnew/
摘要: Python 3.12 带来了许多新特性和改进...

用户问题: Python 最新版本是什么？

请根据以上搜索到的信息回答用户的问题。
```

## 注意事项

1. **API Key 安全**: 不要将 API Key 提交到版本控制系统
2. **搜索频率**: 注意 API 调用频率限制
3. **结果数量**: 默认返回 5 条结果，可根据需要调整
4. **错误处理**: 搜索失败时会记录日志，但不会中断聊天流程
5. **性能影响**: 联网搜索会增加响应时间（通常 1-3 秒）

## 测试

运行测试脚本：

```bash
python web_search/search_api.py
```

这将执行一个简单的搜索测试并输出结果。

## 故障排查

### 问题：搜索功能不可用

**解决方案**:
1. 检查 `.env` 文件中是否配置了 `METASO_API_KEY`
2. 访问 `/api/web_search/status` 检查功能状态
3. 查看后端日志中的错误信息

### 问题：搜索结果为空

**解决方案**:
1. 检查搜索关键词是否合理
2. 尝试使用不同的搜索词
3. 检查 API Key 是否有效

### 问题：响应时间过长

**解决方案**:
1. 减少 `max_results` 参数值
2. 使用更具体的搜索关键词
3. 考虑添加缓存机制

## 扩展功能

可以考虑添加以下功能：

1. **搜索结果缓存**: 避免重复搜索相同内容
2. **搜索历史**: 记录用户的搜索历史
3. **结果过滤**: 根据来源、时间等过滤搜索结果
4. **多搜索引擎**: 支持切换不同的搜索 API
5. **智能搜索词提取**: 自动从用户消息中提取关键词

## 许可证

本模块遵循项目主许可证。
