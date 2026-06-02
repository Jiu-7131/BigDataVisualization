#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图10: 行业配置桑基图"""

import plotly.graph_objects as go

from .common import dark_layout, save
from config import BG_DARK


def generate(data):
    df = data['sankey'].copy()

    all_nodes = list(set(df['source'].unique()) | set(df['target'].unique()))
    node_map = {n: i for i, n in enumerate(all_nodes)}

    macro_phases = {'复苏期', '过热期', '滞胀期', '衰退期', '过渡期'}

    def get_color(node):
        if node in macro_phases:
            return 'rgba(79,195,247,0.55)'
        elif '价值' in node or '成长' in node or '盘' in node:
            return 'rgba(102,187,106,0.45)'
        else:
            return 'rgba(255,167,38,0.4)'

    fig = go.Figure(data=[go.Sankey(
        arrangement='snap',
        node=dict(
            pad=15, thickness=18,
            line=dict(color='rgba(255,255,255,0.1)', width=0.5),
            label=all_nodes,
            color=[get_color(n) for n in all_nodes],
            hovertemplate='<b>%{label}</b><extra></extra>',
        ),
        link=dict(
            source=[node_map[s] for s in df['source']],
            target=[node_map[t] for t in df['target']],
            value=df['value'] * 100,
            customdata=df['win_rate'],
            color='rgba(120,140,170,0.2)',
            hovertemplate='%{source.label} → %{target.label}<br>强度: %{value:.1f}<br>历史胜率: %{customdata:.1%}<extra></extra>',
        ),
    )])

    dark_layout(fig, height=700,
                title='行业配置决策桑基图 (宏观周期 → 策略风格 → 推荐行业)',
                font=dict(size=11))
    fig.update_layout(paper_bgcolor=BG_DARK, plot_bgcolor=BG_DARK)
    save(fig, '10_行业配置桑基图')
