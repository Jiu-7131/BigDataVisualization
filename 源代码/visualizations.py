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


def save(fig, name, is_plotly=True, inject_js=None):
    if is_plotly:
        html_path = os.path.join(OUT_DIR, f'{name}.html')
        fig.write_html(html_path)
        # 注入自定义 JavaScript (如交互增强)
        if inject_js:
            with open(html_path, 'r', encoding='utf-8') as f:
                html = f.read()
            html = html.replace('</body>', inject_js + '\n</body>')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
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
    """图1: 宏观经济周期仪表盘 — 4+1 布局（四个指标卡片 + 周期判定区）"""
    df = data['macro'].copy()
    df = df.dropna(subset=['pmi'])
    latest = df.iloc[-1]
    cur_month = latest['month'].strftime('%Y-%m')

    # 检查数据可用性
    has_bond = 'bond_10y' in df.columns and df['bond_10y'].notna().any()
    has_sf = 'sf_yoy' in df.columns and df['sf_yoy'].notna().any()

    # ---- 辅助: 取最近12个月用于迷你折线图 ----
    df12 = df.tail(12).copy()
    df12['t_idx'] = range(len(df12))

    # ============================================================
    #  四个指标卡片定义
    # ============================================================
    # 每张卡: (键名, 标题, 范围, 色区列表, 当前值格式化, 阈值线, 单位后缀)
    # 色区: [(low, high, color_rgba), ...]
    gauge_defs = [
        {
            'key': 'pmi', 'title': 'PMI 制造业采购经理指数', 'unit': '',
            'range': [40, 60], 'threshold': 50,
            'steps': [
                (40, 48, 'rgba(239,83,80,0.30)'),
                (48, 50, 'rgba(255,183,77,0.30)'),
                (50, 52, 'rgba(102,187,106,0.30)'),
                (52, 60, 'rgba(79,195,247,0.30)'),
            ],
            'annotation': f"连续{abs(int(latest['pmi_streak']))}个月{'扩张' if latest['pmi_streak'] > 0 else '收缩'}",
            'fmt': '.1f',
        },
        {
            'key': 'cpi_yoy', 'title': 'CPI 居民消费价格指数', 'unit': '%',
            'range': [-2, 5], 'threshold': None,
            'steps': [
                (-2, 0, 'rgba(79,195,247,0.30)'),
                (0, 2, 'rgba(102,187,106,0.30)'),
                (2, 3, 'rgba(255,183,77,0.30)'),
                (3, 5, 'rgba(239,83,80,0.30)'),
            ],
            'annotation': f"食品/非食品分项",
            'fmt': '.1f',
        },
        {
            'key': 'bond_10y' if has_bond else 'm2_yoy',
            'title': '10Y国债收益率' if has_bond else 'M2 同比增速',
            'unit': '%',
            'range': [1.5, 4.5] if has_bond else [5, 13],
            'threshold': None,
            'steps': [
                (1.5, 2.5, 'rgba(79,195,247,0.30)'),
                (2.5, 3.0, 'rgba(102,187,106,0.30)'),
                (3.0, 3.5, 'rgba(255,183,77,0.30)'),
                (3.5, 4.5, 'rgba(239,83,80,0.30)'),
            ] if has_bond else [
                (5, 8, 'rgba(79,195,247,0.30)'),
                (8, 10, 'rgba(102,187,106,0.30)'),
                (10, 12, 'rgba(255,183,77,0.30)'),
                (12, 13, 'rgba(239,83,80,0.30)'),
            ],
            'annotation': '期限利差(10Y-2Y)' if has_bond else 'M2货币供应',
            'fmt': '.2f' if has_bond else '.1f',
        },
        {
            'key': 'sf_yoy', 'title': '社融存量同比增速', 'unit': '%',
            'range': [4, 14], 'threshold': None,
            'steps': [
                (4, 8, 'rgba(239,83,80,0.30)'),
                (8, 10, 'rgba(255,183,77,0.30)'),
                (10, 12, 'rgba(102,187,106,0.30)'),
                (12, 14, 'rgba(79,195,247,0.30)'),
            ],
            'annotation': '结构:政府债/企业/居民',
            'fmt': '.1f',
        },
    ]

    # ============================================================
    #  构建 Figure
    # ============================================================
    fig = go.Figure()

    # --- 4 个仪表盘 (go.Indicator) ---
    for i, gd in enumerate(gauge_defs):
        x0 = i * 0.25 + 0.005
        x1 = (i + 1) * 0.25 - 0.005
        val = latest[gd['key']]
        gauge_steps = [
            {'range': [lo, hi], 'color': c} for lo, hi, c in gd['steps']
        ]
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=val,
            number={'font': {'color': '#fff', 'size': 32}, 'suffix': gd['unit'],
                    'valueformat': gd['fmt']},
            title={'text': f"<b>{gd['title']}</b><br><span style='font-size:10px;color:{TEXT_SECOND}'>{cur_month}</span>",
                   'font': {'color': TEXT_PRIMARY, 'size': 11}},
            domain={'x': [x0, x1], 'y': [0.42, 0.96]},
            gauge={
                'axis': {'range': gd['range'], 'tickwidth': 1, 'tickcolor': TEXT_SECOND,
                         'tickfont': {'size': 9}},
                'bar': {'color': get_gauge_color(val, gd['steps']), 'thickness': 0.12},
                'bgcolor': BG_PLOT,
                'borderwidth': 0,
                'steps': gauge_steps,
                'threshold': {
                    'line': {'color': 'rgba(255,255,255,0.5)', 'width': 1.5},
                    'thickness': 0.6, 'value': gd['threshold'],
                } if gd['threshold'] else None,
            },
            customdata=[gd['annotation']],
            meta=[gd['title']],
        ))
        # 卡片底部标注
        fig.add_annotation(
            x=(x0 + x1) / 2, y=0.44,
            text=gd['annotation'],
            xref='paper', yref='paper',
            showarrow=False,
            font=dict(color=TEXT_SECOND, size=9),
        )

    # --- 迷你折线图 (最近12个月) ---
    spark_colors = ['#4fc3f7', '#ef5350', '#66bb6a', '#ffb74d']
    for i, gd in enumerate(gauge_defs):
        x0 = i * 0.25 + 0.02
        x1 = (i + 1) * 0.25 - 0.02
        key = gd['key']
        vals = df12[key].values
        # 归一化到 [0, 1] 用于迷你图显示
        y_norm = (vals - vals.min()) / (vals.max() - vals.min() + 1e-9)
        # 用独立 x/y 轴对定位
        fig.add_trace(go.Scatter(
            x=df12['t_idx'], y=y_norm * 0.08 + 0.34,
            mode='lines',
            line=dict(color=spark_colors[i], width=1.5),
            fill='tozeroy',
            fillcolor=f'rgba{tuple(list(int(spark_colors[i].lstrip("#")[j:j+2], 16) for j in (0, 2, 4)) + [0.15])}',
            hoverinfo='skip',
            showlegend=False,
        ))
        # 当前值标记点
        fig.add_trace(go.Scatter(
            x=[df12['t_idx'].iloc[-1]], y=[y_norm[-1] * 0.08 + 0.34],
            mode='markers',
            marker=dict(color=spark_colors[i], size=6, line=dict(color='#fff', width=1)),
            hoverinfo='skip',
            showlegend=False,
        ))

    # --- 迷你折线图 (隐藏坐标轴，仅展示趋势) ---

    # ============================================================
    #  周期判定区 (2×2 矩阵)
    # ============================================================
    # 矩阵边界
    matrix_x0, matrix_x1 = 0.08, 0.92
    matrix_y0, matrix_y1 = 0.02, 0.30
    mid_x = (matrix_x0 + matrix_x1) / 2
    mid_y = (matrix_y0 + matrix_y1) / 2

    # 四个象限: (x0, y0, x1, y1, label, sub_label, color, bg_color)
    # 布局: 上排=增长上行, 下排=增长下行; 左列=低通胀, 右列=高通胀
    quadrants = [
        # 增长上行 + 低通胀 → 复苏 (左上)
        (matrix_x0, mid_y, mid_x, matrix_y1, '复苏期',
         '汽车 / 家电 / 建材', COLORS['复苏期'],
         'rgba(79,195,247,0.15)'),
        # 增长上行 + 高通胀 → 过热 (右上)
        (mid_x, mid_y, matrix_x1, matrix_y1, '过热期',
         '有色金属 / 煤炭 / 钢铁', COLORS['过热期'],
         'rgba(239,83,80,0.15)'),
        # 增长下行 + 低通胀 → 衰退 (左下)
        (matrix_x0, matrix_y0, mid_x, mid_y, '衰退期',
         '食品饮料 / 医药 / 公用事业', COLORS['衰退期'],
         'rgba(92,107,192,0.15)'),
        # 增长下行 + 高通胀 → 滞胀 (右下)
        (mid_x, matrix_y0, matrix_x1, mid_y, '滞胀期',
         '农业 / 黄金 / 能源', COLORS['滞胀期'],
         'rgba(255,183,77,0.15)'),
    ]

    current_phase = latest['cycle_phase']

    for qx0, qy0, qx1, qy1, phase_name, industries, color, bg_color in quadrants:
        is_current = (phase_name == current_phase)
        border_color = color if is_current else 'rgba(255,255,255,0.08)'
        border_width = 3 if is_current else 1
        bg = color if is_current else bg_color
        bg = bg.replace('0.15', '0.30') if is_current else bg

        # 象限背景矩形
        fig.add_shape(
            type='rect', x0=qx0, y0=qy0, x1=qx1, y1=qy1,
            xref='paper', yref='paper',
            fillcolor=bg, line=dict(color=border_color, width=border_width),
            layer='below',
        )
        # 象限标签
        fig.add_annotation(
            x=(qx0 + qx1) / 2, y=(qy0 + qy1) / 2 + 0.02,
            text=f"<b>{phase_name}</b>",
            xref='paper', yref='paper',
            showarrow=False,
            font=dict(color=color, size=is_current and 16 or 13),
        )
        # 行业配置建议
        fig.add_annotation(
            x=(qx0 + qx1) / 2, y=(qy0 + qy1) / 2 - 0.025,
            text=f"<span style='font-size:9px;color:{TEXT_SECOND}'>{industries}</span>",
            xref='paper', yref='paper',
            showarrow=False,
        )

    # 轴标签 — Y: 上=增长上行, 下=增长下行; X: 左=低通胀, 右=高通胀
    fig.add_annotation(x=matrix_x0 - 0.01, y=mid_y - 0.02, text='增长<br>下行',
                       xref='paper', yref='paper', showarrow=False,
                       font=dict(color=TEXT_SECOND, size=9), align='center')
    fig.add_annotation(x=matrix_x0 - 0.01, y=mid_y + 0.02, text='增长<br>上行',
                       xref='paper', yref='paper', showarrow=False,
                       font=dict(color=TEXT_SECOND, size=9), align='center')
    fig.add_annotation(x=mid_x, y=matrix_y1 + 0.015, text='低通胀 ← CPI/国债 → 高通胀',
                       xref='paper', yref='paper', showarrow=False,
                       font=dict(color=TEXT_SECOND, size=10))
    fig.add_annotation(x=matrix_x0, y=matrix_y1 + 0.005, text='低通胀',
                       xref='paper', yref='paper', showarrow=False,
                       font=dict(color='#4fc3f7', size=9))
    fig.add_annotation(x=matrix_x1, y=matrix_y1 + 0.005, text='高通胀',
                       xref='paper', yref='paper', showarrow=False,
                       font=dict(color='#ef5350', size=9))

    # 当前阶段指示器
    fig.add_annotation(
        x=mid_x, y=matrix_y1 + 0.06,
        text=(f"<b>当前阶段: {current_phase}</b>  |  "
              f"增长票 {int(latest['growth_votes'])}/4  |  "
              f"通胀票 {int(latest['inflation_votes'])}/2  |  "
              f"数据月: {cur_month}"),
        xref='paper', yref='paper', showarrow=False,
        font=dict(color='#fff', size=13),
        bgcolor='rgba(0,0,0,0.4)', borderpad=8,
    )

    # 投票细则说明
    cpi_vote = 1 if latest['cpi_yoy'] >= 2.5 else 0
    rate_label = '国债' if has_bond else 'M2'
    rate_val = latest['bond_10y'] if has_bond else latest['m2_yoy']
    rate_vote = 1 if (has_bond and latest['bond_10y'] >= 3.0) or (not has_bond and latest['m2_yoy'] >= 10.0) else 0
    voting_detail = (
        f"PMI({latest['pmi']:.1f}) → {int(latest['pmi_votes'])}票  |  "
        f"社融({latest['sf_yoy']:.1f}%) → {int(latest['sf_votes'])}票  |  "
        f"CPI({latest['cpi_yoy']:.1f}%) → {cpi_vote}票  |  "
        f"{rate_label}({rate_val:.1f}%) → {rate_vote}票")
    fig.add_annotation(
        x=mid_x, y=matrix_y1 + 0.09,
        text=f"<span style='font-size:9px;color:{TEXT_SECOND}'>{voting_detail}</span>",
        xref='paper', yref='paper', showarrow=False,
    )

    # ============================================================
    #  Layout
    # ============================================================
    fig.update_layout(
        height=850,
        title=dict(text='宏观经济周期仪表盘', font=dict(size=20, color='#fff'), x=0.5,
                   subtitle=dict(text='数据来源: Tushare Pro | 6票投票制周期判定',
                                 font=dict(size=10, color=TEXT_SECOND))),
        paper_bgcolor=BG_DARK, plot_bgcolor=BG_PLOT,
        font=dict(color=TEXT_PRIMARY),
        margin=dict(l=30, r=30, t=80, b=20),
        # 隐藏所有坐标轴（迷你折线图使用paper坐标）
        xaxis=dict(visible=False, domain=[0, 1]),
        yaxis=dict(visible=False, domain=[0, 1]),
    )

    # ============================================================
    #  历史回看 & 自动播放 (Frames)
    # ============================================================
    months_all = [d.strftime('%Y-%m') for d in df['month']]
    frames = []
    for idx, (_, row) in enumerate(df.iterrows()):
        month_str = months_all[idx]
        # 只更新4个 indicator 的值和 bar 颜色
        frame_data = []
        for i, gd in enumerate(gauge_defs):
            val = row[gd['key']]
            steps = gd['steps']
            bar_color = get_gauge_color(val, steps)
            frame_data.append(go.Indicator(
                value=val,
                gauge={'bar': {'color': bar_color}},
            ))
        frames.append(go.Frame(data=frame_data, name=month_str))

    fig.frames = frames

    # 播放/暂停按钮
    fig.update_layout(
        updatemenus=[dict(
            type='buttons',
            direction='left',
            x=0.5, y=-0.02,
            xanchor='center', yanchor='top',
            buttons=[
                dict(label='▶ 自动播放',
                     method='animate',
                     args=[None, {'frame': {'duration': 600, 'redraw': False},
                                  'fromcurrent': True,
                                  'mode': 'immediate',
                                  'transition': {'duration': 300}}]),
                dict(label='⏸ 暂停',
                     method='animate',
                     args=[[None], {'frame': {'duration': 0, 'redraw': False},
                                    'mode': 'immediate',
                                    'transition': {'duration': 0}}]),
            ],
            font=dict(color=TEXT_PRIMARY, size=11),
            bgcolor=BG_PLOT,
            bordercolor=LINE_COLOR,
            borderwidth=1,
        )],
    )

    # 月份滑块
    sliders = [dict(
        active=len(df) - 1,
        currentvalue={'prefix': '查看月份: ', 'font': {'color': TEXT_PRIMARY}},
        pad=dict(t=10),
        steps=[dict(
            label=m,
            method='animate',
            args=[[m], {'frame': {'duration': 300, 'redraw': False},
                        'mode': 'immediate',
                        'transition': {'duration': 300}}],
        ) for m in months_all],
        font=dict(color=TEXT_SECOND, size=9),
        bgcolor=BG_PLOT,
        bordercolor=LINE_COLOR,
    )]

    fig.update_layout(sliders=sliders)

    # 添加 CSS 类名以便 dashboard 识别
    fig.update_layout(
        meta=f'cycle_phase:{current_phase}',
    )

    # 行业配置详情（点击象限展开）
    phase_detail = {
        '复苏期': {'color': COLORS['复苏期'], 'icon': '🟢',
                     'desc': '经济复苏阶段，企业盈利改善，市场信心回升。',
                     'sectors': '汽车、家电、建材、电子、机械设备',
                     'strategy': '超配周期成长股，关注可选消费和制造业'},
        '过热期': {'color': COLORS['过热期'], 'icon': '🟠',
                     'desc': '经济过热阶段，通胀压力上升，央行可能收紧货币政策。',
                     'sectors': '有色金属、煤炭、钢铁、化工、石油石化',
                     'strategy': '超配资源品和周期股，警惕政策转向风险'},
        '滞胀期': {'color': COLORS['滞胀期'], 'icon': '🔴',
                     'desc': '滞胀阶段，增长放缓+通胀高企，政策两难。',
                     'sectors': '农业、黄金、能源、公用事业',
                     'strategy': '防御为主，配置抗通胀资产和必需消费'},
        '衰退期': {'color': COLORS['衰退期'], 'icon': '🔵',
                     'desc': '经济衰退阶段，需求疲软，央行降息刺激经济。',
                     'sectors': '食品饮料、医药生物、公用事业、银行',
                     'strategy': '超配防御性板块，关注高股息和必选消费'},
    }

    import json
    phase_detail_json = json.dumps(phase_detail, ensure_ascii=False)

    inject_js = f'''
    <div id="phase-popup" style="display:none;position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);
        background:#1a2332;color:#d1d4dc;padding:24px;border-radius:12px;z-index:9999;
        max-width:420px;box-shadow:0 8px 32px rgba(0,0,0,0.6);border:1px solid rgba(255,255,255,0.12);">
      <div id="phase-popup-content"></div>
      <button onclick="document.getElementById('phase-popup').style.display='none'"
        style="margin-top:12px;padding:6px 16px;background:#3498db;border:none;color:#fff;
        border-radius:4px;cursor:pointer;font-size:12px;">关闭</button>
    </div>
    <script>
    const phaseDetail = {phase_detail_json};
    const phaseColors = {{
      '复苏期': '{COLORS["复苏期"]}',
      '过热期': '{COLORS["过热期"]}',
      '滞胀期': '{COLORS["滞胀期"]}',
      '衰退期': '{COLORS["衰退期"]}',
    }};

    document.addEventListener('DOMContentLoaded', function() {{
      const gd = document.querySelector('.plotly-graph-div');
      if (!gd) return;

      // 点击象限弹出行业配置详情
      gd.on('plotly_click', function(data) {{
        const popup = document.getElementById('phase-popup');
        const content = document.getElementById('phase-popup-content');
        if (data.points.length === 0) return;
        const pt = data.points[0];
        if (pt.x === undefined) return;
        // 判断是否点击在矩阵区域的annotation附近
        const clickX = pt.x;
        const clickY = pt.y;
        // annotation 点击: text 含阶段名
        let phase = null;
        if (pt.text && pt.text.includes('期')) {{
          for (const [p, info] of Object.entries(phaseDetail)) {{
            if (pt.text.includes(p)) {{ phase = p; break; }}
          }}
        }}
        if (phase) {{
          const info = phaseDetail[phase];
          content.innerHTML = `<h3 style="color:${{info.color}};margin:0 0 8px">${{info.icon}} ${{phase}}阶段</h3>
            <p style="font-size:13px;color:#aaa;margin:4px 0">${{info.desc}}</p>
            <p style="margin:8px 0 4px"><b>推荐行业:</b> ${{info.sectors}}</p>
            <p style="margin:4px 0"><b>配置策略:</b> ${{info.strategy}}</p>`;
          popup.style.display = 'block';
        }}
      }});

      // 键盘导航: 左右箭头切换月份帧
      let currentFrame = {len(df) - 1};
      const totalFrames = {len(df)};
      document.addEventListener('keydown', function(e) {{
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        if (e.key === 'ArrowLeft' && currentFrame > 0) {{
          e.preventDefault();
          currentFrame--;
          Plotly.animate(gd, [months_all[currentFrame]], {{
            frame: {{duration: 300, redraw: false}},
            mode: 'immediate',
            transition: {{duration: 300}}
          }});
        }}
        if (e.key === 'ArrowRight' && currentFrame < totalFrames - 1) {{
          e.preventDefault();
          currentFrame++;
          Plotly.animate(gd, [months_all[currentFrame]], {{
            frame: {{duration: 300, redraw: false}},
            mode: 'immediate',
            transition: {{duration: 300}}
          }});
        }}
      }});

      const months_all = {json.dumps([d.strftime('%Y-%m') for d in df['month']], ensure_ascii=False)};
    }});
    </script>'''

    save(fig, '01_宏观经济周期仪表盘', inject_js=inject_js)


def get_gauge_color(value, steps):
    """根据值所在色区返回对应颜色"""
    for lo, hi, color in steps:
        if lo <= value <= hi:
            # 提取 rgba 中的主色
            return color.replace('0.30', '0.85').replace('rgba', 'rgb').replace(',0.85)', ')')
    return '#888'


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
