import os
import sys
import json
import requests
import base64
import markdown

APP_ID = os.environ.get("WECHAT_APP_ID")
APP_SECRET = os.environ.get("WECHAT_APP_SECRET")

def get_access_token():
    if not APP_ID or not APP_SECRET:
        print("Missing WECHAT_APP_ID or WECHAT_APP_SECRET")
        return None
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APP_ID}&secret={APP_SECRET}"
    try:
        resp = requests.get(url)
        data = resp.json()
        if "access_token" in data:
            print("WeChat Token OK")
            return data["access_token"]
        else:
            print(f"WeChat Auth Failed: {data}")
            return None
    except Exception as e:
        print(f"WeChat Auth Error: {e}")
        return None

def upload_cover_image(token):
    possible_paths = [
        "assets/cover.jpg",
        "daily_report/assets/cover.jpg",
    ]
    cover_path = None
    for p in possible_paths:
        if os.path.exists(p):
            cover_path = p
            break
    if not cover_path:
        print("Cover image missing. Using fallback.")
        img_data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAYAAABw4pVUAAAAdElEQVR4nO3TSw3AQAwEwTyd8EMP00P/FAy8DRw20MzA2fd79y/wf5AIEiGCRJAIESSCRIggESRCBIkgESJIhAgSQSJIhAgSQSJIhAgSQSJIhAgSQSJIhAgSQSJIhAgSQSJIhAgSQSJIhAgSQSJIhAgScwArWQE/qUu89AAAAABJRU5ErkJggg==")
        with open("temp_cover.png", "wb") as f:
            f.write(img_data)
        cover_path = "temp_cover.png"
    url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image"
    try:
        files = {"media": open(cover_path, "rb")}
        resp = requests.post(url, files=files)
        data = resp.json()
        if "media_id" in data:
            print(f"Cover uploaded: {data['media_id']}")
            return data["media_id"]
        else:
            print(f"Cover upload failed: {data}")
            return None
    except Exception as e:
        print(f"Cover upload error: {e}")
        return None

def format_html(md_text):
    html_content = markdown.markdown(md_text, extensions=["extra", "nl2br"])
    html = f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; font-size: 15px;">{html_content}</div>"""
    html = html.replace("<h2>", '<h2 style="font-size: 18px; color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 5px; margin-top: 30px;">')
    html = html.replace("<h3>", '<h3 style="font-size: 16px; color: #34495e; margin-top: 20px;">')
    html = html.replace("<p>", '<p style="margin-bottom: 15px; text-align: justify;">')
    html = html.replace("<ul>", '<ul style="padding-left: 20px; color: #555;">')
    html = html.replace("<a ", '<a style="color: #2980b9; text-decoration: none;" ')
    return html

def upload_draft(token, media_id, html_content, title):
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
    article_data = {
        "articles": [{
            "title": title,
            "author": "Antigravity",
            "digest": "AI curated weekly digest.",
            "content": html_content,
            "thumb_media_id": media_id,
            "need_open_comment": 1,
            "only_fans_can_comment": 0
        }]
    }
    try:
        resp = requests.post(url, data=json.dumps(article_data, ensure_ascii=False).encode("utf-8"))
        data = resp.json()
        if "media_id" in data:
            print(f"Draft created! Media ID: {data['media_id']}")
            return True
        else:
            print(f"Draft upload failed: {data}")
            return False
    except Exception as e:
        print(f"Draft upload error: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python wechat_md_uploader.py <markdown_file> [title]")
        return
    md_path = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else "Daily AI Digest"
    if not os.path.exists(md_path):
        print(f"Markdown file not found: {md_path}")
        return
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()
    token = get_access_token()
    if not token: return
    media_id = upload_cover_image(token)
    if not media_id: return
    html = format_html(md_text)
    upload_draft(token, media_id, html, title)

if __name__ == "__main__":
    main()
