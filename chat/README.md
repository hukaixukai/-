# chat/ — 对话会话管理模块

本模块管理按学科隔离的聊天会话，包含会话生命周期、系统提示词和历史压缩。

## 文件说明

| 文件 | 用途 |
|---|---|
| `session.py` | 会话管理：`ChatSession`（单个学科会话）+ `SessionManager`（多学科管理） |
| `prompts.py` | 各场景的系统提示词模板 |
| `compressor.py` | 聊天历史压缩与持久化 |

## 核心类

### `ChatSession`
- `send(message)` — 发送消息并获取回复（自动管理历史）
- `send_stream(message)` — 流式获取回复
- `clear_history()` — 清空当前学科对话历史

### `SessionManager`
- `get_session(subject)` — 获取或创建学科会话
- `list_subjects()` — 列出所有有历史记录的学科
- `delete_subject(subject)` — 删除学科及其所有数据

### `HistoryCompressor`
- 当消息数超过 `COMPRESSION_THRESHOLD`（默认10条）时自动触发
- 用 LLM 将旧消息压缩为摘要，保留最近的原始消息
- 摘要以 `system` 角色消息插入历史开头

## 系统提示词（`prompts.py`）

| 常量 | 用途 |
|---|---|
| `STUDY_COMPANION_SYSTEM` | 学伴主对话人设（结构化回答：定义→原理→示例→易错点） |
| `RAG_QA_SYSTEM` | RAG 问答：基于参考资料回答 |
| `EXERCISE_GENERATION_SYSTEM` | 出题：JSON 格式生成练习题 |
| `EXERCISE_EVALUATION_SYSTEM` | 评判：对学生答案进行评价和反馈 |
| `DIAGNOSTICS_SYSTEM` | 学情诊断：分析薄弱知识点 |
| `PLANNING_SYSTEM` | 学习规划：制定个性化学习计划 |
| `HISTORY_COMPRESSION_SYSTEM` | 历史压缩：摘要旧对话 |

## 存储结构

聊天历史按学科存储在 `data/subjects/<学科名>/<学科名>_history.json`。
