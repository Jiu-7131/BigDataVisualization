#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
宏观环境层数据处理脚本
覆盖图表: 图1宏观经济周期仪表盘 / 图2市场风格轮动热力三角图

输出:
  processed/02_macro/
    ├── macro_cycle.csv              - 宏观周期判断 (美林时钟)
    └── style_factor_monthly.csv     - 风格因子月度收益 (大盘/小盘/价值/成长)

依赖: preprocessed_all_data/cn_pmi.csv, cn_cpi.csv, cn_m.csv, style_index/
"""

import os
import numpy as np
import pandas as pd

# ========== 配置 ==========
SOURCE_DIR = "preprocessed_all_data"
OUTPUT_DIR = "processed/02_macro"

# 风格指数代码 (已在 style_index 目录中)
# 000016_SH_上证50.csv → 大盘价值
# 000300_SH_沪深300.csv → 大盘基准
# 000905_SH_中证500.csv → 中盘
# 399001_SZ_深证成指.csv → 深市基准
# 399006_SZ_创业板指.csv → 成长
# =========================

os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_macro_data():
    """加载宏观数据 (优先使用原始数据，避免预处理中 datetime 解析错误)"""
    raw = "tushare_all_interfaces"
    pmi = pd.read_csv(os.path.join(raw, "cn_pmi.csv"))
    cpi = pd.read_csv(os.path.join(raw, "cn_cpi.csv"))
    m2 = pd.read_csv(os.path.join(raw, "cn_m.csv"))
    return pmi, cpi, m2


def load_social_finance():
    """加载社融数据，计算存量同比增速"""
    raw = "tushare_all_interfaces"
    sf = pd.read_csv(os.path.join(raw, "social_finance.csv"))
    sf['month'] = pd.to_datetime(sf['month'].astype(str), format='%Y%m')
    sf = sf.sort_values('month').reset_index(drop=True)
    # 社融存量同比增速
    sf['sf_yoy'] = sf['stk_endval'].pct_change(12) * 100
    # 当月增量(亿元)和累计增量
    sf['inc_month'] = pd.to_numeric(sf['inc_month'], errors='coerce')
    sf['inc_cumval'] = pd.to_numeric(sf['inc_cumval'], errors='coerce')
    return sf[['month', 'inc_month', 'inc_cumval', 'stk_endval', 'sf_yoy']]


def load_bond_data():
    """加载10年期国债收益率，若不可用则回退到M2"""
    raw = "tushare_all_interfaces"
    bond_path = os.path.join(raw, "cn_10y_bond.csv")
    if os.path.exists(bond_path):
        bond = pd.read_csv(bond_path)
        bond['trade_date'] = pd.to_datetime(bond['trade_date'])
        bond['month'] = bond['trade_date'].dt.to_period('M').dt.to_timestamp()
        monthly = bond.groupby('month')['yield'].mean().reset_index()
        monthly.columns = ['month', 'bond_10y']
        return monthly, True
    return None, False


def clean_pmi(pmi):
    """清洗 PMI 数据: PMI列名为大写 MONTH (int: 202604), PMI010000"""
    month_col = 'MONTH' if 'MONTH' in pmi.columns else 'month'
    if 'PMI010000' in pmi.columns:
        df = pmi[[month_col, 'PMI010000']].copy()
    else:
        pmi_cols = [c for c in pmi.columns if 'PMI' in c and c not in ('CREATE_TIME', 'UPDATE_TIME', 'ID', 'UPDATE_BY', 'CREATE_BY')]
        df = pmi[[month_col, pmi_cols[0]]].copy()
    df.columns = ['month', 'pmi']
    df['month'] = pd.to_datetime(df['month'].astype(str), format='%Y%m')
    df['pmi'] = pd.to_numeric(df['pmi'], errors='coerce')
    return df.dropna(subset=['pmi'])


def clean_cpi(cpi):
    """清洗 CPI 数据: 提取全国CPI同比"""
    if 'nt_yoy' in cpi.columns:
        df = cpi[['month', 'nt_yoy']].copy()
        df.columns = ['month', 'cpi_yoy']
    else:
        # 尝试寻找同比列
        yoy_cols = [c for c in cpi.columns if 'yoy' in c.lower()]
        if yoy_cols:
            df = cpi[['month', yoy_cols[0]]].copy()
            df.columns = ['month', 'cpi_yoy']
        else:
            raise ValueError(f"无法识别CPI同比列，列: {cpi.columns.tolist()}")
    df['month'] = pd.to_datetime(df['month'].astype(str), format='%Y%m')
    df['cpi_yoy'] = pd.to_numeric(df['cpi_yoy'], errors='coerce')
    return df.dropna(subset=['cpi_yoy'])


def clean_m2(m2):
    """清洗 M2 数据: 提取M2同比增速"""
    if 'm2_yoy' in m2.columns:
        df = m2[['month', 'm2_yoy']].copy()
    else:
        yoy_cols = [c for c in m2.columns if 'yoy' in c.lower()]
        if yoy_cols:
            df = m2[['month', yoy_cols[0]]].copy()
            df.columns = ['month', 'm2_yoy']
        else:
            raise ValueError(f"无法识别M2列，列: {m2.columns.tolist()}")
    df['month'] = pd.to_datetime(df['month'].astype(str), format='%Y%m')
    df['m2_yoy'] = pd.to_numeric(df['m2_yoy'], errors='coerce')
    return df.dropna(subset=['m2_yoy'])


def load_style_indices():
    """加载风格指数日线数据"""
    style_dir = os.path.join(SOURCE_DIR, "style_index")
    style_files = os.listdir(style_dir)

    style_data = {}
    for fname in style_files:
        if not fname.endswith('.csv'):
            continue
        df = pd.read_csv(os.path.join(style_dir, fname))
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df = df.sort_values('trade_date')
        # 从文件名提取名称
        name = fname.replace('.csv', '')
        style_data[name] = df

    return style_data


def compute_monthly_returns(style_data):
    """计算风格指数月度收益率"""
    monthly_records = []
    for name, df in style_data.items():
        df = df.copy()
        df['year'] = df['trade_date'].dt.year
        df['month'] = df['trade_date'].dt.month

        for (yr, mo), grp in df.groupby(['year', 'month']):
            grp = grp.sort_values('trade_date')
            if 'pct_chg' in grp.columns:
                monthly_ret = (1 + grp['pct_chg'] / 100).prod() - 1
            elif 'close' in grp.columns:
                monthly_ret = grp['close'].iloc[-1] / grp['close'].iloc[0] - 1
            else:
                continue

            monthly_records.append({
                'month': pd.Timestamp(year=yr, month=mo, day=1),
                'index_name': name,
                'monthly_ret': monthly_ret,
            })

    return pd.DataFrame(monthly_records)


# ============================================================
# Step 1: 构建宏观周期表 (图1: 宏观经济周期仪表盘)
# ============================================================
print("=" * 60)
print("宏观环境层数据处理")
print("=" * 60)

print("\nStep 1: 构建宏观经济周期表...")
pmi, cpi, m2 = load_macro_data()
df_pmi = clean_pmi(pmi)
df_cpi = clean_cpi(cpi)
df_m2 = clean_m2(m2)

# 加载社融和国债数据
df_sf = load_social_finance()
df_bond, has_bond = load_bond_data()

# 合并宏观数据
df_macro = df_pmi.merge(df_cpi, on='month', how='outer').merge(df_m2, on='month', how='outer')
df_macro = df_macro.merge(df_sf, on='month', how='outer')
if has_bond:
    df_macro = df_macro.merge(df_bond, on='month', how='outer')
df_macro = df_macro.sort_values('month').reset_index(drop=True)
# 过滤到分析期 (2022-2026)
df_macro = df_macro[df_macro['month'] >= pd.Timestamp('2022-01-01')].reset_index(drop=True)
df_macro = df_macro.ffill()  # 前向填充月度缺失

# 计算趋势指标
df_macro['pmi_ma3'] = df_macro['pmi'].rolling(3, min_periods=1).mean()
df_macro['pmi_trend'] = df_macro['pmi'].diff(3)  # 3个月变化
df_macro['cpi_ma3'] = df_macro['cpi_yoy'].rolling(3, min_periods=1).mean()
df_macro['sf_ma3'] = df_macro['sf_yoy'].rolling(3, min_periods=1).mean()
df_macro['sf_trend'] = df_macro['sf_yoy'].diff(3)  # 社融3月趋势

# ---- 6票投票制周期判定 ----
# 增长方向: PMI(2票) + 社融(2票)
# 通胀方向: CPI(1票) + 国债/M2(1票)
# 共6票，增长上行+低通胀→复苏，增长上行+高通胀→过热
#       增长下行+低通胀→衰退，增长下行+高通胀→滞胀

# PMI 投票 (2票): >50 为增长上行
pmi_growth_votes = np.where(df_macro['pmi'] >= 50, 2, 0)
# 社融投票 (2票): sf_yoy > 8 为增长上行
sf_growth_votes = np.where(df_macro['sf_yoy'] >= 8, 2, 0)
growth_votes = pmi_growth_votes + sf_growth_votes  # 0-4票

# CPI 投票 (1票): cpi_yoy > 2.5 为高通胀
cpi_inflation_votes = np.where(df_macro['cpi_yoy'] >= 2.5, 1, 0)
# 国债/M2 投票 (1票): 国债 > 3.0 或 M2 > 10 为高通胀信号
if has_bond and 'bond_10y' in df_macro.columns:
    bond_inflation_votes = np.where(df_macro['bond_10y'] >= 3.0, 1, 0)
else:
    bond_inflation_votes = np.where(df_macro['m2_yoy'] >= 10.0, 1, 0)
inflation_votes = cpi_inflation_votes + bond_inflation_votes  # 0-2票

# 判定: 增长票 >= 3 (过半) → 增长上行; 通胀票 >= 1 → 高通胀
growth_up = growth_votes >= 3
high_inflation = inflation_votes >= 1

conditions = [
    growth_up & ~high_inflation,       # 增长上行 + 低通胀 → 复苏
    growth_up & high_inflation,        # 增长上行 + 高通胀 → 过热
    ~growth_up & high_inflation,       # 增长下行 + 高通胀 → 滞胀
    ~growth_up & ~high_inflation,      # 增长下行 + 低通胀 → 衰退
]
choices = ['复苏期', '过热期', '滞胀期', '衰退期']
df_macro['cycle_phase'] = np.select(conditions, choices, default='过渡期')

# 保存投票明细供图表使用
df_macro['growth_votes'] = growth_votes
df_macro['inflation_votes'] = inflation_votes
df_macro['pmi_votes'] = pmi_growth_votes
df_macro['sf_votes'] = sf_growth_votes

# 周期阶段变迁检测
df_macro['phase_change'] = (df_macro['cycle_phase'] != df_macro['cycle_phase'].shift(1)).astype(int)

# 仪表盘指标
df_macro['pmi_vs_50'] = df_macro['pmi'] - 50
df_macro['growth_score'] = (
    (df_macro['pmi_vs_50'].clip(-5, 5) / 5 * 50) + 50
).clip(0, 100)

# 连续扩张/收缩月数 (PMI)
pmi_above = df_macro['pmi'] >= 50
streak = 0
streak_arr = []
for v in pmi_above:
    if v:
        streak = streak + 1 if streak > 0 else 1
    else:
        streak = streak - 1 if streak < 0 else -1
    streak_arr.append(streak)
df_macro['pmi_streak'] = streak_arr

df_macro.to_csv(os.path.join(OUTPUT_DIR, "macro_cycle.csv"), index=False, encoding='utf-8-sig')
print(f"   macro_cycle.csv: {len(df_macro)} 行")
print(f"   周期分布:\n{df_macro['cycle_phase'].value_counts().to_string()}")
print(f"   社融增速范围: {df_macro['sf_yoy'].min():.1f} ~ {df_macro['sf_yoy'].max():.1f}")
if has_bond:
    print(f"   国债收益率范围: {df_macro['bond_10y'].min():.2f} ~ {df_macro['bond_10y'].max():.2f}")
else:
    print(f"   国债数据不可用，使用M2作为替代")
print(f"   最新月 ({df_macro['month'].iloc[-1].strftime('%Y-%m')}): "
      f"PMI={df_macro['pmi'].iloc[-1]:.1f}, "
      f"增长票={int(df_macro['growth_votes'].iloc[-1])}/4, "
      f"通胀票={int(df_macro['inflation_votes'].iloc[-1])}/2, "
      f"→ {df_macro['cycle_phase'].iloc[-1]}")

# ============================================================
# Step 2: 构建风格轮动数据 (图2: 市场风格轮动热力三角图)
# ============================================================
print("\nStep 2: 构建市场风格轮动数据...")
style_data = load_style_indices()
print(f"   已加载 {len(style_data)} 个风格指数")

df_style_monthly = compute_monthly_returns(style_data)

# 透视: 月份 × 指数
style_pivot = df_style_monthly.pivot_table(
    values='monthly_ret', index='month', columns='index_name', aggfunc='first'
).reset_index()

# 识别各指数角色 (根据文件名判断)
# 大盘: 上证50 / 沪深300
# 小盘: 中证500
# 价值: 上证50 (偏价值)
# 成长: 创业板指
large_cap_col = None
small_cap_col = None
value_col = None
growth_col = None

for col in style_pivot.columns:
    if col == 'month':
        continue
    if '上证50' in col:
        large_cap_col = col
        value_col = col
    elif '沪深300' in col:
        if large_cap_col is None:
            large_cap_col = col
    elif '中证500' in col:
        small_cap_col = col
    elif '创业板' in col:
        growth_col = col
    elif '深证' in col:
        pass

# 备用映射
if large_cap_col is None:
    large_cap_col = [c for c in style_pivot.columns if c != 'month'][0] if len(style_pivot.columns) > 1 else None
if small_cap_col is None:
    small_cap_col = large_cap_col
if value_col is None:
    value_col = large_cap_col
if growth_col is None:
    growth_col = [c for c in style_pivot.columns if c != 'month'][-1] if len(style_pivot.columns) > 2 else large_cap_col

print(f"   大盘: {large_cap_col}")
print(f"   小盘: {small_cap_col}")
print(f"   价值: {value_col}")
print(f"   成长: {growth_col}")

# 计算风格因子
df_style = style_pivot[['month']].copy()
if large_cap_col and small_cap_col and large_cap_col in style_pivot.columns and small_cap_col in style_pivot.columns:
    df_style['large_cap_ret'] = style_pivot[large_cap_col]
    df_style['small_cap_ret'] = style_pivot[small_cap_col]
    df_style['size_premium'] = df_style['small_cap_ret'] - df_style['large_cap_ret']
else:
    df_style['large_cap_ret'] = np.nan
    df_style['small_cap_ret'] = np.nan
    df_style['size_premium'] = np.nan

if value_col and growth_col and value_col in style_pivot.columns and growth_col in style_pivot.columns:
    df_style['value_ret'] = style_pivot[value_col]
    df_style['growth_ret'] = style_pivot[growth_col]
    df_style['value_growth_premium'] = df_style['value_ret'] - df_style['growth_ret']
else:
    df_style['value_ret'] = np.nan
    df_style['growth_ret'] = np.nan
    df_style['value_growth_premium'] = np.nan

# 风格方向判断
df_style['style_quadrant'] = '均衡'
df_style.loc[(df_style['size_premium'] > 0) & (df_style['value_growth_premium'] > 0), 'style_quadrant'] = '小盘价值'
df_style.loc[(df_style['size_premium'] > 0) & (df_style['value_growth_premium'] < 0), 'style_quadrant'] = '小盘成长'
df_style.loc[(df_style['size_premium'] < 0) & (df_style['value_growth_premium'] > 0), 'style_quadrant'] = '大盘价值'
df_style.loc[(df_style['size_premium'] < 0) & (df_style['value_growth_premium'] < 0), 'style_quadrant'] = '大盘成长'

# 热力三角图: X=大小盘溢价, Y=价值成长溢价
# 计算滚动强度 (3个月平滑)
df_style['size_strength'] = df_style['size_premium'].rolling(3, min_periods=1).mean()
df_style['value_strength'] = df_style['value_growth_premium'].rolling(3, min_periods=1).mean()
# 风格漂移距离 (相对于原点)
df_style['style_drift'] = np.sqrt(df_style['size_strength']**2 + df_style['value_strength']**2)
df_style['style_angle'] = np.arctan2(df_style['value_strength'], df_style['size_strength'])

# 保留原始风格指数数据
for col in style_pivot.columns:
    if col != 'month' and col not in df_style.columns:
        df_style[col] = style_pivot[col]

df_style.to_csv(os.path.join(OUTPUT_DIR, "style_factor_monthly.csv"), index=False, encoding='utf-8-sig')
print(f"   style_factor_monthly.csv: {len(df_style)} 行")
print(f"   风格象限分布:\n{df_style['style_quadrant'].value_counts().to_string()}")

# ============================================================
# 完成
# ============================================================
print("\n" + "=" * 60)
print("宏观环境层处理完成!")
print(f"输出目录: {os.path.abspath(OUTPUT_DIR)}")
for f in os.listdir(OUTPUT_DIR):
    fpath = os.path.join(OUTPUT_DIR, f)
    size_kb = os.path.getsize(fpath) / 1024
    print(f"  {f} ({size_kb:.1f} KB)")
