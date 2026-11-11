from flask import Flask, redirect, abort
import requests
import re
import time
from functools import wraps
import urllib3

# SSL uyarılarını gizle (verify=False için)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# 1 saatlik (3600 saniye) TTL cache decorator'ü
def ttl_cache(seconds=3600):
    def decorator(func):
        cache = {'result': None, 'time': 0}
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            if cache['result'] is not None and (now - cache['time'] < seconds):
                return cache['result']
            
            result = func(*args, **kwargs)
            if result[0] is not None: # Sadece başarılı sonuçları cache'le
                cache['result'] = result
                cache['time'] = now
            return result
        return wrapper
    return decorator

@ttl_cache(3600)
def get_stream_links():
    url = 'https://www.nowtv.com.tr/canli-yayin'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        if response.status_code == 200:
            html = response.text
            
            # 1. Önce nowtv-live-ad.ercdn.net ile başlayanı ara
            match = re.search(r'(https?://nowtv-live-ad\.ercdn\.net/nowtv/playlist\.m3u8[^\s\'"]*)', html)
            
            # 2. Bulunamazsa nowtv-ad-live.ercdn.net ile başlayanı ara
            if not match:
                match = re.search(r'(https?://nowtv-ad-live\.ercdn\.net/nowtv/playlist\.m3u8[^\s\'"]*)', html)
            
            if match:
                ercdn_url = match.group(1)
                
                # Tokenler bozulmadan re.sub ile daioncdn formatına çevir
                daion_url = re.sub(
                    r'https?://(?:nowtv-live-ad|nowtv-ad-live)\.ercdn\.net/nowtv/playlist\.m3u8',
                    'https://nowtv.daioncdn.net/nowtv/nowtv.m3u8',
                    ercdn_url
                )
                return ercdn_url, daion_url
                
    except Exception as e:
        print(f"Hata oluştu: {e}")
        
    return None, None

@app.route('/nowtv')
def redirect_ercdn():
    ercdn_url, _ = get_stream_links()
    if ercdn_url:
        return redirect(ercdn_url)
    return abort(404, description="Ercdn yayın linki bulunamadı.")

@app.route('/nowtvdai')
def redirect_daion():
    _, daion_url = get_stream_links()
    if daion_url:
        return redirect(daion_url)
    return abort(404, description="Daion yayın linki bulunamadı.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
