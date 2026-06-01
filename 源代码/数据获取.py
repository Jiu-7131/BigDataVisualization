#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tushare 数据获取脚本（所有接口，不含 cn_bond 和 social_finance）
时间范围：2022-01-01 至 2025-12-31
支持断点续传，已按接口频率限制设置延时。
"""

import os
import time
import tushare as ts
import pandas as pd
from tqdm import tqdm

# ==================== 配置 ====================
TOKEN = '42c404ed61ea286a905dfbc5955b6ddf480cd4f82f243c9aef1bcc1b'               # 请替换为你的 Tushare Token
START_DATE = '20220101'          # 开始日期 (2022年)
END_DATE   = '20251231'          # 结束日期 (2025年)

# 各接口请求间隔（秒）
SLEEP_FAST = 0.3          # 宏观数据、指数等低频接口
SLEEP_STOCK = 0.5         # 个股循环接口（日线、复权因子、daily_basic、资金流向）
SLEEP_MEMBER = 65         # index_member_all 专用（1次/分钟）
# =============================================

ts.set_token(TOKEN)
pro = ts.pro_api()

ROOT_DIR = "../数据集/tushare_all_interfaces"
os.makedirs(ROOT_DIR, exist_ok=True)

# 失败追踪
failed_stocks_daily = []
failed_stocks_adj = []
failed_stocks_basic = []
failed_stocks_money = []
failed_members = []
failed_sw_index = []

# ---------- 1. 交易日历 ----------
print("1. 交易日历...")
cal_file = os.path.join(ROOT_DIR, "trade_cal.csv")
if not os.path.exists(cal_file):
    df = pro.trade_cal(exchange='SSE', start_date=START_DATE, end_date=END_DATE)
    df.to_csv(cal_file, index=False, encoding='utf-8-sig')
    print(f"   已保存 {len(df)} 条")
else:
    print("   已存在，跳过")
time.sleep(SLEEP_FAST)

# ---------- 2. 行业分类 通过 stock_basic 获取行业信息 ----------
print("2. 获取股票基础信息（含行业分类）...")
stock_file = os.path.join(ROOT_DIR, "stock_basic.csv")
if not os.path.exists(stock_file):
    try:
        # 不限制 list_status，获取全部股票（含已退市），确保覆盖分析期内所有在市的个股
        df_stock = pro.stock_basic(exchange='', fields='ts_code,symbol,name,industry,list_date,list_status')
        if df_stock is not None and not df_stock.empty:
            df_stock = df_stock[df_stock['list_date'] <= END_DATE]
            df_stock.to_csv(stock_file, index=False, encoding='utf-8-sig')
            print(f"   已保存 {len(df_stock)} 条股票基础信息（含已退市）")
        else:
            print("   API 返回空数据，检查 Token 是否有效")
            exit(1)
    except Exception as e:
        print(f"   获取 stock_basic 失败: {e}")
        exit(1)
else:
    df_stock = pd.read_csv(stock_file, dtype={'ts_code': str})
    print(f"   股票基础信息已存在，共 {len(df_stock)} 条")

# 检查股票列表是否为空
codes = df_stock['ts_code'].tolist()
if not codes:
    print("   错误：股票列表为空，无法继续")
    exit(1)
print(f"   共 {len(codes)} 只股票")
time.sleep(SLEEP_FAST)

# ---------- 3. 行业成分股 使用 index_member_all（1次/分钟）----------
print("3. 行业成分股（申万一级）...")
sw_level1_codes = [
    '801010.SI', '801020.SI', '801030.SI', '801040.SI', '801050.SI',
    '801080.SI', '801110.SI', '801120.SI', '801130.SI', '801140.SI',
    '801150.SI', '801160.SI', '801170.SI', '801180.SI', '801200.SI',
    '801210.SI', '801230.SI', '801710.SI', '801720.SI', '801730.SI',
    '801740.SI', '801750.SI', '801760.SI', '801770.SI', '801780.SI',
    '801790.SI', '801880.SI', '801890.SI'
]
member_dir = os.path.join(ROOT_DIR, "index_member")
os.makedirs(member_dir, exist_ok=True)

for code in tqdm(sw_level1_codes, desc="   下载成分股"):
    safe_name = code.replace('.', '_')
    file_path = os.path.join(member_dir, f"{safe_name}.csv")
    if os.path.exists(file_path):
        continue
    try:
        df = pro.index_member_all(index_code=code)
        if df is not None and not df.empty:
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
        else:
            failed_members.append(code)
    except Exception as e:
        print(f"   下载 {code} 失败: {e}")
        failed_members.append(code)
    time.sleep(SLEEP_MEMBER)
if failed_members:
    print(f"   成分股下载失败 ({len(failed_members)}/{len(sw_level1_codes)}): {failed_members}")
else:
    print(f"   全部 {len(sw_level1_codes)} 个行业成分股下载完成")

# ---------- 4. 个股日线行情 全市场 ----------
print("4. 个股日线行情...")
daily_dir = os.path.join(ROOT_DIR, "daily")
os.makedirs(daily_dir, exist_ok=True)

for ts_code in tqdm(codes, desc="   下载日线"):
    safe_name = ts_code.replace('.', '_')
    file_path = os.path.join(daily_dir, f"{safe_name}.csv")
    if os.path.exists(file_path):
        continue
    try:
        df = pro.daily(ts_code=ts_code, start_date=START_DATE, end_date=END_DATE)
        if df is not None and not df.empty:
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
    except Exception as e:
        failed_stocks_daily.append(ts_code)
    time.sleep(SLEEP_STOCK)
if failed_stocks_daily:
    print(f"   日线下载失败 ({len(failed_stocks_daily)}/{len(codes)})")
else:
    print("   日线行情完成")

# ---------- 5. 复权因子 ----------
print("5. 复权因子...")
adj_dir = os.path.join(ROOT_DIR, "adj_factor")
os.makedirs(adj_dir, exist_ok=True)
for ts_code in tqdm(codes, desc="   下载复权因子"):
    safe_name = ts_code.replace('.', '_')
    file_path = os.path.join(adj_dir, f"{safe_name}.csv")
    if os.path.exists(file_path):
        continue
    try:
        df = pro.adj_factor(ts_code=ts_code, start_date=START_DATE, end_date=END_DATE)
        if df is not None and not df.empty:
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
    except Exception as e:
        failed_stocks_adj.append(ts_code)
    time.sleep(SLEEP_STOCK)
if failed_stocks_adj:
    print(f"   复权因子下载失败 ({len(failed_stocks_adj)}/{len(codes)})")
else:
    print("   复权因子完成")

# ---------- 6. 日频基础指标 ----------
print("6. 日频基础指标 (daily_basic)...")
basic_dir = os.path.join(ROOT_DIR, "daily_basic")
os.makedirs(basic_dir, exist_ok=True)
for ts_code in tqdm(codes, desc="   下载 daily_basic"):
    safe_name = ts_code.replace('.', '_')
    file_path = os.path.join(basic_dir, f"{safe_name}.csv")
    if os.path.exists(file_path):
        continue
    try:
        df = pro.daily_basic(ts_code=ts_code, start_date=START_DATE, end_date=END_DATE)
        if df is not None and not df.empty:
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
    except Exception as e:
        failed_stocks_basic.append(ts_code)
    time.sleep(SLEEP_STOCK)
if failed_stocks_basic:
    print(f"   daily_basic 下载失败 ({len(failed_stocks_basic)}/{len(codes)})")
else:
    print("   daily_basic 完成")

# ---------- 7. 制造业 PMI ----------
print("7. 制造业 PMI...")
pmi_file = os.path.join(ROOT_DIR, "cn_pmi.csv")
if not os.path.exists(pmi_file):
    df = pro.cn_pmi(start_date=START_DATE[:4]+'01', end_date=END_DATE[:4]+'12')
    df.to_csv(pmi_file, index=False, encoding='utf-8-sig')
    print(f"   已保存 {len(df)} 条")
else:
    print("   已存在，跳过")
time.sleep(SLEEP_FAST)

# ---------- 8. CPI ----------
print("8. CPI...")
cpi_file = os.path.join(ROOT_DIR, "cn_cpi.csv")
if not os.path.exists(cpi_file):
    df = pro.cn_cpi(start_date=START_DATE[:4]+'01', end_date=END_DATE[:4]+'12')
    df.to_csv(cpi_file, index=False, encoding='utf-8-sig')
    print(f"   已保存 {len(df)} 条")
else:
    print("   已存在，跳过")
time.sleep(SLEEP_FAST)

# ---------- 9. 风格指数日线 ----------
print("9. 风格指数日线...")
style_indices = {
    '399006.SZ': '创业板指',
    '399001.SZ': '深证成指',
    '000016.SH': '上证50',
    '000300.SH': '沪深300',
    '000905.SH': '中证500',
}
style_dir = os.path.join(ROOT_DIR, "style_index")
os.makedirs(style_dir, exist_ok=True)
for code, name in style_indices.items():
    safe_name = code.replace('.', '_')
    file_path = os.path.join(style_dir, f"{safe_name}_{name}.csv")
    if os.path.exists(file_path):
        print(f"   {name} 已存在，跳过")
        continue
    try:
        df = pro.index_daily(ts_code=code, start_date=START_DATE, end_date=END_DATE)
        if df is not None and not df.empty:
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            print(f"   已保存 {name} ({code})，{len(df)} 条")
    except Exception as e:
        print(f"   下载 {code} 失败: {e}")
    time.sleep(SLEEP_FAST)

# ---------- 10. M2货币供应量 ----------
print("10. M2货币供应量...")
m2_file = os.path.join(ROOT_DIR, "cn_m.csv")
if not os.path.exists(m2_file):
    df = pro.cn_m(start_date=START_DATE[:4]+'01', end_date=END_DATE[:4]+'12')
    df.to_csv(m2_file, index=False, encoding='utf-8-sig')
    print(f"   已保存 {len(df)} 条")
else:
    print("   已存在，跳过")
time.sleep(SLEEP_FAST)

# ---------- 11. 10年期国债收益率 ----------
print("11. 10年期国债收益率...")
bond_file = os.path.join(ROOT_DIR, "cn_10y_bond.csv")
if not os.path.exists(bond_file):
    try:
        df = pro.cn_gc(start_date=START_DATE, end_date=END_DATE, curve_type='0')
        if df is not None and not df.empty:
            # 筛选 10 年期（期限标签可能为 '10Y' 或 '10y' 或 '10'）
            tenors = ['10Y', '10y', '10', '10.0Y', '10.0y']
            for t in tenors:
                if t in df.columns:
                    df_10y = df[['trade_date', t]].copy()
                    df_10y.columns = ['trade_date', 'yield']
                    break
            else:
                # 如果有 tenor 列（长格式），筛选 10 年期行
                if 'tenor' in df.columns or 'maturity' in df.columns:
                    col = 'tenor' if 'tenor' in df.columns else 'maturity'
                    df_10y = df[df[col].astype(str).str.contains('10', na=False)].copy()
                else:
                    df_10y = df.copy()
            df_10y.to_csv(bond_file, index=False, encoding='utf-8-sig')
            print(f"   已保存 {len(df_10y)} 条 10 年期国债收益率")
        else:
            print("   API 返回空数据")
    except Exception as e:
        print(f"   获取国债收益率失败: {e}")
else:
    print("   已存在，跳过")
time.sleep(SLEEP_FAST)

# ---------- 12. 个股资金流向 ----------
print("12. 个股资金流向...")
money_dir = os.path.join(ROOT_DIR, "moneyflow")
os.makedirs(money_dir, exist_ok=True)
for ts_code in tqdm(codes, desc="   下载资金流向"):
    safe_name = ts_code.replace('.', '_')
    file_path = os.path.join(money_dir, f"{safe_name}.csv")
    if os.path.exists(file_path):
        continue
    try:
        df = pro.moneyflow(ts_code=ts_code, start_date=START_DATE, end_date=END_DATE)
        if df is not None and not df.empty:
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
    except Exception as e:
        failed_stocks_money.append(ts_code)
    time.sleep(SLEEP_STOCK)
if failed_stocks_money:
    print(f"   资金流向下载失败 ({len(failed_stocks_money)}/{len(codes)})")
else:
    print("   个股资金流向完成")

# ---------- 13. 申万行业指数日线 ----------
print("13. 申万行业指数日线...")
sw_dir = os.path.join(ROOT_DIR, "sw_index")
os.makedirs(sw_dir, exist_ok=True)
for code in tqdm(sw_level1_codes, desc="   下载申万行业指数"):
    safe_name = code.replace('.', '_')
    file_path = os.path.join(sw_dir, f"{safe_name}.csv")
    if os.path.exists(file_path):
        continue
    try:
        df = pro.sw_daily(ts_code=code, start_date=START_DATE, end_date=END_DATE)
        if df is not None and not df.empty:
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
        else:
            failed_sw_index.append(code)
    except Exception as e:
        failed_sw_index.append(code)
    time.sleep(SLEEP_FAST)
if failed_sw_index:
    print(f"   申万行业指数下载失败 ({len(failed_sw_index)}/{len(sw_level1_codes)}): {failed_sw_index}")
else:
    print("   申万行业指数下载完成")

# ==================== 下载结果汇总 ====================
print("\n" + "=" * 50)
print("数据获取完成，结果汇总：")
print(f"  数据保存目录: {os.path.abspath(ROOT_DIR)}")

def report(name, failed_list, total):
    ok = total - len(failed_list)
    if failed_list:
        print(f"  {name}: {ok}/{total} 成功, {len(failed_list)} 失败")
    else:
        print(f"  {name}: {total}/{total} 全部成功")

report("个股日线",        failed_stocks_daily,  len(codes))
report("复权因子",         failed_stocks_adj,    len(codes))
report("daily_basic",    failed_stocks_basic,  len(codes))
report("资金流向",         failed_stocks_money,  len(codes))
report("行业成分股",       failed_members,       len(sw_level1_codes))
report("申万行业指数日线", failed_sw_index,      len(sw_level1_codes))
print("=" * 50)