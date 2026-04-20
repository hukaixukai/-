# llm/ — LLM 与 Embedding 客户端

本模块封装了与大语言模型和向量嵌入模型的通信接口，所有调用基于 OpenAI 兼容协议。

## 文件说明

| 文件 | 用途 |
|---|---|
| `client.py` | 核心客户端，包含 `ChatClient` 和 `EmbeddingClient` 两个类 |

## 核心类

### `ChatClient`
- `chat(messages, ...)` — 发送对话请求，返回完整回复文本
- `chat_stream(messages, ...)` — 流式返回回复，逐字输出
- 支持参数：`model`、`temperature`、`max_tokens`、`response_format`(JSON模式)

### `EmbeddingClient`
- `embed(texts)` — 批量获取文本向量
- `embed_one(text)` — 获取单条文本向量

## 设计要点

- 使用 `openai.AsyncOpenAI` SDK，通过 `base_url` 指向任意兼容 API
- 同时支持 OpenAI、本地 Ollama、vLLM、MiMo 等任何 OpenAI 兼容端点
- Embedding 客户端可独立配置地址和密钥，与 Chat 使用不同的服务
