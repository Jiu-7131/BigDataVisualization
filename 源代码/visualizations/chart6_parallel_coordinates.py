#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图6: 平行坐标图 — 行业多因子暴露，群落着色 + 时间切片 + 行业高亮"""

import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .common import dark_layout, save
from config import BG_DARK, BG_PLOT, TEXT_PRIMARY, TEXT_SECOND, COLORS


# 群落调色板 (与 chart5 一致)
CLUSTER_COLORS = ['#4fc3f7', '#ef5350', '#66bb6a', '#ffb74d', '#ab47bc',
                  '#f48fb1', '#80cbc4', '#ffcc80', '#90a4ae', '#ce93d8']


def _build_cluster_colorscale(n_clusters):
    """构建离散型群落 colorscale"""
    if n_clusters <= 1:
        return 'RdBu_r'
    cs = []
    step = 1.0 / n_clusters
    for i in range(n_clusters):
        c = CLUSTER_COLORS[i % len(CLUSTER_COLORS)]
        cs.append([i * step, c])
        cs.append([(i + 1) * step, c])
    return cs


def _build_cluster_map(cluster_df, quarter_str):
    """给定季度，返回 {行业名 → cluster_id} 映射"""
    q_data = cluster_df[cluster_df['quarter'] == quarter_str]
    mapping = {}
    for _, row in q_data.iterrows():
        cid = int(row['cluster_id'])
        for ind in str(row['industry_list']).split('|'):
            mapping[ind.strip()] = cid
    return mapping


def generate(data):
    df = data['ind_q'].copy()
    cluster_df = data.get('ind_cluster')
    if cluster_df is None:
        cluster_df = pd.DataFrame()

    # 因子维度及显示标签（含方向）
    factor_cols = ['cum_ret_z', 'mom_1q_z', 'mom_4q_z', 'ann_vol_z',
                   'med_pe_z', 'med_pb_z', 'total_mv_z', 'avg_turnover_z']
    factor_labels = [
        '收益率 ↑', '动量 1Q ↑', '动量 4Q ↑', '波动率 ↓',
        'PE 估值 ↓', 'PB 估值 ↓', '总市值 ↑', '换手率 ↑'
    ]

    # 所有季度
    quarters = sorted(df['quarter'].unique())
    q_labels = [str(q)[:7] for q in quarters]

    # 计算因子重要性（各因子 z-score 跨行业标准差，越大越有区分力）
    imp_scores = {}
    for c in factor_cols:
        imp_scores[c] = df.groupby('quarter')[c].std().median()
    imp_total = sum(imp_scores.values()) or 1

    # 为每个季度预构建帧
    n_clusters_global = 1
    frames = []
    first_frame_data = None
    latest_q = quarters[-1]

    for qi, q in enumerate(quarters):
        q_str = str(q)[:7]
        df_q = df[df['quarter'] == q].dropna(
            subset=['cum_ret_z', 'ann_vol_z', 'med_pe_z']).copy()
        if len(df_q) < 3:
            continue

        # 赋群落 id
        if not cluster_df.empty and q_str in cluster_df['quarter'].values:
            cl_map = _build_cluster_map(cluster_df, q_str)
            df_q['cluster_id'] = df_q['industry'].map(cl_map).fillna(-1).astype(int)
        else:
            df_q['cluster_id'] = 0
        n_clusters = df_q['cluster_id'].nunique()
        n_clusters_global = max(n_clusters_global, n_clusters)

        dims = []
        for c, lab in zip(factor_cols, factor_labels):
            std_s = imp_scores.get(c, 0) / imp_total
            stars = '★' * max(1, int(std_s * 8 + 1))
            dims.append(dict(
                range=[df_q[c].min(), df_q[c].max()],
                label=f'{lab}  {stars}',
                values=df_q[c].values,
            ))

        trace = go.Parcoords(
            line=dict(
                color=df_q['cluster_id'].values if n_clusters > 1 else df_q['cum_ret_z'].values,
                colorscale=_build_cluster_colorscale(max(n_clusters, 2)),
                cmin=0 if n_clusters > 1 else None,
                cmax=n_clusters - 1 if n_clusters > 1 else None,
                showscale=False,
            ),
            dimensions=dims,
            labelside='bottom',
            labelfont=dict(color=TEXT_PRIMARY, size=10),
            labelangle=0,
        )
        if qi == 0:
            first_frame_data = trace
        frames.append(go.Frame(data=[trace], name=q_str))

    if first_frame_data is None:
        print("    (平行坐标数据不足，跳过)")
        return

    # 最新季度作为初始显示
    latest_str = str(latest_q)[:7]
    df_latest = df[df['quarter'] == latest_q].dropna(
        subset=['cum_ret_z', 'ann_vol_z', 'med_pe_z']).copy()
    if not cluster_df.empty and latest_str in cluster_df['quarter'].values:
        cl_map = _build_cluster_map(cluster_df, latest_str)
        df_latest['cluster_id'] = df_latest['industry'].map(cl_map).fillna(-1).astype(int)
    else:
        df_latest['cluster_id'] = 0
    n_clusters_latest = df_latest['cluster_id'].nunique()

    dims_latest = []
    for c, lab in zip(factor_cols, factor_labels):
        std_s = imp_scores.get(c, 0) / imp_total
        stars = '★' * max(1, int(std_s * 8 + 1))
        dims_latest.append(dict(
            range=[df_latest[c].min(), df_latest[c].max()],
            label=f'{lab}  {stars}',
            values=df_latest[c].values,
        ))

    fig = go.Figure(data=[go.Parcoords(
        line=dict(
            color=df_latest['cluster_id'].values if n_clusters_latest > 1 else df_latest['cum_ret_z'].values,
            colorscale=_build_cluster_colorscale(max(n_clusters_latest, 2)),
            cmin=0 if n_clusters_latest > 1 else None,
            cmax=n_clusters_latest - 1 if n_clusters_latest > 1 else None,
            showscale=False,
        ),
        dimensions=dims_latest,
        labelside='bottom',
        labelfont=dict(color=TEXT_PRIMARY, size=10),
        labelangle=0,
    )])

    dark_layout(fig, height=680,
                title=f'行业多因子暴露平行坐标图 · 按群落着色')
    fig.update_layout(paper_bgcolor=BG_DARK, plot_bgcolor=BG_PLOT)

    # 更新帧
    fig.frames = frames

    # 下拉菜单切换季度
    n_per_row = 6
    buttons = []
    for i, q_str in enumerate(q_labels):
        visible = i == (len(q_labels) - 1)
        buttons.append(dict(
            label=q_str,
            method='animate',
            args=[q_str, dict(mode='immediate', frame=dict(duration=400, redraw=True),
                              transition=dict(duration=300))],
        ))

    # 重新排列按钮：每行 n_per_row 个
    button_rows = [buttons[i:i + n_per_row] for i in range(0, len(buttons), n_per_row)]

    fig.update_layout(
        updatemenus=[dict(
            type='buttons',
            buttons=buttons,
            direction='left',
            pad=dict(r=8, t=8),
            x=0.5, y=-0.02,
            xanchor='center', yanchor='top',
            bgcolor='rgba(26,35,50,0.9)',
            bordercolor='rgba(255,255,255,0.1)',
            font=dict(color=TEXT_PRIMARY, size=10),
            active=len(buttons) - 1,
        )],
    )

    # ---- 群落图例 ----
    if not cluster_df.empty and latest_str in cluster_df['quarter'].values:
        cl_map = _build_cluster_map(cluster_df, latest_str)
        # 按群落分组
        comm_groups = {}
        for ind, cid in cl_map.items():
            comm_groups.setdefault(cid, []).append(ind)
        legend_lines = []
        for cid in sorted(comm_groups.keys()):
            color = CLUSTER_COLORS[cid % len(CLUSTER_COLORS)]
            members = comm_groups[cid][:5]
            legend_lines.append(
                f'<span style="color:{color}">■</span> 群落{cid + 1}: '
                f'{", ".join(members)}{"..." if len(comm_groups[cid]) > 5 else ""}'
            )
        if legend_lines:
            fig.add_annotation(
                x=0.01, y=0.98, xref='paper', yref='paper',
                text='<br>'.join(legend_lines),
                showarrow=False,
                font=dict(size=10, color=TEXT_SECOND),
                bgcolor='rgba(15,25,35,0.85)',
                bordercolor='rgba(255,255,255,0.08)',
                borderwidth=1, borderpad=8,
                align='left',
            )

    # ---- 底部说明 ----
    fig.add_annotation(
        x=0.5, y=-0.08, xref='paper', yref='paper',
        text=(f'<span style="font-size:10px;color:{TEXT_SECOND}">'
              '拖拽坐标轴刷选行业 | ★ 越多 = 因子区分力越强 | 颜色 = 行业群落 | '
              '下拉按钮切换季度</span>'),
        showarrow=False,
    )

    # ---- 行业选择交互 JS ----
    inds_all = sorted(df_latest['industry'].tolist())
    fig_json = json.dumps(fig.to_dict(), ensure_ascii=False, default=str)

    inject_js = f"""
    <script>
    (function() {{
        var allInds = {json.dumps(inds_all, ensure_ascii=False)};
        var figData = {fig_json};
        var selected = null;

        // 获取 parcoords trace 在各 frame 和主图中的索引
        function findPCIndices() {{
            var gd = document.querySelector('.plotly-graph-div');
            if (!gd || !gd._fullData) return {{ main: 0 }};
            var idx = -1;
            for (var i = 0; i < gd._fullData.length; i++) {{
                if (gd._fullData[i].type === 'parcoords') {{ idx = i; break; }}
            }}
            return {{ main: idx >= 0 ? idx : 0 }};
        }}

        function highlightIndustry(indName) {{
            var gd = document.querySelector('.plotly-graph-div');
            if (!gd) return;
            var pcIdx = findPCIndices().main;
            var dims = gd._fullData[pcIdx].dimensions;
            if (!dims || !dims.length) return;

            // 在标签维度中找选中行业
            var labelsDim = dims[0];
            var values = labelsDim.values;
            var targetIdx = values.indexOf(indName);

            // 高亮：缩小 constraintrange 到选中行业附近
            var newRanges = [];
            dims.forEach(function(d, di) {{
                if (targetIdx >= 0) {{
                    var v = d.values[targetIdx];
                    var spread = (d.range[1] - d.range[0]) * 0.02;
                    newRanges.push([v - spread, v + spread]);
                }}
            }});

            if (newRanges.length) {{
                var update = {{}};
                dims.forEach(function(d, di) {{
                    update['dimensions[' + di + '].constraintrange'] = [newRanges[di]];
                }});
                Plotly.restyle(gd, update, [pcIdx]);
            }}
        }}

        function resetHighlight() {{
            var gd = document.querySelector('.plotly-graph-div');
            if (!gd) return;
            var pcIdx = findPCIndices().main;
            var dims = gd._fullData[pcIdx].dimensions;
            var update = {{}};
            dims.forEach(function(d, di) {{
                update['dimensions[' + di + '].constraintrange'] = null;
            }});
            Plotly.restyle(gd, update, [pcIdx]);
        }}

        // 行业选择按钮
        var selPanel = document.createElement('div');
        selPanel.style.cssText = 'position:fixed;top:10px;left:10px;z-index:999;';
        var sel = document.createElement('select');
        sel.style.cssText = 'padding:6px 10px;border-radius:6px;border:1px solid rgba(255,255,255,0.12);background:rgba(26,35,50,0.95);color:#d1d4dc;font-size:12px;font-family:Outfit,sans-serif;cursor:pointer;max-width:180px;';
        sel.innerHTML = '<option value="">全部行业</option>' +
            allInds.map(function(n) {{ return '<option value="' + n + '">' + n + '</option>'; }}).join('');
        sel.onchange = function() {{
            if (this.value) highlightIndustry(this.value); else resetHighlight();
        }};
        selPanel.appendChild(sel);
        document.body.appendChild(selPanel);
    }})();
    </script>
    """

    save(fig, '06_平行坐标图', inject_js=inject_js)
