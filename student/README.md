# student/ — 学生档案、学情诊断与学习规划模块

本模块为每位学生建立按学科独立的学习记忆档案，基于档案数据进行学情分析，并生成个性化学习计划。

## 文件说明

| 文件 | 用途 |
|---|---|
| `memory.py` | 学生学习记忆文件（JSON 持久化） |
| `diagnostics.py` | 学情诊断：统计分析 + LLM 深度诊断 |
| `planner.py` | 个性化学习计划生成 |

## 数据流

```
学生答题/提问
    ↓
StudentMemory.record_topic() / record_error() / record_quiz()
    ↓  持久化到 JSON
data/students/<student_id>/<subject>_memory.json
    ↓
LearningDiagnostics.analyze()  →  统计诊断结果
LearningDiagnostics.diagnose() →  LLM 自然语言诊断报告
    ↓
LearningPlanner.generate_plan() →  个性化学习计划
```

## `StudentMemory` 记录内容

| 字段 | 说明 |
|---|---|
| `topics` | 每个知识点的正确/错误次数 |
| `errors` | 具体错误记录（题目、学生答案、正确答案） |
| `quiz_scores` | 测验成绩记录 |
| `question_log` | 学生提问历史 |
| `weak_points` | 自动识别的薄弱知识点（错误率 > 40%） |
| `strong_points` | 自动识别的掌握较好的知识点（正确率 > 80%） |

## 存储结构

```
data/students/<student_id>/
├── 数据结构_memory.json
├── Python编程_memory.json
└── ...
```

每位学生、每个学科都有独立的记忆文件，互不干扰。
