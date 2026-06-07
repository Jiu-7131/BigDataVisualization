#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图5: 行业相关性网络图"""

import numpy as np
import networkx as nx
from scipy.spatial import ConvexHull
import plotly.graph_objects as go

from .common import save
from config import TEXT_PRIMARY, TEXT_SECOND, BG_PLOT


def generate(data):
    df_corr = data['ind_corr'].copy()
    df_m = data['ind_m'].copy()

    latest_m = df_m[df_m['month'] == df_m['month'].max()]
    all_inds = sorted(latest_m['industry'].unique())
    node_info = {}
    for _, r in latest_m.iterrows():
        node_info[r['industry']] = {'ret': r['monthly_ret'], 'mv': r['total_mv'] / 1e8}

    dates = sorted(df_corr['window_end_date'].unique())
    latest_date = dates[-1]

    # 最新窗口边数据
    dc = df_corr[df_corr['window_end_date'] == latest_date]
    edges = dc[dc['correlation'] > 0.4].copy()
    if len(edges) < 20:
        edges = dc.nlargest(150, 'correlation')

    # 建图
    G = nx.Graph()
    for ind in all_inds:
        G.add_node(ind)
    for _, r in edges.iterrows():
        G.add_edge(r['industry_a'], r['industry_b'], weight=abs(r['correlation']), corr=r['correlation'])

    # 布局
    pos = nx.spring_layout(G, k=2.2, seed=42, iterations=100)
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    s = max(max(xs) - min(xs), max(ys) - min(ys), 0.1) / 2.0
    for n in pos:
        pos[n] = (pos[n][0] / s, pos[n][1] / s)

    # 节点属性
    mv_arr = np.array([node_info[n]['mv'] for n in all_inds])
    mv_min, mv_max = mv_arr.min(), mv_arr.max()
    node_sizes = 8 + 32 * (mv_arr - mv_min) / (mv_max - mv_min + 0.01)
    ret_vals = [node_info[n]['ret'] for n in all_inds]
    rmax = max(abs(v) for v in ret_vals) or 0.01

    fig = go.Figure()

    # ---- 群落凸包 ----
    try:
        from networkx.algorithms.community import greedy_modularity_communities
        comms = list(greedy_modularity_communities(G))
    except Exception:
        comms = [set(G.nodes())]
    comm_colors = ['#4fc3f7', '#ef5350', '#66bb6a', '#ffb74d', '#ab47bc']
    for ci, cset in enumerate(comms):
        pts = [pos[n] for n in cset if n in pos]
        if len(pts) >= 3:
            try:
                hull = ConvexHull(np.array(pts))
                hx = [pts[i][0] for i in hull.vertices] + [pts[hull.vertices[0]][0]]
                hy = [pts[i][1] for i in hull.vertices] + [pts[hull.vertices[0]][1]]
                rgb = tuple(int(comm_colors[ci % 5].lstrip('#')[j:j+2], 16) for j in (0, 2, 4))
                fig.add_trace(go.Scatter(x=hx, y=hy, mode='lines', fill='toself',
                    fillcolor=f'rgba{rgb + (0.05,)}',
                    line=dict(color=f'rgba{rgb + (0.25,)}', width=1, dash='dash'),
                    name=f'群落{ci+1}', showlegend=True, hoverinfo='skip'))
            except Exception:
                pass

    # ---- 边: 正蓝负红, 3 组 ----
    edge_data = {'pos_s': ([], []), 'pos_w': ([], []), 'neg': ([], [])}
    for u, v, d in G.edges(data=True):
        x0, y0 = pos[u]; x1, y1 = pos[v]
        corr = d.get('corr', d['weight'])
        key = 'neg' if corr < 0 else ('pos_s' if abs(corr) > 0.6 else 'pos_w')
        edge_data[key][0].extend([x0, x1, None])
        edge_data[key][1].extend([y0, y1, None])
    edge_style = {'pos_s': {'w': 2.8, 'c': 'rgba(80,170,240,0.5)'},
                  'pos_w': {'w': 1.0, 'c': 'rgba(120,195,245,0.3)'},
                  'neg': {'w': 1.8, 'c': 'rgba(230,100,100,0.45)'}}
    for key, (ex, ey) in edge_data.items():
        if ex:
            fig.add_trace(go.Scatter(x=ex, y=ey, mode='lines',
                line=dict(width=edge_style[key]['w'], color=edge_style[key]['c']),
                hoverinfo='none', showlegend=False))

    # ---- 图例 ----
    for label, color, mode in [('月收益率 ↑', '#ef5350', 'markers'),
                                ('月收益率 ↓', '#66bb6a', 'markers'),
                                ('正相关(蓝)', 'rgba(80,170,240,0.6)', 'lines'),
                                ('负相关(红)', 'rgba(230,100,100,0.6)', 'lines')]:
        kw = dict(mode=mode, showlegend=True, hoverinfo='skip')
        if mode == 'markers':
            kw['marker'] = dict(size=11, color=color, symbol='circle')
            kw['x'] = kw['y'] = [None]
        else:
            kw['line'] = dict(width=3, color=color)
            kw['x'] = kw['y'] = [None]
        fig.add_trace(go.Scatter(**kw))

    # ---- 节点 ----
    fig.add_trace(go.Scatter(
        x=[pos[n][0] for n in all_inds],
        y=[pos[n][1] for n in all_inds],
        mode='markers+text',
        text=all_inds,
        textposition='bottom center',
        textfont=dict(size=9, color=TEXT_PRIMARY),
        marker=dict(
            size=node_sizes,
            color=[f'rgba({int(200+55*min(1,v/rmax))},{int(80-50*min(1,v/rmax))},{int(80-50*min(1,v/rmax))},0.9)' if v >= 0
                   else f'rgba({int(80-50*min(1,abs(v)/rmax))},{int(200-50*min(1,abs(v)/rmax))},{int(80-50*min(1,abs(v)/rmax))},0.9)'
                   for v in ret_vals],
            line=dict(width=1.5, color='rgba(255,255,255,0.2)'),
        ),
        customdata=list(zip(all_inds, [f'{r:.1%}' for r in ret_vals],
                           [f'{m:.0f}亿' for m in mv_arr],
                           [str(G.degree(n)) for n in all_inds])),
        hovertemplate='<b>%{customdata[0]}</b><br>收益率: %{customdata[1]}<br>市值: %{customdata[2]}<br>连接度: %{customdata[3]}<extra></extra>',
    ))

    # ---- Layout ----
    fig.update_layout(height=750,
        title=dict(text=f'行业相关性网络图 ({latest_date.strftime("%Y-%m-%d")})',
                   font=dict(size=18, color='#fff'), x=0.5),
        paper_bgcolor='#0f1923', plot_bgcolor='#1a2332',
        font=dict(color=TEXT_PRIMARY), margin=dict(l=20, r=30, t=60, b=50),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-2.2, 2.2]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-2.2, 2.2]),
        legend=dict(font=dict(color=TEXT_SECOND, size=9), bgcolor='rgba(0,0,0,0.3)',
                    x=0.98, y=0.98, xanchor='right', yanchor='top'),
        hovermode='closest')

    fig.add_annotation(
        x=0.5, y=-0.03,
        text=f'<span style="font-size:10px;color:{TEXT_SECOND}">节点=行业(红涨绿跌,大小=市值)  |  蓝线=正相关 红线=负相关 线粗=强度  |  群落虚线框  |  选行业高亮关联</span>',
        xref='paper', yref='paper', showarrow=False,
    )

    # ---- 行业选择注入 JS ----
    import json
    edge_list = json.dumps([[u, v, d.get('corr', d['weight'])] for u, v, d in G.edges(data=True)], ensure_ascii=False)
    inds_json = json.dumps(all_inds, ensure_ascii=False)
    hc = len(comms)
    # 使用非 f-string 避免 JS 花括号冲突
    js_code = """
    <script>
    (function() {
        var allInds = INDSPLACEHOLDER;
        var allEdges = EDGESPLACEHOLDER;
        var MAX_SEL = 5, hc = HULLCOUNT, nodeIdx = hc + 7;
        var selected = [];

        function getVisible(sel) {
            if (!sel.length) return null;
            var s = new Set(sel), r = new Set(sel);
            var cand = [];
            allEdges.forEach(function(e) {
                if (s.has(e[0]) && !s.has(e[1])) cand.push({n: e[1], w: e[2]});
                if (s.has(e[1]) && !s.has(e[0])) cand.push({n: e[0], w: e[2]});
            });
            cand.sort(function(a,b){return b.w-a.w;});
            cand.forEach(function(c){if(r.size<10)r.add(c.n);});
            return Array.from(r);
        }

        function show(indices) {
            var gd = document.querySelector('.plotly-graph-div'); if(!gd) return;
            if(indices && indices.length) {
                var vs = getVisible(indices), vset = new Set(vs);
                var no = allInds.map(function(n){return vset.has(n)?1:0.01;});
                Plotly.restyle(gd, {'marker.opacity':[no],'textfont.opacity':[no]}, [nodeIdx]);
                Plotly.restyle(gd, {'opacity':[0.06]}, Array.from({length:hc+3},function(_,i){return i;}));
            } else {
                Plotly.restyle(gd, {'opacity':[1]}, Array.from({length:hc+8},function(_,i){return i;}));
            }
        }

        var btn = document.createElement('button');
        btn.innerHTML = '选行业';  // 选行业
        btn.style.cssText = 'position:fixed;top:12px;left:14px;z-index:999;padding:6px 14px;border-radius:6px;border:1px solid rgba(255,255,255,0.12);background:rgba(26,35,50,0.9);color:#d1d4dc;font-size:12px;cursor:pointer;font-family:Outfit,sans-serif;';
        btn.onclick = function(){panel.style.display=panel.style.display==='none'?'flex':'none';if(panel.style.display!=='none')inp.focus();};
        document.body.appendChild(btn);

        var panel = document.createElement('div');
        panel.style.cssText = 'display:none;position:fixed;top:52px;left:14px;z-index:999;width:280px;max-height:420px;border-radius:10px;border:1px solid rgba(255,255,255,0.1);background:rgba(17,24,39,0.97);color:#d1d4dc;flex-direction:column;overflow:hidden;';
        panel.innerHTML = '<div style="padding:10px 14px 6px;font-size:11px;color:#787b86;border-bottom:1px solid rgba(255,255,255,0.06);">最多选'+MAX_SEL+'个<span id="sc5" style="float:right;">0/'+MAX_SEL+'</span></div>';
        var iw = document.createElement('div'); iw.style.cssText = 'padding:6px 10px;';
        var inp = document.createElement('input');
        inp.type = 'text'; inp.placeholder = '搜索...';
        inp.style.cssText = 'width:100%;padding:6px 10px;border-radius:5px;border:1px solid rgba(255,255,255,0.1);background:rgba(0,0,0,0.3);color:#e0e4eb;font-size:12px;outline:none;';
        iw.appendChild(inp); panel.appendChild(iw);
        var lw = document.createElement('div');
        lw.style.cssText = 'overflow-y:auto;flex:1;padding:2px 0;';
        lw.onclick = function(e) {
            var item = e.target.closest('[data-idx]'); if(!item) return;
            var idx = parseInt(item.dataset.idx), pos = selected.indexOf(idx);
            if(pos>=0) selected.splice(pos,1); else if(selected.length<MAX_SEL) selected.push(idx);
            rl(); show(selected.length?selected.map(function(i){return allInds[i];}):null);
        };
        function rl(){
            var q=inp.value.toLowerCase();
            document.getElementById('sc5').textContent=selected.length+'/'+MAX_SEL;
            lw.innerHTML=allInds.map(function(n,i){
                if(q&&!n.toLowerCase().includes(q))return'';
                var s=selected.indexOf(i)>=0;
                return '<div data-idx="'+i+'" style="padding:6px 14px;cursor:pointer;font-size:12px;display:flex;align-items:center;gap:8px;'+(s?'background:rgba(79,195,247,0.15);':'')+'">'+
                    '<span style="width:16px;height:16px;border-radius:3px;border:1.5px solid '+(s?'#4fc3f7':'rgba(255,255,255,0.2)')+';display:flex;align-items:center;justify-content:center;flex-shrink:0;">'+(s?'✓':'')+'</span>'+
                    '<span style="color:'+(s?'#fff':'#aaa')+'">'+n+'</span></div>';
            }).join('')||'<div style="padding:12px;color:#555;font-size:11px;text-align:center">无匹配</div>';
        }
        inp.addEventListener('input', rl); panel.appendChild(lw); document.body.appendChild(panel); rl();
    })();
    </script>"""
    inject_js = (js_code.replace('INDSPLACEHOLDER', inds_json)
                       .replace('EDGESPLACEHOLDER', edge_list)
                       .replace('HULLCOUNT', str(hc)))

    save(fig, '05_行业相关性网络图', inject_js=inject_js)
