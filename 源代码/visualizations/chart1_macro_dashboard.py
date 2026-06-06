#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图1: 宏观经济周期仪表盘 — 2×2 仪表盘 + 横条周期判定 + 配置建议"""

import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .common import save, get_gauge_color
from config import BG_DARK, BG_PLOT, TEXT_PRIMARY, TEXT_SECOND, LINE_COLOR, COLORS


# ---- 四个阶段行业映射 ----
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


def _build_phase_scores(latest):
    """计算各阶段支持票数 (0-6)"""
    gv = int(latest['growth_votes'])      # 0-4
    iv = int(latest['inflation_votes'])   # 0-2
    return {
        '复苏期': gv + (2 - iv),
        '过热期': gv + iv,
        '滞胀期': (4 - gv) + iv,
        '衰退期': (4 - gv) + (2 - iv),
    }


def _phase_dots(score, max_dots=6):
    """将票数转为 ●◯ 字符串"""
    filled = int(round(score / 6 * max_dots))
    filled = max(0, min(max_dots, filled))
    return '●' * filled + '◯' * (max_dots - filled)


def _find_previous_phase(df, current_phase, current_idx):
    """查找上次出现当前阶段的月份区间"""
    prev = df[(df['cycle_phase'] == current_phase) & (df.index < current_idx)]
    if len(prev) == 0:
        return None
    # 找最近一段连续区间
    prev_sorted = prev.sort_index()
    last_date = prev_sorted.iloc[-1]['month']
    # 向前找到连续段的起点
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

    # ---- 迷你折线图数据（最近12个月）----
    df12 = df.tail(12).copy()
    df12['t_idx'] = range(len(df12))

    # ================================================================
    #  四个仪表盘定义
    # ================================================================
    gauge_defs = [
        {
            'key': 'pmi', 'title': 'PMI', 'subtitle': '制造业采购经理指数',
            'range': [40, 60], 'threshold': 50,
            'steps': [
                (40, 48, 'rgba(239,83,80,0.30)'),
                (48, 50, 'rgba(255,183,77,0.30)'),
                (50, 52, 'rgba(102,187,106,0.30)'),
                (52, 60, 'rgba(79,195,247,0.30)'),
            ],
            'footnote': f"连续{abs(int(latest['pmi_streak']))}个月{'扩张' if latest['pmi_streak'] > 0 else '收缩'}",
            'fmt': '.1f', 'unit': '',
            'color': '#4fc3f7',
        },
        {
            'key': 'cpi_yoy', 'title': 'CPI', 'subtitle': '居民消费价格指数',
            'range': [-2, 5], 'threshold': None,
            'steps': [
                (-2, 0, 'rgba(79,195,247,0.30)'),
                (0, 2, 'rgba(102,187,106,0.30)'),
                (2, 3, 'rgba(255,183,77,0.30)'),
                (3, 5, 'rgba(239,83,80,0.30)'),
            ],
            'footnote': '食品/非食品分项',
            'fmt': '.1f', 'unit': '%',
            'color': '#ef5350',
        },
        {
            'key': 'bond_10y' if has_bond else 'm2_yoy',
            'title': '国债收益率' if has_bond else 'M2 增速',
            'subtitle': '10年期国债即期收益率' if has_bond else 'M2 货币供应同比',
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
            'footnote': '期限利差 (10Y−2Y)' if has_bond else 'M2货币供应量',
            'fmt': '.2f' if has_bond else '.1f', 'unit': '%',
            'color': '#66bb6a',
        },
        {
            'key': 'sf_yoy', 'title': '社融增速', 'subtitle': '社会融资规模存量同比',
            'range': [4, 14], 'threshold': None,
            'steps': [
                (4, 8, 'rgba(239,83,80,0.30)'),
                (8, 10, 'rgba(255,183,77,0.30)'),
                (10, 12, 'rgba(102,187,106,0.30)'),
                (12, 14, 'rgba(79,195,247,0.30)'),
            ],
            'footnote': '结构: 政府债 / 企业 / 居民',
            'fmt': '.1f', 'unit': '%',
            'color': '#ffb74d',
        },
    ]

    current_phase = latest['cycle_phase']
    phase_scores = _build_phase_scores(latest)
    phase_order = ['复苏期', '过热期', '滞胀期', '衰退期']

    # ================================================================
    #  构建 Figure
    # ================================================================
    fig = go.Figure()

    # ---- 2×2 仪表盘 ----
    # 行列配置: (row, col) → (x_domain, y_domain)
    gauge_positions = [
        (0, 0, 0.02, 0.48, 0.55, 0.90),   # PMI    左上
        (0, 1, 0.52, 0.98, 0.55, 0.90),   # CPI    右上
        (1, 0, 0.02, 0.48, 0.20, 0.55),   # Bond   左下
        (1, 1, 0.52, 0.98, 0.20, 0.55),   # SF     右下
    ]

    for (row, col, x0, x1, y0, y1), gd in zip(gauge_positions, gauge_defs):
        val = latest[gd['key']]
        gauge_steps = [{'range': [lo, hi], 'color': c} for lo, hi, c in gd['steps']]

        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=val,
            number={'font': {'color': '#fff', 'size': 36}, 'suffix': gd['unit'],
                    'valueformat': gd['fmt']},
            title={'text': f"<b>{gd['title']}</b>  {gd['subtitle']}",
                   'font': {'color': TEXT_PRIMARY, 'size': 12}},
            domain={'x': [x0, x1], 'y': [y0, y1]},
            gauge={
                'axis': {'range': gd['range'], 'tickwidth': 1, 'tickcolor': TEXT_SECOND,
                         'tickfont': {'size': 9}},
                'bar': {'color': get_gauge_color(val, gd['steps']), 'thickness': 0.13},
                'bgcolor': BG_PLOT,
                'borderwidth': 0,
                'steps': gauge_steps,
                'threshold': {
                    'line': {'color': 'rgba(255,255,255,0.5)', 'width': 1.5},
                    'thickness': 0.6, 'value': gd['threshold'],
                } if gd['threshold'] else None,
            },
        ))

        # 卡片底部标注
        mid_x = (x0 + x1) / 2
        fig.add_annotation(
            x=mid_x, y=y0 + 0.04,
            text=gd['footnote'],
            xref='paper', yref='paper',
            showarrow=False,
            font=dict(color=TEXT_SECOND, size=9),
        )

    # ---- 迷你折线图 (在每张卡底部) ----
    spark_colors = ['#4fc3f7', '#ef5350', '#66bb6a', '#ffb74d']
    for (row, col, x0, x1, y0, y1), gd, sc in zip(gauge_positions, gauge_defs, spark_colors):
        key = gd['key']
        vals = df12[key].values
        vmin, vmax = vals.min(), vals.max()
        if vmax - vmin < 1e-9:
            y_norm = np.zeros_like(vals)
        else:
            y_norm = (vals - vmin) / (vmax - vmin)
        spark_y = y_norm * 0.06 + y0 + 0.02
        spark_x0 = x0 + 0.03
        spark_x1 = x1 - 0.03

        fig.add_trace(go.Scatter(
            x=df12['t_idx'], y=spark_y,
            mode='lines',
            line=dict(color=sc, width=1.5),
            fill='tozeroy',
            fillcolor=f'rgba{tuple(list(int(sc.lstrip("#")[j:j+2], 16) for j in (0, 2, 4)) + [0.15])}',
            hoverinfo='skip',
            showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=[df12['t_idx'].iloc[-1]], y=[spark_y[-1]],
            mode='markers',
            marker=dict(color=sc, size=7, line=dict(color='#fff', width=1)),
            hoverinfo='skip',
            showlegend=False,
        ))

    # ---- 分隔线 ----
    fig.add_shape(
        type='line', x0=0.03, x1=0.97, y0=0.17, y1=0.17,
        xref='paper', yref='paper',
        line=dict(color='rgba(255,255,255,0.1)', width=1),
    )

    # ================================================================
    #  经济周期判定横条
    # ================================================================
    # 章节标题
    fig.add_annotation(
        x=0.5, y=0.155,
        text='<b>经济周期判定</b>',
        xref='paper', yref='paper', showarrow=False,
        font=dict(color=TEXT_PRIMARY, size=13),
    )

    # 当前阶段的票数
    current_score = phase_scores[current_phase]
    total_votes = 6

    # 4 个阶段卡片
    card_x_positions = [
        (0.02, 0.255),     # 复苏
        (0.265, 0.495),    # 过热
        (0.505, 0.745),    # 滞胀
        (0.755, 0.98),     # 衰退
    ]

    for ci, (phase_name, (cx0, cx1)) in enumerate(zip(phase_order, card_x_positions)):
        is_current = (phase_name == current_phase)
        ps = phase_scores[phase_name]
        color = COLORS[phase_name]
        cy0, cy1 = 0.045, 0.14

        # 卡片背景
        border_color = color if is_current else 'rgba(255,255,255,0.08)'
        border_width = 3 if is_current else 1
        bg_c = f'rgba{tuple(list(int(color.lstrip("#")[j:j+2], 16) for j in (0, 2, 4)) + [0.20 if is_current else 0.06])}'

        fig.add_shape(
            type='rect', x0=cx0, y0=cy0, x1=cx1, y1=cy1,
            xref='paper', yref='paper',
            fillcolor=bg_c, line=dict(color=border_color, width=border_width),
        )

        # 阶段名称
        fig.add_annotation(
            x=(cx0 + cx1) / 2, y=cy1 - 0.015,
            text=f'<b style="font-size:13px;color:{color}">{phase_name}</b>',
            xref='paper', yref='paper', showarrow=False,
        )

        # 信号强度圆点
        dots = _phase_dots(ps, 6)
        dot_html = ''.join(
            f'<span style="color:{color if j < int(round(ps/6*6)) else "#444"};font-size:10px">●</span>'
            for j in range(6)
        )
        fig.add_annotation(
            x=(cx0 + cx1) / 2, y=cy1 - 0.035,
            text=dot_html,
            xref='paper', yref='paper', showarrow=False,
        )

        # 行业建议
        industries = PHASE_INDUSTRIES[phase_name]
        fig.add_annotation(
            x=(cx0 + cx1) / 2, y=cy0 + 0.028,
            text=f'<span style="font-size:9px;color:{TEXT_SECOND}">{industries}</span>',
            xref='paper', yref='paper', showarrow=False,
        )

        # 当前阶段标注 ▲
        if is_current:
            fig.add_annotation(
                x=(cx0 + cx1) / 2, y=cy0 - 0.005,
                text=f'<span style="color:{color};font-size:14px">▲</span> '
                     f'<span style="color:{TEXT_PRIMARY};font-size:10px">当前阶段</span>',
                xref='paper', yref='paper', showarrow=False,
            )

    # ---- 补充信息行 ----
    previous_range = _find_previous_phase(df, current_phase, cur_idx)
    prev_text = f'上次出现: {previous_range}' if previous_range else '首次出现该阶段'

    info_text = (
        f'<span style="font-size:9px;color:{TEXT_SECOND}">'
        f'{prev_text}  |  信号强度: {current_score}/{total_votes} 票'
        f'</span>'
    )
    fig.add_annotation(
        x=0.5, y=0.025,
        text=info_text,
        xref='paper', yref='paper', showarrow=False,
    )

    # ================================================================
    #  配置建议栏
    # ================================================================
    strategy = PHASE_STRATEGY.get(current_phase, '')
    config_text = (
        f'<b style="color:#fff;font-size:12px">配置建议：</b>'
        f'<span style="color:{COLORS[current_phase]};font-size:12px">{strategy}</span>'
    )
    fig.add_annotation(
        x=0.5, y=0.005,
        text=config_text,
        xref='paper', yref='paper', showarrow=False,
        bgcolor='rgba(0,0,0,0.3)', borderpad=6,
    )

    # ================================================================
    #  Layout
    # ================================================================
    fig.update_layout(
        height=1000,
        title=dict(
            text='宏观经济周期仪表盘',
            font=dict(size=20, color='#fff'), x=0.5,
            subtitle=dict(
                text=f'{cur_month}  |  当前判定: <span style="color:{COLORS[current_phase]}">{current_phase}</span>'
                     f'  |  信号强度: {current_score}/{total_votes} 票',
                font=dict(size=11, color=TEXT_SECOND),
            ),
        ),
        paper_bgcolor=BG_DARK, plot_bgcolor=BG_PLOT,
        font=dict(color=TEXT_PRIMARY),
        margin=dict(l=30, r=30, t=80, b=30),
        xaxis=dict(visible=False, domain=[0, 1]),
        yaxis=dict(visible=False, domain=[0, 1]),
    )

    # ================================================================
    #  动画帧与交互
    # ================================================================
    months_all = [d.strftime('%Y-%m') for d in df['month']]
    frames = []
    for idx, (_, row) in enumerate(df.iterrows()):
        frame_traces = []
        for gd in gauge_defs:
            val = row[gd['key']]
            bar_color = get_gauge_color(val, gd['steps'])
            frame_traces.append(go.Indicator(
                value=val,
                gauge={'bar': {'color': bar_color}},
            ))
        frames.append(go.Frame(data=frame_traces, name=months_all[idx]))

    fig.frames = frames

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
    fig.update_layout(meta=f'cycle_phase:{current_phase}')

    # ================================================================
    #  注入 JS: 点击阶段卡片弹窗 + 键盘导航
    # ================================================================
    phase_detail = {
        '复苏期': {'color': COLORS['复苏期'], 'icon': '●',
                   'desc': '经济复苏阶段，企业盈利改善，市场信心回升。PMI 站上荣枯线，社融增速回暖。',
                   'sectors': PHASE_INDUSTRIES['复苏期'],
                   'strategy': PHASE_STRATEGY['复苏期']},
        '过热期': {'color': COLORS['过热期'], 'icon': '●',
                   'desc': '经济过热阶段，通胀压力上升，央行可能收紧货币政策。资源品价格走强。',
                   'sectors': PHASE_INDUSTRIES['过热期'],
                   'strategy': PHASE_STRATEGY['过热期']},
        '滞胀期': {'color': COLORS['滞胀期'], 'icon': '●',
                   'desc': '滞胀阶段，增长放缓但通胀高企，政策面临两难。防御性资产占优。',
                   'sectors': PHASE_INDUSTRIES['滞胀期'],
                   'strategy': PHASE_STRATEGY['滞胀期']},
        '衰退期': {'color': COLORS['衰退期'], 'icon': '●',
                   'desc': '经济衰退阶段，需求疲软，央行降息刺激经济。防御性板块和债券受益。',
                   'sectors': PHASE_INDUSTRIES['衰退期'],
                   'strategy': PHASE_STRATEGY['衰退期']},
    }

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
    const phaseDetail = {json.dumps(phase_detail, ensure_ascii=False)};
    const phaseColors = {{
      '复苏期': '{COLORS["复苏期"]}',
      '过热期': '{COLORS["过热期"]}',
      '滞胀期': '{COLORS["滞胀期"]}',
      '衰退期': '{COLORS["衰退期"]}',
    }};

    document.addEventListener('DOMContentLoaded', function() {{
      const gd = document.querySelector('.plotly-graph-div');
      if (!gd) return;

      gd.on('plotly_click', function(data) {{
        const popup = document.getElementById('phase-popup');
        const content = document.getElementById('phase-popup-content');
        if (data.points.length === 0) return;
        const pt = data.points[0];
        let phase = null;
        if (pt.text && pt.text.includes('期')) {{
          for (const [p, info] of Object.entries(phaseDetail)) {{
            if (pt.text.includes(p)) {{ phase = p; break; }}
          }}
        }}
        if (phase) {{
          const info = phaseDetail[phase];
          content.innerHTML = '<h3 style="color:' + info.color + ';margin:0 0 8px">' +
            info.icon + ' ' + phase + '阶段</h3>' +
            '<p style="font-size:13px;color:#aaa;margin:4px 0">' + info.desc + '</p>' +
            '<p style="margin:8px 0 4px"><b>推荐行业:</b> ' + info.sectors + '</p>' +
            '<p style="margin:4px 0"><b>配置策略:</b> ' + info.strategy + '</p>';
          popup.style.display = 'block';
        }}
      }});

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
