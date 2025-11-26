# 聊天页面功能设计文档

## 一、项目概述
为Anthropic OpenAI Bridge项目添加一个完整的聊天对话页面，集成到现有管理界面中，支持多供应商/多模型选择、流式输出和历史对话记录。

## 二、需求分析

### 功能需求
1. **模型选择器**
   - 三级联动选择：供应商 → API格式 → 具体模型
   - 从provider.json动态读取配置
   - 支持精确选择模型（如moonshotai/Kimi-K2-Thinking）

2. **对话输入与发送**
   - 文本输入框
   - 发送按钮
   - 调用后端/v1/messages接口
   - 使用message_service.py中的handle_message实现

3. **流式输出展示**
   - 实时展示AI回复
   - 类似Claude官方界面的打字机效果

4. **历史对话记录**
   - 数据库存储
   - 查看历史对话列表
   - 加载历史对话内容

### 技术栈
- 后端：FastAPI + SQLite + Pydantic
- 前端：Svelte 5 + TypeScript + SvelteKit
- 接口：RESTful API + Server-Sent Events (SSE)

## 三、数据库设计

### 新增表结构
```sql
-- 对话会话表
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    provider_name TEXT,
    api_format TEXT,
    model TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_updated_at ON conversations(updated_at);

-- 对话消息表
CREATE TABLE IF NOT EXISTS conversation_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role TEXT NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX idx_messages_conversation_id ON conversation_messages(conversation_id);
CREATE INDEX idx_messages_created_at ON conversation_messages(created_at);
```

## 四、后端API设计

### 1. 对话管理API

#### GET /api/conversations
获取当前用户的对话列表
- **认证**: 需要登录
- **参数**: limit, offset
- **响应**: 对话列表（id, title, provider_name, model, created_at, updated_at）

#### GET /api/conversations/{id}
获取单个对话的详细信息（包括消息）
- **认证**: 需要登录
- **响应**: 对话详情 + 消息列表

#### POST /api/conversations
创建新对话
- **认证**: 需要登录
- **请求**: {provider_name, api_format, model, first_message}
- **响应**: 创建的对话对象

#### PUT /api/conversations/{id}
更新对话（重命名）
- **认证**: 需要登录
- **请求**: {title}

#### DELETE /api/conversations/{id}
删除对话
- **认证**: 需要登录

### 2. 聊天API（复用现有）

#### POST /v1/messages
发送消息（已存在）
- **认证**: API Key验证
- **功能**: 复用MessageService.handle_messages实现
- **流式**: 支持SSE流式输出

## 五、前端页面设计

### 页面结构
路由: `/chat`

#### 布局组件
```
┌─────────────────────────────────────┐
│  Header (包含聊天导航项)            │
├──────────┬──────────────────────────┤
│          │                          │
│ Sidebar  │      Main Chat Area      │
│ (History)│                          │
│          │  ┌─────────────────────┐ │
│          │  │  Model Selector     │ │
│          │  ├─────────────────────┤ │
│          │  │                     │ │
│          │  │  Messages           │ │
│          │  │                     │ │
│          │  ├─────────────────────┤ │
│          │  │  Input Box          │ │
│          │  └─────────────────────┘ │
│          │                          │
└──────────┴──────────────────────────┘
```

### 组件设计

#### 1. 模型选择器 (ModelSelector.svelte)
- 三级联动下拉菜单
- 从`/api/providers`加载配置
- 数据结构：
  ```typescript
  interface ModelChoice {
    providerName: string;
    apiFormat: string;
    model: string;  // 完整模型名如"moonshotai/Kimi-K2-Thinking"
  }
  ```

#### 2. 对话历史侧边栏 (ConversationSidebar.svelte)
- 显示历史对话列表
- 支持新建对话
- 支持删除对话
- 显示标题、模型、时间

#### 3. 聊天区域 (ChatArea.svelte)
- 消息展示（用户/助手）
- Markdown渲染
- 代码高亮
- 流式输出动画

#### 4. 输入框 (MessageInput.svelte)
- 多行文本输入
- 发送按钮
- Enter发送，Shift+Enter换行

### 状态管理
```typescript
interface ChatState {
  conversations: Conversation[];  // 对话列表
  currentConversation: Conversation | null;  // 当前对话
  messages: Message[];  // 当前对话消息
  selectedModel: ModelChoice | null;
  isLoading: boolean;
  streamingMessage: string | null;
}
```

## 六、实现步骤

### 阶段1: 数据库层
1. 修改`backend/app/database/core.py`
   - 添加conversations表创建SQL
   - 添加conversation_messages表创建SQL

2. 创建`backend/app/database/conversations.py`
   - ConversationsManager类
   - 实现CRUD操作

### 阶段2: 后端API
1. 创建`backend/app/api/conversations.py`
   - 对话管理路由
   - 认证和权限控制

2. 修改`backend/app/main.py`
   - 注册新的conversations路由

### 阶段3: 前端页面
1. 修改`frontend/src/routes/+layout.svelte`
   - 添加聊天导航项

2. 创建`frontend/src/routes/chat/+page.svelte`
   - 主聊天页面
   - 集成Sidebar和ChatArea

3. 创建组件：
   - `frontend/src/lib/components/chat/ModelSelector.svelte`
   - `frontend/src/lib/components/chat/ConversationSidebar.svelte`
   - `frontend/src/lib/components/chat/ChatArea.svelte`
   - `frontend/src/lib/components/chat/MessageInput.svelte`
   - `frontend/src/lib/components/chat/MessageBubble.svelte`

4. 创建聊天服务：
   - `frontend/src/lib/services/chatService.ts`
   - 对话管理API调用
   - SSE流式处理

### 阶段4: 集成与优化
1. 对接/v1/messages接口
2. 实现流式输出展示
3. 错误处理和用户反馈
4. 响应式布局优化

## 七、关键技术点

### 1. 流式输出实现
```typescript
// 前端SSE处理示例
const response = await fetch('/v1/messages', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${apiKey}`
  },
  body: JSON.stringify(requestBody)
});

const reader = response.body?.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  const lines = chunk.split('\n\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      // 处理流式数据，更新UI
    }
  }
}
```

### 2. 消息格式转换
- Anthropic格式 → OpenAI格式（后端已实现）
- 前端只需要处理Anthropic格式
- 消息类型：message_start, content_block_delta, message_stop

### 3. 历史记录管理
- 自动提取第一消息生成标题
- Token用量统计展示
- 时间戳格式化

## 八、界面设计参考

### 视觉风格
- 沿用现有管理界面风格
- 深色/浅色主题支持
- 卡片式消息布局
- 渐进式加载动画

### 交互设计
- 快捷键支持（Enter发送）
- 加载状态指示
- 错误提示Toast
- 移动端适配

## 九、测试要点

1. **后端测试**
   - 对话CRUD操作
   - 用户权限验证
   - 消息历史查询性能

2. **前端测试**
   - 模型选择器联动
   - SSE流式输出稳定性
   - 历史记录加载

3. **集成测试**
   - 端到端对话流程
   - 错误场景处理
   - 并发请求处理

## 十、部署与监控

### 数据库迁移
```bash
# 启动时自动创建新表
python backend/start_proxy.py
```

### 监控指标
- 对话数量统计
- 消息响应时间
- Token使用量
- 错误率监控

---

**文档版本**: 1.0
**创建时间**: 2025-11-26
**最后更新**: 2025-11-26
