#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将12张独立图表整合到一个仪表盘页面
侧边栏导航 + 单图全屏 — 一次看一张完整图表，点击切换
"""

import os

CHARTS = [
    ("01_宏观经济周期仪表盘.html", "图1 宏观经济周期仪表盘", "宏观环境层"),
    ("02_风格轮动热力三角图.html", "图2 市场风格轮动热力三角图", "宏观环境层"),
    ("03_日历热力图.html", "图3 行业收益率日历热力图", "行业结构层"),
    ("04_动态气泡图.html", "图4 行业轮动动态气泡图", "行业结构层"),
    ("05_行业相关性网络图.html", "图5 行业相关性网络图", "行业结构层"),
    ("06_平行坐标图.html", "图6 行业多维特征平行坐标图", "因子归因层"),
    ("07_因子收益分析.html", "图7 因子收益贡献瀑布图", "因子归因层"),
    ("08_因子拥挤度监控.html", "图8 因子拥挤度监控仪表", "因子归因层"),
    ("09_牛熊周期箱线图.html", "图9 牛熊周期行业箱线图", "决策支持层"),
    ("10_行业配置桑基图.html", "图10 行业配置决策桑基图", "决策支持层"),
    ("11_压力测试热图.html", "图11 极端情景压力测试热图", "决策支持层"),
    ("12_实时监控预警仪表盘.html", "图12 实时监控预警仪表盘", "决策支持层"),
]

SRC_DIR = "可视化成果"

# 读取当前周期阶段（图1输出 → 传给下游作为全局参数）
CYCLE_PHASE = "未知"
CYCLE_GROWTH_VOTES = 0
CYCLE_INFLATION_VOTES = 0
try:
    import pandas as pd
    macro_path = os.path.join("数据集", "processed", "02_macro", "macro_cycle.csv")
    if not os.path.exists(macro_path):
        macro_path = os.path.join("processed", "02_macro", "macro_cycle.csv")
    macro = pd.read_csv(macro_path)
    if len(macro) > 0:
        latest = macro.iloc[-1]
        CYCLE_PHASE = latest.get('cycle_phase', '未知')
        CYCLE_GROWTH_VOTES = int(latest.get('growth_votes', 0))
        CYCLE_INFLATION_VOTES = int(latest.get('inflation_votes', 0))
except Exception:
    pass

OUTPUT = os.path.join(SRC_DIR, "index.html")

missing = [f for f, _, _ in CHARTS if not os.path.exists(os.path.join(SRC_DIR, f))]
if missing:
    print(f"缺少文件: {missing}")
    print("请先运行 visualizations.py 生成所有图表")
    exit(1)

LAYER_DOTS = {"宏观环境层": "#3498db", "行业结构层": "#2ecc71",
              "因子归因层": "#f39c12", "决策支持层": "#e74c3c"}

CYCLE_COLORS = {
    "复苏期": "#4fc3f7", "过热期": "#ef5350",
    "滞胀期": "#ffb74d", "衰退期": "#5c6bc0",
    "过渡期": "#546e7a", "未知": "#555",
}

html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>股票市场行业轮动与因子收益分析 — 综合仪表盘</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; overflow: hidden; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
    background: #1a1a2e; color: #ccc; display: flex;
  }

  /* ===== 侧边栏 ===== */
  .sidebar {
    width: 280px; min-width: 280px; height: 100vh;
    background: #16162a;
    display: flex; flex-direction: column;
    border-right: 1px solid rgba(255,255,255,0.08);
    user-select: none;
  }
  .sidebar-header {
    padding: 20px 18px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
  }
  .sidebar-header h1 {
    font-size: 16px; font-weight: 700; color: #fff; line-height: 1.4;
  }
  .sidebar-header .subtitle {
    font-size: 10px; color: #666; margin-top: 2px;
  }

  /* 搜索过滤 */
  .sidebar-search {
    padding: 10px 14px;
  }
  .sidebar-search input {
    width: 100%; padding: 7px 10px; border-radius: 6px;
    border: 1px solid rgba(255,255,255,0.1); background: #1e1e38;
    color: #ccc; font-size: 12px; outline: none;
  }
  .sidebar-search input:focus { border-color: #3498db; }

  /* 图表列表 */
  .sidebar-nav {
    flex: 1; overflow-y: auto; padding: 6px 0;
  }
  .sidebar-nav::-webkit-scrollbar { width: 4px; }
  .sidebar-nav::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }

  .layer-group { margin-bottom: 2px; }
  .layer-label {
    padding: 10px 18px 6px; font-size: 10px; text-transform: uppercase;
    letter-spacing: 1px; color: #666; font-weight: 600;
  }
  .chart-item {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 18px; cursor: pointer; transition: background 0.15s;
    border-left: 3px solid transparent; font-size: 13px; color: #aaa;
  }
  .chart-item:hover { background: rgba(255,255,255,0.04); color: #ddd; }
  .chart-item.active {
    background: rgba(255,255,255,0.08); color: #fff;
    border-left-color: #3498db;
  }
  .chart-item .dot {
    width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
  }
  .chart-item .num {
    font-size: 10px; color: #555; width: 18px; flex-shrink: 0;
  }

  /* 快捷键提示 */
  .sidebar-footer {
    padding: 12px 18px; border-top: 1px solid rgba(255,255,255,0.08);
    font-size: 10px; color: #555;
  }
  .sidebar-footer kbd {
    display: inline-block; padding: 1px 5px; border-radius: 3px;
    border: 1px solid #444; background: #222; font-family: inherit;
    margin: 0 2px;
  }

  /* ===== 主视图 ===== */
  .main-view {
    flex: 1; height: 100vh; display: flex; flex-direction: column;
    background: #fff;
  }
  .main-header {
    padding: 10px 20px; background: #fafbfc; border-bottom: 1px solid #eee;
    display: flex; align-items: center; justify-content: space-between;
    flex-shrink: 0;
  }
  .main-header .chart-title { font-size: 15px; font-weight: 600; color: #1a1a2e; }
  .main-header .nav-btns { display: flex; gap: 4px; }
  .main-header button {
    padding: 6px 16px; border: 1px solid #ddd; background: #fff;
    border-radius: 4px; cursor: pointer; font-size: 12px; color: #555;
    transition: all 0.15s;
  }
  .main-header button:hover { background: #f0f0f0; border-color: #bbb; }
  .main-header button:active { background: #e0e0e0; }
  .main-iframe {
    flex: 1; width: 100%; border: none;
  }
  .main-placeholder {
    flex: 1; display: flex; align-items: center; justify-content: center;
    color: #ccc; font-size: 18px;
  }

  /* ===== 响应式: 窄屏时侧边栏折叠 ===== */
  @media (max-width: 768px) {
    .sidebar { width: 60px; min-width: 60px; }
    .sidebar-header h1 { font-size: 13px; }
    .sidebar-header .subtitle, .layer-label, .chart-item span:not(.dot):not(.num),
    .sidebar-search, .sidebar-footer { display: none; }
    .chart-item { padding: 10px 12px; justify-content: center; }
    .chart-item .num { display: inline; width: auto; }
  }
</style>
</head>
<body>

<div class="sidebar">
  <div class="sidebar-header">
    <h1>行业轮动与<br>因子收益分析</h1>
    <div class="subtitle">A股 2022-2026 | 12张图表</div>
  </div>
  <div class="sidebar-search">
    <input type="text" id="search" placeholder="搜索图表..." oninput="filterCharts()">
  </div>
  <div class="sidebar-nav" id="sidebarNav">
"""

# ===== 构建侧边栏列表 =====
LAYERS_ORDER = ["宏观环境层", "行业结构层", "因子归因层", "决策支持层"]
layer_groups = {l: [] for l in LAYERS_ORDER}
for fname, title, layer in CHARTS:
    layer_groups[layer].append((fname, title))

idx = 0
for layer_name in LAYERS_ORDER:
    charts_in_layer = layer_groups[layer_name]
    dot_color = LAYER_DOTS[layer_name]
    html += f'    <div class="layer-group"><div class="layer-label">{layer_name}</div>\n'
    for fname, title in charts_in_layer:
        idx += 1
        html += f"""      <div class="chart-item" data-index="{idx}" data-file="{fname}"
           data-title="{title}" data-layer="{layer_name}"
           onclick="selectChart({idx})">
        <span class="num">{idx}</span>
        <span class="dot" style="background:{dot_color}"></span>
        <span>{title}</span>
      </div>
"""
    html += '    </div>\n'

html += """  </div>
  <div class="sidebar-footer">
    <kbd>&uarr;</kbd><kbd>&darr;</kbd> 切换 &nbsp; <kbd>1</kbd>-<kbd>9</kbd> 快速跳转
  </div>
</div>

<div class="main-view">
  <div class="main-header">
    <span class="chart-title" id="mainTitle">图1 宏观经济周期仪表盘</span>
    <span id="cycleBadge" style="padding:4px 12px;border-radius:12px;
      font-size:11px;font-weight:600;color:#fff;
      background:""" + CYCLE_COLORS.get(CYCLE_PHASE, '#555') + """">当前周期: """ + CYCLE_PHASE + f""" (增长{CYCLE_GROWTH_VOTES}/4 通胀{CYCLE_INFLATION_VOTES}/2)</span>
    <div class="nav-btns">
      <button onclick="prevChart()" title="上一张 (↑)">&larr; 上一张</button>
      <button onclick="nextChart()" title="下一张 (↓)">下一张 &rarr;</button>
    </div>
  </div>
  <iframe class="main-iframe" id="mainIframe"
          src="01_宏观经济周期仪表盘.html"></iframe>
</div>

<script>
  const TOTAL = """ + str(len(CHARTS)) + """;
  let current = 1;

  function selectChart(n) {
    current = n;
    const item = document.querySelector(`.chart-item[data-index="${n}"]`);
    if (!item) return;
    document.getElementById('mainTitle').textContent = item.dataset.title;
    document.getElementById('mainIframe').src = item.dataset.file;
    document.querySelectorAll('.chart-item').forEach(el => el.classList.remove('active'));
    item.classList.add('active');
    item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  function nextChart() { if (current < TOTAL) selectChart(current + 1); }
  function prevChart() { if (current > 1) selectChart(current - 1); }

  function filterCharts() {
    const q = document.getElementById('search').value.toLowerCase();
    document.querySelectorAll('.chart-item').forEach(el => {
      const match = !q || el.dataset.title.toLowerCase().includes(q)
                        || el.dataset.layer.toLowerCase().includes(q);
      el.style.display = match ? '' : 'none';
    });
    document.querySelectorAll('.layer-group').forEach(g => {
      const visible = g.querySelectorAll('.chart-item[style*="display: none"]').length
                    < g.querySelectorAll('.chart-item').length;
      g.style.display = visible ? '' : 'none';
    });
  }

  // 键盘导航
  document.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT') return;
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') { e.preventDefault(); nextChart(); }
    if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') { e.preventDefault(); prevChart(); }
    const num = parseInt(e.key);
    if (num >= 1 && num <= 9) { e.preventDefault(); selectChart(num); }
  });

  // 初始选中
  document.querySelector('.chart-item[data-index="1"]').classList.add('active');
</script>

</body>
</html>
"""

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"仪表盘已生成: {os.path.abspath(OUTPUT)}")
print(f"  嵌入图表: {len(CHARTS)} 张")
print(f"  文件大小: {os.path.getsize(OUTPUT) / 1024:.1f} KB")
print(f"\n用浏览器打开 index.html 即可查看")
