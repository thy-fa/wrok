# 大数据招聘岗位数据分析 · 可视化方案

> 数据源：前程无忧大数据岗位清洗数据集 `清洗后job.xlsx`（3357 条 × 21 字段）
> 技术栈：Python · pandas（可选）· matplotlib
> 配套：`job_visualization.py`（可运行脚本）· `visualization.html`（作品集页面）

---

## 〇、先看数据口径（不统一口径，图必错）

这份数据有个陷阱：**薪资有两套写法，且互斥**。

| 字段 | 条数 | 单位 |
|---|---|---|
| 月薪最小值 / 月薪最大值 | 2860 | 元/月 |
| 最低年薪 / 最高年薪 | 497 | 元/年 |

2860 + 497 = 3357，正好互补。若不折算直接画图，等于把年薪当月薪，数值会离谱到一眼假。

**统一口径（全文所有图表一致）**：

```
月薪中位数 = (区间下限 + 上限) / 2        # 月薪列
月薪中位数 = (年薪下限 + 上限) / 2 / 12   # 年薪列
```

清洗后 3357 条全部有有效薪资，中位数 **18000 元**，均值 19575 元（右偏 —— 所以谈薪看中位数，不看均值）。

---

## 一、四张图表设计

### 图1 ｜ 城市机会与薪资（柱 + 折线双轴）

- **图表类型**：组合图（柱状 + 折线），双 Y 轴
- **X 轴**：城市（按岗位数取前 15，样本 ≥ 30 条）
- **左 Y 轴**：岗位数量（条）　**右 Y 轴**：月薪中位数（K）
- **业务意义**：回答「**去哪个城市**」。机会量与价值量单位不同、量级不同，画在一起会互相压扁，必须用双轴。放在同一张图才能暴露错配——**岗位最多的城市不等于薪资最高的城市**。只看岗位数选城市，容易选到「好进但天花板低」的市场。

### 图2 ｜ 学历 × 经验 薪资矩阵（分组柱状）

- **图表类型**：分组柱状图（X 轴为有序分类）
- **X 轴**：工作经验要求（在校生/应届生 → 10年以上，共 8 档）
- **Y 轴**：月薪中位数（K）　**分组**：学历（大专／本科／硕士）
- **业务意义**：回答「**我的起点值多少、往哪走涨得快**」。经验是有序档位而非连续数值，用柱状而非折线，才能诚实呈现**台阶式跃迁**（0年→1年翻倍，1年→3年只涨一点）。柱顶标注样本量，避免小样本极值误导。

### 图3 ｜ 高频技能 Top15（横向条形）

- **图表类型**：横向条形图
- **Y 轴**：技能名（按提及率升序）　**X 轴**：JD 提及率（%）
- **条尾标注**：该技能岗位薪资中位数 + 样本量；颜色区分是否高于全局中位
- **业务意义**：回答「**学什么、简历写什么**」。中文技能名长短不一，竖向条形会挤成一团。用颜色给技能分层：深色＝有溢价，灰色＝基础盘（不写吃亏，写了不加分）。

### 图4 ｜ 薪资分布与定位（直方图 + 定位线）

- **图表类型**：直方图 + 参考线
- **X 轴**：月薪中位数（0.5K 一档）　**Y 轴**：该区间岗位数量
- **参考线**：全局中位 / 大专中位 / 无经验中位；P25–P75 区间高亮
- **业务意义**：回答「**我该要多少**」。前三张图都在讲分组中位，只有分布图能让人看到**自己在市场里的位置**。期望薪资应锚定在自己所处分段，而不是全场中位数。

> 四张图构成决策链：**选城 → 定位 → 补技能 → 定薪资**。

---

## 二、matplotlib 代码

### 2.1 中文字体设置（第一步，不解决全是方框）

```python
import matplotlib
matplotlib.use("Agg")            # 无界面环境（服务器/IDE）也能保存图片
import matplotlib.pyplot as plt
from matplotlib import font_manager

# 常见现象：图中所有中文变成"□□□"
# 根因：matplotlib 默认字体不含中文字形，且不会自动回退到系统字体
candidates = ["Microsoft YaHei", "SimHei", "SimSun", "DengXian",
              "PingFang SC", "Heiti SC", "Arial Unicode MS",
              "Noto Sans CJK SC", "Source Han Sans SC", "WenQuanYi Zen Hei"]

# 关键：先探测系统里真实存在的字体，避免"名字写了但没装"的无效配置
available = {f.name for f in font_manager.fontManager.ttflist}
picked = [f for f in candidates if f in available]

if picked:
    plt.rcParams["font.sans-serif"] = picked
    print(f"[字体] 已选中文字体：{picked[0]}")
else:
    plt.rcParams["font.sans-serif"] = candidates
    print("[警告] 未找到常见中文字体，图中可能显示方框")

plt.rcParams["axes.unicode_minus"] = False   # 修复负号显示为方框
plt.rcParams["figure.dpi"] = 120            # 屏幕预览清晰度
plt.rcParams["savefig.dpi"] = 200           # 存盘清晰度
plt.rcParams["savefig.bbox"] = "tight"      # 防止标签被裁掉
```

> **一个常见误区**：只写 `plt.rcParams["font.sans-serif"] = ["SimHei"]` 并不总是有效。
> 如果系统没装 SimHei，matplotlib 会静默回退到默认字体，中文仍是方框。
> 上面的做法是先探测再设置，能在日志里直接告诉你到底用上了哪个字体。
> 仍不行就手动注册字体文件：
> ```python
> from matplotlib import font_manager
> font_manager.fontManager.addfont("C:/Windows/Fonts/msyh.ttc")
> plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
> ```

### 2.2 图1 城市双轴

```python
def chart_city_salary(plt, recs, outdir):
    by = defaultdict(list)
    for r in recs:
        if r["city"]:
            by[r["city"]].append(r["mid"])
    # 样本量门槛：少于 30 条的城市不单独成柱，否则小样本极值会把图带偏
    stat = [(c, len(v), median(v)) for c, v in by.items() if len(v) >= 30]
    stat.sort(key=lambda t: -t[1])
    stat = stat[:15]

    cities = [s[0] for s in stat]
    counts = [s[1] for s in stat]
    meds = [s[2] / 1000 for s in stat]          # 转 K，轴标签更短

    fig, ax1 = plt.subplots(figsize=(12, 5.6))
    ax1.bar(cities, counts, color="#0b63ce", alpha=.85, label="岗位数量")
    ax1.set_ylabel("岗位数量（条）", color="#0b63ce", fontsize=12)
    ax1.tick_params(axis="y", labelcolor="#0b63ce")

    ax2 = ax1.twinx()                            # 共享 X 轴，新增右侧 Y 轴
    ax2.plot(cities, meds, color="#e8743b", marker="o",
             linewidth=2.4, markersize=6, label="月薪中位数")
    ax2.set_ylabel("月薪中位数（K/月）", color="#e8743b", fontsize=12)
    ax2.tick_params(axis="y", labelcolor="#e8743b")
    for i, v in enumerate(meds):                 # 逐点标数值，别让读者猜刻度
        ax2.annotate(f"{v:.1f}", (i, v), textcoords="offset points",
                     xytext=(0, 8), ha="center", fontsize=9, color="#e8743b")

    ax1.set_title("图1 ｜ 各城市岗位需求量与薪资中位数", fontsize=14, fontweight="bold")
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(f"{outdir}/city_salary.png")
    plt.close(fig)
```

### 2.3 图2 学历 × 经验 分组柱状

```python
EXP_ORDER = ["在校生/应届生", "无需经验", "1年经验", "2年经验",
             "3-4年经验", "5-7年经验", "8-9年经验", "10年以上经验"]
EDU_ORDER = ["大专", "本科", "硕士"]

def chart_edu_exp(plt, recs, outdir):
    cell = defaultdict(list)
    for r in recs:
        if r["edu"] in EDU_ORDER and r["exp"] in EXP_ORDER:
            cell[(r["exp"], r["edu"])].append(r["mid"])

    # 只保留样本量足够的单元格（<20 条不画）
    data = {}
    for e in EXP_ORDER:
        for d in EDU_ORDER:
            v = cell.get((e, d), [])
            if len(v) >= 20:
                data[(e, d)] = (median(v), len(v))

    exps = [e for e in EXP_ORDER if any((e, d) in data for d in EDU_ORDER)]
    fig, ax = plt.subplots(figsize=(12, 5.8))
    width = 0.26                                  # 每组 3 根柱
    colors = {"大专": "#e8743b", "本科": "#0b63ce", "硕士": "#7b5ea7"}

    for i, d in enumerate(EDU_ORDER):
        vals, ns = [], []
        for e in exps:
            if (e, d) in data:
                m, n = data[(e, d)]
                vals.append(m / 1000); ns.append(n)
            else:
                vals.append(0); ns.append(0)      # 样本不足 -> 不画
        offset = [xi + (i - 1) * width for xi in range(len(exps))]
        bars = ax.bar(offset, vals, width=width, label=d, color=colors[d], alpha=.9)
        for b, n, v in zip(bars, ns, vals):       # 柱顶标样本量：这个数可不可信一眼可见
            if n:
                ax.text(b.get_x() + b.get_width()/2, v + .4, f"n={n}",
                        ha="center", fontsize=8, color="#52606d")

    ax.set_xticks(range(len(exps)))
    ax.set_xticklabels(exps)
    ax.set_ylabel("月薪中位数（K/月）")
    ax.set_title("图2 ｜ 学历 × 经验 的薪资矩阵", fontsize=14, fontweight="bold")
    ax.legend(title="学历要求")
    ax.grid(axis="y", alpha=.25)
    fig.tight_layout()
    fig.savefig(f"{outdir}/edu_exp_salary.png")
    plt.close(fig)
```

### 2.4 图3 技能横向条形

```python
def chart_skill_freq(plt, recs, outdir, global_median):
    cnt = Counter(); sal = defaultdict(list)
    for r in recs:
        d = r["desc"]                             # 已 lower() 的职位描述
        for name, kws in SKILL_DICT.items():      # 关键词匹配，无需 jieba
            if any(k in d for k in kws):
                cnt[name] += 1
                sal[name].append(r["mid"])

    items = sorted([(k, v) for k, v in cnt.items() if v >= 30], key=lambda t: t[1])[-15:]
    names = [k for k, _ in items]
    freqs = [v / len(recs) * 100 for _, v in items]        # 提及率比绝对次数更直观
    meds = [median(sal[k]) for k, _ in items]

    fig, ax = plt.subplots(figsize=(11, 7))
    # 颜色语义：高于全局中位=有溢价（深蓝），低于=基础盘（灰）
    colors = ["#0b63ce" if m >= global_median else "#9aa5b1" for m in meds]
    bars = ax.barh(names, freqs, color=colors, alpha=.9)
    for b, m, n in zip(bars, meds, [v for _, v in items]):
        ax.text(b.get_width() + .5, b.get_y() + b.get_height()/2,
                f"{m/1000:.1f}K  (n={n})", va="center", fontsize=9, color="#52606d")

    ax.set_xlabel("职位描述中提及率（%）")
    ax.set_xlim(0, max(freqs) * 1.25)             # 右侧留白给标注文字
    ax.set_title("图3 ｜ 高频技能 Top15：提及率与对应薪资中位数", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(f"{outdir}/skill_freq.png")
    plt.close(fig)
```

### 2.5 图4 薪资分布直方图

```python
def chart_salary_dist(plt, recs, outdir):
    vals = sorted(r["mid"] for r in recs)
    n = len(vals)
    g_med = median(vals)
    d_med = median([r["mid"] for r in recs if r["edu"] == "大专"])
    e_med = median([r["mid"] for r in recs
                    if r["exp"] in ("无需经验", "在校生/应届生")])
    p25, p75 = vals[int(n*.25)], vals[int(n*.75)]

    fig, ax = plt.subplots(figsize=(11, 5.6))
    ax.hist([v/1000 for v in vals], bins=32, color="#0f9d8a", alpha=.75, edgecolor="white")
    for v, c, lb in [(g_med, "#e8743b", f"全局中位 {g_med/1000:.1f}K"),
                     (d_med, "#7b5ea7", f"大专中位 {d_med/1000:.1f}K"),
                     (e_med, "#c0392b", f"无经验中位 {e_med/1000:.1f}K")]:
        ax.axvline(v/1000, color=c, linestyle="--", linewidth=2, label=lb)

    ax.axvspan(p25/1000, p75/1000, color="#e8743b", alpha=.10)   # 大多数人落在哪
    ax.set_xlabel("月薪中位数（K/月）")
    ax.set_ylabel("岗位数量")
    ax.set_title(f"图4 ｜ 薪资分布（n={n}，右偏：谈薪用中位数）", fontsize=14, fontweight="bold")
    ax.legend()
    fig.tight_layout()
    fig.savefig(f"{outdir}/salary_dist.png")
    plt.close(fig)
```

---

## 三、四条业务结论（面向应届生）

### 结论 1 ｜ 经验的边际收益远大于学历 —— 先入行，比先升本科划算

| 对比 | 数值 | 增幅 |
|---|---|---|
| 无需经验 → 1 年经验 | 7.5K → 17.5K | **+133%** |
| 大专 → 本科 | 14.5K → 18.8K | +29% |
| 本科+无需经验 vs 大专+1年经验 | 7.5K **<** 11.5K | 学历不能替代经验定价 |

**落地动作**：接受 7.5K–11.5K 的起薪，先把「1 年经验」这个标签拿到手；参照大专+3-4 年 17.5K，把 18–24 个月后的目标定在 17.5K。不要为了够本科门槛而延后入行——这一年工作经验在定价上比一纸文凭更值钱。

> **口径提醒**：这是分组中位数对比，不是因果推断。薪资差异同时受城市、行业、企业类型影响，结论用于**定方向**，不足以支撑「熬满一年必然翻倍」。

### 结论 2 ｜ 岗位数量 ≠ 薪资水平 —— 选「高薪 + 有量」的城市

- 南京 348 条但中位仅 **14.0K**；深圳 257 条却达 **20.0K**；上海 766 条 / **24.0K**
- 大专岗位数 TOP：南京 138、深圳 101、合肥 68 —— **南京大专岗位最多，但整体薪资偏低**

**落地动作**：优先级 **深圳 > 上海 > 成都**；南京作为「先上岸」备选池。成都 230 条 / 15.0K 是竞争与回报较均衡的选项。

### 结论 3 ｜ 技能决定「能不能进门」，不决定「能拿多少」

- 需求侧：SQL 40.5%、Java 40.0%、MySQL 27.2%、Python 22.5%、Hadoop 20.0%、Spark 18.3%、Hive 14.9%
- 薪资侧：各技能中位数集中在 **17.5K–18.8K**，极差仅约 1.25K（±7%）

**这是本方案最有价值的一个反直觉发现**：技能之间几乎拉不开薪资差距，说明**技能是准入门槛，不是溢价来源**。

**落地动作**：简历技能栏分两层——
- **基础层（必写，覆盖 60%+ JD 关键词）**：SQL、Java、Hadoop、Spark、Hive
- **差异层（选写，定向实时数仓岗）**：Flink 8.3%、ClickHouse 11.4%、数据仓库 11.0%

面试时把「我会什么」转向「我用它做过什么」——因为这些词大家都会写。

### 结论 4 ｜ 期望薪资锚定 P25，投递按企业类型分层

- 分布：P25 **13.3K** ｜ P50 18.0K ｜ P75 24.0K ｜ P90 31.2K
- 全场中位 18.0K 主要由 3-4 年经验岗位支撑，**不是应届生的锚点**
- 定位：大专中位 14.5K，无经验中位 7.5K

**落地动作**：合理报价 **7.5K–13.3K**，冲刺 14.5K；报 18K 会被判定预期脱离市场。
企业类型梯度：合资 27.5K > 外资 25.0K > 国企 18.8K > 已上市 18.0K > 民营 15.0K（民营占 36% 却薪资最低）。
投递分两池：**冲刺池**（外资／合资／国企，量少但溢价明显）、**保底池**（民营，量大用于拿 offer 练手）；同等条件优先 500–1000 人规模企业（中位 22.5K）。

---

## 四、运行方式

```bash
pip install pandas matplotlib openpyxl
python job_visualization.py                       # 默认读 D:/Downloads/清洗后job.xlsx
python job_visualization.py --limit 500           # 小样本先跑通
python job_visualization.py --outdir my_charts
```

产出：

| 文件 | 内容 |
|---|---|
| `charts/city_salary.png` | 图1 城市双轴 |
| `charts/edu_exp_salary.png` | 图2 学历×经验矩阵 |
| `charts/skill_freq.png` | 图3 技能 Top15 |
| `charts/salary_dist.png` | 图4 薪资分布 |
| `charts/viz_summary.csv` | 各维度汇总表（写简历时直接查数） |

作品集页面：`visualization.html`（自包含，图表为内嵌 SVG，双击即可打开）。
重新生成页面：`python build_viz_page.py`。

---

## 五、方案的工程考量（面试可讲）

1. **数据读取双引擎**：有 pandas 用 pandas，没装就走内置的 `zipfile + ElementTree` 标准库解析器（xlsx 本质是 zip 包里的 XML）。保证拿到脚本就能跑，不因缺依赖卡死。
2. **matplotlib 缺失时降级为文本模式**：打印四张图的文字版 + 导出汇总 CSV，先验证数据逻辑对不对，再解决画图问题。
3. **所有分组都设样本量门槛**：城市 ≥30、学历×经验单元 ≥20、技能 ≥30 次。小样本极值（如「硕士+应届生」12 条）会把图带偏，面试被追问很难解释。
4. **技能匹配用关键词不用 jieba**：技术词本来就是固定写法，分词反而容易切错，还少一个依赖。
5. **图3 的颜色是有语义的**，不是装饰：深蓝＝高于全局中位，灰＝低于。一张图同时表达「需求度」和「含金量」。

---

© 大数据招聘岗位数据分析 · 可视化方案 ｜ 求职作品集项目
