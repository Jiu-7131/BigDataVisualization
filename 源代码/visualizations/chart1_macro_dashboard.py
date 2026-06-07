#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图1: 宏观经济周期仪表盘 — 2×2 仪表盘 + 趋势图 + 1×4 周期判定条"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .common import save, get_gauge_color
from config import BG_DARK, BG_PLOT, TEXT_PRIMARY, TEXT_SECOND, LINE_COLOR, COLORS


PHASE_INDUSTRIES = {
    '复苏期': '汽车 / 家电 / 建材',
    '过热期': '有色金属 / 煤炭 / 钢铁',
    '滞胀期': '农业 / 黄金 / 能源',
    '衰退期': '食品饮料 / 医药 / 公用事业',
}

PHASE_STRATEGY = {
    '复苏期': '超配 汽车、家电、建材 | 低配 公用事业',
    '过热期': '超配 有色、煤炭、钢铁 | 低配 消费',
    '滞胀期': '超配 农业、黄金、能源 | 低配 制造',
    '衰退期': '超配 食饮、医药、公用 | 低配 周期',
}


def _phase_scores(latest):
    gv = int(latest['growth_votes'])
    iv = int(latest['inflation_votes'])
    return {
        '复苏期': gv + (2 - iv),
        '过热期': gv + iv,
        '滞胀期': (4 - gv) + iv,
        '衰退期': (4 - gv) + (2 - iv),
    }


def _find_previous_phase(df, phase, cur_idx):
    prev = df[(df['cycle_phase'] == phase) & (df.index < cur_idx)]
    if len(prev) == 0:
        return None
    prev_sorted = prev.sort_index()
    last_date = prev_sorted.iloc[-1]['month']
    idx = prev_sorted.index[-1]
    while idx - 1 in prev_sorted.index:
        idx -= 1
    first_date = prev_sorted.loc[idx, 'month']
    return f"{first_date.strftime('%Y.%m')} ~ {last_date.strftime('%Y.%m')}"


def generate(data):
    df = data['macro'].copy()
    df = df.dropna(subset=['pmi']).reset_index(drop=True)
    latest = df.iloc[-1]
    cur_idx = len(df) - 1
    cur_month = latest['month'].strftime('%Y年%m月')

    has_bond = 'bond_10y' in df.columns and df['bond_10y'].notna().any()

    # 全部月份用于趋势图
    all_months = pd.to_datetime(df['month'])
    month_labels = [d.strftime('%Y-%m') for d in all_months]

    gauge_defs = [
        {
            'key': 'pmi', 'label': 'PMI', 'unit': '',
            'range': [40, 60], 'threshold': 50,
            'steps': [
                (40, 48, 'rgba(239,83,80,0.30)'), (48, 50, 'rgba(255,183,77,0.30)'),
                (50, 52, 'rgba(102,187,106,0.30)'), (52, 60, 'rgba(79,195,247,0.30)'),
            ],
            'footnote': lambda r: f"连续{abs(int(r['pmi_streak']))}个月{'扩张' if r['pmi_streak'] > 0 else '收缩'}",
            'fmt': '.1f', 'color': '#4fc3f7',
        },
        {
            'key': 'cpi_yoy', 'label': 'CPI', 'unit': '%',
            'range': [-2, 5], 'threshold': None,
            'steps': [
                (-2, 0, 'rgba(79,195,247,0.30)'), (0, 2, 'rgba(102,187,106,0.30)'),
                (2, 3, 'rgba(255,183,77,0.30)'), (3, 5, 'rgba(239,83,80,0.30)'),
            ],
            'footnote': lambda r: '食品/非食品分项',
            'fmt': '.1f', 'color': '#ef5350',
        },
        {
            'key': 'bond_10y' if has_bond else 'm2_yoy',
            'label': '国债收益率' if has_bond else 'M2 增速',
            'unit': '%',
            'range': [1.5, 4.5] if has_bond else [5, 13],
            'threshold': None,
            'steps': [
                (1.5, 2.5, 'rgba(79,195,247,0.30)'), (2.5, 3.0, 'rgba(102,187,106,0.30)'),
                (3.0, 3.5, 'rgba(255,183,77,0.30)'), (3.5, 4.5, 'rgba(239,83,80,0.30)'),
            ] if has_bond else [
                (5, 8, 'rgba(79,195,247,0.30)'), (8, 10, 'rgba(102,187,106,0.30)'),
                (10, 12, 'rgba(255,183,77,0.30)'), (12, 13, 'rgba(239,83,80,0.30)'),
            ],
            'footnote': lambda r: '期限利差 (10Y−2Y)' if has_bond else 'M2货币供应量',
            'fmt': '.2f' if has_bond else '.1f', 'color': '#66bb6a',
        },
        {
            'key': 'sf_yoy', 'label': '社融增速', 'unit': '%',
            'range': [4, 14], 'threshold': None,
            'steps': [
                (4, 8, 'rgba(239,83,80,0.30)'), (8, 10, 'rgba(255,183,77,0.30)'),
                (10, 12, 'rgba(102,187,106,0.30)'), (12, 14, 'rgba(79,195,247,0.30)'),
            ],
            'footnote': lambda r: '结构: 政府债 / 企业 / 居民',
            'fmt': '.1f', 'color': '#ffb74d',
        },
    ]

    current_phase = latest['cycle_phase']
    scores = _phase_scores(latest)
    phase_order = ['复苏期', '过热期', '滞胀期', '衰退期']

    # ================================================================
    #  Figure
    # ================================================================
    fig = go.Figure()

    # ---- 1×4 Gauges (y=[0.52, 0.90]) ----
    gauge_pos = [
        (0.01, 0.24, 0.52, 0.91),   # PMI
        (0.255, 0.485, 0.52, 0.91), # CPI
        (0.505, 0.735, 0.52, 0.91), # 国债
        (0.755, 0.99, 0.52, 0.91),  # 社融
    ]

    for (x0, x1, y0, y1), gd in zip(gauge_pos, gauge_defs):
        val = latest[gd['key']]
        steps_cfg = [{'range': [lo, hi], 'color': c} for lo, hi, c in gd['steps']]

        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=val,
            number={'font': {'color': '#fff', 'size': 40}, 'suffix': gd['unit'],
                    'valueformat': gd['fmt']},
            title={'text': f"<b>{gd['label']}</b>",
                   'font': {'color': TEXT_PRIMARY, 'size': 14}},
            domain={'x': [x0, x1], 'y': [y0, y1]},
            gauge={
                'axis': {'range': gd['range'], 'tickwidth': 1, 'tickcolor': TEXT_SECOND,
                         'tickfont': {'size': 10}},
                'bar': {'color': get_gauge_color(val, gd['steps']), 'thickness': 0.15},
                'bgcolor': BG_PLOT, 'borderwidth': 0,
                'steps': steps_cfg,
                'threshold': {
                    'line': {'color': 'rgba(255,255,255,0.6)', 'width': 2},
                    'thickness': 0.7, 'value': gd['threshold'],
                } if gd['threshold'] else None,
            },
        ))

        # Gauge footnote
        mid_x = (x0 + x1) / 2
        fig.add_annotation(x=mid_x, y=y0 - 0.01,
                           text=gd['footnote'](latest),
                           xref='paper', yref='paper', showarrow=False,
                           font=dict(color=TEXT_SECOND, size=11))

    # ---- Divider ----
    fig.add_shape(type='line', x0=0.01, x1=0.99, y0=0.495, y1=0.495,
                  xref='paper', yref='paper',
                  line=dict(color='rgba(255,255,255,0.08)', width=1))

    # ---- Shared Trend Chart (xaxis2/yaxis2, domain y=[0.23, 0.47]) ----
    spark_colors = ['#4fc3f7', '#ef5350', '#66bb6a', '#ffb74d']
    spark_names = ['PMI', 'CPI', '国债收益率' if has_bond else 'M2增速', '社融增速']

    # 趋势线显示当前月起过去12个月（共13个月）
    trend_start = max(0, len(df) - 13)
    trend_months = all_months[trend_start:]
    for gd, sc, sn in zip(gauge_defs, spark_colors, spark_names):
        y_vals = df[gd['key']].values[trend_start:]
        fig.add_trace(go.Scatter(
            x=trend_months, y=y_vals,
            mode='lines+markers',
            name=sn,
            line=dict(color=sc, width=3),
            marker=dict(size=5, color=sc),
            xaxis='x2', yaxis='y2',
            hovertemplate=f'<b>{sn}</b><br>%{{x|%Y-%m}}<br>%{{y:{gd["fmt"]}}}{gd["unit"]}<extra></extra>',
        ))

    fig.update_layout(
        xaxis2=dict(
            domain=[0.03, 0.97],
            anchor='y2',
            title=dict(text='月份', font=dict(color=TEXT_SECOND, size=11)),
            tickfont=dict(color=TEXT_SECOND, size=10),
            tickangle=-45,
            nticks=7,
            gridcolor='rgba(255,255,255,0.05)',
            linecolor=LINE_COLOR,
            range=[trend_months.iloc[0], trend_months.iloc[-1]],
            autorange=False,
        ),
        yaxis2=dict(
            domain=[0.23, 0.47],
            anchor='x2',
            title=dict(text='趋势值', font=dict(color=TEXT_SECOND, size=11)),
            tickfont=dict(color=TEXT_SECOND, size=10),
            gridcolor='rgba(255,255,255,0.05)',
            linecolor=LINE_COLOR,
            zeroline=False,
        ),
        legend=dict(
            x=0.5, y=0.465, xanchor='center', yanchor='bottom',
            orientation='h',
            font=dict(color=TEXT_SECOND, size=10),
            bgcolor='rgba(0,0,0,0)',
        ),
    )

    # ---- 1×4 Phase Cards (y=[0.02, 0.20]) ----
    fig.add_annotation(x=0.5, y=0.215, text='<b>经济周期判定</b>',
                       xref='paper', yref='paper', showarrow=False,
                       font=dict(color=TEXT_PRIMARY, size=13))

    card_x = [(0.015, 0.257), (0.265, 0.507), (0.505, 0.747), (0.755, 0.985)]
    for ci, (phase_name, (cx0, cx1)) in enumerate(zip(phase_order, card_x)):
        is_current = (phase_name == current_phase)
        ps = scores[phase_name]
        color = COLORS[phase_name]
        cy0, cy1 = 0.025, 0.20

        border_color = color if is_current else 'rgba(255,255,255,0.1)'
        border_w = 2 if is_current else 1
        bg = f'rgba{tuple(list(int(color.lstrip("#")[j:j+2], 16) for j in (0, 2, 4)) + [0.15 if is_current else 0.04])}'

        fig.add_shape(type='rect', x0=cx0, y0=cy0, x1=cx1, y1=cy1,
                      xref='paper', yref='paper',
                      fillcolor=bg, line=dict(color=border_color, width=border_w))

        fig.add_annotation(x=(cx0 + cx1) / 2, y=cy1 - 0.018,
                           text=f'<b style="font-size:14px;color:{color}">{phase_name}</b>',
                           xref='paper', yref='paper', showarrow=False)

        n_filled = min(6, max(0, int(round(ps))))
        dots = ''.join(
            f'<span style="color:{color if j < n_filled else "#2a2a3a"};font-size:10px">●</span>'
            for j in range(6)
        )
        fig.add_annotation(x=(cx0 + cx1) / 2, y=cy1 - 0.048,
                           text=dots,
                           xref='paper', yref='paper', showarrow=False)

        fig.add_annotation(x=(cx0 + cx1) / 2, y=cy0 + 0.035,
                           text=f'<span style="font-size:10px;color:{TEXT_SECOND}">{PHASE_INDUSTRIES[phase_name]}</span>',
                           xref='paper', yref='paper', showarrow=False)

        if is_current:
            fig.add_annotation(x=(cx0 + cx1) / 2, y=cy0 - 0.005,
                               text=f'<span style="color:{color};font-size:14px">▲</span> '
                                    f'<span style="color:{TEXT_PRIMARY};font-size:11px">当前阶段</span>',
                               xref='paper', yref='paper', showarrow=False)

    # Info line
    prev_range = _find_previous_phase(df, current_phase, cur_idx)
    prev_text = f'上次出现: {prev_range}' if prev_range else '首次出现该阶段'
    fig.add_annotation(x=0.5, y=0.008,
                       text=f'<span style="font-size:10px;color:{TEXT_SECOND}">{prev_text}  |  信号强度: {scores[current_phase]}/6 票</span>',
                       xref='paper', yref='paper', showarrow=False)

    # Strategy bar
    fig.add_annotation(x=0.5, y=-0.005,
                       text=f'<b style="color:#fff;font-size:12px">配置建议：</b>'
                            f'<span style="color:{COLORS[current_phase]};font-size:12px">{PHASE_STRATEGY[current_phase]}</span>',
                       xref='paper', yref='paper', showarrow=False,
                       bgcolor='rgba(0,0,0,0.3)', borderpad=6)

    # ================================================================
    #  Layout
    # ================================================================
    fig.update_layout(
        height=750,
        title=dict(
            text='宏观经济周期仪表盘',
            font=dict(size=22, color='#fff'), x=0.5,
            subtitle=dict(
                text=f'{cur_month}  |  当前判定: <span style="color:{COLORS[current_phase]}">{current_phase}</span>',
                font=dict(size=12, color=TEXT_SECOND),
            ),
        ),
        paper_bgcolor=BG_DARK, plot_bgcolor=BG_PLOT,
        font=dict(color=TEXT_PRIMARY),
        margin=dict(l=20, r=20, t=75, b=20),
        hovermode='x unified',
    )

    # ================================================================
    #  Slider + Frames
    # ================================================================
    # Build frames: each frame updates gauge values + trend lines (trailing 13 months)
    # Frame structure: 4 gauge + 4 trend + 1 vline = 9 traces (matches base figure)
    frames = []
    for idx in range(len(df)):
        frame_data = []
        row = df.iloc[idx]

        # 4 gauge updates
        for gd in gauge_defs:
            val = row[gd['key']]
            frame_data.append(go.Indicator(
                value=val,
                gauge={'bar': {'color': get_gauge_color(val, gd['steps'])}},
            ))

        # 4 trend lines — trailing 13 months from selected month
        start = max(0, idx - 12)
        end = idx + 1
        win = df.iloc[start:end]
        win_months = all_months[start:end]
        for gd, sc in zip(gauge_defs, spark_colors):
            y_vals = win[gd['key']].values
            frame_data.append(go.Scatter(
                x=win_months, y=y_vals,
                mode='lines+markers',
                line=dict(color=sc, width=3),
                marker=dict(size=6, color=sc),
                xaxis='x2', yaxis='y2',
                showlegend=False,
                hoverinfo='skip',
            ))

        # 1 vertical line at selected month
        sel_date = all_months.iloc[idx]
        y_min = min(df[gd['key']].min() for gd in gauge_defs) - 0.5
        y_max = max(df[gd['key']].max() for gd in gauge_defs) + 0.5
        frame_data.append(go.Scatter(
            x=[sel_date, sel_date],
            y=[y_min, y_max],
            mode='lines',
            line=dict(color='rgba(255,255,255,0.35)', width=1.5, dash='dash'),
            showlegend=False,
            xaxis='x2', yaxis='y2',
            hoverinfo='skip',
        ))

        # Set axis range so rightmost tick = current month
        pad_days = pd.Timedelta(days=15)
        frames.append(go.Frame(
            data=frame_data,
            name=month_labels[idx],
            layout=go.Layout(
                xaxis2=dict(range=[win_months.iloc[0] - pad_days, win_months.iloc[-1] + pad_days])
            ),
        ))

    fig.frames = frames

    # Base trace #9: vline at latest month
    base_start = max(0, len(df) - 13)
    base_win = all_months[base_start:]
    y_min = min(df[gd['key']].min() for gd in gauge_defs) - 0.5
    y_max = max(df[gd['key']].max() for gd in gauge_defs) + 0.5
    fig.add_trace(go.Scatter(
        x=[all_months.iloc[-1], all_months.iloc[-1]],
        y=[y_min, y_max],
        mode='lines',
        line=dict(color='rgba(255,255,255,0.35)', width=1.5, dash='dash'),
        showlegend=False,
        xaxis='x2', yaxis='y2',
        hoverinfo='skip',
    ))

    fig.update_layout(
        updatemenus=[dict(
            type='buttons', direction='left',
            x=0.5, y=-0.04, xanchor='center', yanchor='top',
            buttons=[
                dict(label='▶ 播放', method='animate',
                     args=[None, {'frame': {'duration': 500, 'redraw': True},
                                  'fromcurrent': True, 'mode': 'immediate',
                                  'transition': {'duration': 200}}]),
                dict(label='⏸ 暂停', method='animate',
                     args=[[None], {'frame': {'duration': 0, 'redraw': False},
                                    'mode': 'immediate', 'transition': {'duration': 0}}]),
            ],
            font=dict(color=TEXT_PRIMARY, size=11),
            bgcolor=BG_PLOT, bordercolor=LINE_COLOR, borderwidth=1,
        )],
        sliders=[dict(
            active=len(df) - 1,
            currentvalue={'prefix': '查看月份: ', 'font': {'color': TEXT_PRIMARY, 'size': 12}},
            pad=dict(t=10),
            steps=[dict(
                label=m, method='animate',
                args=[[m], {'frame': {'duration': 250, 'redraw': True},
                            'mode': 'immediate', 'transition': {'duration': 150}}],
            ) for m in month_labels],
            font=dict(color=TEXT_SECOND, size=10),
            bgcolor=BG_PLOT, bordercolor=LINE_COLOR,
        )],
    )

    fig.update_layout(meta=f'cycle_phase:{current_phase}')

    save(fig, '01_宏观经济周期仪表盘')
