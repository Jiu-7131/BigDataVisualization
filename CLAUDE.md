# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 行为准则

以下准则源自 Andrej Karpathy 的 CLAUDE.md，用于减少 LLM 编码中的常见错误。
对于简单任务可用自己的判断，不必死板遵循。

### 1. 先思考再编码

**不假设、不隐藏困惑、明确说出取舍。**

实现之前：
- 明确说出你的假设。如果不确定，先问。
- 如果存在多种理解方式，列出来 — 不要悄悄选择。
- 如果有更简单的方式，说出来。必要时应提出异议。
- 如果有不清楚的地方，停下来，指出哪里困惑，然后问。

### 2. 简洁优先

**用最少代码解决问题。不写臆测性代码。**

- 不添加用户没要求的功能。
- 不为只使用一次的代码创建抽象。
- 不添加不会被触发的错误处理。
- 如果你写了 200 行而 50 行就够了，重写。

自问："一个资深工程师会认为这过度复杂吗？" 如果是，简化。

### 3. 精准修改

**只改必须改的。只清理自己造成的混乱。**

编辑已有代码时：
- 不要"顺便优化"相邻代码、注释或格式。
- 不要重构没坏的东西。
- 匹配已有代码风格，即使你自己的做法不同。
- 如果你发现无关的死代码，提出来 — 但不要删除。

当你引入的变更造成了孤立代码（未使用的 import/变量/函数）：
- 删除掉你引入的变更所造成的孤立代码。
- 不要删除预先存在的死代码，除非用户要求。

检验标准：每一行改动都应该能追溯到用户的需求。

### 4. 目标驱动执行

**定义成功标准。循环直到验证通过。**

将任务转化为可验证的目标：
- "添加验证" → "为无效输入写测试，然后让它通过"
- "修 bug" → "写一个能复现的测试，然后让它通过"
- "重构 X" → "确保重构前后测试都通过"

对多步骤任务，先简述方案，每步带验证检查点。
强的成功标准让你能独立循环推进，弱的标准（"让它能跑"）需要不断问用户。

---

## 项目概述

股票市场行业轮动与因子收益分析 — 大数据可视化课程期末项目。

分析 2022-2025 年中国 A 股市场，通过四层数据处理流水线生成 12 张交互式 Plotly 图表，探索行业轮动、宏观经济周期、因子收益与决策支持。

## 常用命令

```bash
# 安装依赖
pip install pandas numpy plotly kaleido networkx matplotlib seaborn tqdm scikit-learn

# 数据处理流水线（必须在 源代码/ 目录下按顺序执行）
cd 源代码/
python build_industry_data.py      # 第1层: 行业聚合 → processed/01_industry/
python build_macro_cycle.py        # 第2层: 宏观环境 → processed/02_macro/
python build_factor_attribution.py # 第3层: 因子归因 → processed/03_factor/
python build_decision_support.py   # 第4层: 决策支持 → processed/04_decision/

# 生成可视化
python visualizations.py           # 12 张 HTML 图表 + PNG 截图 → visualizations/
python build_dashboard.py          # 综合仪表盘 → visualizations/index.html

# 查看结果：用浏览器打开 visualizations/index.html
```

## 代码架构

### 四层数据流水线

| 层 | 脚本 | 输出目录 | 产出 CSV |
|---|---|---|---|
| 1. 行业聚合 | `build_industry_data.py` | `processed/01_industry/` | 5 个（日度/月度/季度聚合、滚动相关性、聚类） |
| 2. 宏观环境 | `build_macro_cycle.py` | `processed/02_macro/` | 2 个（美林时钟周期、风格因子月度数据） |
| 3. 因子归因 | `build_factor_attribution.py` | `processed/03_factor/` | 3 个（因子收益、行业归因分解、拥挤度） |
| 4. 决策支持 | `build_decision_support.py` | `processed/04_decision/` | 3 个（桑基图数据、压力测试、预警仪表盘） |

每层读取上一层输出的 CSV，产出本层 CSV。CSV 是层间唯一的数据交换格式。

### 可视化层

- `visualizations.py` — 所有 12 张图表的生成逻辑集中在此单文件中（约 850 行），每张图表对应一个独立函数（`chart1_macro_dashboard` ~ `chart12_alert_dashboard`），在文件底部注册到列表中按序生成。
- `build_dashboard.py` — 生成纯 HTML/CSS/JS 综合仪表盘（无框架），左侧边栏导航，iframe 嵌入各图表。

### 金融暗色主题

配色常量定义在 `visualizations.py:29-47`，风格模仿 TradingView/Bloomberg 暗色终端：
- 背景三层：`BG_DARK`（画布底）、`BG_PLOT`（绘图区）、`BG_SIDEBAR`（侧边栏）
- 周期/风格/预警色映射在 `COLORS` 字典中
- 工具函数 `dark_figure()` 和 `dark_layout()` 统一应用主题

### 数据来源

Tushare Pro API，需注册获取 token。原始数据不包含在仓库中，`数据集/` 目录仅含获取说明。数据预处理脚本 `全部数据预处理.py` 负责下载和清洗。

## 关键约定

- **相对路径**：所有脚本使用相对路径，必须从 `源代码/` 目录运行，否则数据目录找不到。
- **中文命名**：输出文件名、图表标题、数据列名、代码注释全部使用中文。行业分类遵循申万一级行业标准（31 个行业）。
- **数据不入库**：原始数据和预处理数据不在版本控制中。
- **单文件图表**：所有图表在一个 `visualizations.py` 中，添加新图表时遵循已有函数命名模式 `chart{N}_{name}` 并在底部注册列表中加入。
