#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图6: 平行坐标图 — 行业多因子暴露"""

import plotly.graph_objects as go

from .common import dark_layout, save
from config import BG_DARK, BG_PLOT, TEXT_PRIMARY, TEXT_SECOND, INDUSTRY_COLORS


def generate(data):
    df = data['ind_q'].copy()
    latest_q = df['quarter'].max()
    df_q = df[df['quarter'] == latest_q].dropna(subset=['cum_ret_z', 'ann_vol_z', 'med_pe_z'])

    if len(df_q) == 0:
        print("    (平行坐标数据为空，跳过)")
        return

    factor_cols = ['cum_ret_z', 'mom_1q_z', 'mom_4q_z', 'ann_vol_z',
                   'med_pe_z', 'med_pb_z', 'total_mv_z', 'avg_turnover_z']
    factor_labels = ['收益率', '动量 1Q', '动量 4Q', '波动率', 'PE 估值', 'PB 估值', '总市值', '换手率']

    fig = go.Figure(data=go.Parcoords(
        line=dict(color=df_q['cum_ret_z'], colorscale='RdBu_r',
                   showscale=True,
                   colorbar=dict(title='收益率 Z', title_font=dict(color=TEXT_SECOND),
                                 tickfont=dict(color=TEXT_SECOND), thickness=12, outlinewidth=0)),
        dimensions=[
            dict(range=[df_q[c].min(), df_q[c].max()],
                 label=lab, values=df_q[c].values)
            for c, lab in zip(factor_cols, factor_labels)
        ],
        labelside='bottom', labelfont=dict(color=TEXT_PRIMARY, size=11),
    ))

    dark_layout(fig, height=620,
                title=f'行业多因子暴露平行坐标图 ({str(latest_q)[:7]})')
    fig.update_layout(paper_bgcolor=BG_DARK, plot_bgcolor=BG_PLOT)
    save(fig, '06_平行坐标图')
