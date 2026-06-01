#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
大数据可视化课程期末项目 — 股票市场行业轮动与因子收益分析
12张图表生成脚本 (Plotly 交互式 HTML)

风格: 专业金融终端暗色主题 (TradingView / Bloomberg 风格)

输出: visualizations/
"""

import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio

# ========== 全局配置 ==========
DATA_DIR = "processed"
OUT_DIR = "visualizations"
os.makedirs(OUT_DIR, exist_ok=True)

# ---- 金融终端暗色主题配色 ----
# 背景层次
BG_DARK      = '#0f1923'   # 画布底色 (TradingView 暗色)
BG_PLOT      = '#1a2332'   # 绘图区底色
BG_SIDEBAR   = '#131c27'   # 侧边栏底色
GRID_COLOR   = 'rgba(255,255,255,0.06)'
TEXT_PRIMARY = '#d1d4dc'   # 主文字
TEXT_SECOND  = '#787b86'   # 次要文字
LINE_COLOR   = 'rgba(255,255,255,0.12)'

# 周期 / 风格 / 预警 专业色板 (饱和度降低, 适合暗底)
COLORS = {
    '复苏期': '#4fc3f7', '过热期': '#ef5350', '滞胀期': '#ffb74d',
    '衰退期': '#5c6bc0', '过渡期': '#546e7a',
    '大盘价值': '#90a4ae', '小盘成长': '#ff8a65',
    '大盘成长': '#64b5f6', '小盘价值': '#4db6ac',
    '正常': '#66bb6a', '关注': '#ffee58', '警示': '#ffa726', '危险': '#ef5350',
}

# 行业色板 (多色, 足够31行业)
INDUSTRY_COLORS = px.colors.qualitative.Dark24 + px.colors.qualitative.Light24

# ---- 全局 Plotly 模板 ----
pio.templates.default = "plotly_dark"

# ---- Matplotlib (如需静态图) ----
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150
plt.rcParams['figure.facecolor'] = BG_DARK
plt.rcParams['axes.facecolor'] = BG_PLOT
plt.rcParams['text.color'] = TEXT_PRIMARY
plt.rcParams['axes.edgecolor'] = '#2a2a3e'
plt.rcParams['axes.labelcolor'] = '#d1d4dc'
plt.rcParams['xtick.color'] = '#787b86'
plt.rcParams['ytick.color'] = '#787b86'
plt.rcParams['grid.color'] = '#1e2a36'


# ================================================================
#  通用工具
# ================================================================
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
    data = {}
    data['macro'] = pd.read_csv(f'{DATA_DIR}/02_macro/macro_cycle.csv', parse_dates=['month'])
    data['style'] = pd.read_csv(f'{DATA_DIR}/02_macro/style_factor_monthly.csv', parse_dates=['month'])
    data['ind_m'] = pd.read_csv(f'{DATA_DIR}/01_industry/industry_monthly.csv', parse_dates=['month'])
    data['ind_q'] = pd.read_csv(f'{DATA_DIR}/01_industry/industry_quarterly.csv', parse_dates=['quarter'])
    data['ind_corr'] = pd.read_csv(f'{DATA_DIR}/01_industry/industry_corr_rolling.csv', parse_dates=['window_end_date'])
    data['ind_cluster'] = pd.read_csv(f'{DATA_DIR}/01_industry/industry_cluster.csv')
    data['factor_ret'] = pd.read_csv(f'{DATA_DIR}/03_factor/factor_returns.csv', parse_dates=['month'])
    data['factor_decomp'] = pd.read_csv(f'{DATA_DIR}/03_factor/industry_factor_decomp.csv')
    data['factor_crowd'] = pd.read_csv(f'{DATA_DIR}/03_factor/factor_crowding.csv', parse_dates=['month'])
    data['sankey'] = pd.read_csv(f'{DATA_DIR}/04_decision/sankey_decision_chain.csv')
    data['stress'] = pd.read_csv(f'{DATA_DIR}/04_decision/stress_test_scenarios.csv')
    data['alert'] = pd.read_csv(f'{DATA_DIR}/04_decision/alert_dashboard.csv', parse_dates=['date'])
    return data


def save(fig, name, is_plotly=True):
    if is_plotly:
        html_path = os.path.join(OUT_DIR, f'{name}.html')
        fig.write_html(html_path)
        # 同时导出高分辨率 PNG (300 DPI)
        png_path = os.path.join(OUT_DIR, f'{name}.png')
        try:
            fig.write_image(png_path, width=1600, height=fig.layout.height or 800, scale=2)
        except Exception as e:
            print(f'    (PNG导出失败: {e})')
    else:
        fig.savefig(os.path.join(OUT_DIR, f'{name}.png'), dpi=300,
                    bbox_inches='tight', facecolor=BG_DARK, edgecolor='none')
        plt.close(fig)
    print(f'  ✓ {name}')


# ================================================================
#  图1: 宏观经济周期仪表盘
# ================================================================
def chart1_macro_dashboard(data):
    df = data['macro'].copy()
    df = df.dropna(subset=['pmi'])
    latest = df.iloc[-1]

    fig = go.Figure()

    # --- 仪表盘 ---
    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=latest['pmi'],
        delta={'reference': 50, 'relative': False},
        title={'text': f"PMI {latest['month'].strftime('%Y-%m')}  |  CPI {latest['cpi_yoy']:.1f}%  |  M2 {latest['m2_yoy']:.1f}%",
               'font': {'color': TEXT_SECOND, 'size': 13}},
        number={'font': {'color': '#fff', 'size': 48}, 'suffix': ''},
        domain={'x': [0.05, 0.95], 'y': [0.42, 0.98]},
        gauge={
            'axis': {'range': [40, 60], 'tickwidth': 1, 'tickcolor': TEXT_SECOND},
            'bar': {'color': '#ef5350' if latest['pmi'] < 50 else '#66bb6a', 'thickness': 0.15},
            'bgcolor': BG_PLOT,
            'borderwidth': 0,
            'steps': [
                {'range': [40, 48], 'color': 'rgba(239,83,80,0.25)'},
                {'range': [48, 50], 'color': 'rgba(255,183,77,0.25)'},
                {'range': [50, 52], 'color': 'rgba(102,187,106,0.25)'},
                {'range': [52, 60], 'color': 'rgba(79,195,247,0.25)'},
            ],
            'threshold': {
                'line': {'color': '#ef5350', 'width': 2},
                'thickness': 0.8, 'value': 50,
            },
        }
    ))

    # --- 走势图 ---
    phase_bg_map = {
        '复苏期': 'rgba(79,195,247,0.08)', '过热期': 'rgba(239,83,80,0.08)',
        '滞胀期': 'rgba(255,183,77,0.08)', '衰退期': 'rgba(92,107,192,0.08)',
    }
    shapes = []
    for phase, color in phase_bg_map.items():
        mask = df['cycle_phase'] == phase
        if mask.sum() > 0:
            phase_df = df[mask]
            for _, row in phase_df.iterrows():
                shapes.append(dict(
                    type='rect',
                    x0=row['month'] - pd.DateOffset(days=14),
                    x1=row['month'] + pd.DateOffset(days=14),
                    y0=0, y1=1, xref='x', yref='paper',
                    fillcolor=color, opacity=0.6, layer='below', line_width=0,
                ))
    shapes.append(dict(
        type='line', x0=df['month'].min(), x1=df['month'].max(),
        y0=50, y1=50, xref='x', yref='y',
        line=dict(dash='dash', color='rgba(255,255,255,0.3)', width=1),
    ))

    fig.add_trace(go.Scatter(
        x=df['month'], y=df['pmi'], mode='lines+markers',
        name='PMI', yaxis='y',
        line=dict(color=COLORS['复苏期'], width=2.5),
        marker=dict(size=4, color=COLORS['复苏期']),
        hovertemplate='<b>%{x|%Y-%m}</b><br>PMI: %{y:.1f}<extra></extra>',
    ))
    fig.add_trace(go.Scatter(
        x=df['month'], y=df['cpi_yoy'], mode='lines+markers',
        name='CPI 同比', yaxis='y', visible='legendonly',
        line=dict(color=COLORS['过热期'], width=2),
        marker=dict(size=3),
    ))
    fig.add_trace(go.Scatter(
        x=df['month'], y=df['m2_yoy'], mode='lines+markers',
        name='M2 同比', yaxis='y', visible='legendonly',
        line=dict(color=COLORS['衰退期'], width=2),
        marker=dict(size=3),
    ))

    fig.update_layout(
        height=800,
        title=dict(text='宏观经济周期仪表盘', font=dict(size=20, color='#fff'), x=0.5),
        paper_bgcolor=BG_DARK, plot_bgcolor=BG_PLOT,
        font=dict(color=TEXT_PRIMARY),
        xaxis=dict(domain=[0.05, 0.95], anchor='y', title='',
                   gridcolor=GRID_COLOR, linecolor=LINE_COLOR, zerolinecolor=LINE_COLOR),
        yaxis=dict(domain=[0.02, 0.40], anchor='x', title='数值 (%)',
                   gridcolor=GRID_COLOR, linecolor=LINE_COLOR, zerolinecolor=LINE_COLOR),
        shapes=shapes,
        annotations=[
            dict(x=df['month'].max(), y=50, text='荣枯线 50',
                 showarrow=False, yshift=10, xref='x', yref='y',
                 font=dict(color=TEXT_SECOND, size=11)),
        ],
        legend=dict(font=dict(color=TEXT_SECOND), orientation='h', y=1.02),
        margin=dict(l=50, r=30, t=70, b=30),
    )
    save(fig, '01_宏观经济周期仪表盘')


# ================================================================
#  图2: 市场风格轮动热力三角图
# ================================================================
def chart2_style_rotation(data):
    df = data['style'].copy()
    fig = dark_figure(height=680)

    colors_q = {
        '大盘价值': COLORS['大盘价值'], '小盘成长': COLORS['小盘成长'],
        '大盘成长': COLORS['大盘成长'], '小盘价值': COLORS['小盘价值'],
        '均衡': TEXT_SECOND,
    }

    for qname, group in df.groupby('style_quadrant'):
        dates = [d.strftime('%Y-%m') for d in group['month']]
        fig.add_trace(go.Scatter(
            x=group['size_strength'], y=group['value_strength'],
            mode='markers',
            name=qname,
            customdata=dates,
            marker=dict(
                size=np.abs(group['style_drift']) * 250 + 10,
                color=colors_q.get(qname, '#888'),
                opacity=0.85,
                line=dict(width=0.5, color='rgba(255,255,255,0.2)'),
            ),
            hovertemplate='<b>%{customdata}</b><br>大小盘溢价: %{x:.2%}<br>价值成长溢价: %{y:.2%}<extra>%{name}</extra>',
        ))

    fig.add_hline(y=0, line_dash="dash", line_color='rgba(255,255,255,0.2)', line_width=1)
    fig.add_vline(x=0, line_dash="dash", line_color='rgba(255,255,255,0.2)', line_width=1)

    annotations = [
        (0.04, 0.04, '大盘价值', COLORS['大盘价值']),
        (-0.04, 0.04, '小盘价值', COLORS['小盘价值']),
        (0.04, -0.04, '大盘成长', COLORS['大盘成长']),
        (-0.04, -0.04, '小盘成长', COLORS['小盘成长']),
    ]
    for x, y, txt, clr in annotations:
        fig.add_annotation(x=x, y=y, text=txt, showarrow=False,
                           font=dict(color=clr, size=11), opacity=0.85)

    dark_layout(fig, height=680,
                title='市场风格轮动热力三角图',
                xaxis=dict(title='大小盘溢价 (小盘 − 大盘)', tickformat='.1%', zeroline=True,
                           zerolinecolor=LINE_COLOR, gridcolor=GRID_COLOR),
                yaxis=dict(title='价值成长溢价 (价值 − 成长)', tickformat='.1%', zeroline=True,
                           zerolinecolor=LINE_COLOR, gridcolor=GRID_COLOR),
                legend=dict(font=dict(color=TEXT_SECOND, size=11)))
    save(fig, '02_风格轮动热力三角图')


# ================================================================
#  图3: 日历热力图 — 行业月度收益率
# ================================================================
def chart3_calendar_heatmap(data):
    df = data['ind_m'].copy()
    industries = sorted(df['industry'].unique())
    months = sorted(df['month'].unique())
    month_labels = [m.strftime('%Y-%m') for m in months]

    # 收益率矩阵
    z_data, text_data = [], []
    for ind in industries:
        row_vals, row_text = [], []
        for m in months:
            sub = df[(df['industry'] == ind) & (df['month'] == m)]['monthly_ret']
            v = sub.iloc[0] if len(sub) > 0 else np.nan
            row_vals.append(v)
            row_text.append(f'{v:.1%}' if not np.isnan(v) else '')
        z_data.append(row_vals)
        text_data.append(row_text)

    # 红绿色偏 — 参考东方财富行业热力图
    custom_colorscale = [
        [0.0, '#26a69a'],  # 深绿 (跌)
        [0.35, '#4db6ac'],
        [0.48, '#1a2332'],  # 中间暗色
        [0.52, '#1a2332'],
        [0.65, '#ef9a9a'],
        [1.0, '#ef5350'],  # 红 (涨)
    ]

    fig = go.Figure(data=go.Heatmap(
        z=z_data, x=month_labels, y=industries,
        colorscale=custom_colorscale, zmid=0,
        text=text_data, texttemplate='%{text}', textfont={"size": 7, "color": TEXT_PRIMARY},
        hovertemplate='<b>%{y}</b> | %{x}<br>月收益: %{z:.2%}<extra></extra>',
        colorbar=dict(
            title='月收益率', title_font=dict(color=TEXT_SECOND),
            tickfont=dict(color=TEXT_SECOND), thickness=12,
            outlinewidth=0,
        ),
        xgap=1, ygap=1,
    ))

    dark_layout(fig, height=900, title='行业月度收益率日历热力图',
                xaxis=dict(title='', tickangle=45, tickfont=dict(size=9, color=TEXT_SECOND)),
                yaxis=dict(title='', tickfont=dict(size=10)))
    fig.update_layout(width=1400)
    save(fig, '03_日历热力图')


# ================================================================
#  图4: 动态气泡图 — 行业风险收益定位
# ================================================================
def chart4_bubble_chart(data):
    df = data['ind_q'].copy()
    df = df.dropna(subset=['ann_vol', 'cum_ret', 'total_mv'])
    df['total_mv_b'] = df['total_mv'] / 1e8
    df = df.sort_values('quarter_str')

    fig = px.scatter(
        df,
        x='ann_vol', y='cum_ret', size='total_mv_b',
        color='industry',
        animation_frame='quarter_str',
        hover_name='industry',
        size_max=60,
        color_discrete_sequence=INDUSTRY_COLORS,
        range_x=[df['ann_vol'].quantile(0.02), df['ann_vol'].quantile(0.98)],
        range_y=[df['cum_ret'].quantile(0.02), df['cum_ret'].quantile(0.98)],
        labels={'ann_vol': '年化波动率', 'cum_ret': '季度累计收益', 'total_mv_b': '总市值(百亿)'},
    )

    fig.add_hline(y=0, line_dash="dash", line_color='rgba(255,255,255,0.25)', line_width=1)
    fig.add_vline(x=df['ann_vol'].median(), line_dash="dash",
                  line_color='rgba(255,255,255,0.15)', line_width=1)

    dark_layout(fig, height=720,
                title='行业风险收益定位与迁移 (动态气泡图)',
                xaxis=dict(title='年化波动率', tickformat='.1%', gridcolor=GRID_COLOR),
                yaxis=dict(title='季度累计收益', tickformat='.1%', gridcolor=GRID_COLOR),
                legend=dict(font=dict(size=9, color=TEXT_SECOND)))
    fig.layout.updatemenus[0].buttons[0].args[1]['frame']['duration'] = 800
    save(fig, '04_动态气泡图')


# ================================================================
#  图5: 行业相关性网络图
# ================================================================
def chart5_correlation_network(data):
    df = data['ind_corr'].copy()
    latest_date = df['window_end_date'].max()
    latest = df[df['window_end_date'] == latest_date].copy()

    # 取相关边
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

    # 边 (按相关性强弱分色)
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

    # 节点
    node_x, node_y, node_text, node_degree = [], [], [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x); node_y.append(y)
        node_text.append(node)
        node_degree.append(G.degree(node))

    deg_arr = np.array(node_degree)
    deg_norm = (deg_arr - deg_arr.min()) / (deg_arr.max() - deg_arr.min() + 0.01)

    # 节点色: 暖色渐变
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


# ================================================================
#  图6: 平行坐标图 — 行业多因子暴露
# ================================================================
def chart6_parallel_coordinates(data):
    df = data['ind_q'].copy()
    latest_q = df['quarter'].max()
    df_q = df[df['quarter'] == latest_q].dropna(subset=['cum_ret_z', 'ann_vol_z', 'med_pe_z'])

    if len(df_q) == 0:
        print("    (平行坐标数据为空，跳过)")
        return

    factor_cols = ['cum_ret_z', 'mom_1q_z', 'mom_4q_z', 'ann_vol_z',
                   'med_pe_z', 'med_pb_z', 'total_mv_z', 'avg_turnover_z']
    factor_labels = ['收益率', '动量 1Q', '动量 4Q', '波动率', 'PE 估值', 'PB 估值', '总市值', '换手率']

    # 行业色
    ind_list = sorted(df_q['industry'].unique())
    ind_to_color = {ind: INDUSTRY_COLORS[i % len(INDUSTRY_COLORS)] for i, ind in enumerate(ind_list)}
    line_colors = [ind_to_color[ind] for ind in df_q['industry']]

    fig = go.Figure(data=go.Parcoords(
        line=dict(color=df_q['cum_ret_z'], colorscale='RdBu_r',
                   showscale=True,
                   colorbar=dict(title='收益率 Z', title_font=dict(color=TEXT_SECOND),
                                 tickfont=dict(color=TEXT_SECOND), thickness=12, outlinewidth=0)),
        dimensions=[
            dict(range=[df_q[c].min(), df_q[c].max()],
                 label=lab, values=df_q[c].values)
            for c, lab in zip(factor_cols, factor_labels)
        ],
        labelside='bottom', labelfont=dict(color=TEXT_PRIMARY, size=11),
    ))

    dark_layout(fig, height=620,
                title=f'行业多因子暴露平行坐标图 ({str(latest_q)[:7]})')
    fig.update_layout(paper_bgcolor=BG_DARK, plot_bgcolor=BG_PLOT)
    save(fig, '06_平行坐标图')


# ================================================================
#  图7: 因子收益分析 (柱状图 + 累计收益)
# ================================================================
def chart7_factor_waterfall(data):
    df = data['factor_ret'].copy()
    factor_labels = ['市场 Rm', '规模 SMB', '价值 HML', '动量 MOM']
    factor_keys = ['Rm', 'SMB', 'HML', 'MOM']
    cum_keys = ['Rm_cum', 'SMB_cum', 'HML_cum', 'MOM_cum']
    colors_f = ['#5c6bc0', '#ef5350', '#66bb6a', '#ffa726']

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('因子月度收益率', '因子累计收益率'),
        column_widths=[0.45, 0.55],
        horizontal_spacing=0.08,
    )

    for i, (key, label) in enumerate(zip(factor_keys, factor_labels)):
        fig.add_trace(go.Bar(
            x=df['month'], y=df[key], name=label,
            marker_color=colors_f[i], opacity=0.85,
            hovertemplate='<b>%{x|%Y-%m}</b><br>' + label + ': %{y:.2%}<extra></extra>',
        ), row=1, col=1)

    for i, (ckey, label) in enumerate(zip(cum_keys, factor_labels)):
        fig.add_trace(go.Scatter(
            x=df['month'], y=df[ckey], mode='lines',
            name=label, line=dict(color=colors_f[i], width=2.5),
            hovertemplate='<b>%{x|%Y-%m}</b><br>' + label + ' 累计: %{y:.2f}<extra></extra>',
        ), row=1, col=2)

    fig.add_hline(y=0, line_dash="solid", line_color='rgba(255,255,255,0.2)',
                  line_width=1, row=1, col=1)
    fig.add_hline(y=1, line_dash="dash", line_color='rgba(255,255,255,0.15)',
                  line_width=1, row=1, col=2)

    dark_layout(fig, height=520,
                title='因子收益分析',
                barmode='group',
                xaxis=dict(title='', gridcolor=GRID_COLOR),
                xaxis2=dict(title='', gridcolor=GRID_COLOR),
                yaxis=dict(title='月收益率', tickformat='.1%', gridcolor=GRID_COLOR),
                yaxis2=dict(title='累计收益 (基准=1)', tickformat='.1f', gridcolor=GRID_COLOR),
                legend=dict(font=dict(color=TEXT_SECOND, size=11), orientation='h', y=1.05))
    save(fig, '07_因子收益分析')


# ================================================================
#  图8: 因子拥挤度监控仪表
# ================================================================
def chart8_crowding_dashboard(data):
    df = data['factor_crowd'].copy()

    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=('估值价差 (PB Top−Bottom)', '因子内相关性', '综合拥挤度分数'),
        vertical_spacing=0.08,
        shared_xaxes=True,
    )

    # Panel 1: 估值价差
    fig.add_trace(go.Scatter(
        x=df['month'], y=df['valuation_spread'], mode='lines+markers',
        name='估值价差', line=dict(color='#5c6bc0', width=2),
        marker=dict(size=4, color='#5c6bc0'),
        hovertemplate='%{x|%Y-%m}<br>价差: %{y:.1f}<extra></extra>',
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df['month'], y=df['valuation_spread'].rolling(3).mean(),
        mode='lines', name='3月均线', line=dict(color='rgba(255,255,255,0.35)', dash='dash', width=1),
        hoverinfo='skip',
    ), row=1, col=1)

    # Panel 2: 因子内相关性
    fig.add_trace(go.Scatter(
        x=df['month'], y=df['within_factor_corr'], mode='lines+markers',
        name='因子内相关', line=dict(color='#ef5350', width=2),
        marker=dict(size=4, color='#ef5350'),
        fill='tozeroy', fillcolor='rgba(239,83,80,0.1)',
        hovertemplate='%{x|%Y-%m}<br>相关性: %{y:.3f}<extra></extra>',
    ), row=2, col=1)

    # Panel 3: 拥挤度分数 (带预警区)
    df_plot = df.dropna(subset=['crowding_score'])
    bar_colors = []
    for v in df_plot['crowding_score']:
        if v > 2: bar_colors.append('#ef5350')
        elif v > 1: bar_colors.append('#ffa726')
        elif v < -1: bar_colors.append('#66bb6a')
        else: bar_colors.append('#ffee58')

    fig.add_trace(go.Bar(
        x=df_plot['month'], y=df_plot['crowding_score'],
        marker_color=bar_colors, name='拥挤度分数',
        hovertemplate='%{x|%Y-%m}<br>拥挤度: %{y:.2f}<extra></extra>',
    ), row=3, col=1)

    for y_val, color, label in [(2, '#ef5350', '危险线'), (1, '#ffa726', '警示线')]:
        fig.add_hline(y=y_val, line_dash="dash", line_color=color,
                      line_width=1, row=3, col=1,
                      annotation_text=label, annotation_font=dict(color=color, size=10))
    fig.add_hline(y=0, line_color='rgba(255,255,255,0.2)', line_width=1, row=3, col=1)

    # 拥挤等级标注
    df_plot2 = df.dropna(subset=['crowding_level'])
    for _, row in df_plot2.iterrows():
        if row['crowding_level'] in ('警示', '危险'):
            fig.add_annotation(
                x=row['month'], y=row['crowding_score'],
                text=row['crowding_level'], showarrow=True, arrowhead=1,
                arrowsize=1, arrowwidth=1, arrowcolor=COLORS.get(row['crowding_level'], '#fff'),
                font=dict(color=COLORS.get(row['crowding_level'], '#fff'), size=10),
                yshift=15, row=3, col=1,
            )

    dark_layout(fig, height=800,
                title='因子拥挤度监控仪表',
                showlegend=False,
                yaxis=dict(title='PB 价差', gridcolor=GRID_COLOR),
                yaxis2=dict(title='平均相关性', gridcolor=GRID_COLOR),
                yaxis3=dict(title='拥挤度 Z-score', gridcolor=GRID_COLOR),
                xaxis3=dict(title='', gridcolor=GRID_COLOR))
    save(fig, '08_因子拥挤度监控')


# ================================================================
#  图9: 牛熊周期箱线图
# ================================================================
def chart9_regime_boxplot(data):
    df_ind = data['ind_m'].copy()
    df_macro = data['macro'].copy()
    df = df_ind.merge(df_macro[['month', 'cycle_phase']], on='month', how='left')
    df = df[df['cycle_phase'].notna()]

    top_inds = df.groupby('industry')['monthly_ret'].std().nlargest(15).index
    df_plot = df[df['industry'].isin(top_inds)]

    fig = px.box(
        df_plot, x='industry', y='monthly_ret', color='cycle_phase',
        color_discrete_map=COLORS,
        labels={'monthly_ret': '月收益率', 'industry': '', 'cycle_phase': '周期阶段'},
        category_orders={'cycle_phase': ['复苏期', '过热期', '滞胀期', '衰退期']},
        notched=False,
    )

    fig.add_hline(y=0, line_dash="dash", line_color='rgba(255,255,255,0.25)', line_width=1)

    # 为每个 box 设置暗色风格
    fig.update_traces(marker=dict(size=3, opacity=0.6), line=dict(width=1))

    dark_layout(fig, height=620,
                title='牛熊周期下行业收益率分布对比',
                xaxis=dict(title='', tickangle=45, gridcolor=GRID_COLOR,
                          tickfont=dict(size=10)),
                yaxis=dict(title='月收益率', tickformat='.1%', gridcolor=GRID_COLOR),
                boxmode='group',
                legend=dict(font=dict(color=TEXT_SECOND, size=10)))
    save(fig, '09_牛熊周期箱线图')


# ================================================================
#  图10: 行业配置桑基图
# ================================================================
def chart10_sankey(data):
    df = data['sankey'].copy()

    all_nodes = list(set(df['source'].unique()) | set(df['target'].unique()))
    node_map = {n: i for i, n in enumerate(all_nodes)}

    macro_phases = {'复苏期', '过热期', '滞胀期', '衰退期', '过渡期'}
    style_strats = {n for n in all_nodes if '盘' in n and '成长' in n or '价值' in n}

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


# ================================================================
#  图11: 策略压力测试热图
# ================================================================
def chart11_stress_test(data):
    df = data['stress'].copy()
    pivot = df.pivot_table(values='cum_return', index='industry', columns='scenario', aggfunc='mean')

    # 自定义 colorscale: 绿→暗→红
    stress_colorscale = [
        [0.0, '#26a69a'],
        [0.35, '#4db6ac'],
        [0.48, '#1a2332'],
        [0.52, '#1a2332'],
        [0.65, '#ef9a9a'],
        [1.0, '#ef5350'],
    ]

    text_matrix = [[f'{v:.1%}' if not np.isnan(v) else '' for v in row] for row in pivot.values]

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
        colorscale=stress_colorscale, zmid=0,
        text=text_matrix, texttemplate='%{text}',
        textfont=dict(size=9, color=TEXT_PRIMARY),
        hovertemplate='<b>%{y}</b> | %{x}<br>区间收益: %{z:.2%}<extra></extra>',
        colorbar=dict(
            title='累计收益', title_font=dict(color=TEXT_SECOND),
            tickfont=dict(color=TEXT_SECOND), tickformat='.1%',
            thickness=12, outlinewidth=0,
        ),
    ))

    dark_layout(fig, height=720,
                title='策略压力测试热图 — 极端事件下各行业收益表现',
                xaxis=dict(title='', tickfont=dict(size=10), gridcolor=GRID_COLOR),
                yaxis=dict(title='', tickfont=dict(size=10)))
    fig.update_layout(width=1000)
    save(fig, '11_压力测试热图')


# ================================================================
#  图12: 实时监控预警仪表盘
# ================================================================
def chart12_alert_dashboard(data):
    df = data['alert'].copy()
    if len(df) == 0:
        print('  (预警数据为空，跳过)')
        return

    df['date'] = pd.to_datetime(df['date'])
    alert_colors_map = {'正常': COLORS['正常'], '关注': COLORS['关注'],
                        '警示': COLORS['警示'], '危险': COLORS['危险']}

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('预警信号时间线', '预警级别分布', '各行业预警次数 Top15', '各指标异常触发次数'),
        specs=[[{"type": "scatter", "colspan": 2}, None],
               [{"type": "bar"}, {"type": "bar"}]],
        vertical_spacing=0.12, horizontal_spacing=0.1,
    )

    # (1,1) 预警时间线
    for level in ['关注', '警示', '危险']:
        sub = df[df['alert_level'] == level]
        if len(sub) > 0:
            fig.add_trace(go.Scatter(
                x=sub['date'], y=sub['z_score'].abs(),
                mode='markers', name=level,
                marker=dict(color=alert_colors_map[level], size=6,
                           opacity=0.75, line=dict(width=0.5, color='rgba(255,255,255,0.2)')),
                customdata=sub[['industry', 'metric']].values,
                hovertemplate='<b>%{customdata[0]}</b><br>指标: %{customdata[1]}<br>|Z|: %{y:.1f}<extra>%{name}</extra>',
            ), row=1, col=1)

    # (2,1) 预警级别分布 (水平柱状图更专业)
    level_counts = df['alert_level'].value_counts()
    level_order = ['正常', '关注', '警示', '危险']
    level_counts = level_counts.reindex([l for l in level_order if l in level_counts.index])
    fig.add_trace(go.Bar(
        y=level_counts.index, x=level_counts.values, orientation='h',
        marker_color=[alert_colors_map.get(l, '#888') for l in level_counts.index],
        text=level_counts.values, textposition='outside',
        textfont=dict(color=TEXT_PRIMARY, size=11),
        hovertemplate='%{y}: %{x} 次<extra></extra>',
    ), row=2, col=1)

    # (2,2) 各行业预警次数
    ind_counts = df['industry'].value_counts().head(15)
    fig.add_trace(go.Bar(
        x=ind_counts.index, y=ind_counts.values,
        marker_color='#5c6bc0', opacity=0.85,
        text=ind_counts.values, textposition='outside',
        textfont=dict(color=TEXT_PRIMARY, size=10),
        hovertemplate='%{x}: %{y} 次<extra></extra>',
    ), row=2, col=2)

    dark_layout(fig, height=750,
                title='实时监控预警仪表盘',
                showlegend=True,
                xaxis=dict(title='', gridcolor=GRID_COLOR),
                xaxis2=dict(title='预警次数', gridcolor=GRID_COLOR),
                xaxis3=dict(title='', tickangle=45, gridcolor=GRID_COLOR),
                yaxis=dict(title='|Z-score|', gridcolor=GRID_COLOR),
                yaxis2=dict(title='', gridcolor=GRID_COLOR),
                yaxis3=dict(title='预警次数', gridcolor=GRID_COLOR),
                legend=dict(font=dict(color=TEXT_SECOND, size=10), orientation='h', y=1.05))
    save(fig, '12_实时监控预警仪表盘')


# ================================================================
#  Main
# ================================================================
if __name__ == '__main__':
    print("=" * 60)
    print("加载数据...")
    data = load_all()
    print(f"  已加载 {len(data)} 个数据集")

    print("\n" + "=" * 60)
    print("生成可视化图表 (金融终端暗色主题)...\n")

    charts = [
        ('图1 宏观经济周期仪表盘', chart1_macro_dashboard),
        ('图2 风格轮动热力三角图', chart2_style_rotation),
        ('图3 日历热力图', chart3_calendar_heatmap),
        ('图4 动态气泡图', chart4_bubble_chart),
        ('图5 行业相关性网络图', chart5_correlation_network),
        ('图6 平行坐标图', chart6_parallel_coordinates),
        ('图7 因子收益分析', chart7_factor_waterfall),
        ('图8 因子拥挤度监控', chart8_crowding_dashboard),
        ('图9 牛熊周期箱线图', chart9_regime_boxplot),
        ('图10 行业配置桑基图', chart10_sankey),
        ('图11 压力测试热图', chart11_stress_test),
        ('图12 实时监控预警仪表盘', chart12_alert_dashboard),
    ]

    for name, func in charts:
        try:
            print(f"  [{name}]")
            func(data)
        except Exception as e:
            print(f"  ✗ 生成失败: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"可视化完成！输出目录: {os.path.abspath(OUT_DIR)}")
    for f in sorted(os.listdir(OUT_DIR)):
        print(f"  {f}")
