#!/usr/bin/env python3
"""
サイト品質向上スクリプト
1. 座標なし181件をmapQueryフィールドで再Geocoding
2. hoursテキストからopenTime/closeTimeを自動解析
3. spots.jsonを更新保存
"""
import json, re, time, os, urllib.parse, urllib.request

# spots.jsonのパスを探す
spots_path = None
for root, dirs, files in os.walk('/home/ubuntu/daisy-kyushu-dog-guide'):
    for f in files:
        if f == 'spots.json':
            spots_path = os.path.join(root, f)
            break

print(f"spots.json: {spots_path}")
with open(spots_path, encoding='utf-8') as f:
    spots = json.load(f)

# ============================================================
# 1. 座標補完（mapQuery / access フィールドを使って再試行）
# ============================================================
def geocode_nominatim(query):
    """Nominatim APIで座標を取得"""
    try:
        q = urllib.parse.quote(query)
        url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1&countrycodes=jp"
        req = urllib.request.Request(url, headers={'User-Agent': 'DaisyKyushuDogGuide/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data:
                return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        pass
    return None, None

no_coord = [s for s in spots if not s.get('lat') or not s.get('lng')]
print(f"\n=== 座標補完開始: {len(no_coord)}件 ===")

success = 0
fail = 0
for i, spot in enumerate(no_coord):
    # クエリ候補を優先順位で試す
    queries = []
    
    # 1. mapQueryフィールド（最も精度が高い）
    if spot.get('mapQuery'):
        queries.append(spot['mapQuery'])
    
    # 2. accessフィールドから住所部分を抽出
    if spot.get('access'):
        access = spot['access']
        # 「/」や「・」で分割して最初の部分（住所）を使う
        addr_part = re.split(r'[/／・]', access)[0].strip()
        if len(addr_part) > 5:
            queries.append(addr_part)
    
    # 3. name + area
    if spot.get('name') and spot.get('area'):
        queries.append(f"{spot['name']} {spot['area']}")
    
    # 4. name + prefecture
    if spot.get('name') and spot.get('prefecture'):
        queries.append(f"{spot['name']} {spot['prefecture']}")
    
    lat, lng = None, None
    used_query = None
    for q in queries:
        lat, lng = geocode_nominatim(q)
        if lat:
            used_query = q
            break
        time.sleep(1.1)
    
    if lat:
        spot['lat'] = round(lat, 6)
        spot['lng'] = round(lng, 6)
        success += 1
        print(f"[{i+1}/{len(no_coord)}] ✅ {spot['name']} → ({lat:.4f}, {lng:.4f})")
    else:
        fail += 1
        print(f"[{i+1}/{len(no_coord)}] ❌ {spot['name']} → 取得失敗")
    
    time.sleep(1.1)
    
    # 50件ごとに中間保存
    if (i + 1) % 50 == 0:
        with open(spots_path, 'w', encoding='utf-8') as f:
            json.dump(spots, f, ensure_ascii=False, indent=2)
        print(f"  → 中間保存完了（{i+1}件処理済み）")

print(f"\n座標補完: 成功{success}件 / 失敗{fail}件")

# ============================================================
# 2. 営業時間テキストからopenTime/closeTimeを自動解析
# ============================================================
print("\n=== 営業時間解析開始 ===")

# 時刻パターン（例: 9:00, 09:00, 9時, 17:30）
TIME_PATTERN = re.compile(r'(\d{1,2})[:\uff1a\u6642](\d{0,2})')

def parse_time(text):
    """時刻文字列をHH:MM形式に変換"""
    m = TIME_PATTERN.search(text)
    if m:
        h = int(m.group(1))
        mi = int(m.group(2)) if m.group(2) else 0
        if 0 <= h <= 23 and 0 <= mi <= 59:
            return f"{h:02d}:{mi:02d}"
    return None

# 区切り文字パターン
SEP = r'[～〜\-–—~\uff5e]'

def parse_hours(hours_text):
    """hoursテキストからopenTime/closeTimeを抽出"""
    if not hours_text or hours_text in ['要確認', '不明', '', '24時間']:
        return None, None
    
    # 「9:00〜18:00」「10:00-17:00」などのパターン
    pattern = re.compile(
        r'(\d{1,2}[:\uff1a\u6642]\d{0,2})' + SEP + r'(\d{1,2}[:\uff1a\u6642]\d{0,2})'
    )
    m = pattern.search(hours_text)
    if m:
        open_t = parse_time(m.group(1))
        close_t = parse_time(m.group(2))
        if open_t and close_t:
            return open_t, close_t
    
    # 「9時〜18時」パターン
    pattern2 = re.compile(r'(\d{1,2})\u6642' + SEP + r'(\d{1,2})\u6642')
    m2 = pattern2.search(hours_text)
    if m2:
        h1, h2 = int(m2.group(1)), int(m2.group(2))
        if 0 <= h1 <= 23 and 0 <= h2 <= 23:
            return f"{h1:02d}:00", f"{h2:02d}:00"
    
    return None, None

hours_set = 0
for spot in spots:
    # すでにopenTime/closeTimeが設定済みならスキップ
    if spot.get('openTime') and spot.get('closeTime'):
        continue
    
    hours = spot.get('hours', '')
    open_t, close_t = parse_hours(hours)
    
    if open_t and close_t:
        spot['openTime'] = open_t
        spot['closeTime'] = close_t
        hours_set += 1

print(f"営業時間解析: {hours_set}件に openTime/closeTime を設定")

# 設定後の統計
with_hours = sum(1 for s in spots if s.get('openTime') and s.get('closeTime'))
print(f"営業時間設定済み合計: {with_hours}/{len(spots)}件")

# ============================================================
# 3. 最終保存
# ============================================================
with open(spots_path, 'w', encoding='utf-8') as f:
    json.dump(spots, f, ensure_ascii=False, indent=2)

with_coord = sum(1 for s in spots if s.get('lat') and s.get('lng'))
print(f"\n=== 完了 ===")
print(f"座標あり合計: {with_coord}/{len(spots)}件")
print(f"営業時間設定済み: {with_hours}/{len(spots)}件")
print(f"spots.json保存完了: {spots_path}")
