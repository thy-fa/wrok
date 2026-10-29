"""
大数据招聘岗位数据：清洗 + EDA 探索性分析（教学版）
技术栈：pandas + numpy + re
输入：jobs.csv（采集层原始数据，建议字段见下方说明）
输出：jobs_clean.csv（清洗后）+ 控制台打印 EDA 结果

运行：python clean_eda.py

【预期输入字段】
job_title, company_name, city, salary_text, education,
experience, company_size, industry, skills, job_description, source, crawl_time
（若你的字段命名不同，请相应修改下方列名）
"""

import re
import numpy as np
import pandas as pd


# ===================== 0. 读取原始数据 =====================
RAW_FILE = "jobs.csv"
CLEAN_FILE = "jobs_clean.csv"

df = pd.read_csv(RAW_FILE, encoding="utf-8-sig")
print(f"[读取] 原始数据 {df.shape[0]} 行，{df.shape[1]} 列")
print("原始字段：", list(df.columns))


# ===================== 1. 工具：字段解析函数 =====================
def parse_salary(text):
    """薪资原文 -> (salary_min, salary_max)，统一单位 K/月；无法解析返回 (NaN, NaN)。"""
    if not isinstance(text, str):
        return (np.nan, np.nan)
    s = text.replace(" ", "").strip()
    if ("面议" in s) or (s == ""):
        return (np.nan, np.nan)
    is_wan = "万" in s          # 万 -> 需 ×10 换算为 K
    is_year = "年" in s         # 年薪 -> 需 /12 换算为月
    # 区间：X-Y / X~Y
    m = re.search(r"(\d+\.?\d*)\s*[-~到至]\s*(\d+\.?\d*)", s)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
    else:
        m2 = re.search(r"(\d+\.?\d*)", s)   # 单一数值（含"以上/以下"）
        if not m2:
            return (np.nan, np.nan)
        lo = hi = float(m2.group(1))
    factor = 10 if is_wan else 1
    lo, hi = lo * factor, hi * factor
    if is_year:
        lo, hi = lo / 12, hi / 12
    return (round(lo, 1), round(hi, 1))


def parse_experience(text):
    """经验原文 -> 最低年限（数值）；应届/在校/不限 视为 0；无法解析返回 NaN。"""
    if not isinstance(text, str):
        return np.nan
    s = text.strip()
    if ("应届" in s) or ("在校" in s) or ("不限" in s):
        return 0
    m = re.search(r"(\d+)\s*[-~]\s*(\d+)", s)
    if m:
        return int(m.group(1))
    m2 = re.search(r"(\d+)\s*年以上", s)
    if m2:
        return int(m2.group(1))
    m3 = re.search(r"(\d+)\s*年以内", s)
    if m3:
        return 0
    return np.nan


EDU_MAP = {"学历不限": 0, "不限": 0, "中专": 1, "中技": 1,
           "大专": 2, "本科": 3, "硕士": 4, "研究生": 4, "博士": 5}


def parse_education(text):
    """学历原文 -> 有序数值（0~5），便于按层级比较；未知返回 NaN。"""
    if not isinstance(text, str):
        return np.nan
    s = text.strip()
    for k, v in EDU_MAP.items():
        if k in s:
            return v
    return np.nan


def clean_city(text):
    """从 '城市·区' 中提取城市；无效值返回 '未知'。"""
    if not isinstance(text, str) or text.strip() == "":
        return "未知"
    city = re.split(r"[·\-—/]", text.strip())[0]
    if ("异地" in city) or (len(city) > 6):
        return "未知"
    return city


# ===================== 2. 数据清洗 =====================
# 2.1 去重：先整行去重，再按"岗位+公司+城市+薪资"业务主键去重
df = df.drop_duplicates()
df = df.drop_duplicates(
    subset=["job_title", "company_name", "city", "salary_text"], keep="first")
print(f"[去重] 剩余 {df.shape[0]} 行")

# 2.2 缺失值查看与处理
print("\n[缺失值统计]\n", df.isna().sum())
# 文本类缺失补默认值；技能/描述补空串
df["skills"] = df.get("skills", "").fillna("")
df["job_description"] = df.get("job_description", "").fillna("")
df["education"] = df["education"].fillna("未知")
df["experience"] = df["experience"].fillna("未知")
df["industry"] = df["industry"].fillna("未知")
df["company_size"] = df["company_size"].fillna("未知")

# 2.3 字段解析与类型转换（核心）
df[["salary_min", "salary_max"]] = df["salary_text"].apply(
    lambda x: pd.Series(parse_salary(x)))
df["salary_avg"] = (df["salary_min"] + df["salary_max"]) / 2
df["exp_min"] = df["experience"].apply(parse_experience)
df["edu_level"] = df["education"].apply(parse_education)
df["city_clean"] = df["city"].apply(clean_city)
df["crawl_time"] = pd.to_datetime(df["crawl_time"], errors="coerce")

# 2.4 异常值处理
before = df.shape[0]
# 薪资：保留 0 < 月薪 <= 200K（单位为 K/月），并修正 min>max 的颠倒
df = df[(df["salary_max"] > 0) & (df["salary_max"] <= 200)]
bad = df["salary_min"] > df["salary_max"]
df.loc[bad, ["salary_min", "salary_max"]] = df.loc[bad, ["salary_max", "salary_min"]].values
# 经验：剔除明显异常（<0 或 >30 年）
df = df[(df["exp_min"] >= 0) & (df["exp_min"] <= 30)]
print(f"[异常值] 剔除 {before - df.shape[0]} 行，剩余 {df.shape[0]} 行")

# 保存清洗结果
df.to_csv(CLEAN_FILE, index=False, encoding="utf-8-sig")
print(f"[保存] 清洗后数据 -> {CLEAN_FILE}")


# ===================== 3. 探索性分析 EDA =====================
print("\n===================== EDA =====================")

# 3.1 描述统计
print("\n[1] 数值字段描述统计（业务：整体薪资/经验/学历水位）")
print(df[["salary_min", "salary_max", "salary_avg", "exp_min", "edu_level"]].describe())

# 3.2 岗位需求：城市分布 Top10
print("\n[2] 城市岗位需求量 Top10（业务：识别高需求城市集群）")
print(df["city_clean"].value_counts().head(10))

# 3.3 学历 / 经验分布
print("\n[3] 学历分布（业务：岗位门槛画像）")
print(df["education"].value_counts())
print("\n[4] 经验分布（业务：目标人群定位）")
print(df["experience"].value_counts())

# 3.4 分组统计：城市 vs 平均薪资
print("\n[5] 各城市平均薪资（业务：区域薪资差异，过滤样本<20的城市）")
city_salary = df.groupby("city_clean")["salary_avg"].agg(["count", "mean", "median"])
city_salary = city_salary[city_salary["count"] >= 20].sort_values("mean", ascending=False)
print(city_salary.head(10).round(1))

# 3.5 学历 vs 薪资
print("\n[6] 学历层级 vs 平均薪资（业务：学历溢价）")
edu_salary = df.groupby("edu_level")["salary_avg"].agg(["count", "mean"]).round(1)
print(edu_salary)

# 3.6 经验 vs 薪资
print("\n[7] 经验最低年限 vs 平均薪资（业务：经验溢价）")
exp_salary = df.groupby("exp_min")["salary_avg"].agg(["count", "mean"]).round(1)
print(exp_salary)

# 3.7 行业 vs 薪资 / 需求
print("\n[8] 行业需求与薪资（业务：细分赛道选择）")
ind_salary = df.groupby("industry")["salary_avg"].agg(["count", "mean"])
ind_salary = ind_salary[ind_salary["count"] >= 20].sort_values("count", ascending=False)
print(ind_salary.head(10).round(1))

# 3.8 技能词频 Top20
print("\n[9] 高频技能 Top20（业务：核心技能图谱）")
skill_series = (df["skills"].dropna().str.split(r"[,，、/]").explode()
                .str.strip())
skill_series = skill_series[skill_series != ""]
print(skill_series.value_counts().head(20))

print("\n[完成] EDA 结果已打印，可据此撰写分析报告与可视化。")
