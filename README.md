# 股票市场行业轮动与因子收益分析

## AI 工具使用声明

本项目使用了 **Claude Code (Anthropic)** 辅助以下工作：

| 用途 | 说明 |
|------|------|
| 数据处理脚本 | `build_industry_data.py`, `build_macro_cycle.py`, `build_factor_attribution.py`, `build_decision_support.py` 的框架搭建与调试 |
| 可视化脚本 | `visualizations/` 包全部12张图表的 Plotly 代码生成、金融暗色主题适配 |
| 仪表盘 | `build_dashboard.py` 的 HTML/CSS/JS 布局设计与交互逻辑 |
| 项目报告 | 报告文字初稿起草 |

所有 AI 生成的代码均经过人工审查、运行验证与修改，确保逻辑正确、数据准确。

## 项目结构

```
BigDataVisualization/
├── 项目说明.txt              # 运行说明
├── 数据来源说明.txt          # 数据来源文档
├── README.md                 # 本文件
├── 项目报告.html             # 完整项目报告 (浏览器打开 → 打印为PDF)
├── CLAUDE.md                 # Claude Code 项目指引
│
├── 源代码/                   # 所有 Python 脚本
│   ├── config.py             # 全局配置（路径、配色、Plotly/Matplotlib 主题）
│   ├── 数据获取.py           # 数据获取 (Tushare Pro API)
│   ├── build_industry_data.py    # 第1层: 行业聚合
│   ├── build_macro_cycle.py      # 第2层: 宏观环境
│   ├── build_factor_attribution.py  # 第3层: 因子归因
│   ├── build_decision_support.py # 第4层: 决策支持
│   ├── build_dashboard.py    # 综合仪表盘生成
│   ├── visualizations.py     # 向后兼容薄包装 → visualizations/
│   └── visualizations/       # 图表包（每图独立文件）
│       ├── __init__.py       # 注册表 + run_all() 入口
│       ├── common.py         # 共享工具函数
│       └── chart1_*.py ~ chart12_*.py
│
├── 数据集/                   # 数据目录
│   ├── tushare_all_interfaces/   # 原始数据
│   ├── processed/                # 最终分析数据 (13 CSV)
│   │   ├── 01_industry/          # 行业结构层
│   │   ├── 02_macro/             # 宏观环境层
│   │   ├── 03_factor/            # 因子归因层
│   │   └── 04_decision/          # 决策支持层
│   └── 数据集描述.txt / 预处理说明.txt
│
└── 可视化成果/               # 可视化输出
    ├── index.html            # 综合仪表盘入口
    ├── 01_*.html ~ 12_*.html # 12张交互式图表
    └── 01_*.png ~ 12_*.png   # 12张高清静态截图
```

## 运行方式

详见 [项目说明.txt](./项目说明.txt)
