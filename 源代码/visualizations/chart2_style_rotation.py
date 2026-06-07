#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图2: 市场风格轮动四象限散点图 — 大小盘溢价 × 价值成长溢价 + 逐月动画"""

import numpy as np
import plotly.graph_objects as go

from .common import dark_figure, dark_layout, save
from config import COLORS, TEXT_PRIMARY, TEXT_SECOND, GRID_COLOR, LINE_COLOR, BG_PLOT


def generate(data):
    df = data['style'].copy().sort_values('month').reset_index(drop=True)
    n_total = len(df)

    colors_q = {
        '大盘价值': COLORS['大盘价值'],
        '小盘成长': COLORS['小盘成长'],
        '大盘成长': COLORS['大盘成长'],
        '小盘价值': COLORS['小盘价值'],
        '均衡': TEXT_SECOND,
    }
    month_labels = [d.strftime('%Y-%m') for d in df['month']]

    # 数据范围
    x_max = max(abs(df['size_strength'].max()), abs(df['size_strength'].min()), 0.02)
    y_max = max(abs(df['value_strength'].max()), abs(df['value_strength'].min()), 0.02)
    x_range = [-x_max * 1.28, x_max * 1.28]
    y_range = [-y_max * 1.28, y_max * 1.28]

    fig = dark_figure(height=750)

    # ================================================================
    #  Base traces (full data) — 6 traces
    # ================================================================
    # Trace 1-4: quadrant groups
    for qname in ['大盘价值', '小盘价值', '大盘成长', '小盘成长']:
        group = df[df['style_quadrant'] == qname]
        dates = [d.strftime('%Y-%m') for d in group['month']]
        fig.add_trace(go.Scatter(
            x=group['size_strength'], y=group['value_strength'],
            mode='markers',
            name=qname,
            customdata=dates,
            marker=dict(
                size=np.abs(group['style_drift']) * 250 + 12,
                color=colors_q.get(qname, '#888'),
                opacity=0.8,
                line=dict(width=0.5, color='rgba(255,255,255,0.15)'),
            ),
            hovertemplate='<b>%{customdata}</b><br>大小盘溢价: %{x:.2%}<br>价值成长溢价: %{y:.2%}<extra>%{name}</extra>',
        ))

    # Trace 5: trajectory line
    fig.add_trace(go.Scatter(
        x=df['size_strength'], y=df['value_strength'],
        mode='lines',
        line=dict(color='rgba(255,255,255,0.15)', width=1, dash='dot'),
        showlegend=False, hoverinfo='skip',
    ))

    # Trace 6: current point highlight
    latest = df.iloc[-1]
    fig.add_trace(go.Scatter(
        x=[latest['size_strength']], y=[latest['value_strength']],
        mode='markers',
        marker=dict(size=22, color=colors_q.get(latest['style_quadrant'], '#fff'),
                    line=dict(color='#fff', width=3)),
        name='当前时点',
        customdata=[[latest['month'].strftime('%Y-%m')]],
        hovertemplate='<b>%{customdata[0]}</b><br>大小盘溢价: %{x:.2%}<br>价值成长溢价: %{y:.2%}<extra>当前时点</extra>',
    ))

    # ================================================================
    #  Frames — 逐月显现
    # ================================================================
    frames = []
    for idx in range(n_total):
        sub = df.iloc[:idx + 1]
        fd = []

        # 4 quadrant traces (filtered)
        for qname in ['大盘价值', '小盘价值', '大盘成长', '小盘成长']:
            g = sub[sub['style_quadrant'] == qname]
            fd.append(go.Scatter(
                x=g['size_strength'], y=g['value_strength'],
                mode='markers',
                marker=dict(
                    size=np.abs(g['style_drift']) * 250 + 12,
                    color=colors_q.get(qname, '#888'),
                    opacity=0.8,
                    line=dict(width=0.5, color='rgba(255,255,255,0.15)'),
                ),
                customdata=[d.strftime('%Y-%m') for d in g['month']],
                hovertemplate='<b>%{customdata}</b><br>大小盘溢价: %{x:.2%}<br>价值成长溢价: %{y:.2%}<extra>%{name}</extra>',
            ))

        # trajectory line
        fd.append(go.Scatter(
            x=sub['size_strength'], y=sub['value_strength'],
            mode='lines',
            line=dict(color='rgba(255,255,255,0.15)', width=1, dash='dot'),
            showlegend=False, hoverinfo='skip',
        ))

        # current point
        cur = sub.iloc[-1]
        fd.append(go.Scatter(
            x=[cur['size_strength']], y=[cur['value_strength']],
            mode='markers',
            marker=dict(size=22, color=colors_q.get(cur['style_quadrant'], '#fff'),
                        line=dict(color='#fff', width=3)),
            name='当前时点',
            customdata=[[cur['month'].strftime('%Y-%m')]],
            hovertemplate='<b>%{customdata[0]}</b><br>大小盘溢价: %{x:.2%}<br>价值成长溢价: %{y:.2%}<extra>当前时点</extra>',
        ))

        # drift direction label (trace 8 — text)
        recent_sub = sub.tail(3)
        drift_text = ''
        drift_x, drift_y = cur['size_strength'], cur['value_strength']
        if len(recent_sub) >= 2:
            ddx = recent_sub['size_strength'].iloc[-1] - recent_sub['size_strength'].iloc[0]
            ddy = recent_sub['value_strength'].iloc[-1] - recent_sub['value_strength'].iloc[0]
            if np.sqrt(ddx ** 2 + ddy ** 2) > 0.001:
                parts = []
                if abs(ddx) > 0.005:
                    parts.append('小盘' if ddx > 0 else '大盘')
                if abs(ddy) > 0.005:
                    parts.append('价值' if ddy > 0 else '成长')
                if parts:
                    drift_text = ''.join(parts) + '迁移'

        fd.append(go.Scatter(
            x=[drift_x], y=[drift_y],
            mode='text',
            text=[drift_text],
            textposition='top right',
            textfont=dict(color='#f59e0b', size=13, family='Outfit'),
            showlegend=False, hoverinfo='skip',
        ))

        frames.append(go.Frame(data=fd, name=month_labels[idx]))

    fig.frames = frames

    # ================================================================
    #  Base drift label (trace 7 — text, for initial state)
    # ================================================================
    base_recent = df.tail(3)
    base_drift = ''
    base_x, base_y = latest['size_strength'], latest['value_strength']
    if len(base_recent) >= 2:
        ddx = base_recent['size_strength'].iloc[-1] - base_recent['size_strength'].iloc[0]
        ddy = base_recent['value_strength'].iloc[-1] - base_recent['value_strength'].iloc[0]
        if np.sqrt(ddx ** 2 + ddy ** 2) > 0.001:
            parts = []
            if abs(ddx) > 0.005:
                parts.append('小盘' if ddx > 0 else '大盘')
            if abs(ddy) > 0.005:
                parts.append('价值' if ddy > 0 else '成长')
            if parts:
                base_drift = '→ ' + ''.join(parts) + '迁移'

    fig.add_trace(go.Scatter(
        x=[base_x], y=[base_y],
        mode='text',
        text=[base_drift],
        textposition='top right',
        textfont=dict(color='#f59e0b', size=13, family='Outfit'),
        showlegend=False, hoverinfo='skip',
    ))

    # ================================================================
    #  四象限标注
    # ================================================================
    q_labels = [
        (0.06, 0.06, '大盘价值', COLORS['大盘价值']),
        (-0.06, 0.06, '小盘价值', COLORS['小盘价值']),
        (0.06, -0.06, '大盘成长', COLORS['大盘成长']),
        (-0.06, -0.06, '小盘成长', COLORS['小盘成长']),
    ]
    for x, y, txt, clr in q_labels:
        fig.add_annotation(x=x, y=y, text=txt, showarrow=False,
                           font=dict(color=clr, size=14, family='Outfit'), opacity=0.9)

    # ================================================================
    #  Layout
    # ================================================================
    dark_layout(fig, height=750,
                title='市场风格轮动四象限图',
                xaxis=dict(
                    title=dict(text='大小盘溢价 (小盘 − 大盘)', font=dict(size=13, color=TEXT_SECOND)),
                    tickformat='.0%', range=x_range,
                    zeroline=True, zerolinecolor='rgba(255,255,255,0.2)',
                    gridcolor=GRID_COLOR, tickfont=dict(size=11, color=TEXT_SECOND),
                ),
                yaxis=dict(
                    title=dict(text='价值成长溢价 (价值 − 成长)', font=dict(size=13, color=TEXT_SECOND)),
                    tickformat='.0%', range=y_range,
                    zeroline=True, zerolinecolor='rgba(255,255,255,0.2)',
                    gridcolor=GRID_COLOR, tickfont=dict(size=11, color=TEXT_SECOND),
                ),
                legend=dict(font=dict(color=TEXT_SECOND, size=11), bgcolor='rgba(0,0,0,0)',
                            x=0.98, y=0.98, xanchor='right', yanchor='top'),
    )

    # 底部时间轴
    time_range = f"{df['month'].iloc[0].strftime('%Y-%m')} → {df['month'].iloc[-1].strftime('%Y-%m')}"
    fig.add_annotation(
        x=0.5, y=-0.06,
        text=f'<span style="font-size:11px;color:{TEXT_SECOND}">数据区间: {time_range}  |  共 {n_total} 个月</span>',
        xref='paper', yref='paper', showarrow=False,
    )

    # ================================================================
    #  Slider + Play
    # ================================================================
    fig.update_layout(
        updatemenus=[dict(
            type='buttons', direction='left',
            x=0.5, y=-0.04, xanchor='center', yanchor='top',
            buttons=[
                dict(label='▶ 播放', method='animate',
                     args=[None, {'frame': {'duration': 400, 'redraw': True},
                                  'fromcurrent': True, 'mode': 'immediate',
                                  'transition': {'duration': 150}}]),
                dict(label='⏸ 暂停', method='animate',
                     args=[[None], {'frame': {'duration': 0, 'redraw': False},
                                    'mode': 'immediate', 'transition': {'duration': 0}}]),
            ],
            font=dict(color=TEXT_PRIMARY, size=11),
            bgcolor=BG_PLOT, bordercolor=LINE_COLOR, borderwidth=1,
        )],
        sliders=[dict(
            active=n_total - 1,
            currentvalue={'prefix': '月份: ', 'font': {'color': TEXT_PRIMARY, 'size': 12}},
            pad=dict(t=10),
            steps=[dict(
                label=m, method='animate',
                args=[[m], {'frame': {'duration': 200, 'redraw': True},
                            'mode': 'immediate', 'transition': {'duration': 100}}],
            ) for m in month_labels],
            font=dict(color=TEXT_SECOND, size=10),
            bgcolor=BG_PLOT, bordercolor=LINE_COLOR,
        )],
    )

    save(fig, '02_风格轮动热力三角图')
