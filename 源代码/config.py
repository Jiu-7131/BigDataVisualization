#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全局配置 — 路径、配色、Plotly/Matplotlib 主题设置
供所有脚本通过 `from config import ...` 引用
"""

import os

# ---- 项目根目录（基于本文件位置推导） ----
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- 路径常量 ----
DATA_DIR      = os.path.join(PROJECT_ROOT, "数据集")
OUT_DIR       = os.path.join(PROJECT_ROOT, "可视化成果")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
RAW_DATA_DIR  = os.path.join(DATA_DIR, "tushare_all_interfaces")

# 各层处理后数据子目录
PROCESSED_01_INDUSTRY = os.path.join(PROCESSED_DIR, "01_industry")
PROCESSED_02_MACRO    = os.path.join(PROCESSED_DIR, "02_macro")
PROCESSED_03_FACTOR   = os.path.join(PROCESSED_DIR, "03_factor")
PROCESSED_04_DECISION = os.path.join(PROCESSED_DIR, "04_decision")

os.makedirs(OUT_DIR, exist_ok=True)

# ---- 金融终端暗色主题配色 ----
# 背景层次
BG_DARK      = '#0f1923'   # 画布底色 (TradingView 暗色)
BG_PLOT      = '#1a2332'   # 绘图区底色
BG_SIDEBAR   = '#131c27'   # 侧边栏底色
GRID_COLOR   = 'rgba(255,255,255,0.06)'
TEXT_PRIMARY = '#d1d4dc'   # 主文字
TEXT_SECOND  = '#787b86'   # 次要文字
LINE_COLOR   = 'rgba(255,255,255,0.12)'

# 周期 / 风格 / 预警 专业色板 (饱和度降低, 适合暗底)
COLORS = {
    '复苏期': '#4fc3f7', '过热期': '#ef5350', '滞胀期': '#ffb74d',
    '衰退期': '#5c6bc0', '过渡期': '#546e7a',
    '大盘价值': '#90a4ae', '小盘成长': '#ff8a65',
    '大盘成长': '#64b5f6', '小盘价值': '#4db6ac',
    '正常': '#66bb6a', '关注': '#ffee58', '警示': '#ffa726', '危险': '#ef5350',
}

# 行业色板 (多色, 足够31行业)
import plotly.express as px
INDUSTRY_COLORS = px.colors.qualitative.Dark24 + px.colors.qualitative.Light24

# ---- 全局 Plotly 模板 ----
import plotly.io as pio
pio.templates.default = "plotly_dark"

# ---- Matplotlib rcParams ----
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150
plt.rcParams['figure.facecolor'] = BG_DARK
plt.rcParams['axes.facecolor'] = BG_PLOT
plt.rcParams['text.color'] = TEXT_PRIMARY
plt.rcParams['axes.edgecolor'] = '#2a2a3e'
plt.rcParams['axes.labelcolor'] = '#d1d4dc'
plt.rcParams['xtick.color'] = '#787b86'
plt.rcParams['ytick.color'] = '#787b86'
plt.rcParams['grid.color'] = '#1e2a36'
