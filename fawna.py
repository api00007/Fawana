import requests
import re
import json
import random
import time
import os
import shutil
from datetime import datetime
import pytz
from collections import OrderedDict

# --- সেটিংস ---
# কোনো হার্ডকোডেড ইউআরএল রাখা হয়নি, সরাসরি গিটহাব সিক্রেট থেকে আসবে
BASE_URL = os.getenv("BASE_URL")
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
    print(f"[-] অন্য GitHub রিপোজিটরিতে {OUTPUT_FILE} আপডেট করা হচ্ছে...")
    GITHUB_TOKEN = os.getenv("GH_TOKEN")
    GITHUB_USER = os.getenv("TGITHUB_USER")
    GITHUB_REPO = os.getenv("TGITHUB_REPO")
    GITHUB_EMAIL = os.getenv("TGITHUB_EMAIL")
    
    # একটি আলাদা অস্থায়ী ডিরেক্টরি নাম
    temp_dir = "temp_external_repo"
    remote_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_USER}/{GITHUB_REPO}.git"

    try:
        # ১. আগের কোনো টেম্পোরারি ফোল্ডার থাকলে তা মুছে ফেলা
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            
        # ২. অন্য রিপোজিটরিটি একদম নতুনভাবে ক্লোন করা
        clone_status = os.system(f"git clone {remote_url} {temp_dir}")
        if clone_status != 0:
            raise Exception("Git Clone ব্যর্থ হয়েছে। দয়া করে টোকেন ও রিপোজিটরি নাম চেক করুন।")
        
        # ৩. সদ্য স্ক্র্যাপ করা fawna.json ফাইলটি ক্লোন করা ফোল্ডারে কপি করা
        shutil.copy(OUTPUT_FILE, os.path.join(temp_dir, OUTPUT_FILE))
        
        # ৪. ক্লোন ফোল্ডারের ভেতর প্রবেশ করে কনফিগার, কমিট ও পুশ করা
        current_dir = os.getcwd()
        os.chdir(temp_dir)
        
        os.system(f'git config user.email "{GITHUB_EMAIL}"')
        os.system(f'git config user.name "{GITHUB_USER}"')
        os.system(f"git add {OUTPUT_FILE}")
        os.system(f'git commit -m "Auto Update: {get_ist_time()}" || echo "No changes"')
        push_status = os.system("git push origin main")
        
        # ৫. কাজ শেষে আবার আগের প্রধান ডিরেক্টরিতে ফিরে আসা
        os.chdir(current_dir)
        
        # অস্থায়ী ফোল্ডারটি মুছে ফেলা
        shutil.rmtree(temp_dir)
        
        if push_status == 0:
            print(f"[SUCCESS] অন্য রিপোজিটরিতে {OUTPUT_FILE} সফলভাবে আপডেট সম্পন্ন।")
        else:
            print("[ERROR] পুশ কমান্ড সফল হয়নি।")
            
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
                                m3u8_links = list(dict.fromkeys(re.findall(r'["\']([^"\']+\.m3u8[^"\']*)["\']', m_res.text)))
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
                                time.sleep(random.uniform(0.1, 0.5))
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
    if not BASE_URL:
        print("[ERROR] BASE_URL পাওয়া যায়নি! দয়া করে গিটহাব সিক্রেট চেক করুন।")
    else:
        try:
            print(f"\n[!] Fawna স্ক্র্যাপ শুরু: {get_ist_time()}")
            run_automation()
            print("[-] কাজ শেষ।")
        except Exception as e:
            print(f"Error: {e}")
