#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
==============================================================================
 和鲸社区「前程无忧-大数据岗位数据集」获取与标准化脚本（合规版）
==============================================================================

目标数据集：
  https://www.heywhale.com/mw/dataset/63ca209030f8a115ae718284
  前程无忧-大数据岗位数据集（2022-11 采集）
  - 清洗后.csv   3357 条 × 21 字段  → 适合直接做分析与可视化
  - job_all.csv  4100 条 × 15 字段  → 适合练习数据清洗

==============================================================================
【先说清楚一件事：本脚本为什么不自动下载文件】
==============================================================================

该站点 robots.txt 内容为：

    User-agent: *
    Allow: /
    Disallow: /api/
    Disallow: /org/
    Disallow: /static/

而和鲸的文件列表与下载接口全部位于 /api/ 之下，即**站点明确禁止自动化访问**。
同时数据集页面为 JS 动态渲染，文件直链不在 HTML 里，必须调 API 才能拿到——
也就是说：**任何"自动下载该数据集"的脚本，都必然违反 robots 协议。**

因此本脚本采取合规路径：

  ① 由你用浏览器正常登录、正常点击下载（普通用户行为，不受 robots 约束）；
  ② 下载后用本脚本读取、清洗、标准化，统一落盘为 jobs_raw.csv。

脚本同时提供 --check 与 --page 两个合规的网络功能：
  --check  拉取并解读 robots.txt，明确告诉你哪些路径能碰、哪些不能碰
  --page   抓取数据集页面 HTML（属 Allow 范围），提取元信息存档备查

脚本内置护栏：**任何 /api/ 路径的请求都会被主动拒绝**，防止误用。

==============================================================================
【三种运行方式】
==============================================================================

  # 1) 查看合规边界（推荐第一步）
  python heywhale_dataset_loader.py --check

  # 2) 抓取数据集页面元信息（合规，存档用）
  python heywhale_dataset_loader.py --page

  # 3) 处理你手动下载的数据文件（核心功能）
  python heywhale_dataset_loader.py --from-file 清洗后.csv
  python heywhale_dataset_loader.py --from-file job_all.csv --output jobs_raw.csv
  python heywhale_dataset_loader.py --from-dir ./downloads      # 批量处理整个目录

==============================================================================
"""

import sys
import os
import csv
import re
import glob
import time
import random
import argparse
from datetime import datetime
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 依赖检测：requests 缺失时降级到标准库 urllib，保证脚本任何环境都能跑
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib.request


# ==============================================================================
# 配置区
# ==============================================================================
DATASET_ID = "63ca209030f8a115ae718284"
DATASET_URL = f"https://www.heywhale.com/mw/dataset/{DATASET_ID}"
SITE_ROOT = "https://www.heywhale.com"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept-Language": "zh-CN,zh;q=0.9",
}

MIN_DELAY, MAX_DELAY = 3.0, 6.0   # 请求间隔（秒），宁慢勿快
TIMEOUT = 15
OUTPUT_FILE = "jobs_raw.csv"

# 常见中文 CSV 编码，逐个尝试，解决"打开是乱码"这个老大难问题
ENCODINGS = ["utf-8-sig", "utf-8", "gbk", "gb18030", "big5"]

# 字段角色猜测：用于自动识别薪资 / 城市 / 学历 / 经验等列（命中不了也不影响，只影响增值列）
ROLE_KEYWORDS = {
    "salary":     ["薪资", "工资", "薪酬", "待遇", "salary"],
    "city":       ["城市", "地点", "地区", "工作地", "city", "location"],
    "education":  ["学历", "education"],
    "experience": ["经验", "工作年限", "experience"],
    "job_title":  ["职位", "岗位", "招聘", "title", "job"],
    "company":    ["公司", "企业", "company"],
}


# ==============================================================================
# 合规护栏：robots 校验 + /api/ 硬拦截
# ==============================================================================
BLOCKED_PREFIXES = ("/api/", "/org/", "/static/")   # 与 robots.txt 的 Disallow 保持一致


def is_hard_blocked(url):
    """站点 robots.txt 明确禁止的路径前缀，直接拒绝，不打任何折扣。"""
    path = urlparse(url).path
    return any(path.startswith(p) for p in BLOCKED_PREFIXES)


def can_fetch(url):
    """robots 校验：读不到 robots.txt 时保守返回 False。"""
    parsed = urlparse(url)
    rp = RobotFileParser()
    rp.set_url(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
    try:
        rp.read()
    except Exception as e:
        log(f"[合规] 无法读取 robots.txt（{e}），默认不采集。")
        return False
    return rp.can_fetch(HEADERS["User-Agent"], url)


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def http_get(url, save_as=None):
    """
    合规 GET：先查护栏，再查 robots，最后才发请求。
    有 requests 用 requests，没有就用标准库 urllib 降级。
    """
    if is_hard_blocked(url):
        log(f"[拒绝] {urlparse(url).path} 属于站点 robots.txt 明令禁止的路径，已拦截。")
        log("       本脚本不提供任何绕过手段，请勿修改此护栏。")
        return None
    if not can_fetch(url):
        log(f"[拒绝] robots.txt 不允许访问：{url}")
        return None

    log(f"[请求] {url}")
    try:
        if HAS_REQUESTS:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if resp.status_code != 200:
                log(f"[失败] 状态码 {resp.status_code}")
                return None
            resp.encoding = resp.apparent_encoding
            text = resp.text
        else:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                raw = r.read()
            text = None
            for enc in ENCODINGS:
                try:
                    text = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if text is None:
                text = raw.decode("utf-8", errors="ignore")
    except Exception as e:
        log(f"[失败] 请求异常：{e}")
        return None

    if save_as:
        with open(save_as, "w", encoding="utf-8") as f:
            f.write(text)
        log(f"[保存] 页面已存为 {save_as}")
    return text


# ==============================================================================
# 功能一：--check 解读 robots 边界
# ==============================================================================
def cmd_check():
    log("=" * 62)
    log("合规检查：和鲸社区 robots 边界")
    log("=" * 62)
    parsed = urlparse(SITE_ROOT)
    rp = RobotFileParser()
    rp.set_url(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
    try:
        rp.read()
    except Exception as e:
        log(f"[提示] 本机未能联网读取 robots.txt（{e}）。")
        log("       已知规则（2026-10 核对）：Allow: / ；Disallow: /api/、/org/、/static/")
        return

    for path in ["/", f"/mw/dataset/{DATASET_ID}", "/api/", "/static/"]:
        allowed = rp.can_fetch(HEADERS["User-Agent"], SITE_ROOT + path)
        flag = "允许" if allowed else "禁止"
        note = ""
        if path == "/api/":
            note = "  ← 文件列表与下载接口全在这里，所以不能自动化下载"
        elif path.startswith("/mw/dataset"):
            note = "  ← 数据集详情页，可合规抓取元信息"
        log(f"  {flag}  {path}{note}")

    log("-" * 62)
    log("结论：数据集文件请手动下载（浏览器登录后点击下载），再用 --from-file 处理。")
    log("      脚本已内置 /api/ 硬拦截，任何自动化下载请求都会被拒绝。")


# ==============================================================================
# 功能二：--page 抓取数据集页面元信息（合规）
# ==============================================================================
def cmd_page():
    log("=" * 62)
    log("抓取数据集页面元信息（合规路径）")
    html = http_get(DATASET_URL, save_as="dataset_page.html")
    if html is None:
        log("[结束] 未能获取页面。若在离线环境，可先跳过此步，直接用 --from-file。")
        return

    meta = extract_meta(html)
    out = "dataset_meta.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["item", "value"])
        for k, v in meta.items():
            w.writerow([k, v])
    log(f"[完成] 元信息已写入 {out}：")
    for k, v in meta.items():
        log(f"        {k} = {v[:60]}")


def extract_meta(html):
    """从页面 HTML 中提取标题、简介等元信息（页面为 SPA，能提取到的信息有限）。"""
    meta = {}
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    meta["page_title"] = m.group(1).strip() if m else ""
    m = re.search(r'<meta[^>]+name="description"[^>]+content="(.*?)"', html, re.S)
    if not m:
        m = re.search(r'<meta[^>]+content="(.*?)"[^>]+name="description"', html, re.S)
    meta["description"] = m.group(1).strip() if m else ""
    meta["file_count_hint"] = str(len(re.findall(r"\.(?:csv|xlsx|xls|zip)", html, re.I)))
    meta["dataset_url"] = DATASET_URL
    meta["fetched_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return meta


# ==============================================================================
# 功能三：--from-file / --from-dir 读取本地文件并标准化
# ==============================================================================
def read_csv_any_encoding(path):
    """自动尝试多种编码读取 CSV，解决中文乱码。"""
    if not os.path.exists(path):
        log(f"[错误] 文件不存在：{path}")
        log("       请确认路径；文件名含中文或空格时，用引号包起来，例如：")
        log('       python heywhale_dataset_loader.py --from-file "清洗后.csv"')
        return [], ""
    for enc in ENCODINGS:
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                rows = list(csv.DictReader(f))
            if rows:
                log(f"[读取] {os.path.basename(path)} ｜ 编码 {enc} ｜ {len(rows)} 行")
                return rows, enc
        except UnicodeDecodeError:
            continue          # 换下一种编码再试，这是正常流程
        except Exception as e:
            log(f"[错误] 读取失败（{enc}）：{e}")
            break             # 非编码问题（权限、文件损坏等），不再重试
    log(f"[失败] 未能读取：{path}")
    return [], ""


def read_excel(path):
    """读取 xlsx；没装 openpyxl 时给出明确提示（数据集本身提供 csv，不必强求）。"""
    try:
        from openpyxl import load_workbook
    except ImportError:
        log("[提示] 读取 xlsx 需要 openpyxl：pip install openpyxl")
        log("       数据集同时提供 .csv 版本，直接用 csv 即可，无需额外依赖。")
        return []
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows_iter = ws.iter_rows(values_only=True)
    header = [str(c).strip() if c is not None else "" for c in next(rows_iter, [])]
    rows = []
    for r in rows_iter:
        if r is None or all(v is None for v in r):
            continue
        rows.append({header[i]: ("" if v is None else str(v)) for i, v in enumerate(r) if i < len(header)})
    wb.close()
    log(f"[读取] {os.path.basename(path)} ｜ {len(rows)} 行")
    return rows


def load_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        rows, _ = read_csv_any_encoding(path)
        return rows
    if ext in (".xlsx", ".xlsm"):
        return read_excel(path)
    if ext == ".xls":
        log("[提示] .xls 旧格式请先另存为 .xlsx 或 .csv 再处理。")
        return []
    log(f"[跳过] 不支持的格式：{path}")
    return []


# ---------- 薪资解析：把各种中文薪资写法统一成"月薪中位数（元）" ----------
_SALARY_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(万|千|[kK])?\s*(?:[-~至到]\s*(\d+(?:\.\d+)?)\s*(万|千|[kK])?)?"
)
_PERIOD_RE = re.compile(r"/?\s*(年|月|周|天|小时|时)")


def _unit_value(num_str, unit):
    """把 (数字, 单位) 折算成元。"""
    try:
        v = float(num_str)
    except ValueError:
        return None
    if unit in ("万",):
        return v * 10000
    if unit in ("千", "k", "K"):
        return v * 1000
    return v          # 无单位：视为元


def parse_salary(text):
    """
    解析薪资文本，返回 (月薪下限, 月薪上限, 月薪中位数)，单位：元/月。
    支持：1.5-2万/月 | 8千-1.2万/月 | 15-25K | 8000-12000 | 20万/年 | 面议
    解析不了返回 (None, None, None)。
    """
    if not text:
        return (None, None, None)
    s = str(text).strip()
    if "面议" in s or "不限" in s:
        return (None, None, None)

    m = _SALARY_RE.search(s)
    if not m:
        return (None, None, None)

    first_num, first_unit, second_num, second_unit = m.groups()
    if first_unit and second_unit:
        # 两边都写了单位（如"8千-1.2万"），各用各的
        lo = _unit_value(first_num, first_unit)
        hi = _unit_value(second_num, second_unit)
    else:
        # 只有一边写了单位（如"15-25K"、"1.5-2万"），整数区间共用同一个单位
        unit = first_unit or second_unit
        lo = _unit_value(first_num, unit)
        hi = _unit_value(second_num, unit) if second_num else lo
    if lo is None:
        return (None, None, None)
    if hi is None:
        hi = lo

    # 时间单位折算到"每月"
    pm = _PERIOD_RE.search(s)
    period = pm.group(1) if pm else "月"
    factor = {"月": 1.0, "年": 1 / 12, "周": 4.345, "天": 21.75, "小时": 174.0, "时": 174.0}.get(period, 1.0)
    lo, hi = lo * factor, hi * factor
    return (round(lo), round(hi), round((lo + hi) / 2))


def guess_roles(columns):
    """按关键词猜测每列的角色，猜不中就返回 None（不影响主流程）。"""
    roles = {}
    for col in columns:
        low = str(col).lower()
        for role, kws in ROLE_KEYWORDS.items():
            if any(kw in low for kw in kws):
                roles[col] = role
                break
    return roles


def dedup_key(rec):
    """去重键：优先职位+公司，缺列时退化为整行内容。"""
    keys = [rec.get(k, "") for k in ("job_title", "company_name", "职位", "公司", "公司名称")]
    keys = [k for k in keys if k]
    if not keys:
        keys = list(rec.values())[:3]
    return tuple(keys)


def standardize(rows, source_name):
    """
    标准化：去空白 → 补元字段 → 识别薪资列 → 去重。
    保留原始所有列（不擅自删列），新增列统一加在末尾。
    """
    if not rows:
        return [], {}, None

    columns = [c for c in rows[0].keys() if c]
    roles = guess_roles(columns)
    salary_col = next((c for c, r in roles.items() if r == "salary"), None)

    cleaned, seen = [], set()
    for r in rows:
        rec = {k: (str(v).strip() if v is not None else "") for k, v in r.items() if k}
        # 薪资解析（仅当识别到薪资列时）
        if salary_col:
            lo, hi, mid = parse_salary(rec.get(salary_col, ""))
            rec["salary_min"], rec["salary_max"], rec["salary_mid"] = (
                "" if lo is None else lo, "" if hi is None else hi, "" if mid is None else mid
            )
        rec["source"] = source_name
        rec["loaded_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        k = dedup_key(rec)
        if k in seen:
            continue
        seen.add(k)
        cleaned.append(rec)

    # 字段顺序：原列 + 新增列
    extra = ["salary_min", "salary_max", "salary_mid", "source", "loaded_at"]
    fieldnames = [c for c in columns] + [e for e in extra if salary_col or e in ("source", "loaded_at")]
    return cleaned, roles, fieldnames


def save_to_csv(records, fieldnames, out_path):
    if not records:
        return 0
    write_header = not os.path.exists(out_path)
    with open(out_path, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            w.writeheader()
        w.writerows(records)
    return len(records)


def cmd_from_file(path, output):
    rows = load_file(path)
    if not rows:
        log("[结束] 未读到任何数据。")
        return
    log(f"[字段] 原始列名（{len(rows[0])} 个）：")
    for c in rows[0].keys():
        log(f"        - {c}")

    cleaned, roles, fieldnames = standardize(rows, os.path.basename(path))
    n = save_to_csv(cleaned, fieldnames, output)
    log(f"[角色识别] {roles if roles else '未自动识别（不影响，可手动指定）'}")
    log(f"[完成] 读取 {len(rows)} 行 → 去重后写入 {n} 行 → {output}")
    if cleaned:
        log("[预览] 首条记录：")
        for k, v in list(cleaned[0].items())[:8]:
            log(f"        {k} = {v}")


def cmd_from_dir(dir_path, output):
    files = []
    for ext in ("*.csv", "*.xlsx", "*.xlsm"):
        files.extend(glob.glob(os.path.join(dir_path, ext)))
    if not files:
        log(f"[结束] 目录中没有 csv / xlsx 文件：{dir_path}")
        return
    log(f"[发现] {len(files)} 个文件：{', '.join(os.path.basename(f) for f in files)}")
    total = 0
    for f in files:
        log("-" * 62)
        cmd_from_file(f, output)
        total += 1
    log("=" * 62)
    log(f"[完成] 共处理 {total} 个文件，统一输出到 {output}")


# ==============================================================================
# 主流程
# ==============================================================================
def main():
    ap = argparse.ArgumentParser(
        description="和鲸「前程无忧-大数据岗位数据集」获取与标准化脚本（合规版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="典型用法：\n"
               "  python heywhale_dataset_loader.py --check\n"
               "  python heywhale_dataset_loader.py --page\n"
               "  python heywhale_dataset_loader.py --from-file 清洗后.csv\n"
               "  python heywhale_dataset_loader.py --from-dir ./downloads\n"
    )
    ap.add_argument("--check", action="store_true", help="检查 robots 边界（推荐第一步）")
    ap.add_argument("--page", action="store_true", help="抓取数据集页面元信息（合规路径）")
    ap.add_argument("--from-file", metavar="FILE", help="读取手动下载的 csv / xlsx 并标准化")
    ap.add_argument("--from-dir", metavar="DIR", help="批量读取目录下所有 csv / xlsx")
    ap.add_argument("--output", default=OUTPUT_FILE, help=f"输出 CSV，默认 {OUTPUT_FILE}")
    args = ap.parse_args()

    log("=" * 62)
    log("和鲸数据集 · 获取与标准化脚本")
    log(f"网络组件：{'requests' if HAS_REQUESTS else '标准库 urllib（可选装 requests）'}")

    # 未带参数时给出清晰指引（PyCharm 直接点 Run 也能看懂）
    if not (args.check or args.page or args.from_file or args.from_dir):
        log("[提示] 未指定操作，输出使用指引：")
        log("")
        log("  第一步  手动下载：浏览器打开数据集页面，登录并下载 清洗后.csv / job_all.csv")
        log(f"           {DATASET_URL}")
        log("")
        log("  第二步  标准化：  python heywhale_dataset_loader.py --from-file 清洗后.csv")
        log("")
        log("  合规自查：        python heywhale_dataset_loader.py --check")
        log("")
        log("[说明] 该站点 robots.txt 禁止 /api/，故脚本不提供自动下载，请勿绕过。")
        return

    if args.check:
        cmd_check()
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    if args.page:
        cmd_page()
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    if args.from_file:
        cmd_from_file(args.from_file, args.output)

    if args.from_dir:
        cmd_from_dir(args.from_dir, args.output)

    log("=" * 62)
    log("[下一步] 用 pandas 读取 jobs_raw.csv 做 EDA 与可视化。")


if __name__ == "__main__":
    main()
