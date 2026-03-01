# benkyou 需求文档 v1.3

## 一、产品概述

**产品名称：** benkyou

**产品形态：** MCP Server + Claude Desktop（或其他支持 MCP 的客户端）

**目标用户：** 使用「大家的日本语」系列教材自学日语的学习者

**核心价值：** 将教材数字化，在 Claude Desktop 中实现按课时查阅知识点、交互式练习批改、词典查询、随时追问的学习体验。

---

## 二、项目目录结构

```
benkyou/
  indexer/          # PDF → Markdown 一次性处理脚本
  mcp-server/       # MCP Server
  mcp-client/       # 后续特化 Client（暂占位）
  data/
    manifest.json   # 数据资产元信息
    elementary-vol1/
      textbook/
        _pages/       # PDF 各页 PNG（可 .gitignore）
        toc.json      # 人工确认后的目录
        lesson_01.md
        ...
      workbook/
        _pages/
        toc.json
        lesson_01.md
        ...
    elementary-vol2/
      ...
  inbox/            # 放置待处理 PDF 的目录
  README.md
```

---

## 三、整体架构

```
PDF
  ↓ indexer/ 脚本（一次性手动执行）
  ↓ 转图片 → VLM 批量处理（OCR + 结构化 + 分界）
按课 Markdown 文件（data/）
        ↓
  MCP Server (mcp-server/)
   ↙              ↘
本地 MD 文件    词典 API（待定）
        ↓
MCP 客户端（Claude Desktop / 自定义 Client）
```

---

## 四、Indexer 设计（一次性脚本）

### 4.1 处理流程

1. PDF 转图片：每页导出为图片（`pymupdf`，存至 `data/<volume>/<type>/_pages/`）
2. 目录页识别：用户通过 `--toc-pages` 指定目录页码范围，将对应图片送给 VLM，输出每课标题和页码范围，生成 `toc.json` 供人工确认，确认前不执行后续步骤
3. 按课批量 OCR + 整理：确认 `toc.json` 后，对每课图片做两轮处理——第一轮逐页提取 Markdown 片段，第二轮将所有片段聚合为一份结构化 Markdown（含 frontmatter）；课与课之间并行处理，每课最多重试 3 次（指数退避）
4. 写入 data/ 目录，更新 manifest.json

### 4.2 使用方式

```bash
# 第一步：生成 toc.json 供确认（--toc-pages 指定目录所在页码范围，1-indexed 闭区间）
python indexer/run.py --pdf inbox/elementary-vol1.pdf --volume elementary-vol1 --type textbook --step toc --toc-pages 3-5

# 人工将 toc.json 中 toc_confirmed 改为 true 后，执行完整处理
python indexer/run.py --pdf inbox/elementary-vol1.pdf --volume elementary-vol1 --type textbook --step index
```

主要 CLI 参数说明：

| 参数            | 说明                                                             |
| --------------- | ---------------------------------------------------------------- |
| `--toc-pages`   | 目录页码范围，如 `3-5`（1-indexed，闭区间），`--step toc` 时必填 |
| `--page-base`   | TOC 页码偏移量，当 PDF 页码与实际页数不一致时使用                |
| `--concurrency` | `--step index` 并行 VLM worker 数（默认 8）                      |
| `--model`       | VLM 模型（默认 `gpt-5-mini-2025-08-07`）                         |

### 4.3 toc.json 格式

```json
{
  "toc_confirmed": false,
  "confirmed_at": null,
  "lessons": [
    { "lesson": 1, "title": "第1課 これはほんです", "page_start": 10, "page_end": 21 },
    { "lesson": 2, "title": "第2課 これはだれのかばんですか", "page_start": 22, "page_end": 33 }
  ]
}
```

`--step index` 执行前会检查 `toc_confirmed: true`，否则中止并提示人工确认。

### 4.4 manifest.json 格式

```json
[
  {
    "volume": "elementary-vol1",
    "type": "textbook",
    "source_pdf": "inbox/elementary-vol1.pdf",
    "generated_at": "2026-02-28",
    "model": "gpt-5-mini-2025-08-07",
    "lessons": 25,
    "status": "complete"
  }
]
```

### 4.5 Markdown 结构规范

课本每课格式：

```markdown
---
volume: elementary-vol1
lesson: 3
type: textbook
title: これはほんです
---

# 第3課 これはほんです

## 単語
| 単語 | 品詞 | 意味 |
| ---- | ---- | ---- |

## 文型

## 例文

## 会話

## 文法
### 语法点1
### 语法点2
```

练习册每课格式：

```markdown
---
volume: elementary-vol1
lesson: 3
type: workbook
title: これはほんです
---

# 第3課 練習

## 問題1
题目内容

### (1)
### (2)

## 問題2
题目内容
```

题号规范：必须连续，统一使用 `## 問題N`，小问统一使用 `### (N)`，不允许混用全角数字或其他格式。

### 4.6 VLM 选型

默认 `gpt-5-mini-2025-08-07`，成本低、日语识别质量好，适合批量处理。代码层面支持 `--model` 参数切换，以应对扫描质量较差的 PDF。

---

## 五、MCP Server 设计

### 5.1 工具列表

**`list_volumes()`**
- 从 manifest.json 读取，返回所有已导入册的名称、类型、课数、状态

**`list_lessons(volume)`**
- 遍历指定册目录，返回所有课编号和标题列表

**`get_lesson(volume, lesson, type)`**
- 返回指定课的完整 Markdown 内容
- type：`textbook` / `workbook`
- 用于场景一整课浏览，以及场景二开始前加载课文上下文

**`get_question_structure(volume, lesson)`**
- 返回指定课练习册的题目结构元数据
- 包含：大题总数、每个大题的题号及小问数量
- 场景二开始时调用，Claude 据此规划逐题推进流程

**`get_question(volume, lesson, question_num)`**
- 返回指定课指定大题的完整内容
- 场景二逐题推进时调用，每次只拉当前大题，避免一次性加载全部题目

**`lookup_word(word)`**
- 通过 `jamdict` 在本地 JMDict 数据库中查词（离线，无需 HTTP）
- 返回：读音、词性、释义
- 由 Claude 在需要时自主调用


### 5.2 技术选型

- 语言：Python
- 框架：`mcp` 官方 Python SDK
- 词典：`jamdict`（本地离线 JMDict 数据库，无需 API Key）

---

## 六、典型交互场景

**场景一：整课浏览**
> 用户：「我要看初级上册第3课」
> Claude：调用 `get_lesson(volume=elementary-vol1, lesson=3, type=textbook)`，一次性展示完整课程内容，包含词汇、文型、例文、会话、语法各节，用户可随时追问

**场景二：练习批改**
> 用户：「我要做初级上册第3课的练习」
> Claude：调用 `get_question_structure(volume=elementary-vol1, lesson=3)` 获取题目结构，了解共几个大题；调用 `get_question(volume=elementary-vol1, lesson=3, question_num=1)` 展示問題1；用户一次性回答所有小问；Claude逐条批改，答对给简要解释，答错给出正确答案及详细解释；用户确认后自动推进到問題2，循环直至全课完成

**场景三：随时追问**
> 用户：「这个単語什么意思」→ Claude 调用 `lookup_word` 查词典，返回读音、词性、释义和例句
> 用户：「て形怎么变」→ Claude 直接用自身知识解释并举例，无需调用工具

---

## 七、未来架构演进

自行实现 MCP Client 做场景特化的 context engineering：

- 会话状态管理：记住当前课，无需每次重复说明
- Context 预加载：对话开始时自动注入当前课 section
- 练习模式：自动逐题推进，结合 `## 問題N / ### (N)` 结构解析题目列表
- 学习数据记录：答题历史、错误率、生词本

MCP Server 侧无需改动，客户端独立迭代。

---

## 八、MVP 范围

**包含：**
- Indexer 脚本（含 toc 确认步骤、manifest 生成）
- MCP Server：5 个 tools
- Claude Desktop 配置文件

**不包含（后续迭代）：**
- 学习进度记录
- 生词本 / 错题本
- 音频 / 发音支持
- 自定义 MCP Client

---

## 九、开发任务拆解

| 阶段 | 任务                                                                      |
| ---- | ------------------------------------------------------------------------- |
| P0   | Indexer：PDF 转图片 + VLM 目录识别 + 生成 toc.json                        |
| P0   | Indexer：toc 确认检查 + 按课批量 OCR + Markdown 生成 + 写入 manifest.json |
| P0   | 人工确认 toc.json + 校对 Markdown 文件                                    |
| P1   | MCP Server 搭建 + tools 实现（含 section 别名归一化）                |
| P1   | Claude Desktop 配置接入                                                   |
| P2   | 端到端测试                                                                |