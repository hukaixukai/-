# exercise/ — 练习生成与评价模块

本模块负责智能化生成练习题并对学生答案进行评价反馈。

## 文件说明

| 文件 | 用途 |
|---|---|
| `generator.py` | 练习题生成器 |
| `evaluator.py` | 答案评判与反馈 |

## `ExerciseGenerator`

根据主题、难度、题型生成练习题：

| 参数 | 可选值 |
|---|---|
| `topic` | 任意知识点名称 |
| `difficulty` | `easy` / `medium` / `hard` |
| `question_type` | `choice`(选择题) / `fill`(填空题) / `short_answer`(简答题) / `coding`(编程题) |
| `count` | 题目数量 |
| `context` | 可选的 RAG 参考资料上下文 |

返回 JSON 结构的题目列表，每题包含：id、type、difficulty、question、options、answer、explanation。

## `ExerciseEvaluator`

- `evaluate(question, correct_answer, student_answer, ...)` — 单题评判，返回反馈文本
- `evaluate_batch(questions, student_answers, ...)` — 批量评判，返回各题结果和总分
- 自动将结果记录到 `StudentMemory`（知识点记录 + 错误记录 + 测验成绩）
