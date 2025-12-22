import os
import requests
import datetime
import sys

# --- Configuration ---
# Secrets
HYPOTHESIS_TOKEN = os.environ.get("HYPOTHESIS_TOKEN")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DB_ID = os.environ.get("NOTION_NOTES_DB_ID") # New DB for Notes

# API Endpoints
HYP_API_URL = "https://api.hypothes.is/api/search"
NOTION_API_URL = "https://api.notion.com/v1/pages"

def get_hypothesis_annotations():
    """Fetch recent annotations from Hypothesis."""
    headers = {
        "Authorization": f"Bearer {HYPOTHESIS_TOKEN}",
        "Content-Type": "application/json"
    }
    # Get user's own annotations
    # We might want to filter by group later, but start with all "user" annotations
    params = {
        "user": "me", 
        "limit": 50,
        "order": "desc"
    }
    try:
        response = requests.get(HYP_API_URL, headers=headers, params=params)
        response.raise_for_status()
        return response.json().get('rows', [])
    except Exception as e:
        print(f"Error fetching Hypothesis: {e}")
        return []

def push_to_notion(annotation):
    """Create a page in Notion for the annotation."""
    
    # Extract Data
    uri = annotation.get('uri', '')
    text = "" # Quote
    comment = annotation.get('text', '') # User comment
    
    # Find the "TextQuoteSelector" to get the highlighted text
    targets = annotation.get('target', [])
    for t in targets:
        selectors = t.get('selector', [])
        for s in selectors:
            if s.get('type') == 'TextQuoteSelector':
                text = s.get('exact', '')
                break
    
    if not text and not comment:
        return # Skip empty ones

    # Construct Notion Payload (Basic)
    # Assumes DB has: 'Name' (Comment), 'Quote' (RichText), 'URL' (Url)
    # Adjust properties based on User's actual DB. 
    # For MVP, we use standard Title for Comment/Quote, and URL.
    
    # Title = Comment (or first 50 chars of quote if no comment)
    title_content = comment if comment else (text[:50] + "...")
    
    properties = {
        "Name": {"title": [{"text": {"content": title_content}}]}, # The main column
        "URL": {"url": uri},
        "Quote": {"rich_text": [{"text": {"content": text}}]},
        "Date": {"date": {"start": annotation['created'][:10]}} 
    }
    
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    # Check for duplication? (Skip for MVP, or check URL + content hash? fast impl: just push)
    # Real impl should query Notion to see if this ID exists. 
    # Hypothesis ID is in annotation['id'].
    # We should probably store Hypothesis ID in Notion to prevent dupes.
    
    payload = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": properties
    }
    
    try:
        # TODO: Add Deduplication logic here
        resp = requests.post(NOTION_API_URL, headers=headers, json=payload)
        # resp.raise_for_status() # Don't crash on one failure
        if resp.status_code == 200:
            print(f"✅ Synced: {title_content[:20]}")
        else:
            print(f"⚠️ Failed to sync: {resp.text}")
    except Exception as e:
        print(f"Error pushing to Notion: {e}")

if __name__ == "__main__":
    if not all([HYPOTHESIS_TOKEN, NOTION_TOKEN, NOTION_DB_ID]):
        print("Skipping Sync: Missing Credentials (HYPOTHESIS_TOKEN or NOTION_NOTES_DB_ID)")
        sys.exit(0) # Exit gracefully so we don't break the main workflow

    print("Starting Hypothesis Sync...")
    notes = get_hypothesis_annotations()
    print(f"Found {len(notes)} annotations.")
    
    for note in notes:
        push_to_notion(note)
    
    print("Sync Complete.")
