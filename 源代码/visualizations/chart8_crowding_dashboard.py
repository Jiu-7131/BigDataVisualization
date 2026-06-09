#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图8: 因子拥挤度监控仪表 — 2×2 速度表 + 历史趋势"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from .common import dark_layout, save
from config import BG_DARK, BG_PLOT, TEXT_PRIMARY, TEXT_SECOND, GRID_COLOR, COLORS


# 4 个拥挤度指标定义
GAUGE_DEFS = [
    {
        'key': 'valuation_spread_z', 'label': '估值拥挤度',
        'subtitle': 'PB 价差 Z-score',
        'color': '#5c6bc0',
    },
    {
        'key': 'turnover_hhi_z', 'label': '交易拥挤度',
        'subtitle': '换手率 HHI Z-score',
        'color': '#ef5350',
    },
    {
        'key': 'within_factor_corr_z', 'label': '因子相关性',
        'subtitle': '因子内平均相关 Z',
        'color': '#ffa726',
    },
    {
        'key': 'crowding_score', 'label': '综合拥挤度',
        'subtitle': '多指标合成 Z-score',
        'color': '#66bb6a',
    },
]


def _gauge_steps(max_val=3.0):
    """绿-黄-红三区阈值"""
    return [
        {'range': [0, 1], 'color': 'rgba(102,187,106,0.35)'},
        {'range': [1, 2], 'color': 'rgba(255,167,38,0.35)'},
        {'range': [2, max_val], 'color': 'rgba(239,83,80,0.35)'},
    ]


def generate(data):
    df = data['factor_crowd'].copy()
    df['month'] = pd.to_datetime(df['month'])

    if len(df) == 0:
        print('    (拥挤度数据为空，跳过)')
        return

    latest = df.iloc[-1]
    max_val = 3.0  # z-score 显示范围

    # ---- 构建 Figure ----
    fig = go.Figure()

    # 4 个仪表盘（手动 domain 定位）
    positions = [
        {'x': [0.02, 0.48], 'y': [0.50, 0.96]},   # 左上
        {'x': [0.52, 0.98], 'y': [0.50, 0.96]},   # 右上
        {'x': [0.02, 0.48], 'y': [0.04, 0.50]},   # 左下
        {'x': [0.52, 0.98], 'y': [0.04, 0.50]},   # 右下
    ]

    for i, gdef in enumerate(GAUGE_DEFS):
        pos = positions[i]
        key = gdef['key']
        val = latest.get(key, np.nan)
        if pd.isna(val):
            val_display = None
            gauge_val = 0
            title_text = f'<b>{gdef["label"]}</b><br><span style="font-size:10px;color:#787b86">数据不足</span>'
        else:
            gauge_val = min(abs(val), max_val) * (1 if val >= 0 else -1)
            val_display = val
            title_text = f'<b>{gdef["label"]}</b><br><span style="font-size:10px;color:#787b86">{gdef["subtitle"]}</span>'

        fig.add_trace(go.Indicator(
            mode='gauge+number',
            value=gauge_val if val_display is not None else 0,
            number=dict(
                font=dict(color='#e0e4eb', size=28, family='Outfit'),
                suffix=' σ',
                valueformat='.2f',
            ),
            domain=pos,
            title=dict(
                text=title_text,
                font=dict(color=TEXT_PRIMARY, size=12),
            ),
            gauge=dict(
                shape='angular',
                axis=dict(
                    range=[-max_val, max_val],
                    tickformat='.1f',
                    tickfont=dict(color=TEXT_SECOND, size=9),
                    tickcolor='rgba(255,255,255,0.15)',
                ),
                bar=dict(
                    color=gdef['color'],
                    thickness=0.18,
                ),
                bgcolor='rgba(255,255,255,0.03)',
                borderwidth=0,
                steps=[
                    {'range': [-max_val, -2], 'color': 'rgba(239,83,80,0.35)'},
                    {'range': [-2, -1], 'color': 'rgba(255,167,38,0.35)'},
                    {'range': [-1, 0], 'color': 'rgba(102,187,106,0.3)'},
                    {'range': [0, 1], 'color': 'rgba(102,187,106,0.3)'},
                    {'range': [1, 2], 'color': 'rgba(255,167,38,0.35)'},
                    {'range': [2, max_val], 'color': 'rgba(239,83,80,0.35)'},
                ],
                threshold=dict(
                    line=dict(color='rgba(255,255,255,0.4)', width=1.5),
                    thickness=0.85,
                    value=gauge_val if val_display is not None else 0,
                ),
            ),
        ))

    # ---- 底部历史趋势图 ----
    # 添加第二个 yaxis（使用独立的轴系统在底部区域）
    # 由于 indicator traces 使用 domain，需要手动添加 scatter
    df_valid = df.dropna(subset=['crowding_score'])

    fig.add_trace(go.Scatter(
        x=df_valid['month'], y=df_valid['crowding_score'],
        mode='lines+markers',
        name='综合拥挤度',
        line=dict(color='#66bb6a', width=2),
        marker=dict(size=4, color='#66bb6a'),
        hovertemplate='%{x|%Y-%m}<br>拥挤度: %{y:.2f}<extra></extra>',
        xaxis='x2', yaxis='y2',
    ))

    # 添加警戒线
    for y_val, color, label in [(1, '#ffa726', '警示线'), (2, '#ef5350', '危险线')]:
        fig.add_shape(type='line', x0=0, x1=1, y0=y_val, y1=y_val,
                      xref='x2 domain', yref='y2',
                      line=dict(dash='dash', color=color, width=1))
        fig.add_annotation(x=1, y=y_val, xref='x2 domain', yref='y2',
                          text=label, showarrow=False,
                          font=dict(color=color, size=9),
                          xanchor='right')

    fig.add_shape(type='line', x0=0, x1=1, y0=0, y1=0,
                  xref='x2 domain', yref='y2',
                  line=dict(color='rgba(255,255,255,0.15)', width=1))

    # 标注红色区域的历史事件
    danger_mask = df_valid['crowding_level'] == '危险'
    if danger_mask.any():
        danger_dates = df_valid[danger_mask]
        for _, dr in danger_dates.iterrows():
            fig.add_annotation(
                x=dr['month'], y=dr['crowding_score'],
                text='⚠', showarrow=True, arrowhead=1,
                arrowsize=1, arrowwidth=1,
                arrowcolor='#ef5350',
                font=dict(color='#ef5350', size=14),
                yshift=12,
                xref='x2', yref='y2',
            )

    # 配置双轴
    fig.update_layout(
        xaxis2=dict(
            domain=[0.04, 0.96],
            anchor='y2',
            title='',
            gridcolor=GRID_COLOR,
            showgrid=True,
        ),
        yaxis2=dict(
            domain=[0.0, 0.40],
            anchor='x2',
            title=dict(text='拥挤度 Z-score', font=dict(color=TEXT_SECOND, size=10)),
            gridcolor=GRID_COLOR,
            zerolinecolor='rgba(255,255,255,0.2)',
        ),
    )

    # ---- 当前状态标签 ----
    level = latest.get('crowding_level', '未知')
    level_color = COLORS.get(level, '#888')
    level_score = latest.get('crowding_score', 0)

    fig.add_annotation(
        x=0.5, y=0.445, xref='paper', yref='paper',
        text=(f'<span style="font-size:13px;color:{TEXT_SECOND}">当前状态：</span>'
              f'<span style="font-size:16px;color:{level_color};font-weight:600;">{level}</span>'
              f'<span style="font-size:12px;color:{TEXT_SECOND}">　|　综合分：{level_score:+.2f}σ</span>'),
        showarrow=False,
    )

    dark_layout(fig, height=850,
                title=f'因子拥挤度监控仪表 ({str(latest["month"])[:7]})')
    fig.update_layout(
        paper_bgcolor=BG_DARK, plot_bgcolor=BG_PLOT,
        margin=dict(l=20, r=20, t=60, b=30),
    )

    # ---- 红色闪烁 JS ----
    flash_js = ""
    if level == '危险':
        flash_js = """
        <script>
        (function() {
            var style = document.createElement('style');
            style.textContent = '@keyframes dangerFlash { 0%,100%{box-shadow:0 0 0 rgba(239,83,80,0)} 50%{box-shadow:0 0 20px rgba(239,83,80,0.6)} }';
            document.head.appendChild(style);
            var gd = document.querySelector('.plotly-graph-div');
            if (gd) { gd.style.animation = 'dangerFlash 2s ease-in-out infinite'; gd.style.borderRadius = '8px'; }
        })();
        </script>
        """

    # 底部说明
    fig.add_annotation(
        x=0.5, y=-0.01, xref='paper', yref='paper',
        text=(f'<span style="font-size:9px;color:{TEXT_SECOND}">'
              '绿色=安全(-1~1σ) 黄色=警戒(1~2σ) 红色=危险(>2σ) | 底部折线可拖拽缩放 | '
              f'数据更新至 {str(latest["month"])[:7]}</span>'),
        showarrow=False,
    )

    inject_js = flash_js
    save(fig, '08_因子拥挤度监控', inject_js=inject_js if flash_js else None)
