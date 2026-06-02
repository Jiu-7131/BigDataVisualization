#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图8: 因子拥挤度监控仪表"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .common import dark_layout, save
from config import COLORS, GRID_COLOR


def generate(data):
    df = data['factor_crowd'].copy()

    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=('估值价差 (PB Top−Bottom)', '因子内相关性', '综合拥挤度分数'),
        vertical_spacing=0.08,
        shared_xaxes=True,
    )

    fig.add_trace(go.Scatter(
        x=df['month'], y=df['valuation_spread'], mode='lines+markers',
        name='估值价差', line=dict(color='#5c6bc0', width=2),
        marker=dict(size=4, color='#5c6bc0'),
        hovertemplate='%{x|%Y-%m}<br>价差: %{y:.1f}<extra></extra>',
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df['month'], y=df['valuation_spread'].rolling(3).mean(),
        mode='lines', name='3月均线', line=dict(color='rgba(255,255,255,0.35)', dash='dash', width=1),
        hoverinfo='skip',
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df['month'], y=df['within_factor_corr'], mode='lines+markers',
        name='因子内相关', line=dict(color='#ef5350', width=2),
        marker=dict(size=4, color='#ef5350'),
        fill='tozeroy', fillcolor='rgba(239,83,80,0.1)',
        hovertemplate='%{x|%Y-%m}<br>相关性: %{y:.3f}<extra></extra>',
    ), row=2, col=1)

    df_plot = df.dropna(subset=['crowding_score'])
    bar_colors = []
    for v in df_plot['crowding_score']:
        if v > 2: bar_colors.append('#ef5350')
        elif v > 1: bar_colors.append('#ffa726')
        elif v < -1: bar_colors.append('#66bb6a')
        else: bar_colors.append('#ffee58')

    fig.add_trace(go.Bar(
        x=df_plot['month'], y=df_plot['crowding_score'],
        marker_color=bar_colors, name='拥挤度分数',
        hovertemplate='%{x|%Y-%m}<br>拥挤度: %{y:.2f}<extra></extra>',
    ), row=3, col=1)

    for y_val, color, label in [(2, '#ef5350', '危险线'), (1, '#ffa726', '警示线')]:
        fig.add_hline(y=y_val, line_dash="dash", line_color=color,
                      line_width=1, row=3, col=1,
                      annotation_text=label, annotation_font=dict(color=color, size=10))
    fig.add_hline(y=0, line_color='rgba(255,255,255,0.2)', line_width=1, row=3, col=1)

    df_plot2 = df.dropna(subset=['crowding_level'])
    for _, row in df_plot2.iterrows():
        if row['crowding_level'] in ('警示', '危险'):
            fig.add_annotation(
                x=row['month'], y=row['crowding_score'],
                text=row['crowding_level'], showarrow=True, arrowhead=1,
                arrowsize=1, arrowwidth=1, arrowcolor=COLORS.get(row['crowding_level'], '#fff'),
                font=dict(color=COLORS.get(row['crowding_level'], '#fff'), size=10),
                yshift=15, row=3, col=1,
            )

    dark_layout(fig, height=800,
                title='因子拥挤度监控仪表',
                showlegend=False,
                yaxis=dict(title='PB 价差', gridcolor=GRID_COLOR),
                yaxis2=dict(title='平均相关性', gridcolor=GRID_COLOR),
                yaxis3=dict(title='拥挤度 Z-score', gridcolor=GRID_COLOR),
                xaxis3=dict(title='', gridcolor=GRID_COLOR))
    save(fig, '08_因子拥挤度监控')
