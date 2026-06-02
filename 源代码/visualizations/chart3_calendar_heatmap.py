#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图3: 日历热力图 — 行业月度收益率"""

import numpy as np
import plotly.graph_objects as go

from .common import dark_layout, save
from config import TEXT_PRIMARY, TEXT_SECOND


def generate(data):
    df = data['ind_m'].copy()
    industries = sorted(df['industry'].unique())
    months = sorted(df['month'].unique())
    month_labels = [m.strftime('%Y-%m') for m in months]

    z_data, text_data = [], []
    for ind in industries:
        row_vals, row_text = [], []
        for m in months:
            sub = df[(df['industry'] == ind) & (df['month'] == m)]['monthly_ret']
            v = sub.iloc[0] if len(sub) > 0 else np.nan
            row_vals.append(v)
            row_text.append(f'{v:.1%}' if not np.isnan(v) else '')
        z_data.append(row_vals)
        text_data.append(row_text)

    custom_colorscale = [
        [0.0, '#26a69a'],
        [0.35, '#4db6ac'],
        [0.48, '#1a2332'],
        [0.52, '#1a2332'],
        [0.65, '#ef9a9a'],
        [1.0, '#ef5350'],
    ]

    fig = go.Figure(data=go.Heatmap(
        z=z_data, x=month_labels, y=industries,
        colorscale=custom_colorscale, zmid=0,
        text=text_data, texttemplate='%{text}', textfont={"size": 7, "color": TEXT_PRIMARY},
        hovertemplate='<b>%{y}</b> | %{x}<br>月收益: %{z:.2%}<extra></extra>',
        colorbar=dict(
            title='月收益率', title_font=dict(color=TEXT_SECOND),
            tickfont=dict(color=TEXT_SECOND), thickness=12,
            outlinewidth=0,
        ),
        xgap=1, ygap=1,
    ))

    dark_layout(fig, height=900, title='行业月度收益率日历热力图',
                xaxis=dict(title='', tickangle=45, tickfont=dict(size=9, color=TEXT_SECOND)),
                yaxis=dict(title='', tickfont=dict(size=10)))
    fig.update_layout(width=1400)
    save(fig, '03_日历热力图')
