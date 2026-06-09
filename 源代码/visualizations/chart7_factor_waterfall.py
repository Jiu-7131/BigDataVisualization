#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图7: 因子收益贡献瀑布图 — 行业超额收益分解"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .common import dark_layout, save
from config import BG_DARK, BG_PLOT, TEXT_PRIMARY, TEXT_SECOND, GRID_COLOR, COLORS


def generate(data):
    df_decomp = data['factor_decomp'].copy()
    df_factor = data['factor_ret'].copy()

    quarters = sorted(df_decomp['quarter'].unique())
    latest_q = quarters[-1]
    df_q = df_decomp[df_decomp['quarter'] == latest_q].copy()
    industries = sorted(df_q['industry'].unique())

    # 计算最新季度的因子 IC（因子收益率均值）
    df_factor['q'] = pd.to_datetime(df_factor['month']).dt.to_period('Q').astype(str)
    # 匹配 latest_q 格式 "2025Q4"
    latest_q_str = str(latest_q)
    factor_q = df_factor[df_factor['q'] == latest_q_str]
    if len(factor_q) == 0:
        factor_q = df_factor[df_factor['q'] == df_factor['q'].values[-1]]
    ic_smb = factor_q['SMB'].mean() if len(factor_q) else 0
    ic_hml = factor_q['HML'].mean() if len(factor_q) else 0
    ic_mom = factor_q['MOM'].mean() if len(factor_q) else 0

    # 预建所有行业的瀑布数据
    waterfall_data = {}
    for ind in industries:
        row = df_q[df_q['industry'] == ind].iloc[0]
        measures = ['relative', 'relative', 'relative', 'relative', 'total']
        x_labels = [
            f'SMB (规模)<br><i>IC={ic_smb:.3f}</i>',
            f'HML (价值)<br><i>IC={ic_hml:.3f}</i>',
            f'MOM (动量)<br><i>IC={ic_mom:.3f}</i>',
            'alpha (特质)',
            f'{ind}<br>超额收益',
        ]
        values = [
            row['SMB_contrib'],
            row['HML_contrib'],
            row['MOM_contrib'],
            row['alpha'],
            row['excess_ret'],
        ]
        texts = [f'{v:+.2%}' for v in values]
        waterfall_data[ind] = {
            'measures': measures,
            'x': x_labels,
            'y': values,
            'text': texts,
            'excess_ret': row['excess_ret'],
        }

    # 默认选中行业
    default_ind = industries[0]
    wd = waterfall_data[default_ind]

    fig = go.Figure(go.Waterfall(
        name='因子贡献',
        orientation='v',
        measure=wd['measures'],
        x=wd['x'],
        y=wd['y'],
        text=wd['text'],
        textposition='outside',
        textfont=dict(color=TEXT_PRIMARY, size=11),
        connector=dict(line=dict(color='rgba(255,255,255,0.15)', width=1)),
        increasing=dict(marker=dict(color='#66bb6a', line=dict(color='rgba(255,255,255,0.1)', width=1))),
        decreasing=dict(marker=dict(color='#ef5350', line=dict(color='rgba(255,255,255,0.1)', width=1))),
        totals=dict(marker=dict(color='#5c6bc0', line=dict(color='rgba(255,255,255,0.2)', width=1.5))),
        hovertemplate='<b>%{x}</b><br>贡献: %{y:+.3%}<extra></extra>',
    ))

    # 添加零线
    fig.add_hline(y=0, line_dash='solid', line_color='rgba(255,255,255,0.25)', line_width=1)

    # 添加下拉菜单
    buttons = []
    for ind in industries:
        wd_ind = waterfall_data[ind]
        buttons.append(dict(
            label=ind,
            method='restyle',
            args=[{
                'measure': [wd_ind['measures']],
                'x': [wd_ind['x']],
                'y': [wd_ind['y']],
                'text': [wd_ind['text']],
            }],
        ))

    # 分组按钮（每行6个）
    fig.update_layout(
        updatemenus=[dict(
            type='buttons',
            buttons=buttons,
            direction='left',
            pad=dict(r=8, t=8),
            x=0.5, y=-0.08,
            xanchor='center', yanchor='top',
            bgcolor='rgba(26,35,50,0.9)',
            bordercolor='rgba(255,255,255,0.1)',
            font=dict(color=TEXT_PRIMARY, size=9),
            active=0,
        )],
    )

    dark_layout(fig, height=580,
                title=f'因子收益贡献瀑布图 ({latest_q_str})<br><sup style="font-size:11px;color:{TEXT_SECOND}">超额收益 = 规模 + 价值 + 动量 + 特质收益</sup>')
    fig.update_layout(paper_bgcolor=BG_DARK, plot_bgcolor=BG_PLOT,
                      xaxis=dict(gridcolor=GRID_COLOR),
                      yaxis=dict(title='收益贡献', tickformat='.1%', gridcolor=GRID_COLOR))

    # 底部说明
    fig.add_annotation(
        x=0.5, y=-0.14, xref='paper', yref='paper',
        text=(f'<span style="font-size:10px;color:{TEXT_SECOND}">'
              '绿柱=正向贡献 红柱=负向贡献 蓝柱=超额收益 | IC = 该因子当期多空收益率均值 | 下拉切换行业</span>'),
        showarrow=False,
    )

    save(fig, '07_因子收益分析')
