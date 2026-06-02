#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图4: 动态气泡图 — 行业风险收益定位"""

import numpy as np
import plotly.express as px

from .common import dark_layout, save
from config import INDUSTRY_COLORS, TEXT_SECOND, GRID_COLOR


def generate(data):
    df = data['ind_q'].copy()
    df = df.dropna(subset=['ann_vol', 'cum_ret', 'total_mv'])
    df['total_mv_b'] = df['total_mv'] / 1e8
    df = df.sort_values('quarter_str')

    fig = px.scatter(
        df,
        x='ann_vol', y='cum_ret', size='total_mv_b',
        color='industry',
        animation_frame='quarter_str',
        hover_name='industry',
        size_max=60,
        color_discrete_sequence=INDUSTRY_COLORS,
        range_x=[df['ann_vol'].quantile(0.02), df['ann_vol'].quantile(0.98)],
        range_y=[df['cum_ret'].quantile(0.02), df['cum_ret'].quantile(0.98)],
        labels={'ann_vol': '年化波动率', 'cum_ret': '季度累计收益', 'total_mv_b': '总市值(百亿)'},
    )

    fig.add_hline(y=0, line_dash="dash", line_color='rgba(255,255,255,0.25)', line_width=1)
    fig.add_vline(x=df['ann_vol'].median(), line_dash="dash",
                  line_color='rgba(255,255,255,0.15)', line_width=1)

    dark_layout(fig, height=720,
                title='行业风险收益定位与迁移 (动态气泡图)',
                xaxis=dict(title='年化波动率', tickformat='.1%', gridcolor=GRID_COLOR),
                yaxis=dict(title='季度累计收益', tickformat='.1%', gridcolor=GRID_COLOR),
                legend=dict(font=dict(size=9, color=TEXT_SECOND)))
    fig.layout.updatemenus[0].buttons[0].args[1]['frame']['duration'] = 800
    save(fig, '04_动态气泡图')
