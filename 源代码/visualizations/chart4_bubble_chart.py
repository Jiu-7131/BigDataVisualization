#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图4: 动态气泡图 — 行业风险收益定位与跨周期迁移"""

import pandas as pd
import plotly.graph_objects as go

from .common import save


INDUSTRY_GROUPS = {
    '周期': ['有色金属', '煤炭', '钢铁', '基础化工', '石油石化', '建筑材料',
             '建筑装饰', '机械设备', '电力设备', '环保'],
    '成长': ['计算机', '电子', '通信', '传媒', '国防军工', '医药生物',
             '汽车', '电力设备'],
    '防御': ['食品饮料', '公用事业', '农林牧渔', '银行', '交通运输',
             '房地产', '纺织服饰', '商贸零售', '社会服务'],
}
GROUP_COLORS = {'周期': '#f59e0b', '成长': '#4fc3f7', '防御': '#66bb6a'}


def _get_group(ind):
    for g, members in INDUSTRY_GROUPS.items():
        if ind in members:
            return g
    return '其他'


def generate(data):
    df = data['ind_q'].copy()
    df = df.dropna(subset=['ann_vol', 'cum_ret', 'total_mv'])
    df['total_mv_b'] = df['total_mv'] / 1e8
    df = df.sort_values('quarter_str')
    df['group'] = df['industry'].apply(_get_group)
    df['group_color'] = df['group'].map(GROUP_COLORS).fillna('#888')

    median_vol = df['ann_vol'].median()

    # JS 在浏览器中构建完整图表（含月/季切换、行业选择），此处仅生成空白底图
    fig = go.Figure()
    fig.update_layout(
        height=750,
        title=dict(text='行业风险收益定位与迁移 (动态气泡图)',
                   font=dict(size=18, color='#fff'), x=0.5),
        paper_bgcolor='#0f1923', plot_bgcolor='#1a2332',
        font=dict(color='#d1d4dc'),
        margin=dict(l=50, r=30, t=60, b=60),
    )

    # ================================================================
    #  按月聚合数据 (用于月滑动)
    # ================================================================
    df_m = data['ind_m'].copy()
    df_m = df_m[(df_m['month'] >= pd.Timestamp('2022-01-01')) & (df_m['month'] <= pd.Timestamp('2025-12-01'))].copy()
    df_m = df_m.sort_values(['industry', 'month'])
    # 计算12月滚动累计收益
    df_m['cum_ret'] = df_m.groupby('industry')['monthly_ret'].transform(
        lambda x: x.rolling(12, min_periods=1).sum())
    df_m['total_mv_b'] = df_m['total_mv'] / 1e8
    df_m['ann_vol'] = df_m['monthly_vol'].clip(lower=0)
    df_m['group'] = df_m['industry'].apply(_get_group)
    df_m = df_m.dropna(subset=['cum_ret', 'ann_vol', 'total_mv'])

    # ================================================================
    #  Inject JS: 行业选择（同图3）+ 月/季切换
    # ================================================================
    all_rows = []
    for _, row in df.iterrows():
        all_rows.append({
            'q': row['quarter_str'], 'ind': row['industry'],
            'x': float(row['cum_ret']), 'y': float(row['ann_vol']),
            's': float(row['total_mv_b']), 'g': row['group'],
        })
    # 按月数据
    df_m['month_str'] = df_m['month'].dt.strftime('%Y-%m')
    all_rows_m = []
    for _, row in df_m.iterrows():
        all_rows_m.append({
            'q': row['month_str'], 'ind': row['industry'],
            'x': float(row['cum_ret']), 'y': float(row['ann_vol']),
            's': float(row['total_mv_b']), 'g': row['group'],
        })
    quarters_list = sorted(df['quarter_str'].unique())
    months_list = sorted(df_m['month_str'].unique())
    industries_list = sorted(df['industry'].unique())
    # 合并月/季数据范围
    all_x = list(df['cum_ret']) + list(df_m['cum_ret'])
    all_y = list(df['ann_vol']) + list(df_m['ann_vol'])
    x_min = float(min(all_x) * 1.6)
    x_max = float(max(all_x) * 1.6)
    y_min = float(min(all_y) * 0.6)
    y_max = float(max(all_y) * 1.4)

    import json
    inject_js = f'''
    <script>
    (function() {{
        var dataQ = {json.dumps(all_rows, ensure_ascii=False)};
        var dataM = {json.dumps(all_rows_m, ensure_ascii=False)};
        var quarters = {json.dumps(quarters_list)};
        var months = {json.dumps(months_list)};
        var allInds = {json.dumps(industries_list, ensure_ascii=False)};
        var gColors = {{'周期':'#f59e0b','成长':'#4fc3f7','防御':'#66bb6a'}};
        var medianVol = {float(median_vol)};
        var xRange = [{x_min}, {x_max}];
        var yRange = [{y_min}, {y_max}];

        var gd = document.querySelector('.plotly-graph-div');
        if (!gd) return;

        var currentMode = 'Q';
        function buildFigure(selected, mode) {{
            mode = mode || currentMode;
            currentMode = mode;
            var timeLabels = mode === 'M' ? months : quarters;
            var allData = mode === 'M' ? dataM : dataQ;
            var selSet = new Set(selected && selected.length ? selected : allInds);
            var activeTime = timeLabels[timeLabels.length - 1];

            var groups = ['周期','成长','防御'];
            var traces = [];
            // Base traces: only show active time period
            groups.forEach(function(g) {{
                var pts = allData.filter(function(d) {{ return d.ind && selSet.has(d.ind) && d.g === g && d.q === activeTime; }});
                traces.push({{
                    type: 'scatter', mode: 'markers',
                    x: pts.map(function(d){{return d.x;}}),
                    y: pts.map(function(d){{return d.y;}}),
                    marker: {{
                        size: pts.map(function(d){{return Math.max(d.s * 3, 12);}}),
                        color: gColors[g],
                        line: {{width: 1, color: 'rgba(255,255,255,0.3)'}},
                    }},
                    name: g,
                    customdata: pts.map(function(d){{return [d.ind, d.q];}}),
                    hovertemplate: '<b>%{{customdata[0]}}</b><br>%{{customdata[1]}}<br>收益率: %{{x:.1%}}<br>波动率: %{{y:.1%}}<extra>%{{name}}</extra>',
                }});
            }});

            // Build frames
            var frames = [];
            timeLabels.forEach(function(t) {{
                var fTraces = [];
                groups.forEach(function(g) {{
                    var pts = allData.filter(function(d) {{ return d.q === t && d.g === g && selSet.has(d.ind); }});
                    fTraces.push({{
                        type: 'scatter', mode: 'markers',
                        x: pts.map(function(d){{return d.x;}}),
                        y: pts.map(function(d){{return d.y;}}),
                        marker: {{
                            size: pts.map(function(d){{return Math.max(d.s * 3, 12);}}),
                            color: gColors[g],
                            line: {{width: 1, color: 'rgba(255,255,255,0.3)'}},
                        }},
                        name: g,
                        customdata: pts.map(function(d){{return [d.ind, d.q];}}),
                        hovertemplate: '<b>%{{customdata[0]}}</b><br>%{{customdata[1]}}<br>收益率: %{{x:.1%}}<br>波动率: %{{y:.1%}}<extra>%{{name}}</extra>',
                    }});
                }});
                frames.push({{data: fTraces, name: t}});
            }});

            var nTimes = timeLabels.length;
            var sliderPrefix = mode === 'M' ? '月份: ' : '季度: ';
            var xTitle = mode === 'M' ? '12月滚动累计收益率' : '季度累计收益率';

            var layout = {{
                title: {{text: '行业风险收益定位与迁移 (动态气泡图)', font: {{size: 18, color: '#fff'}}, x: 0.5}},
                paper_bgcolor: '#0f1923', plot_bgcolor: '#1a2332',
                font: {{color: '#d1d4dc'}},
                height: 750,
                margin: {{l: 50, r: 30, t: 60, b: 60}},
                hovermode: 'closest',
                xaxis: {{title: xTitle, tickformat: '.0%', range: xRange,
                         gridcolor: 'rgba(255,255,255,0.06)', tickfont: {{size: 11, color: '#787b86'}}}},
                yaxis: {{title: '年化波动率', tickformat: '.0%', range: yRange,
                         gridcolor: 'rgba(255,255,255,0.06)', tickfont: {{size: 11, color: '#787b86'}}}},
                legend: {{font: {{size: 11, color: '#787b86'}}, bgcolor: 'rgba(0,0,0,0)', x: 0.98, y: 0.98, xanchor: 'right', yanchor: 'top'}},
                updatemenus: [{{type: 'buttons', direction: 'left', x: 0.5, y: -0.04, xanchor: 'center', yanchor: 'top',
                    buttons: [
                        {{label: '▶ 播放', method: 'animate', args: [null, {{frame: {{duration: 400, redraw: true}}, fromcurrent: true, mode: 'immediate', transition: {{duration: 150}}}}]}},
                        {{label: '⏸ 暂停', method: 'animate', args: [[null], {{frame: {{duration: 0, redraw: false}}, mode: 'immediate', transition: {{duration: 0}}}}]}},
                    ],
                    font: {{color: '#d1d4dc', size: 11}}, bgcolor: '#1a2332', bordercolor: 'rgba(255,255,255,0.12)', borderwidth: 1,
                }}],
                sliders: [{{
                    active: nTimes - 1,
                    currentvalue: {{prefix: sliderPrefix, font: {{color: '#d1d4dc', size: 12}}}},
                    pad: {{t: 10}},
                    steps: timeLabels.map(function(t, i) {{
                        return {{label: t, method: 'animate', args: [[t], {{frame: {{duration: 250, redraw: true}}, mode: 'immediate', transition: {{duration: 100}}}}]}};
                    }}),
                    font: {{color: '#787b86', size: 9}}, bgcolor: '#1a2332', bordercolor: 'rgba(255,255,255,0.12)',
                }}],
                shapes: [
                    {{type: 'line', x0: 0, x1: 1, y0: medianVol, y1: medianVol, xref: 'x', yref: 'y',
                      line: {{color: 'rgba(255,255,255,0.15)', width: 1, dash: 'dash'}}}},
                    {{type: 'line', x0: 0, x1: 0, y0: yRange[0], y1: yRange[1], xref: 'x', yref: 'y',
                      line: {{color: 'rgba(255,255,255,0.15)', width: 1, dash: 'dash'}}}},
                ],
                annotations: [
                    {{x: xRange[1]*0.6, y: medianVol + (yRange[1] - medianVol)*0.5, text: '进攻区', showarrow: false, font: {{color: '#ef5350', size: 16}}, opacity: 0.6}},
                    {{x: xRange[0]*0.6, y: medianVol + (yRange[1] - medianVol)*0.5, text: '理想区', showarrow: false, font: {{color: '#66bb6a', size: 16}}, opacity: 0.6}},
                    {{x: xRange[0]*0.6, y: medianVol - (medianVol - yRange[0])*0.25, text: '防御区', showarrow: false, font: {{color: '#4fc3f7', size: 16}}, opacity: 0.6}},
                    {{x: xRange[1]*0.6, y: medianVol - (medianVol - yRange[0])*0.25, text: '陷阱区', showarrow: false, font: {{color: '#ffb74d', size: 16}}, opacity: 0.6}},
                    {{x: 0.5, y: -0.04, text: '<span style="font-size:10px;color:#787b86">气泡大小=市值  |  左上角切换月/季、选行业</span>', xref: 'paper', yref: 'paper', showarrow: false}},
                ],
            }};

            Plotly.react(gd, traces, layout, {{responsive: true}}).then(function() {{
                Plotly.addFrames(gd, frames);
            }});
        }}

        // ---- 行业选择面板 ----
        var MAX_SEL = 10;
        var selected = [];

        var tb = document.createElement('div');
        tb.style.cssText = 'position:fixed;top:12px;left:14px;z-index:999;display:flex;gap:6px;';
        var btn = document.createElement('button');
        btn.innerHTML = '&#128269; 选行业';
        btn.style.cssText = 'padding:6px 14px;border-radius:6px;border:1px solid rgba(255,255,255,0.12);background:rgba(26,35,50,0.9);color:#d1d4dc;font-size:12px;cursor:pointer;font-family:Outfit,sans-serif;backdrop-filter:blur(8px);';
        btn.onclick = function() {{ panel.style.display = panel.style.display === 'none' ? 'flex' : 'none'; if (panel.style.display !== 'none') inp.focus(); }};
        tb.appendChild(btn);

        var toggleBtn = document.createElement('button');
        toggleBtn.innerHTML = '月';
        toggleBtn.style.cssText = 'padding:6px 12px;border-radius:6px;border:1px solid rgba(255,255,255,0.12);background:rgba(79,195,247,0.25);color:#4fc3f7;font-size:12px;cursor:pointer;font-family:Outfit,sans-serif;';
        toggleBtn.onclick = function() {{
            var newMode = currentMode === 'Q' ? 'M' : 'Q';
            toggleBtn.innerHTML = newMode === 'Q' ? '月' : '季';
            toggleBtn.style.cssText = 'padding:6px 12px;border-radius:6px;border:1px solid rgba(255,255,255,0.12);background:' + (newMode === 'Q' ? 'rgba(79,195,247,0.25)' : 'rgba(255,255,255,0.06)') + ';color:' + (newMode === 'Q' ? '#4fc3f7' : '#787b86') + ';font-size:12px;cursor:pointer;font-family:Outfit,sans-serif;';
            var sel = selected.length ? selected.map(function(i){{return allInds[i];}}) : null;
            buildFigure(sel, newMode);
        }};
        tb.appendChild(toggleBtn);
        document.body.appendChild(tb);

        var panel = document.createElement('div');
        panel.style.cssText = 'display:none;position:fixed;top:52px;left:14px;z-index:999;width:280px;max-height:420px;border-radius:10px;border:1px solid rgba(255,255,255,0.1);background:rgba(17,24,39,0.97);color:#d1d4dc;flex-direction:column;overflow:hidden;backdrop-filter:blur(12px);box-shadow:0 8px 32px rgba(0,0,0,0.5);';
        panel.innerHTML = '<div style="padding:10px 14px 6px;font-size:11px;color:#787b86;border-bottom:1px solid rgba(255,255,255,0.06);">选择行业（最多' + MAX_SEL + '个）<span id="selCount4" style="float:right;">0/' + MAX_SEL + '</span></div>';
        var inpWrap = document.createElement('div'); inpWrap.style.cssText = 'padding:6px 10px;';
        var inp = document.createElement('input');
        inp.type = 'text'; inp.placeholder = '输入行业名称搜索...';
        inp.style.cssText = 'width:100%;padding:6px 10px;border-radius:5px;border:1px solid rgba(255,255,255,0.1);background:rgba(0,0,0,0.3);color:#e0e4eb;font-size:12px;outline:none;';
        inpWrap.appendChild(inp);
        panel.appendChild(inpWrap);

        var listWrap = document.createElement('div');
        listWrap.style.cssText = 'overflow-y:auto;flex:1;padding:2px 0;';
        listWrap.onclick = function(e) {{
            var item = e.target.closest('[data-idx]');
            if (!item) return;
            var idx = parseInt(item.dataset.idx);
            var pos = selected.indexOf(idx);
            if (pos >= 0) selected.splice(pos, 1);
            else if (selected.length < MAX_SEL) selected.push(idx);
            refreshList4();
            buildFigure(selected.length ? selected.map(function(i){{return allInds[i];}}) : null, currentMode);
        }};
        function refreshList4() {{
            var q = inp.value.toLowerCase();
            document.getElementById('selCount4').textContent = selected.length + '/' + MAX_SEL;
            var html = '';
            for (var i = 0; i < allInds.length; i++) {{
                if (q && !allInds[i].toLowerCase().includes(q)) continue;
                var isSel = selected.indexOf(i) >= 0;
                html += '<div data-idx="' + i + '" style="padding:6px 14px;cursor:pointer;font-size:12px;display:flex;align-items:center;gap:8px;transition:background 0.1s;' + (isSel ? 'background:rgba(79,195,247,0.15);' : '') + '">' +
                    '<span style="width:16px;height:16px;border-radius:3px;border:1.5px solid ' + (isSel ? '#4fc3f7' : 'rgba(255,255,255,0.2)') + ';display:flex;align-items:center;justify-content:center;flex-shrink:0;">' + (isSel ? '&#10003;' : '') + '</span>' +
                    '<span style="color:' + (isSel ? '#fff' : '#aaa') + '">' + allInds[i] + '</span></div>';
            }}
            listWrap.innerHTML = html || '<div style="padding:12px;color:#555;font-size:11px;text-align:center">无匹配行业</div>';
        }}
        inp.addEventListener('input', refreshList4);
        panel.appendChild(listWrap);
        document.body.appendChild(panel);
        refreshList4();
        // 初始加载时直接用 JS 构建，保证月/季切换后布局一致
        setTimeout(function() {{ buildFigure(null, 'Q'); }}, 100);
    }})();
    </script>'''

    save(fig, '04_动态气泡图', inject_js=inject_js)
