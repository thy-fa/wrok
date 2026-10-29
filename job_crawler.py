#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
==============================================================================
 大数据招聘岗位数据采集脚本（完整可运行版）
==============================================================================

【三种运行方式】

  1) 演示模式（零依赖、零网络，拿来就能跑，用于验证全流程）
     python job_crawler.py --demo

  2) 解析本地 HTML（调试真实站点时强烈推荐先用这个）
     用浏览器把目标页面"另存为" sample.html，然后：
     python job_crawler.py --parse-local sample.html

  3) 真实站点采集（需先安装依赖）
     pip install requests beautifulsoup4
     python job_crawler.py --url "https://目标站点/jobs" --keyword 大数据 --pages 10

【合规声明 · 使用前必读】
  1. 本脚本仅供学习研究，禁止商业用途与高频批量抓取。
  2. 采集前请阅读目标站点的 robots.txt 与用户协议；脚本默认开启 robots 校验。
  3. 仅采集企业公开的岗位信息，严禁采集求职者简历、联系方式等个人隐私。
  4. 请求间隔默认 3~6 秒随机休眠，不使用代理池、不并发。
  5. 遇到 403 / 429 立即停止，不做绕过、不破解验证码。

【输出】
  jobs_raw.csv（utf-8-sig 编码，Excel 直接打开不乱码；追加写，支持断点续采）
==============================================================================
"""

import sys
import os
import csv
import time
import random
import argparse
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

# Windows 控制台默认 GBK，中文 print 可能报错，这里强制 UTF-8 输出
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# ==============================================================================
# 依赖检测：requests / bs4 缺失时自动降级，保证脚本"至少能跑起来"
# ==============================================================================
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


# ==============================================================================
# 配置区：改这里就行，不需要动下面的逻辑
# ==============================================================================

# 请求头（把 User-Agent 换成你自己浏览器的，F12 → Network → 任意请求 → 复制）
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# CSS 选择器映射：采集真实站点前，用浏览器 F12 查看真实 class 后替换
# 格式："字段名": "CSS 选择器"（相对岗位卡片内部）
SELECTORS = {
    "job_title":    ".job-title",      # 职位名称
    "company_name": ".company-name",   # 公司名称
    "city":         ".city",           # 工作城市
    "salary_text":  ".salary",         # 薪资原文（保留原样，清洗阶段再解析）
    "education":    ".edu",            # 学历要求
    "experience":   ".exp",            # 经验要求
    "company_size": ".size",           # 公司规模
    "industry":     ".industry",       # 所属行业
    "publish_date": ".pub-date",       # 发布日期
}
CARD_SELECTOR = "div.job-item"         # 岗位卡片容器选择器

# CSV 字段顺序（固定，不能改顺序；新增字段请追加到末尾）
FIELDNAMES = [
    "job_title", "company_name", "city", "salary_text",
    "education", "experience", "company_size", "industry",
    "publish_date", "source", "keyword", "page_url", "crawl_time",
]

MIN_DELAY, MAX_DELAY = 3.0, 6.0   # 真实采集的请求间隔（秒），宁慢勿快
RETRIES = 3                        # 单次请求最大重试次数
TIMEOUT = 10                       # 单次请求超时（秒）
OUTPUT_FILE = "jobs_raw.csv"       # 输出文件名
PROGRESS_FILE = "progress.txt"     # 断点续采进度文件


# ==============================================================================
# 零依赖降级解析器：没装 bs4 时用标准库 html.parser 顶上
# 支持的选择器语法： "tag" / ".class" / "tag.class"
# ==============================================================================
_VOID_TAGS = {"br", "img", "meta", "link", "input", "hr", "source"}


class _Node:
    """极简 DOM 节点：只保留标签名、class、文本和子节点。"""
    __slots__ = ("tag", "classes", "children", "text")

    def __init__(self, tag):
        self.tag = tag
        self.classes = []
        self.children = []
        self.text = ""

    def all_text(self):
        """拼接自身及所有后代的文本。"""
        buf = [self.text]
        for child in self.children:
            buf.append(child.all_text())
        return "".join(buf)


class _MiniParser(HTMLParser):
    """把 HTML 解析成一棵极简节点树。"""
    def __init__(self):
        super().__init__()
        self.root = _Node("root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = _Node(tag)
        for k, v in attrs:
            if k == "class" and v:
                node.classes = v.split()
        self.stack[-1].children.append(node)
        if tag not in _VOID_TAGS:
            self.stack.append(node)

    def handle_endtag(self, tag):
        # 从栈顶向下找最近的同名开标签并弹栈（容错不规范的 HTML）
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if self.stack:
            self.stack[-1].text += data


def _match(node, tag, cls):
    return (tag is None or node.tag == tag) and (cls is None or cls in node.classes)


def _find_all(node, tag, cls, out):
    for child in node.children:
        if _match(child, tag, cls):
            out.append(child)
        _find_all(child, tag, cls, out)
    return out


def _parse_selector(selector):
    """把 "div.job-item" / ".job-title" / "div" 拆成 (tag, cls)。"""
    selector = selector.strip()
    if "." in selector:
        tag, _, cls = selector.partition(".")
        return (tag or None), cls
    return selector, None


def parse_with_stdlib(html):
    """零依赖解析：返回 [{字段: 值}, ...]。"""
    parser = _MiniParser()
    parser.feed(html)
    card_tag, card_cls = _parse_selector(CARD_SELECTOR)
    cards = _find_all(parser.root, card_tag, card_cls, [])

    records = []
    for card in cards:
        record = {}
        for field, selector in SELECTORS.items():
            tag, cls = _parse_selector(selector)
            hits = _find_all(card, tag, cls, [])
            # 取第一个命中的节点文本；找不到就填空字符串，绝不抛异常
            record[field] = hits[0].all_text().strip() if hits else ""
        records.append(record)
    return records


def parse_with_bs4(html):
    """bs4 解析（依赖已安装时优先走这条路，容错性更好）。"""
    soup = BeautifulSoup(html, "html.parser")
    records = []
    for card in soup.select(CARD_SELECTOR):
        record = {}
        for field, selector in SELECTORS.items():
            node = card.select_one(selector)
            # 关键：select_one 可能返回 None，直接 .get_text() 会崩
            record[field] = node.get_text(strip=True) if node else ""
        records.append(record)
    return records


def parse_jobs(html):
    """统一解析入口：有 bs4 用 bs4，没有就用标准库降级方案。"""
    if HAS_BS4:
        return parse_with_bs4(html)
    return parse_with_stdlib(html)


# ==============================================================================
# 演示数据：内置 3 页模拟 HTML，用来在无网络、无依赖时验证全流程
# ==============================================================================
def _demo_page(page_no):
    """返回第 page_no 页的模拟 HTML；第 3 页返回空列表页，用于验证"末页终止"逻辑。"""
    def card(title, company, city, salary, edu, exp, size, industry, pub):
        return f"""
        <div class="job-item">
            <span class="job-title">{title}</span>
            <span class="company-name">{company}</span>
            <span class="city">{city}</span>
            <span class="salary">{salary}</span>
            <span class="edu">{edu}</span>
            <span class="exp">{exp}</span>
            <span class="size">{size}</span>
            <span class="industry">{industry}</span>
            <span class="pub-date">{pub}</span>
        </div>"""

    page1 = card("大数据开发工程师", "示例科技A", "北京", "15-25K·13薪", "本科", "3-5年", "500-999人", "互联网", "2026-10-20") + \
            card("数据仓库工程师", "示例科技B", "上海", "18-30K", "本科", "1-3年", "1000-9999人", "电子商务", "2026-10-21") + \
            card("数据分析师", "示例科技C", "深圳", "12-20K", "大专", "1-3年", "100-499人", "金融科技", "2026-10-22") + \
            card("ETL开发工程师", "示例科技D", "杭州", "14-22K·14薪", "本科", "3-5年", "500-999人", "企业服务", "2026-10-23") + \
            card("大数据平台运维", "示例科技E", "成都", "10-16K", "大专", "1-3年", "100-499人", "信息安全", "2026-10-24") + \
            card("Spark开发工程师", "示例科技F", "北京", "20-35K", "本科", "5年以上", "10000人以上", "互联网", "2026-10-25")

    page2 = card("大数据开发工程师", "示例科技A", "北京", "15-25K·13薪", "本科", "3-5年", "500-999人", "互联网", "2026-10-20") + \
            card("数据挖掘工程师", "示例科技G", "广州", "16-28K", "硕士及以上", "3-5年", "1000-9999人", "人工智能", "2026-10-26") + \
            card("BI报表开发", "示例科技H", "成都", "9-15K", "大专", "应届", "20-99人", "企业服务", "2026-10-27")

    bodies = {1: page1, 2: page2, 3: ""}   # 第 3 页为空 → 触发"本页无数据，已到末页"
    body = bodies.get(page_no, "")
    return f'<html><body><div class="job-list">{body}</div></body></html>'


# ==============================================================================
# 采集核心函数
# ==============================================================================
def log(msg):
    """带时间戳的日志输出，方便观察节奏与排查问题。"""
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def can_fetch(url):
    """
    robots 协议校验：不允许就返回 False。
    读不到 robots.txt 时保守返回 False —— 宁可不采，也不冒风险。
    """
    parsed = urlparse(url)
    rp = RobotFileParser()
    rp.set_url(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
    try:
        rp.read()
    except Exception as e:
        log(f"[合规] 无法读取 robots.txt（{e}），默认不采集。")
        return False
    allowed = rp.can_fetch(HEADERS["User-Agent"], url)
    if not allowed:
        log("[合规] robots.txt 禁止采集该路径，已终止。")
    return allowed


def fetch_page(session, url, params, min_delay, max_delay):
    """
    抓取单页 HTML。
    - 200 返回文本；
    - 403/429 立即放弃（已被识别，继续只会加重风险）；
    - 其他状态码与网络异常则重试，最多 RETRIES 次。
    """
    for attempt in range(1, RETRIES + 1):
        try:
            resp = session.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            if resp.status_code == 200:
                resp.encoding = resp.apparent_encoding   # 中文站点常需自动识别编码
                return resp.text
            if resp.status_code in (403, 429):
                log(f"[停止] 状态码 {resp.status_code}，疑似被限制，放弃本页。")
                return None
            log(f"[重试 {attempt}/{RETRIES}] 状态码 {resp.status_code}")
        except Exception as e:
            log(f"[重试 {attempt}/{RETRIES}] 请求异常：{e}")
        time.sleep(random.uniform(min_delay, max_delay))
    return None


def make_record(raw, source, keyword, page_url):
    """补齐元字段，保证字段顺序与 FIELDNAMES 完全一致。"""
    record = {field: raw.get(field, "") for field in SELECTORS.keys()}
    record["source"] = source
    record["keyword"] = keyword
    record["page_url"] = page_url
    record["crawl_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {k: record.get(k, "") for k in FIELDNAMES}


def dedup_key(record):
    """去重键：优先岗位标题 + 公司 + 城市。有站点 job_id 时可替换为此处。"""
    return (record.get("job_title", ""), record.get("company_name", ""), record.get("city", ""))


def load_seen(csv_path):
    """从已有 CSV 读取去重键，支持断点续采时不重复入库。"""
    seen = set()
    if not os.path.exists(csv_path):
        return seen
    try:
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                seen.add((row.get("job_title", ""), row.get("company_name", ""), row.get("city", "")))
    except Exception as e:
        log(f"[提示] 读取已有 CSV 失败（{e}），将不启用去重。")
    return seen


def save_to_csv(records, csv_path):
    """追加写入 CSV；文件不存在时先写表头。utf-8-sig 保证 Excel 中文不乱码。"""
    if not records:
        return 0
    write_header = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerows(records)
    return len(records)


def load_progress():
    """读取断点：已完成页码集合。"""
    if not os.path.exists(PROGRESS_FILE):
        return set()
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return {int(line.strip()) for line in f if line.strip().isdigit()}
    except Exception:
        return set()


def mark_progress(page):
    """记录已完成页码，进程被杀也不会丢进度。"""
    with open(PROGRESS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{page}\n")


# ==============================================================================
# 主流程
# ==============================================================================
def main():
    ap = argparse.ArgumentParser(
        description="大数据招聘岗位数据采集脚本（完整可运行版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例：\n"
               "  python job_crawler.py --demo\n"
               "  python job_crawler.py --parse-local sample.html\n"
               '  python job_crawler.py --url "https://xxx/jobs" --keyword 大数据 --pages 10\n'
    )
    ap.add_argument("--demo", action="store_true", help="演示模式：内置模拟数据，无需网络与依赖")
    ap.add_argument("--parse-local", metavar="FILE", help="解析本地 HTML 文件（调试选择器用）")
    ap.add_argument("--url", help="目标站点搜索页 URL（真实采集）")
    ap.add_argument("--keyword", default="大数据", help="检索关键词，默认 大数据")
    ap.add_argument("--pages", type=int, default=3, help="最大采集页数，默认 3")
    ap.add_argument("--output", default=OUTPUT_FILE, help=f"输出 CSV 文件名，默认 {OUTPUT_FILE}")
    ap.add_argument("--min-delay", type=float, default=MIN_DELAY, help="最小请求间隔（秒）")
    ap.add_argument("--max-delay", type=float, default=MAX_DELAY, help="最大请求间隔（秒）")
    ap.add_argument("--resume", action="store_true", help="断点续采：跳过已完成的页码")
    ap.add_argument("--skip-robots", action="store_true", help="跳过 robots 校验（不推荐，仅供教学调试）")
    args = ap.parse_args()

    log("=" * 60)
    log("大数据招聘岗位数据采集 启动")
    log(f"解析引擎：{'BeautifulSoup' if HAS_BS4 else '标准库解析器（未装 bs4，功能正常，可选安装）'}")

    # ---------- 未带参数时自动进入演示模式 ----------
    # 这样在 PyCharm / VS Code 里直接点 Run（不带任何命令行参数）也能跑出结果，
    # 不会卡在"请指定运行方式"。需要真实采集时再配置运行参数即可。
    if not (args.demo or args.url or args.parse_local):
        log("[提示] 未指定运行方式，已自动进入演示模式。")
        log('       真实采集：--url "https://目标站点/jobs"  调试选择器：--parse-local sample.html')
        args.demo = True

    # ---------- 模式一：解析本地 HTML（调试选择器专用） ----------
    if args.parse_local:
        if not os.path.exists(args.parse_local):
            log(f"[错误] 文件不存在：{args.parse_local}")
            return
        with open(args.parse_local, "r", encoding="utf-8") as f:
            html = f.read()
        records = [make_record(r, "local-file", "debug", args.parse_local) for r in parse_jobs(html)]
        n = save_to_csv(records, args.output)
        log(f"[完成] 本地解析到 {len(records)} 条，写入 {n} 条 -> {args.output}")
        if records:
            log("[预览] 首条记录：")
            for k, v in records[0].items():
                log(f"        {k} = {v}")
        return

    # ---------- 模式二：演示模式 ----------
    if args.demo:
        log("[模式] 演示模式：使用内置模拟数据，不发起任何网络请求。")
        session = None
        source, base_url = "demo", "demo://local"
        min_delay, max_delay = 0.3, 0.8    # 演示模式缩短延时，避免干等
    # ---------- 模式三：真实站点采集 ----------
    elif args.url:
        if not HAS_REQUESTS:
            log("[错误] 真实采集需要 requests，请先执行：pip install requests beautifulsoup4")
            return
        source, base_url = urlparse(args.url).netloc, args.url
        min_delay, max_delay = args.min_delay, args.max_delay
        if not args.skip_robots and not can_fetch(args.url):
            log("[终止] 未通过 robots 校验。若确认合规可加 --skip-robots，但请自行承担风险。")
            return
        session = requests.Session()
        session.headers.update(HEADERS)
        log(f"[模式] 真实采集：{args.url} ｜ 关键词：{args.keyword} ｜ 间隔 {min_delay}~{max_delay}s")
    else:
        log("[错误] 请指定运行方式：--demo（演示） / --parse-local FILE（调试） / --url URL（真实采集）")
        log("       查看帮助：python job_crawler.py -h")
        return

    # ---------- 通用采集循环 ----------
    seen = load_seen(args.output)
    done_pages = load_progress() if args.resume else set()
    total_new = total_skip = 0

    for page in range(1, args.pages + 1):
        if page in done_pages:
            log(f"[跳过] 第 {page} 页已完成（断点续采）。")
            continue

        # 取页面 HTML：演示模式取内置数据，真实模式发起请求
        if args.demo:
            html = _demo_page(page)
            page_url = f"demo://local/page/{page}"
        else:
            page_url = f"{base_url}?keyword={args.keyword}&page={page}"
            html = fetch_page(session, base_url, {"keyword": args.keyword, "page": page},
                              min_delay, max_delay)

        if html is None:
            log("[结束] 本页获取失败，停止采集。")
            break

        raw_list = parse_jobs(html)
        if not raw_list:
            log(f"[结束] 第 {page} 页无数据，可能已到末页。")
            break

        # 逐条去重并补齐元字段
        records, dup = [], 0
        for raw in raw_list:
            rec = make_record(raw, source, args.keyword, page_url)
            key = dedup_key(rec)
            if key in seen:
                dup += 1
                continue
            seen.add(key)
            records.append(rec)

        written = save_to_csv(records, args.output)
        total_new += written
        total_skip += dup
        mark_progress(page)
        log(f"[进度] 第 {page} 页：解析 {len(raw_list)} 条，新增 {written} 条，重复 {dup} 条。")

        # 页间限速——真实采集时必须保留
        time.sleep(random.uniform(min_delay, max_delay))

    log("=" * 60)
    log(f"[完成] 新增 {total_new} 条，跳过重复 {total_skip} 条，输出文件：{args.output}")
    if not HAS_BS4:
        log("[可选] 当前用标准库解析，已足够本项目使用；如需更强容错可 pip install beautifulsoup4。")
    log("[下一步] 运行清洗脚本，把 jobs_raw.csv 加工为 jobs_clean.csv。")


if __name__ == "__main__":
    main()
