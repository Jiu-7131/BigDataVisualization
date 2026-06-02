#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图12: 实时监控预警仪表盘"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .common import dark_layout, save
from config import COLORS, TEXT_PRIMARY, TEXT_SECOND, GRID_COLOR


def generate(data):
    df = data['alert'].copy()
    if len(df) == 0:
        print('  (预警数据为空，跳过)')
        return

    df['date'] = pd.to_datetime(df['date'])
    alert_colors_map = {'正常': COLORS['正常'], '关注': COLORS['关注'],
                        '警示': COLORS['警示'], '危险': COLORS['危险']}

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('预警信号时间线', '预警级别分布', '各行业预警次数 Top15', '各指标异常触发次数'),
        specs=[[{"type": "scatter", "colspan": 2}, None],
               [{"type": "bar"}, {"type": "bar"}]],
        vertical_spacing=0.12, horizontal_spacing=0.1,
    )

    for level in ['关注', '警示', '危险']:
        sub = df[df['alert_level'] == level]
        if len(sub) > 0:
            fig.add_trace(go.Scatter(
                x=sub['date'], y=sub['z_score'].abs(),
                mode='markers', name=level,
                marker=dict(color=alert_colors_map[level], size=6,
                           opacity=0.75, line=dict(width=0.5, color='rgba(255,255,255,0.2)')),
                customdata=sub[['industry', 'metric']].values,
                hovertemplate='<b>%{customdata[0]}</b><br>指标: %{customdata[1]}<br>|Z|: %{y:.1f}<extra>%{name}</extra>',
            ), row=1, col=1)

    level_counts = df['alert_level'].value_counts()
    level_order = ['正常', '关注', '警示', '危险']
    level_counts = level_counts.reindex([l for l in level_order if l in level_counts.index])
    fig.add_trace(go.Bar(
        y=level_counts.index, x=level_counts.values, orientation='h',
        marker_color=[alert_colors_map.get(l, '#888') for l in level_counts.index],
        text=level_counts.values, textposition='outside',
        textfont=dict(color=TEXT_PRIMARY, size=11),
        hovertemplate='%{y}: %{x} 次<extra></extra>',
    ), row=2, col=1)

    ind_counts = df['industry'].value_counts().head(15)
    fig.add_trace(go.Bar(
        x=ind_counts.index, y=ind_counts.values,
        marker_color='#5c6bc0', opacity=0.85,
        text=ind_counts.values, textposition='outside',
        textfont=dict(color=TEXT_PRIMARY, size=10),
        hovertemplate='%{x}: %{y} 次<extra></extra>',
    ), row=2, col=2)

    dark_layout(fig, height=750,
                title='实时监控预警仪表盘',
                showlegend=True,
                xaxis=dict(title='', gridcolor=GRID_COLOR),
                xaxis2=dict(title='预警次数', gridcolor=GRID_COLOR),
                xaxis3=dict(title='', tickangle=45, gridcolor=GRID_COLOR),
                yaxis=dict(title='|Z-score|', gridcolor=GRID_COLOR),
                yaxis2=dict(title='', gridcolor=GRID_COLOR),
                yaxis3=dict(title='预警次数', gridcolor=GRID_COLOR),
                legend=dict(font=dict(color=TEXT_SECOND, size=10), orientation='h', y=1.05))
    save(fig, '12_实时监控预警仪表盘')
