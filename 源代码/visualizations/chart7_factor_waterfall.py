#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图7: 因子收益分析 (柱状图 + 累计收益)"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .common import dark_layout, save
from config import TEXT_SECOND, GRID_COLOR


def generate(data):
    df = data['factor_ret'].copy()
    factor_labels = ['市场 Rm', '规模 SMB', '价值 HML', '动量 MOM']
    factor_keys = ['Rm', 'SMB', 'HML', 'MOM']
    cum_keys = ['Rm_cum', 'SMB_cum', 'HML_cum', 'MOM_cum']
    colors_f = ['#5c6bc0', '#ef5350', '#66bb6a', '#ffa726']

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('因子月度收益率', '因子累计收益率'),
        column_widths=[0.45, 0.55],
        horizontal_spacing=0.08,
    )

    for i, (key, label) in enumerate(zip(factor_keys, factor_labels)):
        fig.add_trace(go.Bar(
            x=df['month'], y=df[key], name=label,
            marker_color=colors_f[i], opacity=0.85,
            hovertemplate='<b>%{x|%Y-%m}</b><br>' + label + ': %{y:.2%}<extra></extra>',
        ), row=1, col=1)

    for i, (ckey, label) in enumerate(zip(cum_keys, factor_labels)):
        fig.add_trace(go.Scatter(
            x=df['month'], y=df[ckey], mode='lines',
            name=label, line=dict(color=colors_f[i], width=2.5),
            hovertemplate='<b>%{x|%Y-%m}</b><br>' + label + ' 累计: %{y:.2f}<extra></extra>',
        ), row=1, col=2)

    fig.add_hline(y=0, line_dash="solid", line_color='rgba(255,255,255,0.2)',
                  line_width=1, row=1, col=1)
    fig.add_hline(y=1, line_dash="dash", line_color='rgba(255,255,255,0.15)',
                  line_width=1, row=1, col=2)

    dark_layout(fig, height=520,
                title='因子收益分析',
                barmode='group',
                xaxis=dict(title='', gridcolor=GRID_COLOR),
                xaxis2=dict(title='', gridcolor=GRID_COLOR),
                yaxis=dict(title='月收益率', tickformat='.1%', gridcolor=GRID_COLOR),
                yaxis2=dict(title='累计收益 (基准=1)', tickformat='.1f', gridcolor=GRID_COLOR),
                legend=dict(font=dict(color=TEXT_SECOND, size=11), orientation='h', y=1.05))
    save(fig, '07_因子收益分析')
