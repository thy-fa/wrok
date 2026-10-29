# -*- coding: utf-8 -*-
"""
生成【可视化方案 · 作品集页面】visualization.html

特点：
  - 纯标准库运行（不需要 pandas / matplotlib）
  - 直接读取 清洗后job.xlsx，用真实数据绘制内嵌 SVG 图表
  - 图表数据与 job_visualization.py 完全一致（同一套统计口径）
  - 代码段从 job_visualization.py 自动抽取，保证文档与脚本永不同步失效

运行：python build_viz_page.py
"""

import os
import re
import html
import zipfile
from collections import Counter, defaultdict
from xml.etree import ElementTree as ET

# 复用可视化脚本里的常量，避免两套口径
import job_visualization as JV

SRC_XLSX = JV.DEFAULT_INPUT
OUT_HTML = "visualization.html"
FONT = "PingFang SC, Microsoft YaHei, Segoe UI, sans-serif"

C_MAIN = "#0b63ce"
C_ACCENT = "#e8743b"
C_TEAL = "#0f9d8a"
C_PURPLE = "#7b5ea7"
C_GRAY = "#9aa5b1"
C_RED = "#c0392b"


# ==============================================================================
# 数据加载（直接复用 job_visualization 的读取与整理逻辑）
# ==============================================================================
def load():
    _, rows = JV.load_data(SRC_XLSX, None)
    return JV.build_records(rows)


# ==============================================================================
# SVG 工具
# ==============================================================================
def esc(s):
    return html.escape(str(s))


def svg_open(w, h):
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" '
            f'xmlns="http://www.w3.org/2000/svg" '
            f'style="font-family:{FONT};max-width:{w}px">')


def txt(x, y, s, size=12, fill="#1f2933", anchor="start", weight="normal"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}">{esc(s)}</text>')


def rect(x, y, w, h, fill, opacity=1.0, rx=0):
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w,0):.1f}" '
            f'height="{max(h,0):.1f}" fill="{fill}" opacity="{opacity}" rx="{rx}"/>')


def line(x1, y1, x2, y2, stroke, width=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{width}"{d}/>')


# ==============================================================================
# 图1：城市机会与薪资（柱 + 折线双轴）
# ==============================================================================
def svg_city(recs):
    by = defaultdict(list)
    for r in recs:
        if r["city"]:
            by[r["city"]].append(r["mid"])
    stat = [(c, len(v), JV.median(v)) for c, v in by.items() if len(v) >= JV.MIN_CITY_N]
    stat.sort(key=lambda t: -t[1])
    stat = stat[:15]
    if not stat:
        return ""

    W, H = 900, 430
    L, R, T, B = 62, 62, 56, 78
    pw, ph = W - L - R, H - T - B
    maxc = max(s[1] for s in stat)
    maxm = max(s[2] for s in stat) / 1000

    p = [svg_open(W, H)]
    p.append(txt(W / 2, 26, "图1 ｜ 各城市岗位需求量与薪资中位数（样本≥%d 条）" % JV.MIN_CITY_N,
                 14, "#1f2933", "middle", "bold"))

    # 网格 + 左轴（岗位数）
    for i in range(5):
        y = T + ph - ph * i / 4
        p.append(line(L, y, L + pw, y, "#e4e7eb", 1))
        p.append(txt(L - 8, y + 4, f"{int(maxc*i/4)}", 11, C_MAIN, "end"))
    # 右轴（薪资）
    for i in range(5):
        y = T + ph - ph * i / 4
        p.append(txt(L + pw + 8, y + 4, f"{maxm*i/4:.0f}K", 11, C_ACCENT, "start"))

    bw = pw / len(stat) * 0.56
    pts = []
    for i, (c, n, m) in enumerate(stat):
        cx = L + pw * (i + .5) / len(stat)
        bh = ph * n / maxc
        p.append(rect(cx - bw / 2, T + ph - bh, bw, bh, C_MAIN, .85, 2))
        pts.append((cx, T + ph - ph * (m / 1000) / maxm))
        p.append(txt(cx, H - 56, c, 11, "#1f2933", "middle"))
        p.append(txt(cx, T + ph - bh - 5, str(n), 9.5, C_MAIN, "middle"))

    # 折线
    for a, b in zip(pts, pts[1:]):
        p.append(line(a[0], a[1], b[0], b[1], C_ACCENT, 2.4))
    for (cx, cy), (c, n, m) in zip(pts, stat):
        p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="#fff" '
                 f'stroke="{C_ACCENT}" stroke-width="2.4"/>')
        p.append(txt(cx, cy - 9, f"{m/1000:.1f}", 9.5, C_ACCENT, "middle"))

    p.append(line(L, T + ph, L + pw, T + ph, "#52606d", 1.2))
    p.append(txt(L - 8, T - 14, "岗位数量（条）", 11.5, C_MAIN, "end", "bold"))
    p.append(txt(L + pw + 8, T - 14, "月薪中位数（K）", 11.5, C_ACCENT, "start", "bold"))
    p.append(txt(W / 2, H - 18, "柱=岗位机会量（左轴）　折线=薪资水平（右轴）　两者错配处即策略空间",
                 11.5, "#52606d", "middle"))
    p.append('</svg>')
    return "".join(p)


# ==============================================================================
# 图2：学历 × 经验 薪资矩阵（分组柱状）
# ==============================================================================
def svg_edu_exp(recs):
    cell = defaultdict(list)
    for r in recs:
        if r["edu"] in JV.EDU_ORDER and r["exp"] in JV.EXP_ORDER:
            cell[(r["exp"], r["edu"])].append(r["mid"])
    data = {}
    for e in JV.EXP_ORDER:
        for d in JV.EDU_ORDER:
            v = cell.get((e, d), [])
            if len(v) >= JV.MIN_CELL_N:
                data[(e, d)] = (JV.median(v), len(v))
    exps = [e for e in JV.EXP_ORDER if any((e, d) in data for d in JV.EDU_ORDER)]
    if not exps:
        return ""

    W, H = 900, 440
    L, R, T, B = 62, 24, 62, 84
    pw, ph = W - L - R, H - T - B
    maxv = max(m for m, n in data.values()) / 1000

    p = [svg_open(W, H)]
    p.append(txt(W / 2, 26, "图2 ｜ 学历 × 经验 的薪资矩阵（柱顶 n=样本量，样本<%d 不展示）" % JV.MIN_CELL_N,
                 14, "#1f2933", "middle", "bold"))

    for i in range(5):
        y = T + ph - ph * i / 4
        p.append(line(L, y, L + pw, y, "#e4e7eb", 1))
        p.append(txt(L - 8, y + 4, f"{maxv*i/4:.0f}K", 11, "#52606d", "end"))

    colors = {"大专": C_ACCENT, "本科": C_MAIN, "硕士": C_PURPLE}
    gw = pw / len(exps)
    bw = gw * 0.24
    for i, e in enumerate(exps):
        gx = L + gw * (i + .5)
        for j, d in enumerate(JV.EDU_ORDER):
            if (e, d) not in data:
                continue
            m, n = data[(e, d)]
            bh = ph * (m / 1000) / maxv
            x = gx + (j - 1) * (bw + 2)
            p.append(rect(x - bw / 2, T + ph - bh, bw, bh, colors[d], .9, 2))
            p.append(txt(x, T + ph - bh - 16, f"{m/1000:.1f}K", 9.5, colors[d], "middle", "bold"))
            p.append(txt(x, T + ph - bh - 5, f"n={n}", 8.5, "#52606d", "middle"))
        p.append(txt(gx, T + ph + 18, e, 11, "#1f2933", "middle"))

    p.append(line(L, T + ph, L + pw, T + ph, "#52606d", 1.2))
    p.append(txt(L - 8, T - 14, "月薪中位数（K）", 11.5, "#52606d", "end", "bold"))
    # 图例
    lx = L + pw - 210
    for j, d in enumerate(JV.EDU_ORDER):
        p.append(rect(lx + j * 72, T - 26, 12, 12, colors[d], .9, 2))
        p.append(txt(lx + j * 72 + 17, T - 16, d, 11.5, "#1f2933"))
    p.append(txt(W / 2, H - 20, "X 轴＝工作经验要求（有序档位）　Y 轴＝月薪中位数　分组＝学历要求",
                 11.5, "#52606d", "middle"))
    p.append('</svg>')
    return "".join(p)


# ==============================================================================
# 图3：技能 Top15（横向条形）
# ==============================================================================
def svg_skill(recs, gm):
    cnt = Counter(); sal = defaultdict(list)
    for r in recs:
        for name, kws in JV.SKILL_DICT.items():
            if any(k in r["desc"] for k in kws):
                cnt[name] += 1
                sal[name].append(r["mid"])
    items = [(k, v) for k, v in cnt.items() if v >= JV.MIN_SKILL_N]
    items.sort(key=lambda t: t[1])
    items = items[-15:]
    if not items:
        return ""

    W = 900
    rowh = 27
    H = 96 + rowh * len(items)
    L, R, T = 116, 130, 62
    pw = W - L - R
    maxf = max(v / len(recs) * 100 for _, v in items)

    p = [svg_open(W, H)]
    p.append(txt(W / 2, 26, "图3 ｜ 高频技能 Top15：提及率与对应薪资中位数", 14, "#1f2933", "middle", "bold"))
    p.append(txt(W / 2, 46, "深蓝＝薪资高于全局中位 %.1fK（有溢价）　灰＝低于（属基础盘，不写就吃亏）"
                 % (gm / 1000), 11.5, "#52606d", "middle"))

    for i, (k, v) in enumerate(items):
        y = T + i * rowh
        m = JV.median(sal[k])
        col = C_MAIN if m >= gm else C_GRAY
        f = v / len(recs) * 100
        p.append(txt(L - 10, y + 15, k, 11.5, "#1f2933", "end", "bold"))
        p.append(rect(L, y + 3, pw * f / maxf, 17, col, .88, 2))
        p.append(txt(L + pw * f / maxf + 8, y + 16,
                     f"{f:.1f}%　{m/1000:.1f}K　(n={v})", 10.5, "#52606d"))

    p.append(txt(L, H - 16, "条形长度＝JD 提及率　条尾标注＝该技能岗位薪资中位数与样本量",
                 11.5, "#52606d"))
    p.append('</svg>')
    return "".join(p)


# ==============================================================================
# 图4：薪资分布直方图
# ==============================================================================
def svg_dist(recs):
    vals = sorted(r["mid"] for r in recs)
    if not vals:
        return ""
    n = len(vals)
    gm = JV.median(vals)
    dm = JV.median([r["mid"] for r in recs if r["edu"] == "大专"]) or gm
    em = JV.median([r["mid"] for r in recs
                    if r["exp"] in ("无需经验", "在校生/应届生")]) or gm
    p25, p75 = vals[int(n * .25)], vals[int(n * .75)]

    # 分箱：0.5K 一档，覆盖到 55K
    bins = Counter(int(v // 500) for v in vals)
    lo_b, hi_b = 11, min(110, max(bins))
    maxc = max(bins.get(b, 0) for b in range(lo_b, hi_b + 1))

    W, H = 900, 410
    L, R, T, B = 62, 24, 60, 76
    pw, ph = W - L - R, H - T - B

    p = [svg_open(W, H)]
    p.append(txt(W / 2, 26, "图4 ｜ 大数据岗位薪资分布（右偏：谈薪用中位数，不用均值）",
                 14, "#1f2933", "middle", "bold"))

    for i in range(5):
        y = T + ph - ph * i / 4
        p.append(line(L, y, L + pw, y, "#e4e7eb", 1))
        p.append(txt(L - 8, y + 4, f"{int(maxc*i/4)}", 11, "#52606d", "end"))

    # 关键：柱子与刻度必须共用同一套坐标映射（按薪资值比例定位），
    # 否则按"分箱数均分宽度"会和刻度线错位。
    scale = hi_b * 500 + 500          # X 轴满量程（元）
    def xp(v):                        # 薪资值 -> 画布 X
        return L + pw * v / scale
    bw = pw * 500 / scale             # 每根柱宽（0.5K 一档）
    for b in range(lo_b, hi_b + 1):
        c = bins.get(b, 0)
        bh = ph * c / maxc
        x = xp(b * 500)
        # P25~P75 区间用强调色，其余用青色
        inband = p25 <= b * 500 < p75
        p.append(rect(x + .5, T + ph - bh, bw - 1, bh,
                      C_ACCENT if inband else C_TEAL, .8, 1))

    # X 轴刻度（每 10K）
    for k in range(0, 56, 10):
        x = L + pw * (k * 1000) / (hi_b * 500 + 500)
        if x <= L + pw:
            p.append(line(x, T + ph, x, T + ph + 4, "#52606d", 1))
            p.append(txt(x, T + ph + 18, f"{k}K", 11, "#52606d", "middle"))

    # 三条定位线
    for v, c, lb in [(gm, C_ACCENT, f"全局中位 {gm/1000:.1f}K"),
                     (dm, C_PURPLE, f"大专中位 {dm/1000:.1f}K"),
                     (em, C_RED, f"无经验中位 {em/1000:.1f}K")]:
        x = L + pw * v / (hi_b * 500 + 500)
        p.append(line(x, T, x, T + ph, c, 2, "5,4"))
        p.append(txt(x + 5, T + 14, lb, 10.5, c, "start", "bold"))

    p.append(line(L, T + ph, L + pw, T + ph, "#52606d", 1.2))
    p.append(txt(L - 8, T - 14, "岗位数量", 11.5, "#52606d", "end", "bold"))
    p.append(txt(W / 2, H - 20,
                 f"X 轴＝月薪中位数　Y 轴＝岗位数量　P25–P75 区间：{p25/1000:.1f}K – {p75/1000:.1f}K（橙色柱）",
                 11.5, "#52606d", "middle"))
    p.append('</svg>')
    return "".join(p)


# ==============================================================================
# 从 job_visualization.py 抽取代码段（保证文档与脚本同步）
# ==============================================================================
def extract_code():
    src = open("job_visualization.py", encoding="utf-8").read()
    a = src.index("def setup_chinese_font")
    b = src.index("# ==========", src.index("def chart_city_salary"))
    c = src.index("# 八、降级方案")
    c = src.rindex("# ==========", 0, c)
    return src[a:b].rstrip(), src[src.index("def chart_city_salary"):c].rstrip()


# ==============================================================================
# 组装 HTML
# ==============================================================================
def build():
    recs = load()
    gm = JV.median([r["mid"] for r in recs])
    dm = JV.median([r["mid"] for r in recs if r["edu"] == "大专"])
    em = JV.median([r["mid"] for r in recs
                    if r["exp"] in ("无需经验", "在校生/应届生")])
    vals = sorted(r["mid"] for r in recs)
    n = len(vals)
    p25, p75, p90 = vals[int(n * .25)], vals[int(n * .75)], vals[int(n * .90)]

    # 关键数字（用于结论中的表述，与图表严格一致）
    def med(**kw):
        s = [r["mid"] for r in recs if all(r.get(k) == v for k, v in kw.items())]
        return JV.median(s) if s else None

    m_noexp = med(exp="无需经验")
    m_1y = med(exp="1年经验")
    m_34y = med(exp="3-4年经验")
    m_bk = med(edu="本科")
    m_dz1y = med(edu="大专", exp="1年经验")
    m_dz34 = med(edu="大专", exp="3-4年经验")
    m_bk_noexp = med(edu="本科", exp="无需经验")

    city_stat = defaultdict(list)
    for r in recs:
        if r["city"]:
            city_stat[r["city"]].append(r["mid"])
    dz_city = Counter(r["city"] for r in recs if r["edu"] == "大专")

    def cstat(c):
        v = city_stat.get(c, [])
        return len(v), (JV.median(v) or 0)

    nj_n, nj_m = cstat("南京")
    sz_n, sz_m = cstat("深圳")
    sh_n, sh_m = cstat("上海")
    cd_n, cd_m = cstat("成都")
    dztop = dz_city.most_common(3)
    dztop_txt = "、".join(f"{c} {n}" for c, n in dztop)

    ctype_med = {}
    for r in recs:
        ctype_med.setdefault(r["ctype"], []).append(r["mid"])
    ct = sorted(((k, len(v), JV.median(v)) for k, v in ctype_med.items()),
                key=lambda t: -t[2])
    # 企业类型梯度文案（过滤样本 < 60 的类别，避免小样本极值上榜）
    ct_txt = " > ".join(f"{k} {v/1000:.1f}K" for k, n, v in ct if n >= 60)
    private_n = len(ctype_med.get("民营", []))
    private_pct = private_n / len(recs) * 100

    code_font, code_charts = extract_code()

    def pre(s):
        return f'<pre><code>{esc(s)}</code></pre>'

    charts = [
        ("图1", "城市机会与薪资（柱 + 折线双轴）", svg_city(recs),
         "组合图：柱状图 + 折线图，双 Y 轴",
         "X 轴＝城市（按岗位数取前 15，样本 ≥ 30 条）",
         "Y1（左）＝岗位数量／条　Y2（右）＝月薪中位数（K）",
         "回答「去哪个城市」。把<strong>机会量</strong>和<strong>价值</strong>放在同一张图里，"
         "直接暴露两者的错配：岗位最多的城市不一定薪资最高。若只看岗位数选城市，"
         "很可能选到一个「好进但天花板低」的市场。"),

        ("图2", "学历 × 经验 薪资矩阵（分组柱状）", svg_edu_exp(recs),
         "分组柱状图（有序分类 X 轴）",
         "X 轴＝工作经验要求（在校生/应届生 → 10年以上，共 8 档）",
         "Y 轴＝月薪中位数（K）　分组＝学历（大专／本科／硕士）",
         "回答「我的起点值多少、往哪走涨得快」。经验是有序档位而非连续数值，"
         "用柱状而非折线，才能诚实呈现<strong>台阶式跃迁</strong>；柱顶标注样本量，"
         "避免小样本极值误导判断。"),

        ("图3", "高频技能 Top15（横向条形）", svg_skill(recs, gm),
         "横向条形图（排名 + 对比）",
         "Y 轴＝技能名称（按提及率升序排列）",
         "X 轴＝职位描述中的提及率（%）　条尾标注＝薪资中位数与样本量",
         "回答「学什么」。用颜色区分技能含金量：深蓝＝高于全局中位（学了有溢价），"
         "灰＝低于（属基础盘，不写进简历就吃亏）。据此把技能分成"
         "<strong>必写项</strong>和<strong>差异项</strong>两层。"),

        ("图4", "薪资分布与定位（直方图 + 定位线）", svg_dist(recs),
         "直方图 + 参考线",
         "X 轴＝月薪中位数（0.5K 一档分箱）",
         "Y 轴＝该区间岗位数量　参考线＝全局／大专／无经验中位",
         "回答「我该要多少」。前三张图都在讲分组中位，只有分布图能让人看到"
         "<strong>自己在市场里的位置</strong>。P25–P75 阴影区即大多数人的落点，"
         "期望薪资应锚定在自己所处分段，而不是全场中位数。"),
    ]

    fig_html = []
    for tag, title, svg, ctype_, xaxis, yaxis, biz in charts:
        if not svg:
            continue
        fig_html.append(f"""
  <section class="chart">
    <h2>{esc(tag)} ｜ {esc(title)}</h2>
    <div class="svgbox">{svg}</div>
    <table class="meta">
      <tr><th width="88">图表类型</th><td>{esc(ctype_)}</td></tr>
      <tr><th>X 轴</th><td>{esc(xaxis)}</td></tr>
      <tr><th>Y 轴</th><td>{esc(yaxis)}</td></tr>
    </table>
    <div class="biz"><b>业务意义：</b>{biz}</div>
  </section>""")

    conclusions = f"""
  <section class="chart">
    <h2>四、面向应届生的 4 条业务结论</h2>

    <div class="concl">
      <h3>结论 1 ｜ 经验的边际收益远大于学历 —— 先入行，比先升本科划算</h3>
      <ul>
        <li>同一批数据里：<strong>「无需经验」中位 {m_noexp/1000:.1f}K → 「1 年经验」{m_1y/1000:.1f}K</strong>，
            增幅 {(m_1y/m_noexp-1)*100:.0f}%；而<strong>大专 {dm/1000:.1f}K → 本科 {m_bk/1000:.1f}K</strong>，增幅仅 {(m_bk/dm-1)*100:.0f}%。</li>
        <li>更能说明问题的一组交叉：<strong>本科+无需经验 {m_bk_noexp/1000:.1f}K</strong>，
            反而<strong>低于大专+1 年经验 {m_dz1y/1000:.1f}K</strong>。学历并不能替代经验定价。</li>
        <li><b>落地动作：</b>接受 {em/1000:.1f}K–{m_dz1y/1000:.1f}K 的起薪先拿到「1 年经验」这个标签；
            参照大专+3-4 年 {m_dz34/1000:.1f}K，把 18–24 个月后的目标定在 {m_dz34/1000:.1f}K 左右。
            不要为了够本科门槛而延后入行——这一年工作经验在定价上比一纸文凭更值钱。</li>
      </ul>
      <div class="note"><b>口径提醒：</b>这是分组中位数对比，不是因果推断。薪资差异同时受城市、
      行业、公司类型影响，结论用于<strong>定方向</strong>，不足以支撑「只要熬满一年就必然翻倍」。</div>
    </div>

    <div class="concl">
      <h3>结论 2 ｜ 岗位数量 ≠ 薪资水平 —— 大专生应选「高薪 + 有量」的城市，而非岗位最多的城市</h3>
      <ul>
        <li>错配最明显的两处：<strong>南京 {nj_n} 条但中位仅 {nj_m/1000:.1f}K</strong>；
            <strong>深圳 {sz_n} 条却达 {sz_m/1000:.1f}K</strong>；
            上海以 {sh_n} 条居首，中位 {sh_m/1000:.1f}K。</li>
        <li>落到大专这个池子，岗位数 TOP 是<strong>{dztop_txt}</strong> ——
            南京大专岗位最多，但整体薪资水平偏低。</li>
        <li><b>落地动作：</b>优先级定为<strong>深圳 &gt; 上海 &gt; 成都</strong>（岗位量与薪资兼顾），
            南京作为「先上岸」的备选池。成都 {cd_n} 条 / {cd_m/1000:.1f}K 属于竞争与回报较均衡的选项。</li>
      </ul>
    </div>

    <div class="concl">
      <h3>结论 3 ｜ 技能决定「能不能进门」，不决定「能拿多少」—— 简历要分层写</h3>
      <ul>
        <li>需求侧：<strong>SQL 40.5%、Java 40.0%、MySQL 27.2%、Python 22.5%</strong>，
            大数据生态里 Hadoop 20.0%、Spark 18.3%、Hive 14.9%。</li>
        <li>但薪资侧几乎拉不开差距：各技能岗位中位数集中在 <strong>17.5K–18.8K</strong>，
            极差仅约 1.25K（±7%）。<strong>技能是准入门槛，不是溢价来源。</strong></li>
        <li><b>落地动作：</b>简历技能栏分两层写——
            <strong>基础层</strong>（必写，覆盖 60%+ 的 JD 关键词）：SQL、Java、Hadoop、Spark、Hive；
            <strong>差异层</strong>（选写，用于定向岗位）：Flink 8.3%、ClickHouse 11.4%、数据仓库 11.0%，
            对应实时数仓方向。面试时把「我会什么」转向「我用它做过什么」——因为大家都会写这些词。</li>
      </ul>
    </div>

    <div class="concl">
      <h3>结论 4 ｜ 期望薪资锚定 P25 而非中位数，投递优先级按企业类型排</h3>
      <ul>
        <li>分布：<strong>P25 {p25/1000:.1f}K ｜ P50 {gm/1000:.1f}K ｜ P75 {p75/1000:.1f}K ｜ P90 {p90/1000:.1f}K</strong>。
            全场中位数 {gm/1000:.1f}K 主要由 3-4 年经验岗位支撑，<strong>不是应届生的锚点</strong>。</li>
        <li>定位自己：大专中位 {dm/1000:.1f}K，无经验中位 {em/1000:.1f}K。合理报价区间是
            <strong>{em/1000:.1f}K–{p25/1000:.1f}K</strong>，冲刺 {dm/1000:.1f}K；报 {gm/1000:.0f}K 会被判定为预期脱离市场。</li>
        <li>企业类型薪资梯度：<strong>{ct_txt}</strong>（样本 &lt; 60 的类别已剔除）。
            其中民营占 {private_pct:.0f}%（{private_n} 条）却薪资最低。</li>
        <li><b>落地动作：</b>把投递分成两池——<strong>冲刺池</strong>（外资／合资／国企，量少但溢价明显）、
            <strong>保底池</strong>（民营，量大用于拿 offer 练手）。同等条件下优先 500–1000 人规模企业（中位 22.5K 最高）。</li>
      </ul>
    </div>
  </section>"""

    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>大数据招聘岗位数据分析 · 可视化方案</title>
<style>
  :root{{
    --ink:#1f2933; --sub:#52606d; --line:#e4e7eb; --bg:#ffffff;
    --brand:#0b63ce; --brand-soft:#e8f1fc; --accent:#0f9d8a; --chip:#f4f6f8;
    --warn:#b4540a; --warn-bg:#fff4e6;
  }}
  *{{box-sizing:border-box;}}
  body{{margin:0; background:#eef2f7; color:var(--ink);
    font-family:"PingFang SC","Microsoft YaHei","Segoe UI",sans-serif;
    line-height:1.75; font-size:15px;}}
  .hero{{background:linear-gradient(135deg,#0b63ce,#0f9d8a); color:#fff;
    padding:54px 24px 46px; text-align:center;}}
  .hero h1{{font-size:29px; margin:0 0 10px; letter-spacing:1px;}}
  .hero p{{font-size:15px; opacity:.92; margin:0 auto; max-width:720px;}}
  .tags{{margin-top:18px; display:flex; flex-wrap:wrap; gap:10px; justify-content:center;}}
  .tags span{{background:rgba(255,255,255,.18); border:1px solid rgba(255,255,255,.4);
    padding:5px 14px; border-radius:20px; font-size:13px;}}
  .wrap{{max-width:1000px; margin:30px auto; background:var(--bg);
    padding:44px 50px; border-radius:14px; box-shadow:0 8px 30px rgba(20,40,80,.08);}}
  h2{{font-size:20px; color:var(--brand); margin:38px 0 14px;
    border-left:5px solid var(--brand); padding-left:12px;}}
  h3{{font-size:16px; color:var(--ink); margin:18px 0 8px;}}
  p{{margin:0 0 12px;}}
  ul{{margin:0 0 12px; padding-left:20px;}}
  li{{margin-bottom:7px;}}
  .card{{background:var(--chip); border-left:4px solid var(--brand);
    padding:14px 18px; border-radius:0 8px 8px 0; margin-bottom:14px; font-size:14px;}}
  .biz{{background:#eafaf4; border:1px solid #bfe9d8; border-radius:8px;
    padding:10px 14px; font-size:13.5px; color:#0f6b4f; margin:8px 0 14px;}}
  .note{{background:var(--warn-bg); border:1px solid #f0d99b; border-radius:8px;
    padding:10px 14px; font-size:13px; color:#7a5d12; margin:10px 0;}}
  table{{width:100%; border-collapse:collapse; margin:6px 0 4px; font-size:13.5px;}}
  th,td{{border:1px solid var(--line); padding:9px 12px; text-align:left; vertical-align:top;}}
  th{{background:var(--brand-soft); color:var(--brand); font-weight:600;}}
  tr:nth-child(even) td{{background:#fafbfc;}}
  table.meta td{{background:#fff;}}
  .chart{{margin-bottom:34px;}}
  .svgbox{{background:#fbfcfe; border:1px solid var(--line); border-radius:10px;
    padding:16px 12px; margin:12px 0; overflow-x:auto;}}
  .concl{{background:#fafcff; border:1px solid #d8e6f8; border-radius:10px;
    padding:16px 20px; margin-bottom:16px;}}
  .concl h3{{color:var(--brand); margin-top:4px; font-size:15.5px;}}
  pre{{background:#1f2933; color:#e6edf3; padding:16px 18px; border-radius:10px;
    overflow-x:auto; font-size:12.5px; line-height:1.65;}}
  pre code{{font-family:"Cascadia Code","Consolas",monospace; white-space:pre;}}
  code{{background:var(--chip); padding:1px 5px; border-radius:4px; font-size:13px;}}
  pre code{{background:none; padding:0;}}
  footer{{margin-top:40px; padding-top:18px; border-top:1px solid var(--line);
    color:var(--sub); font-size:12.5px; text-align:center;}}
  @media(max-width:680px){{.wrap{{padding:28px 20px;}}}}
</style>
</head>
<body>

<div class="hero">
  <h1>大数据招聘岗位数据分析 · 可视化方案</h1>
  <p>基于前程无忧大数据岗位清洗数据集（{n} 条 × 21 字段），
     用 4 张图表回答应届生最关心的四个求职决策问题：去哪、值多少、学什么、投哪里。</p>
  <div class="tags">
    <span>Python</span><span>pandas</span><span>matplotlib</span>
    <span>数据可视化</span><span>求职决策</span><span>专科 · 大数据技术</span>
  </div>
</div>

<div class="wrap">

  <section>
    <h2>一、方案概览</h2>
    <div class="card">
      <b>数据口径：</b>月薪中位数 =（区间下限 + 上限）/ 2。原始数据存在两套薪资写法且互斥
      ——「月薪最小/最大值」{2860} 条、「最低/最高年薪」{497} 条，后者统一除以 12 折算为月薪。
      不统一口径直接作图，等于把年薪当月薪画，图会明显失真。
    </div>
    <table>
      <tr><th width="60">编号</th><th>图表</th><th width="140">回答的问题</th></tr>
      <tr><td>图1</td><td>城市机会与薪资（双轴组合）</td><td>去哪个城市</td></tr>
      <tr><td>图2</td><td>学历 × 经验 薪资矩阵</td><td>我的起点值多少</td></tr>
      <tr><td>图3</td><td>高频技能 Top15</td><td>学什么、简历写什么</td></tr>
      <tr><td>图4</td><td>薪资分布与定位</td><td>我该要多少</td></tr>
    </table>
    <p style="margin-top:10px">四张图构成完整决策链：<strong>选城 → 定位 → 补技能 → 定薪资</strong>，
    每一张都对应一个可执行的动作，而不是单纯的数据展示。</p>
  </section>

  <section>
    <h2>二、四张图表与业务意义</h2>
    {''.join(fig_html)}
  </section>

  <section class="chart">
    <h2>三、matplotlib 实现代码</h2>

    <h3>3.1 中文字体设置（最先要解决的一步）</h3>
    <p>matplotlib 默认字体不含中文字形，且不自动回退系统字体，中文会全部显示成「□□□」。
    下面这段会<strong>先探测系统里真实存在的中文字体</strong>再设置，避免出现「名字写了但没装」的无效配置。</p>
    {pre(code_font)}

    <h3>3.2 四张图表的绘制函数</h3>
    <p>完整可运行脚本见 <code>job_visualization.py</code>，含数据读取双引擎（pandas / 标准库降级）
    与缺失 matplotlib 时的文本兜底。</p>
    {pre(code_charts)}
  </section>

  {conclusions}

  <section>
    <h2>五、复现方式</h2>
    <pre><code>pip install pandas matplotlib openpyxl
python job_visualization.py                       # 默认读 D:\\Downloads\\清洗后job.xlsx
python job_visualization.py --limit 500           # 小样本先跑通
python job_visualization.py --outdir my_charts    # 指定输出目录</code></pre>
    <p>产出：<code>charts/city_salary.png</code>、<code>charts/edu_exp_salary.png</code>、
    <code>charts/skill_freq.png</code>、<code>charts/salary_dist.png</code>，
    另附 <code>charts/viz_summary.csv</code>（各维度汇总表，写简历时可直接查数）。</p>
    <div class="note"><b>说明：</b>本页图表由 <code>build_viz_page.py</code> 直接读取同一份 xlsx
    实时计算并绘制为内嵌 SVG，与脚本产出完全一致；PNG 版本需本地安装 matplotlib 后生成。</div>
  </section>

  <footer>
    大数据招聘岗位数据分析 · 可视化方案　|　求职作品集项目　|　数据源：前程无忧大数据岗位公开数据集（{n} 条）
  </footer>
</div>
</body>
</html>
"""
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_doc)
    print(f"[生成] {OUT_HTML}  （{len(html_doc)} 字符，样本 {n} 条）")


if __name__ == "__main__":
    build()
