#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
共享工具函数 — dark_figure, dark_layout, load_all, save, get_gauge_color
"""

import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from config import (
    BG_DARK, BG_PLOT, TEXT_PRIMARY, TEXT_SECOND, GRID_COLOR, LINE_COLOR,
    OUT_DIR, PROCESSED_01_INDUSTRY, PROCESSED_02_MACRO,
    PROCESSED_03_FACTOR, PROCESSED_04_DECISION,
)


def dark_figure(height=600):
    """返回预配暗色主题的 Figure"""
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor=BG_DARK, plot_bgcolor=BG_PLOT,
        font=dict(color=TEXT_PRIMARY, size=12),
        title=dict(font=dict(size=18, color='#fff'), x=0.5),
        margin=dict(l=40, r=20, t=60, b=40),
        height=height,
        xaxis=dict(gridcolor=GRID_COLOR, linecolor=LINE_COLOR, zerolinecolor=LINE_COLOR),
        yaxis=dict(gridcolor=GRID_COLOR, linecolor=LINE_COLOR, zerolinecolor=LINE_COLOR),
        legend=dict(font=dict(color=TEXT_SECOND)),
        hoverlabel=dict(bgcolor=BG_PLOT, font=dict(color=TEXT_PRIMARY)),
    )
    return fig


def dark_layout(fig, height=600, title='', **kwargs):
    """给已有 figure 应用暗色主题 layout"""
    base_font = dict(color=TEXT_PRIMARY, size=12)
    extra_font = kwargs.pop('font', {})
    base_font.update(extra_font)
    fig.update_layout(
        paper_bgcolor=BG_DARK, plot_bgcolor=BG_PLOT,
        font=base_font,
        title=dict(text=title, font=dict(size=18, color='#fff'), x=0.5),
        margin=dict(l=40, r=20, t=60, b=40),
        height=height,
        hoverlabel=dict(bgcolor=BG_PLOT, font=dict(color=TEXT_PRIMARY)),
        **kwargs,
    )
    fig.update_xaxes(gridcolor=GRID_COLOR, linecolor=LINE_COLOR, zerolinecolor=LINE_COLOR)
    fig.update_yaxes(gridcolor=GRID_COLOR, linecolor=LINE_COLOR, zerolinecolor=LINE_COLOR)


def load_all():
    """加载所有处理后数据到一个字典"""
    data = {}
    data['macro']        = pd.read_csv(f'{PROCESSED_02_MACRO}/macro_cycle.csv', parse_dates=['month'])
    data['style']        = pd.read_csv(f'{PROCESSED_02_MACRO}/style_factor_monthly.csv', parse_dates=['month'])
    data['ind_m']        = pd.read_csv(f'{PROCESSED_01_INDUSTRY}/industry_monthly.csv', parse_dates=['month'])
    data['ind_q']        = pd.read_csv(f'{PROCESSED_01_INDUSTRY}/industry_quarterly.csv', parse_dates=['quarter'])
    data['ind_corr']     = pd.read_csv(f'{PROCESSED_01_INDUSTRY}/industry_corr_rolling.csv', parse_dates=['window_end_date'])
    data['ind_cluster']  = pd.read_csv(f'{PROCESSED_01_INDUSTRY}/industry_cluster.csv')
    data['factor_ret']   = pd.read_csv(f'{PROCESSED_03_FACTOR}/factor_returns.csv', parse_dates=['month'])
    data['factor_decomp'] = pd.read_csv(f'{PROCESSED_03_FACTOR}/industry_factor_decomp.csv')
    data['factor_crowd'] = pd.read_csv(f'{PROCESSED_03_FACTOR}/factor_crowding.csv', parse_dates=['month'])
    data['sankey']       = pd.read_csv(f'{PROCESSED_04_DECISION}/sankey_decision_chain.csv')
    data['stress']       = pd.read_csv(f'{PROCESSED_04_DECISION}/stress_test_scenarios.csv')
    data['alert']        = pd.read_csv(f'{PROCESSED_04_DECISION}/alert_dashboard.csv', parse_dates=['date'])
    return data


def save(fig, name, is_plotly=True, inject_js=None):
    """保存图表为 HTML + PNG"""
    if is_plotly:
        html_path = os.path.join(OUT_DIR, f'{name}.html')
        fig.write_html(html_path)
        if inject_js:
            with open(html_path, 'r', encoding='utf-8') as f:
                html = f.read()
            html = html.replace('</body>', inject_js + '\n</body>')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
        png_path = os.path.join(OUT_DIR, f'{name}.png')
        try:
            fig.write_image(png_path, width=1600, height=fig.layout.height or 800, scale=2)
        except Exception as e:
            print(f'    (PNG导出失败: {e})')
    else:
        import matplotlib.pyplot as plt
        fig.savefig(os.path.join(OUT_DIR, f'{name}.png'), dpi=300,
                    bbox_inches='tight', facecolor=BG_DARK, edgecolor='none')
        plt.close(fig)
    print(f'  ✓ {name}')


def get_gauge_color(value, steps):
    """根据值所在色区返回对应颜色"""
    for lo, hi, color in steps:
        if lo <= value <= hi:
            return color.replace('0.30', '0.85').replace('rgba', 'rgb').replace(',0.85)', ')')
    return '#888'
