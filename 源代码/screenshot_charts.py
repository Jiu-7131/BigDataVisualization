#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""使用 Playwright 将12张 HTML 图表截图为高清 PNG (2x retina)"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright

HTML_DIR = r'D:\e-book\计算机\数据库\数据可视化\大作业\数据集相关\visualizations'

charts = [
    '01_宏观经济周期仪表盘',
    '02_风格轮动热力三角图',
    '03_日历热力图',
    '04_动态气泡图',
    '05_行业相关性网络图',
    '06_平行坐标图',
    '07_因子收益分析',
    '08_因子拥挤度监控',
    '09_牛熊周期箱线图',
    '10_行业配置桑基图',
    '11_压力测试热图',
    '12_实时监控预警仪表盘',
]

missing = [f'{c}.html' for c in charts if not os.path.exists(os.path.join(HTML_DIR, f'{c}.html'))]
if missing:
    print(f'缺少HTML文件: {missing}')
    sys.exit(1)

print(f'开始截图 {len(charts)} 张图表...')

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1600, 'height': 900})

    for name in charts:
        html_path = os.path.join(HTML_DIR, f'{name}.html')
        png_path = os.path.join(HTML_DIR, f'{name}.png')

        # file:// URL
        url = 'file:///' + html_path.replace('\\', '/')
        page.goto(url, wait_until='networkidle', timeout=30000)

        # 等 Plotly 渲染完成
        page.wait_for_timeout(2000)

        # 获取实际内容高度
        content_height = page.evaluate('document.body.scrollHeight')
        page.set_viewport_size({'width': 1600, 'height': min(content_height, 8000)})

        # 截图 (2x 高清)
        page.screenshot(path=png_path, full_page=True, scale='device')
        size_kb = os.path.getsize(png_path) / 1024
        print(f'  ✓ {name}.png ({size_kb:.0f} KB)')

    browser.close()

print(f'\n全部截图完成！输出目录: {HTML_DIR}')
