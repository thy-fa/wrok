# -*- coding: utf-8 -*-
"""生成自包含求职项目报告 report.html（图表 base64 内嵌，单文件可直接发布）。"""
import base64
import pathlib

BASE = pathlib.Path(__file__).parent
CHART_DIR = BASE / "charts"


def b64(name: str) -> str:
    return base64.b64encode((CHART_DIR / name).read_bytes()).decode()


img = {n: b64(n) for n in
       ["city_salary.png", "edu_salary.png", "exp_salary.png", "skill_freq.png"]}

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>大数据招聘岗位数据分析 · 求职项目报告</title>
<style>
  :root{
    --bg:#f7f9fc; --card:#ffffff; --ink:#1f2933; --sub:#5b6b7b;
    --line:#e3e9f0; --accent:#2563eb; --accent2:#0e9f9a; --warn:#d97706;
    --soft:#eef3fb; --code-bg:#f4f6fa;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
    background:var(--bg);color:var(--ink);line-height:1.75;font-size:16px}
  .wrap{max-width:960px;margin:0 auto;padding:0 20px 80px}
  .hero{background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 55%,#0e9f9a 100%);
    color:#fff;padding:64px 20px 56px;text-align:center}
  .hero h1{font-size:34px;font-weight:800;letter-spacing:.5px}
  .hero .tag{margin-top:14px;font-size:15px;opacity:.92}
  .tags{margin-top:22px;display:flex;flex-wrap:wrap;gap:10px;justify-content:center}
  .tags span{background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.3);
    padding:6px 14px;border-radius:999px;font-size:13px}
  .toc{background:var(--card);border:1px solid var(--line);border-radius:14px;
    padding:18px 22px;margin:-30px 0 36px;box-shadow:0 8px 24px rgba(30,58,138,.08);position:relative;z-index:2}
  .toc h3{font-size:14px;color:var(--sub);text-transform:uppercase;letter-spacing:1px;margin-bottom:10px}
  .toc ol{list-style:none;display:grid;grid-template-columns:1fr 1fr;gap:8px 24px}
  .toc a{color:var(--accent);text-decoration:none;font-size:14.5px}
  .toc a:hover{text-decoration:underline}
  section{background:var(--card);border:1px solid var(--line);border-radius:14px;
    padding:30px 32px;margin-bottom:26px;box-shadow:0 4px 16px rgba(30,58,138,.05)}
  h2{font-size:23px;margin-bottom:6px;display:flex;align-items:center;gap:10px}
  h2 .num{background:var(--accent);color:#fff;width:32px;height:32px;border-radius:9px;
    display:inline-flex;align-items:center;justify-content:center;font-size:16px;flex:0 0 auto}
  h3{font-size:18px;margin:24px 0 10px;color:#1e3a8a}
  h4{font-size:15.5px;margin:16px 0 6px;color:var(--sub)}
  p{margin:10px 0;color:#33414f}
  ul,ol{margin:10px 0 10px 22px}
  li{margin:6px 0}
  .lead{color:var(--sub);margin-bottom:4px}
  table{border-collapse:collapse;width:100%;margin:14px 0;font-size:14.5px}
  th,td{border:1px solid var(--line);padding:9px 12px;text-align:left;vertical-align:top}
  th{background:var(--soft);color:#1e3a8a;font-weight:700}
  tr:nth-child(even) td{background:#fafcff}
  code{background:var(--code-bg);border:1px solid var(--line);border-radius:6px;
    padding:1px 7px;font-family:"SFMono-Regular",Consolas,monospace;font-size:13.5px;color:#0e7490}
  pre{background:var(--code-bg);border:1px solid var(--line);border-radius:10px;
    padding:16px 18px;overflow:auto;font-size:13px;line-height:1.6;margin:12px 0}
  pre code{background:none;border:none;padding:0;color:#1f2933}
  .pipe{display:flex;flex-wrap:wrap;gap:8px;align-items:stretch;margin:18px 0}
  .pipe .step{flex:1 1 150px;background:var(--soft);border:1px solid var(--line);
    border-radius:10px;padding:14px;text-align:center}
  .pipe .step b{display:block;color:var(--accent);font-size:14px;margin-bottom:4px}
  .pipe .step span{font-size:13px;color:var(--sub)}
  .pipe .arr{align-self:center;color:var(--sub);font-weight:700}
  .box{border-left:4px solid var(--accent);background:var(--soft);border-radius:0 10px 10px 0;
    padding:14px 18px;margin:14px 0}
  .box.warn{border-color:var(--warn);background:#fff7ed}
  .box.good{border-color:var(--accent2);background:#ecfdf9}
  .box b{color:var(--ink)}
  figure{margin:20px 0;text-align:center}
  figure img{max-width:100%;border:1px solid var(--line);border-radius:12px;box-shadow:0 4px 14px rgba(0,0,0,.06)}
  figcaption{font-size:13.5px;color:var(--sub);margin-top:8px}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  @media(max-width:680px){.toc ol{grid-template-columns:1fr}.grid2{grid-template-columns:1fr}}
  .footer{text-align:center;color:var(--sub);font-size:13px;margin-top:30px}
  .kpi{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:18px 0}
  .kpi div{background:var(--soft);border:1px solid var(--line);border-radius:12px;padding:16px;text-align:center}
  .kpi b{display:block;font-size:24px;color:var(--accent)}
  .kpi span{font-size:13px;color:var(--sub)}
  @media(max-width:680px){.kpi{grid-template-columns:1fr 1fr}}
</style>
</head>
<body>
<div class="hero">
  <h1>大数据招聘岗位数据分析</h1>
  <div class="tag">求职作品集项目报告 · 从合规采集到数据驱动决策的全流程实践</div>
  <div class="tags">
    <span>Python</span><span>requests / BeautifulSoup</span><span>pandas</span>
    <span>matplotlib</span><span>数据清洗</span><span>EDA</span><span>数据可视化</span>
  </div>
</div>

<div class="wrap">
<div class="toc">
  <h3>目录</h3>
  <ol>
    <li><a href="#s1">项目概述</a></li>
    <li><a href="#s2">数据源与采集方案</a></li>
    <li><a href="#s3">数据预处理与清洗</a></li>
    <li><a href="#s4">探索性数据分析</a></li>
    <li><a href="#s5">业务结论与项目价值</a></li>
    <li><a href="#s6">总结·局限·优化方向</a></li>
  </ol>
</div>

<section id="s1">
  <h2><span class="num">1</span>项目概述</h2>
  <p class="lead">一句话定位：用数据说话，把"大数据岗位到底招什么人、值多少钱、在哪招"讲清楚，为应届生求职决策提供量化依据。</p>
  <h3>1.1 项目背景</h3>
  <p>近年来大数据产业高速扩张，企业对"大数据开发、数据分析、数据运维"等岗位的需求持续走高。但招聘平台的信息高度分散、描述非结构化，求职者往往只能凭感觉判断"该学什么技能、去哪个城市、期望薪资多少"。作为<b>专科大数据技术专业大三学生</b>，本项目以公开招聘信息为研究对象，独立完成"采集—清洗—分析—可视化"全流程，既是对专业能力的综合训练，也直接服务于自身的求职规划。</p>
  <h3>1.2 业务目标</h3>
  <p>项目围绕四个可量化目标展开，彼此构成一条"从市场到个人"的决策链：</p>
  <div class="kpi">
    <div><b>市场画像</b><span>刻画区域 / 学历 / 经验需求分布</span></div>
    <div><b>技能提炼</b><span>构建技能需求图谱，定位学习优先级</span></div>
    <div><b>薪资预期</b><span>量化城市 / 学历 / 经验对薪资的影响</span></div>
    <div><b>方法论</b><span>沉淀可复用的全流程工程能力</span></div>
  </div>
  <h3>1.3 技术架构</h3>
  <p>整体采用轻量、可复现的五层流水线，每一层对应明确的技术栈，便于在简历与面试中清晰表述：</p>
  <div class="pipe">
    <div class="step"><b>① 采集</b><span>requests + BeautifulSoup<br>robots 校验 / 频率控制</span></div>
    <div class="arr">→</div>
    <div class="step"><b>② 存储</b><span>CSV (utf-8-sig)<br>追加写 / 断点续采</span></div>
    <div class="arr">→</div>
    <div class="step"><b>③ 清洗</b><span>pandas<br>去重 / 缺失 / 异常 / 类型</span></div>
    <div class="arr">→</div>
    <div class="step"><b>④ 分析</b><span>pandas EDA<br>描述 / 分组统计</span></div>
    <div class="arr">→</div>
    <div class="step"><b>⑤ 可视化</b><span>matplotlib<br>中文渲染 / 4 张图</span></div>
  </div>
</section>

<section id="s2">
  <h2><span class="num">2</span>数据源与采集方案</h2>
  <p class="lead">采集是项目工程素养的第一道检验，合规优先于数据量。</p>
  <h3>2.1 推荐公开数据源（按风险分级）</h3>
  <table>
    <tr><th>层级</th><th>数据源</th><th>风险</th><th>适用阶段 / 说明</th></tr>
    <tr><td>公开数据集</td><td>Kaggle（Data Science Job Salaries 等）、和鲸社区、阿里天池</td><td>低</td><td><b>练手首选</b>：已脱敏、结构化、可直接下载，适合先跑通清洗与可视化</td></tr>
    <tr><td>综合招聘平台</td><td>51job、智联招聘</td><td>中</td><td>数据更贴近国内行情；需先校验 robots 协议、控制频率</td></tr>
    <tr><td>垂直 / 即时招聘</td><td>BOSS 直聘、拉勾</td><td>高</td><td>反爬强、登录限制多，<b>不建议学生自用</b>，易触发封禁与法律风险</td></tr>
  </table>
  <div class="box good"><b>稳妥路线建议：</b>先用公开数据集完成全流程验证，再视需要采集少量合规的国内平台数据做补充，避免一上来就直面高风险站点。</div>
  <h3>2.2 采集字段清单</h3>
  <p>围绕"岗位—公司—薪资—技能"四个维度设计 14 个字段，兼顾分析价值与可解析性：</p>
  <table>
    <tr><th>字段</th><th>含义</th><th>类型</th><th>备注</th></tr>
    <tr><td>job_title</td><td>岗位名称</td><td>文本</td><td>业务主键之一</td></tr>
    <tr><td>company_name</td><td>公司名称</td><td>文本</td><td>业务主键之一</td></tr>
    <tr><td>city</td><td>工作城市</td><td>文本</td><td>归一化为 city_clean</td></tr>
    <tr><td>salary_text</td><td>薪资原文</td><td>文本</td><td>"15-25K·13薪"等</td></tr>
    <tr><td>salary_min / max / avg</td><td>解析后月薪</td><td>数值(K/月)</td><td>统一口径，详见第 3 节</td></tr>
    <tr><td>education</td><td>学历要求</td><td>有序</td><td>映射为 edu_level</td></tr>
    <tr><td>experience</td><td>经验要求</td><td>文本/数值</td><td>解析为 exp_min（年）</td></tr>
    <tr><td>industry</td><td>行业</td><td>文本</td><td>公司所属行业</td></tr>
    <tr><td>company_size</td><td>公司规模</td><td>文本</td><td>如"1000-9999人"</td></tr>
    <tr><td>skills</td><td>技能要求</td><td>文本</td><td>分号分隔，用于词频</td></tr>
    <tr><td>job_desc</td><td>岗位描述</td><td>文本</td><td>补充信息</td></tr>
    <tr><td>publish_date</td><td>发布时间</td><td>日期</td><td>转 datetime</td></tr>
  </table>
  <h3>2.3 采集核心代码框架（requests + BeautifulSoup）</h3>
  <p>框架内置 robots 校验、请求重试、随机休眠与 CSV 落库，关键处均有中文注释，便于调试：</p>
  <pre><code>import requests, time, random, csv
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser

HEADERS = {"User-Agent": "Mozilla/5.0 (学习用途/爬虫练习)"}

def can_fetch(url):
    '''校验目标站点的 robots 协议，禁止抓取的路径直接跳过。'''
    rp = RobotFileParser()
    rp.set_url("https://www.example.com/robots.txt")
    rp.read()
    return rp.can_fetch(HEADERS["User-Agent"], url)

def fetch_page(url, retry=3):
    '''带超时与重试的页面请求，自动处理编码。'''
    for i in range(retry):
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.encoding = r.apparent_encoding
            return r.text
        except Exception as e:
            print(f"第{i+1}次请求失败：{e}")
            time.sleep(random.uniform(2, 5))
    return None

def parse_jobs(html):
    '''用 BeautifulSoup 提取岗位信息，选择器需按目标站点调整（TODO）。'''
    soup = BeautifulSoup(html, "html.parser")
    # jobs = soup.select("...")  # 用浏览器开发者工具定位真实选择器
    # return [{"job_title":..., "company_name":..., ...} for ...]
    return []

def save_to_csv(rows, path="jobs.csv"):
    '''utf-8-sig 编码避免 Excel 中文乱码；追加写支持断点续采。'''
    with open(path, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writerows(rows)

def main():
    for page in range(1, 6):                 # 控制分页总量
        url = f"https://www.example.com/jobs?page={page}"
        if not can_fetch(url):
            print("robots 禁止抓取，跳过"); continue
        html = fetch_page(url)
        if not html: continue
        save_to_csv(parse_jobs(html))
        time.sleep(random.uniform(2, 5))     # 频率控制：2–5 秒随机休眠</code></pre>
  <h3>2.4 爬虫规范与法律风险（务必遵守）</h3>
  <ul>
    <li><b>robots 协议</b>：抓取前用 <code>RobotFileParser</code> 校验，被禁止的路径一律跳过。</li>
    <li><b>频率控制</b>：随机休眠 2–5 秒、单站总量设上限，避免对服务器造成压力。</li>
    <li><b>不采集个人隐私</b>：不抓取求职者简历、姓名、手机号、身份证等个人信息。</li>
    <li><b>用途边界</b>：仅用于学习与研究，<b>不商用、不转售</b>采集结果。</li>
    <li><b>法律合规</b>：遵守《个人信息保护法》《网络安全法》《数据安全法》，遇登录墙、加密接口即止步。</li>
  </ul>
  <h3>2.5 数据存储方案</h3>
  <p>选用 <b>CSV</b> 作为落库格式：轻量、通用、易用 pandas 读取。使用 <code>utf-8-sig</code> 编码解决 Excel 打开中文乱码问题；采用追加写（<code>mode="a"</code>）支持断点续采，中断后无需重头抓取。</p>
</section>

<section id="s3">
  <h2><span class="num">3</span>数据预处理与清洗</h2>
  <p class="lead">清洗的目标只有一句话：让后续每一条结论都建立在可信数据之上。</p>
  <h3>3.1 去重</h3>
  <ul>
    <li><b>整行去重</b>：<code>df.drop_duplicates()</code> 清除完全重复记录（多页抓取常见）。</li>
    <li><b>业务主键去重</b>：按 <code>job_title + company_name + city + salary_text</code> 去重，消除"同一岗位被不同入口重复收录"的冗余。</li>
  </ul>
  <h3>3.2 缺失值处理</h3>
  <p>先用 <code>df.isna().sum()</code> 量化各字段缺失比例，再分级处理：</p>
  <table>
    <tr><th>字段类别</th><th>处理策略</th></tr>
    <tr><td>技能 / 描述（skills, job_desc）</td><td>补空串，缺失不影响核心分析</td></tr>
    <tr><td>学历 / 经验 / 行业 / 规模</td><td>补"未知"，保留样本参与分布统计</td></tr>
    <tr><td>薪资（salary_text 为"面议"/空）</td><td>解析为 <code>NaN</code>，<b>薪资分析时自动剔除、不硬填</b>，避免拉低真实水位</td></tr>
  </table>
  <h3>3.3 异常值处理</h3>
  <p>采用<b>业务域值规则</b>而非 IQR（薪资天然右偏，IQR 易误删高薪长尾）：</p>
  <ul>
    <li><b>薪资</b>：保留 <code>0 &lt; 月薪 ≤ 200K</code>（单位 K/月）；修正 <code>min &gt; max</code> 的颠倒记录。</li>
    <li><b>经验</b>：剔除 <code>&lt; 0</code> 或 <code>&gt; 30</code> 年的明显错误值。</li>
  </ul>
  <h3>3.4 字段类型转换</h3>
  <p>把"人能读"的文本转化为"机器能算"的结构：</p>
  <ul>
    <li><b>薪资解析</b>：<code>salary_text</code> → <code>salary_min / max / avg</code>，统一为 K/月；自动处理"万""年""13薪"等口径（如"20-30万/年"折算为月度）。</li>
    <li><b>经验</b>：解析为 <code>exp_min</code>（年），便于做数值分组。</li>
    <li><b>学历</b>：映射为有序的 <code>edu_level</code>（大专 &lt; 本科 &lt; 硕士 &lt; 博士），支持顺序比较。</li>
    <li><b>城市 / 时间</b>：城市归一化为 <code>city_clean</code>；发布时间转为 <code>datetime</code>。</li>
  </ul>
  <div class="box"><b>清洗前后对照（示意）：</b>原始样本经"整行去重 + 主键去重"后通常去除 5%–15% 冗余；薪资解析使约 10%–20%"面议"记录退出薪资分析池，但让剩余薪资结论更稳健。</div>
</section>

<section id="s4">
  <h2><span class="num">4</span>探索性数据分析（EDA）</h2>
  <p class="lead">EDA 的核心是把清洗后的数据"翻译"成业务能看懂的分布与对比。</p>
  <h3>4.1 分析维度设计</h3>
  <table>
    <tr><th>维度</th><th>方法</th><th>输出</th></tr>
    <tr><td>描述统计</td><td><code>df.describe()</code>、<code>value_counts()</code></td><td>薪资 / 经验 / 学历水位；城市需求 Top10</td></tr>
    <tr><td>分组统计</td><td><code>groupby</code> 聚合均值</td><td>城市×薪资、学历×薪资、经验×薪资、行业×薪资</td></tr>
    <tr><td>文本挖掘</td><td><code>skills.str.split(";").explode()</code></td><td>技能词频 Top（定位必备技能）</td></tr>
  </table>
  <h3>4.2 四张核心图表与业务解读</h3>
  <h4>图 1 · 城市需求与薪资（双轴组合图：柱=岗位数，线=平均薪资）</h4>
  <figure><img src="data:image/png;base64,__CITY__" alt="城市需求与薪资"><figcaption>横轴=城市，左纵轴=岗位数量，右纵轴=平均月薪(K)。</figcaption></figure>
  <div class="box"><b>业务含义：</b>寻找"柱高且线高"的城市集群——既好找工作、薪资又不低，是投递的优先战场；"柱高线低"的城市说明供给多但溢价弱，需控制预期。</div>
  <h4>图 2 · 学历 vs 薪资（柱状图，柱顶标注均值）</h4>
  <figure><img src="data:image/png;base64,__EDU__" alt="学历与薪资"><figcaption>横轴=学历要求，纵轴=平均月薪(K)。</figcaption></figure>
  <div class="box"><b>业务含义：</b>量化"学历溢价"。本科通常是薪资拐点；同时观察大专学历的真实薪资水位，帮助专科生校准预期、判断"用项目经验弥补学历"的空间。</div>
  <h4>图 3 · 经验 vs 薪资（折线图）</h4>
  <figure><img src="data:image/png;base64,__EXP__" alt="经验与薪资"><figcaption>横轴=工作年限要求，纵轴=平均月薪(K)。</figcaption></figure>
  <div class="box"><b>业务含义：</b>刻画"经验复利曲线"。重点关注 0–3 年的斜率——这往往是薪资跃升最陡的区间，提示应届生前几年应聚焦能力积累而非频繁跳槽。</div>
  <h4>图 4 · 高频技能 Top15（水平条形图）</h4>
  <figure><img src="data:image/png;base64,__SKILL__" alt="高频技能"><figcaption>横轴=出现频次，纵轴=技能名称。</figcaption></figure>
  <div class="box"><b>业务含义：</b>这是简历技能栏的"对标清单"。频次越高越接近岗位准入门槛，可直接用于逐条自检：必备语言 / 数据库 / 计算引擎 / BI 工具各是否覆盖。</div>
  <div class="box warn"><b>样本说明：</b>本报告中四张图表基于<b>演示数据集</b>渲染，用于完整展示分析 pipeline 与图表口径。将项目脚本运行于你实际采集 / 下载的真实数据集后，图表会输出对应真实结果，结论中的城市、技能与数值也应同步替换为真实数据。</div>
</section>

<section id="s5">
  <h2><span class="num">5</span>业务结论与项目价值</h2>
  <p class="lead">结论必须落地——每一条都能直接指导"投哪、学什么、怎么定位"。</p>
  <h3>5.1 面向应届生的四条落地结论</h3>
  <div class="grid2">
    <div class="box"><b>① 地域策略</b><br>把投递重心压在图 1 中"高需求 + 高薪"的 3–5 个城市，避免在低需求城市盲目海投，提升单位时间求职效率。</div>
    <div class="box"><b>② 技能自检</b><br>用图 4 Top15 逐条核对简历技能栏：确保覆盖"1 门语言(Python) + SQL + 1 个计算引擎(Hadoop/Spark) + 1 个 BI 工具"，缺口即学习优先级。</div>
    <div class="box"><b>③ 自我定位</b><br>本科虽是薪资拐点，但 1–3 年经验段跃升最大。应届生不必过度纠结起薪，应优先用 2–3 个可量化项目弥补"经验"短板。</div>
    <div class="box"><b>④ 成长节奏</b><br>0–3 年薪资斜率最陡，前两年聚焦能写进简历的产出，减少无成长的频繁跳槽，把复利曲线拉满。</div>
  </div>
  <h3>5.2 项目价值</h3>
  <ul>
    <li><b>个人决策价值</b>：用真实数据替代"听别人说"，把求职选择建立在可验证的证据上。</li>
    <li><b>能力展示价值</b>：覆盖采集合规、数据清洗、探索分析、可视化表达全链路，是简历中"端到端"项目的实证。</li>
    <li><b>方法论沉淀</b>：形成的采集框架、清洗脚本、分析模板可在后续课程设计 / 实习中直接复用。</li>
  </ul>
</section>

<section id="s6">
  <h2><span class="num">6</span>项目总结、局限性与后续优化方向</h2>
  <h3>6.1 项目总结</h3>
  <p>本项目以"大数据招聘岗位"为研究对象，独立完成了<b>合规采集 → CSV 落库 → pandas 清洗 → 探索性分析 → matplotlib 可视化</b>的完整闭环。最终量化了岗位的区域分布、学历 / 经验薪资溢价与核心技能图谱，既是一份可展示的作品集，也直接反哺了自身的求职决策。</p>
  <h3>6.2 局限性说明</h3>
  <table>
    <tr><th>局限</th><th>说明</th></tr>
    <tr><td>样本覆盖偏差</td><td>数据集中于少数平台 / 城市，未必代表全国全行业真实供需</td></tr>
    <tr><td>时效性</td><td>招聘信息随时间波动，结论存在窗口期，需定期更新</td></tr>
    <tr><td>薪资口径</td><td>"面议"未计入；不同城市生活成本差异未被折算</td></tr>
    <tr><td>文本提取误差</td><td>技能多从原文正则提取，存在漏提 / 别名不一致</td></tr>
    <tr><td>供需视角单一</td><td>仅有"岗位侧"数据，缺"求职者侧"竞争强度</td></tr>
    <tr><td>合规边界</td><td>受 robots 与法律限制，数据规模与字段完整度有限</td></tr>
  </table>
  <h3>6.3 后续可优化方向</h3>
  <ul>
    <li><b>存储升级</b>：从 CSV 迁移到 SQLite / MySQL，或接入数据仓库，支撑更大规模与多源关联。</li>
    <li><b>技能深度挖掘</b>：引入 jieba 分词 + 技能<b>共现矩阵</b>与词云，识别"技能组合"而非单点技能。</li>
    <li><b>时间序列</b>：按 <code>publish_date</code> 做需求趋势与薪资走势预测（如 Prophet / 移动平均）。</li>
    <li><b>交互式看板</b>：用 ECharts / Tableau 替代静态图，支持城市、学历多维联动筛选。</li>
    <li><b>自动化流水线</b>：用定时任务 / Airflow 串起"采集→清洗→出图"，形成可持续更新的招聘监测面板。</li>
  </ul>
  <div class="box good"><b>给面试官的一句话：</b>我独立完成了从合规采集、数据清洗、探索性分析到可视化的全流程，最终量化了大数据岗位的城市分布、学历 / 经验薪资溢价与核心技能图谱，为自己的求职决策提供了数据支撑。</div>
</section>

<div class="footer">
  大数据招聘岗位数据分析 · 求职作品集项目报告 ｜ 专科大数据技术专业 · 全流程实践<br>
  技术栈：Python · requests · BeautifulSoup · pandas · matplotlib
</div>
</div>
</body>
</html>
"""

HTML = (HTML
        .replace("__CITY__", img["city_salary.png"])
        .replace("__EDU__", img["edu_salary.png"])
        .replace("__EXP__", img["exp_salary.png"])
        .replace("__SKILL__", img["skill_freq.png"]))

out = BASE / "report.html"
out.write_text(HTML, encoding="utf-8")
print("OK 生成:", out, "大小:", out.stat().st_size, "字节")
