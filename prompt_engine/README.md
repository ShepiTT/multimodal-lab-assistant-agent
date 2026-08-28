# Prompt 引擎模块

## 概述

Prompt 引擎是智能体理解实验室复杂意图的关键模块。本模块针对四大业务场景设计了动态提示词模板，能够根据用户输入自动识别场景并生成优化的提示词。

## 四大业务场景

### 1. 操作指导场景 (Operation Guide)

**特点**：
- 强调步骤的原子性与顺序感
- 每个步骤独立完整，可单独执行
- 包含预期结果验证

**输出格式**：
```
## 步骤 N：[操作名称]
**操作内容**：[具体操作描述]
**预期结果**：[完成后应看到的结果]
**注意事项**：[需要特别注意的点]
```

**适用场景**：
- 设备操作指南
- 软件使用教程
- 配置步骤说明

### 2. 故障诊断场景 (Fault Diagnosis)

**特点**：
- 采用思维链（CoT）引导逻辑推理
- 按照"现象-成因-对策"三段式输出
- 提供多个可能原因及验证方法

**输出格式**：
```
## 📋 故障现象
[详细描述]

## 🔍 成因分析（思维链推理）
### 可能原因 1：[原因名称]
**推理过程**：[逻辑推理步骤]
**可能性**：⭐⭐⭐⭐⭐
**验证方法**：[如何验证]

## 🛠️ 解决对策
[具体解决方案]
```

**适用场景**：
- 设备故障排查
- 系统异常诊断
- 错误原因分析

### 3. 安全规范场景 (Safety Regulation)

**特点**：
- 设定极高的警示优先级
- 安全预警信息处于显著位置
- 使用醒目的标记符号

**输出格式**：
```
## 🚨 安全警示（必须首先显示）
### ⚠️ 风险等级：[高危/中危/低危]

**禁止事项**：
❌ [绝对不能做的事情]

**必须遵守**：
✅ [必须执行的安全措施]

**潜在风险**：
⚡ [可能发生的危险]
```

**适用场景**：
- 高危操作警告
- 安全规范说明
- 风险提示

### 4. 代码调试场景 (Code Debug)

**特点**：
- 以 Diff 格式或代码注释形式指出错误
- 提供修复后的代码片段
- 说明错误原因和修复逻辑

**输出格式**：
```
## 🐛 错误诊断
**文件**：[文件名]
**行号**：[具体行号]
**错误类型**：[错误分类]

### 错误代码
```python
# ❌ 错误代码
[原始代码]
```

## ✅ 修复方案
### 修复后代码
```python
# ✅ 修复后代码
[修复后的代码]
```

### Diff 格式
```diff
- [删除的代码]
+ [添加的代码]
```
```

**适用场景**：
- 代码错误修复
- 代码审查
- 性能优化建议

## 使用方法

### 1. 基础使用

```python
from prompt_engine import get_prompt_engine, ScenarioType

# 获取引擎实例
engine = get_prompt_engine()

# 生成操作指导场景的提示词
prompt = engine.generate_prompt(
    scenario=ScenarioType.OPERATION_GUIDE
)

# 增强用户消息
enhanced_message = engine.enhance_user_message(
    user_message="如何设置设备参数？",
    scenario=ScenarioType.OPERATION_GUIDE
)
```

### 2. 自动场景检测

```python
from prompt_engine.api_integration import detect_scenario_from_message

# 自动检测场景
message = "设备无法启动，怎么办？"
scenario = detect_scenario_from_message(message)
# 返回: ScenarioType.FAULT_DIAGNOSIS
```

### 3. 与聊天接口集成

```python
from prompt_engine.api_integration import integrate_with_chat_stream

# 自动增强消息和生成系统提示词
enhanced_message, system_prompt = integrate_with_chat_stream(
    user_message="如何更换电池？",
    auto_detect=True,  # 自动检测场景
    knowledge_base_context="设备型号: XYZ-100"
)
```

### 4. API 接口使用

#### 获取场景列表
```bash
GET /api/prompt_engine/scenarios
```

响应：
```json
{
  "success": true,
  "scenarios": [
    {
      "type": "operation_guide",
      "name": "操作指导场景",
      "description": "强调步骤的原子性与顺序感",
      "output_format": "步骤化列表"
    },
    ...
  ]
}
```

#### 生成场景化提示词
```bash
POST /api/prompt_engine/generate
Content-Type: application/json

{
  "scenario": "operation_guide",
  "user_context": {
    "device": "设备名称",
    "version": "版本号"
  },
  "custom_constraints": [
    "约束条件1",
    "约束条件2"
  ]
}
```

响应：
```json
{
  "success": true,
  "prompt": "生成的完整提示词...",
  "scenario_info": {
    "name": "操作指导场景",
    "description": "...",
    ...
  }
}
```

#### 增强用户消息
```bash
POST /api/prompt_engine/enhance_message
Content-Type: application/json

{
  "message": "用户原始消息",
  "scenario": "fault_diagnosis",
  "knowledge_base_context": "知识库上下文"
}
```

响应：
```json
{
  "success": true,
  "original_message": "用户原始消息",
  "enhanced_message": "增强后的消息..."
}
```

## 在聊天接口中使用

在 `/api/chat_stream` 接口中，Prompt 引擎已自动集成：

```javascript
// 前端请求示例
fetch('/api/chat_stream', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message: "如何设置设备参数？",
    enable_prompt_engine: true,  // 启用 Prompt 引擎（默认启用）
    scenario_type: "operation_guide",  // 可选：指定场景类型
    // 其他参数...
  })
})
```

**参数说明**：
- `enable_prompt_engine`: 是否启用 Prompt 引擎（默认 `true`）
- `scenario_type`: 指定场景类型（可选），如果不指定则自动检测
  - 可选值：`operation_guide`, `fault_diagnosis`, `safety_regulation`, `code_debug`

## 场景检测关键词

系统会根据以下关键词自动检测场景：

| 场景 | 关键词 |
|------|--------|
| 操作指导 | 如何、怎么、步骤、操作、使用、设置、配置、how to、step、guide |
| 故障诊断 | 故障、错误、异常、不工作、失败、问题、为什么、error、fault、bug |
| 安全规范 | 安全、危险、风险、注意、警告、禁止、不能、safety、danger、warning |
| 代码调试 | 代码、调试、修复、debug、fix、code、函数、语法、逻辑、性能 |

## 测试

运行测试脚本：

```bash
python test_prompt_engine.py
```

测试内容包括：
1. 场景列表获取
2. 场景自动检测
3. 提示词生成
4. 消息增强

## 扩展

### 添加新场景

1. 在 `ScenarioType` 枚举中添加新场景类型
2. 在 `PromptEngine._initialize_templates()` 中添加场景模板
3. 实现对应的 `_build_xxx_prompt()` 方法
4. 在 `detect_scenario_from_message()` 中添加关键词检测逻辑

### 自定义约束条件

```python
prompt = engine.generate_prompt(
    scenario=ScenarioType.OPERATION_GUIDE,
    custom_constraints=[
        "必须使用中文输出",
        "每个步骤不超过50字",
        "包含图片说明"
    ]
)
```

## 注意事项

1. **场景优先级**：如果同时指定 `scenario_type` 和启用自动检测，以 `scenario_type` 为准
2. **系统提示词覆盖**：场景化的系统提示词会覆盖默认的系统提示词
3. **知识库集成**：Prompt 引擎会自动整合知识库上下文到增强消息中
4. **性能考虑**：场景检测基于关键词匹配，性能开销很小

## 架构设计

```
prompt_engine/
├── __init__.py              # 模块导出
├── prompt_templates.py      # 核心引擎和模板定义
├── api_integration.py       # Flask API 集成
└── README.md               # 本文档
```

**核心类**：
- `PromptEngine`: 提示词引擎核心类
- `ScenarioType`: 场景类型枚举

**核心函数**：
- `get_prompt_engine()`: 获取引擎单例
- `detect_scenario_from_message()`: 自动场景检测
- `integrate_with_chat_stream()`: 与聊天接口集成

## 版本历史

- **v1.0.0** (2026-01-08)
  - 初始版本
  - 支持四大业务场景
  - 自动场景检测
  - API 接口集成
