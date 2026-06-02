#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图1: 宏观经济周期仪表盘 — 4+1 布局（四个指标卡片 + 周期判定区）"""

import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .common import save, get_gauge_color
from config import BG_DARK, BG_PLOT, TEXT_PRIMARY, TEXT_SECOND, LINE_COLOR, COLORS


def generate(data):
    df = data['macro'].copy()
    df = df.dropna(subset=['pmi'])
    latest = df.iloc[-1]
    cur_month = latest['month'].strftime('%Y-%m')

    has_bond = 'bond_10y' in df.columns and df['bond_10y'].notna().any()

    df12 = df.tail(12).copy()
    df12['t_idx'] = range(len(df12))

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
            'annotation': '食品/非食品分项',
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

    fig = go.Figure()

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
        fig.add_annotation(
            x=(x0 + x1) / 2, y=0.44,
            text=gd['annotation'],
            xref='paper', yref='paper',
            showarrow=False,
            font=dict(color=TEXT_SECOND, size=9),
        )

    spark_colors = ['#4fc3f7', '#ef5350', '#66bb6a', '#ffb74d']
    for i, gd in enumerate(gauge_defs):
        x0 = i * 0.25 + 0.02
        x1 = (i + 1) * 0.25 - 0.02
        key = gd['key']
        vals = df12[key].values
        y_norm = (vals - vals.min()) / (vals.max() - vals.min() + 1e-9)
        fig.add_trace(go.Scatter(
            x=df12['t_idx'], y=y_norm * 0.08 + 0.34,
            mode='lines',
            line=dict(color=spark_colors[i], width=1.5),
            fill='tozeroy',
            fillcolor=f'rgba{tuple(list(int(spark_colors[i].lstrip("#")[j:j+2], 16) for j in (0, 2, 4)) + [0.15])}',
            hoverinfo='skip',
            showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=[df12['t_idx'].iloc[-1]], y=[y_norm[-1] * 0.08 + 0.34],
            mode='markers',
            marker=dict(color=spark_colors[i], size=6, line=dict(color='#fff', width=1)),
            hoverinfo='skip',
            showlegend=False,
        ))

    matrix_x0, matrix_x1 = 0.08, 0.92
    matrix_y0, matrix_y1 = 0.02, 0.30
    mid_x = (matrix_x0 + matrix_x1) / 2
    mid_y = (matrix_y0 + matrix_y1) / 2

    quadrants = [
        (matrix_x0, mid_y, mid_x, matrix_y1, '复苏期',
         '汽车 / 家电 / 建材', COLORS['复苏期'], 'rgba(79,195,247,0.15)'),
        (mid_x, mid_y, matrix_x1, matrix_y1, '过热期',
         '有色金属 / 煤炭 / 钢铁', COLORS['过热期'], 'rgba(239,83,80,0.15)'),
        (matrix_x0, matrix_y0, mid_x, mid_y, '衰退期',
         '食品饮料 / 医药 / 公用事业', COLORS['衰退期'], 'rgba(92,107,192,0.15)'),
        (mid_x, matrix_y0, matrix_x1, mid_y, '滞胀期',
         '农业 / 黄金 / 能源', COLORS['滞胀期'], 'rgba(255,183,77,0.15)'),
    ]

    current_phase = latest['cycle_phase']

    for qx0, qy0, qx1, qy1, phase_name, industries, color, bg_color in quadrants:
        is_current = (phase_name == current_phase)
        border_color = color if is_current else 'rgba(255,255,255,0.08)'
        border_width = 3 if is_current else 1
        bg = color if is_current else bg_color
        bg = bg.replace('0.15', '0.30') if is_current else bg

        fig.add_shape(
            type='rect', x0=qx0, y0=qy0, x1=qx1, y1=qy1,
            xref='paper', yref='paper',
            fillcolor=bg, line=dict(color=border_color, width=border_width),
            layer='below',
        )
        fig.add_annotation(
            x=(qx0 + qx1) / 2, y=(qy0 + qy1) / 2 + 0.02,
            text=f"<b>{phase_name}</b>",
            xref='paper', yref='paper',
            showarrow=False,
            font=dict(color=color, size=is_current and 16 or 13),
        )
        fig.add_annotation(
            x=(qx0 + qx1) / 2, y=(qy0 + qy1) / 2 - 0.025,
            text=f"<span style='font-size:9px;color:{TEXT_SECOND}'>{industries}</span>",
            xref='paper', yref='paper',
            showarrow=False,
        )

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

    fig.update_layout(
        height=850,
        title=dict(text='宏观经济周期仪表盘', font=dict(size=20, color='#fff'), x=0.5,
                   subtitle=dict(text='数据来源: Tushare Pro | 6票投票制周期判定',
                                 font=dict(size=10, color=TEXT_SECOND))),
        paper_bgcolor=BG_DARK, plot_bgcolor=BG_PLOT,
        font=dict(color=TEXT_PRIMARY),
        margin=dict(l=30, r=30, t=80, b=20),
        xaxis=dict(visible=False, domain=[0, 1]),
        yaxis=dict(visible=False, domain=[0, 1]),
    )

    months_all = [d.strftime('%Y-%m') for d in df['month']]
    frames = []
    for idx, (_, row) in enumerate(df.iterrows()):
        frame_data = []
        for i, gd in enumerate(gauge_defs):
            val = row[gd['key']]
            bar_color = get_gauge_color(val, gd['steps'])
            frame_data.append(go.Indicator(
                value=val,
                gauge={'bar': {'color': bar_color}},
            ))
        frames.append(go.Frame(data=frame_data, name=months_all[idx]))

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

      gd.on('plotly_click', function(data) {{
        const popup = document.getElementById('phase-popup');
        const content = document.getElementById('phase-popup-content');
        if (data.points.length === 0) return;
        const pt = data.points[0];
        if (pt.x === undefined) return;
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
