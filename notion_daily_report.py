import json
import urllib.request
import urllib.error
import urllib.parse
import ssl
import sys
import os
import subprocess
import requests
import datetime
import re
from collections import defaultdict
from html.parser import HTMLParser

# --- Configuration ---
NOTION_TOKEN = "ntn_W157212211790Of6npaBWZhhxxde9ti1FDcABWA2PLw2rR"
DATABASE_ID = "18005db4ae0580f08860ff2b20e42e44"
DEEPSEEK_API_KEY = "sk-4cd620c0fcfc49668c6b1e7b8c70c746"
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/6f7c6542-0818-4284-a925-25dadf5353db"

# Use today's date for filtering
TODAY = datetime.date.today().isoformat() 
# For production use:
# TODAY = datetime.date.today().isoformat()

# --- Helpers ---

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
    
    def handle_data(self, data):
        if data.strip():
            self.result.append(data.strip())
            
    def get_text(self):
        return " ".join(self.result)

def scrape_webpage(url):
    """Simple scraper to get text content from a URL."""
    print(f"   Drafting content from: {url[:50]}...")
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        # Spoof User-Agent to avoid 403s
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            html_content = response.read().decode('utf-8', errors='ignore')
            
            # Simple text extraction
            parser = TextExtractor()
            parser.feed(html_content)
            text = parser.get_text()
            
            # Truncate to avoid token limits (first 3000 chars is usually enough for summary)
            return text[:3000]
    except Exception as e:
        print(f"   [Scrape Error] {e}")
        return ""

def analyze_article_with_ai(title, content):
    """Call DeepSeek API to analyze article and return structured JSON."""
    if not content:
        return {
            "entity": "未知",
            "clean_title": title,
            "summary": "无法抓取内容，请手动查看。",
            "category": "其他"
        }
        
    print(f"   🤖 Asking DeepSeek to analyze: {title[:20]}...")
    
    prompt = f"""
    你是著名的科技媒体主编。请分析下面的文章，并返回一个 JSON 格式的结果。
    
    【文章标题】：{title}
    【文章正文（片段）】：{content[:2500]}
    
    【要求】：
    1. **entity**: 提取文章的核心主体（产品名/公司名/人名），如 "Gemini 3.0", "OpenAI", "Kimi"。不超过 15 个字符。
    2. **clean_title**: 重写一个吸引人的标题。要求：一句话，简练，突出新闻点。不要包含 Entity（因为我会把 Entity 拼在前面）。
    3. **summary**: 50-100字的深度摘要，风格犀利专业，吸引点击。
    4. **category**: 从以下列表中选择最匹配的一个分类：
       - "🤖 模型与技术" (Model Updates & Tech)
       - "🧠 提示词与教程" (Prompt Learning & Tutorials)
       - "📰 行业新闻" (Industry News)
       - "💡 深度观点" (Insights)
       - "🔧 工具与应用" (Tools & Apps)
    
    【返回格式】：
    仅返回合法的 JSON 字符串，不要包含 markdown 代码块标记。
    Example:
    {{
        "entity": "DeepSeek V3",
        "clean_title": "发布最强开源模型，性能对标 GPT-4",
        "summary": "...",
        "category": "🤖 模型与技术"
    }}
    """
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a professional AI news editor. You must response in JSON format."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 500,
        "response_format": { "type": "json_object" }
    }
    
    try:
        req = urllib.request.Request(
            DEEPSEEK_API_URL, 
            data=json.dumps(payload).encode('utf-8'),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
            }
        )
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(req, context=ctx, timeout=25) as response:
            result = json.loads(response.read().decode('utf-8'))
            content_str = result['choices'][0]['message']['content'].strip()
            # Clean potential markdown code blocks if AI ignores instruction
            if content_str.startswith("```json"):
                content_str = content_str[7:-3]
            try:
                data = json.loads(content_str)
                return data
            except json.JSONDecodeError:
                print("   [AI Error] Invalid JSON returned.")
                return {
                    "entity": "Unknown",
                    "clean_title": title,
                    "summary": content_str[:100], # Fallback to raw text
                    "category": "其他"
                }
            
    except Exception as e:
        print(f"   [AI Error] {e}")
        return {
            "entity": "Error",
            "clean_title": title,
            "summary": "AI 分析失败，请检查网络或 Key。",
            "category": "其他"
        }

# (Merged Layout Functions)

def generate_markdown(articles_by_category, highlight_desc, target_date):
    content = f"# 📅 Daily AI Report - {target_date}\n\n"
    
    # Section 1: Summary
    content += "## 1. 今日总结 (Daily Summary)\n"
    count = sum(len(v) for v in articles_by_category.values())
    content += f"今日共收录 **{count}** 篇内容。\n"
    content += f"> **今日看点**: {highlight_desc}\n\n"

    # Section 2: Feed (Waterfall)
    content += "## 2. 精选日报 (Daily Feed)\n"
    
    # Sort categories to ensure consistent order
    preferred_order = ["🤖 模型与技术", "📰 行业新闻", "🧠 提示词与教程", "💡 深度观点", "🔧 工具与应用"]
    sorted_cats = sorted(articles_by_category.keys(), key=lambda x: preferred_order.index(x) if x in preferred_order else 99)
    
    for cat in sorted_cats:
        items = articles_by_category[cat]
        if not items: continue
        
        content += f"### {cat}\n"
        for item in items:
            # Entity-First Title
            display_title = f"**[{item['entity']}]** {item['clean_title']}"
            
            content += f"#### {display_title}\n"
            content += f"*   🔗 [阅读原文]({item['url']})\n"
            content += f"*   📝 {item['summary']}\n"
            if item['time']:
                content += f"*   ⏰ *{item['time']}*\n"
            content += "\n"
        
    return content

def generate_html(articles_by_category, highlight_desc, target_date):
    # Calculate Total
    total_count = sum(len(v) for v in articles_by_category.values())
    
    html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Daily AI Report - {target_date}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; line-height: 1.6; color: #333; background-color: #f4f5f7; }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #eaeaea; padding-bottom: 15px; margin-bottom: 30px; text-align: center; }}
            
            /* Highlight Section (Full Width) */
            .highlight-box {{ 
                background-color: #fff; 
                border-top: 4px solid #E74C3C; 
                padding: 20px; 
                border-radius: 8px; 
                margin-bottom: 30px; 
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            }}
            .summary-title {{ font-weight: bold; color: #d35400; margin-bottom: 10px; font-size: 1.2em; }}
            
            /* Dashboard Grid (Masonry Layout) */
            .dashboard-grid {{
                column-count: 2;
                column-gap: 25px;
            }}
            
            /* Category Card */
            .category-card {{
                background: #fff;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                border: 1px solid #e1e4e8;
                margin-bottom: 25px; /* Spacing between items in column */
                break-inside: avoid; /* Prevent card from splitting across columns */
            }}
            
            .cat-header {{
                border-bottom: 2px solid #f0f0f0;
                padding-bottom: 10px;
                margin-bottom: 15px;
                font-size: 1.3em;
                font-weight: bold;
                color: #2c3e50;
            }}
            
            /* Article Item inside Category */
            .article-item {{
                padding-bottom: 15px;
                margin-bottom: 15px;
                border-bottom: 1px dashed #eee;
            }}
            .article-item:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
            
            .article-title-row {{ display: block; margin-bottom: 6px; line-height: 1.4; }}
            .entity-badge {{ 
                background: #e1ecf4; 
                color: #39739d; 
                padding: 2px 6px; 
                border-radius: 4px; 
                font-size: 0.8em; 
                font-weight: 600; 
                margin-right: 6px; 
                display: inline-block;
            }}
            
            .article-link {{ font-weight: bold; text-decoration: none; color: #2c3e50; font-size: 1.05em; }}
            .article-link:hover {{ color: #0366d6; }}
            
            .article-summary {{ font-size: 0.9em; color: #666; margin-top: 5px; }}
            .article-time {{ font-size: 0.8em; color: #bbb; margin-left: 5px; }}

            /* Mobile Responsiveness */
            @media (max-width: 768px) {{
                .dashboard-grid {{
                    column-count: 1;
                }}
            }}
        </style>
    </head>
    <body>
        <h1>📅 Daily AI Report</h1>
        <div class="meta-info">
            {target_date} | 共收录 <b>{total_count}</b> 篇精选内容
        </div>
        
        <div class="highlight-box">
            <div class="summary-title">🌟 今日看点 (Highlights)</div>
            <p>{highlight_desc}</p>
        </div>
        
        <div class="dashboard-grid">
    """
    
    # Sort categories
    preferred_order = ["🤖 模型与技术", "📰 行业新闻", "🧠 提示词与教程", "💡 深度观点", "🔧 工具与应用"]
    sorted_cats = sorted(articles_by_category.keys(), key=lambda x: preferred_order.index(x) if x in preferred_order else 99)
    
    for cat in sorted_cats:
        items = articles_by_category[cat]
        if not items: continue
        
        html += f"""
        <div class="category-card">
            <div class="cat-header">{cat}</div>
        """
        
        for item in items:
            html += f"""
            <div class="article-item">
                <div class="article-title-row">
                    <span class="entity-badge">{item['entity']}</span>
                    <a href="{item['url']}" target="_blank" class="article-link">{item['clean_title']}</a>
                    <span class="article-time">{item['time']}</span>
                </div>
                <div class="article-summary">
                    {item['summary']}
                </div>
            </div>
            """
        
        html += '</div>' # End category-card
            
    html += """
        </div> <!-- End dashboard-grid -->
    </body>
    </html>
    """
    return html

import argparse

# ... (Previous helper functions remain unchanged)

def get_daily_report(target_date):
    print(f"Generating enhanced AI report for: {target_date}...")
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    
    # Filter for items created on target_date
    payload = {
        "filter": {
            "property": "创建时间",
            "date": {
                "equals": target_date
            }
        },
        "sorts": [
            {
                "property": "创建时间",
                "direction": "ascending"
            }
        ]
    }
    
    # ... (Rest of logic uses target_date instead of TODAY)
    # Notion request setup
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    headers_notion = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    req = urllib.request.Request(url, headers=headers_notion, data=json.dumps(payload).encode('utf-8'))
    
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            data = json.loads(response.read().decode('utf-8'))
            results = data.get('results', [])
            
            if not results:
                print(f"No articles found for {target_date}.")
                return

            # --- Process Data ---
            articles = []
            categories = defaultdict(list)
            
            for page in results:
                props = page.get('properties', {})
                
                # Title (Raw)
                title_list = props.get('标题', {}).get('title', [])
                raw_title = title_list[0].get('plain_text', 'Untitled') if title_list else 'Untitled'
                print(f"Processing: {raw_title}")
                
                # URL
                url_prop = props.get('原链接', {}).get('url')
                if not url_prop:
                    url_prop = props.get('Cubox 深度链接', {}).get('url') or page.get('url')
                
                # Time
                created_time_prop = props.get('创建时间', {}).get('date', {})
                created_time_str = created_time_prop.get('start', '')
                time_display = created_time_str.split('T')[1][:5] if 'T' in created_time_str else ''

                # --- AI Analysis (One Shot) ---
                ai_data = None
                
                if url_prop:
                    raw_text = scrape_webpage(url_prop)
                    # Call new Analysis function
                    ai_data = analyze_article_with_ai(raw_title, raw_text)
                
                if not ai_data:
                    # Fallback if scrape failed
                    ai_data = {
                        "entity": "Unknown",
                        "clean_title": raw_title,
                        "summary": "无法抓取内容 (No Content)",
                        "category": "其他"
                    }

                article_data = {
                    "raw_title": raw_title,
                    "entity": ai_data.get('entity', 'Unknown'),
                    "clean_title": ai_data.get('clean_title', raw_title),
                    "summary": ai_data.get('summary', ''),
                    "url": url_prop,
                    "time": time_display,
                    "category": ai_data.get('category', '其他')
                }
                
                articles.append(article_data)
                categories[article_data['category']].append(article_data)

            # --- Remove Duplicates ---
            # Dedup by URL and Title
            unique_articles = []
            seen_urls = set()
            seen_titles = set()
            
            for art in articles:
                # Normalize URL (remove query params for looser matching if needed, but strict is safer for now)
                url = art['url']
                title = art['clean_title']
                
                if url in seen_urls:
                    print(f"Skipping duplicate URL: {title}")
                    continue
                if title in seen_titles:
                    print(f"Skipping duplicate Title: {title}")
                    continue
                    
                seen_urls.add(url)
                seen_titles.add(title)
                unique_articles.append(art)
            
            articles = unique_articles
            
            # Re-build categories with unique articles
            categories = defaultdict(list)
            for art in articles:
                categories[art['category']].append(art)

            # Sort within categories to group by Entity (Topic clustering) for better layout
            for cat in categories:
                # Sort by Entity (to group similar topics), then by Time
                # We use simple sorting: Entity A-Z, then Time
                categories[cat].sort(key=lambda x: x['entity'].lower())


            # --- Pick Highlight ---
            # Pick the longest summary as highlight for now
            highlight_desc = next((a['summary'] for a in articles if len(a['summary']) > 20), "今日主要涵盖了 AI 行业的最新动态。")

            # --- Save Data as JSON (Level 2: Structured Data) ---
            # This is for RAG/Algorithm usage
            report_data = {
                "date": target_date,
                "generated_at": datetime.datetime.now().isoformat(),
                "highlight": highlight_desc,
                "stats": {
                    "total_articles": len(articles),
                    "categories": {k: len(v) for k, v in categories.items()}
                },
                "articles": articles
            }
            json_file = os.path.join("reports", f"daily_report_{target_date}.json")
            os.makedirs("reports", exist_ok=True)
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            print(f"Saved {json_file} (Structured Data)")

            # --- Generate Markdown (V7) ---
            md_content = generate_markdown(categories, highlight_desc, target_date)
            # Save to reports/ folder
            md_file = os.path.join("reports", f"daily_report_{target_date}.md")
            os.makedirs("reports", exist_ok=True)
            
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(md_content)
            print(f"Saved {md_file}")

            # --- Generate HTML (V7) ---
            html_content = generate_html(categories, highlight_desc, target_date)
            # Save to reports/ folder
            html_file = os.path.join("reports", f"daily_report_{target_date}.html")
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"Saved {html_file}")
            
            # --- Update Index Page ---
            generate_index_page()
            
            # --- Git Auto-Push (GitHub Pages) ---
            git_push_changes(target_date)
            
            # --- Feishu Notification ---
            print("Sending Feishu notification...")
            # Note: We link to the report in the reports/ folder, but webhooks can't reach local.
            # We stick to the text summary card.  
            send_feishu_card(FEISHU_WEBHOOK, "AI日报", highlight_desc, categories, target_date)
            print("注意：受限于飞书 Webhook 权限，无法直接发送 HTML 文件，请查看飞书卡片中的链接内容。")

            # Auto-open the INDEX page locally (Best Experience)
            try:
                subprocess.run(["open", "index.html"])
            except:
                pass

    except Exception as e:
        print(f"Critical Error: {e}")

def send_feishu_card(webhook_url, title, summary, articles_by_category, target_date):
    """Send a structured Feishu Interactive Card."""
    print(f"Sending Feishu Card to {webhook_url}...")
    
    daily_url = f"{GITHUB_PAGES_BASE}reports/daily_report_{target_date}.html"
    
    # Calculate Total
    total_count = sum(len(v) for v in articles_by_category.values())

    # 1. Build Header
    card_content = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"📅 AI日报 | {target_date} (共{total_count}篇)"},
            "template": "blue"
        },
        "elements": [
            # Top Links
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md", 
                    "content": f"🏠 [访问知识库首页]({GITHUB_PAGES_BASE})  |  📄 [阅读今日完整日报 (Web)]({daily_url})"
                }
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**🌟 今日看点**\n{summary}"}
            },
            {"tag": "hr"}
        ]
    }
    
    # 2. Build Category Sections
    preferred_order = ["🤖 模型与技术", "📰 行业新闻", "🧠 提示词与教程", "💡 深度观点", "🔧 工具与应用"]
    sorted_cats = sorted(articles_by_category.keys(), key=lambda x: preferred_order.index(x) if x in preferred_order else 99)
    
    for cat in sorted_cats:
        items = articles_by_category[cat]
        if not items: continue
        
        # Category Title
        card_content["elements"].append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**{cat}**"}
        })
        
        # Articles Links
        # Feishu limits card size, so we list titles linked to URLs
        article_lines = []
        for item in items:
            # Format: [Entity] Title
            clean_t = item['clean_title'].replace("[", "【").replace("]", "】") # Escape brackets
            entity = item['entity']
            url = item['url']
            line = f"• **[{entity}]** [{clean_t}]({url})"
            article_lines.append(line)
        
        card_content["elements"].append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "\n".join(article_lines)}
        })
        card_content["elements"].append({"tag": "hr"})

    # 3. Footer
    card_content["elements"].append({
        "tag": "note",
        "elements": [{"tag": "plain_text", "content": f"Generated by AI Agent at {datetime.datetime.now().strftime('%H:%M')} | Note: File upload not supported via Webhook"}]
    })

    # Send Request
    payload = {
        "msg_type": "interactive",
        "card": card_content
    }
    
    try:
        resp = requests.post(webhook_url, json=payload)
        print(f"Feishu Response: {resp.text}")
    except Exception as e:
        print(f"Feishu Error: {e}")

def generate_index_page():
    """Scans reports/ folder and builds a Timeline Index Page."""
    print("Updating Index Page...")
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    
    # Find all HTML reports
    report_files = [f for f in os.listdir(reports_dir) if f.startswith("daily_report_") and f.endswith(".html")]
    report_files.sort(reverse=True) # Newest first
    
    timeline_items = []
    
    for filename in report_files:
        # Extract Date from filename: daily_report_YYYY-MM-DD.html
        try:
            date_str = filename.replace("daily_report_", "").replace(".html", "")
            
            # Read file to extract highlight
            path = os.path.join(reports_dir, filename)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Extract highlight using Regex (Robust)
            # Pattern: matches content inside <p> within highlight-box
            highlight = "点击查看详情..."
            match = re.search(r'<div class="highlight-box">.*?<p>(.*?)</p>', content, re.DOTALL)
            if match:
                highlight = match.group(1).strip()
            
            timeline_items.append({
                "date": date_str,
                "highlight": highlight,
                "link": f"reports/{filename}"
            })
        except Exception as e:
            print(f"Skipping {filename}: {e}")
            
    # Build HTML Index
    html = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🧠 My AI Knowledge Base</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 40px 20px; line-height: 1.6; color: #333; background-color: #f9f9f9; }
            header { text-align: center; margin-bottom: 50px; }
            h1 { color: #2c3e50; margin-bottom: 10px; }
            .subtitle { color: #7f8c8d; font-size: 1.1em; }
            
            .timeline { position: relative; max-width: 700px; margin: 0 auto; }
            .timeline::after { content: ''; position: absolute; width: 4px; background-color: #e9ecef; top: 0; bottom: 0; left: 20px; margin-left: -2px; }
            
            .card {
                position: relative;
                background-color: white;
                border-radius: 8px;
                padding: 20px;
                margin-left: 50px;
                margin-bottom: 30px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                border-left: 5px solid #3498db;
                transition: transform 0.2s;
            }
            .card:hover { transform: translateY(-2px); box-shadow: 0 8px 15px rgba(0,0,0,0.1); }
            
            .card::before {
                content: '';
                position: absolute;
                width: 16px; 
                height: 16px;
                left: -38px; /* Adjust based on margin-left */
                background-color: white;
                border: 4px solid #3498db;
                top: 20px;
                border-radius: 50%;
                z-index: 1;
            }
            
            .date-badge { 
                background: #3498db; 
                color: white; 
                padding: 4px 10px; 
                border-radius: 20px; 
                font-size: 0.85em; 
                font-weight: bold; 
                display: inline-block;
                margin-bottom: 10px;
            }
            
            .highlight-text { color: #555; margin-bottom: 15px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
            
            .read-btn { 
                display: inline-block; 
                text-decoration: none; 
                color: #3498db; 
                font-weight: bold; 
                border: 1px solid #3498db; 
                padding: 6px 15px; 
                border-radius: 4px; 
                font-size: 0.9em;
                transition: all 0.2s;
            }
            .read-btn:hover { background: #3498db; color: white; }
            
            .empty-state { text-align: center; color: #999; margin-top: 50px; }
        </style>
    </head>
    <body>
        <header>
            <h1>🧠 My AI Knowledge Base</h1>
            <div class="subtitle">Personal Archive of Daily AI Intelligence</div>
        </header>
        
        <div class="timeline">
    """
    
    if not timeline_items:
        html += '<div class="empty-state">No reports found via script. Run generation first.</div>'
    
    for item in timeline_items:
        html += f"""
            <div class="card">
                <div class="date-badge">{item['date']}</div>
                <div class="highlight-text">{item['highlight']}</div>
                <a href="{item['link']}" class="read-btn">Read Report →</a>
            </div>
        """
        
    html += """
        </div>
    </body>
    </html>
    """
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Index Page updated: index.html")

def git_push_changes(date_str):
    """Commits and pushes changes to GitHub."""
    print("🚀 Syncing with GitHub...")
    try:
        # Check if git is initialized
        if not os.path.exists(".git"):
            print("Git not initialized. Skipping push.")
            return

        subprocess.run(["git", "add", "."], check=True)
        # Use --allow-empty in case no changes
        subprocess.run(["git", "commit", "-m", f"Update report for {date_str}"], stderr=subprocess.DEVNULL) 
        subprocess.run(["git", "push"], check=True)
        print("✅ Successfully pushed to GitHub!")
    except Exception as e:
        print(f"⚠️ Git Push Failed: {e} (Ensure you have set up the repo first)")

if __name__ == "__main__":
    # Default to Yesterday (T-1 Mode) so morning runs capture the full previous day
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    
    parser = argparse.ArgumentParser(description="Notion Daily Report Generator")
    parser.add_argument("--date", type=str, default=yesterday, help="Date in YYYY-MM-DD format (default: yesterday)")
    args = parser.parse_args()
    
    get_daily_report(args.date)
