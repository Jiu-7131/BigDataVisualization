#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图9: 牛熊周期箱线图 — 小提琴 + 箱线 + 不对称标注 + 牛熊/周期切换"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .common import dark_layout, save
from config import COLORS, TEXT_PRIMARY, TEXT_SECOND, GRID_COLOR


def _classify_bull_bear(market_ret, threshold=0.20):
    """简单牛熊分类：累计收益超阈值"""
    cum = (1 + market_ret).cumprod()
    peak = cum.cummax()
    trough = cum.cummin()
    drawdown = cum / peak - 1
    rally = cum / trough - 1

    result = pd.Series('震荡', index=market_ret.index)
    result[rally > threshold] = '上涨'
    result[drawdown < -threshold] = '下跌'
    return result


def generate(data):
    df_ind = data['ind_m'].copy()
    df_ind['month'] = pd.to_datetime(df_ind['month'])
    df_macro = data['macro'].copy()
    df_macro['month'] = pd.to_datetime(df_macro['month'])

    df = df_ind.merge(df_macro[['month', 'cycle_phase']], on='month', how='left')
    df = df[df['cycle_phase'].notna()].copy()
    if len(df) == 0:
        print('    (箱线图数据为空，跳过)')
        return

    # 计算市场平均收益作为牛熊分类依据
    market_monthly = df.groupby('month')['monthly_ret'].mean()
    df['market_regime'] = df['month'].map(
        _classify_bull_bear(market_monthly))

    # 周期色彩
    phase_order = ['复苏期', '过热期', '滞胀期', '衰退期']
    phase_colors = {
        '复苏期': COLORS['复苏期'],
        '过热期': COLORS['过热期'],
        '滞胀期': COLORS['滞胀期'],
        '衰退期': COLORS['衰退期'],
    }
    regime_colors = {'上涨': '#ef5350', '震荡': '#ffb74d', '下跌': '#66bb6a'}

    industries = sorted(df['industry'].unique())

    # ======== 构建双模式 Figure ========
    fig = go.Figure()

    # ---- 默认模式：周期阶段分组 ----
    phases_present = [p for p in phase_order if p in df['cycle_phase'].values]
    for phase in phases_present:
        df_p = df[df['cycle_phase'] == phase]
        if len(df_p) < 3:
            continue

        # 按行业聚合
        rets_by_ind = []
        inds_ordered = []
        for ind in industries:
            vals = df_p[df_p['industry'] == ind]['monthly_ret'].dropna()
            if len(vals) >= 3:
                rets_by_ind.append(vals.values)
                inds_ordered.append(ind)

        if not rets_by_ind:
            continue

        color = phase_colors.get(phase, '#888')

        # violin
        fig.add_trace(go.Violin(
            y=np.concatenate(rets_by_ind),
            x=np.concatenate([[ind] * len(r) for ind, r in zip(inds_ordered, rets_by_ind)]),
            name=phase,
            legendgroup=phase,
            scalegroup=phase,
            side='positive' if phases_present.index(phase) % 2 == 0 else 'negative',
            line=dict(color=color, width=0.8),
            fillcolor=f'rgba{tuple(int(color.lstrip("#")[j:j+2],16) for j in (0,2,4)) + (0.18,)}',
            points=False,
            bandwidth=0.03,
            spanmode='soft',
            hoverinfo='skip',
            visible=True,
        ))

    # ---- 箱线图（周期模式） ----
    box_traces_start = len(fig.data)
    for phase in phases_present:
        df_p = df[df['cycle_phase'] == phase]
        rets_by_ind = []
        inds_ordered = []
        stats_by_ind = []
        for ind in industries:
            vals = df_p[df_p['industry'] == ind]['monthly_ret'].dropna()
            if len(vals) >= 3:
                rets_by_ind.append(vals.values)
                inds_ordered.append(ind)
                # 计算指标
                pos_ret = vals[vals > 0]
                stats_by_ind.append({
                    'win_rate': len(pos_ret) / len(vals),
                    'mean_ret': vals.mean(),
                    'median_ret': np.median(vals),
                })

        if not rets_by_ind:
            continue

        color = phase_colors.get(phase, '#888')

        fig.add_trace(go.Box(
            y=np.concatenate(rets_by_ind),
            x=np.concatenate([[ind] * len(r) for ind, r in zip(inds_ordered, rets_by_ind)]),
            name=f'{phase} (箱线)',
            legendgroup=phase,
            marker=dict(color=color, size=3, opacity=0.7),
            line=dict(color=color, width=1.2),
            fillcolor='rgba(0,0,0,0)',
            boxpoints='outliers',
            jitter=0.3,
            hoverinfo='y+name',
            visible=True,
        ))

    # ---- 牛熊模式 traces（初始隐藏） ----
    regime_order = ['上涨', '震荡', '下跌']
    regimes_present = [r for r in regime_order if r in df['market_regime'].values]

    for regime in regimes_present:
        df_r = df[df['market_regime'] == regime]
        rets_by_ind = []
        inds_ordered = []
        for ind in industries:
            vals = df_r[df_r['industry'] == ind]['monthly_ret'].dropna()
            if len(vals) >= 3:
                rets_by_ind.append(vals.values)
                inds_ordered.append(ind)

        if not rets_by_ind:
            continue

        color = regime_colors.get(regime, '#888')
        fig.add_trace(go.Violin(
            y=np.concatenate(rets_by_ind),
            x=np.concatenate([[ind] * len(r) for ind, r in zip(inds_ordered, rets_by_ind)]),
            name=f'{regime} (小提琴)',
            legendgroup=f'regime_{regime}',
            scalegroup=f'regime_{regime}',
            side='positive',
            line=dict(color=color, width=0.8),
            fillcolor=f'rgba{tuple(int(color.lstrip("#")[j:j+2],16) for j in (0,2,4)) + (0.18,)}',
            points=False,
            bandwidth=0.03,
            spanmode='soft',
            hoverinfo='skip',
            visible=False,
        ))

        fig.add_trace(go.Box(
            y=np.concatenate(rets_by_ind),
            x=np.concatenate([[ind] * len(r) for ind, r in zip(inds_ordered, rets_by_ind)]),
            name=f'{regime} (箱线)',
            legendgroup=f'regime_{regime}',
            marker=dict(color=color, size=3, opacity=0.7),
            line=dict(color=color, width=1.2),
            fillcolor='rgba(0,0,0,0)',
            boxpoints='outliers',
            jitter=0.3,
            hoverinfo='y+name',
            visible=False,
        ))

    # ---- 标注：计算不对称比和胜率 ----
    # 计算各行业在牛/熊市的表现差异
    bull_mask = df['market_regime'] == '上涨'
    bear_mask = df['market_regime'] == '下跌'
    annotation_text_parts = []
    for ind in industries[:8]:  # 前8个行业展示
        bull_vals = df[(df['industry'] == ind) & bull_mask]['monthly_ret']
        bear_vals = df[(df['industry'] == ind) & bear_mask]['monthly_ret']
        if len(bull_vals) >= 2 and len(bear_vals) >= 2:
            asym = bull_vals.mean() - bear_vals.mean()
            annotation_text_parts.append(
                f'{ind}: 牛熊差 {asym:+.1%}  |  复苏胜率 '
                f'{len(df[(df["industry"]==ind)&(df["cycle_phase"]=="复苏期")&(df["monthly_ret"]>0)])/max(1,len(df[(df["industry"]==ind)&(df["cycle_phase"]=="复苏期")])):.0%}'
            )

    # ---- 切换按钮 ----
    n_phase_traces = len(phases_present) * 2  # violin + box
    n_regime_traces = len(regimes_present) * 2

    fig.update_layout(
        updatemenus=[dict(
            type='buttons',
            direction='left',
            x=0.5, y=-0.06,
            xanchor='center', yanchor='top',
            bgcolor='rgba(26,35,50,0.9)',
            bordercolor='rgba(255,255,255,0.1)',
            font=dict(color=TEXT_PRIMARY, size=10),
            buttons=[
                dict(label='按周期阶段分组',
                     method='update',
                     args=[{'visible': [True] * n_phase_traces + [False] * n_regime_traces},
                           {'title': '不同经济周期阶段下行业收益率分布'}]),
                dict(label='按牛/熊/震荡分组',
                     method='update',
                     args=[{'visible': [False] * n_phase_traces + [True] * n_regime_traces},
                           {'title': '牛熊市下行业收益率分布对比'}]),
            ],
        )],
    )

    # ---- 零线 ----
    fig.add_hline(y=0, line_dash='dash', line_color='rgba(255,255,255,0.25)', line_width=1)

    dark_layout(fig, height=650,
                title='不同经济周期阶段下行业收益率分布')
    fig.update_layout(
        paper_bgcolor='#0f1923', plot_bgcolor='#1a2332',
        xaxis=dict(title='', tickangle=45, gridcolor=GRID_COLOR,
                   tickfont=dict(size=9, color=TEXT_PRIMARY)),
        yaxis=dict(title='月收益率', tickformat='.1%', gridcolor=GRID_COLOR),
        boxmode='group', violinmode='group',
        legend=dict(font=dict(color=TEXT_SECOND, size=9),
                    orientation='h', y=1.02, x=0.5, xanchor='center'),
        hovermode='closest',
        margin=dict(l=40, r=20, t=80, b=80),
    )

    # ---- 底部标注 ----
    if annotation_text_parts:
        fig.add_annotation(
            x=0.5, y=-0.12, xref='paper', yref='paper',
            text='<br>'.join(annotation_text_parts[:4]),
            showarrow=False,
            font=dict(size=9, color=TEXT_SECOND),
            align='left',
        )

    save(fig, '09_牛熊周期箱线图')
