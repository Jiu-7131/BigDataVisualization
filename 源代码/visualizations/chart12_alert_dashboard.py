#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图12: 实时监控预警仪表盘 — 3×2 卡片网格 + 状态灯 + 迷你图 + 点击跳转"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .common import dark_layout, save
from config import COLORS, TEXT_PRIMARY, TEXT_SECOND, GRID_COLOR


# 6 张卡片定义: (标题, 数据来源, 跳转目标, 图类)
CARD_DEFS = [
    {
        'id': 'rotation', 'title': '行业轮动信号',
        'chart_link': '03_日历热力图.html',
        'icon': '🔄',
    },
    {
        'id': 'factor_fail', 'title': '因子失效预警',
        'chart_link': '07_因子收益分析.html',
        'icon': '⚠️',
    },
    {
        'id': 'crowding', 'title': '拥挤交易监控',
        'chart_link': '08_因子拥挤度监控.html',
        'icon': '📊',
    },
    {
        'id': 'style_switch', 'title': '风格切换预警',
        'chart_link': '02_风格轮动热力三角图.html',
        'icon': '🔄',
    },
    {
        'id': 'liquidity', 'title': '流动性异常',
        'chart_link': '04_动态气泡图.html',
        'icon': '💧',
    },
    {
        'id': 'tail_risk', 'title': '尾部风险指标',
        'chart_link': '11_压力测试热图.html',
        'icon': '📉',
    },
]


def _compute_card_data(data, card_id):
    """为每张卡计算迷你图数据和当前状态"""
    alert_df = data['alert'].copy()
    alert_df['date'] = pd.to_datetime(alert_df['date'])

    result = {'status': '正常', 'color': COLORS['正常'],
              'summary': '暂无异常', 'dates': [], 'values': [], 'latest_z': 0}

    if card_id == 'rotation':
        # 行业轮动: 收益率偏离的月度计数
        sub = alert_df[alert_df['metric'] == '收益率偏离']
        if len(sub) > 0:
            monthly = sub.groupby(pd.Grouper(key='date', freq='ME')).agg(
                alert_count=('alert_level', lambda x: (x.isin(['警示', '危险'])).sum()),
                mean_abs_z=('z_score', lambda x: x.abs().mean()),
            ).dropna()
            result['dates'] = monthly.index.tolist()
            result['values'] = monthly['alert_count'].tolist()
            latest = sub[sub['date'] == sub['date'].max()]
            result['latest_z'] = latest['z_score'].abs().max()

    elif card_id == 'factor_fail':
        # 因子失效: 从因子收益率判断
        df_fr = data['factor_ret'].copy()
        df_fr['month'] = pd.to_datetime(df_fr['month'])
        # 计算因子收益率滚动3月均值的方向
        df_fr = df_fr.dropna(subset=['Rm', 'SMB', 'HML', 'MOM'])
        if len(df_fr) >= 3:
            df_fr['factor_momentum'] = (df_fr['Rm'] + df_fr['SMB'] + df_fr['HML'] + df_fr['MOM']) / 4
            df_fr['rolling_3m'] = df_fr['factor_momentum'].rolling(3).mean()
            valid = df_fr.dropna(subset=['rolling_3m'])
            result['dates'] = valid['month'].tolist()
            result['values'] = valid['rolling_3m'].tolist()
            result['latest_z'] = valid['rolling_3m'].iloc[-1]
            if result['latest_z'] < -0.03:
                result['status'] = '危险'
            elif result['latest_z'] < -0.01:
                result['status'] = '警示'

    elif card_id == 'crowding':
        # 拥挤交易: 从 crowding_score 取
        df_c = data['factor_crowd'].copy()
        df_c['month'] = pd.to_datetime(df_c['month'])
        valid = df_c.dropna(subset=['crowding_score'])
        result['dates'] = valid['month'].tolist()
        result['values'] = valid['crowding_score'].tolist()
        latest = valid.iloc[-1]
        result['latest_z'] = latest['crowding_score']
        result['status'] = latest.get('crowding_level', '正常')

    elif card_id == 'style_switch':
        # 风格切换: style drift 强度
        df_s = data['style'].copy()
        df_s['month'] = pd.to_datetime(df_s['month'])
        if 'style_strength' in df_s.columns:
            valid = df_s.dropna(subset=['style_strength'])
            result['dates'] = valid['month'].tolist()
            result['values'] = valid['style_strength'].tolist()
            result['latest_z'] = valid['style_strength'].iloc[-1]
        elif 'size_premium' in df_s.columns and 'value_growth_premium' in df_s.columns:
            # 用 size_premium 和 value_growth_premium 的绝对值之和
            valid = df_s.dropna(subset=['size_premium', 'value_growth_premium'])
            result['dates'] = valid['month'].tolist()
            result['values'] = (valid['size_premium'].abs() + valid['value_growth_premium'].abs()).tolist()
            result['latest_z'] = result['values'][-1] if result['values'] else 0

    elif card_id == 'liquidity':
        # 流动性异常: 成交量异常
        sub = alert_df[alert_df['metric'] == '成交量异常']
        if len(sub) > 0:
            monthly = sub.groupby(pd.Grouper(key='date', freq='ME')).agg(
                alert_count=('alert_level', lambda x: (x.isin(['警示', '危险'])).sum()),
                mean_abs_z=('z_score', lambda x: x.abs().mean()),
            ).dropna()
            result['dates'] = monthly.index.tolist()
            result['values'] = monthly['mean_abs_z'].tolist()
            latest = sub[sub['date'] == sub['date'].max()]
            result['latest_z'] = latest['z_score'].abs().max()

    elif card_id == 'tail_risk':
        # 尾部风险: 行业月收益率的极端值占比
        df_ind = data['ind_m'].copy()
        df_ind['month'] = pd.to_datetime(df_ind['month'])
        # 每月超过 ±2 标准差的行业比例
        monthly_tail = df_ind.groupby('month').agg(
            tail_ratio=('monthly_ret', lambda x: (
                (np.abs((x - x.mean()) / x.std()) > 2).sum() / len(x)
            )),
        ).dropna()
        result['dates'] = monthly_tail.index.tolist()
        result['values'] = (monthly_tail['tail_ratio'] * 100).tolist()
        result['latest_z'] = result['values'][-1] if result['values'] else 0
        if result['latest_z'] > 20:
            result['status'] = '危险'
        elif result['latest_z'] > 12:
            result['status'] = '警示'
        elif result['latest_z'] > 6:
            result['status'] = '关注'

    # 更新颜色和总结
    result['color'] = COLORS.get(result['status'], '#888')
    latest_z = result['latest_z']
    if result['status'] == '危险':
        result['summary'] = f'危险! Z={latest_z:+.2f}'
    elif result['status'] == '警示':
        result['summary'] = f'警戒 Z={latest_z:+.2f}'
    elif result['status'] == '关注':
        result['summary'] = f'关注 Z={latest_z:+.2f}'
    else:
        result['summary'] = f'正常 Z={latest_z:+.2f}'

    return result


def generate(data):
    alert_df = data['alert'].copy()
    if len(alert_df) == 0:
        print('  (预警数据为空，跳过)')
        return

    alert_df['date'] = pd.to_datetime(alert_df['date'])

    # 为每张卡计算数据
    card_data = {}
    for cd in CARD_DEFS:
        card_data[cd['id']] = _compute_card_data(data, cd['id'])

    # 构建 3×2 子图
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=[f'{cd["icon"]} {cd["title"]}' for cd in CARD_DEFS],
        vertical_spacing=0.10,
        horizontal_spacing=0.08,
    )

    # 轴引用名：x, x2, x3, x4, x5, x6（x1 不存在）
    def _xref(idx):
        return 'x' if idx == 0 else f'x{idx+1}'

    def _yref(idx):
        return 'y' if idx == 0 else f'y{idx+1}'

    # 填充每张卡
    for i, cd in enumerate(CARD_DEFS):
        row = i // 2 + 1
        col = i % 2 + 1
        cd_data = card_data[cd['id']]
        xr = _xref(i)
        yr = _yref(i)

        if cd_data['dates'] and cd_data['values']:
            # 迷你折线
            fig.add_trace(go.Scatter(
                x=cd_data['dates'], y=cd_data['values'],
                mode='lines',
                line=dict(color=cd_data['color'], width=1.8),
                fill='tozeroy',
                fillcolor=f'rgba{tuple(int(cd_data["color"].lstrip("#")[j:j+2],16) for j in (0,2,4)) + (0.1,)}',
                hoverinfo='skip',
                showlegend=False,
            ), row=row, col=col)
        else:
            # 无数据占位
            fig.add_annotation(
                x=0.5, y=0.5, xref=f'{xr} domain', yref=f'{yr} domain',
                text='数据不足', showarrow=False,
                font=dict(color=TEXT_SECOND, size=14),
            )

        # 状态标签
        fig.add_annotation(
            x=0.02, y=0.95, xref=f'{xr} domain', yref=f'{yr} domain',
            text=(f'<span style="display:inline-block;width:10px;height:10px;'
                  f'border-radius:50%;background:{cd_data["color"]};margin-right:4px;"></span>'
                  f'<b style="color:{cd_data["color"]};font-size:11px;">{cd_data["status"]}</b>'),
            showarrow=False,
        )

        # 底部总结
        fig.add_annotation(
            x=0.5, y=-0.12, xref=f'{xr} domain', yref=f'{yr} domain',
            text=f'<span style="font-size:10px;color:{TEXT_SECOND}">{cd_data["summary"]}</span>',
            showarrow=False,
        )

    # 整体布局
    dark_layout(fig, height=820,
                title='实时监控预警仪表盘'
                      f'<br><sup style="font-size:10px;color:{TEXT_SECOND}">'
                      f'数据更新至 {str(alert_df["date"].max())[:10]} · 点击卡片跳转详情</sup>')
    fig.update_layout(
        paper_bgcolor='#0f1923', plot_bgcolor='#1a2332',
        margin=dict(l=30, r=30, t=80, b=50),
        showlegend=False,
    )

    # 全局轴样式
    for i in range(1, 7):
        fig.update_xaxes(gridcolor=GRID_COLOR, showticklabels=False, row=(i-1)//2+1, col=(i-1)%2+1)
        fig.update_yaxes(gridcolor=GRID_COLOR, showticklabels=False, row=(i-1)//2+1, col=(i-1)%2+1)

    # ---- 阈值预设按钮 ----
    fig.update_layout(
        updatemenus=[dict(
            type='buttons',
            direction='left',
            x=0.5, y=-0.03,
            xanchor='center', yanchor='top',
            bgcolor='rgba(26,35,50,0.9)',
            bordercolor='rgba(255,255,255,0.1)',
            font=dict(color=TEXT_PRIMARY, size=10),
            buttons=[
                dict(label='保守 (Z>1.5)',
                     method='relayout',
                     args=['title', '实时监控预警仪表盘<br><sup>阈值: 保守模式 (Z>1.5 触发关注)</sup>']),
                dict(label='中等 (Z>2.0)',
                     method='relayout',
                     args=['title', '实时监控预警仪表盘<br><sup>阈值: 中等模式 (Z>2.0 触发关注)</sup>']),
                dict(label='激进 (Z>3.0)',
                     method='relayout',
                     args=['title', '实时监控预警仪表盘<br><sup>阈值: 激进模式 (Z>3.0 触发关注)</sup>']),
            ],
        )],
    )

    # ---- 点击跳转 JS ----
    chart_links_json = {cd['title']: cd['chart_link'] for cd in CARD_DEFS}
    inject_js = f"""
    <script>
    (function() {{
        var links = {chart_links_json.__repr__().replace("'", '"')};
        // 将子图标题映射到链接
        document.querySelectorAll('.subplot-title').forEach(function(el) {{
            el.style.cursor = 'pointer';
            el.style.transition = 'color 0.2s';
            el.addEventListener('mouseenter', function() {{ this.style.color = '#f59e0b'; }});
            el.addEventListener('mouseleave', function() {{ this.style.color = ''; }});
            el.addEventListener('click', function() {{
                var title = this.textContent.replace(/^[^ ]+ /, '').trim();
                var file = links[title];
                if (file) {{
                    if (window.parent && window.parent !== window) {{
                        window.parent.location.href = file;
                    }} else {{
                        window.open(file, '_self');
                    }}
                }}
            }});
        }});

        // 红色卡片闪烁
        var styleEl = document.createElement('style');
        styleEl.textContent = '@keyframes dangerPulse {{ 0%,100%{{box-shadow:0 0 0 rgba(239,83,80,0) inset}} 50%{{box-shadow:0 0 12px rgba(239,83,80,0.4) inset}} }}';
        document.head.appendChild(styleEl);

        // 给危险卡片添加闪烁
        document.querySelectorAll('.subplot-title').forEach(function(el) {{
            var text = el.textContent;
            if (text.includes('危险')) {{
                var parent = el.closest('.subplot');
                if (parent) parent.style.animation = 'dangerPulse 2s ease-in-out infinite';
            }}
        }});
    }})();
    </script>
    """

    save(fig, '12_实时监控预警仪表盘', inject_js=inject_js)
