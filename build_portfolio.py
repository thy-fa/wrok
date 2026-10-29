# -*- coding: utf-8 -*-
"""构建自包含作品集网站 portfolio.html（4 张图 base64 内嵌）。"""
import base64
import pathlib

BASE = pathlib.Path(".")
charts = {}
for name in ["city_salary", "edu_salary", "exp_salary", "skill_freq"]:
    b = BASE / f"charts/{name}.png"
    charts[name] = "data:image/png;base64," + base64.b64encode(b.read_bytes()).decode()

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>大数据招聘岗位数据分析 · 求职作品集</title>
<style>
  :root{
    --ink:#1f2933; --sub:#52606d; --line:#e4e7eb; --bg:#ffffff;
    --brand:#0b63ce; --brand-soft:#e8f1fc; --accent:#0f9d8a; --chip:#f4f6f8;
    --warn:#b4540a; --warn-bg:#fff4e6;
  }
  *{box-sizing:border-box;}
  body{margin:0; background:#eef2f7; color:var(--ink);
    font-family:"PingFang SC","Microsoft YaHei","Segoe UI",sans-serif;
    line-height:1.75; font-size:15px;}
  .hero{background:linear-gradient(135deg,#0b63ce,#0f9d8a); color:#fff;
    padding:54px 24px 46px; text-align:center;}
  .hero h1{font-size:30px; margin:0 0 10px; letter-spacing:1px;}
  .hero p{font-size:15px; opacity:.92; margin:0 auto; max-width:680px;}
  .tags{margin-top:18px; display:flex; flex-wrap:wrap; gap:10px; justify-content:center;}
  .tags span{background:rgba(255,255,255,.18); border:1px solid rgba(255,255,255,.4);
    padding:5px 14px; border-radius:20px; font-size:13px;}
  .wrap{max-width:960px; margin:30px auto; background:var(--bg);
    padding:44px 50px; border-radius:14px; box-shadow:0 8px 30px rgba(20,40,80,.08);}
  h2{font-size:20px; color:var(--brand); margin:38px 0 14px;
    border-left:5px solid var(--brand); padding-left:12px;}
  h3{font-size:16px; color:var(--ink); margin:18px 0 8px;}
  p{margin:0 0 12px;}
  ul{margin:0 0 12px; padding-left:20px;}
  li{margin-bottom:8px;}
  .card{background:var(--chip); border-left:4px solid var(--brand);
    padding:14px 18px; border-radius:0 8px 8px 0; margin-bottom:14px;}
  .biz{background:#eafaf4; border:1px solid #bfe9d8; border-radius:8px;
    padding:10px 14px; font-size:13.5px; color:#0f6b4f; margin:8px 0 14px;}
  table{width:100%; border-collapse:collapse; margin:6px 0 4px; font-size:13.5px;}
  th,td{border:1px solid var(--line); padding:9px 12px; text-align:left; vertical-align:top;}
  th{background:var(--brand-soft); color:var(--brand); font-weight:600;}
  tr:nth-child(even) td{background:#fafbfc;}
  .flow{display:flex; gap:0; flex-wrap:wrap; align-items:stretch; margin:10px 0;}
  .flow .step{flex:1; min-width:150px; background:var(--brand-soft); border:1px solid #cfe2fb;
    border-radius:10px; padding:12px; margin:6px; text-align:center;}
  .flow .step b{display:block; color:var(--brand); font-size:14px;}
  .flow .step span{font-size:12.5px; color:var(--sub);}
  .gallery{display:grid; grid-template-columns:1fr 1fr; gap:16px; margin:14px 0;}
  .gallery figure{margin:0; background:var(--chip); border:1px solid var(--line);
    border-radius:10px; padding:10px;}
  .gallery img{width:100%; border-radius:6px; display:block;}
  .gallery figcaption{font-size:12.5px; color:var(--sub); margin-top:6px; text-align:center;}
  .note{background:var(--warn-bg); border:1px solid #f0d99b; border-radius:8px;
    padding:12px 16px; font-size:13.5px; color:#7a5d12;}
  footer{margin-top:40px; padding-top:18px; border-top:1px solid var(--line);
    color:var(--sub); font-size:12.5px; text-align:center;}
  @media(max-width:680px){.gallery{grid-template-columns:1fr;} .wrap{padding:28px 20px;}}
</style>
</head>
<body>

<div class="hero">
  <h1>大数据招聘岗位数据分析</h1>
  <p>从公开招聘数据出发，完成"采集 → 清洗 → 探索性分析 → 可视化"全流程，量化呈现大数据岗位的市场需求、技能门槛与薪资规律，为应届生求职提供数据驱动的决策参考。</p>
  <div class="tags">
    <span>Python</span><span>requests / BeautifulSoup</span><span>pandas</span>
    <span>matplotlib</span><span>数据清洗</span><span>EDA</span><span>数据可视化</span>
  </div>
</div>

<div class="wrap">

  <!-- 背景与目标 -->
  <h2>一、项目背景与业务目标</h2>
  <div class="card">
    <p style="margin:0"><strong>背景：</strong>大数据产业持续扩张，但岗位需求结构、技能门槛与薪资水平在区域、行业间差异显著。作为大数据技术专业学生，仅凭零散求职经验难以把握市场全貌，本项目以公开岗位数据为样本，用数据说话。</p>
  </div>
  <p><strong>业务目标：</strong></p>
  <ul>
    <li>摸清大数据岗位的市场规模、城市分布与人才画像（学历 / 经验要求）。</li>
    <li>提炼高频技术技能与技能组合规律，明确学习重点与竞争力构建方向。</li>
    <li>量化薪资影响因素，建立合理的薪资预期与岗位匹配参考。</li>
    <li>形成可复用的"采集—清洗—分析—可视化"方法论，沉淀为作品集标杆项目。</li>
  </ul>

  <!-- 架构 -->
  <h2>二、整体技术架构</h2>
  <p>项目采用分层数据流水线，自上而下贯穿五个阶段，形成端到端分析闭环：</p>
  <div class="flow">
    <div class="step"><b>① 数据采集</b><span>requests + bs4<br>robots 校验 / 频率控制</span></div>
    <div class="step"><b>② 数据存储</b><span>CSV / MySQL<br>utf-8-sig 落库</span></div>
    <div class="step"><b>③ 数据清洗</b><span>pandas<br>去重 / 缺失 / 异常 / 转换</span></div>
    <div class="step"><b>④ 探索分析</b><span>描述统计 + 分组统计<br>相关性 / 词频</span></div>
    <div class="step"><b>⑤ 可视化</b><span>matplotlib<br>组合图 / 条形 / 词频</span></div>
  </div>

  <!-- 阶段一 采集 -->
  <h2>三、阶段一 · 数据采集（合规优先）</h2>
  <p><strong>数据源：</strong>优先使用 Kaggle / 和鲸社区等公开数据集练手，再谨慎尝试 51job、智联等招聘平台，并全程遵守 robots 协议与频率限制（2–5 秒随机休眠）。</p>
  <p><strong>采集字段：</strong>职位名称、公司、城市、薪资原文、学历、经验、公司规模、行业、技能标签、岗位描述、来源、采集时间。</p>
  <div class="note">合规底线：仅采集公开岗位信息，严禁抓取求职者简历等个人隐私；数据仅用于学习研究，不商用、不高频批量抓取，并在报告中主动声明数据来源。</div>

  <!-- 阶段二 清洗与EDA -->
  <h2>四、阶段二 · 数据清洗与 EDA</h2>
  <p><strong>四类清洗：</strong></p>
  <ul>
    <li><strong>去重</strong>：整行去重 + 业务主键（岗位+公司+城市+薪资）去重。</li>
    <li><strong>缺失值</strong>：文本补默认、薪资"面议"标空不硬填，避免失真。</li>
    <li><strong>异常值</strong>：薪资保留 0&lt;月薪≤200K 并修正 min&gt;max；经验剔除 &lt;0 或 &gt;30 年。</li>
    <li><strong>类型转换</strong>：薪资原文→K/月、经验→年限、学历→有序数值、城市归一化。</li>
  </ul>
  <p><strong>分析维度：</strong>描述统计（整体水位）+ 分组统计（城市 / 学历 / 经验 / 行业 × 薪资、技能词频），每一步都对应一个求职业务问题。</p>

  <!-- 阶段三 可视化 -->
  <h2>五、阶段三 · 数据可视化与结论</h2>
  <p>用 matplotlib 绘制 4 张图，叙事主线为"<strong>去哪（城市）→ 值多少（学历/经验）→ 学什么（技能）</strong>"。</p>
  <div class="gallery">
    <figure><img src="__CITY__" alt="城市需求与薪资"><figcaption>① 城市需求与薪资（双轴）</figcaption></figure>
    <figure><img src="__EDU__" alt="学历与薪资"><figcaption>② 学历 vs 平均薪资</figcaption></figure>
    <figure><img src="__EXP__" alt="经验与薪资"><figcaption>③ 经验 vs 平均薪资</figcaption></figure>
    <figure><img src="__SKILL__" alt="高频技能"><figcaption>④ 高频技能 Top15</figcaption></figure>
  </div>

  <h3>面向应届生的 4 条落地结论</h3>
  <div class="card"><p style="margin:0"><strong>① 地域：</strong>把投递重心压在"岗位多且薪资高"的 3–5 个城市（典型为一线北上深 + 新一线杭成广），避免在低需求城市无差别海投。</p></div>
  <div class="card"><p style="margin:0"><strong>② 技能：</strong>用技能词频 Top15 做简历技能栏逐条自检——必备 Python + SQL + 1 个计算引擎（Spark/Hive），再补 1 个 BI 工具。</p></div>
  <div class="card"><p style="margin:0"><strong>③ 定位：</strong>本科虽是薪资拐点，但 1–3 年经验段跃升最大；应届生不纠结起薪，用 2–3 个可量化落地项目补经验短板。</p></div>
  <div class="card"><p style="margin:0"><strong>④ 节奏：</strong>0→3 年薪资斜率最陡，毕业前两年聚焦能写进简历的产出，减少无成长跳槽。</p></div>
  <div class="note">说明：本页 4 张图为演示数据渲染的示例；请用你的真实 <code>jobs_clean.csv</code> 运行 <code>job_visualization.py</code> 替换为真实结果，结论也将随之个性化。</div>

  <!-- 项目亮点 -->
  <h2>六、项目亮点（面试话术参考）</h2>
  <ul>
    <li><strong>全链路闭环</strong>：独立打通"采集—清洗—分析—可视化"，而非只做单点脚本。</li>
    <li><strong>工程素养</strong>：爬虫内置 robots 校验与频率控制，体现合规与风险意识。</li>
    <li><strong>数据严谨</strong>：薪资多单位（万/年/13薪）解析、异常值与缺失值规则化处理。</li>
    <li><strong>业务导向</strong>：每个分析维度都映射为求职决策，结论可落地而非堆图表。</li>
  </ul>

  <!-- 文件清单 -->
  <h2>七、文件清单与运行说明</h2>
  <table>
    <tr><th style="width:34%">文件</th><th>作用</th></tr>
    <tr><td>job_crawler_framework.py</td><td>数据采集框架（requests+bs4，含合规校验）</td></tr>
    <tr><td>clean_eda.py</td><td>数据清洗 + EDA（pandas）</td></tr>
    <tr><td>job_visualization.py</td><td>4 张图表可视化（matplotlib）</td></tr>
    <tr><td>portfolio.html</td><td>本作品集页面（自包含，可直接发布）</td></tr>
    <tr><td>charts/*.png</td><td>可视化成品图</td></tr>
  </table>
  <p><strong>运行顺序：</strong><code>采集 → clean_eda.py（产出 jobs_clean.csv）→ job_visualization.py（产出 charts/）</code>。本地需 <code>pip install pandas matplotlib</code>。</p>

  <footer>大数据招聘岗位数据分析 · 求职作品集　|　专科 · 大数据技术专业</footer>
</div>
</body>
</html>
"""

html = (TEMPLATE
        .replace("__CITY__", charts["city_salary"])
        .replace("__EDU__", charts["edu_salary"])
        .replace("__EXP__", charts["exp_salary"])
        .replace("__SKILL__", charts["skill_freq"]))

out = BASE / "portfolio.html"
out.write_text(html, encoding="utf-8")
print("已生成", out, "大小", out.stat().st_size, "字节")
