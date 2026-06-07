# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

股票市场行业轮动与因子收益分析 — 大数据可视化课程期末项目。分析 2022–2025 年中国 A 股市场，通过四层数据流水线 + 12 张交互式 Plotly 图表，探索行业轮动、宏观经济周期、因子收益与决策支持。

多人协作项目，远程仓库: `https://github.com/Jiu-7131/BigDataVisualization.git`

## 常用命令

```bash
# 安装依赖
pip install pandas numpy plotly kaleido networkx matplotlib seaborn tqdm

# 数据处理流水线（必须在 源代码/ 目录下按顺序执行）
cd 源代码/
python build_industry_data.py              # 第1层: 行业聚合
python build_macro_cycle.py                # 第2层: 宏观环境
python build_factor_attribution.py         # 第3层: 因子归因
python build_decision_support.py           # 第4层: 决策支持

# 生成可视化
python -m visualizations                   # 12张 HTML + PNG → 可视化成果/
python visualizations.py                   # 兼容：薄包装，同上
python build_dashboard.py                  # 综合仪表盘 → 可视化成果/index.html

# 查看结果：用浏览器打开 可视化成果/index.html

# Git/GitHub（多人协作）
git pull --rebase origin main             # 拉取最新变更
git status && git diff --staged            # 提交前检查
git add <files> && git commit -m "消息"    # 本地提交
git push origin main                       # 推送到远程
```

## Git 工作流

- **分支策略**：直接在 main 上工作（小型团队项目），涉及实验性修改时先开 feature 分支
- **提交规范**：每次有意义的修改后执行一次 commit + push，保持提交粒度适中（一个功能/一个修复 = 一个 commit）
- **Pull 策略**：每次开始工作前先 `git pull --rebase`，避免 merge commit 污染历史
- **Commit 消息格式**：中文，简明扼要说清楚"做了什么"和"为什么"
- **修改后自动提交**：每次完成代码修改（数据处理脚本、图表、配置等）后，确认能正常运行，然后立即 commit + push，使远程始终反映最新状态

## 代码架构

### 四层数据流水线

| 层 | 脚本 | 输出目录 | 产出 |
|---|---|---|---|
| 1. 行业聚合 | `build_industry_data.py` | `processed/01_industry/` | 5 CSV（日度/月度/季度聚合、滚动相关性、聚类） |
| 2. 宏观环境 | `build_macro_cycle.py` | `processed/02_macro/` | 2 CSV（美林时钟周期、风格因子月度数据） |
| 3. 因子归因 | `build_factor_attribution.py` | `processed/03_factor/` | 3 CSV（因子收益、行业归因分解、拥挤度；因子收益率用截面回归法计算） |
| 4. 决策支持 | `build_decision_support.py` | `processed/04_decision/` | 3 CSV + signals/ 子目录（桑基图数据、压力测试、预警仪表盘信号） |

CSV 是层间唯一数据交换格式。每层只读前序层输出的 CSV，不跨层读取原始数据。

### 可视化层

- `config.py` — 全局配置：绝对路径（基于 `__file__` 推导）、TradingView 暗色主题配色、Plotly/Matplotlib 全局设置
- `visualizations/` 包 — 12 个图表文件，每个导出 `generate(data)` 函数
  - `common.py` — `dark_figure()`, `dark_layout()`, `load_all()`, `save()`, `get_gauge_color()`
  - `__init__.py` — 注册表 `CHART_REGISTRY` + `run_all()` 入口
- `visualizations.py` — 向后兼容包装，委托给 `visualizations/` 包

### 图间数据流

```
图1(宏观) ──周期标签──→ 图3(热力图) ──行业胜率──→ 图10(桑基图)
    │                      │                        ↑
    ├──→ 图2(风格)        ├──→ 图4(气泡)          │
    │                      │                        │
    └──→ 图9(箱线图)      ├──→ 图5(网络) ──群落──→ 图6(平行坐标)
                           │                        │
                           └──→ 图6(因子得分) ──→ 图7(瀑布图)
                                    │                    │
                                    └──→ 图8(拥挤度) ←──┘

                          图12(预警) ←── signals/ ←── 图1-11
```

## 关键设计决策（已定案）

以下决策来自 `图表设计文档.md` 的优化讨论，新代码必须遵守：

| 决策 | 内容 |
|---|---|
| 周期判定算法 | 规则引擎（PMI↑+CPI↓=复苏, 等），输出 JSON 含 phase/confidence/drivers |
| 因子收益率 | 在第3层用截面回归法（多空组合）计算，写入 `factor_returns.csv` |
| 图2 图表类型 | 四象限散点图（大小盘溢价 × 价值成长溢价），非三元相图 |
| 交互精简 | 跨图跳改用 URL 参数（`chart6.html?highlight=动量`），放弃实时跨页通信 |
| 实施顺序 | A: 1→2→9 → B: 3→5→6 → C: 4→7→8 → D: 10→11 → E: 12 |

## 每张图的成功标准

每图只回答**一个核心问题**：

| 图 | 核心问题 |
|---|---|
| 1 | 当前处于经济周期的哪个阶段？ |
| 2 | 风格向哪个方向漂移？ |
| 3 | 哪些行业持续跑赢/跑输？ |
| 4 | 行业风险收益如何变化？ |
| 5 | 哪些行业关联性最强？ |
| 6 | 行业在因子空间中的定位？ |
| 7 | 超额收益来自哪些因子？ |
| 8 | 哪些因子过度拥挤？ |
| 9 | 不同周期下哪些行业更好？ |
| 10 | 当前应配置哪些行业？ |
| 11 | 极端情景下哪个行业最脆弱？ |
| 12 | 当前哪些指标预警？ |

## 改动范围约定

**不可动**（已验证/提交，改动需团队讨论）：
- 四层流水线架构和顺序依赖
- `config.py` 的路径推导和配色常量
- `visualizations/common.py` 的工具函数签名
- `visualizations/__init__.py` 的注册表机制

**可动**（单文件范围，不影响其他图表）：
- 各 `chartN_*.py` 的可视化元素和交互逻辑
- 每图的数据处理逻辑（在其文件范围内）

## 颜色与主题

金融暗色主题，TradingView 风格：
- `BG_DARK=#0f1923`, `BG_PLOT=#1a2332`, `BG_SIDEBAR=#131c27`
- 周期色：复苏=蓝、过热=红、滞胀=橙、衰退=紫
- 预警色：正常=绿、关注=黄、警示=橙、危险=红
- 图表用 `dark_figure()` / `dark_layout()` 初始化，配色常量从 `config.py` 引用
