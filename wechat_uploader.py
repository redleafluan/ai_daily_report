import os
import sys
import json
import datetime
import requests
import base64

# Configuration
APP_ID = os.environ.get("WECHAT_APP_ID")
APP_SECRET = os.environ.get("WECHAT_APP_SECRET")
GITHUB_PAGES_BASE = "https://redleafluan.github.io/ai_daily_report"

def get_access_token():
    """Get WeChat Access Token"""
    if not APP_ID or not APP_SECRET:
        print("❌ Missing WECHAT_APP_ID or WECHAT_APP_SECRET")
        return None
    
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APP_ID}&secret={APP_SECRET}"
    try:
        resp = requests.get(url)
        data = resp.json()
        if "access_token" in data:
            print("✅ WeChat Token/Auth Success")
            return data["access_token"]
        else:
            print(f"❌ WeChat Auth Failed: {data}")
            return None
    except Exception as e:
        print(f"❌ WeChat Auth Error: {e}")
        return None

def upload_cover_image(token):
    """Upload the default cover image."""
    # Try multiple possible paths to be robust
    possible_paths = [
        "daily_report/assets/cover.jpg", # From Repo Root (GitHub Actions)
        "assets/cover.jpg",              # From daily_report dir (Local)
        "/Users/hongyeluan/Desktop/antigravity/daily_report/assets/cover.jpg" # Absolute (Dev)
    ]
    
    cover_path = None
    for p in possible_paths:
        if os.path.exists(p):
            cover_path = p
            break
            
    if not cover_path:
        print(f"⚠️ Cover image missing in {possible_paths}. Generating Red Dot fallback.")
        img_data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAYAAABw4pVUAAAAdElEQVR4nO3TSw3AQAwEwTyd8EMP00P/FAy8DRw20MzA2fd79y/wf5AIEiGCRJAIESSCRIggESRCBIkgESJIhAgSQSJIhAgSQSJIhAgSQSJIhAgSQSJIhAgSQSJIhAgSQSJIhAgSQSJIhAgScwArWQE/qUu89AAAAABJRU5ErkJggg==")
        with open("temp_cover.png", "wb") as f:
            f.write(img_data)
        cover_path = "temp_cover.png"
        
    url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image"
    
    try:
        files = {'media': open(cover_path, 'rb')}
        resp = requests.post(url, files=files)
        data = resp.json()
        if "media_id" in data:
            print(f"✅ Cover Image Uploaded: {data['media_id']}")
            return data["media_id"]
        else:
            print(f"❌ Cover Upload Failed: {data}")
            return None
    except Exception as e:
        print(f"❌ Cover Upload Error: {e}")
        return None

def format_wechat_html(json_data, target_date):
    """Convert JSON to WeChat compatible HTML (Inline Styles)"""
    
    articles_data = json_data["articles"]
    
    # Handle Case 1: articles is a List (Old JSON or raw export) -> Group it now
    if isinstance(articles_data, list):
        grouped = {}
        mapping = {
            "Model Release": "🤖 模型与技术",
            "Technique": "🤖 模型与技术",
            "New Benchmark": "📊 评测与榜单",
            "Survey": "💡 深度观点",
            "Other": "📰 行业新闻"
        }
        for item in articles_data:
            cat_raw = item.get('category', 'Other')
            # Try to map if it matches keys, otherwise treat as value
            cat_display = mapping.get(cat_raw, cat_raw) 
            if cat_display not in grouped: grouped[cat_display] = []
            grouped[cat_display].append(item)
        articles_data = grouped
        total_count = sum(len(v) for v in articles_data.values())
    else:
        # Case 2: Dict
        total_count = sum(len(v) for v in articles_data.values())
    
    # Style optimized for WeChat Mobile
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333;">
        <h1 style="font-size: 22px; font-weight: bold; margin-bottom: 20px; text-align: center;">📅 AI Daily Report ({target_date})</h1>
        
        <div style="background-color: #f7f7f7; padding: 15px; border-radius: 8px; margin-bottom: 20px; font-size: 14px; color: #666;">
            共收录 <b>{total_count}</b> 篇精选内容。<br>
            <span style="color: #E74C3C;">🌟 今日看点：</span> {json_data.get('highlight', '暂无摘要')}
        </div>
    """
    
    preferred_order = ["🤖 模型与技术", "📰 行业新闻", "🧠 提示词与教程", "💡 深度观点", "🔧 工具与应用"]
    # Sort keys
    sorted_cats = sorted(articles_data.keys(), key=lambda x: preferred_order.index(x) if x in preferred_order else 99)
    
    for cat in sorted_cats:
        items = articles_data[cat]
        if not items: continue
        
        html += f"""
        <div style="margin-top: 30px; margin-bottom: 15px;">
            <span style="background-color: #2c3e50; color: #fff; padding: 5px 10px; border-radius: 4px; font-size: 16px; font-weight: bold;">{cat}</span>
        </div>
        """
        
        for item in items:
            entity_badge = f"<span style='color: #2980b9; font-weight: bold;'>[{item['entity']}]</span>" if item.get('entity') and item['entity'] != "Unknown" else ""
            clean_title = item.get('clean_title', item.get('title', 'No Title'))
            raw_title = item.get('raw_title', clean_title)
            summary = item.get('summary', 'No Summary')
            url = item.get('url', '')
            
            # Build the "文章：" link row if URL is available
            article_link_html = ""
            if url:
                article_link_html = f"""
                <div style="margin-top: 10px; font-size: 15px; color: #333;">
                    文章：<a href="{url}" style="color: #2980b9; text-decoration: none;">【{raw_title}】</a>
                </div>
                """
            
            html += f"""
            <section style="margin-bottom: 25px; border-bottom: 1px dashed #eee; padding-bottom: 15px;">
                <div style="font-size: 17px; font-weight: bold; margin-bottom: 8px; line-height: 1.4;">
                    {entity_badge} {clean_title}
                </div>
                <div style="font-size: 15px; color: #555; text-align: left;">
                    {summary}
                </div>
                {article_link_html}
            </section>
            """
            
    # Footer
    html += """
    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; text-align: center; color: #999; font-size: 12px;">
        <p>本文由 AI 自动聚合，摘要仅供参考。</p>
        <p>文章来源已汇总至完整版报告中。</p>
        <p>👇 点击下方 <strong>[阅读原文]</strong> 查看完整版及进行笔记划线</p>
    </div>
    </div>
    """
    return html

def upload_draft(token, media_id, html_content, target_date):
    """Upload article as Draft"""
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
    
    article_url = f"{GITHUB_PAGES_BASE}/daily_report_{target_date}.html"
    
    article_data = {
        "articles": [
            {
                "title": f"Daily AI Digest | 全网精选 ({target_date})",
                "author": "Antigravity",
                "digest": "AI 自动为您筛选今日最值得关注的科技动态。",
                "content": html_content,
                "content_source_url": article_url, # The "Read More" link
                "thumb_media_id": media_id,
                "need_open_comment": 1,
                "only_fans_can_comment": 0
            }
        ]
    }
    
    try:
        # Important: ensure utf-8 encoding
        resp = requests.post(url, data=json.dumps(article_data, ensure_ascii=False).encode('utf-8'))
        data = resp.json()
        if "media_id" in data:
            print(f"✅ Draft Created Successfully! Media ID: {data['media_id']}")
            return True
        else:
            print(f"❌ Draft Upload Failed: {data}")
            return False
    except Exception as e:
        print(f"❌ Draft Upload Error: {e}")
        return False

def main():
    target_date = sys.argv[1] if len(sys.argv) > 1 else datetime.datetime.now().strftime("%Y-%m-%d")
    json_path = f"reports/daily_report_{target_date}.json"
    
    # Try different paths to find the report
    possible_paths = [
        json_path,
        os.path.join(os.path.dirname(__file__), json_path),
        os.path.join("daily_report", json_path)
    ]
    
    final_json_path = None
    for p in possible_paths:
        if os.path.exists(p):
            final_json_path = p
            break

    if not final_json_path:
        print(f"⚠️ JSON report for {target_date} not found. Searched in: {possible_paths}")
        # Not finding a report is a valid case (e.g. no articles today), so just exit
        return

    print(f"🚀 Starting WeChat Upload for {target_date} from {final_json_path}...")
    
    # 1. Read JSON
    with open(final_json_path, "r", encoding="utf-8") as f:
        json_data = json.load(f)
        
    # 2. Get Token
    token = get_access_token()
    if not token: return
    
    # 3. Upload Cover
    media_id = upload_cover_image(token)
    if not media_id: return
    
    # 4. Generate HTML
    report_html = format_wechat_html(json_data, target_date)
    
    # 5. Upload Draft
    upload_draft(token, media_id, report_html, target_date)

if __name__ == "__main__":
    main()
