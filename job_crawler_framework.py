"""
大数据招聘岗位数据采集框架（教学版）
技术栈：requests + BeautifulSoup(bs4) + csv
适用：专科大数据专业求职项目 / 课程设计

【重要合规声明】
1. 本脚本仅供学习交流，禁止商业用途或高频批量抓取。
2. 运行前请阅读目标网站的 robots.txt 与用户协议。
3. 仅采集公开的岗位信息，严禁采集任何个人隐私数据（如求职者简历）。
4. 控制请求频率，避免对目标服务器造成压力（详见下方频率参数）。
"""

import os
import time
import random
import csv
from typing import Optional, List, Dict
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup


# ===================== 0. 基础配置 =====================
# 目标站点（示例基准 URL，请替换为实际目标站点的搜索页）
BASE_URL = "https://example.com/jobs/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# 请求间隔（秒）：随机抖动，既降低被封风险，也体现合规意识
MIN_DELAY, MAX_DELAY = 2.0, 4.0
# 最大采集页数：学生练习建议小范围（如 10 页），避免大批量请求
MAX_PAGES = 10
# 单次请求重试次数
RETRIES = 3
# 输出文件名
OUTPUT_FILE = "jobs.csv"


# ===================== 1. robots.txt 合规校验 =====================
def can_fetch(url: str) -> bool:
    """检查目标 URL 是否被 robots 协议允许爬取。"""
    parsed = urlparse(url)
    rp = RobotFileParser()
    rp.set_url(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
    try:
        rp.read()
        allowed = rp.can_fetch(HEADERS["User-Agent"], url)
        if not allowed:
            print(f"[合规] robots.txt 禁止爬取：{url}")
        return allowed
    except Exception as e:
        # 读不到 robots 时，默认保守不爬取
        print(f"[合规] 无法读取 robots.txt（{e}），默认不爬取以保证合规。")
        return False


# ===================== 2. 单次 HTTP 请求（含重试） =====================
def fetch_page(url: str, params: Optional[Dict] = None) -> Optional[str]:
    """发起带重试机制的 GET 请求，返回页面 HTML 文本。"""
    for attempt in range(1, RETRIES + 1):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
            resp.encoding = resp.apparent_encoding  # 自动识别中文编码
            if resp.status_code == 200:
                return resp.text
            print(f"[重试 {attempt}/{RETRIES}] 状态码 {resp.status_code}")
        except requests.RequestException as e:
            print(f"[重试 {attempt}/{RETRIES}] 请求异常：{e}")
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
    return None


# ===================== 3. 页面解析（核心：bs4 提取字段） =====================
def parse_jobs(html: str) -> List[Dict]:
    """
    解析岗位列表页，提取每条岗位记录。
    注意：以下选择器为【示例占位】，必须使用浏览器开发者工具
    查看目标站点的真实 class / 标签后替换。
    """
    soup = BeautifulSoup(html, "html.parser")
    records: List[Dict] = []

    # TODO: 替换为真实的"岗位卡片"容器选择器，例如 soup.select('.job-card')
    job_cards = soup.select("div.job-item")

    for card in job_cards:
        # TODO: 每个字段按目标站点的真实结构替换选择器
        title = card.select_one(".job-title")
        company = card.select_one(".company-name")
        city = card.select_one(".city")
        salary = card.select_one(".salary")
        edu = card.select_one(".edu")
        exp = card.select_one(".experience")

        record = {
            "job_title": title.get_text(strip=True) if title else "",
            "company_name": company.get_text(strip=True) if company else "",
            "city": city.get_text(strip=True) if city else "",
            "salary_text": salary.get_text(strip=True) if salary else "",
            "education": edu.get_text(strip=True) if edu else "",
            "experience": exp.get_text(strip=True) if exp else "",
            "company_size": "",
            "industry": "",
            "skills": "",
            "job_description": "",
            "source": urlparse(BASE_URL).netloc,
            "crawl_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        records.append(record)
    return records


# ===================== 4. 保存为 CSV =====================
def save_to_csv(records: List[Dict], filename: str = OUTPUT_FILE) -> None:
    """
    将记录追加写入 CSV。
    - 使用 utf-8-sig 编码：保证 Excel 打开中文不乱码。
    - 文件不存在时写表头，存在时追加（不重复写表头）。
    """
    if not records:
        return
    fieldnames = records[0].keys()
    write_header = not os.path.exists(filename)
    with open(filename, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(records)
    print(f"[保存] 本次写入 {len(records)} 条 -> {filename}")


# ===================== 5. 主流程 =====================
def main() -> None:
    total = 0
    for page in range(1, MAX_PAGES + 1):
        params = {"keyword": "大数据", "page": page}
        # 合规校验：robots 不允许则跳过本页
        if not can_fetch(BASE_URL):
            print(f"[跳过] 站点未被 robots 允许，停止采集。")
            break
        html = fetch_page(BASE_URL, params=params)
        if not html:
            print(f"[结束] 第 {page} 页获取失败，停止采集。")
            break
        records = parse_jobs(html)
        if not records:
            print(f"[结束] 第 {page} 页无数据，可能已到末页。")
            break
        save_to_csv(records)
        total += len(records)
        print(f"[进度] 第 {page} 页完成，累计 {total} 条。")
        # 频率控制：每页之间随机休眠
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
    print(f"[完成] 共采集 {total} 条岗位数据，保存于 {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
