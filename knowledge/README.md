# knowledge/ — 知识库与 RAG 检索模块

本模块负责将课程资料（PDF、图片、文本）导入为可检索的向量知识库，并支持基于检索增强生成（RAG）的智能问答。

## 文件说明

| 文件 | 用途 |
|---|---|
| `loader.py` | 文档加载与文本分块（PDF/图片OCR/纯文本） |
| `vectorstore.py` | 向量存储：FAISS（优先）或 NumPy 余弦相似度回退 |
| `retriever.py` | RAG 检索器：`KnowledgeBase` 类整合加载→嵌入→检索→生成 |

## 数据流

```
PDF/图片/文本
    ↓  loader.py: 提取文本 + 分块
[chunk1, chunk2, ...]
    ↓  EmbeddingClient: 生成向量
向量 + 元数据
    ↓  vectorstore.py: 构建索引
FAISS/Numpy 索引  ←持久化→  data/subjects/<学科>/vectors/
    ↓  retriever.py: 查询 + LLM生成
带引用的结构化回答
```

## 支持的文件格式

- `.pdf` — 通过 PyMuPDF 提取文本
- `.png/.jpg/.jpeg/.bmp/.tiff/.gif` — OCR 提取文字（需安装 `pytesseract`）
- `.txt/.md/.py/.java/.js/.html/.json/.yaml` 等 — 直接读取

## 存储结构

每个学科在 `data/subjects/<学科名>/vectors/` 下独立存储：
- `index.faiss` 或 `vectors.npy` — 向量索引
- `meta.json` — 分块文本和元数据
- `manifest.json` — 已导入文件清单
