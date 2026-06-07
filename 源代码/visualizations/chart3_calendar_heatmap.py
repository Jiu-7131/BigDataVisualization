#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图3: 日历热力图 — 行业月度收益率排名分位（滚轮翻页）"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .common import dark_layout, save
from config import TEXT_PRIMARY, TEXT_SECOND, BG_PLOT


def _calc_rank(z_data):
    arr = np.array(z_data)
    ranks = np.zeros_like(arr)
    for j in range(arr.shape[1]):
        col = arr[:, j]
        valid = ~np.isnan(col)
        if valid.sum() > 0:
            r = pd.Series(col[valid]).rank(pct=True)
            ranks[valid, j] = r.values
        ranks[~valid, j] = np.nan
    return ranks


def generate(data):
    df = data['ind_m'].copy()
    start_date = pd.Timestamp('2022-01-01')
    end_date = pd.Timestamp('2025-12-01')
    df = df[(df['month'] >= start_date) & (df['month'] <= end_date)].copy()
    industries_raw = sorted(df['industry'].unique())
    months = sorted(df['month'].unique())
    month_labels = [m.strftime('%Y-%m') for m in months]
    n_months = len(months)

    # 行业聚类排序
    ret_pivot = df.pivot_table(index='industry', columns='month', values='monthly_ret')
    corr = ret_pivot.T.corr()
    from scipy.cluster.hierarchy import linkage, leaves_list
    try:
        order = leaves_list(linkage(corr, method='average'))
        industries = [ret_pivot.index[i] for i in order]
    except Exception:
        industries = industries_raw

    n_inds = len(industries)

    # 构建矩阵
    z_data = []
    text_data = []
    for ind in industries:
        row_vals, row_text = [], []
        for m in months:
            sub = df[(df['industry'] == ind) & (df['month'] == m)]['monthly_ret']
            v = sub.iloc[0] if len(sub) > 0 else np.nan
            row_vals.append(v)
            row_text.append(f'{v:.1%}' if not np.isnan(v) else '')
        z_data.append(row_vals)
        text_data.append(row_text)

    rank_data = _calc_rank(z_data)

    # 着色
    custom_colorscale = [
        [0.0, '#1a237e'], [0.15, '#283593'],
        [0.35, '#1a2332'], [0.50, '#1a2332'],
        [0.65, '#b71c1c'], [0.85, '#e53935'], [1.0, '#ff5252'],
    ]

    # ================================================================
    #  Figure — 使用数值坐标 + 自定义 tick 标签
    # ================================================================
    fig = go.Figure()

    fig.add_trace(go.Heatmap(
        z=rank_data,
        x=list(range(n_months)),
        y=list(range(n_inds)),
        colorscale=custom_colorscale, zmin=0, zmax=1,
        text=text_data, texttemplate='%{text}',
        hovertemplate='<b>%{y}</b> | %{x}<br>月收益: %{text}<br>排名分位: %{z:.0%}<extra></extra>',
        textfont={"size": 11, "color": TEXT_PRIMARY},
        colorbar=dict(
            title='排名分位', title_font=dict(color=TEXT_SECOND, size=11),
            tickfont=dict(color=TEXT_SECOND, size=10),
            tickvals=[0, 0.25, 0.5, 0.75, 1],
            ticktext=['最差', '较差', '中位', '较好', '最好'],
            thickness=14, outlinewidth=0,
        ),
        xgap=1.5, ygap=1.5,
    ))

    # ================================================================
    #  Layout
    # ================================================================
    fig.update_layout(
        height=800,
        title=dict(text='行业月度收益率日历热力图',
                   font=dict(size=20, color='#fff'), x=0.5),
        paper_bgcolor='#0a0e17',
        plot_bgcolor=BG_PLOT,
        font=dict(color=TEXT_PRIMARY),
        margin=dict(l=20, r=30, t=60, b=30),
        yaxis=dict(
            title='',
            tickfont=dict(size=11, color=TEXT_SECOND),
            tickvals=list(range(n_inds)),
            ticktext=industries,
            range=[-0.5, 7.5],
            gridcolor='rgba(255,255,255,0.05)',
        ),
        xaxis=dict(
            title='', side='top', tickangle=-45,
            tickfont=dict(size=10, color=TEXT_SECOND),
            tickvals=list(range(n_months)),
            ticktext=month_labels,
            range=[-0.5, 11.5],
            nticks=12,
            gridcolor='rgba(255,255,255,0.05)',
        ),
    )

    fig.add_annotation(
        x=0.5, y=-0.02,
        text=f'<span style="font-size:10px;color:{TEXT_SECOND}">颜色=月度排名分位  |  红=跑赢 蓝=跑输 深色=中位  |  滚轮上下翻行业 · Shift+滚轮左右翻月份</span>',
        xref='paper', yref='paper', showarrow=False,
    )

    # ================================================================
    #  JS: 滚轮翻页
    # ================================================================
    inject_js = f'''
    <script>
    (function() {{
        // ================================================================
        //  Data
        // ================================================================
        var ALL_INDS = {str(industries)};
        var ALL_MONS = {str(month_labels)};
        var ALL_Z = {str(rank_data.tolist())};
        var ALL_TEXT = {str(text_data)};
        var nInds = ALL_INDS.length, nMons = ALL_MONS.length;

        // ================================================================
        //  Heatmap update (restyle — preserves layout/theme)
        // ================================================================
        function renderHeatmap(indices) {{
            var sel = indices || ALL_INDS.map(function(_, i) {{ return i; }});
            var rows = sel.length;
            var z = [], txt = [];
            for (var r = 0; r < rows; r++) {{
                z.push(ALL_Z[sel[r]]);
                txt.push(ALL_TEXT[sel[r]]);
            }}
            // Use numeric y coords + ticktext for labels
            var yNum = [];
            for (var r = 0; r < rows; r++) yNum.push(r);
            Plotly.restyle(gd, {{
                'z': [z], 'y': [yNum], 'text': [txt],
            }}).then(function() {{
                // 确保 y 轴范围在整数边界，行完整显示
                var yEnd = Math.min(rows, 8);
                var yRange = [-0.5, yEnd - 0.5];
                // 更新滚动变量
                rowPage = yEnd;
                y0 = 0; x0 = 0;
                Plotly.relayout(gd, {{
                    'yaxis.tickvals': yNum,
                    'yaxis.ticktext': sel.map(function(i) {{ return ALL_INDS[i]; }}),
                    'yaxis.range': yRange,
                    'xaxis.range': [-0.5, 11.5],
                }});
            }});
        }}

        // ================================================================
        //  Wheel navigation
        // ================================================================
        var rowPage = 8, colPage = 12;
        var y0 = 0, x0 = 0;
        var gd = document.querySelector('.plotly-graph-div');
        if (!gd) return;
        function update() {{
            Plotly.relayout(gd, {{
                'yaxis.range': [y0 - 0.5, y0 + rowPage - 0.5],
                'xaxis.range': [x0 - 0.5, x0 + colPage - 0.5],
            }});
        }}
        gd.addEventListener('wheel', function(e) {{
            if (!e.target.closest('.plotly')) return;
            e.preventDefault();
            if (e.ctrlKey) {{
                var delta = e.deltaY > 0 ? 2 : -2;
                var curRows = gd._fullData && gd._fullData[0] ? gd._fullData[0].z.length : nInds;
                rowPage = Math.max(4, Math.min(curRows, rowPage + delta));
                y0 = Math.min(y0, curRows - rowPage);
                update();
            }} else if (e.shiftKey) {{
                x0 = Math.max(0, Math.min(nMons - colPage, x0 + (e.deltaY > 0 ? 3 : -3)));
                update();
            }} else {{
                var curRows = gd._fullData && gd._fullData[0] ? gd._fullData[0].z.length : nInds;
                y0 = Math.max(0, Math.min(curRows - rowPage, y0 + (e.deltaY > 0 ? 3 : -3)));
                update();
            }}
        }}, {{passive: false}});

        // ================================================================
        //  Industry selector
        // ================================================================
        var selected = [];
        var MAX_SEL = 10;

        // Add search button
        var btn = document.createElement('button');
        btn.innerHTML = '&#128269; 选行业';
        btn.style.cssText = 'position:fixed;top:12px;left:14px;z-index:999;padding:6px 14px;border-radius:6px;border:1px solid rgba(255,255,255,0.12);background:rgba(26,35,50,0.9);color:#d1d4dc;font-size:12px;cursor:pointer;font-family:Outfit,sans-serif;backdrop-filter:blur(8px);';
        btn.onclick = function() {{
            panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
            if (panel.style.display !== 'none') inp.focus();
        }};
        document.body.appendChild(btn);

        // Build panel
        var panel = document.createElement('div');
        panel.style.cssText = 'display:none;position:fixed;top:52px;left:14px;z-index:999;width:280px;max-height:420px;border-radius:10px;border:1px solid rgba(255,255,255,0.1);background:rgba(17,24,39,0.97);color:#d1d4dc;flex-direction:column;overflow:hidden;backdrop-filter:blur(12px);box-shadow:0 8px 32px rgba(0,0,0,0.5);';
        panel.innerHTML = '<div style="padding:10px 14px 6px;font-size:11px;color:#787b86;border-bottom:1px solid rgba(255,255,255,0.06);">选择行业（最多' + MAX_SEL + '个）<span id="selCount" style="float:right;">0/' + MAX_SEL + '</span></div>';
        var inpWrap = document.createElement('div');
        inpWrap.style.cssText = 'padding:6px 10px;';
        var inp = document.createElement('input');
        inp.type = 'text';
        inp.placeholder = '输入行业名称搜索...';
        inp.style.cssText = 'width:100%;padding:6px 10px;border-radius:5px;border:1px solid rgba(255,255,255,0.1);background:rgba(0,0,0,0.3);color:#e0e4eb;font-size:12px;outline:none;';
        inpWrap.appendChild(inp);

        var listWrap = document.createElement('div');
        listWrap.style.cssText = 'overflow-y:auto;flex:1;padding:2px 0;';
        listWrap.onclick = function(e) {{
            var item = e.target.closest('[data-idx]');
            if (!item) return;
            var idx = parseInt(item.dataset.idx);
            var pos = selected.indexOf(idx);
            if (pos >= 0) {{ selected.splice(pos, 1); }}
            else if (selected.length < MAX_SEL) {{ selected.push(idx); }}
            refreshList();
            renderHeatmap(selected.length ? selected : null);
        }};

        function refreshList() {{
            var q = inp.value.toLowerCase();
            document.getElementById('selCount').textContent = selected.length + '/' + MAX_SEL;
            var html = '';
            for (var i = 0; i < nInds; i++) {{
                if (q && !ALL_INDS[i].toLowerCase().includes(q)) continue;
                var isSel = selected.indexOf(i) >= 0;
                html += '<div data-idx="' + i + '" style="padding:6px 14px;cursor:pointer;font-size:12px;display:flex;align-items:center;gap:8px;transition:background 0.1s;' + (isSel ? 'background:rgba(79,195,247,0.15);' : '') + '">' +
                    '<span style="width:16px;height:16px;border-radius:3px;border:1.5px solid ' + (isSel ? '#4fc3f7' : 'rgba(255,255,255,0.2)') + ';display:flex;align-items:center;justify-content:center;flex-shrink:0;">' + (isSel ? '&#10003;' : '') + '</span>' +
                    '<span style="color:' + (isSel ? '#fff' : '#aaa') + '">' + ALL_INDS[i] + '</span></div>';
            }}
            listWrap.innerHTML = html || '<div style="padding:12px;color:#555;font-size:11px;text-align:center">无匹配行业</div>';
        }}

        inp.addEventListener('input', refreshList);
        panel.appendChild(inpWrap);
        panel.appendChild(listWrap);
        document.body.appendChild(panel);

        // Init list
        refreshList();
    }})();
    </script>'''

    save(fig, '03_日历热力图', inject_js=inject_js)
