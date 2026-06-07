#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
12张图表可视化包
运行方式:
    python -m visualizations          # 从 源代码/ 目录
    from visualizations import run_all; run_all()  # 程序化调用
"""

import os
import sys
import io
import traceback

# 设置 stdout 编码（兼容 Windows 中文输出）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from .common import load_all
from config import OUT_DIR

from .chart1_macro_dashboard import generate as generate_chart1
from .chart2_style_rotation import generate as generate_chart2
from .chart3_calendar_heatmap import generate as generate_chart3
from .chart4_bubble_chart import generate as generate_chart4
# 图5暂时移除
# from .chart5_correlation_network import generate as generate_chart5
from .chart6_parallel_coordinates import generate as generate_chart6
from .chart7_factor_waterfall import generate as generate_chart7
from .chart8_crowding_dashboard import generate as generate_chart8
from .chart9_regime_boxplot import generate as generate_chart9
from .chart10_sankey import generate as generate_chart10
from .chart11_stress_test import generate as generate_chart11
from .chart12_alert_dashboard import generate as generate_chart12

CHART_REGISTRY = [
    ('图1 宏观经济周期仪表盘', generate_chart1),
    ('图2 风格轮动热力三角图', generate_chart2),
    ('图3 日历热力图', generate_chart3),
    ('图4 动态气泡图', generate_chart4),
    ('图5 行业相关性网络图', None),  # 暂时移除
    ('图6 平行坐标图', generate_chart6),
    ('图7 因子收益分析', generate_chart7),
    ('图8 因子拥挤度监控', generate_chart8),
    ('图9 牛熊周期箱线图', generate_chart9),
    ('图10 行业配置桑基图', generate_chart10),
    ('图11 压力测试热图', generate_chart11),
    ('图12 实时监控预警仪表盘', generate_chart12),
]


def run_all(data=None):
    """加载数据并生成全部 12 张图表"""
    if data is None:
        data = load_all()

    for name, func in CHART_REGISTRY:
        if func is None:
            print(f"  [{name}] (已跳过)")
            continue
        try:
            print(f"  [{name}]")
            func(data)
        except Exception as e:
            print(f"  ✗ 生成失败: {e}")
            traceback.print_exc()

    print(f"\n可视化完成！输出目录: {os.path.abspath(OUT_DIR)}")
    for f in sorted(os.listdir(OUT_DIR)):
        print(f"  {f}")


if __name__ == '__main__':
    print("=" * 60)
    print("加载数据...")
    data = load_all()
    print(f"  已加载 {len(data)} 个数据集")
    print("\n" + "=" * 60)
    print("生成可视化图表 (金融终端暗色主题)...\n")
    run_all(data=data)
