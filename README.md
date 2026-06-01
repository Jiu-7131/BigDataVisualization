# 股票市场行业轮动与因子收益分析

## AI 工具使用声明

本项目使用了 **Claude Code (Anthropic)** 辅助以下工作：

| 用途 | 说明 |
|------|------|
| 数据处理脚本 | `build_industry_data.py`, `build_macro_cycle.py`, `build_factor_attribution.py`, `build_decision_support.py` 的框架搭建与调试 |
| 可视化脚本 | `visualizations.py` 全部12张图表的 Plotly 代码生成、金融暗色主题适配 |
| 仪表盘 | `build_dashboard.py` 的 HTML/CSS/JS 布局设计与交互逻辑 |
| 项目报告 | 报告文字初稿起草 |

所有 AI 生成的代码均经过人工审查、运行验证与修改，确保逻辑正确、数据准确。

## 项目结构

```
数据集相关/
├── 项目说明.txt              # 运行说明
├── 数据来源说明.txt          # 数据来源文档
├── README.md                 # 本文件
├── 项目报告.html             # 完整项目报告 (浏览器打开 → 打印为PDF)
│
├── 全部数据预处理.py         # 数据获取 (Tushare Pro API)
├── build_industry_data.py    # 行业聚合层处理
├── build_macro_cycle.py      # 宏观环境层处理
├── build_factor_attribution.py  # 因子归因层处理
├── build_decision_support.py # 决策支持层处理
├── visualizations.py         # 12张图表生成 (Plotly)
├── build_dashboard.py        # 综合仪表盘生成
│
├── tushare_all_interfaces/   # 原始数据
├── preprocessed_all_data/    # 预处理后数据
├── processed/                # 最终分析数据 (13 CSV)
│   ├── 01_industry/          # 行业结构层
│   ├── 02_macro/             # 宏观环境层
│   ├── 03_factor/            # 因子归因层
│   └── 04_decision/          # 决策支持层
│
└── visualizations/           # 可视化成果
    ├── index.html            # 综合仪表盘入口
    ├── 01_*.html ~ 12_*.html # 12张交互式图表
    ├── 01_*.png ~ 12_*.png   # 12张高清静态截图
    └── README.md
```

## 运行方式

详见 [项目说明.txt](./项目说明.txt)
