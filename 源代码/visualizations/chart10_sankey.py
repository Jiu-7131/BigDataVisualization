#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图10: 行业配置桑基图 — 周期高亮 + 胜率标注 + 阶段切换"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .common import dark_layout, save
from config import BG_DARK, TEXT_SECOND, COLORS


# 周期色
PHASE_COLORS = {
    '复苏期': '#4fc3f7', '过热期': '#ef5350',
    '滞胀期': '#ffb74d', '衰退期': '#5c6bc0', '过渡期': '#546e7a',
}


def generate(data):
    df = data['sankey'].copy()
    df_macro = data['macro'].copy()

    # 当前周期
    current_phase = '过渡期'
    if len(df_macro) > 0:
        latest_macro = df_macro.iloc[-1]
        current_phase = latest_macro.get('cycle_phase', '过渡期')

    macro_phases = {'复苏期', '过热期', '滞胀期', '衰退期', '过渡期'}
    all_nodes = sorted(set(df['source'].unique()) | set(df['target'].unique()),
                       key=lambda n: (0 if n in macro_phases else 1 if n in
                                      {'小盘成长', '小盘价值', '大盘成长', '大盘价值',
                                       '周期股', '逆周期', '政策受益', '质量优先',
                                       '均衡配置', '灵活配置'} else 2, n))
    node_map = {n: i for i, n in enumerate(all_nodes)}

    # ---- 计算每节点胜率 ----
    node_win = {}
    for _, r in df.iterrows():
        s, t = r['source'], r['target']
        wr = r['win_rate']
        node_win[s] = max(node_win.get(s, 0), wr)
        node_win[t] = max(node_win.get(t, 0), wr)

    # 节点标签（附胜率）
    node_labels = []
    for n in all_nodes:
        wr = node_win.get(n, 0)
        if n in macro_phases:
            node_labels.append(f'{n}')
        elif wr > 0:
            node_labels.append(f'{n} ({wr:.0%})')
        else:
            node_labels.append(n)

    # ---- 当前阶段高亮配色 ----
    def compute_link_colors(highlight_phase):
        colors = []
        for _, r in df.iterrows():
            if r['source'] == highlight_phase:
                c = PHASE_COLORS.get(highlight_phase, '#4fc3f7')
                colors.append(f'rgba{tuple(int(c.lstrip("#")[j:j+2],16) for j in (0,2,4)) + (0.55,)}')
            else:
                colors.append('rgba(120,140,170,0.08)')
        return colors

    def compute_node_colors(highlight_phase):
        colors = []
        for n in all_nodes:
            if n == highlight_phase:
                c = PHASE_COLORS.get(n, '#4fc3f7')
                colors.append(f'rgba{tuple(int(c.lstrip("#")[j:j+2],16) for j in (0,2,4)) + (0.7,)}')
            elif n in macro_phases:
                colors.append('rgba(120,140,170,0.15)')
            elif any(kw in n for kw in ('成长', '价值', '盘', '周期',
                                                '逆周期', '政策', '质量', '均衡', '灵活')):
                colors.append('rgba(120,160,200,0.2)')
            else:
                colors.append('rgba(255,167,38,0.18)')
        return colors

    link_colors_current = compute_link_colors(current_phase)
    node_colors_current = compute_node_colors(current_phase)

    fig = go.Figure(data=[go.Sankey(
        arrangement='snap',
        node=dict(
            pad=15, thickness=18,
            line=dict(color='rgba(255,255,255,0.08)', width=0.5),
            label=node_labels,
            color=node_colors_current,
            hovertemplate='<b>%{label}</b><extra></extra>',
        ),
        link=dict(
            source=[node_map[s] for s in df['source']],
            target=[node_map[t] for t in df['target']],
            value=df['value'] * 100,
            customdata=df['win_rate'],
            color=link_colors_current,
            hovertemplate='%{source.label} → %{target.label}<br>强度: %{value:.1f}<br>胜率: %{customdata:.1%}<extra></extra>',
        ),
    )])

    # ---- 下拉切换阶段 ----
    all_phase_names = [p for p in ['复苏期', '过热期', '滞胀期', '衰退期']
                       if p in [s for s in df['source'].unique()]]

    if len(all_phase_names) > 1:
        buttons = []
        for phase in all_phase_names:
            lc = compute_link_colors(phase)
            nc = compute_node_colors(phase)
            buttons.append(dict(
                label=phase,
                method='restyle',
                args=[{'link.color': [lc], 'node.color': [nc]}],
            ))

        fig.update_layout(
            updatemenus=[dict(
                type='buttons',
                buttons=buttons,
                direction='left',
                pad=dict(r=8, t=8),
                x=0.5, y=-0.04,
                xanchor='center', yanchor='top',
                bgcolor='rgba(26,35,50,0.9)',
                bordercolor='rgba(255,255,255,0.1)',
                font=dict(color='#d1d4dc', size=10),
                active=all_phase_names.index(current_phase)
                if current_phase in all_phase_names else 0,
            )],
        )

    dark_layout(fig, height=700,
                title=f'行业配置决策桑基图 — 当前周期: {current_phase}'
                      f'<br><sup style="font-size:11px;color:{TEXT_SECOND}">宏观周期 → 策略风格 → 推荐行业 | 流量宽度=推荐权重</sup>')
    fig.update_layout(
        paper_bgcolor=BG_DARK, plot_bgcolor=BG_DARK,
        margin=dict(l=20, r=20, t=80, b=60),
    )

    # 底部说明
    fig.add_annotation(
        x=0.5, y=-0.08, xref='paper', yref='paper',
        text=(f'<span style="font-size:10px;color:{TEXT_SECOND}">'
              '当前周期路径高亮 | 节点标签()内为历史胜率 | 下拉按钮切换周期 | '
              f'跨图跳转: URL 参数传参</span>'),
        showarrow=False,
    )

    save(fig, '10_行业配置桑基图')
