# -*- coding: utf-8 -*-
"""
=============================================================================
大数据招聘岗位数据分析 · 可视化流水线（v2，基于清洗后数据集）
=============================================================================
数据源：清洗后job.xlsx  （3357 条 × 21 字段，前程无忧大数据岗位）
技术栈：pandas（可选） + matplotlib + openpyxl（可选）
输出：4 张图表 PNG -> charts/ 目录

  图1  city_salary.png      城市机会与薪资（柱+折线双轴）
  图2  edu_exp_salary.png   学历 × 经验 薪资矩阵（分组柱状）
  图3  skill_freq.png       高频技能 Top15（横向条形 + 薪资标注）
  图4  salary_dist.png      薪资分布直方图 + 定位线

运行：
    python job_visualization.py
    python job_visualization.py --input "D:/Downloads/清洗后job.xlsx"
    python job_visualization.py --limit 500        # 小样本先跑通
    python job_visualization.py --outdir my_charts

设计说明（为什么这么写）：
  1) 数据读取做了【双引擎】。有 pandas 就用 pandas，没装就走内置的标准库
     xlsx 解析器（zipfile + ElementTree）。这样你第一次拿到脚本不会因为
     "没装 pandas" 就直接跑不了，至少能看到数据读没读对。
  2) 绘图依赖 matplotlib，这个没法降级。但没装时脚本不会崩，会退化为
     打印文本表格 + 导出汇总 CSV，让你先验证数据逻辑对不对。
  3) 所有分组统计都带【样本量门槛】。样本太少的分组（如"硕士+应届生"12 条）
     不参与绘图，否则一个小样本极值会把图带偏，面试时被追问很难解释。
=============================================================================
"""

import os
import re
import sys
import csv
import json
import zipfile
import argparse
from collections import Counter, defaultdict

# ==============================================================================
# 〇、全局配置
# ==============================================================================
# 输入文件候选路径（按顺序查找第一个存在的），避免把个人机器的绝对路径写死
DEFAULT_INPUTS = [
    "清洗后job.xlsx",                 # 当前目录
    os.path.join("data", "清洗后job.xlsx"),   # data 子目录
    r"D:\Downloads\清洗后job.xlsx",   # 常见下载位置
]
DEFAULT_OUTDIR = "charts"

# 分组统计的最小样本量：低于此值不画图（避免小样本极值误导）
MIN_CITY_N = 30      # 城市：少于 30 条不单独成柱
MIN_CELL_N = 20      # 学历×经验交叉单元：少于 20 条不画柱
MIN_SKILL_N = 30     # 技能：提及少于 30 次不进 Top 榜

# 经验档位的人工排序（不能按字符串排，否则"10年以上"会排在"1年"前面）
EXP_ORDER = ["在校生/应届生", "无需经验", "1年经验", "2年经验",
             "3-4年经验", "5-7年经验", "8-9年经验", "10年以上经验"]
# 学历的人工排序
EDU_ORDER = ["大专", "本科", "硕士"]

# 技能关键词表：键是展示名，值是匹配用的关键词（小写）
# 说明：技术词本来就是固定写法，用关键词匹配比 jieba 分词更准、也不需要装依赖
SKILL_DICT = {
    "SQL": ["sql"],
    "Java": ["java"],
    "MySQL": ["mysql"],
    "机器学习": ["机器学习", "算法", "建模"],
    "Python": ["python"],
    "ElasticSearch": ["elasticsearch", "es"],
    "Hadoop": ["hadoop"],
    "Linux": ["linux"],
    "Spark": ["spark"],
    "BI/报表": ["bi", "报表", "tableau", "帆软"],
    "Redis": ["redis"],
    "Hive": ["hive"],
    "Kafka": ["kafka"],
    "HBase": ["hbase"],
    "ClickHouse": ["clickhouse"],
    "数据仓库": ["数据仓库", "数仓"],
    "Flink": ["flink"],
    "ETL": ["etl"],
    "Shell": ["shell"],
    "MongoDB": ["mongodb"],
    "数据治理": ["数据治理", "数据质量"],
    "Docker/K8s": ["docker", "k8s", "kubernetes"],
    "Scala": ["scala"],
}

# 配色（统一视觉，作品集里四张图放一起才协调）
C_MAIN = "#0b63ce"    # 主色蓝
C_ACCENT = "#e8743b"  # 强调橙
C_TEAL = "#0f9d8a"    # 辅助青
C_PURPLE = "#7b5ea7"  # 辅助紫
C_GRAY = "#9aa5b1"    # 弱化灰


# ==============================================================================
# 一、中文字体设置（matplotlib 最常见的坑，单独封装）
# ==============================================================================
def setup_chinese_font():
    """
    让 matplotlib 正确显示中文。

    常见现象：图中所有中文变成"□□□"方框。
    根因：matplotlib 默认字体不含中文字形，且它不会自动回退到系统字体。

    本函数做两件事：
      1) 从系统已安装字体里挑一个真正存在的中文字体，避免"名字写了但没装"；
      2) 关闭 unicode_minus，否则负号也会变成方框（画相关系数/差异值时必踩）。
    """
    import matplotlib
    matplotlib.use("Agg")           # 无界面环境（服务器/IDE）也能保存图片
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    # 候选字体按优先级排列：Windows 常见 -> macOS -> Linux
    candidates = ["Microsoft YaHei", "SimHei", "SimSun", "DengXian",
                  "PingFang SC", "Heiti SC", "Arial Unicode MS",
                  "Noto Sans CJK SC", "Source Han Sans SC", "WenQuanYi Zen Hei"]

    # 取系统里真实存在的字体名集合
    available = {f.name for f in font_manager.fontManager.ttflist}
    picked = [f for f in candidates if f in available]

    if picked:
        plt.rcParams["font.sans-serif"] = picked
        print(f"[字体] 已选中文字体：{picked[0]}")
    else:
        # 一个都没找到：仍然按候选顺序设置，matplotlib 会尝试回退
        plt.rcParams["font.sans-serif"] = candidates
        print("[字体][警告] 未在系统中找到常见中文字体，图中可能显示方框。")
        print("           Windows 建议安装「微软雅黑」；或手动指定字体文件路径：")
        print("           from matplotlib import font_manager")
        print("           font_manager.fontManager.addfont('C:/Windows/Fonts/msyh.ttc')")

    plt.rcParams["axes.unicode_minus"] = False   # 修复负号显示为方框
    plt.rcParams["figure.dpi"] = 120             # 屏幕预览清晰度
    plt.rcParams["savefig.dpi"] = 200            # 存盘清晰度（网页/简历够用）
    plt.rcParams["savefig.bbox"] = "tight"       # 防止标签被裁掉
    return plt


# ==============================================================================
# 二、数据读取（双引擎：pandas 优先，标准库兜底）
# ==============================================================================
def read_table_pandas(path, limit=None):
    """引擎 A：pandas 读取（需 pandas + openpyxl）。返回 (表头list, 数据list-of-dict)。"""
    import pandas as pd
    df = pd.read_excel(path)
    df.columns = [str(c).strip() for c in df.columns]
    if limit:
        df = df.head(limit)
    df = df.fillna("")
    rows = df.astype(str).to_dict("records")
    return list(df.columns), rows


def read_table_stdlib(path, limit=None):
    """
    引擎 B：纯标准库解析 xlsx（无需任何第三方库）。

    原理：xlsx 本质是一个 zip 包，里面是 XML。
      xl/sharedStrings.xml  存放所有字符串（单元格用下标引用它）
      xl/worksheets/sheet1.xml  存放单元格的引用与值
    用 zipfile + ElementTree 就能读出来。这也是面试可以讲的一个点。
    """
    from xml.etree import ElementTree as ET
    NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    NSR = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

    def col_to_idx(ref):
        """把 Excel 列标 'AB12' 转成从 0 开始的列下标。"""
        m = re.match(r"([A-Z]+)", ref)
        n = 0
        for ch in m.group(1):
            n = n * 26 + (ord(ch) - 64)
        return n - 1

    z = zipfile.ZipFile(path)
    # 1) 共享字符串池
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall(f"{NS}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{NS}t")))
    # 2) 定位第一个工作表
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid2t = {r.get("Id"): r.get("Target") for r in rels}
    sheet_path = None
    for sh in wb.iter(f"{NS}sheet"):
        tgt = rid2t[sh.get(f"{NSR}id")]
        sheet_path = tgt if tgt.startswith("xl/") else "xl/" + tgt.lstrip("/")
        break
    # 3) 逐行读单元格
    grid = []
    rroot = ET.fromstring(z.read(sheet_path))
    for row in rroot.iter(f"{NS}row"):
        cells = {}
        for c in row.findall(f"{NS}c"):
            t = c.get("t")
            v = c.find(f"{NS}v")
            isel = c.find(f"{NS}is")
            if t == "s" and v is not None:            # 共享字符串
                val = shared[int(v.text)]
            elif t == "inlineStr" and isel is not None:  # 内联字符串
                val = "".join(x.text or "" for x in isel.iter(f"{NS}t"))
            elif v is not None:                       # 数字 / 日期序列值
                val = v.text
            else:
                val = ""
            idx = col_to_idx(c.get("r")) if c.get("r") else len(cells)
            cells[idx] = val
        grid.append(cells)

    if not grid:
        return [], []
    width = max((max(r.keys()) + 1) if r else 0 for r in grid)
    table = [[r.get(i, "") for i in range(width)] for r in grid]
    header = [h.strip() for h in table[0]]
    body = table[1:]
    if limit:
        body = body[:limit]
    rows = [dict(zip(header, r)) for r in body]
    return header, rows


def load_data(path, limit=None):
    """按可用性自动选择读取引擎，返回 list-of-dict。"""
    if not os.path.exists(path):
        sys.exit(f"[失败] 找不到数据文件：{path}\n       请用 --input 指定正确路径。")
    try:
        header, rows = read_table_pandas(path, limit)
        engine = "pandas"
    except ImportError:
        header, rows = read_table_stdlib(path, limit)
        engine = "标准库（未装 pandas/openpyxl，功能正常）"
    except Exception as e:                      # pandas 读失败也退回标准库
        print(f"[提示] pandas 读取失败（{e}），改用标准库解析。")
        header, rows = read_table_stdlib(path, limit)
        engine = "标准库（pandas 读取异常，已回退）"
    print(f"[读取] {os.path.basename(path)} ｜ 引擎 {engine} ｜ {len(rows)} 行 × {len(header)} 列")
    return header, rows


# ==============================================================================
# 三、字段标准化：把 21 个原始字段整理成分析用的“宽表记录”
# ==============================================================================
def to_number(s):
    """安全转数字，失败返回 None（不要用 float() 裸转，遇到空串会抛异常）。"""
    try:
        v = float(str(s).strip())
        return v
    except Exception:
        return None


def clean_text(s):
    """清洗文本：去首尾空白 + 修复转义符。

    这份数据里公司标签/经验列存在 '在校生\\/应届生' 这种转义写法，
    不处理的话同一个值会被当成两个类别，分组统计直接错。
    """
    s = str(s or "").strip()
    return s.replace("\\/", "/")


def build_records(rows):
    """
    把原始行整理成分析记录列表。核心是【薪资口径统一】。

    这份数据的薪资有两种写法，且互斥（月薪有值则年薪为空，反之亦然）：
      - 月薪最小值 / 月薪最大值   （2860 条，单位：元/月）
      - 最低年薪   / 最高年薪     （497 条， 单位：元/年）
    不统一就作图，等于把年薪当成月薪画，图会离谱到一眼假。
    统一口径：一律折算为【月薪中位数 = (下限+上限)/2】。
    """
    recs = []
    skipped = 0
    for r in rows:
        lo = to_number(r.get("月薪最小值", ""))
        hi = to_number(r.get("月薪最大值", ""))
        if lo and hi and lo > 0:
            mid = (lo + hi) / 2
        else:
            ylo = to_number(r.get("最低年薪", ""))
            yhi = to_number(r.get("最高年薪", ""))
            if ylo and yhi and ylo > 0:
                mid = (ylo + yhi) / 2 / 12      # 年薪 -> 月薪
            else:
                skipped += 1
                continue                        # 两个口径都没有，无法参与薪资分析
        recs.append({
            "city": clean_text(r.get("城市", "")),
            "edu": clean_text(r.get("学历要求", "")),
            "exp": clean_text(r.get("工作经验要求", "")),
            "ctype": clean_text(r.get("公司类型", "")),
            "scale": clean_text(r.get("公司规模", "")),
            "desc": clean_text(r.get("职位描述或任职要求", "")).lower(),
            "mid": float(mid),
        })
    print(f"[整理] 有效薪资样本 {len(recs)} 条，因薪资缺失剔除 {skipped} 条")
    return recs


def median(xs):
    """中位数（不依赖 numpy，避免多装一个库）。"""
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


# ==============================================================================
# 四、图1：城市机会与薪资（柱 + 折线双轴）
# ==============================================================================
def chart_city_salary(plt, recs, outdir):
    """
    为什么要双轴：
      岗位数（机会量）和薪资（价值）单位不同、量级不同，画在一根轴上会互相压扁。
      双轴才能让"岗位最多的城市 ≠ 薪资最高的城市"这个结论一眼看出来。
    """
    by = defaultdict(list)
    for r in recs:
        if r["city"]:
            by[r["city"]].append(r["mid"])
    # 样本量门槛 + 取岗位数前 15
    stat = [(c, len(v), median(v)) for c, v in by.items() if len(v) >= MIN_CITY_N]
    stat.sort(key=lambda t: -t[1])
    stat = stat[:15]
    if not stat:
        print("[跳过] 图1：没有满足样本量门槛的城市。")
        return None

    cities = [s[0] for s in stat]
    counts = [s[1] for s in stat]
    meds = [s[2] / 1000 for s in stat]          # 转成 K，轴标签更短

    fig, ax1 = plt.subplots(figsize=(12, 5.6))
    ax1.bar(cities, counts, color=C_MAIN, alpha=.85, label="岗位数量")
    ax1.set_ylabel("岗位数量（条）", color=C_MAIN, fontsize=12)
    ax1.set_xlabel("城市")
    ax1.tick_params(axis="y", labelcolor=C_MAIN)
    ax1.tick_params(axis="x", rotation=30)
    for lbl in ax1.get_xticklabels():
        lbl.set_ha("right")

    ax2 = ax1.twinx()                            # 共享 X 轴，新增右侧 Y 轴
    ax2.plot(cities, meds, color=C_ACCENT, marker="o",
             linewidth=2.4, markersize=6, label="月薪中位数")
    ax2.set_ylabel("月薪中位数（K/月）", color=C_ACCENT, fontsize=12)
    ax2.tick_params(axis="y", labelcolor=C_ACCENT)
    # 每个点标数值，避免读者去猜刻度
    for i, v in enumerate(meds):
        ax2.annotate(f"{v:.1f}", (i, v), textcoords="offset points",
                     xytext=(0, 8), ha="center", fontsize=9, color=C_ACCENT)

    ax1.set_title("图1 ｜ 各城市岗位需求量与薪资中位数（样本≥%d 条）" % MIN_CITY_N,
                  fontsize=14, fontweight="bold")
    ax1.grid(axis="y", alpha=.25)
    fig.tight_layout()
    path = os.path.join(outdir, "city_salary.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"[保存] {path}")
    return path


# ==============================================================================
# 五、图2：学历 × 经验 薪资矩阵（分组柱状）
# ==============================================================================
def chart_edu_exp(plt, recs, outdir):
    """
    为什么用分组柱状而不是折线：
      经验是【有序分类】不是连续数值（"3-4年"不是 3.5），折线会暗示线性关系，
      而真实的薪资跃迁是台阶式的（0年→1年翻倍，1年→3年只涨一点）。柱状更诚实。
    """
    cell = defaultdict(list)
    for r in recs:
        if r["edu"] in EDU_ORDER and r["exp"] in EXP_ORDER:
            cell[(r["exp"], r["edu"])].append(r["mid"])

    # 只保留样本量足够的单元格
    data = {}
    for e in EXP_ORDER:
        for d in EDU_ORDER:
            v = cell.get((e, d), [])
            if len(v) >= MIN_CELL_N:
                data[(e, d)] = (median(v), len(v))

    exps = [e for e in EXP_ORDER if any((e, d) in data for d in EDU_ORDER)]
    if not exps:
        print("[跳过] 图2：没有满足样本量门槛的学历×经验组合。")
        return None

    fig, ax = plt.subplots(figsize=(12, 5.8))
    x = range(len(exps))
    width = 0.26                                  # 每组 3 根柱，总宽 0.78
    colors = {"大专": C_ACCENT, "本科": C_MAIN, "硕士": C_PURPLE}

    for i, d in enumerate(EDU_ORDER):
        vals, ns = [], []
        for e in exps:
            if (e, d) in data:
                m, n = data[(e, d)]
                vals.append(m / 1000)
                ns.append(n)
            else:
                vals.append(0)                    # 样本不足 -> 不画（高度 0）
                ns.append(0)
        offset = [xi + (i - 1) * width for xi in x]
        bars = ax.bar(offset, vals, width=width, label=d, color=colors[d], alpha=.9)
        # 柱顶标注样本量，让"这个数可不可信"一目了然
        for b, n, v in zip(bars, ns, vals):
            if n:
                ax.text(b.get_x() + b.get_width() / 2, v + .4,
                        f"n={n}", ha="center", fontsize=8, color="#52606d")

    ax.set_xticks(list(x))
    ax.set_xticklabels(exps)
    ax.set_ylabel("月薪中位数（K/月）")
    ax.set_xlabel("工作经验要求")
    ax.set_title("图2 ｜ 学历 × 经验 的薪资矩阵（柱顶 n=样本量，样本<%d 不展示）" % MIN_CELL_N,
                 fontsize=14, fontweight="bold")
    ax.legend(title="学历要求")
    ax.grid(axis="y", alpha=.25)
    fig.tight_layout()
    path = os.path.join(outdir, "edu_exp_salary.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"[保存] {path}")
    return path


# ==============================================================================
# 六、图3：高频技能 Top15（横向条形 + 薪资标注）
# ==============================================================================
def chart_skill_freq(plt, recs, outdir, global_median):
    """
    为什么用横向条形：技能名是中文且长短不一，竖向条形会让 X 轴标签挤成一团，
    横向条形从长到短排列，既是排名也是频次对比，读起来最省力。

    颜色语义：深蓝 = 该技能岗位薪资高于全局中位（学了有溢价）；
              浅灰 = 低于全局中位（属于基础盘，不写进简历就吃亏，写了也不加分）。
    """
    cnt = Counter()
    sal = defaultdict(list)
    for r in recs:
        d = r["desc"]
        for name, kws in SKILL_DICT.items():
            if any(k in d for k in kws):
                cnt[name] += 1
                sal[name].append(r["mid"])

    items = [(k, v) for k, v in cnt.items() if v >= MIN_SKILL_N]
    items.sort(key=lambda t: t[1])                # 升序，画出来最长的在顶部
    if not items:
        print("[跳过] 图3：没有满足门槛的技能。")
        return None
    items = items[-15:]

    names = [k for k, _ in items]
    freqs = [v / len(recs) * 100 for _, v in items]     # 转成提及率 %，比绝对次数更直观
    meds = [median(sal[k]) for k, _ in items]

    fig, ax = plt.subplots(figsize=(11, 7))
    colors = [C_MAIN if m >= global_median else C_GRAY for m in meds]
    bars = ax.barh(names, freqs, color=colors, alpha=.9)

    # 条尾标注薪资，把"需求度"和"含金量"两个信息压进一张图
    for b, m, n in zip(bars, meds, [v for _, v in items]):
        ax.text(b.get_width() + .5, b.get_y() + b.get_height() / 2,
                f"{m/1000:.1f}K  (n={n})", va="center", fontsize=9, color="#52606d")

    ax.set_xlabel("职位描述中提及率（%）")
    ax.set_xlim(0, max(freqs) * 1.25)             # 右侧留白给标注文字
    ax.set_title("图3 ｜ 高频技能 Top15：提及率与对应薪资中位数\n"
                 "（深蓝=薪资高于全局中位 %.1fK，灰=低于）" % (global_median / 1000),
                 fontsize=13, fontweight="bold")
    ax.grid(axis="x", alpha=.25)
    fig.tight_layout()
    path = os.path.join(outdir, "skill_freq.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"[保存] {path}")
    return path


# ==============================================================================
# 七、图4：薪资分布直方图 + 定位线
# ==============================================================================
def chart_salary_dist(plt, recs, outdir):
    """
    为什么最后要画分布：前面三张图都在讲"分组均值/中位"，
    但应届生最想知道的是"我该要多少"——这需要看到自己在整体分布里的位置。

    三条定位线分别是：全局中位数、大专学历中位数、无经验中位数。
    把"市场整体"和"我当前的起点"放在同一个坐标里，期望薪资才定得有理有据。
    """
    vals = sorted(r["mid"] for r in recs)
    if not vals:
        print("[跳过] 图4：无有效薪资。")
        return None
    n = len(vals)
    g_med = median(vals)
    d_med = median([r["mid"] for r in recs if r["edu"] == "大专"]) or g_med
    e_med = median([r["mid"] for r in recs if r["exp"] in ("无需经验", "在校生/应届生")]) or g_med
    p25, p75 = vals[int(n * .25)], vals[int(n * .75)]

    fig, ax = plt.subplots(figsize=(11, 5.6))
    ax.hist([v / 1000 for v in vals], bins=32, color=C_TEAL, alpha=.75, edgecolor="white")
    for v, c, lb in [(g_med, C_ACCENT, f"全局中位 {g_med/1000:.1f}K"),
                     (d_med, C_PURPLE, f"大专中位 {d_med/1000:.1f}K"),
                     (e_med, "#c0392b", f"无经验中位 {e_med/1000:.1f}K")]:
        ax.axvline(v / 1000, color=c, linestyle="--", linewidth=2, label=lb)

    # P25~P75 区间阴影：这是"大多数岗位落在哪"的直观范围
    ax.axvspan(p25 / 1000, p75 / 1000, color=C_ACCENT, alpha=.10)
    ax.text((p25 + p75) / 2000, ax.get_ylim()[1] * .92,
            f"P25–P75：{p25/1000:.1f}K – {p75/1000:.1f}K",
            ha="center", fontsize=10, color=C_ACCENT)

    ax.set_xlabel("月薪中位数（K/月）")
    ax.set_ylabel("岗位数量")
    ax.set_title(f"图4 ｜ 大数据岗位薪资分布（n={n}，右偏：均值高于中位数，谈薪用中位数）",
                 fontsize=14, fontweight="bold")
    ax.legend()
    ax.grid(axis="y", alpha=.25)
    fig.tight_layout()
    path = os.path.join(outdir, "salary_dist.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"[保存] {path}")
    return path


# ==============================================================================
# 八、降级方案：没装 matplotlib 时，输出文本图表 + 汇总 CSV
# ==============================================================================
def text_report(recs, outdir):
    """无 matplotlib 时的兜底：把四张图要表达的东西用文字和 CSV 固化下来。"""
    print("\n" + "=" * 68)
    print("未安装 matplotlib，已切换为【文本模式】：下面就是四张图要呈现的内容")
    print("=" * 68)

    gm = median([r["mid"] for r in recs])
    print(f"\n全局月薪中位数：{gm:.0f} 元   样本 {len(recs)} 条")

    print("\n--- 图1 城市（样本≥%d，按岗位数排序）---" % MIN_CITY_N)
    by = defaultdict(list)
    for r in recs:
        if r["city"]:
            by[r["city"]].append(r["mid"])
    stat = sorted(((c, len(v), median(v)) for c, v in by.items() if len(v) >= MIN_CITY_N),
                  key=lambda t: -t[1])
    for c, n, m in stat:
        bar = "█" * int(n / max(s[1] for s in stat) * 30)
        print(f"  {c:<6}{n:>5}条  {m:>7.0f}元  {bar}")

    print("\n--- 图2 学历 × 经验（样本≥%d）---" % MIN_CELL_N)
    cell = defaultdict(list)
    for r in recs:
        cell[(r["exp"], r["edu"])].append(r["mid"])
    for e in EXP_ORDER:
        row = []
        for d in EDU_ORDER:
            v = cell.get((e, d), [])
            row.append(f"{d}:{median(v):>7.0f}(n={len(v)})" if len(v) >= MIN_CELL_N else f"{d}:{'—':>7}      ")
        print(f"  {e:<12} " + "  ".join(row))

    print("\n--- 图3 技能 Top15 ---")
    cnt = Counter(); sal = defaultdict(list)
    for r in recs:
        for name, kws in SKILL_DICT.items():
            if any(k in r["desc"] for k in kws):
                cnt[name] += 1
                sal[name].append(r["mid"])
    for k, v in cnt.most_common(15):
        m = median(sal[k])
        flag = "↑" if m >= gm else " "
        print(f"  {k:<14}{v/len(recs)*100:>5.1f}%  {m:>7.0f}元 {flag}")

    print("\n--- 图4 薪资分布 ---")
    vals = sorted(r["mid"] for r in recs)
    print(f"  P10 {vals[int(len(vals)*.10)]:.0f} | P25 {vals[int(len(vals)*.25)]:.0f} | "
          f"P50 {vals[len(vals)//2]:.0f} | P75 {vals[int(len(vals)*.75)]:.0f} | "
          f"P90 {vals[int(len(vals)*.90)]:.0f}")
    print(f"  大专中位：{median([r['mid'] for r in recs if r['edu']=='大专']):.0f}")
    print(f"  无经验中位：{median([r['mid'] for r in recs if r['exp'] in ('无需经验','在校生/应届生')]):.0f}")

    # 导出汇总 CSV，方便你自己再做图
    path = os.path.join(outdir, "viz_summary.csv")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["维度", "分组", "样本数", "月薪中位数"])
        for c, n, m in stat:
            w.writerow(["城市", c, n, round(m)])
        for e in EXP_ORDER:
            for d in EDU_ORDER:
                v = cell.get((e, d), [])
                if len(v) >= MIN_CELL_N:
                    w.writerow(["学历×经验", f"{d}+{e}", len(v), round(median(v))])
        for k, v in cnt.most_common():
            w.writerow(["技能", k, v, round(median(sal[k]))])
    print(f"\n[保存] {path}（可用 Excel 打开，自己补图）")
    return path


# ==============================================================================
# 九、主流程
# ==============================================================================
def main():
    ap = argparse.ArgumentParser(description="大数据招聘岗位 · 可视化流水线 v2")
    ap.add_argument("--input", default=None, help="清洗后的 xlsx/csv 路径（默认按候选路径自动查找）")
    ap.add_argument("--outdir", default=DEFAULT_OUTDIR, help="图表输出目录")
    ap.add_argument("--limit", type=int, default=None, help="只取前 N 行（小样本调试用）")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # 0) 确定输入文件：显式指定优先，否则按候选路径自动查找
    if args.input:
        input_path = args.input
    else:
        input_path = next((p for p in DEFAULT_INPUTS if os.path.exists(p)), DEFAULT_INPUTS[0])
        print(f"[输入] 自动定位到：{input_path}")

    # 1) 读数据（支持 csv 走 csv 模块分支）
    if input_path.lower().endswith(".csv"):
        with open(input_path, "r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        print(f"[读取] {os.path.basename(input_path)} ｜ {len(rows)} 行")
    else:
        _, rows = load_data(input_path, args.limit)

    # 2) 整理成分析记录
    recs = build_records(rows)
    if not recs:
        sys.exit("[失败] 没有有效薪资样本，请检查字段名是否与清洗后数据集一致。")

    # 3) 全局中位数（图3 用它做颜色分界）
    global_median = median([r["mid"] for r in recs])
    print(f"[概览] 有效样本 {len(recs)} 条 ｜ 月薪中位数 {global_median:.0f} 元 ｜ "
          f"均值 {sum(r['mid'] for r in recs)/len(recs):.0f} 元")

    # 4) 绘图（matplotlib 缺失则降级）
    try:
        plt = setup_chinese_font()
    except ImportError:
        print("[提示] 未安装 matplotlib，切换到文本模式。安装：pip install matplotlib")
        text_report(recs, args.outdir)
        return

    chart_city_salary(plt, recs, args.outdir)
    chart_edu_exp(plt, recs, args.outdir)
    chart_skill_freq(plt, recs, args.outdir, global_median)
    chart_salary_dist(plt, recs, args.outdir)
    # 无论有没有图，都导出一份汇总 CSV，方便写简历时查数
    text_report(recs, args.outdir)
    print(f"\n[完成] 4 张图表已输出至 {os.path.abspath(args.outdir)}")


if __name__ == "__main__":
    main()
