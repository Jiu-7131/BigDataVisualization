#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tushare Pro 全量数据获取脚本
=============================
时间范围：2022-01-01 至 2025-12-31（4 个完整年度）
特性：断点续传、按接口频率限制延时、步骤选择（--steps）、依赖自动解析
数据输出：../数据集/tushare_all_interfaces/

用法:
  python 数据获取.py                  # 运行全部 14 个步骤
  python 数据获取.py --list           # 列出所有步骤和依赖关系
  python 数据获取.py -s 1,2,4,8       # 只运行指定步骤（逗号分隔）
  python 数据获取.py -s 8             # 获取三类 PMI（合并为一步）
  python 数据获取.py -s 4             # 选步 4 自动包含依赖步 2
  python 数据获取.py -s 9-12          # 只获取宏观数据
"""

# ── 标准库 ──────────────────────────────────────────
import argparse
import os
import sys

# ╔══════════════════════════════════════════════════════════════╗
# ║                  步骤注册表 & 命令行解析                      ║
# ║       （此阶段不依赖 tushare，--list 可离线运行）             ║
# ╚══════════════════════════════════════════════════════════════╝

# 步骤注册：{ 编号: (名称, 依赖步骤集合) }
# 依赖自动展开：选中下游步骤时，其依赖步骤会被自动包含
STEPS = {
    # ── 一、基础数据 ──
    1:  ("交易日历",           set()),
    2:  ("股票基础信息",       set()),
    3:  ("行业成分股",         {2}),
    # ── 二、个股行情数据 ──
    4:  ("个股日线行情",       {2}),
    5:  ("复权因子",           {2}),
    6:  ("日频基础指标",       {2}),
    7:  ("个股资金流向",       {2}),
    # ── 三、宏观经济数据 ──
    8:  ("PMI（制造/非制造/综合）", set()),
    9:  ("CPI",                set()),
    10: ("M2货币供应量",       set()),
    11: ("10年期国债收益率",   set()),
    12: ("社融规模",           set()),
    # ── 四、指数行情数据 ──
    13: ("风格指数日线",       set()),
    14: ("申万行业指数日线",   {3}),
}

# ── 命令行参数 ──────────────────────────────────────
parser = argparse.ArgumentParser(
    description="Tushare Pro 全量数据获取脚本（2022-2025）",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="示例:\n  python 数据获取.py -s 8-12          # 宏观数据\n"
           "  python 数据获取.py -s 1-7              # 个股数据\n"
           "  python 数据获取.py -s 4                # 日线（自动含步2）")
parser.add_argument("-s", "--steps", type=str, default="all",
                    help="要运行的步骤，逗号分隔或范围，如 '1,4,8-10'（默认 all）")
parser.add_argument("-l", "--list", action="store_true",
                    help="列出所有可用步骤及依赖关系")
args = parser.parse_args()

# ── --list：打印步骤表并退出 ────────────────────────
if args.list:
    sections = {
        "一、基础数据":   [1, 2, 3],
        "二、个股行情数据": [4, 5, 6, 7],
        "三、宏观经济数据": [8, 9, 10, 11, 12],
        "四、指数行情数据": [13, 14],
    }
    for title, ids in sections.items():
        print(f"\n  {title}")
        for sid in ids:
            name, deps = STEPS[sid]
            dep_str = f"  ← 依赖: {', '.join(STEPS[d][0] for d in deps)}" if deps else ""
            print(f"    {sid:2d}. {name}{dep_str}")
    sys.exit(0)

# ── 解析步骤选择（含依赖递归展开）───────────────────
def resolve_steps(step_str):
    """将 '1,4,8-10' 解析为步骤编号集合，并递归展开所有依赖"""
    if step_str.lower() == "all":
        return set(STEPS.keys())
    selected = set()
    for part in step_str.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            selected.update(range(int(a), int(b) + 1))
        else:
            selected.add(int(part))
    # 循环展开依赖直到不再增加
    changed = True
    while changed:
        changed = False
        for sid in list(selected):
            for dep in STEPS[sid][1]:
                if dep not in selected:
                    selected.add(dep)
                    changed = True
    return selected

selected = resolve_steps(args.steps)
print(f"将运行步骤: {sorted(selected)}")
print("-" * 40)

# ╔══════════════════════════════════════════════════════════════╗
# ║              第三方库导入 & 配置 & 初始化                    ║
# ╚══════════════════════════════════════════════════════════════╝

# ── 依赖导入（--list 后才会执行到这里）─────────────
import time
import tushare as ts
import numpy as np
import pandas as pd
from tqdm import tqdm

# ── 全局配置 ───────────────────────────────────────
TOKEN = 'df52f92c5a4200a3f9598718539201a65d87becdb0fe6ba1328aaa31'   # 请替换为你的 Tushare Pro Token
START_DATE = '20220101'          # 数据开始日期（含）
END_DATE   = '20251231'          # 数据结束日期（含）

# 请求间隔（秒），避免触发 Tushare 频率限制
SLEEP_FAST   = 0.3    # 宏观数据、指数等低频接口
SLEEP_STOCK  = 0.5    # 个股循环接口（日线、复权因子、daily_basic、资金流向）
SLEEP_MEMBER = 65     # index_member_all 专用（1 次/分钟限制）
ts.set_token(TOKEN)
pro = ts.pro_api()
ROOT_DIR = "../数据集/tushare_all_interfaces"   # 数据输出根目录
os.makedirs(ROOT_DIR, exist_ok=True)

# ── 共享数据 ───────────────────────────────────────
# 申万一级行业代码（由步3从 index_classify 加载，此处初始化默认值兜底）
sw_level1_codes = []

# 失败追踪列表（循环步骤用，末尾汇总报告）
failed_stocks_daily = []
failed_stocks_adj   = []
failed_stocks_basic = []
failed_stocks_money = []
failed_members      = []
failed_sw_index     = []


# ── 进度追踪工具 ─────────────────────────────────
# 用于长时间循环步骤的断点续读：每处理 N 条将已完成列表写入 _progress.txt
FLUSH_EVERY = 10   # 每完成 N 条刷新一次进度文件

def load_progress(tracker_file):
    """读取已完成代码的集合，文件不存在则返回空集合"""
    if os.path.exists(tracker_file):
        with open(tracker_file, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_progress(tracker_file, done_set):
    """将已完成集合写入进度文件"""
    with open(tracker_file, 'w') as f:
        for code in sorted(done_set):
            f.write(code + '\n')

# ╔══════════════════════════════════════════════════════════════╗
# ║           一、基础数据：交易日历 / 股票列表 / 行业分类        ║
# ║      后续所有个股和行业步骤都依赖此板块的输出                 ║
# ╚══════════════════════════════════════════════════════════════╝

# ── 步1：交易日历 ──────────────────────────────────
# 获取上交所全部交易日，用于时间轴对齐和日期校验
# 输出：trade_cal.csv
if 1 in selected:
    print("1. 交易日历...")
    cal_file = os.path.join(ROOT_DIR, "trade_cal.csv")
    if not os.path.exists(cal_file):
        df = pro.trade_cal(exchange='SSE', start_date=START_DATE, end_date=END_DATE)
        df.to_csv(cal_file, index=False, encoding='utf-8-sig')
        print(f"   已保存 {len(df)} 条交易日")
    else:
        print("   已存在，跳过")
    time.sleep(SLEEP_FAST)

# ── 步2：股票基础信息 ──────────────────────────────
# 获取全部 A 股列表（含行业分类、上市日期），不限上市状态以确保覆盖退市股
# 输出：stock_basic.csv
# 此步骤为依赖基：选中步3-7 或 步14 时自动包含
need_stock_basic = bool(selected & {2, 3, 4, 5, 6, 7, 14})
if need_stock_basic:
    print("2. 获取股票基础信息（含行业分类）...")
    stock_file = os.path.join(ROOT_DIR, "stock_basic.csv")
    if not os.path.exists(stock_file):
        try:
            # 不限 list_status → 含已退市股票，确保覆盖分析期内全部在市的个股
            df_stock = pro.stock_basic(exchange='',
                                       fields='ts_code,symbol,name,industry,list_date,list_status')
            if df_stock is not None and not df_stock.empty:
                df_stock = df_stock[df_stock['list_date'] <= END_DATE]
                df_stock.to_csv(stock_file, index=False, encoding='utf-8-sig')
                print(f"   已保存 {len(df_stock)} 条股票基础信息（含已退市）")
            else:
                print("   API 返回空数据，请检查 Token 是否有效")
                exit(1)
        except Exception as e:
            print(f"   获取 stock_basic 失败: {e}")
            exit(1)
    else:
        df_stock = pd.read_csv(stock_file, dtype={'ts_code': str})
        print(f"   股票基础信息已存在，共 {len(df_stock)} 条")

    # 提取股票代码列表（后续个股循环步骤共用）
    codes = df_stock['ts_code'].tolist()
    if not codes:
        print("   错误：股票列表为空，无法继续")
        exit(1)
    print(f"   共 {len(codes)} 只股票")
    time.sleep(SLEEP_FAST)

# ── 步3：行业分类 + 成分股 ──────────────────────────
# 获取 SW2021 申万一级行业分类（31 个），再下载各行业成分股
# 输出：index_member/{code}.csv + index_classify.csv
if 3 in selected:
    print("3. 行业分类与成分股（SW2021）...")

    # 3a. 获取行业分类（SW2021，31 个一级行业）
    classify_file = os.path.join(ROOT_DIR, "index_classify.csv")
    if not os.path.exists(classify_file):
        df_cls = pro.index_classify(level='L1', src='SW2021')
        if df_cls is not None and not df_cls.empty:
            df_cls.to_csv(classify_file, index=False, encoding='utf-8-sig')
            sw_level1_codes[:] = df_cls['index_code'].tolist()
            print(f"   已保存行业分类: {len(sw_level1_codes)} 个 SW2021 一级行业")
        else:
            print("   index_classify 返回空，使用默认28行业")
            sw_level1_codes[:] = ['801010.SI','801020.SI','801030.SI','801040.SI','801050.SI',
                '801080.SI','801110.SI','801120.SI','801130.SI','801140.SI',
                '801150.SI','801160.SI','801170.SI','801180.SI','801200.SI',
                '801210.SI','801230.SI','801710.SI','801720.SI','801730.SI',
                '801740.SI','801750.SI','801760.SI','801770.SI','801780.SI',
                '801790.SI','801880.SI','801890.SI']
    else:
        df_cls = pd.read_csv(classify_file, dtype={'index_code': str})
        sw_level1_codes[:] = df_cls['index_code'].tolist()
        print(f"   行业分类已存在: {len(sw_level1_codes)} 个行业")
    time.sleep(SLEEP_FAST)

    # 3b. 下载各行业成分股
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


# ╔══════════════════════════════════════════════════════════════╗
# ║          二、个股行情数据：OHLCV / 复权 / 指标 / 资金         ║
# ║      全部按股票代码逐只遍历，断点续传，可分批运行              ║
# ╚══════════════════════════════════════════════════════════════╝

# ── 步4：个股日线行情 ──────────────────────────────
# 每只股票每日的开盘价、最高价、最低价、收盘价、成交量、成交额、涨跌幅
# 输出：daily/{ts_code}.csv（约 5463 个文件）
# 进度：daily/_progress.txt，每 10 条刷新
if 4 in selected:
    print("4. 个股日线行情...")
    daily_dir = os.path.join(ROOT_DIR, "daily")
    os.makedirs(daily_dir, exist_ok=True)
    tracker = os.path.join(daily_dir, "_progress.txt")
    done = load_progress(tracker)
    cnt = len(done)

    for i, ts_code in enumerate(tqdm(codes, desc="   下载日线", initial=cnt, total=len(codes))):
        safe_name = ts_code.replace('.', '_')
        file_path = os.path.join(daily_dir, f"{safe_name}.csv")
        if safe_name in done or os.path.exists(file_path):
            done.add(safe_name)
            continue
        try:
            df = pro.daily(ts_code=ts_code, start_date=START_DATE, end_date=END_DATE)
            if df is not None and not df.empty:
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                done.add(safe_name)
        except Exception:
            failed_stocks_daily.append(ts_code)
        time.sleep(SLEEP_STOCK)
        # 每 FLUSH_EVERY 条刷新进度文件
        if (i + 1) % FLUSH_EVERY == 0:
            save_progress(tracker, done)
    save_progress(tracker, done)  # 最终刷新
    if failed_stocks_daily:
        print(f"   日线下载失败 ({len(failed_stocks_daily)}/{len(codes)})")
    else:
        print("   日线行情完成")

# ── 步5：复权因子 ──────────────────────────────────
# 每只股票每日的前复权因子，用于价格调整
# 输出：adj_factor/{ts_code}.csv
# 进度：adj_factor/_progress.txt，每 10 条刷新
if 5 in selected:
    print("5. 复权因子...")
    adj_dir = os.path.join(ROOT_DIR, "adj_factor")
    os.makedirs(adj_dir, exist_ok=True)
    tracker = os.path.join(adj_dir, "_progress.txt")
    done = load_progress(tracker)
    cnt = len(done)
    for i, ts_code in enumerate(tqdm(codes, desc="   下载复权因子", initial=cnt, total=len(codes))):
        safe_name = ts_code.replace('.', '_')
        file_path = os.path.join(adj_dir, f"{safe_name}.csv")
        if safe_name in done or os.path.exists(file_path):
            done.add(safe_name)
            continue
        try:
            df = pro.adj_factor(ts_code=ts_code, start_date=START_DATE, end_date=END_DATE)
            if df is not None and not df.empty:
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                done.add(safe_name)
        except Exception:
            failed_stocks_adj.append(ts_code)
        time.sleep(SLEEP_STOCK)
        if (i + 1) % FLUSH_EVERY == 0:
            save_progress(tracker, done)
    save_progress(tracker, done)
    if failed_stocks_adj:
        print(f"   复权因子下载失败 ({len(failed_stocks_adj)}/{len(codes)})")
    else:
        print("   复权因子完成")

# ── 步6：日频基础指标 ──────────────────────────────
# 每只股票每日的 PE_TTM、PB、换手率、总市值等基本面指标
# 输出：daily_basic/{ts_code}.csv
# 进度：daily_basic/_progress.txt，每 10 条刷新
if 6 in selected:
    print("6. 日频基础指标 (daily_basic)...")
    basic_dir = os.path.join(ROOT_DIR, "daily_basic")
    os.makedirs(basic_dir, exist_ok=True)
    tracker = os.path.join(basic_dir, "_progress.txt")
    done = load_progress(tracker)
    cnt = len(done)
    for i, ts_code in enumerate(tqdm(codes, desc="   下载 daily_basic", initial=cnt, total=len(codes))):
        safe_name = ts_code.replace('.', '_')
        file_path = os.path.join(basic_dir, f"{safe_name}.csv")
        if safe_name in done or os.path.exists(file_path):
            done.add(safe_name)
            continue
        try:
            df = pro.daily_basic(ts_code=ts_code, start_date=START_DATE, end_date=END_DATE)
            if df is not None and not df.empty:
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                done.add(safe_name)
        except Exception:
            failed_stocks_basic.append(ts_code)
        time.sleep(SLEEP_STOCK)
        if (i + 1) % FLUSH_EVERY == 0:
            save_progress(tracker, done)
    save_progress(tracker, done)
    if failed_stocks_basic:
        print(f"   daily_basic 下载失败 ({len(failed_stocks_basic)}/{len(codes)})")
    else:
        print("   daily_basic 完成")

# ── 步7：个股资金流向 ──────────────────────────────
# 每只股票每日的大单、中单、小单净流入额及主力资金净流向
# 输出：moneyflow/{ts_code}.csv（部分股票可能无数据，属正常）
# 进度：moneyflow/_progress.txt，每 10 条刷新
if 7 in selected:
    print("7. 个股资金流向...")
    money_dir = os.path.join(ROOT_DIR, "moneyflow")
    os.makedirs(money_dir, exist_ok=True)
    tracker = os.path.join(money_dir, "_progress.txt")
    done = load_progress(tracker)
    cnt = len(done)
    for i, ts_code in enumerate(tqdm(codes, desc="   下载资金流向", initial=cnt, total=len(codes))):
        safe_name = ts_code.replace('.', '_')
        file_path = os.path.join(money_dir, f"{safe_name}.csv")
        if safe_name in done or os.path.exists(file_path):
            done.add(safe_name)
            continue
        try:
            df = pro.moneyflow(ts_code=ts_code, start_date=START_DATE, end_date=END_DATE)
            if df is not None and not df.empty:
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                done.add(safe_name)
        except Exception:
            failed_stocks_money.append(ts_code)
        time.sleep(SLEEP_STOCK)
        if (i + 1) % FLUSH_EVERY == 0:
            save_progress(tracker, done)
    save_progress(tracker, done)
    if failed_stocks_money:
        print(f"   资金流向下载失败 ({len(failed_stocks_money)}/{len(codes)})")
    else:
        print("   个股资金流向完成")


# ╔══════════════════════════════════════════════════════════════╗
# ║      三、宏观经济数据：PMI / CPI / M2 / 国债 / 社融          ║
# ║      均为月度低频数据，通过 SLEEP_FAST 控制请求间隔            ║
# ╚══════════════════════════════════════════════════════════════╝

# ── 步8：PMI（制造业 + 非制造业 + 综合）────────────
# cn_pmi 接口一次性返回全部三类 PMI 数据（65 列）
# 制造业：PMI01xxxx（36 列），非制造业：PMI02xxxx（22 列），综合：PMI030000（1 列）
# 输出：cn_pmi.csv / cn_nmi_pmi.csv / cn_cpmi.csv
if 8 in selected:
    print("8. PMI（制造业 / 非制造业 / 综合）...")

    # 8a. 下载 cn_pmi（包含全部三类 PMI 明细）
    pmi_file = os.path.join(ROOT_DIR, "cn_pmi.csv")
    if not os.path.exists(pmi_file):
        df = pro.cn_pmi(start_date=START_DATE[:4]+'01', end_date=END_DATE[:4]+'12')
        df.to_csv(pmi_file, index=False, encoding='utf-8-sig')
        print(f"   已保存 cn_pmi: {len(df)} 条 × {len(df.columns)} 列")
        time.sleep(SLEEP_FAST)
    else:
        print("   cn_pmi.csv 已存在，跳过下载")

    # 8b. 提取非制造业PMI（PMI02xxxx 列）
    nmi_file = os.path.join(ROOT_DIR, "cn_nmi_pmi.csv")
    if not os.path.exists(nmi_file):
        df_pmi = pd.read_csv(pmi_file)
        df_pmi = df_pmi[(df_pmi['MONTH'] >= 202201) & (df_pmi['MONTH'] <= 202512)]
        nmi_cols = ['MONTH'] + [c for c in df_pmi.columns if c.startswith('PMI02')]
        df_nmi = df_pmi[nmi_cols].sort_values('MONTH')
        df_nmi.to_csv(nmi_file, index=False, encoding='utf-8-sig')
        print(f"   已保存 cn_nmi_pmi: {len(df_nmi)} 条 × {len(nmi_cols)-1} 个指标")
    else:
        print("   cn_nmi_pmi.csv 已存在，跳过提取")

    # 8c. 提取综合PMI（PMI030000 列）
    cpmi_file = os.path.join(ROOT_DIR, "cn_cpmi.csv")
    if not os.path.exists(cpmi_file):
        df_pmi = pd.read_csv(pmi_file)
        df_pmi = df_pmi[(df_pmi['MONTH'] >= 202201) & (df_pmi['MONTH'] <= 202512)]
        df_cpmi = df_pmi[['MONTH', 'PMI030000']].sort_values('MONTH')
        df_cpmi.to_csv(cpmi_file, index=False, encoding='utf-8-sig')
        print(f"   已保存 cn_cpmi: {len(df_cpmi)} 条")
    else:
        print("   cn_cpmi.csv 已存在，跳过提取")
    time.sleep(SLEEP_FAST)

# ── 步9：CPI ───────────────────────────────────────
# 中国居民消费价格指数（同比、环比），衡量通胀水平
# 输出：cn_cpi.csv
if 9 in selected:
    print("9. CPI...")
    cpi_file = os.path.join(ROOT_DIR, "cn_cpi.csv")
    if not os.path.exists(cpi_file):
        df = pro.cn_cpi(start_date=START_DATE[:4]+'01', end_date=END_DATE[:4]+'12')
        df.to_csv(cpi_file, index=False, encoding='utf-8-sig')
        print(f"   已保存 {len(df)} 条")
    else:
        print("   已存在，跳过")
    time.sleep(SLEEP_FAST)

# ── 步10：M2货币供应量 ─────────────────────────────
# 广义货币 M2 同比增速，流动性指标
# 输出：cn_m.csv
if 10 in selected:
    print("10. M2货币供应量...")
    m2_file = os.path.join(ROOT_DIR, "cn_m.csv")
    if not os.path.exists(m2_file):
        df = pro.cn_m(start_date=START_DATE[:4]+'01', end_date=END_DATE[:4]+'12')
        df.to_csv(m2_file, index=False, encoding='utf-8-sig')
        print(f"   已保存 {len(df)} 条")
    else:
        print("   已存在，跳过")
    time.sleep(SLEEP_FAST)

# ── 步11：10年期国债收益率 ─────────────────────────
# 中债国债即期收益率曲线（yc_cb），逐日查询 curve_term=10.0 的 10 年期利率
# 输出：cn_10y_bond.csv（约 970 条，按交易日逐日获取）
if 11 in selected:
    print("11. 10年期国债收益率（逐交易日获取，约 5 分钟）...")
    bond_file = os.path.join(ROOT_DIR, "cn_10y_bond.csv")
    if not os.path.exists(bond_file):
        try:
            # 读取交易日历获取全部交易日
            cal_file = os.path.join(ROOT_DIR, "trade_cal.csv")
            if not os.path.exists(cal_file):
                print("   需要交易日历，请先运行步1")
            else:
                cal = pd.read_csv(cal_file)
                cal_dates = cal[cal['is_open'] == 1]['cal_date'].astype(str).tolist()
                cal_dates = [d for d in cal_dates if '2022' <= d[:4] <= '2025']
                all_bond = []
                for d in tqdm(cal_dates, desc="   获取国债收益率"):
                    df = pro.yc_cb(start_date=d, end_date=d, curve_type='0')
                    if df is not None and not df.empty:
                        df_10y = df[df['curve_term'] == 10.0][['trade_date', 'yield']].copy()
                        all_bond.append(df_10y)
                    time.sleep(SLEEP_FAST)
                if all_bond:
                    df_bond = pd.concat(all_bond).drop_duplicates('trade_date').sort_values('trade_date')
                    df_bond.to_csv(bond_file, index=False, encoding='utf-8-sig')
                    print(f"   已保存 {len(df_bond)} 条（{df_bond['trade_date'].min()} ~ {df_bond['trade_date'].max()}）")
                else:
                    print("   API 返回空数据")
        except Exception as e:
            print(f"   获取国债收益率失败: {e}")
    else:
        print("   已存在，跳过")
    time.sleep(SLEEP_FAST)

# ── 步12：社融规模 ─────────────────────────────────
# 中国社会融资规模（sf_month），含当月增量、累计增量、期末存量
# 输出：social_finance.csv
if 12 in selected:
    print("12. 社融规模...")
    sf_file = os.path.join(ROOT_DIR, "social_finance.csv")
    if not os.path.exists(sf_file):
        try:
            all_sf = []
            for y in range(2022, 2026):
                for m in range(1, 13):
                    month = f'{y}{m:02d}'
                    df = pro.sf_month(m=month)
                    if df is not None and not df.empty:
                        all_sf.append(df)
                    time.sleep(SLEEP_FAST)
            if all_sf:
                df_sf = pd.concat(all_sf).sort_values('month')
                df_sf.to_csv(sf_file, index=False, encoding='utf-8-sig')
                print(f"   已保存 {len(df_sf)} 条（{df_sf['month'].min()} ~ {df_sf['month'].max()}）")
            else:
                print("   API 返回空数据")
        except Exception as e:
            print(f"   获取社融规模失败: {e}")
    else:
        print("   已存在，跳过")
    time.sleep(SLEEP_FAST)


# ╔══════════════════════════════════════════════════════════════╗
# ║           四、指数行情数据：风格指数 / 申万行业指数           ║
# ║      指数日线用于市场风格分析、行业轮动与基准比较             ║
# ╚══════════════════════════════════════════════════════════════╝

# ── 步13：风格指数日线 ─────────────────────────────
# 5 个核心宽基/风格指数：上证50(大盘价值)、沪深300(大盘均衡)、
#   中证500(中盘)、深证成指、创业板指(小盘成长)
# 输出：style_index/{code}_{name}.csv（5 个文件）
if 13 in selected:
    print("13. 风格指数日线...")
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

# ── 步14：申万行业指数日线（自建）──────────────────
# 因 sw_daily 接口权限不足，改为从成份股日线+市值自建行业指数
# 方法：流通市值加权，基期 1000，逐日累计
# 输出：sw_index/{code}.csv（31 个文件，含 o/h/l/c/vol/amount）
if 14 in selected:
    print("14. 申万行业指数日线（成份股自建，约 10-20 分钟）...")
    sw_dir = os.path.join(ROOT_DIR, "sw_index")
    os.makedirs(sw_dir, exist_ok=True)
    tracker = os.path.join(sw_dir, "_progress.txt")
    done = load_progress(tracker)
    cnt = len(done)

    # 预加载交易日历
    cal = pd.read_csv(os.path.join(ROOT_DIR, "trade_cal.csv"))
    trade_dates = sorted(cal[cal['is_open'] == 1]['cal_date'].astype(str).tolist())
    trade_dates = [d for d in trade_dates if '2022' <= d[:4] <= '2025']

    for i, code in enumerate(tqdm(sw_level1_codes, desc="   自建行业指数", initial=cnt, total=len(sw_level1_codes))):
        safe_name = code.replace('.', '_')
        file_path = os.path.join(sw_dir, f"{safe_name}.csv")
        if safe_name in done or os.path.exists(file_path):
            done.add(safe_name)
            continue

        try:
            # 读取该行业的成份股列表（含 in_date/out_date 用于按日筛选）
            member_file = os.path.join(ROOT_DIR, "index_member", f"{safe_name}.csv")
            if not os.path.exists(member_file):
                failed_sw_index.append(code)
                continue
            members = pd.read_csv(member_file, dtype={'ts_code': str})

            # 构建每只股票的有效日期范围
            stock_dates = {}  # {ts_code: set of valid dates}
            for _, row in members.iterrows():
                ts = row['ts_code']
                if ts not in stock_dates:
                    stock_dates[ts] = []
                in_d = str(row.get('in_date', ''))[:8] if pd.notna(row.get('in_date')) else '20220101'
                out_d = str(row.get('out_date', ''))[:8] if pd.notna(row.get('out_date')) else '20251231'
                stock_dates[ts].append((in_d, out_d))

            # 预加载成份股日线 + 市值（仅加载在 trade_dates 范围内有成分资格的股票）
            stock_data = {}  # {ts_code: DataFrame with trade_date, ret, mv}
            all_codes = list(stock_dates.keys())
            for ts_code in all_codes:
                sname = ts_code.replace('.', '_')
                daily_f = os.path.join(ROOT_DIR, "daily", f"{sname}.csv")
                basic_f = os.path.join(ROOT_DIR, "daily_basic", f"{sname}.csv")
                if not os.path.exists(daily_f):
                    continue
                df_d = pd.read_csv(daily_f, dtype={'trade_date': str})
                df_d = df_d[['trade_date', 'close', 'pct_chg']].copy()
                if os.path.exists(basic_f):
                    df_b = pd.read_csv(basic_f, dtype={'trade_date': str})
                    if 'total_mv' in df_b.columns:
                        df_d = df_d.merge(df_b[['trade_date', 'total_mv']], on='trade_date', how='left')
                    else:
                        df_d['total_mv'] = np.nan
                else:
                    df_d['total_mv'] = np.nan
                df_d['ret'] = df_d['pct_chg'].fillna(0) / 100.0
                df_d.set_index('trade_date', inplace=True)
                stock_data[ts_code] = df_d

            if not stock_data:
                failed_sw_index.append(code)
                continue

            # 按交易日计算市值加权行业收益率
            rows = []
            for d in trade_dates:
                day_ret = 0.0
                day_mv_sum = 0.0
                active_count = 0

                # 筛选当日有效的成份股
                active_stocks = []
                for ts_code in all_codes:
                    for in_d, out_d in stock_dates.get(ts_code, []):
                        if in_d <= d <= out_d:
                            active_stocks.append(ts_code)
                            break

                for ts_code in active_stocks:
                    if ts_code in stock_data and d in stock_data[ts_code].index:
                        row = stock_data[ts_code].loc[d]
                        ret = row['ret'] if pd.notna(row['ret']) else 0.0
                        mv = row['total_mv'] if pd.notna(row['total_mv']) else 0.0
                        day_ret += ret * mv
                        day_mv_sum += mv
                        active_count += 1

                pct = (day_ret / day_mv_sum * 100) if day_mv_sum > 0 else (day_ret / active_count * 100 if active_count > 0 else 0)
                rows.append({'trade_date': d, 'pct_chg': pct, 'n_stocks': active_count})

            df_idx = pd.DataFrame(rows)
            if len(df_idx) > 0:
                # 以 1000 为基期，逐日累计
                df_idx['index'] = 1000 * (1 + df_idx['pct_chg'] / 100).cumprod()
                df_idx.to_csv(file_path, index=False, encoding='utf-8-sig')
                done.add(safe_name)
            else:
                failed_sw_index.append(code)

        except Exception as e:
            print(f"   {code} 失败: {e}")
            failed_sw_index.append(code)

        if (i + 1) % FLUSH_EVERY == 0:
            save_progress(tracker, done)
    save_progress(tracker, done)
    if failed_sw_index:
        print(f"   申万行业指数失败 ({len(failed_sw_index)}/{len(sw_level1_codes)}): {failed_sw_index}")
    else:
        print(f"   全部 {len(sw_level1_codes)} 个行业指数完成")


# ╔══════════════════════════════════════════════════════════════╗
# ║                      下载结果汇总                            ║
# ╚══════════════════════════════════════════════════════════════╝

print("\n" + "=" * 50)
print("数据获取完成，结果汇总：")
print(f"  数据保存目录: {os.path.abspath(ROOT_DIR)}")

def report(name, failed_list, total):
    """单项汇总：成功/失败数"""
    ok = total - len(failed_list)
    if failed_list:
        print(f"  {name}: {ok}/{total} 成功, {len(failed_list)} 失败")
    else:
        print(f"  {name}: {total}/{total} 全部成功")

_stock_total = len(codes) if need_stock_basic else 0
if 4 in selected:
    report("个股日线",        failed_stocks_daily,  _stock_total)
if 5 in selected:
    report("复权因子",         failed_stocks_adj,    _stock_total)
if 6 in selected:
    report("daily_basic",    failed_stocks_basic,  _stock_total)
if 7 in selected:
    report("资金流向",         failed_stocks_money,  _stock_total)
if 3 in selected:
    report("行业成分股",       failed_members,       len(sw_level1_codes))
if 14 in selected:
    report("申万行业指数日线", failed_sw_index,      len(sw_level1_codes))
print("=" * 50)
