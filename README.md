# 智能学伴 — Intelligent Study Companion

一个基于大语言模型的 AI 智能学习辅助系统，面向具体课程（如数据结构、Python编程、大学英语等），提供智能问答、知识库检索（RAG）、学情诊断、练习生成、个性化学习计划等完整学习支持功能。

## 快速开始

### 1. 环境要求

- **Python** >= 3.11
- **操作系统**：Windows / macOS / Linux

### 2. 安装依赖

```bash
cd new-agent
pip install openai fastapi uvicorn rich python-dotenv numpy Pillow pydantic
pip install PyMuPDF           # PDF 文本提取（必需）
pip install faiss-cpu          # 向量检索加速（可选，无则自动回退到 NumPy）
pip install pytesseract        # 图片 OCR（可选，仅需识别图片中的文字时）
```

### 3. 配置 API

复制 `.env.example` 为 `.env`，填入你的 API 信息：

```bash
cp .env.example .env
```

`.env` 内容：

```env
# LLM 接口（任何 OpenAI 兼容 API 均可）
LLM_API_BASE=https://api.openai.com/v1
LLM_API_KEY=sk-your-api-key
LLM_MODEL=gpt-4o-mini

# Embedding 接口（可与 LLM 共用同一服务）
EMBEDDING_API_BASE=https://api.openai.com/v1
EMBEDDING_API_KEY=sk-your-api-key
EMBEDDING_MODEL=text-embedding-3-small
```

支持的 API 提供商（任选其一）：
- OpenAI
- 本地 Ollama（`http://localhost:11434/v1`）
- vLLM 本地部署
- MiMo API
- 其他任何 OpenAI 兼容端点

### 4. 运行

**CLI 交互式界面（主要入口）：**

```bash
python main.py
```

**REST API 服务器（为 Web 前端预留）：**

```bash
python api_server.py
# 启动后访问 http://127.0.0.1:8080/docs 查看 API 文档
```

## 项目结构

```
new-agent/
├── main.py                 # CLI 入口
├── api_server.py           # API 服务器入口
├── config.py               # 全局配置（从 .env 加载）
├── models.py               # Pydantic 数据模型
│
├── llm/                    # LLM 与 Embedding 客户端
│   └── client.py
│
├── knowledge/              # 知识库与 RAG 检索
│   ├── loader.py           #   文档加载与分块
│   ├── vectorstore.py      #   向量存储（FAISS/NumPy）
│   └── retriever.py        #   RAG 检索生成
│
├── chat/                   # 对话会话管理
│   ├── session.py          #   多学科会话管理
│   ├── prompts.py          #   系统提示词
│   └── compressor.py       #   历史压缩与持久化
│
├── student/                # 学生档案与诊断
│   ├── memory.py           #   学习记忆文件（JSON）
│   ├── diagnostics.py      #   学情诊断分析
│   └── planner.py          #   个性化学习计划
│
├── exercise/               # 练习与评价
│   ├── generator.py        #   练习题生成
│   └── evaluator.py        #   答案评判反馈
│
├── api/                    # REST API 路由
│   └── routes.py           #   20 个 API 端点
│
├── cli/                    # Rich 命令行界面
│   └── interface.py        #   交互式菜单与对话
│
└── data/                   # 运行时数据（自动创建）
    ├── subjects/           #   按学科存储（知识库+历史）
    └── students/           #   按学生存储（记忆档案）
```

## 核心功能

### 1. 智能问答

学生可以自然语言提问，系统基于课程知识库给出结构化回答（定义 → 原理 → 示例 → 易错点）。对话中自动判断是否需要检索知识库。

### 2. 知识库检索（RAG）

支持导入 PDF、图片、文本文件作为课程知识库。系统会将资料切分为文本块，生成向量索引。学生提问时自动检索最相关的参考资料，基于真实资料生成回答，减少幻觉。

### 3. 学情诊断

系统自动记录学生的答题情况、错误模式、测验成绩。通过统计分析识别薄弱知识点和掌握较好的知识点，可生成详细的 AI 诊断报告。

### 4. 练习生成与评价

支持四种题型：选择题、填空题、简答题、编程题。可根据指定主题、难度智能生成题目，学生作答后即时评判并给出解析。所有结果自动记录到学生档案。

### 5. 个性化学习计划

基于学生的学情诊断结果、薄弱知识点和可用时间，AI 自动生成阶段性的学习计划安排。

### 6. 学习过程记录

- **对话历史**：按学科独立存储，支持 LLM 自动压缩旧消息
- **学生档案**：按学生+学科独立存储知识点掌握、错误记录、测验成绩
- **知识库清单**：记录每个学科导入了哪些资料

### 7. 多学科独立

每个学科拥有独立的：
- 聊天历史文件
- 知识库向量索引
- 学生记忆档案

切换学科时互不干扰。

## 运行原理

```
┌──────────────┐     ┌──────────────────────────────────────────┐
│  CLI 前端    │     │              后端核心                      │
│  (Rich TUI)  │────▶│                                          │
│              │◀────│  ┌─────────┐  ┌──────────┐  ┌─────────┐  │
└──────────────┘     │  │ Chat    │  │ Knowledge│  │ Student │  │
                     │  │ Session │  │ Base     │  │ Memory  │  │
┌──────────────┐     │  │         │  │ (RAG)    │  │         │  │
│  REST API    │────▶│  └────┬────┘  └────┬─────┘  └────┬────┘  │
│  (FastAPI)   │◀────│       │            │             │        │
└──────────────┘     │       ▼            ▼             ▼        │
                     │  ┌─────────────────────────────────────┐  │
                     │  │        LLM Client (OpenAI API)      │  │
                     │  │   Chat  +  Embedding                │  │
                     │  └─────────────────────────────────────┘  │
                     └──────────────────────────────────────────┘
```

**对话流程**：
1. 学生输入问题
2. 如果知识库有内容 → 检索相关段落 → 构建 RAG 提示词 → LLM 生成有依据的回答
3. 如果知识库为空 → 直接 LLM 对话
4. 回复自动追加到历史，超过阈值时压缩旧消息
5. 答题结果写入学生记忆档案

## API 文档

启动 API 服务器后访问 `http://127.0.0.1:8080/docs` 查看完整的 Swagger 文档。

主要端点：

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/chat` | 发送消息 |
| POST | `/api/chat/stream` | 流式对话 |
| POST | `/api/knowledge/import` | 导入知识库文件 |
| POST | `/api/exercise/generate` | 生成练习题 |
| POST | `/api/exercise/evaluate` | 评判答案 |
| GET | `/api/student/{id}/{subject}/profile` | 学情档案 |
| POST | `/api/student/plan` | 生成学习计划 |
| GET | `/api/subjects` | 学科列表 |

详见 [api/README.md](api/README.md)。

## 数据存储

所有运行时数据存储在 `data/` 目录下，无需数据库：

```
data/
├── subjects/
│   └── <学科名>/
│       ├── vectors/              # 向量索引
│       │   ├── index.faiss       #   FAISS 索引（或 vectors.npy）
│       │   └── meta.json         #   文本块元数据
│       ├── <学科名>_history.json  # 聊天历史
│       └── manifest.json         # 知识库导入清单
│
└── students/
    └── <学生ID>/
        └── <学科名>_memory.json   # 学习记忆档案
```

## 未来拓展方向

- **Web 前端**：基于 REST API 构建浏览器端界面，替代 CLI
- **多模态输入**：支持学生拍照上传手写答案，OCR 识别后评判
- **语音交互**：接入语音识别/合成，实现口语化学习辅导
- **协作学习**：多学生共享知识库，支持学习小组模式
- **知识图谱**：将知识点关联构建图谱，可视化学习路径
- **自适应难度**：根据学生表现动态调整出题难度
- **离线模式**：集成本地模型（Ollama），无需联网即可使用
- **学习报告**：定期生成 PDF 学习报告，邮件推送
- **数据库后端**：将 JSON 文件迁移至 SQLite/PostgreSQL 以支持更大规模
