# -*- coding: utf-8 -*-
"""
生成【大数据招聘岗位数据分析 · 完整项目报告】project_report.html

- 复用 build_viz_page.py 的 SVG 绘图函数，图表数据与可视化脚本严格同源
- 复用 job_visualization.py 的数据读取与统计口径
- 纯标准库运行，输出自包含 HTML（可直接挂作品集网站 / 打印为 PDF）

运行：python build_full_report.py
"""

import html
from collections import Counter, defaultdict

import job_visualization as JV
from build_viz_page import svg_city, svg_edu_exp, svg_skill, svg_dist, load

OUT = "project_report.html"


def esc(s):
    return html.escape(str(s))


# ==============================================================================
# 统计计算
# ==============================================================================
recs = load()
N = len(recs)
vals = sorted(r["mid"] for r in recs)
GM = JV.median(vals)
MEAN = sum(vals) / N
P10, P25, P50, P75, P90 = (vals[int(N * q)] for q in (.10, .25, .50, .75, .90))


def med(**kw):
    s = [r["mid"] for r in recs if all(r.get(k) == v for k, v in kw.items())]
    return JV.median(s) if s else None


def cnt(**kw):
    return sum(1 for r in recs if all(r.get(k) == v for k, v in kw.items()))


M_NOEXP = med(exp="无需经验")
M_1Y = med(exp="1年经验")
M_34Y = med(exp="3-4年经验")
M_BK = med(edu="本科")
M_DZ = med(edu="大专")
M_DZ1Y = med(edu="大专", exp="1年经验")
M_DZ34 = med(edu="大专", exp="3-4年经验")
M_BK_NOEXP = med(edu="本科", exp="无需经验")
N_DZ = cnt(edu="大专")

# 城市
city_stat = defaultdict(list)
for r in recs:
    if r["city"]:
        city_stat[r["city"]].append(r["mid"])
city_rows = [(c, len(v), JV.median(v)) for c, v in city_stat.items() if len(v) >= 30]
city_rows.sort(key=lambda t: -t[1])
dz_city = Counter(r["city"] for r in recs if r["edu"] == "大专")

# 学历 / 经验
edu_rows = sorted(((e, cnt(edu=e), med(edu=e)) for e in JV.EDU_ORDER), key=lambda t: -t[1])
exp_rows = [(e, cnt(exp=e), med(exp=e)) for e in JV.EXP_ORDER if cnt(exp=e) > 0]

# 技能
sk_cnt = Counter(); sk_med = {}
for name, kws in JV.SKILL_DICT.items():
    hit = [r["mid"] for r in recs if any(k in r["desc"] for k in kws)]
    if hit:
        sk_cnt[name] = len(hit)
        sk_med[name] = JV.median(hit)
sk_rows = sk_cnt.most_common(15)

# 企业类型 / 规模
ct_stat = defaultdict(list)
for r in recs:
    ct_stat[r["ctype"]].append(r["mid"])
ct_rows = sorted(((k, len(v), JV.median(v)) for k, v in ct_stat.items() if len(v) >= 60),
                 key=lambda t: -t[2])
sc_stat = defaultdict(list)
for r in recs:
    sc_stat[r["scale"]].append(r["mid"])
SC_ORDER = ["少于50人", "50-150人", "150-500人", "500-1000人",
            "1000-5000人", "5000-10000人", "10000人以上"]
sc_rows = [(k, len(sc_stat[k]), JV.median(sc_stat[k])) for k in SC_ORDER if sc_stat.get(k)]


def k(v):
    return f"{v/1000:.1f}K"


# ==============================================================================
# 各章节 HTML
# ==============================================================================
TOC = """
<nav class="toc">
  <b>目录</b>
  <ol>
    <li><a href="#c1">项目概述</a></li>
    <li><a href="#c2">数据源与采集方案</a></li>
    <li><a href="#c3">数据预处理与清洗</a></li>
    <li><a href="#c4">探索性数据分析</a></li>
    <li><a href="#c5">业务结论与项目价值</a></li>
    <li><a href="#c6">总结、局限性与后续优化</a></li>
    <li><a href="#ca">附录：简历项目经历描述</a></li>
  </ol>
</nav>"""

CH1 = f"""
<section id="c1">
<h2><span class="no">1</span>项目概述</h2>

<h3>1.1 项目背景</h3>
<p>大数据技术专业大三学生进入求职季时，会同时面对三个具体问题：<strong>去哪个城市发展</strong>、
<strong>优先学哪些技能</strong>、<strong>期望薪资定在多少</strong>。</p>
<p>网络上关于"大数据前景好、薪资高"的判断大多是笼统的印象，缺少可验证的数据支撑。
本项目采集前程无忧平台的<strong>大数据岗位真实招聘数据</strong>，
用数据分析的方法把这三个问题转化为可量化的结论，
让求职决策建立在数据之上，而不是感觉之上。</p>

<h3>1.2 项目目标</h3>
<table>
  <tr><th width="130">目标</th><th>说明</th></tr>
  <tr><td>市场画像</td><td>岗位集中在哪些城市、哪些行业、什么类型的公司，机会量如何分布</td></tr>
  <tr><td>门槛结构</td><td>学历与经验要求的分布，大专生真正够得着的岗位池有多大</td></tr>
  <tr><td>薪资量化</td><td>薪资的整体分布与分位数，以及学历、经验、城市、公司类型对薪资的影响</td></tr>
  <tr><td>技能图谱</td><td>哪些技能是入场券（必须会），哪些是差异化（会了加分）</td></tr>
  <tr><td>方法论沉淀</td><td>完整跑通"采集 → 存储 → 清洗 → 分析 → 可视化"的流水线，形成可复用的工程习惯</td></tr>
</table>

<h3>1.3 技术架构</h3>
<div class="flow">
  <div class="step"><b>采集层</b><span>公开数据集 + 自建爬虫<br>requests / bs4</span></div>
  <div class="step"><b>存储层</b><span>原始层 CSV<br>标准层 SQLite</span></div>
  <div class="step"><b>清洗层</b><span>去重 / 补缺 / 解析<br>pandas</span></div>
  <div class="step"><b>分析层</b><span>描述统计 / 分组统计<br>关键词匹配</span></div>
  <div class="step"><b>可视化层</b><span>4 张图表 + 报告<br>matplotlib</span></div>
</div>
<p class="cap">图：项目五层流水线。每层职责单一、产出可验证，任一步出错都能定位到具体环节。</p>

<h3>1.4 数据集概况</h3>
<table>
  <tr><th width="150">项目</th><th>内容</th></tr>
  <tr><td>数据来源</td><td>和鲸社区公开数据集《前程无忧 - 大数据岗位数据集》（原始出处：前程无忧）</td></tr>
  <tr><td>分析主表</td><td>清洗后数据集，{N} 条 × 21 字段</td></tr>
  <tr><td>时间窗口</td><td>2022 年 11 月（数据集发布时点），属横截面数据</td></tr>
  <tr><td>覆盖城市</td><td>{len(city_stat)} 个城市，岗位量 TOP：{"、".join(f"{c}({n})" for c, n, m in city_rows[:5])}</td></tr>
  <tr><td>核心技术栈</td><td>Python · pandas · matplotlib · openpyxl · SQLite</td></tr>
</table>
</section>"""

CH2 = """
<section id="c2">
<h2><span class="no">2</span>数据源与采集方案</h2>

<h3>2.1 数据源的选择过程</h3>
<p>项目最初计划<strong>自建爬虫</strong>采集招聘平台。在动手前先做了两项前置检查，结论改变了技术路线：</p>
<ul>
  <li><strong>robots 协议检查</strong>：读取和鲸社区 <code>robots.txt</code>，内容为
      <code>Allow: /</code> 但 <code>Disallow: /api/</code>。而数据集的文件列表与下载接口全部位于
      <code>/api/</code> 下——这意味着<strong>任何自动下载脚本都必然违反站点的 robots 约定</strong>。</li>
  <li><strong>页面渲染方式验证</strong>：用 Python 直接抓取数据集页面，返回的标题为"工作台"、
      文件链接数为 0，证实页面为 JavaScript 动态渲染，直链不在 HTML 中，只能调用接口获取。</li>
</ul>
<div class="note"><b>决策：</b>放弃自动下载，改为<strong>注册登录后手动下载 + 脚本标准化处理</strong>的合规路径。
这一判断本身就是项目的一部分——识别合规边界、主动放弃技术手段，比"能爬下来"更能体现工程素养。
面试时被问到"数据怎么来的"，这条理由是可公开陈述的。</div>

<h3>2.2 数据集的两个版本</h3>
<table>
  <tr><th width="120">版本</th><th width="110">规模</th><th>用途</th></tr>
  <tr><td>原始版<br><code>job_all</code></td><td>4100 条 × 15 字段</td>
      <td>保留原始形态（含脏数据），用于<strong>演练并验证清洗流程</strong>，
      量化数据质量问题</td></tr>
  <tr><td>清洗版<br><code>清洗后</code></td><td>3357 条 × 21 字段</td>
      <td>已完成去重与字段拆分，含月薪/年薪拆分列，<strong>作为本次分析的主表</strong></td></tr>
</table>
<p>两个版本形成对照：原始版用来说明"数据有多脏、清洗规则为什么这么定"，
清洗版用来支撑分析结论。这样既展示了清洗能力，也避免了重复造轮子。</p>

<h3>2.3 字段清单（按层级划分）</h3>
<table>
  <tr><th width="110">层级</th><th>字段</th></tr>
  <tr><td>岗位基本<br>信息</td><td>职位名称、公司名称、工作地点、发布时间、职位描述或任职要求</td></tr>
  <tr><td>公司信息</td><td>公司福利、公司规模、公司类型、公司标签</td></tr>
  <tr><td>地理维度</td><td>城市、地区</td></tr>
  <tr><td>任职要求</td><td>工作经验要求、学历要求</td></tr>
  <tr><td>薪资字段</td><td>十三薪等、最低年薪、最高年薪、月薪最小值、月薪最大值</td></tr>
  <tr><td>时间派生</td><td>发布时间月、发布时间日、发布时间时</td></tr>
</table>

<h3>2.4 自建采集方案（备选路径）</h3>
<p>尽管最终采用公开数据集，采集方案仍完整设计并实现，用于应对数据集不可用或需要增量更新的场景。
核心要点：</p>
<table>
  <tr><th width="110">环节</th><th>做法</th></tr>
  <tr><td>目标判断</td><td>F12 → Network → Fetch/XHR 判断是静态 HTML 还是接口 JSON；能走接口就不解析 HTML</td></tr>
  <tr><td>采集实现</td><td><code>requests</code> + <code>BeautifulSoup</code>；封装 <code>safe_text()</code>
      处理 <code>select_one()</code> 返回 None 的情况</td></tr>
  <tr><td>频率控制</td><td>每页间隔 3–6 秒随机休眠，单线程，不并发、不使用代理池</td></tr>
  <tr><td>中断策略</td><td>遇到 403 / 429 <strong>立即停止</strong>而非重试——被识别后硬重试只会加重风险</td></tr>
  <tr><td>断点续采</td><td>进度写入 <code>progress.txt</code>，支持中断后继续</td></tr>
  <tr><td>降级设计</td><td>未安装 bs4 时自动切换到标准库 <code>html.parser</code> 解析器，保证脚本可运行</td></tr>
</table>

<h3>2.5 合规边界</h3>
<ul>
  <li><strong>频率</strong>：单线程、3–6 秒间隔，不对目标站点造成负载压力。</li>
  <li><strong>robots</strong>：采集前校验 robots.txt；读取失败时<strong>默认不采集</strong>。</li>
  <li><strong>法律</strong>：不破解验证码与反爬措施（刑法第 285 条）；不采集个人身份信息
      （个人信息保护法）；数据仅用于个人学习研究，不作商业用途（反不正当竞争法、著作权法）。</li>
  <li><strong>产出</strong>：对外只展示聚合统计结果，不对外分发原始数据集。</li>
</ul>
</section>"""

CH3 = f"""
<section id="c3">
<h2><span class="no">3</span>数据预处理与清洗</h2>

<h3>3.1 原始数据存在的真实问题</h3>
<p>清洗规则不是凭经验拍脑袋定的，而是先把原始版 4100 条数据完整统计一遍，
针对<strong>实际存在的问题</strong>逐条设计规则。以下是实测结果：</p>
<table>
  <tr><th width="110">问题</th><th width="100">数量</th><th>后果</th></tr>
  <tr><td>重复岗位</td><td>1281 条（31%）</td><td>不去重会让所有统计虚高，城市排名失真</td></tr>
  <tr><td>整行坏数据</td><td>475 条</td><td>城市、经验、描述三者同时为空，属采集失败残留，纯噪音</td></tr>
  <tr><td>转义符 <code>\\/</code></td><td>薪酬 593、公司标签 1497</td>
      <td><code>12-20万\\/年</code> 不处理会导致薪资解析失败或被放大 12 倍</td></tr>
  <tr><td>列错位</td><td>学历 46 条、经验 2 条</td><td>学历列混入"11-16发布"这类日期串，污染分类统计</td></tr>
  <tr><td>薪酬缺失</td><td>82 条</td><td>无"面议"标记，直接为空，需单独策略处理</td></tr>
</table>

<h3>3.2 清洗七步</h3>
<table>
  <tr><th width="50">步骤</th><th width="180">动作</th><th>理由</th></tr>
  <tr><td>0</td><td>初检：删除无名索引列</td><td>导出时残留的行号列无业务含义</td></tr>
  <tr><td>1</td><td>清洗转义符 <code>\\/</code> → <code>/</code></td>
      <td>最隐蔽的一步，直接影响后续所有解析</td></tr>
  <tr><td>2</td><td>剔除坏行（关键字段同时为空）</td><td>信息量不足以支撑任何分析</td></tr>
  <tr><td>3</td><td>去重（职位+公司+城市+薪酬）</td>
      <td><strong>用四个键而非三个</strong>：三键会误删同公司同城同职位但薪资不同的真实多岗位</td></tr>
  <tr><td>4</td><td>缺失值分策处理</td><td>薪酬缺失删行（无法推断）；学历/经验/规模填"未知"（保留样本）</td></tr>
  <tr><td>5</td><td>字段解析与类型转换</td><td>薪资→月薪中位数、城市拆分、学历/经验→有序分类、时间→datetime</td></tr>
  <tr><td>6</td><td>异常值处理</td><td>合理区间外剔除 + 1%~99% 分位截尾</td></tr>
  <tr><td>7</td><td>删除冗余列并输出</td><td>产出 <code>jobs_clean.csv</code>，原始层与清洗层分离保存</td></tr>
</table>

<h3>3.3 薪资口径统一（本项目最关键的一步）</h3>
<p>清洗版数据集中薪资存在<strong>两套写法且互斥</strong>：</p>
<table>
  <tr><th width="180">字段</th><th width="90">条数</th><th>单位</th></tr>
  <tr><td>月薪最小值 / 月薪最大值</td><td>2860</td><td>元/月</td></tr>
  <tr><td>最低年薪 / 最高年薪</td><td>497</td><td>元/年</td></tr>
</table>
<p>2860 + 497 = 3357，正好互补。若不折算直接分析，等于把年薪当成月薪，结果会离谱到一眼可辨。
统一规则如下：</p>
<pre><code>月薪中位数 = (月薪最小值 + 月薪最大值) / 2            # 月薪口径
月薪中位数 = (最低年薪 + 最高年薪) / 2 / 12           # 年薪口径（÷12 折算）

# 缺失策略：两套口径都没有值 -> 该条不参与薪资分析（不猜、不填 0）</code></pre>
<p>处理后的效果（实测）：</p>
<table>
  <tr><th width="150">原始写法</th><th width="110">月薪下限</th><th width="110">月薪上限</th><th>月薪中位数</th></tr>
  <tr><td><code>8千-1.6万</code></td><td>8000</td><td>16000</td><td>12000</td></tr>
  <tr><td><code>12-20万/年</code></td><td>10000</td><td>16667</td><td>13333</td></tr>
  <tr><td><code>6-8千</code></td><td>6000</td><td>8000</td><td>7000</td></tr>
  <tr><td><code>面议</code> / 空值</td><td>—</td><td>—</td><td>不参与计算</td></tr>
</table>
<div class="note"><b>一个踩过的坑：</b>初版解析把 <code>15-25K</code> 算成了 15 而不是 15000——
因为单位只写在后一个数上。修正逻辑为"任一边有单位则整数区间共用单位，两边都有则各用各的"。
这类问题只有把真实数据跑一遍才会暴露。</div>

<h3>3.4 字段类型转换</h3>
<ul>
  <li><strong>学历、经验 → 有序分类（Categorical）</strong>：不是普通字符串。
      经验若按字符串排序，"10年以上"会排在"1年"前面，图表横轴顺序直接错乱。
      本项目显式定义顺序：<code>{" → ".join(JV.EXP_ORDER)}</code>。</li>
  <li><strong>薪资 → 数值型</strong>：区间文本解析为数值，才能参与统计与比较。</li>
  <li><strong>发布时间 → datetime</strong>：原始值为 Excel 日期序列值（如 44881.17），需转换。</li>
  <li><strong>公司标签 → 文本清洗</strong>：还原转义符后拆分，避免同一标签被计为多个类别。</li>
</ul>

<h3>3.5 异常值处理：为什么用截尾而不是删除</h3>
<p>月薪低于 2000 元或高于 100000 元的记录先按规则剔除（多为录入错误或非全职岗位），
其余极值采用 <strong>1%~99% 分位截尾</strong>而非直接删除。</p>
<p>原因是：像"3-6 万/月"这类高薪岗位是<strong>真实存在的市场信号</strong>，直接删除会损失信息，
也会低估高端岗位的存在。截尾只压缩极值对均值的影响，保留样本本身。</p>

<h3>3.6 清洗前后对比</h3>
<table>
  <tr><th width="150">指标</th><th>清洗前（原始版）</th><th>分析主表（清洗版）</th></tr>
  <tr><td>记录数</td><td>4100</td><td>3357</td></tr>
  <tr><td>字段数</td><td>15</td><td>21（含薪资拆分与派生字段）</td></tr>
  <tr><td>重复记录</td><td>1281 条（31%）</td><td>已去除</td></tr>
  <tr><td>薪资可用率</td><td>存在缺失与多口径混杂</td><td>100%（口径已统一为月薪中位数）</td></tr>
  <tr><td>字段脏值</td><td>转义符、列错位、日期混入</td><td>已清洗并转为规范类型</td></tr>
</table>
</section>"""

# ---------------- 第4章：EDA（含图表） ----------------
edu_table = "".join(
    f"<tr><td>{e}</td><td>{n}</td><td>{n/N*100:.1f}%</td><td>{k(m)}</td></tr>"
    for e, n, m in edu_rows)
exp_table = "".join(
    f"<tr><td>{e}</td><td>{n}</td><td>{k(m) if m else '—'}</td></tr>"
    for e, n, m in exp_rows)
skill_table = "".join(
    f"<tr><td>{s}</td><td>{c}</td><td>{c/N*100:.1f}%</td><td>{k(sk_med[s])}</td></tr>"
    for s, c in sk_rows[:10])
ct_table = "".join(
    f"<tr><td>{c}</td><td>{n}</td><td>{k(m)}</td></tr>" for c, n, m in ct_rows)
sc_table = "".join(
    f"<tr><td>{s}</td><td>{n}</td><td>{k(m)}</td></tr>" for s, n, m in sc_rows)

CH4 = f"""
<section id="c4">
<h2><span class="no">4</span>探索性数据分析</h2>
<p>本章围绕四个维度展开，每个维度对应一张图表，每张图表对应一个求职决策问题。
所有数字均来自清洗后的 {N} 条真实数据。</p>

<h3>4.1 描述统计：先看整体分布</h3>
<table>
  <tr><th width="90">统计量</th><th width="90">P10</th><th width="90">P25</th>
      <th width="90">中位数</th><th width="90">P75</th><th width="90">P90</th><th>均值</th></tr>
  <tr><td>月薪（元）</td><td>{P10:,.0f}</td><td>{P25:,.0f}</td>
      <td><b>{P50:,.0f}</b></td><td>{P75:,.0f}</td><td>{P90:,.0f}</td><td>{MEAN:,.0f}</td></tr>
</table>
<p><strong>均值（{MEAN:,.0f}）高于中位数（{P50:,.0f}），说明薪资分布右偏</strong>——
少数高薪岗位把均值拉高了。因此本报告一律使用<strong>中位数</strong>作为薪资代表值，
谈薪时也应参考中位数而非平均薪资，否则会被极端值误导。</p>

<h3>4.2 维度一：学历与经验构成</h3>
<table>
  <tr><th width="90">学历要求</th><th width="80">岗位数</th><th width="80">占比</th><th>月薪中位数</th></tr>
  {edu_table}
</table>
<table>
  <tr><th width="160">工作经验要求</th><th width="90">岗位数</th><th>月薪中位数</th></tr>
  {exp_table}
</table>
<p>两个结构性事实：<strong>本科占 {edu_rows[0][1]/N*100:.1f}%</strong>，是绝对主流；
<strong>大专占 {N_DZ/N*100:.1f}%</strong>（{N_DZ} 条），这就是本项目视角下真正够得着的岗位池。
经验侧则高度集中在 3-4 年（{cnt(exp="3-4年经验")} 条）与 5-7 年（{cnt(exp="5-7年经验")} 条），
说明市场对<strong>成熟人才</strong>的需求远大于应届生。</p>

<h3>4.3 图1 ｜ 各城市的机会量与薪资水平</h3>
<div class="svgbox">{svg_city(recs)}</div>
<table class="meta">
  <tr><th width="88">图表类型</th><td>组合图：柱状图 + 折线图，双 Y 轴</td></tr>
  <tr><th>X 轴</th><td>城市（按岗位数取前 15，样本 ≥ 30 条）</td></tr>
  <tr><th>Y 轴</th><td>左轴＝岗位数量（条）；右轴＝月薪中位数（K）</td></tr>
</table>
<p><strong>看到了什么：</strong>岗位量最多的上海（{city_rows[0][1]} 条）中位薪资 {k(city_rows[0][2])}，
而岗位量排在第二的南京（{city_rows[1][1]} 条）中位仅 {k(city_rows[1][2])}；
深圳岗位数更少（{[r for r in city_rows if r[0]=='深圳'][0][1]} 条）却达到 {k([r for r in city_rows if r[0]=='深圳'][0][2])}。
<strong>岗位数量与薪资水平并不正相关。</strong></p>
<div class="biz"><b>业务意义：</b>回答"去哪个城市"。双轴是刚需——两个指标量级不同，
画在同一根轴上会互相压扁。放在一张图里才能暴露<strong>机会量与价值的错配</strong>：
只看岗位数选城市，容易选到"好进但天花板低"的市场。</div>

<h3>4.4 图2 ｜ 学历 × 经验 的薪资矩阵</h3>
<div class="svgbox">{svg_edu_exp(recs)}</div>
<table class="meta">
  <tr><th width="88">图表类型</th><td>分组柱状图（X 轴为有序分类）</td></tr>
  <tr><th>X 轴</th><td>工作经验要求（在校生/应届生 → 10年以上，共 8 档）</td></tr>
  <tr><th>Y 轴</th><td>月薪中位数（K）；分组＝学历；柱顶标注样本量</td></tr>
</table>
<p><strong>看到了什么：</strong>薪资随经验呈<strong>台阶式跃迁</strong>而非线性增长——
从"无需经验" {k(M_NOEXP)} 到"1 年经验" {k(M_1Y)} 是一次大跳，
但"1 年"到"3-4 年"（{k(M_34Y)}）涨幅明显趋缓。
学历维度上，大专 {k(M_DZ)} 与本科 {k(M_BK)} 的差距，远小于经验档位之间的差距。</p>
<div class="biz"><b>业务意义：</b>回答"我的起点值多少、往哪走涨得快"。
经验是<strong>有序分类</strong>而非连续数值，用柱状而非折线，才能诚实呈现台阶式跃迁；
柱顶标注样本量，让"这个数可不可信"一目了然（样本 &lt; 20 的组合不展示）。</div>

<h3>4.5 图3 ｜ 高频技能与对应薪资</h3>
<div class="svgbox">{svg_skill(recs, GM)}</div>
<table class="meta">
  <tr><th width="88">图表类型</th><td>横向条形图</td></tr>
  <tr><th>Y 轴</th><td>技能名称（按提及率升序排列）</td></tr>
  <tr><th>X 轴</th><td>职位描述中的提及率（%）；条尾标注薪资中位数与样本量</td></tr>
</table>
<table>
  <tr><th width="130">技能</th><th width="80">提及次数</th><th width="80">提及率</th><th>对应岗位月薪中位数</th></tr>
  {skill_table}
</table>
<p><strong>看到了什么（这是本项目最有价值的发现）：</strong>需求侧差异很大——
SQL {sk_rows[0][1]/N*100:.1f}%、Java {[c for s,c in sk_rows if s=='Java'][0]/N*100:.1f}% 高居前列，
而 Flink 仅 {sk_cnt.get('Flink',0)/N*100:.1f}%。
但薪资侧<strong>几乎拉不开差距</strong>：各技能对应岗位的中位数集中在 {k(min(sk_med.values()))}–{k(max(sk_med.values()))}，
极差仅约 {(max(sk_med.values())-min(sk_med.values()))/1000:.2f}K。</p>
<div class="biz"><b>业务意义：</b>回答"学什么、简历写什么"。结论是反直觉的——
<strong>技能决定你能不能进门，但决定不了你能拿多少</strong>。
技能应按"必写项 / 差异项"分层管理，而不是盲目堆砌。</div>

<h3>4.6 图4 ｜ 薪资分布与自我定位</h3>
<div class="svgbox">{svg_dist(recs)}</div>
<table class="meta">
  <tr><th width="88">图表类型</th><td>直方图 + 参考线</td></tr>
  <tr><th>X 轴</th><td>月薪中位数（0.5K 一档分箱）</td></tr>
  <tr><th>Y 轴</th><td>该区间内的岗位数量；参考线＝全局 / 大专 / 无经验中位</td></tr>
</table>
<p><strong>看到了什么：</strong>分布明显右偏，多数岗位集中在 {k(P25)}–{k(P75)} 区间（图中高亮部分）。
大专学历的中位线（{k(M_DZ)}）和无经验的中位线（{k(M_NOEXP)}）都落在全局中位线（{k(GM)}）左侧。</p>
<div class="biz"><b>业务意义：</b>回答"我该要多少"。前三张图都在讲分组中位，
只有分布图能让人看到<strong>自己在市场里的具体位置</strong>。
期望薪资应锚定在自己所处的分段，而不是全场中位数。</div>

<h3>4.7 补充维度：企业类型与公司规模</h3>
<table>
  <tr><th width="140">公司类型</th><th width="90">岗位数</th><th>月薪中位数</th></tr>
  {ct_table}
</table>
<table>
  <tr><th width="140">公司规模</th><th width="90">岗位数</th><th>月薪中位数</th></tr>
  {sc_table}
</table>
<p>企业类型之间存在明显梯度，且<strong>这个梯度大于学历带来的差距</strong>。
规模维度上并非越大越好，500–1000 人区间薪资最高。</p>
</section>"""

CH5 = f"""
<section id="c5">
<h2><span class="no">5</span>业务结论与项目价值</h2>

<h3>5.1 结论一：经验的边际收益远大于学历，先入行比先升本科划算</h3>
<table>
  <tr><th width="220">对比</th><th width="150">数值变化</th><th>增幅</th></tr>
  <tr><td>无需经验 → 1 年经验</td><td>{k(M_NOEXP)} → {k(M_1Y)}</td><td><b>+{(M_1Y/M_NOEXP-1)*100:.0f}%</b></td></tr>
  <tr><td>大专 → 本科</td><td>{k(M_DZ)} → {k(M_BK)}</td><td>+{(M_BK/M_DZ-1)*100:.0f}%</td></tr>
  <tr><td>本科+无经验 vs 大专+1 年经验</td><td>{k(M_BK_NOEXP)} <b>&lt;</b> {k(M_DZ1Y)}</td><td>学历不能替代经验定价</td></tr>
</table>
<p><strong>落地动作：</strong>接受 {k(M_NOEXP)}–{k(M_DZ1Y)} 的起薪，先把"1 年工作经验"这个标签拿到手；
参照大专+3-4 年的 {k(M_DZ34)}，把 18–24 个月后的目标定在 {k(M_DZ34)} 左右。
不要为了够本科门槛而延后入行——这一年工作经验在定价上比一纸文凭更值钱。</p>
<div class="note"><b>口径提醒：</b>这是分组中位数对比，<strong>不是因果推断</strong>。
薪资差异同时受城市、行业、企业类型影响，本结论用于确定方向，
不足以支撑"只要熬满一年薪资必然翻倍"的推论。</div>

<h3>5.2 结论二：岗位数量 ≠ 薪资水平，选"高薪且有量"的城市</h3>
<p>错配最典型的两处：南京 {[r for r in city_rows if r[0]=='南京'][0][1]} 条但中位仅
{k([r for r in city_rows if r[0]=='南京'][0][2])}；深圳 {[r for r in city_rows if r[0]=='深圳'][0][1]} 条却达
{k([r for r in city_rows if r[0]=='深圳'][0][2])}。
而大专岗位数量 TOP 恰恰是 {"、".join(f"{c}（{n} 条）" for c, n in dz_city.most_common(3))}——
<strong>南京大专岗位最多，但整体薪资水平偏低</strong>。</p>
<p><strong>落地动作：</strong>城市优先级定为 <b>深圳 &gt; 上海 &gt; 成都</b>（岗位量与薪资兼顾），
南京作为"先上岸"的备选池；成都（{[r for r in city_rows if r[0]=='成都'][0][1]} 条 /
{k([r for r in city_rows if r[0]=='成都'][0][2])}）属于竞争与回报较均衡的选项。</p>

<h3>5.3 结论三：技能决定"能不能进门"，不决定"能拿多少"</h3>
<p>需求侧：SQL {sk_rows[0][1]/N*100:.1f}%、Java {[c for s,c in sk_rows if s=='Java'][0]/N*100:.1f}%、
MySQL {sk_cnt.get('MySQL',0)/N*100:.1f}%、Python {sk_cnt.get('Python',0)/N*100:.1f}%、
Hadoop {sk_cnt.get('Hadoop',0)/N*100:.1f}%、Spark {sk_cnt.get('Spark',0)/N*100:.1f}%。</p>
<p>但薪资侧几乎拉不开差距（{k(min(sk_med.values()))}–{k(max(sk_med.values()))}，极差约
{(max(sk_med.values())-min(sk_med.values()))/1000:.2f}K）。<strong>技能是准入门槛，不是溢价来源。</strong></p>
<p><strong>落地动作：</strong>简历技能栏分两层写——</p>
<ul>
  <li><strong>基础层（必写，覆盖 60%+ 的 JD 关键词）</strong>：SQL、Java、Hadoop、Spark、Hive</li>
  <li><strong>差异层（选写，用于定向实时数仓岗位）</strong>：Flink（{sk_cnt.get('Flink',0)/N*100:.1f}%）、
      ClickHouse（{sk_cnt.get('ClickHouse',0)/N*100:.1f}%）、数据仓库（{sk_cnt.get('数据仓库',0)/N*100:.1f}%）</li>
</ul>
<p>面试时应把"我会什么"转向"我用它做过什么"——因为技能词大家都会写，项目经历才能区分。</p>

<h3>5.4 结论四：期望薪资锚定 P25，投递按企业类型分层</h3>
<p>分布：P25 <b>{k(P25)}</b> ｜ 中位数 {k(P50)} ｜ P75 {k(P75)} ｜ P90 {k(P90)}。
全场中位数 {k(P50)} 主要由 3-4 年经验的岗位支撑，<strong>不是应届生的锚点</strong>。</p>
<p><strong>落地动作：</strong>合理报价区间为 <b>{k(M_NOEXP)}–{k(P25)}</b>，冲刺 {k(M_DZ)}；
若直接报 {k(P50)} 容易被判定为预期脱离市场。
企业类型梯度（{" &gt; ".join(f"{c} {k(m)}" for c, n, m in ct_rows)}）——
投递可分两池：<strong>冲刺池</strong>（外资／合资／国企，量少但溢价明显）、
<strong>保底池</strong>（民营，量大，用于拿 offer 与积累面试经验）。</p>

<h3>5.5 项目价值</h3>
<table>
  <tr><th width="110">层面</th><th>价值</th></tr>
  <tr><td>技术层面</td><td>完整跑通"采集—清洗—分析—可视化"全链路，而非单点脚本；
      具备依赖降级、异常中断、断点续采等工程化处理</td></tr>
  <tr><td>业务层面</td><td>每个分析维度都映射为一个具体决策动作（选城、定薪、补技能、选企业类型），
      结论可落地而非堆砌图表</td></tr>
  <tr><td>方法论层面</td><td>形成了可复用的分析套路：先查数据质量再定清洗规则；
      先统一口径再统计；分组统计必设样本量门槛</td></tr>
  <tr><td>合规层面</td><td>主动识别 robots 约束并放弃自动下载方案，
      建立"先判断能不能做、再考虑怎么做"的习惯</td></tr>
</table>
</section>"""

CH6 = f"""
<section id="c6">
<h2><span class="no">6</span>总结、局限性与后续优化</h2>

<h3>6.1 项目总结</h3>
<p>本项目以 {N} 条真实招聘数据为基础，完成了从数据获取到决策建议的完整闭环：</p>
<ul>
  <li><strong>数据侧</strong>：识别并解决了重复、坏行、转义符、列错位、多口径薪资等真实脏数据问题，
      薪资可用率提升至 100%。</li>
  <li><strong>分析侧</strong>：围绕城市、学历、经验、技能、企业类型五个维度展开，
      产出 4 张图表与 4 条可执行的求职结论。</li>
  <li><strong>结论侧</strong>：以数据量化了"经验溢价 &gt; 学历溢价"这一核心判断，
      并据此给出了具体的起薪接受区间、城市优先级与技能投入分层。</li>
</ul>
<p>最大的收获不是画图本身，而是三个习惯：<strong>先查数据质量再定规则</strong>、
<strong>先统一口径再做统计</strong>、<strong>每个结论都标注适用边界</strong>。</p>

<h3>6.2 局限性</h3>
<table>
  <tr><th width="130">局限</th><th>说明</th></tr>
  <tr><td>样本偏差</td><td>数据来自单一平台（前程无忧）单一时点，不能完全代表整个招聘市场；
      且以"大数据"为关键词检索，可能遗漏相关岗位</td></tr>
  <tr><td>时效性</td><td>数据为 2022 年 11 月横截面数据，技术栈热度与薪资水平会随时间变化，
      结论需结合当下行情使用</td></tr>
  <tr><td>薪资口径</td><td>招聘信息展示的多为<strong>薪资区间上限的理论值</strong>，
      与实际到手薪资、年终奖结构存在差异；本分析取区间中位数，是折中而非精确值</td></tr>
  <tr><td>文本提取误差</td><td>技能词频采用关键词匹配，可能受否定语境影响
      （如"不要求 Hadoop"），且无法识别同一技术的不同写法</td></tr>
  <tr><td>视角单一</td><td>仅分析<strong>需求侧</strong>（企业发布什么岗位），
      未涉及供给侧（求职人数、竞争比），无法判断真实录取难度</td></tr>
  <tr><td>因果受限</td><td>所有结论均为<strong>相关性</strong>描述。
      薪资差异受城市、行业、企业、个人能力共同影响，不能简单归因于单一因素</td></tr>
  <tr><td>合规约束</td><td>受 robots 与平台协议限制，采用手动下载方式获取数据，
      无法自动增量更新，数据规模受限于公开数据集</td></tr>
</table>

<h3>6.3 后续可优化方向</h3>
<table>
  <tr><th width="150">方向</th><th>具体做法</th></tr>
  <tr><td>扩大样本与时效</td><td>接入多个招聘平台并按季度更新，建立时间序列，
      观察薪资与技能热度的变化趋势</td></tr>
  <tr><td>深化薪资建模</td><td>引入多元回归或树模型，量化城市、学历、经验、企业类型
      各自对薪资的贡献权重（本项目仅做了分组对比）</td></tr>
  <tr><td>优化技能提取</td><td>引入 jieba 分词与自定义词典，或做否定语境识别，
      提升技能提取准确率；可做技能共现网络分析</td></tr>
  <tr><td>补充供给侧数据</td><td>结合岗位投递人数、城市人才流入等数据，
      计算真实的竞争激烈程度，而非仅看岗位数量</td></tr>
  <tr><td>工程化改造</td><td>将清洗与分析流程封装为定时任务 + 自动报告，
      并接入 ECharts 做交互式仪表盘，提升项目的完整度与展示效果</td></tr>
</table>
</section>"""

APPENDIX = f"""
<section id="ca">
<h2><span class="no">A</span>附录：简历项目经历描述（可直接粘贴）</h2>
<div class="card">
<b>大数据招聘岗位数据分析</b>　|　个人项目　|　Python · pandas · matplotlib · SQLite　|　2026.03 – 2026.04
<ul>
  <li>基于前程无忧 {N} 条大数据岗位真实招聘数据，独立完成"采集—清洗—分析—可视化"全链路分析，
      围绕城市、学历经验、技能、企业类型四个维度产出 4 张图表与求职决策建议。</li>
  <li>针对原始数据中 31% 重复记录、475 条空行、转义符污染（薪酬 593 条 / 公司标签 1497 条）
      等问题设计清洗规则，统一"月薪 / 年薪"双口径为月薪中位数，薪资可用率由混杂状态提升至 100%。</li>
  <li>采用分组统计与关键词匹配完成 EDA，量化发现<strong>经验溢价（+{(M_1Y/M_NOEXP-1)*100:.0f}%）
      显著高于学历溢价（+{(M_BK/M_DZ-1)*100:.0f}%）</strong>，
      并识别"技能需求差异大但薪资极差仅 {k(min(sk_med.values()))}–{k(max(sk_med.values()))}"
      的反直觉结论，据此给出分层简历撰写与期望薪资定位建议。</li>
  <li>工程实现上采用双引擎数据读取（pandas / 标准库降级）与依赖缺失时的文本模式兜底，
      保证脚本在零第三方依赖环境下仍可运行；matplotlib 输出图表统一处理中文字体与分位数标注。</li>
  <li>主动识别目标站点 robots 对 <code>/api/</code> 的禁止约定，放弃自动下载方案，
      改用"手动下载 + 脚本标准化"的合规路径，数据仅用于个人研究。</li>
</ul>
</div>
<div class="note"><b>使用提示：</b>粘贴前请确认数字与你的实际运行结果一致；
若面试被追问数据来源，可直接陈述合规判断过程，这是加分项而非减分项。</div>
</section>"""

HTML = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>大数据招聘岗位数据分析 · 完整项目报告</title>
<style>
  :root{{
    --ink:#1f2933; --sub:#52606d; --line:#e4e7eb; --bg:#ffffff;
    --brand:#0b63ce; --brand-soft:#e8f1fc; --accent:#0f9d8a; --chip:#f4f6f8;
    --warn:#b4540a; --warn-bg:#fff4e6;
  }}
  *{{box-sizing:border-box;}}
  body{{margin:0; background:#eef2f7; color:var(--ink);
    font-family:"PingFang SC","Microsoft YaHei","Segoe UI",sans-serif;
    line-height:1.78; font-size:15px;}}
  .hero{{background:linear-gradient(135deg,#0b63ce,#0f9d8a); color:#fff;
    padding:56px 24px 48px; text-align:center;}}
  .hero h1{{font-size:30px; margin:0 0 12px; letter-spacing:1px;}}
  .hero p{{font-size:15px; opacity:.93; margin:0 auto; max-width:760px;}}
  .tags{{margin-top:18px; display:flex; flex-wrap:wrap; gap:10px; justify-content:center;}}
  .tags span{{background:rgba(255,255,255,.18); border:1px solid rgba(255,255,255,.4);
    padding:5px 14px; border-radius:20px; font-size:13px;}}
  .wrap{{max-width:1000px; margin:30px auto; background:var(--bg);
    padding:44px 50px; border-radius:14px; box-shadow:0 8px 30px rgba(20,40,80,.08);}}
  h2{{font-size:21px; color:var(--brand); margin:44px 0 16px;
    border-left:5px solid var(--brand); padding-left:12px; display:flex; align-items:center; gap:10px;}}
  h2 .no{{display:inline-flex; align-items:center; justify-content:center;
    background:var(--brand); color:#fff; width:28px; height:28px; border-radius:50%;
    font-size:15px; flex:none;}}
  h3{{font-size:16.5px; color:var(--ink); margin:26px 0 10px;
    padding-left:10px; border-left:3px solid var(--accent);}}
  p{{margin:0 0 12px;}}
  ul{{margin:0 0 12px; padding-left:20px;}}
  li{{margin-bottom:7px;}}
  table{{width:100%; border-collapse:collapse; margin:8px 0 16px; font-size:13.5px;}}
  th,td{{border:1px solid var(--line); padding:9px 12px; text-align:left; vertical-align:top;}}
  th{{background:var(--brand-soft); color:var(--brand); font-weight:600;}}
  tr:nth-child(even) td{{background:#fafbfc;}}
  table.meta td{{background:#fff;}}
  .biz{{background:#eafaf4; border:1px solid #bfe9d8; border-radius:8px;
    padding:10px 14px; font-size:13.5px; color:#0f6b4f; margin:10px 0 16px;}}
  .note{{background:var(--warn-bg); border:1px solid #f0d99b; border-radius:8px;
    padding:11px 15px; font-size:13.5px; color:#7a5d12; margin:12px 0;}}
  .card{{background:var(--chip); border-left:4px solid var(--brand);
    padding:16px 20px; border-radius:0 8px 8px 0; margin:12px 0; font-size:14px;}}
  .toc{{background:var(--chip); border:1px solid var(--line); border-radius:10px;
    padding:16px 20px 16px 34px; margin-bottom:8px;}}
  .toc b{{color:var(--brand); font-size:15px;}}
  .toc ol{{margin:8px 0 0; padding-left:18px;}}
  .toc li{{margin-bottom:5px;}}
  .toc a{{color:var(--ink); text-decoration:none;}}
  .toc a:hover{{color:var(--brand); text-decoration:underline;}}
  .flow{{display:flex; flex-wrap:wrap; margin:12px 0;}}
  .flow .step{{flex:1; min-width:160px; background:var(--brand-soft);
    border:1px solid #cfe2fb; border-radius:10px; padding:12px; margin:5px; text-align:center;}}
  .flow .step b{{display:block; color:var(--brand); font-size:14px;}}
  .flow .step span{{font-size:12.5px; color:var(--sub);}}
  .cap{{font-size:12.5px; color:var(--sub); text-align:center; margin:0 0 16px;}}
  .svgbox{{background:#fbfcfe; border:1px solid var(--line); border-radius:10px;
    padding:16px 12px; margin:12px 0; overflow-x:auto;}}
  pre{{background:#1f2933; color:#e6edf3; padding:14px 18px; border-radius:10px;
    overflow-x:auto; font-size:12.5px; line-height:1.6;}}
  pre code{{font-family:"Cascadia Code","Consolas",monospace; white-space:pre; background:none; padding:0;}}
  code{{background:var(--chip); padding:1px 5px; border-radius:4px; font-size:13px;}}
  section{{scroll-margin-top:16px;}}
  footer{{margin-top:44px; padding-top:18px; border-top:1px solid var(--line);
    color:var(--sub); font-size:12.5px; text-align:center;}}
  @media(max-width:680px){{.wrap{{padding:28px 20px;}}}}
  @media print{{
    body{{background:#fff;}} .wrap{{box-shadow:none; margin:0; max-width:100%;}}
    .hero{{background:#0b63ce !important; -webkit-print-color-adjust:exact;}}
    h2{{page-break-after:avoid;}} table, .svgbox{{page-break-inside:avoid;}}
  }}
</style>
</head>
<body>

<div class="hero">
  <h1>大数据招聘岗位数据分析</h1>
  <p>完整项目报告　|　基于 {N} 条真实招聘数据的全链路分析<br>
     采集 → 清洗 → 分析 → 可视化 → 决策建议</p>
  <div class="tags">
    <span>专科 · 大数据技术</span><span>Python</span><span>pandas</span>
    <span>matplotlib</span><span>数据清洗</span><span>EDA</span>
    <span>数据可视化</span><span>求职决策</span>
  </div>
</div>

<div class="wrap">
{TOC}
{CH1}
{CH2}
{CH3}
{CH4}
{CH5}
{CH6}
{APPENDIX}

  <footer>
    大数据招聘岗位数据分析 · 完整项目报告　|　数据源：和鲸社区公开数据集《前程无忧 - 大数据岗位数据集》（{N} 条 × 21 字段）<br>
    本项目数据仅用于个人学习研究，不作商业用途
  </footer>
</div>
</body>
</html>
"""

with open(OUT, "w", encoding="utf-8") as f:
    f.write(HTML)
print(f"[生成] {OUT}  （{len(HTML)} 字符，分析样本 {N} 条）")
