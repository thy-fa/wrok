# 📊 大数据招聘岗位数据分析

> 一个面向求职的作品集项目：从**合规采集**到**数据驱动决策**的全流程实践。
> 作者：专科 · 大数据技术专业 · 大三 ｜ 技术栈：Python · requests · BeautifulSoup · pandas · matplotlib

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-CC%20BY--NC%204.0-green.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
[![Status](https://img.shields.io/badge/Status-完成-brightgreen.svg)]()

---

## 📌 项目一句话

用数据说话，把"大数据岗位到底招什么人、值多少钱、在哪招"讲清楚，为应届生求职决策提供量化依据。

## 🎯 业务目标

1. **市场画像** — 刻画岗位的区域 / 学历 / 经验需求分布
2. **技能提炼** — 构建技能需求图谱，定位学习优先级
3. **薪资预期** — 量化城市 / 学历 / 经验对薪资的影响
4. **方法论** — 沉淀可复用的全流程工程能力

## 🧱 技术架构（五层流水线）

```
采集(requests+bs4, robots校验/频率控制)
   ↓
存储(CSV, utf-8-sig, 追加写/断点续采)
   ↓
清洗(pandas: 去重/缺失/异常/类型)
   ↓
分析(pandas EDA: 描述统计/分组统计)
   ↓
可视化(matplotlib: 中文渲染/4张图)
```

## 📂 仓库结构

```
.
├── README.md              # 本文件（仓库首页）
├── index.html             # 网站首页（= 作品集网站，图表已内嵌，打开即看）
├── report.md              # 完整项目报告（标准 Markdown，含 GitHub Pages 发布步骤）
├── report.html            # 完整报告（自包含 HTML，图表已内嵌）
├── pitch_script.md        # 2 分钟面试口述稿
├── interview_qa.md        # 常见面试提问 + 参考回答
├── job_crawler_framework.py   # 采集框架（requests + bs4）
├── clean_eda.py               # 清洗与 EDA 脚本
├── job_visualization.py       # 可视化脚本
├── build_report.py            # 报告生成脚本
└── charts/                    # 4 张分析成品图
    ├── city_salary.png
    ├── edu_salary.png
    ├── exp_salary.png
    └── skill_freq.png
```

## 🚀 快速开始

```bash
# 1. 安装依赖（建议用虚拟环境）
pip install pandas matplotlib numpy requests beautifulsoup4

# 2. 数据清洗 + EDA（读取 jobs.csv，输出 jobs_clean.csv）
python clean_eda.py

# 3. 生成 4 张可视化图表到 charts/
python job_visualization.py

# 4.（可选）重新打包自包含 HTML 报告
python build_report.py
```

> ⚠️ 脚本默认在找不到 `jobs.csv` 时自动用**演示数据**兜底渲染，便于你先看效果；拿到真实数据后替换即可。

## 🔍 核心发现（示意，真实数据以报告为准）

- **地域**：高需求 + 高薪城市集群是投递优先战场。
- **学历**：本科是薪资拐点，但大专仍有可争取的水位。
- **经验**：0–3 年薪资斜率最陡，前两年聚焦能力积累。
- **技能**：Python + SQL + 1 个计算引擎 + 1 个 BI 工具是简历基线。

## ⚖️ 合规声明

- 本项目数据采集严格遵守目标站点 **robots 协议**与频率限制。
- **不采集**任何求职者个人隐私（简历、姓名、电话、身份证等）。
- 数据仅用于**学习与研究**，**不商用、不转售**。
- 遵守《个人信息保护法》《网络安全法》《数据安全法》。

## 📄 许可证

本项目文档与代码以 [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) 发布，禁止商业使用。

## 🌐 发布到 GitHub Pages（详细步骤）

本仓库为纯静态站点（含 `index.html` / `report.html` / `report.md` 与 `charts/`），GitHub Pages 可免费托管。以下两种方法任选其一。

### 方法一：网页上传（无需安装 Git）

1. **新建仓库**：登录 github.com → 右上角 **➕ → New repository** → 名称建议 `bigdata-job-analysis` → 可见性选 **Public** → 点 **Create repository**。
2. **上传文件**：进入仓库 → **Add file → Upload files** → 将本目录**全部文件与 `charts/` 文件夹**拖入上传（⚠️ 必须含 `charts/`，否则报告图片会裂）。
3. **提交**：底部填写说明（如"求职作品集：大数据招聘岗位数据分析"）→ **Commit changes**。
4. **开启 Pages**：仓库 **Settings → Pages → Build and deployment** → Source 选 **Deploy from a branch** → Branch 选 **main**、目录 **/(root)** → **Save**。
5. **访问**：等待 1–2 分钟，打开 `https://<你的用户名>.github.io/<仓库名>/`，首页即 `index.html`（完整报告，图表已内嵌）。

### 方法二：Git 命令行（推荐，便于后续更新）

```bash
cd "项目所在目录"
git init
git add .
git commit -m "求职作品集：大数据招聘岗位数据分析"
git branch -M main
git remote add origin https://github.com/<用户名>/<仓库名>.git
git push -u origin main
```

推送后按方法一第 4、5 步开启 Pages 即可。

### ⚠️ 常见问题排查

- **图片裂开**：确认 `charts/` 已一并上传；GitHub 路径大小写敏感，引用须为小写 `charts/city_salary.png`。
- **Pages 打不开**：检查 Settings → Pages 中 Branch=main、目录=/(root)；首次发布需等 1–2 分钟。
- **更新不生效**：重新 `git push`（方法二）或网页重新 Upload（方法一），Pages 会自动重建。
- **report.md 独立页**：GitHub Pages 会把它渲染为 `.../report.html`；`index.html` 作为首页优先级更高。

> 💡 `index.html` 已设为网站首页（自包含、图表内嵌，手机也能直接看）。报告图表基于**演示数据**渲染；拿到真实 `jobs_clean.csv` 后运行 `clean_eda.py → job_visualization.py → build_report.py` 重新生成并替换结论数值。

---

© 大数据招聘岗位数据分析 · 求职作品集项目
