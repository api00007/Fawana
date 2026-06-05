import requests
import re
import json
import random
import time
import os
from datetime import datetime
import pytz
from collections import OrderedDict

# --- সেটিংস ---
BASE_URL = "http://www.fawanews.sc/"
OUTPUT_FILE = "fawna.json" 

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://www.google.com/"
}

# কি-ওয়ার্ড
NEWS_KEYWORDS = ["announce", "retirement", "chief", "report", "confirm", "interview", "says", "warns", "exit", "driver", "reserve", "statement", "suspension", "injury"]
MATCH_KEYWORDS = [" vs ", " v ", "cup", "league", "atp", "wta", "golf", "sport", "cricket", "football", "tennis", "tour", "nba", "basketball", "race", "prix", "match", "live"]

def get_ist_time():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).strftime('%d/%m/%y %H:%M:%S IST')

def push_to_github():
    print(f"[-] একই GitHub রিপোজিটরিতে {OUTPUT_FILE} আপডেট করা হচ্ছে...")
    try:
        # রানারের অটোমেটিক বিল্ট-ইন গিট ট্র্যাকিং ব্যবহার করা হচ্ছে
        os.system('git config user.name "github-actions[bot]"')
        os.system('git config user.email "41898282+github-actions[bot]@users.noreply.github.com"')
        
        os.system(f"git add {OUTPUT_FILE}")
        os.system(f'git commit -m "Update {OUTPUT_FILE} only: {get_ist_time()}" || echo "No changes"')
        os.system("git push origin main")
        
        print(f"[SUCCESS] একই রিপোজিটরিতে {OUTPUT_FILE} আপডেট সম্পন্ন।")
    except Exception as e:
        print(f"[ERROR] পুশ ফেইল: {e}")

def fetch_proxies():
    print("[-] প্রক্সি সংগ্রহ করা হচ্ছে...")
    try:
        url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=2000&country=us,gb&ssl=all&anonymity=all"
        res = requests.get(url, timeout=5)
        return [p.strip() for p in res.text.strip().split('\n') if p.strip()]
    except: return []

def run_automation():
    proxies = fetch_proxies()
    random.shuffle(proxies)
    
    trial_proxies = proxies[:5] + [None] 
    match_list = []
    session = requests.Session()
    session.headers.update(HEADERS)
    found_any = False

    for proxy in trial_proxies:
        if proxy:
            session.proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            timeout_val = 6
        else:
            session.proxies = {}
            timeout_val = 10
            print("[-] সরাসরি সংযোগ (Direct Connection) চেষ্টা করা হচ্ছে...")

        try:
            res = session.get(BASE_URL, timeout=timeout_val)
            if res.status_code == 200 and "fawanews" in res.text.lower():
                links_data = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', res.text, re.S)
                seen_links = set()
                for href, full_text in links_data:
                    clean_text = re.sub('<[^<]+?>', '', full_text).strip()
                    text_lower = clean_text.lower()
                    
                    if any(bad in text_lower for bad in NEWS_KEYWORDS): continue
                    
                    if any(k in text_lower for k in MATCH_KEYWORDS) or " vs " in text_lower:
                        if href not in seen_links:
                            full_url = href if href.startswith("http") else BASE_URL.rstrip("/") + "/" + href.lstrip("/")
                            lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
                            rivals = lines[0] if lines else "Match"
                            title = lines[1] if len(lines) >= 2 else "Live"
                            
                            try:
                                m_res = session.get(full_url, timeout=5)
                                m3u8_links = list(dict.fromkeys(re.findall(r'["\']([^"\']+\.m3u8[^'\"]*)['\"]', m_res.text)))
                                if m3u8_links:
                                    for idx, m3u8 in enumerate(m3u8_links, 1):
                                        match_list.append({
                                            "Id": str(len(match_list) + 1),
                                            "Rivels": rivals,
                                            "Title": f"{title} (S-{idx})",
                                            "Link": f"{m3u8}|referer={BASE_URL}"
                                        })
                                    seen_links.add(href)
                                    found_any = True
                            except: continue
                if found_any: break
        except: continue

    if found_any:
        final_package = OrderedDict([
            ("Owner", "Ivan-FluX"),
            ("Telegram", "https://t.me/iVan_flux"),
            ("App name", "fawna-auto-scrape-api"),
            ("Last update", get_ist_time()),
            ("Total_Matches", len(match_list)),
            ("Live_Data", match_list)
        ])
        
        try:
            with open(OUTPUT_FILE, "w") as f:
                json.dump(final_package, f, indent=4)
            print(f"[+] {OUTPUT_FILE} আপডেট হয়েছে।")
            push_to_github()
        except Exception as e:
            print(f"[ERROR] ফাইল সেভ ফেইল: {e}")
    else:
        print("[!] কোনো ডাটা পাওয়া যায়নি।")

if __name__ == "__main__":
    try:
        print(f"\n[!] Fawna স্ক্র্যাপ শুরু: {get_ist_time()}")
        run_automation()
        print("[-] কাজ শেষ।")
    except Exception as e:
        print(f"Error: {e}")
