# api/ — REST API 路由模块

本模块定义了所有 REST API 端点，为后续 Web 前端提供标准化接口。当前通过 CLI 使用，但 API 已完整可用。

## 文件说明

| 文件 | 用途 |
|---|---|
| `routes.py` | 所有 API 路由定义（FastAPI Router） |

## API 端点一览

### 对话
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/chat` | 发送消息，获取回复 |
| POST | `/api/chat/stream` | 流式获取回复（SSE） |

### 知识库
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/knowledge/import` | 导入文件到知识库 |
| GET | `/api/knowledge/{subject}` | 列出知识库已导入资料 |
| DELETE | `/api/knowledge/{subject}` | 清空知识库 |

### 练习
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/exercise/generate` | 生成练习题 |
| POST | `/api/exercise/evaluate` | 单题评判 |
| POST | `/api/exercise/evaluate/batch` | 批量评判 |

### 学生档案
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/student/{id}/{subject}/profile` | 获取学情档案 |
| GET | `/api/student/{id}/{subject}/diagnosis` | 获取 AI 诊断报告 |
| POST | `/api/student/plan` | 生成学习计划 |

### 学科管理
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/subjects` | 列出所有学科 |
| POST | `/api/subjects` | 创建新学科 |
| DELETE | `/api/subjects/{subject}` | 删除学科 |

## 依赖注入

路由所需的客户端和管理器通过 `api_server.py` 中的 `routes.init()` 注入，保持路由函数无状态。
