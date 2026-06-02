#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图2: 市场风格轮动热力三角图"""

import numpy as np
import plotly.graph_objects as go

from .common import dark_figure, dark_layout, save
from config import COLORS, TEXT_SECOND, GRID_COLOR, LINE_COLOR


def generate(data):
    df = data['style'].copy()
    fig = dark_figure(height=680)

    colors_q = {
        '大盘价值': COLORS['大盘价值'], '小盘成长': COLORS['小盘成长'],
        '大盘成长': COLORS['大盘成长'], '小盘价值': COLORS['小盘价值'],
        '均衡': TEXT_SECOND,
    }

    for qname, group in df.groupby('style_quadrant'):
        dates = [d.strftime('%Y-%m') for d in group['month']]
        fig.add_trace(go.Scatter(
            x=group['size_strength'], y=group['value_strength'],
            mode='markers',
            name=qname,
            customdata=dates,
            marker=dict(
                size=np.abs(group['style_drift']) * 250 + 10,
                color=colors_q.get(qname, '#888'),
                opacity=0.85,
                line=dict(width=0.5, color='rgba(255,255,255,0.2)'),
            ),
            hovertemplate='<b>%{customdata}</b><br>大小盘溢价: %{x:.2%}<br>价值成长溢价: %{y:.2%}<extra>%{name}</extra>',
        ))

    fig.add_hline(y=0, line_dash="dash", line_color='rgba(255,255,255,0.2)', line_width=1)
    fig.add_vline(x=0, line_dash="dash", line_color='rgba(255,255,255,0.2)', line_width=1)

    annotations = [
        (0.04, 0.04, '大盘价值', COLORS['大盘价值']),
        (-0.04, 0.04, '小盘价值', COLORS['小盘价值']),
        (0.04, -0.04, '大盘成长', COLORS['大盘成长']),
        (-0.04, -0.04, '小盘成长', COLORS['小盘成长']),
    ]
    for x, y, txt, clr in annotations:
        fig.add_annotation(x=x, y=y, text=txt, showarrow=False,
                           font=dict(color=clr, size=11), opacity=0.85)

    dark_layout(fig, height=680,
                title='市场风格轮动热力三角图',
                xaxis=dict(title='大小盘溢价 (小盘 − 大盘)', tickformat='.1%', zeroline=True,
                           zerolinecolor=LINE_COLOR, gridcolor=GRID_COLOR),
                yaxis=dict(title='价值成长溢价 (价值 − 成长)', tickformat='.1%', zeroline=True,
                           zerolinecolor=LINE_COLOR, gridcolor=GRID_COLOR),
                legend=dict(font=dict(color=TEXT_SECOND, size=11)))
    save(fig, '02_风格轮动热力三角图')
