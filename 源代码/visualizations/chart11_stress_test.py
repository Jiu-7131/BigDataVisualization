#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图11: 策略压力测试热图 — 综合评分 + 最脆弱标注 + 情景说明"""

import numpy as np
import plotly.graph_objects as go

from .common import dark_layout, save
from config import TEXT_PRIMARY, TEXT_SECOND, GRID_COLOR


# 情景定义
SCENARIO_DEFS = {
    '2022年4月\n疫情封控': '上海疫情封控，供应链中断，市场恐慌下跌',
    '2022年10月\n市场探底': '美联储激进加息，人民币贬值，A股二次探底',
    '2024年2月\n量化风暴': '量化DMA策略集中平仓，微盘股流动性危机',
    '2024年9月\n政策组合拳': '央行降准+房地产刺激+资本市场改革政策密集出台',
    '2025年4月\n关税冲击': '中美关税升级，出口链承压，市场避险情绪升温',
}


def generate(data):
    df = data['stress'].copy()
    pivot = df.pivot_table(values='cum_return', index='industry',
                           columns='scenario', aggfunc='mean')

    # 综合压力得分（均值越低越脆弱）
    stress_score = pivot.mean(axis=1)
    ordered_inds = stress_score.sort_values().index.tolist()
    pivot = pivot.loc[ordered_inds]

    # 添加综合评分列
    pivot['综合压力得分'] = stress_score[ordered_inds].values

    scenarios = [c for c in pivot.columns if c != '综合压力得分']
    all_cols = list(pivot.columns)

    # 每行业最脆弱情景
    worst_scenario = {}
    for ind in pivot.index:
        row_vals = {s: pivot.loc[ind, s] for s in scenarios}
        worst_s = min(row_vals, key=row_vals.get)
        worst_scenario[ind] = {'scenario': worst_s, 'value': row_vals[worst_s]}

    # ---- 构建颜色矩阵 ----
    z = pivot.values.copy()
    # 为综合评分列单独归一化
    score_col_idx = all_cols.index('综合压力得分')
    scenario_cols_idx = [i for i, c in enumerate(all_cols) if c != '综合压力得分']

    # 底色：使用自定义阈值映射
    text_matrix = []
    for i, ind in enumerate(pivot.index):
        row_text = []
        for j, col in enumerate(all_cols):
            v = pivot.iloc[i, j]
            if np.isnan(v):
                row_text.append('')
            elif col == '综合压力得分':
                row_text.append(f'<b>{v:.1%}</b>')
            else:
                # 标注最脆弱情景
                if worst_scenario[ind]['scenario'] == col:
                    row_text.append(f'▼{v:.1%}')
                else:
                    row_text.append(f'{v:.1%}')
        text_matrix.append(row_text)

    # 自定义 colorscale: 绿→黄→红
    stress_colorscale = [
        [0.0, '#26a69a'],    # 深绿 (正收益)
        [0.2, '#66bb6a'],    # 绿
        [0.4, '#ffb74d'],    # 黄
        [0.6, '#ef9a9a'],    # 浅红
        [1.0, '#ef5350'],    # 深红 (负收益)
    ]

    fig = go.Figure(data=go.Heatmap(
        z=z, x=all_cols, y=pivot.index.tolist(),
        colorscale=stress_colorscale,
        zmid=0,
        text=text_matrix, texttemplate='%{text}',
        textfont=dict(size=9, color=TEXT_PRIMARY),
        hovertemplate='<b>%{y}</b> | %{x}<br>区间收益: %{z:.2%}<extra></extra>',
        colorbar=dict(
            title='累计收益', title_font=dict(color=TEXT_SECOND),
            tickfont=dict(color=TEXT_SECOND), tickformat='.1%',
            thickness=12, outlinewidth=0,
        ),
        xgap=1, ygap=1,
    ))

    # ---- 最脆弱标注（三角形） ----
    for ind in pivot.index:
        ws = worst_scenario[ind]
        col_idx = all_cols.index(ws['scenario'])
        row_idx = list(pivot.index).index(ind)
        fig.add_annotation(
            x=col_idx, y=row_idx,
            text='<b>⚠</b>',
            showarrow=False,
            font=dict(color='#fff', size=11),
            bgcolor='rgba(0,0,0,0.5)',
            borderpad=2,
        )

    # ---- 情景说明 ----
    scenario_notes = []
    for s in scenarios:
        clean_name = s.replace('\n', ' ')
        desc = SCENARIO_DEFS.get(s, '')
        scenario_notes.append(f'<b>{clean_name}</b>: {desc}')

    fig.add_annotation(
        x=0.5, y=-0.14, xref='paper', yref='paper',
        text='<br>'.join(scenario_notes),
        showarrow=False,
        font=dict(size=9, color=TEXT_SECOND),
        align='left',
        bordercolor='rgba(255,255,255,0.06)',
        borderwidth=1, borderpad=8,
        bgcolor='rgba(17,24,39,0.7)',
    )

    dark_layout(fig, height=820,
                title='策略压力测试热图 — 极端事件下各行业收益表现<br>'
                      f'<sup style="font-size:10px;color:{TEXT_SECOND}">'
                      '▼ = 该行业最脆弱情景 | 行业按综合脆弱度排序 | 绿色=正收益 红色=回撤</sup>')
    fig.update_layout(
        width=1050,
        xaxis=dict(title='', tickfont=dict(size=9, color=TEXT_PRIMARY), gridcolor=GRID_COLOR),
        yaxis=dict(title='', tickfont=dict(size=10, color=TEXT_PRIMARY)),
        margin=dict(l=20, r=20, t=80, b=200),
    )

    save(fig, '11_压力测试热图')
