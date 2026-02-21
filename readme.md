# Notion Daily Report Generator (V7 - Ultimate Edition)

全自动 Notion 日报生成器。**Entity-First 设计**，由 DeepSeek AI 驱动的科技媒体级排版。
汇总html链接：https://redleafluan.github.io/ai_daily_report/index.html

## 🌟 核心亮点 (V7)
1.  **AI 智能重写**: 自动提取文章主角（如 `[OpenAI]`），标题更有吸引力。
2.  **知识库归档 (Web)**: 
    - 自动生成 `index.html` 时间轴。
    - **GitHub Pages 集成**: 支持自动推送代码到 GitHub，生成在线网站。
3.  **全自动流程**: 
    - 抓取 -> 分析 -> 生成 -> 归档 -> **Git Push** -> 飞书通知。
4.  **数据资产沉淀 (New!)**:
    - 自动生成 `JSON` 格式的结构化数据，为未来的 RAG/AI 分析做好数据储备。

## 🚀 快速开始

### 1. 文件夹结构
您的项目现在位于 `daily_report/` 文件夹中：
```
daily_report/
├── notion_daily_report.py  # 核心脚本
├── setup_schedule.py       # 自动化配置
├── reports/                # 历史存档 (HTML/MD/JSON)
└── index.html              # 知识库主页
```

### 2. 生成日报
进入目录并运行：
```bash
cd daily_report
python3 notion_daily_report.py
```

---
*Created by DeepMind Agent*
