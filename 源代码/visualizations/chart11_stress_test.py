#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图11: 策略压力测试热图"""

import numpy as np
import plotly.graph_objects as go

from .common import dark_layout, save
from config import TEXT_PRIMARY, TEXT_SECOND, GRID_COLOR


def generate(data):
    df = data['stress'].copy()
    pivot = df.pivot_table(values='cum_return', index='industry', columns='scenario', aggfunc='mean')

    stress_colorscale = [
        [0.0, '#26a69a'],
        [0.35, '#4db6ac'],
        [0.48, '#1a2332'],
        [0.52, '#1a2332'],
        [0.65, '#ef9a9a'],
        [1.0, '#ef5350'],
    ]

    text_matrix = [[f'{v:.1%}' if not np.isnan(v) else '' for v in row] for row in pivot.values]

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
        colorscale=stress_colorscale, zmid=0,
        text=text_matrix, texttemplate='%{text}',
        textfont=dict(size=9, color=TEXT_PRIMARY),
        hovertemplate='<b>%{y}</b> | %{x}<br>区间收益: %{z:.2%}<extra></extra>',
        colorbar=dict(
            title='累计收益', title_font=dict(color=TEXT_SECOND),
            tickfont=dict(color=TEXT_SECOND), tickformat='.1%',
            thickness=12, outlinewidth=0,
        ),
    ))

    dark_layout(fig, height=720,
                title='策略压力测试热图 — 极端事件下各行业收益表现',
                xaxis=dict(title='', tickfont=dict(size=10), gridcolor=GRID_COLOR),
                yaxis=dict(title='', tickfont=dict(size=10)))
    fig.update_layout(width=1000)
    save(fig, '11_压力测试热图')
