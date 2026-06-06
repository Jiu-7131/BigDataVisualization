#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
行业聚合层数据处理脚本
覆盖图表: 图3日历热力图 / 图4动态气泡图 / 图5行业相关性网络图 / 图6平行坐标图 / 图9箱线图

输出:
  processed/01_industry/
    ├── industry_daily.csv          - 行业日度聚合
    ├── industry_monthly.csv        - 行业月度聚合 (日历热力图)
    ├── industry_quarterly.csv      - 行业季度聚合 (气泡图+平行坐标)
    ├── industry_corr_rolling.csv   - 滚动相关性 (网络图)
    └── industry_cluster.csv        - 聚类结果 (抱团识别)

依赖: preprocessed_all_data/daily/*, daily_basic/*, index_member/*, stock_basic.csv
"""

import os
import numpy as np
import pandas as pd
from tqdm import tqdm
from collections import defaultdict

# ========== 配置 ==========
SOURCE_DIR = "preprocessed_all_data"
SOURCE_RAW = "tushare_all_interfaces"  # 用于 index_member
OUTPUT_DIR = "processed/01_industry"
ROLLING_WINDOW = 60  # 滚动相关性窗口 (交易日)
MIN_STOCKS_IN_INDUSTRY = 3  # 行业最少股票数
# =========================

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# Step 1: 构建 股票 → 申万一级行业 映射
# ============================================================
print("Step 1: 构建股票 → 申万一级行业映射...")
member_dir = os.path.join(SOURCE_DIR, "index_member")
if not os.path.exists(member_dir) or not os.listdir(member_dir):
    member_dir = os.path.join(SOURCE_RAW, "index_member")
member_files = [f for f in os.listdir(member_dir) if f.endswith('.csv')]

stock_to_l1 = {}  # ts_code → l1_name
l1_industries = set()

for fname in member_files:
    df = pd.read_csv(os.path.join(member_dir, fname))
    for _, row in df.iterrows():
        l1_name = row['l1_name']
        l1_industries.add(l1_name)
        code = row['ts_code'].replace('.', '_')  # 统一为下划线格式，匹配文件名
        if code not in stock_to_l1:
            stock_to_l1[code] = l1_name

l1_industries = sorted(l1_industries)
print(f"   申万一级行业数: {len(l1_industries)}")
print(f"   已映射股票数: {len(stock_to_l1)}")

# ============================================================
# Step 2: 读取所有个股日线 + 日频基础数据，按行业聚合
# ============================================================
print("\nStep 2: 逐股票聚合为行业日度数据...")

daily_src = os.path.join(SOURCE_DIR, "daily")
basic_src = os.path.join(SOURCE_DIR, "daily_basic")
daily_files = [f for f in os.listdir(daily_src) if f.endswith('.csv')]
print(f"   共 {len(daily_files)} 只股票待处理")

# industry → date → {ret_sum, ret_count, mv_weighted_ret, turnover_list, pe_list, pb_list, mv_list, ...}
industry_accum = defaultdict(lambda: defaultdict(lambda: {
    'ret_sum': 0.0, 'ret_count': 0,
    'mv_ret_sum': 0.0, 'mv_total': 0.0,
    'turnover_list': [], 'pe_list': [], 'pb_list': [], 'mv_list': [],
    'pct_chg_list': [], 'vol_list': [], 'amount_list': [],
    'stock_count_set': set()
}))

skipped_no_industry = 0
for fname in tqdm(daily_files, desc="   处理个股"):
    ts_code = fname.replace('.csv', '')
    industry = stock_to_l1.get(ts_code)
    if industry is None:
        skipped_no_industry += 1
        continue

    daily_path = os.path.join(daily_src, fname)
    basic_path = os.path.join(basic_src, fname)

    try:
        df = pd.read_csv(daily_path)
        df['trade_date'] = pd.to_datetime(df['trade_date'])
    except Exception:
        continue

    has_basic = False
    if os.path.exists(basic_path):
        try:
            df_basic = pd.read_csv(basic_path)
            df_basic['trade_date'] = pd.to_datetime(df_basic['trade_date'])
            df = df.merge(df_basic[['trade_date', 'pe', 'pe_ttm', 'pb', 'total_mv', 'turnover_rate']],
                          on='trade_date', how='left')
            has_basic = True
        except Exception:
            pass

    # 向量化计算收益率
    if 'ret' in df.columns:
        df['_ret'] = df['ret']
    elif 'pct_chg' in df.columns:
        df['_ret'] = df['pct_chg'] / 100.0
    else:
        continue

    # 预过滤无效行，避免循环内逐行判断
    valid = df['_ret'].notna()
    if not valid.any():
        continue
    df = df[valid]

    for row in df.itertuples():
        date = row.trade_date
        acc = industry_accum[industry][date]
        ret = row._ret

        acc['ret_sum'] += ret
        acc['ret_count'] += 1
        acc['pct_chg_list'].append(ret * 100)
        acc['stock_count_set'].add(ts_code)

        mv = row.total_mv if has_basic else np.nan
        if not (pd.isna(mv) or mv <= 0):
            acc['mv_ret_sum'] += ret * mv
            acc['mv_total'] += mv
            acc['mv_list'].append(mv)

        if has_basic:
            pe = row.pe_ttm if pd.notna(row.pe_ttm) else row.pe
            pb = row.pb
            turnover = row.turnover_rate
        else:
            pe = np.nan
            pb = np.nan
            turnover = np.nan

        if not pd.isna(pe) and pe > 0:
            acc['pe_list'].append(pe)
        if not pd.isna(pb) and pb > 0:
            acc['pb_list'].append(pb)
        if not pd.isna(turnover):
            acc['turnover_list'].append(turnover)

        vol = row.vol
        amount = row.amount
        if not pd.isna(vol):
            acc['vol_list'].append(vol)
        if not pd.isna(amount):
            acc['amount_list'].append(amount)

print(f"   无行业映射的股票: {skipped_no_industry}")

# ============================================================
# Step 3: 计算行业日度聚合指标
# ============================================================
print("\nStep 3: 计算行业日度聚合指标...")
daily_records = []
for industry in tqdm(l1_industries, desc="   计算日度指标"):
    if industry not in industry_accum:
        continue
    for date, acc in industry_accum[industry].items():
        n_stocks = len(acc['stock_count_set'])
        if n_stocks < MIN_STOCKS_IN_INDUSTRY:
            continue

        avg_ret = acc['ret_sum'] / acc['ret_count'] if acc['ret_count'] > 0 else 0
        cap_ret = acc['mv_ret_sum'] / acc['mv_total'] if acc['mv_total'] > 0 else avg_ret
        avg_turnover = np.mean(acc['turnover_list']) if acc['turnover_list'] else np.nan
        med_pe = np.median(acc['pe_list']) if acc['pe_list'] else np.nan
        med_pb = np.median(acc['pb_list']) if acc['pb_list'] else np.nan
        total_mv = np.sum(acc['mv_list']) if acc['mv_list'] else np.nan
        total_vol = np.sum(acc['vol_list']) if acc['vol_list'] else np.nan
        total_amount = np.sum(acc['amount_list']) if acc['amount_list'] else np.nan
        avg_pct_chg = np.mean(acc['pct_chg_list']) if acc['pct_chg_list'] else np.nan

        daily_records.append({
            'trade_date': date,
            'industry': industry,
            'stock_count': n_stocks,
            'avg_ret': avg_ret,
            'cap_weighted_ret': cap_ret,
            'avg_pct_chg': avg_pct_chg,
            'avg_turnover': avg_turnover,
            'med_pe': med_pe,
            'med_pb': med_pb,
            'total_mv': total_mv,
            'total_vol': total_vol,
            'total_amount': total_amount,
        })

df_daily = pd.DataFrame(daily_records)
df_daily = df_daily.sort_values(['industry', 'trade_date']).reset_index(drop=True)
df_daily.to_csv(os.path.join(OUTPUT_DIR, "industry_daily.csv"), index=False, encoding='utf-8-sig')
print(f"   industry_daily.csv: {len(df_daily)} 行, {df_daily['industry'].nunique()} 个行业")

# ============================================================
# Step 4: 月度聚合
# ============================================================
print("\nStep 4: 计算行业月度聚合...")
df_daily['year'] = df_daily['trade_date'].dt.year
df_daily['month'] = df_daily['trade_date'].dt.month

monthly_records = []
for (industry, yr, mo), grp in tqdm(df_daily.groupby(['industry', 'year', 'month']), desc="   计算月度指标"):
    grp = grp.sort_values('trade_date')

    # 月度累计收益率
    monthly_ret = (1 + grp['avg_ret']).prod() - 1
    # 月内日波动率 (年化)
    daily_std = grp['avg_ret'].std()
    monthly_vol = daily_std * np.sqrt(252)

    monthly_records.append({
        'month': pd.Timestamp(year=yr, month=mo, day=1),
        'year': yr,
        'month_num': mo,
        'industry': industry,
        'monthly_ret': monthly_ret,
        'monthly_vol': monthly_vol,
        'avg_daily_ret': grp['avg_ret'].mean(),
        'med_pe': grp['med_pe'].iloc[-1] if len(grp) > 0 else np.nan,
        'med_pb': grp['med_pb'].iloc[-1] if len(grp) > 0 else np.nan,
        'total_mv': grp['total_mv'].iloc[-1] if len(grp) > 0 else np.nan,
        'avg_turnover': grp['avg_turnover'].mean(),
        'avg_stock_count': grp['stock_count'].mean(),
    })

df_monthly = pd.DataFrame(monthly_records)
df_monthly = df_monthly.sort_values(['industry', 'month']).reset_index(drop=True)
df_monthly.to_csv(os.path.join(OUTPUT_DIR, "industry_monthly.csv"), index=False, encoding='utf-8-sig')
print(f"   industry_monthly.csv: {len(df_monthly)} 行")

# ============================================================
# Step 5: 季度聚合 (含因子得分)
# ============================================================
print("\nStep 5: 计算行业季度聚合与因子得分...")
df_daily['quarter'] = df_daily['trade_date'].dt.to_period('Q')

quarterly_records = []
for (industry, q), grp in tqdm(df_daily.groupby(['industry', 'quarter']), desc="   计算季度指标"):
    grp = grp.sort_values('trade_date')
    rets = grp['avg_ret'].dropna()

    cum_ret = (1 + rets).prod() - 1
    avg_daily_ret = rets.mean()
    daily_vol = rets.std()
    ann_vol = daily_vol * np.sqrt(252)
    sharpe = (avg_daily_ret * 252) / ann_vol if ann_vol > 0 else 0

    # 动量：过去1季(即本季)、2季需要历史数据，先记录本季
    last_pe = grp['med_pe'].dropna().iloc[-1] if len(grp['med_pe'].dropna()) > 0 else np.nan
    last_pb = grp['med_pb'].dropna().iloc[-1] if len(grp['med_pb'].dropna()) > 0 else np.nan
    last_mv = grp['total_mv'].dropna().iloc[-1] if len(grp['total_mv'].dropna()) > 0 else np.nan

    quarterly_records.append({
        'quarter': q.end_time,
        'quarter_str': str(q),
        'industry': industry,
        'cum_ret': cum_ret,
        'ann_vol': ann_vol,
        'sharpe': sharpe,
        'avg_daily_ret': avg_daily_ret,
        'med_pe': last_pe,
        'med_pb': last_pb,
        'total_mv': last_mv,
        'avg_turnover': grp['avg_turnover'].mean(),
        'avg_stock_count': grp['stock_count'].mean(),
    })

df_q = pd.DataFrame(quarterly_records)
df_q = df_q.sort_values(['industry', 'quarter']).reset_index(drop=True)

# 计算动量因子 (过去 N 个季度累计收益，不含当季)
print("   计算动量因子...")
df_q = df_q.sort_values(['industry', 'quarter']).reset_index(drop=True)
cum_plus1 = df_q.groupby('industry')['cum_ret'].transform(lambda x: (1 + x).cumprod())
for lag in [1, 2, 4]:
    col = f'mom_{lag}q'
    numerator = cum_plus1.groupby(df_q['industry']).shift(1)
    denominator = cum_plus1.groupby(df_q['industry']).shift(lag + 1).fillna(1)
    df_q[col] = numerator / denominator - 1
    gp_pos = df_q.groupby('industry').cumcount()
    df_q.loc[gp_pos < lag, col] = np.nan

# Z-score 标准化各因子 (跨行业，每个季度)
print("   因子 Z-score 标准化...")
factor_cols = ['cum_ret', 'ann_vol', 'med_pe', 'med_pb', 'total_mv', 'avg_turnover', 'mom_1q', 'mom_2q', 'mom_4q']
for col in factor_cols:
    if col not in df_q.columns:
        continue
    df_q[f'{col}_z'] = df_q.groupby('quarter')[col].transform(
        lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0
    )

df_q.to_csv(os.path.join(OUTPUT_DIR, "industry_quarterly.csv"), index=False, encoding='utf-8-sig')
print(f"   industry_quarterly.csv: {len(df_q)} 行")

# ============================================================
# Step 6: 滚动相关性矩阵
# ============================================================
print("\nStep 6: 计算行业间滚动相关性...")
# 构造行业 × 日期 收益率矩阵
ret_pivot = df_daily.pivot_table(
    values='avg_ret', index='trade_date', columns='industry', aggfunc='mean'
).sort_index()

# 至少要有足够数据
valid_industries = ret_pivot.columns[ret_pivot.count() > ROLLING_WINDOW].tolist()
ret_pivot = ret_pivot[valid_industries].dropna(how='all')
print(f"   有效行业数: {len(valid_industries)}")

corr_records = []
# 每20个交易日取一个窗口，减少数据量
step = 20
dates = ret_pivot.index.tolist()
for i in tqdm(range(ROLLING_WINDOW - 1, len(dates), step), desc="   计算滚动相关"):
    window_end = dates[i]
    window_start = dates[i - ROLLING_WINDOW + 1]
    window_data = ret_pivot.loc[window_start:window_end]
    window_data = window_data.dropna(axis=1, thresh=ROLLING_WINDOW // 2)

    if window_data.shape[1] < 5:
        continue

    corr = window_data.corr()
    for ia, ind_a in enumerate(corr.columns):
        for ind_b in corr.columns[ia+1:]:
            corr_records.append({
                'window_end_date': window_end,
                'industry_a': ind_a,
                'industry_b': ind_b,
                'correlation': corr.loc[ind_a, ind_b],
            })

df_corr = pd.DataFrame(corr_records)
df_corr.to_csv(os.path.join(OUTPUT_DIR, "industry_corr_rolling.csv"), index=False, encoding='utf-8-sig')
print(f"   industry_corr_rolling.csv: {len(df_corr)} 行")

# ============================================================
# Step 7: 行业聚类 (抱团识别)
# ============================================================
print("\nStep 7: 行业聚类 (抱团识别)...")
# 按季度取平均相关性矩阵，然后聚类
try:
    from sklearn.cluster import AgglomerativeClustering

    df_corr['quarter'] = df_corr['window_end_date'].dt.to_period('Q')
    cluster_records = []

    for q, grp in tqdm(df_corr.groupby('quarter'), desc="   季度聚类"):
        if len(grp) < 100:
            continue

        # 构建平均相关矩阵
        avg_corr = grp.groupby(['industry_a', 'industry_b'])['correlation'].mean().reset_index()
        industries_in_q = sorted(set(avg_corr['industry_a'].unique()) | set(avg_corr['industry_b'].unique()))

        if len(industries_in_q) < 5:
            continue

        # 构建对称矩阵
        corr_matrix = pd.DataFrame(np.eye(len(industries_in_q)),
                                    index=industries_in_q, columns=industries_in_q)
        for _, row in avg_corr.iterrows():
            corr_matrix.loc[row['industry_a'], row['industry_b']] = row['correlation']
            corr_matrix.loc[row['industry_b'], row['industry_a']] = row['correlation']

        # 聚类 (3-5类)
        n_clusters = min(5, max(3, len(industries_in_q) // 5))
        dist = 1 - corr_matrix.values
        clustering = AgglomerativeClustering(n_clusters=n_clusters, linkage='ward')
        labels = clustering.fit_predict(dist)

        for ind, label in zip(industries_in_q, labels):
            cluster_records.append({
                'quarter': str(q),
                'industry': ind,
                'cluster_id': int(label),
            })

    df_cluster = pd.DataFrame(cluster_records)
    # 计算每个聚类内部平均相关性
    cluster_summary = []
    for (q, cid), grp in df_cluster.groupby(['quarter', 'cluster_id']):
        members = grp['industry'].tolist()
        q_period = pd.Period(q, freq='Q')
        sub = df_corr[(df_corr['window_end_date'].dt.to_period('Q') == q_period) &
                       (df_corr['industry_a'].isin(members)) &
                       (df_corr['industry_b'].isin(members))]
        avg_corr_val = sub['correlation'].mean() if len(sub) > 0 else np.nan
        cluster_summary.append({
            'quarter': str(q),
            'cluster_id': int(cid),
            'industry_count': len(members),
            'industry_list': '|'.join(members),
            'avg_correlation': avg_corr_val,
        })

    df_cluster_summary = pd.DataFrame(cluster_summary)
    df_cluster_summary.to_csv(os.path.join(OUTPUT_DIR, "industry_cluster.csv"),
                               index=False, encoding='utf-8-sig')
    print(f"   industry_cluster.csv: {len(df_cluster_summary)} 行")

except ImportError:
    print("   sklearn 未安装，跳过聚类分析。请 pip install scikit-learn")
    # 退而求其次：输出高相关行业对
    high_corr = df_corr[df_corr['correlation'] > 0.7]
    high_corr.to_csv(os.path.join(OUTPUT_DIR, "industry_cluster.csv"),
                     index=False, encoding='utf-8-sig')
    print(f"   industry_cluster.csv: 高相关行业对 {len(high_corr)} 行 (阈值>0.7)")

# ============================================================
# 完成
# ============================================================
print("\n" + "=" * 60)
print("行业聚合层处理完成!")
print(f"输出目录: {os.path.abspath(OUTPUT_DIR)}")
print("输出文件:")
for f in os.listdir(OUTPUT_DIR):
    fpath = os.path.join(OUTPUT_DIR, f)
    size_kb = os.path.getsize(fpath) / 1024
    print(f"  {f} ({size_kb:.1f} KB)")
