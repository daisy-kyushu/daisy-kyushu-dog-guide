#!/usr/bin/env python3
"""
spots.jsonのtype表記統一 + Nominatim Geocodingで座標補完
"""
import json, os, time, re
import urllib.request
import urllib.parse

# ---- spots.jsonのパスを探す ----
spots_path = None
for root, dirs, files in os.walk('/home/ubuntu/daisy-kyushu-dog-guide'):
    for f in files:
        if f == 'spots.json':
            spots_path = os.path.join(root, f)
            break

print(f"spots.json: {spots_path}")

with open(spots_path, encoding='utf-8') as f:
    spots = json.load(f)

# ---- type統一マッピング ----
TYPE_MAP = {
    # 英語→日本語
    'dogrun':       'ドッグラン',
    'walk':         '散策・公園',
    'cafe':         'カフェ',
    # 複合表記の統一
    'ドッグラン/カフェ':              'ドッグラン・カフェ',
    'ドッグラン / カフェ':            'ドッグラン・カフェ',
    'カフェ / ドッグラン':            'ドッグラン・カフェ',
    'カフェ/ドッグラン':              'ドッグラン・カフェ',
    'ドッグカフェ / 犬同伴OK飲食店':  'ドッグラン・カフェ',
    'ドッグカフェ / 犬同伴OK飲食店 / ドッグラン': 'ドッグラン・カフェ',
    'ドッグカフェ':                   'ドッグラン・カフェ',
    '犬同伴OK飲食店 / ドッグラン':    'ドッグラン・カフェ',
    'サービスエリア / ドッグラン':    'ドッグラン',
    'ドッグラン / 公園':              'ドッグラン',
    'ドッグラン / 犬と遊びに行ける場所': 'ドッグラン',
    'ドッグラン / ショッピング':      'ドッグラン',
    'ドッグラン / 宿泊':              'ドッグラン',
    'ドッグラン / 観光':              'ドッグラン',
    'ドッグラン/観光/カフェ':         'ドッグラン・カフェ',
    'テーマパーク / ドッグラン':      'ドッグラン',
    '公園 / ドッグラン':              'ドッグラン',
    # 観光系
    '観光 / 散策':   '観光・散策',
    '観光 / 温泉':   '観光・温泉',
    '観光 / 自然':   '観光・自然',
    '観光 / 庭園':   '観光・自然',
    '観光 / ショッピング': '観光・ショッピング',
    '公園 / 観光':   '観光・散策',
    # 自然系
    '自然 / 海浜':   '自然・海浜',
    '自然 / 散策':   '自然・散策',
    '自然 / 観光':   '観光・自然',
    '自然 / 温泉':   '自然・温泉',
    '自然 / 世界遺産': '観光・自然',
    '公園 / 自然':   '自然・散策',
    '公園 / 海浜':   '自然・海浜',
    '公園 / 散策':   '散策・公園',
    # 公園系
    '公園':          '散策・公園',
    '散策':          '散策・公園',
    # カフェ系
    'カフェ / 海浜': 'カフェ',
    'レストラン':    'カフェ',
    # その他
    'ビーチ':        '自然・海浜',
    'アウトドア':    '自然・散策',
    '公式まとめ / 情報源': '観光・散策',
}

# type統一を適用
type_fixed = 0
for s in spots:
    old = s.get('type', '')
    if old in TYPE_MAP:
        s['type'] = TYPE_MAP[old]
        type_fixed += 1
    elif not old or old == '(なし)':
        s['type'] = '観光・散策'  # デフォルト
        type_fixed += 1

print(f"type統一: {type_fixed}件修正")

# ---- Nominatim Geocodingで座標補完 ----
def geocode(name, address, prefecture):
    """住所からNominatimで緯度経度を取得"""
    queries = []
    if address and address.strip():
        queries.append(address)
    if name:
        queries.append(f"{name} {prefecture}")
    
    for q in queries:
        try:
            params = urllib.parse.urlencode({
                'q': q,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'jp',
                'accept-language': 'ja'
            })
            url = f"https://nominatim.openstreetmap.org/search?{params}"
            req = urllib.request.Request(url, headers={
                'User-Agent': 'DaisyKyushuDogGuide/1.0 (daisy-kyushu.github.io)'
            })
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                if data:
                    lat = float(data[0]['lat'])
                    lng = float(data[0]['lon'])
                    # 九州の範囲チェック（緯度30〜34、経度129〜132）
                    if 29.0 <= lat <= 34.5 and 128.0 <= lng <= 132.5:
                        return lat, lng
        except Exception as e:
            pass
        time.sleep(1.1)  # Nominatimのレート制限（1req/sec）
    return None, None

# 座標なしのスポットを抽出
no_coord = [s for s in spots if not s.get('lat') or not s.get('lng')]
print(f"座標補完対象: {len(no_coord)}件")

geocoded = 0
failed = 0
for i, s in enumerate(no_coord):
    name = s.get('name', '')
    address = s.get('address', '')
    pref = s.get('prefecture', s.get('area', '九州'))
    
    lat, lng = geocode(name, address, pref)
    if lat and lng:
        s['lat'] = lat
        s['lng'] = lng
        geocoded += 1
        print(f"[{i+1}/{len(no_coord)}] ✅ {name[:20]} → ({lat:.4f}, {lng:.4f})")
    else:
        failed += 1
        if (i+1) % 20 == 0:
            print(f"[{i+1}/{len(no_coord)}] ❌ {name[:20]} → 取得失敗")
    
    # 進捗保存（50件ごと）
    if (i+1) % 50 == 0:
        with open(spots_path, 'w', encoding='utf-8') as f:
            json.dump(spots, f, ensure_ascii=False, indent=2)
        print(f"  → 中間保存完了（{i+1}件処理済み）")

# 最終保存
with open(spots_path, 'w', encoding='utf-8') as f:
    json.dump(spots, f, ensure_ascii=False, indent=2)

print(f"\n=== 完了 ===")
print(f"座標取得成功: {geocoded}件")
print(f"座標取得失敗: {failed}件")
print(f"type統一: {type_fixed}件")

# 最終統計
with_coord = sum(1 for s in spots if s.get('lat') and s.get('lng'))
print(f"座標あり合計: {with_coord}/{len(spots)}件")
