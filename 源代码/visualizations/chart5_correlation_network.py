#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图5: 行业相关性网络图"""

import numpy as np
import plotly.graph_objects as go

from .common import dark_layout, save
from config import TEXT_PRIMARY


def generate(data):
    df = data['ind_corr'].copy()
    latest_date = df['window_end_date'].max()
    latest = df[df['window_end_date'] == latest_date].copy()

    edges = latest[latest['correlation'] > 0.45].copy()
    if len(edges) < 20:
        edges = latest.nlargest(150, 'correlation')

    import networkx as nx
    G = nx.Graph()
    for _, row in edges.iterrows():
        G.add_edge(row['industry_a'], row['industry_b'], weight=row['correlation'])

    if len(G.nodes()) == 0:
        print("    (网络图为空，跳过)")
        return

    pos = nx.spring_layout(G, k=1.8, seed=42, iterations=150)

    edge_x, edge_y = [], []
    for u, v, d in G.edges(data=True):
        x0, y0 = pos[u]; x1, y1 = pos[v]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y, mode='lines',
        line=dict(width=0.6, color='rgba(120,140,170,0.35)'),
        hoverinfo='none',
    )

    node_x, node_y, node_text, node_degree = [], [], [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x); node_y.append(y)
        node_text.append(node)
        node_degree.append(G.degree(node))

    deg_arr = np.array(node_degree)
    deg_norm = (deg_arr - deg_arr.min()) / (deg_arr.max() - deg_arr.min() + 0.01)

    node_colors = [
        f'rgba({int(100 + 155 * d)},{int(60 + 100 * (1 - d))},{int(80 + 100 * (1 - d))},0.9)'
        for d in deg_norm
    ]

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode='markers+text',
        text=node_text, textposition='top center',
        textfont=dict(size=10, color=TEXT_PRIMARY),
        marker=dict(
            size=deg_arr * 3 + 12, color=node_colors,
            line=dict(width=0.5, color='rgba(255,255,255,0.15)'),
        ),
        hovertemplate='<b>%{text}</b><br>连接度: %{marker.size:.0f}<extra></extra>',
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    dark_layout(fig, height=800,
                title=f'行业相关性网络图 (窗口: {latest_date.strftime("%Y-%m-%d")})',
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    fig.update_layout(showlegend=False)
    save(fig, '05_行业相关性网络图')
