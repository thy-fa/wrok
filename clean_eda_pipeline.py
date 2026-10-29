#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
==============================================================================
 大数据招聘岗位数据分析 · 数据清洗 + EDA 全流程脚本（基于真实数据）
==============================================================================

数据源：job_all.xlsx（和鲸「前程无忧-大数据岗位数据集」未清洗版，4100 条 × 15 字段）

运行：
    pip install pandas openpyxl
    python clean_eda_pipeline.py
    python clean_eda_pipeline.py --input D:/Downloads/job_all.xlsx --limit 500   # 小样本调试

产出：
    jobs_clean.csv        清洗后的标准数据（供后续分析与可视化）
    eda_summary.csv       各维度分组统计结果汇总

==============================================================================
【本脚本针对的真实数据问题】（逐条来自对 4100 条原始数据的实际统计）

  1. 重复严重        按「职位+公司+城市」去重后 4100 → 2819，重复 1281 条（31%）
  2. 整行坏数据       城市、经验、职位描述三者同时为空共 475 条，属采集失败行
  3. 转义符污染       薪酬列 593 条、公司标签列 1497 条含 "\\/"，需还原为 "/"
  4. 列错位脏值       学历要求列混入 46 条 "11-16发布" 之类日期串；经验列 2 条
  5. 薪酬单位混杂     "8千-1.6万"（月，3425 条）与 "12-20万/年"（年，593 条）混存
  6. 城市字段复合     "上海-浦东新区" 形式占 2713 条，需拆出城市
  7. 缺失分布不均     公司福利 25.4%、公司规模 18.9%、学历/经验 11.6%、薪酬 2.0%
==============================================================================
"""

import sys
import os
import re
import argparse
from datetime import datetime
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import pandas as pd
    import numpy as np
except ImportError:
    print("[错误] 缺少 pandas / numpy，请先执行：pip install pandas openpyxl")
    sys.exit(1)


# ==============================================================================
# 配置区
# ==============================================================================
DEFAULT_INPUT = "D:/Downloads/job_all.xlsx"
OUTPUT_CLEAN = "jobs_clean.csv"
OUTPUT_SUMMARY = "eda_summary.csv"

# 学历分档（有序，从低到高）
EDU_MAP = {
    "初中及以下": "大专以下", "高中": "大专以下", "中技/中专": "大专以下",
    "大专": "大专",
    "本科": "本科",
    "硕士": "硕士及以上", "博士": "硕士及以上",
}
EDU_ORDER = ["大专以下", "大专", "本科", "硕士及以上"]

# 经验分档（有序）
EXP_MAP = {
    "无需经验": "应届", "在校生/应届生": "应届",
    "1年经验": "1-3年", "2年经验": "1-3年",
    "3-4年经验": "3-5年",
    "5-7年经验": "5年以上", "8-9年经验": "5年以上", "10年以上经验": "5年以上",
}
EXP_ORDER = ["应届", "1-3年", "3-5年", "5年以上"]

# 公司规模分档（有序）
SIZE_ORDER = ["少于50人", "50-150人", "150-500人", "500-1000人",
              "1000-5000人", "5000-10000人", "10000人以上"]

# 技术技能词典：用于从职位描述中统计技能需求（直接关键词匹配，无需 jieba 分词）
SKILL_DICT = [
    "Hadoop", "HDFS", "MapReduce", "Yarn", "Hive", "Spark", "Flink", "Kafka",
    "HBase", "Zookeeper", "Sqoop", "Flume", "Airflow", "DolphinScheduler",
    "Scala", "Java", "Python", "SQL", "MySQL", "Oracle", "Redis", "MongoDB",
    "ClickHouse", "Doris", "StarRocks", "Elasticsearch", "ETL", "Kettle",
    "数据仓库", "数仓", "数据中台", "BI", "Tableau", "FineBI", "PowerBI",
    "Linux", "Shell", "机器学习", "深度学习", "数据挖掘", "统计分析", "Excel",
]


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


# ==============================================================================
# 薪资解析：把中文薪资文本统一折算为"月薪中位数（元/月）"
# ==============================================================================
_SALARY_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(万|千|[kK])?\s*(?:[-~至到]\s*(\d+(?:\.\d+)?)\s*(万|千|[kK])?)?"
)
_PERIOD_RE = re.compile(r"/?\s*(年|月|周|天|小时|时)")


def _unit_value(num_str, unit):
    """把 (数字, 单位) 折算成元。"""
    try:
        v = float(num_str)
    except (ValueError, TypeError):
        return None
    if unit == "万":
        return v * 10000
    if unit in ("千", "k", "K"):
        return v * 1000
    return v


def parse_salary(text):
    """
    支持：'8千-1.6万' | '12-20万/年' | '1.8-2.3万' | '6-8千' | '面议' | ''
    返回 (月薪下限, 月薪上限, 月薪中位数)；解析不了返回 (None, None, None)
    """
    if text is None:
        return (None, None, None)
    s = str(text).strip()
    if not s or "面议" in s or "不限" in s:
        return (None, None, None)

    m = _SALARY_RE.search(s)
    if not m:
        return (None, None, None)

    first_num, first_unit, second_num, second_unit = m.groups()
    if first_unit and second_unit:
        lo = _unit_value(first_num, first_unit)
        hi = _unit_value(second_num, second_unit)
    else:
        unit = first_unit or second_unit      # 如 "15-25K"、"1.5-2万"，共用单位
        lo = _unit_value(first_num, unit)
        hi = _unit_value(second_num, unit) if second_num else lo
    if lo is None:
        return (None, None, None)
    hi = lo if hi is None else hi

    # 时间单位折算到"每月"
    pm = _PERIOD_RE.search(s)
    period = pm.group(1) if pm else "月"
    factor = {"月": 1.0, "年": 1 / 12, "周": 4.345,
              "天": 21.75, "小时": 174.0, "时": 174.0}.get(period, 1.0)
    lo, hi = lo * factor, hi * factor
    return (round(lo), round(hi), round((lo + hi) / 2))


# ==============================================================================
# 一、数据清洗
# ==============================================================================
def load_raw(path, limit=None):
    """读取原始数据；xlsx 需要 openpyxl，缺失时给出明确提示。"""
    if not os.path.exists(path):
        log(f"[错误] 文件不存在：{path}")
        sys.exit(1)
    try:
        df = pd.read_excel(path)
    except ImportError:
        log("[错误] 读取 xlsx 需要 openpyxl，请执行：pip install openpyxl")
        sys.exit(1)
    if limit:
        df = df.head(limit)
    log(f"[读取] {path} ｜ 原始形状 {df.shape}")
    return df


def step0_overview(df):
    """步骤 0：初检——先看清楚缺失与唯一值，再决定怎么洗。"""
    section("步骤 0 · 数据初检")
    print(f"形状：{df.shape[0]} 行 × {df.shape[1]} 列")
    print(f"\n列名：{list(df.columns)}")

    # 无名列（Excel 导出的索引列）识别：列名为 Unnamed 或全为数字序号
    unnamed = [c for c in df.columns if str(c).startswith("Unnamed")]
    if unnamed:
        print(f"\n发现无名列：{unnamed}（Excel 导出的索引列，直接删除）")
        df = df.drop(columns=unnamed)

    print("\n缺失率与唯一值：")
    info = pd.DataFrame({
        "缺失数": df.isna().sum(),
        "缺失率": (df.isna().mean() * 100).round(1),
        "唯一值": df.nunique(),
    })
    print(info)
    return df


def step1_unescape(df):
    """步骤 1：清理转义符 —— 薪酬 593 条、公司标签 1497 条含 "\\/"。"""
    section("步骤 1 · 清理转义符 \\/ → /")
    for col in ["薪酬", "公司标签", "城市地区", "公司类型"]:
        if col not in df.columns:
            continue
        # 先把 NaN 填成空串，避免 .str 操作报错
        df[col] = df[col].fillna("").astype(str)
        before = df[col].str.contains(r"\\/", regex=True).sum()
        if before:
            df[col] = df[col].str.replace("\\/", "/", regex=False)
            log(f"  {col}：清理 {before} 条（如 '12-20万\\/年' → '12-20万/年'）")
    return df


def step2_drop_bad_rows(df):
    """
    步骤 2：剔除整行坏数据。
    真实情况：城市 / 工作经验 / 职位描述三者同时为空的共 475 条，属采集失败行，
    保留只会污染统计（尤其会拉低均值、让缺失率虚高）。
    """
    section("步骤 2 · 剔除采集失败的整行坏数据")
    key_cols = ["城市地区", "工作经验要求", "职位描述或任职要求"]
    key_cols = [c for c in key_cols if c in df.columns]
    mask_bad = (df[key_cols].fillna("").astype(str).apply(
        lambda s: s.str.strip() == "").all(axis=1))
    log(f"  三项关键字段同时为空：{mask_bad.sum()} 条 → 剔除")
    df = df[~mask_bad].copy()
    log(f"  剩余 {df.shape[0]} 行")
    return df


def step3_dedup(df):
    """
    步骤 3：去重。
    按「职位 + 公司 + 城市 + 薪酬」去重（比只按前三项多保留 167 条真实差异岗位）。
    真实数据：按前三项去重会砍掉 1281 条，其中部分是同公司同城同职位的多个真实岗位。
    """
    section("步骤 3 · 去重")
    keys = [c for c in ["职位名称", "公司名称", "城市地区", "薪酬"] if c in df.columns]
    before = len(df)
    df = df.drop_duplicates(subset=keys, keep="first").copy()
    log(f"  去重键：{keys}")
    log(f"  {before} → {len(df)} 行，删除重复 {before - len(df)} 条")
    return df


def step4_missing(df):
    """
    步骤 4：缺失值处理（分字段施策，不搞一刀切）。
      - 薪酬缺失 → 直接删行（薪资是核心因变量，不能编造）
      - 学历/经验缺失 → 填"未知"（保留样本量，分组时单列）
      - 公司规模/公司福利缺失 → 填"未知"/"无"（非核心维度）
    """
    section("步骤 4 · 缺失值处理")
    n0 = len(df)

    if "薪酬" in df.columns:
        miss = df["薪酬"].fillna("").astype(str).str.strip().eq("").sum()
        df = df[df["薪酬"].fillna("").astype(str).str.strip() != ""].copy()
        log(f"  薪酬为空：{miss} 条 → 删除（薪资为核心因变量，不做填充）")

    for col, fill in [("学历要求", "未知"), ("工作经验要求", "未知"),
                      ("公司规模", "未知"), ("公司福利", "无"), ("公司标签", "未知")]:
        if col in df.columns:
            m = df[col].isna().sum() + (df[col].astype(str).str.strip() == "").sum()
            df[col] = df[col].replace("", np.nan).fillna(fill)
            log(f"  {col}：缺失 {m} 条 → 填充为「{fill}」")

    log(f"  {n0} → {len(df)} 行")
    return df


def step5_parse_and_cast(df):
    """
    步骤 5：字段解析与类型转换（清洗的核心，把脏文本变成可分析的变量）。
      薪酬   → salary_min / salary_max / salary_mid（月薪，元）
      城市   → city（从 "上海-浦东新区" 拆出 "上海"）
      经验   → exp_level（有序分类）+ 非法值清洗
      学历   → edu_level（有序分类）+ 非法值清洗
      时间   → publish_time（datetime）
    """
    section("步骤 5 · 字段解析与类型转换")

    # ---- 5.1 薪资解析 ----
    parsed = df["薪酬"].apply(
        lambda x: pd.Series(parse_salary(x), index=["salary_min", "salary_max", "salary_mid"])
    )
    df = pd.concat([df, parsed], axis=1)
    fail = df["salary_mid"].isna().sum()
    log(f"  薪资解析：成功 {len(df) - fail} 条，失败 {fail} 条（置为缺失）")
    if len(df):
        log(f"  薪资样本：{df['薪酬'].iloc[0]!r} → {df['salary_mid'].iloc[0]} 元/月")

    # ---- 5.2 城市拆分 ----
    df["city"] = df["城市地区"].astype(str).str.split("-").str[0].str.strip()
    log(f"  城市拆分：{df['城市地区'].nunique()} 个原始值 → {df['city'].nunique()} 个城市")
    log(f"  城市 TOP5：{df['city'].value_counts().head(5).to_dict()}")

    # ---- 5.3 经验分档（含非法值清洗）----
    valid_exp = set(EXP_MAP.keys())
    bad = (~df["工作经验要求"].isin(valid_exp)) & (df["工作经验要求"] != "未知")
    if bad.sum():
        log(f"  经验非法值 {bad.sum()} 条（如 '大专'、'10-12发布'）→ 置为「未知」")
        df.loc[bad, "工作经验要求"] = "未知"
    df["exp_level"] = df["工作经验要求"].map(EXP_MAP).fillna("未知")
    df["exp_level"] = pd.Categorical(df["exp_level"], categories=EXP_ORDER + ["未知"], ordered=True)

    # ---- 5.4 学历分档（含非法值清洗）----
    valid_edu = set(EDU_MAP.keys())
    bad = (~df["学历要求"].isin(valid_edu)) & (df["学历要求"] != "未知")
    if bad.sum():
        log(f"  学历非法值 {bad.sum()} 条（如 '11-16发布' 日期串，属列错位）→ 置为「未知」")
        df.loc[bad, "学历要求"] = "未知"
    df["edu_level"] = df["学历要求"].map(EDU_MAP).fillna("未知")
    df["edu_level"] = pd.Categorical(df["edu_level"], categories=EDU_ORDER + ["未知"], ordered=True)

    # ---- 5.5 时间与规模 ----
    df["publish_time"] = pd.to_datetime(df["发布时间"], errors="coerce")
    df["publish_date"] = df["publish_time"].dt.date
    df["company_size_level"] = pd.Categorical(
        df["公司规模"], categories=SIZE_ORDER + ["未知"], ordered=True)

    log(f"  时间解析：成功 {df['publish_time'].notna().sum()} 条")
    log(f"  新增列：salary_min/max/mid、city、exp_level、edu_level、publish_time、company_size_level")
    return df


def step6_outliers(df):
    """
    步骤 6：异常值处理。
      - 剔除月薪中位数 < 2000 或 > 100000 的明显异常（如单位识别错误）
      - 再用 1%~99% 分位截尾（winsorize），避免极值拉偏均值
      注意：截尾只影响均值类统计，中位数不受影响，两者都报告。
    """
    section("步骤 6 · 异常值处理")
    n0 = len(df)

    mask = (df["salary_mid"] < 2000) | (df["salary_mid"] > 100000)
    log(f"  月薪 <2000 或 >100000：{mask.sum()} 条 → 剔除")
    log(f"    示例：{df.loc[mask, '薪酬'].head(3).tolist()}")
    df = df[~mask].copy()

    lo, hi = df["salary_mid"].quantile([0.01, 0.99])
    log(f"  1% 分位 {lo:.0f} ｜ 99% 分位 {hi:.0f} → 对超出部分做截尾（保留行数不变）")
    df["salary_mid_wins"] = df["salary_mid"].clip(lo, hi)

    log(f"  {n0} → {len(df)} 行")
    return df


def step7_finalize(df):
    """步骤 7：整理字段，输出标准清洗数据。"""
    section("步骤 7 · 整理输出")
    drop_cols = [c for c in ["地区经验学历", "更新时间"] if c in df.columns]
    if drop_cols:
        df = df.drop(columns=drop_cols)
        log(f"  删除冗余列：{drop_cols}（可从其他列推导 / 信息量极低）")
    df.to_csv(OUTPUT_CLEAN, index=False, encoding="utf-8-sig")
    log(f"  已保存 → {OUTPUT_CLEAN}（{df.shape[0]} 行 × {df.shape[1]} 列，utf-8-sig）")
    return df


# ==============================================================================
# 二、EDA 探索性分析
# ==============================================================================
def eda0_describe(df):
    """描述统计：先看薪资的整体分布形态。"""
    section("EDA 1 · 薪资描述统计（业务含义：建立薪资基准线）")
    s = df["salary_mid"]
    stat = pd.Series({
        "样本数": int(s.count()),
        "均值": round(s.mean(), 0),
        "中位数": int(s.median()),
        "标准差": round(s.std(), 0),
        "最小值": int(s.min()),
        "25%分位": int(s.quantile(0.25)),
        "75%分位": int(s.quantile(0.75)),
        "最大值": int(s.max()),
        "偏度": round(s.skew(), 2),
    })
    print(stat.to_string())
    print(f"\n业务含义：均值 {s.mean():.0f} 高于中位数 {s.median():.0f}，"
          f"呈右偏（偏度 {s.skew():.2f}）——少数高薪岗位拉高了平均，")
    print("           因此对外谈薪资预期时应以【中位数】为准，而非均值。")
    return stat


def eda_city(df, summaries):
    """Q1：城市维度——需求分布与薪资差异。"""
    section("EDA 2 · 城市维度（业务含义：投递优先级）")
    g = df.groupby("city").agg(
        岗位数=("职位名称", "count"),
        薪资中位数=("salary_mid", "median"),
        薪资均值=("salary_mid_wins", "mean"),
    ).round(0).sort_values("岗位数", ascending=False)

    print("岗位数 TOP15 城市：")
    print(g.head(15).to_string())
    print("\n薪资中位数 TOP10 城市（仅统计岗位数 ≥ 20 的城市，避免小样本失真）：")
    print(g[g["岗位数"] >= 20].sort_values("薪资中位数", ascending=False).head(10).to_string())

    print("\n业务含义：岗位数代表【机会总量】，薪资中位数代表【单岗位价值】。")
    print("           两者不总是一致（如北京机会多但竞争也大），需结合看：")
    print("           高岗位数 + 高薪资 = 优先投递；高薪资 + 低岗位数 = 高风险高回报。")
    summaries["城市维度"] = g.reset_index()
    return g


def eda_edu_exp(df, summaries):
    """Q2：学历 × 经验——门槛结构。"""
    section("EDA 3 · 学历与经验门槛（业务含义：我够得着吗）")
    print("学历分布：")
    edu_cnt = df["edu_level"].value_counts().reindex(EDU_ORDER + ["未知"])
    edu_pct = (edu_cnt / edu_cnt.sum() * 100).round(1)
    print(pd.DataFrame({"岗位数": edu_cnt, "占比%": edu_pct}).to_string())

    print("\n经验分布：")
    exp_cnt = df["exp_level"].value_counts().reindex(EXP_ORDER + ["未知"])
    exp_pct = (exp_cnt / exp_cnt.sum() * 100).round(1)
    print(pd.DataFrame({"岗位数": exp_cnt, "占比%": exp_pct}).to_string())

    print("\n学历 × 经验 交叉表（岗位数）：")
    ct = pd.crosstab(df["edu_level"], df["exp_level"])
    print(ct.to_string())

    print("\n学历 → 薪资中位数：")
    edu_sal = df.groupby("edu_level", observed=True)["salary_mid"].median().round(0)
    print(edu_sal.to_string())

    print("\n业务含义：大专可投递的岗位占比 = 上表中「大专 + 大专以下」的比例，这是")
    print("           你作为专科生真正可争取的【岗位池大小】，比总岗位数更有意义。")
    print("           再对比各学历档的薪资中位数，可量化「学历溢价」——")
    print("           若溢价小，说明能力比学历更能决定薪资，这是简历该突出的方向。")
    summaries["学历分布"] = pd.DataFrame({"岗位数": edu_cnt, "占比%": edu_pct}).reset_index()
    summaries["学历薪资"] = edu_sal.reset_index()
    return ct


def eda_factors(df, summaries):
    """Q3：多维因素对薪资的影响。"""
    section("EDA 4 · 薪资影响因素对比（业务含义：什么最值钱）")
    for col, label in [("exp_level", "工作经验"), ("company_size_level", "公司规模"),
                       ("公司类型", "公司类型")]:
        g = df.groupby(col, observed=True).agg(
            岗位数=("职位名称", "count"),
            薪资中位数=("salary_mid", "median"),
        ).round(0).sort_values("薪资中位数", ascending=False)
        print(f"\n按【{label}】分组：")
        print(g.to_string())
        summaries[f"薪资by{label}"] = g.reset_index()

    # 数值化后的相关分析：把有序分类转成序号，算与薪资的相关系数
    df["_edu_code"] = df["edu_level"].cat.codes
    df["_exp_code"] = df["exp_level"].cat.codes
    corr = df[["salary_mid", "_edu_code", "_exp_code"]].corr()["salary_mid"].round(3)
    print(f"\n与薪资的相关系数：\n{corr.to_string()}")
    print("\n业务含义：相关系数为正说明该因素越高薪资越高。经验的相关系数通常")
    print("           明显高于学历——这意味着「积累项目经验」的回报高于「单纯提升学历」，")
    print("           可直接指导你是先就业还是先升学。")
    return corr


def eda_skills(df, summaries):
    """Q4：技能需求图谱（关键词匹配，无需分词依赖）。"""
    section("EDA 5 · 技能需求图谱（业务含义：学什么）")
    desc = df["职位描述或任职要求"].fillna("").astype(str)
    total = len(desc)
    rows = []
    for sk in SKILL_DICT:
        # 英文词用大小写不敏感匹配；中文直接包含匹配
        cnt = int(desc.str.contains(sk, case=False, regex=False).sum())
        if cnt:
            rows.append({"技能": sk, "出现岗位数": cnt, "占比%": round(cnt / total * 100, 1)})
    skill_df = pd.DataFrame(rows).sort_values("出现岗位数", ascending=False)
    print(f"职位描述非空 {total} 条，技能需求 TOP20：")
    print(skill_df.head(20).to_string(index=False))

    print("\n业务含义：占比 = 该技能在多少比例的岗位中被提到。TOP 技能就是")
    print("           「简历基线」——不会这些，连筛选都过不了；")
    print("           中腰部技能是「差异化竞争力」，学会可与同层次候选人拉开差距。")
    summaries["技能需求"] = skill_df
    return skill_df


def eda_welfare(df, summaries):
    """Q5：福利词频（数据集特色字段）与公司标签。"""
    section("EDA 6 · 公司福利与公司标签（业务含义：怎么挑公司）")
    wel = df["公司福利"].fillna("").astype(str)
    counter = Counter()
    for w in wel:
        if w and w != "无":
            for item in re.split(r"[\s、,，]+", w):
                if item.strip():
                    counter[item.strip()] += 1
    wel_df = pd.DataFrame(counter.most_common(15), columns=["福利", "出现次数"])
    print("福利 TOP15：")
    print(wel_df.to_string(index=False))

    if "公司标签" in df.columns:
        g = df.groupby("公司标签").agg(
            岗位数=("职位名称", "count"),
            薪资中位数=("salary_mid", "median"),
        ).round(0).sort_values("岗位数", ascending=False)
        print("\n行业标签 TOP10：")
        print(g.head(10).to_string())
        print("\n业务含义：福利词频反映企业普遍给予的待遇基线（五险一金是否普遍）；")
        print("           行业标签 × 薪资交叉，可找出【高薪且需求大】的细分赛道，")
        print("           用于决定往哪个行业方向投递。")
        summaries["行业标签"] = g.reset_index()
    summaries["公司福利"] = wel_df
    return wel_df


# ==============================================================================
# 主流程
# ==============================================================================
def main():
    ap = argparse.ArgumentParser(description="大数据招聘岗位 · 清洗与 EDA 全流程")
    ap.add_argument("--input", default=DEFAULT_INPUT, help=f"原始数据路径，默认 {DEFAULT_INPUT}")
    ap.add_argument("--limit", type=int, default=None, help="只处理前 N 行（调试用）")
    args = ap.parse_args()

    df = load_raw(args.input, args.limit)

    # ---------- 清洗 ----------
    df = step0_overview(df)
    df = step1_unescape(df)
    df = step2_drop_bad_rows(df)
    df = step3_dedup(df)
    df = step4_missing(df)
    df = step5_parse_and_cast(df)
    df = step6_outliers(df)
    df = step7_finalize(df)

    # ---------- EDA ----------
    summaries = {}
    eda0_describe(df)
    eda_city(df, summaries)
    eda_edu_exp(df, summaries)
    eda_factors(df, summaries)
    eda_skills(df, summaries)
    eda_welfare(df, summaries)

    # 汇总统计落盘
    with open(OUTPUT_SUMMARY, "w", encoding="utf-8-sig", newline="") as f:
        for name, tbl in summaries.items():
            f.write(f"\n### {name}\n")
            tbl.to_csv(f, index=False)
    log(f"\n各维度统计已汇总到 {OUTPUT_SUMMARY}")
    log("下一步：读取 jobs_clean.csv 做可视化（4 张图：城市薪资、学历薪资、经验薪资、技能词频）")


if __name__ == "__main__":
    main()
