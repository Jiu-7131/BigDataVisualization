#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图9: 牛熊周期箱线图"""

import plotly.express as px

from .common import dark_layout, save
from config import COLORS, TEXT_SECOND, GRID_COLOR


def generate(data):
    df_ind = data['ind_m'].copy()
    df_macro = data['macro'].copy()
    df = df_ind.merge(df_macro[['month', 'cycle_phase']], on='month', how='left')
    df = df[df['cycle_phase'].notna()]

    top_inds = df.groupby('industry')['monthly_ret'].std().nlargest(15).index
    df_plot = df[df['industry'].isin(top_inds)]

    fig = px.box(
        df_plot, x='industry', y='monthly_ret', color='cycle_phase',
        color_discrete_map=COLORS,
        labels={'monthly_ret': '月收益率', 'industry': '', 'cycle_phase': '周期阶段'},
        category_orders={'cycle_phase': ['复苏期', '过热期', '滞胀期', '衰退期']},
        notched=False,
    )

    fig.add_hline(y=0, line_dash="dash", line_color='rgba(255,255,255,0.25)', line_width=1)
    fig.update_traces(marker=dict(size=3, opacity=0.6), line=dict(width=1))

    dark_layout(fig, height=620,
                title='牛熊周期下行业收益率分布对比',
                xaxis=dict(title='', tickangle=45, gridcolor=GRID_COLOR,
                          tickfont=dict(size=10)),
                yaxis=dict(title='月收益率', tickformat='.1%', gridcolor=GRID_COLOR),
                boxmode='group',
                legend=dict(font=dict(color=TEXT_SECOND, size=10)))
    save(fig, '09_牛熊周期箱线图')
