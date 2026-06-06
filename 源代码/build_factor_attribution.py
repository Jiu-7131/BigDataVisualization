#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
因子归因层数据处理脚本
覆盖图表: 图7因子收益贡献瀑布图 / 图8因子拥挤度监控仪表

输出:
  processed/03_factor/
    ├── factor_returns.csv          - 因子月度收益率 (SMB/HML/MOM)
    ├── industry_factor_decomp.csv  - 行业超额收益的因子拆解
    └── factor_crowding.csv         - 因子拥挤度指标

依赖: 个股 daily + daily_basic 数据 (PE/PB/市值用于分组)
"""

import os
import numpy as np
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# ========== 配置 ==========
SOURCE_DIR = "preprocessed_all_data"
OUTPUT_DIR = "processed/03_factor"
N_PORTFOLIOS = 5  # 分组数量 (五分位)
# =========================

os.makedirs(OUTPUT_DIR, exist_ok=True)


def _process_one_stock(fname, daily_src, basic_src):
    """处理单只股票的月度数据 (供并行调用)"""
    ts_code = fname.replace('.csv', '')
    records = []
    try:
        df = pd.read_csv(os.path.join(daily_src, fname))
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df['year'] = df['trade_date'].dt.year
        df['month'] = df['trade_date'].dt.month
    except Exception:
        return records

    basic_path = os.path.join(basic_src, fname)
    df_basic = None
    if os.path.exists(basic_path):
        try:
            df_basic = pd.read_csv(basic_path)
            df_basic['trade_date'] = pd.to_datetime(df_basic['trade_date'])
        except Exception:
            pass

    for (yr, mo), grp in df.groupby(['year', 'month']):
        grp = grp.sort_values('trade_date')
        if len(grp) < 10:
            continue
        if 'ret' in grp.columns:
            monthly_ret = (1 + grp['ret']).prod() - 1
        elif 'pct_chg' in grp.columns:
            monthly_ret = (1 + grp['pct_chg'] / 100).prod() - 1
        else:
            continue
        record = {
            'month': pd.Timestamp(year=yr, month=mo, day=1),
            'ts_code': ts_code,
            'monthly_ret': monthly_ret,
            'avg_vol': grp['vol'].mean() if 'vol' in grp.columns else np.nan,
            'pe_ttm': np.nan, 'pb': np.nan, 'total_mv': np.nan, 'turnover_rate': np.nan,
        }
        if df_basic is not None:
            last_basic = df_basic[(df_basic['trade_date'].dt.year == yr) & (df_basic['trade_date'].dt.month == mo)]
            if len(last_basic) > 0:
                last = last_basic.iloc[-1]
                record['pe_ttm'] = last.get('pe_ttm', last.get('pe', np.nan))
                record['pb'] = last.get('pb', np.nan)
                record['total_mv'] = last.get('total_mv', np.nan)
                record['turnover_rate'] = last.get('turnover_rate', np.nan)
        records.append(record)
    return records


def load_stock_monthly_returns():
    """并行读取个股日线计算月度收益率"""
    daily_src = os.path.join(SOURCE_DIR, "daily")
    basic_src = os.path.join(SOURCE_DIR, "daily_basic")
    files = [f for f in os.listdir(daily_src) if f.endswith('.csv')]

    print(f"   并行处理 {len(files)} 只股票的月度数据...")
    monthly_records = []

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_process_one_stock, f, daily_src, basic_src): f for f in files}
        for future in tqdm(as_completed(futures), total=len(files), desc="   个股月度收益"):
            try:
                monthly_records.extend(future.result())
            except Exception:
                pass

    df = pd.DataFrame(monthly_records)
    df = df.dropna(subset=['monthly_ret'])
    print(f"   共 {len(df)} 条月度记录")
    return df


def build_factors(df_monthly):
    """
    构建 Fama-French 风格因子 (SMB, HML, MOM)
    每月按市值/PB/动量排序分5组，Top-Bottom = 因子收益率
    """
    print("   构建因子...")
    factor_records = []

    for month, grp in tqdm(df_monthly.groupby('month'), desc="   月度因子"):
        grp = grp.copy()
        if len(grp) < 30:
            continue

        # --- SMB (Small Minus Big): 按市值 ---
        grp_smb = grp.dropna(subset=['total_mv'])
        if len(grp_smb) >= 30:
            grp_smb['size_rank'] = pd.qcut(grp_smb['total_mv'], N_PORTFOLIOS, labels=False, duplicates='drop')
            if grp_smb['size_rank'].nunique() >= 2:
                small = grp_smb[grp_smb['size_rank'] == 0]['monthly_ret'].mean()
                big = grp_smb[grp_smb['size_rank'] == grp_smb['size_rank'].max()]['monthly_ret'].mean()
                smb = small - big
            else:
                smb = np.nan
        else:
            smb = np.nan

        # --- HML (High Minus Low): 按PB (低PB=价值, 高PB=成长) ---
        grp_hml = grp.dropna(subset=['pb'])
        if len(grp_hml) >= 30:
            grp_hml['pb_rank'] = pd.qcut(grp_hml['pb'], N_PORTFOLIOS, labels=False, duplicates='drop')
            if grp_hml['pb_rank'].nunique() >= 2:
                high_pb = grp_hml[grp_hml['pb_rank'] == grp_hml['pb_rank'].max()]['monthly_ret'].mean()
                low_pb = grp_hml[grp_hml['pb_rank'] == 0]['monthly_ret'].mean()
                hml = low_pb - high_pb  # 价值 - 成长
            else:
                hml = np.nan
        else:
            hml = np.nan

        # --- MOM (Momentum): 按过去12个月累计收益 ---
        grp_mom = grp.dropna(subset=['mom_12m'])
        if len(grp_mom) >= 30:
            try:
                grp_mom['mom_rank'] = pd.qcut(grp_mom['mom_12m'], N_PORTFOLIOS, labels=False, duplicates='drop')
                if grp_mom['mom_rank'].nunique() >= 2:
                    winners = grp_mom[grp_mom['mom_rank'] == grp_mom['mom_rank'].max()]['monthly_ret'].mean()
                    losers = grp_mom[grp_mom['mom_rank'] == 0]['monthly_ret'].mean()
                    mom = winners - losers
                else:
                    mom = np.nan
            except Exception:
                mom = np.nan
        else:
            mom = np.nan

        # 市场因子: 全部股票等权平均
        mkt = grp['monthly_ret'].mean()

        factor_records.append({
            'month': month,
            'Rm': mkt,
            'SMB': smb,
            'HML': hml,
            'MOM': mom,
            'stock_count': len(grp),
        })

    return pd.DataFrame(factor_records)


def decompose_industry_excess(df_monthly, df_factors, df_industry):
    """对每个行业超额收益做因子归因"""
    print("   行业超额收益归因...")

    # 合并行业标签
    monthly_with_ind = df_monthly.merge(df_industry, on='ts_code', how='left')

    decomp_records = []
    for (q, industry), grp in tqdm(monthly_with_ind.groupby(
        [monthly_with_ind['month'].dt.to_period('Q'), 'l1_industry']
    ), desc="   归因"):
        if industry == '其他' or len(grp) < 5:
            continue

        # 行业等权月度收益
        ind_ret = grp['monthly_ret'].mean()

        # 合并因子
        merged = grp[['month']].drop_duplicates().merge(
            df_factors[['month', 'Rm', 'SMB', 'HML', 'MOM']], on='month', how='inner'
        )
        if len(merged) < 6:
            continue

        # 行业超额 vs 市场
        excess = (1 + ind_ret) - (1 + merged['Rm'].mean())

        # 近似归因: 计算行业在各因子上的平均暴露
        avg_smb = merged['SMB'].mean()
        avg_hml = merged['HML'].mean()
        avg_mom = merged['MOM'].mean()

        decomp_records.append({
            'quarter': q.end_time,
            'industry': industry,
            'industry_ret': ind_ret,
            'market_ret': merged['Rm'].mean(),
            'excess_ret': excess,
            'SMB_contrib': avg_smb,
            'HML_contrib': avg_hml,
            'MOM_contrib': avg_mom,
            'alpha': excess - (avg_smb + avg_hml + avg_mom),
        })

    return pd.DataFrame(decomp_records)


def compute_crowding(df_monthly):
    """计算因子拥挤度"""
    print("   计算因子拥挤度...")
    crowding_records = []

    for month, grp in tqdm(df_monthly.groupby('month'), desc="   拥挤度"):
        grp = grp.copy()
        if len(grp) < 30:
            continue

        # 1. 估值价差 (top - bottom PB分组的PB中位数之差)
        grp_pb = grp.dropna(subset=['pb'])
        valuation_spread = np.nan
        if len(grp_pb) >= 30:
            try:
                grp_pb['pb_rank'] = pd.qcut(grp_pb['pb'], N_PORTFOLIOS, labels=False, duplicates='drop')
                top_pb = grp_pb[grp_pb['pb_rank'] == grp_pb['pb_rank'].max()]['pb'].median()
                bot_pb = grp_pb[grp_pb['pb_rank'] == 0]['pb'].median()
                valuation_spread = top_pb - bot_pb
            except Exception:
                pass

        # 2. 因子内相关性 (市值因子组内个股 pairwise 平均相关性)
        grp_mv = grp.dropna(subset=['total_mv'])
        within_corr = np.nan
        if len(grp_mv) >= 30:
            try:
                grp_mv['mv_rank'] = pd.qcut(grp_mv['total_mv'], N_PORTFOLIOS, labels=False, duplicates='drop')
                top_mv_stocks = grp_mv[grp_mv['mv_rank'] == grp_mv['mv_rank'].max()]['ts_code'].tolist()
                # 从历史数据中取这些股票过去3个月的收益相关性
                past = df_monthly[
                    (df_monthly['month'] <= month) &
                    (df_monthly['month'] > month - pd.DateOffset(months=3)) &
                    (df_monthly['ts_code'].isin(top_mv_stocks))
                ]
                if len(top_mv_stocks) >= 5:
                    pivot = past.pivot_table(values='monthly_ret', index='month', columns='ts_code')
                    if pivot.shape[1] >= 5:
                        corr = pivot.corr()
                        within_corr = corr.values[np.triu_indices_from(corr.values, k=1)].mean()
            except Exception:
                pass

        # 3. 换手率集中度 (HHI)
        grp_turn = grp.dropna(subset=['turnover_rate'])
        turnover_hhi = np.nan
        if len(grp_turn) >= 30:
            try:
                total_turn = grp_turn['turnover_rate'].sum()
                if total_turn > 0:
                    shares = grp_turn['turnover_rate'] / total_turn
                    turnover_hhi = (shares ** 2).sum()
            except Exception:
                pass

        crowding_records.append({
            'month': month,
            'valuation_spread': valuation_spread,
            'within_factor_corr': within_corr,
            'turnover_hhi': turnover_hhi,
        })

    df_crowd = pd.DataFrame(crowding_records)

    # 用 expanding 标准化 (避免前视偏差)
    for col in ['valuation_spread', 'within_factor_corr', 'turnover_hhi']:
        exp_mean = df_crowd[col].expanding(min_periods=12).mean()
        exp_std = df_crowd[col].expanding(min_periods=12).std()
        df_crowd[f'{col}_z'] = ((df_crowd[col] - exp_mean) / exp_std.replace(0, np.nan)).fillna(0)

    z_cols = [c for c in df_crowd.columns if c.endswith('_z')]
    df_crowd['crowding_score'] = df_crowd[z_cols].mean(axis=1)

    # 分级预警
    bins = [-np.inf, -1, 1, 2, np.inf]
    labels = ['正常', '关注', '警示', '危险']
    df_crowd['crowding_level'] = pd.cut(df_crowd['crowding_score'], bins=bins, labels=labels)

    return df_crowd


# ============================================================
# Main
# ============================================================
print("=" * 60)
print("因子归因层数据处理")
print("=" * 60)

# Step 1: 加载个股月度数据
print("\nStep 1: 加载个股月度收益率和基本面数据...")
df_monthly = load_stock_monthly_returns()

# Pre-compute 12-month momentum per stock (avoid O(n*m) scan per month)
print("   预计算动量因子...")
df_monthly = df_monthly.sort_values(['ts_code', 'month'])
cum_plus1 = df_monthly.groupby('ts_code')['monthly_ret'].transform(lambda x: (1 + x).cumprod())
df_monthly['mom_12m'] = cum_plus1 / cum_plus1.groupby(df_monthly['ts_code']).shift(12).fillna(1) - 1

# Step 2: 构建因子收益率
print("\nStep 2: 构建 SMB/HML/MOM 因子...")
df_factors = build_factors(df_monthly)

# 计算因子累计收益
df_factors = df_factors.sort_values('month')
for col in ['Rm', 'SMB', 'HML', 'MOM']:
    df_factors[f'{col}_cum'] = (1 + df_factors[col].fillna(0)).cumprod()

df_factors.to_csv(os.path.join(OUTPUT_DIR, "factor_returns.csv"), index=False, encoding='utf-8-sig')
print(f"   factor_returns.csv: {len(df_factors)} 行")

# Step 3: 行业超额收益归因
print("\nStep 3: 行业超额收益因子拆解...")

# 加载行业映射
member_dir = os.path.join(SOURCE_DIR, "index_member")
if not os.path.exists(member_dir):
    member_dir = os.path.join("tushare_all_interfaces", "index_member")
member_files = [f for f in os.listdir(member_dir) if f.endswith('.csv')]

stock_to_l1 = {}
for fname in member_files:
    df_member = pd.read_csv(os.path.join(member_dir, fname))
    for _, row in df_member.iterrows():
        code = row['ts_code'].replace('.', '_')
        if code not in stock_to_l1:
            stock_to_l1[code] = row['l1_name']

df_industry_map = pd.DataFrame([
    {'ts_code': k, 'l1_industry': v} for k, v in stock_to_l1.items()
])

df_decomp = decompose_industry_excess(df_monthly, df_factors, df_industry_map)
df_decomp.to_csv(os.path.join(OUTPUT_DIR, "industry_factor_decomp.csv"), index=False, encoding='utf-8-sig')
print(f"   industry_factor_decomp.csv: {len(df_decomp)} 行")

# Step 4: 因子拥挤度
print("\nStep 4: 计算因子拥挤度...")
df_crowding = compute_crowding(df_monthly)
df_crowding.to_csv(os.path.join(OUTPUT_DIR, "factor_crowding.csv"), index=False, encoding='utf-8-sig')
print(f"   factor_crowding.csv: {len(df_crowding)} 行")

# ============================================================
print("\n" + "=" * 60)
print("因子归因层处理完成!")
print(f"输出目录: {os.path.abspath(OUTPUT_DIR)}")
for f in os.listdir(OUTPUT_DIR):
    fpath = os.path.join(OUTPUT_DIR, f)
    size_kb = os.path.getsize(fpath) / 1024
    print(f"  {f} ({size_kb:.1f} KB)")
