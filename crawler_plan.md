# 大数据招聘岗位数据分析 · 数据采集方案

> 适用：专科 · 大数据技术专业 · 大三 ｜ 技术栈：Python · requests · BeautifulSoup · CSV
> 定位：**讲思路 + 给骨架 + 配成品脚本**。正文三、五节为可自行填充的骨架，第七节为完整可运行的 `job_crawler.py`

---

## 〇、动手前先想清楚三件事

这三点决定整个采集方案的结构，比写代码更重要。

### 1. 目标页是"静态 HTML"还是"接口 JSON"？

- 打开浏览器 F12 → Network → 选 **Fetch/XHR** → 刷新页面，看岗位数据是从 HTML 里直接渲染的，还是通过某个接口返回的 JSON。
- **如果是接口**：直接 `requests.get(接口URL)` 拿 JSON，比解析 HTML 稳定得多，也不易因前端改版失效。这是优先方案。
- **如果是静态 HTML**：才用 BeautifulSoup 解析。

> 学生常见误区：一上来就写 bs4 解析，结果发现页面是 JS 动态渲染的，`soup.select()` 永远选不到东西。**先判断，再动手。**

### 2. 字段在"列表页"还是"详情页"？

- 列表页通常只有：职位名、公司、城市、薪资、学历、经验。
- 岗位描述、技能标签往往只在**详情页**。
- 抓详情页意味着：请求量 ×N，被封风险 ×N，耗时 ×N。

> 建议：**第一阶段只采列表页**，先跑通"采集 → 清洗 → 分析 → 出图"全流程。列表页字段已足够支撑 Q1（区域薪资）、Q2（学历经验门槛）、Q3（薪资影响因素）三个问题。**第二阶段**再按需补详情页，且只抽样采集（如每城市 200 条），用于 Q4 技能图谱。

### 3. 这个站"能不能采"？

先做合规判断，再做技术判断。判断不了就换源——**换源的成本远低于踩坑的成本**。

---

## 一、推荐可采集的公开数据源

按风险从低到高排列。**学生项目的正确姿势是"公开数据集打底 + 少量自建采集练手"**，而不是硬刚大厂反爬。

| 数据源 | 类型 | 风险 | 说明与用法 |
| --- | --- | --- | --- |
| **Kaggle 公开数据集** | 公开数据集 | 低 | `Data Science Job Salaries` 等，直接下载 CSV，零法律风险。适合先把清洗、分析、可视化跑通 |
| **和鲸社区（heywhale）** | 公开数据集 | 低 | 国内中文数据集较多，含招聘/薪资类，语境更贴合本项目 |
| **阿里云天池** | 赛题数据集 | 低 | 部分招聘相关赛题提供结构化数据，可省去采集环节 |
| **国家大学生就业服务平台** | 政府公开 | 低 | 官方就业信息与报告，权威合规，适合做对比验证与背景背书 |
| **企业官网招聘页** | 公开页面 | 低 | 大厂官网校招页（如腾讯、阿里、字节招聘站）结构规整、数据干净，且多为公开校招信息 |
| **51job 前程无忧** | 招聘平台 | 中 | 页面结构相对规律，需处理分页与编码；务必遵守 robots 与频率限制 |
| **智联招聘** | 招聘平台 | 中 | 存在半公开 JSON 接口，优先尝试接口而非整页解析 |
| **BOSS 直聘 / 拉勾** | 招聘平台 | **高** | 反爬强、需登录态与加密参数，**不推荐新手**。易触发封禁，且合规争议大 |

### 推荐路线（分两步走）

- **第一步（保底）**：用 Kaggle / 和鲸数据集完成"清洗 → 分析 → 可视化"全流程。这一步保证你**一定有一个能写进简历的完整项目**，不依赖采集是否成功。
- **第二步（加分）**：选一个中等风险站点做**小规模采集实践**（几百条即可），单独展示"数据采集能力"，并在作品集里明确标注合规措施。

> 这样即便第二步受阻，项目也不会烂尾。面试时可以说："主分析基于公开数据集，另自建采集模块验证了工程能力。"——这句话既诚实又完整。

---

## 二、字段清单

按**采集来源**分层列出，避免你误以为列表页能拿到全部字段。

### A. 列表页可得（第一阶段采集）

| 字段键 | 中文 | 类型 | 说明 / 清洗备注 |
| --- | --- | --- | --- |
| `job_id` | 站点岗位 ID | str | 若页面能取到，用作唯一键去重；取不到则用下方组合键 |
| `job_title` | 职位名称 | str | 用于岗位分类（数仓 / 数开 / 分析 / 运维） |
| `company_name` | 公司名称 | str | 与公司规模、行业聚合 |
| `city` | 工作城市 | str | 统一到城市级；原文可能是"北京·朝阳区"，需截断 |
| `salary_text` | 薪资原文 | str | **保留原文**，如"15-25K·13薪"，清洗阶段再解析 |
| `education` | 学历要求 | str | 归一化为 大专 / 本科 / 硕士及以上 / 不限 |
| `experience` | 经验要求 | str | 归一化为 应届 / 1-3年 / 3-5年 / 5年以上 |
| `company_size` | 公司规模 | str | 如"100-499人"，部分站点列表页没有 |
| `industry` | 所属行业 | str | 如"互联网/电商" |
| `publish_date` | 发布日期 | str | 部分站点只有"今日/3天内"相对时间，需记录原文 |

### B. 详情页可得（第二阶段抽样采集）

| 字段键 | 中文 | 说明 |
| --- | --- | --- |
| `job_description` | 岗位描述原文 | 用于词频统计与技能共现；**注意著作权，作品集只展示聚合结果** |
| `skills` | 技能标签 | 由描述文本经分词 + 技能词典抽取得到，属**派生字段** |
| `district` | 区县 | 比城市更细的地理维度 |

### C. 采集时自动生成的元字段（必加）

| 字段键 | 说明 |
| --- | --- |
| `source` | 来源站点域名，便于多源合并与溯源 |
| `keyword` | 本次检索使用的关键词，便于分层核对 |
| `page_url` | 该条记录的来源页 URL，出问题可回溯定位 |
| `crawl_time` | 采集时间戳，标识数据截面 |

### D. 清洗阶段派生字段（不在采集时计算）

`salary_min` / `salary_max` / `salary_mid`（月薪中位数，元/月）、`edu_level`（学历等级编码）、`exp_level`（经验档位编码）。

> **原则：采集层只负责"忠实记录原文"，不做清洗加工。** 原文保留下来，清洗规则改了可以重算；原文丢了就再也找不回。

---

## 三、Python 采集思路与代码骨架

整体分 6 个模块，每个模块职责单一，方便单独调试。

```
① 配置与会话  →  ② robots 校验  →  ③ 单页抓取（重试/超时）
                                          ↓
                        ④ 解析（选择器）→  ⑤ CSV 落库（追加）
                                          ↓
                              ⑥ 主循环（翻页 + 限速）
```

### 模块①：配置与会话

**思路**：用 `requests.Session()` 复用 TCP 连接，统一 headers；所有可调参数集中放顶部，方便调试时改。

```python
import requests

BASE_URL = "https://example.com/jobs/search"   # TODO: 替换为目标站点搜索页
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",  # TODO: 换成你自己浏览器的 UA
    "Accept-Language": "zh-CN,zh;q=0.9",
}
MIN_DELAY, MAX_DELAY = 3.0, 6.0   # 请求间隔（秒），随机抖动；宁慢勿快
MAX_PAGES = 5                     # 调试阶段先设 1~2，确认无误再放量
RETRIES = 3
TIMEOUT = 10
OUTPUT_FILE = "jobs_raw.csv"

session = requests.Session()      # 复用连接，比每次 requests.get 更省资源
session.headers.update(HEADERS)
```

### 模块②：robots 协议校验

**思路**：采集前先问一句"这个路径允许我访问吗"。**读不到 robots.txt 时默认不采**——保守策略不会出错。

```python
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

def can_fetch(url: str) -> bool:
    """检查 robots 是否允许抓取该 URL；读取失败时保守返回 False。"""
    parsed = urlparse(url)
    rp = RobotFileParser()
    rp.set_url(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
    try:
        rp.read()
    except Exception as e:
        print(f"[合规] 无法读取 robots.txt（{e}），默认不采集。")
        return False
    # 若站点声明了 Crawl-delay，应以其为准，不小于该值
    return rp.can_fetch(HEADERS["User-Agent"], url)
```

### 模块③：单页抓取（重试 + 异常）

**思路**：网络请求必然有失败，要区分三种情况——**成功、被拒（403/429）、异常**。被拒时不要硬重试，应停止并降温。

```python
import time, random

def fetch_page(url: str, params: dict | None = None) -> str | None:
    """抓取单页 HTML；失败重试，403/429 直接放弃（说明被识别，继续只会加重风险）。"""
    for attempt in range(1, RETRIES + 1):
        try:
            resp = session.get(url, params=params, timeout=TIMEOUT)
            if resp.status_code == 200:
                resp.encoding = resp.apparent_encoding   # 中文站点常需自动识别编码
                return resp.text
            if resp.status_code in (403, 429):
                print(f"[停止] 状态码 {resp.status_code}，疑似被限制，放弃本页。")
                return None
            print(f"[重试 {attempt}/{RETRIES}] 状态码 {resp.status_code}")
        except requests.RequestException as e:
            print(f"[重试 {attempt}/{RETRIES}] 请求异常：{e}")
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
    return None
```

### 模块④：解析（bs4 选择器）

**思路**：这是最需要反复调试的一步。**不要边请求边调选择器**——先把一页 HTML 存到本地，离线反复试，零请求、零风险。

```python
# 调试流程（强烈建议照做）：
# 1. 先抓一页存下来：
#      html = fetch_page(BASE_URL, {"keyword": "大数据", "page": 1})
#      open("sample.html", "w", encoding="utf-8").write(html)
# 2. 之后所有选择器调试都用本地文件，不再请求服务器：
#      soup = BeautifulSoup(open("sample.html", encoding="utf-8").read(), "html.parser")
# 3. 在浏览器 F12 里复制真实 CSS 选择器，逐个验证：
#      print(len(soup.select("你的选择器")))     # 先看数量对不对
#      print(soup.select_one("你的选择器").get_text(strip=True))  # 再看内容对不对

from bs4 import BeautifulSoup

def parse_jobs(html: str) -> list[dict]:
    """从列表页 HTML 中解析岗位记录。所有选择器均为占位，需按真实页面替换。"""
    soup = BeautifulSoup(html, "html.parser")
    records = []

    cards = soup.select("div.job-item")   # TODO: 替换为真实岗位卡片容器选择器
    for card in cards:
        # TODO: 逐个字段替换为真实选择器；取不到时填空字符串，不要让程序崩
        records.append({
            "job_title":    card.select_one(".job-title").get_text(strip=True) if card.select_one(".job-title") else "",
            "company_name": card.select_one(".company-name").get_text(strip=True) if card.select_one(".company-name") else "",
            "city":         "",   # TODO
            "salary_text":  "",   # TODO
            "education":    "",   # TODO
            "experience":   "",   # TODO
            # ... 其余字段同理
        })
    return records
```

> **调试心法**：`select_one()` 可能返回 `None`，直接 `.get_text()` 会抛 `AttributeError`。新手 80% 的报错来自这里。要么用上面的三元判断，要么封装一个 `safe_text(card, selector)` 辅助函数。

### 模块⑤：CSV 落库（追加写）

**思路**：**追加写 + 首次写表头**，这样中断后重跑不会覆盖已有数据，天然支持断点续采。

```python
import csv, os

FIELDNAMES = ["job_title", "company_name", "city", "salary_text",
              "education", "experience", "company_size", "industry",
              "publish_date", "source", "keyword", "page_url", "crawl_time"]

def save_to_csv(records: list[dict], filename: str = OUTPUT_FILE) -> None:
    """追加写入 CSV；文件不存在时先写表头。utf-8-sig 保证 Excel 打开中文不乱码。"""
    if not records:
        return
    write_header = not os.path.exists(filename)
    with open(filename, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerows(records)
    print(f"[保存] 写入 {len(records)} 条 -> {filename}")
```

### 模块⑥：主循环（翻页 + 限速）

**思路**：翻页循环里要处理三种终止条件——**到达设定页数、页面无数据（已到末页）、被拒绝**。限速放在每页之间。

```python
def main() -> None:
    total = 0
    if not can_fetch(BASE_URL):                 # 先做合规校验，不合规直接退出
        print("[终止] robots 不允许采集该路径。")
        return
    for page in range(1, MAX_PAGES + 1):
        params = {"keyword": "大数据", "page": page}   # TODO: 按真实站点参数名替换
        html = fetch_page(BASE_URL, params)
        if html is None:
            break                                # 被拒或连续失败，停止
        records = parse_jobs(html)
        if not records:
            print("[结束] 本页无数据，可能已到末页。")
            break
        save_to_csv(records)
        total += len(records)
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))   # 页间限速，必须保留
    print(f"[完成] 共采集 {total} 条。")
```

### 调试路线建议（按顺序做，别跳步）

1. `MAX_PAGES = 1`，先只抓一页，存成 `sample.html`。
2. 在本地 `sample.html` 上反复调选择器，直到字段全部取对。
3. 接上 CSV 写入，确认 Excel 打开不乱码、表头齐全。
4. 再放开翻页（先 `MAX_PAGES = 5`），观察是否有重复、缺页。
5. 加去重逻辑与进度记录。
6. 检查 robots 与频率，确认无异常后再考虑放量。
7. **全程不要开代理池、不要并发、不要多线程。**

---

## 四、爬虫规范与法律边界

这一节的优先级高于所有技术内容。**写在简历上的项目，必须经得起"你这数据怎么来的"这一问。**

### ① 频率控制

- 请求间隔 **3–6 秒随机休眠**（上例 `MIN_DELAY=3.0, MAX_DELAY=6.0`）。宁可慢，也不要快。
- 单次采集控制规模（建议单站点 ≤ 50 页），避免短时高并发。
- 使用真实、稳定的 `User-Agent`，**不伪造、不轮换 UA、不使用代理池**。
- 不用多线程 / 异步并发加速。并发是"从采集变攻击"的分界线。

### ② robots 协议

- 采集前访问 `https://目标站点/robots.txt`，确认路径未被 `Disallow`。
- 代码层用 `RobotFileParser` 自动校验，被禁则主动跳过（上例模块②）。
- 若站点声明 `Crawl-delay`，以其值为下限。

### ③ 法律风险规避

| 风险点 | 规避做法 |
| --- | --- |
| 非法获取计算机信息系统数据（《刑法》285 条） | **不破解验证码、不绕过登录、不逆向加密参数**。遇到登录墙就换源 |
| 侵犯公民个人信息（《个人信息保护法》） | **只采企业公开的岗位信息，严禁采集求职者简历、联系方式等任何个人信息** |
| 破坏生产经营 / 拒服攻击风险 | 严格限速，不对服务器造成实质负担 |
| 不正当竞争（《反不正当竞争法》） | 数据不商用、不转售、不搭建对外数据服务 |
| 著作权（岗位描述文本） | 作品集与报告只展示**聚合统计结果**（词频、占比、薪资中位数），**不展示岗位原文全文** |
| 平台条款违约 | 阅读并遵守目标站点用户协议；协议禁止即放弃 |

### ④ 在作品集里怎么说（面试话术）

> "数据来自公开招聘平台的公开岗位信息，采集前校验了 robots 协议，请求间隔 3–6 秒且未使用代理与并发；仅采集企业公开信息，不涉及任何求职者个人隐私，数据仅用于个人学习研究，未商用。"

**主动声明合规措施反而是加分项**——多数候选人不会提，你提了就是工程素养。

---

## 五、数据存储方案：CSV

### 为什么用 CSV

无需装数据库、pandas 一行读入、版本可追溯、便于放进 GitHub 仓库作为作品集附件。对千级到万级样本完全够用。

### 六条关键约定

1. **编码用 `utf-8-sig`**：否则 Excel 打开中文乱码（最常见的坑）。
2. **追加写 `open(..., "a")` + 首次写表头**：支持中断后重跑，天然断点续采。
3. **字段顺序固定**：用 `FIELDNAMES` 常量约束，别用 `records[0].keys()`——首条记录缺字段会导致表头不完整。
4. **换行符 `newline=""`**：不加会导致 Windows 下每行之间多一个空行。
5. **描述类字段先清理换行**：`job_description` 若含 `\n`，CSV 会自动加引号，虽不报错但影响可读性，建议 `replace("\n", " ")`。
6. **原始层与清洗层分离**：采集只写 `jobs_raw.csv` **永不手工修改**；清洗脚本读它、产 `jobs_clean.csv`。改规则时重跑即可，原始数据始终可回溯。

### 去重策略

- 有 `job_id` 时用 `job_id + source` 作唯一键。
- 无 `job_id` 时用 `job_title + company_name + city` 组合键。
- 去重可在采集时做（维护一个 `seen` 集合），也可留到清洗层用 pandas 做。**推荐留到清洗层**——采集脚本越简单越稳。

### 断点续采（可选进阶）

- 简单做法：把已完成的页码写入 `progress.txt`，启动时读取断点继续。
- 更稳的做法：每页成功写入后立即 `flush`，进程被杀也不丢已采数据。

---

## 六、与后续环节的衔接

```
jobs_raw.csv（采集层产出，只读不改）
      ↓  clean_eda.py
jobs_clean.csv（薪资解析 / 学历经验归一化 / 去重 / 技能标签抽取）
      ↓  job_visualization.py
charts/*.png + 报告
```

采集层只做一件事：**忠实、完整、合规地把原文搬回来**。任何加工都放到清洗层，这样你的项目才是可复现、可审计的。

---

## 七、配套成品脚本：`job_crawler.py`

上面三、五两节的骨架，已实现为**完整可运行**的 `job_crawler.py`。脚本已在本机跑通验证。

### 三种运行方式

```bash
# 1) 演示模式：零依赖、零网络，立刻看到全流程效果
#    （不加任何参数直接点运行也会自动进入演示模式，适合 PyCharm / VS Code 里点 Run）
python job_crawler.py --demo

# 2) 解析本地 HTML：调试真实站点的选择器（强烈推荐先走这步）
python job_crawler.py --parse-local sample.html

# 3) 真实站点采集：需先装依赖
pip install requests beautifulsoup4
python job_crawler.py --url "https://目标站点/jobs" --keyword 大数据 --pages 10
```

### 常用参数

| 参数 | 说明 |
| --- | --- |
| `--demo` | 内置模拟数据，不发起网络请求 |
| `--parse-local FILE` | 解析本地 HTML，并打印首条记录各字段，便于核对选择器 |
| `--url URL` | 真实采集的目标搜索页 |
| `--keyword 关键词` | 检索关键词，默认"大数据" |
| `--pages N` | 最大页数，默认 3 |
| `--output FILE` | 输出 CSV，默认 `jobs_raw.csv` |
| `--min-delay / --max-delay` | 请求间隔秒数，默认 3.0 / 6.0 |
| `--resume` | 断点续采，跳过 `progress.txt` 中已完成的页 |
| `--skip-robots` | 跳过 robots 校验（**不推荐**，仅供教学调试） |

### 脚本已内置的能力

- **依赖降级**：装了 `bs4` 用它解析，没装就自动切到标准库 `html.parser` 自写的极简解析器，**保证任何环境都能跑起来**。
- **robots 校验**：真实采集前自动校验；读不到 robots.txt 时保守不采。
- **403/429 立即停止**：被识别就降温，不做重试硬刚。
- **去重**：以 `职位 + 公司 + 城市` 为键，跨页、跨次运行均生效。
- **断点续采**：每页完成即写入 `progress.txt`，中断后可 `--resume` 继续。
- **CSV 追加写**：`utf-8-sig` 编码，`newline=""`，首次自动写表头。
- **限速**：真实采集每页间隔 3–6 秒随机休眠。

### 接真实站点的三步

1. 浏览器打开目标搜索页 → 右键"另存为" → 存成 `sample.html`。
2. 用 F12 找到岗位卡片的真实 class，修改脚本顶部的 `CARD_SELECTOR` 与 `SELECTORS` 字典。
3. 反复执行 `python job_crawler.py --parse-local sample.html`（**不产生任何网络请求**），直到打印的字段值全部正确，再换 `--url` 上真实站点。

> 提示：跑真实采集前，先删除演示模式产生的 `jobs_raw.csv` 与 `progress.txt`，避免演示数据混入真实样本。

---

© 大数据招聘岗位数据分析 · 数据采集方案
