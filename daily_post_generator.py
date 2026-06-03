#!/usr/bin/env python3
"""
Daisy九州犬連れガイド - 毎日Instagram自動投稿スクリプト
毎朝8時に実行し、投稿案を生成してユーザーに確認を求める
"""

import json
import os
import sys
import datetime
import hashlib
import random
from pathlib import Path
from openai import OpenAI

# ===== 設定 =====
SITE_URL = "https://daisy-kyushu-dog-guide.pages.dev"
DATA_DIR = Path(__file__).parent
OUTPUT_DIR = Path("/home/ubuntu/daily_post_output")
OUTPUT_DIR.mkdir(exist_ok=True)

# 曜日別テーマ (0=月, 1=火, 2=水, 3=木, 4=金, 5=土, 6=日)
THEME_BY_WEEKDAY = {
    0: "spot",      # 月: スポット紹介
    1: "product",   # 火: おすすめグッズ
    2: "spot",      # 水: スポット紹介
    3: "event",     # 木: イベント告知
    4: "spot",      # 金: 週末スポット
    5: "product",   # 土: 週末グッズ
    6: "summary",   # 日: サイト紹介・まとめ
}

THEME_LABELS = {
    "spot": "犬連れスポット紹介",
    "product": "おすすめ犬グッズ",
    "event": "イベント告知",
    "summary": "サイト紹介",
}

HASHTAGS = {
    "spot": "#犬連れ旅行 #九州犬連れ #犬とお出かけ #サモエド #大型犬 #ドッグフレンドリー #北九州 #福岡犬連れ #犬旅",
    "product": "#犬グッズ #大型犬グッズ #サモエド #犬のいる生活 #楽天 #犬用品 #愛犬グッズ #ペットグッズ #犬連れ旅行",
    "event": "#犬イベント #九州犬イベント #ドッグイベント #犬連れ #サモエド #大型犬 #北九州 #福岡 #犬とお出かけ",
    "summary": "#犬連れ旅行 #九州犬連れ #サモエド #大型犬 #ドッグフレンドリー #犬旅 #犬のいる生活 #九州旅行 #犬とお出かけ",
}


def load_data():
    """サイトデータを読み込む"""
    with open(DATA_DIR / "spots.json") as f:
        spots = json.load(f)
    with open(DATA_DIR / "products.json") as f:
        products = json.load(f)
    with open(DATA_DIR / "events.json") as f:
        events = json.load(f)
    return spots, products, events


def get_today_seed():
    """今日の日付からシードを生成（同じ日は同じネタを選ぶ）"""
    today = datetime.date.today().isoformat()
    return int(hashlib.md5(today.encode()).hexdigest(), 16) % (2**31)


def pick_spot(spots):
    """今日のスポットを選択（weekendRecommended優先、大型犬OK優先）"""
    seed = get_today_seed()
    rng = random.Random(seed)
    
    # 大型犬OKのスポットを優先
    good_spots = [s for s in spots if s.get("largeDog") in ["可", "OK", "○", "大型犬可"] 
                  and s.get("status") not in ["閉業", "要確認のみ"]]
    if not good_spots:
        good_spots = [s for s in spots if s.get("status") not in ["閉業"]]
    
    return rng.choice(good_spots)


def pick_product(products):
    """今日の商品を選択"""
    seed = get_today_seed() + 1
    rng = random.Random(seed)
    
    # 評価が高い商品を優先
    good_products = [p for p in products if p.get("rating", 0) >= 4.0 
                     and p.get("affiliateStatus") != "inactive"]
    if not good_products:
        good_products = products
    
    return rng.choice(good_products)


def pick_event(events):
    """近日開催のイベントを選択"""
    today = datetime.date.today()
    upcoming = []
    
    for e in events:
        # eventDateまたはdateから開催日を取得
        date_str = e.get("eventDate") or e.get("date", "")
        try:
            if "〜" in date_str:
                date_str = date_str.split("〜")[0]
            event_date = datetime.date.fromisoformat(date_str[:10])
            # 今日から60日以内のイベント
            if today <= event_date <= today + datetime.timedelta(days=60):
                upcoming.append((event_date, e))
        except:
            pass
    
    if not upcoming:
        # 期限切れでも直近のものを返す
        return events[0] if events else None
    
    # 最も近いイベントを返す
    upcoming.sort(key=lambda x: x[0])
    return upcoming[0][1]


def generate_post_content(theme, item, client):
    """AIで投稿文を生成"""
    
    if theme == "spot":
        prompt = f"""
あなたは九州の犬連れ旅行サイト「Daisy九州犬連れガイド」のInstagram担当です。
サモエドのDaisyと一緒に九州を旅するコンセプトのアカウントです。

以下のスポット情報を元に、Instagramの投稿キャプションを作成してください。

スポット名: {item.get('name')}
エリア: {item.get('area')}
種別: {item.get('type')}
大型犬: {item.get('largeDog', '要確認')}
メモ: {item.get('memo', '')}
営業時間: {item.get('hours', '要確認')}
料金: {item.get('fee', '要確認')}

【ルール】
- 300文字以内（ハッシュタグ除く）
- 最初の1行は絵文字なしの短いキャッチコピー（20文字以内）
- Daisyが実際に訪れた感想風に書く（一人称: Daisyが〜）
- 曖昧・不確かな情報は書かない（「要確認」の情報は省く）
- サイトへの誘導文を最後に入れる（「詳しくはプロフのリンクから」）
- ハッシュタグは含めない（別途追加）
- 改行を適切に使う

キャプションのみ出力してください。
"""
    elif theme == "product":
        prompt = f"""
あなたは九州の犬連れ旅行サイト「Daisy九州犬連れガイド」のInstagram担当です。
サモエドのDaisyと一緒に九州を旅するコンセプトのアカウントです。

以下の商品情報を元に、Instagramの投稿キャプションを作成してください。

商品名: {item.get('productName')}
カテゴリ: {item.get('category')}
対象: {item.get('target')}
メモ: {item.get('memo', '')}
評価: {item.get('rating', '')}点（{item.get('reviewCount', '')}件）
価格: {item.get('itemPrice', '')}円

【ルール】
- 300文字以内（ハッシュタグ除く）
- 最初の1行は絵文字なしの短いキャッチコピー（20文字以内）
- 大型犬・サモエドとの旅行に役立つ観点で紹介
- 具体的なメリットを1〜2つ書く
- 曖昧・不確かな情報は書かない
- 「楽天で購入できます」「詳しくはプロフのリンクから」を最後に入れる
- ハッシュタグは含めない（別途追加）
- 改行を適切に使う

キャプションのみ出力してください。
"""
    elif theme == "event":
        prompt = f"""
あなたは九州の犬連れ旅行サイト「Daisy九州犬連れガイド」のInstagram担当です。
サモエドのDaisyと一緒に九州を旅するコンセプトのアカウントです。

以下のイベント情報を元に、Instagramの投稿キャプションを作成してください。

イベント名: {item.get('title') or item.get('name')}
エリア: {item.get('area')}
会場: {item.get('venue', '')}
開催日: {item.get('date') or item.get('eventDate')}
入場料: {item.get('fee', '要確認')}
概要: {item.get('description', '')}

【ルール】
- 300文字以内（ハッシュタグ除く）
- 最初の1行は絵文字なしの短いキャッチコピー（20文字以内）
- 開催日・場所は必ず明記する
- 曖昧・不確かな情報（「要確認」の情報）は省く
- 「詳しくはプロフのリンクから」を最後に入れる
- ハッシュタグは含めない（別途追加）
- 改行を適切に使う

キャプションのみ出力してください。
"""
    else:  # summary
        prompt = f"""
あなたは九州の犬連れ旅行サイト「Daisy九州犬連れガイド」のInstagram担当です。
サモエドのDaisyと一緒に九州を旅するコンセプトのアカウントです。

今週の投稿まとめ・サイト紹介のInstagramキャプションを作成してください。

サイト概要:
- 九州の犬連れスポット300件以上掲載
- 大型犬・サモエド向け情報に特化
- イベント情報・おすすめグッズも掲載
- サイトURL: {SITE_URL}

【ルール】
- 300文字以内（ハッシュタグ除く）
- 最初の1行は絵文字なしの短いキャッチコピー（20文字以内）
- 週末のお出かけを促す内容
- 「詳しくはプロフのリンクから」を最後に入れる
- ハッシュタグは含めない（別途追加）
- 改行を適切に使う

キャプションのみ出力してください。
"""
    
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def generate_image_prompt(theme, item, caption):
    """画像生成用プロンプトを作成"""
    today = datetime.date.today()
    season = "夏" if today.month in [6, 7, 8] else "秋" if today.month in [9, 10, 11] else "冬" if today.month in [12, 1, 2] else "春"
    
    if theme == "spot":
        name = item.get('name', '')
        area = item.get('area', '')
        spot_type = item.get('type', '')
        return f"""広告風チラシ画像。九州の犬連れスポット「{name}」の紹介。
エリア: {area}、種別: {spot_type}。
白い大型犬（サモエド）が楽しそうにしている{season}の屋外シーン。
明るく爽やかな色調。日本語テキストを含む広告デザイン。
上部に大きく「{name}」、下部に「大型犬OK」「犬連れOK」のバッジ。
プロフェッショナルな広告チラシスタイル、縦長1:1比率。"""
    
    elif theme == "product":
        product_name = item.get('productName', '')
        category = item.get('category', '')
        return f"""広告風チラシ画像。犬用グッズ「{product_name}」の紹介。
カテゴリ: {category}。
白い大型犬（サモエド）が商品を使っているシーン、または商品の魅力的な展示。
明るく清潔感のある色調。日本語テキストを含む広告デザイン。
上部に「{product_name}」、楽天での購入を促すデザイン要素。
プロフェッショナルな広告チラシスタイル、縦長1:1比率。"""
    
    elif theme == "event":
        event_name = item.get('title') or item.get('name', '')
        area = item.get('area', '')
        date = item.get('date') or item.get('eventDate', '')
        return f"""広告風イベント告知チラシ。「{event_name}」の告知。
開催地: {area}、開催日: {date}。
白い大型犬（サモエド）を含む賑やかなイベントシーン。
明るく楽しい雰囲気の色調。日本語テキストを含む広告デザイン。
大きく「{event_name}」、開催日と場所を目立つように配置。
プロフェッショナルなイベントポスタースタイル、縦長1:1比率。"""
    
    else:  # summary
        return f"""広告風チラシ画像。九州犬連れ旅行ガイドサイトの紹介。
白い大型犬（サモエド）が九州の美しい景色の前でポーズ。
明るく爽やかな{season}の色調。日本語テキストを含む広告デザイン。
「九州犬連れガイド」「300スポット掲載」「大型犬OK情報満載」のテキスト。
プロフェッショナルな広告チラシスタイル、縦長1:1比率。"""


def get_item_link(theme, item):
    """投稿に含めるリンクを取得"""
    if theme == "spot":
        spot_id = item.get('id', '')
        return f"{SITE_URL}/spots.html#{spot_id}" if spot_id else SITE_URL
    elif theme == "product":
        return item.get('rakutenAffiliateUrl') or item.get('normalUrl') or SITE_URL
    elif theme == "event":
        return item.get('officialUrl') or SITE_URL
    else:
        return SITE_URL


def main():
    """メイン処理"""
    print("=" * 60)
    print("Daisy九州犬連れガイド - 本日の投稿案を生成中...")
    print("=" * 60)
    
    today = datetime.date.today()
    weekday = today.weekday()
    theme = THEME_BY_WEEKDAY[weekday]
    theme_label = THEME_LABELS[theme]
    
    print(f"\n📅 日付: {today.strftime('%Y年%m月%d日')} ({['月','火','水','木','金','土','日'][weekday]}曜日)")
    print(f"📌 テーマ: {theme_label}")
    
    # データ読み込み
    spots, products, events = load_data()
    
    # 今日のアイテムを選択
    if theme == "spot":
        item = pick_spot(spots)
        print(f"\n✅ 選択スポット: {item.get('name')} ({item.get('area')})")
    elif theme == "product":
        item = pick_product(products)
        print(f"\n✅ 選択商品: {item.get('productName')} ({item.get('category')})")
    elif theme == "event":
        item = pick_event(events)
        if item:
            print(f"\n✅ 選択イベント: {item.get('title') or item.get('name')} ({item.get('date') or item.get('eventDate')})")
        else:
            print("\n⚠️ 近日開催のイベントがありません。スポット投稿に切り替えます。")
            theme = "spot"
            item = pick_spot(spots)
    else:
        item = None
        print(f"\n✅ テーマ: サイト紹介・まとめ")
    
    # OpenAI クライアント初期化
    client = OpenAI()
    
    # 投稿文生成
    print("\n📝 投稿文を生成中...")
    caption = generate_post_content(theme, item or {}, client)
    hashtags = HASHTAGS[theme]
    full_caption = f"{caption}\n\n{hashtags}"
    
    # リンク取得
    link = get_item_link(theme, item or {})
    
    # 画像プロンプト生成
    image_prompt = generate_image_prompt(theme, item or {}, caption)
    
    # 結果を保存
    output = {
        "date": today.isoformat(),
        "weekday": ['月','火','水','木','金','土','日'][weekday],
        "theme": theme,
        "theme_label": theme_label,
        "item_name": item.get('name') or item.get('title') or item.get('productName', '') if item else "サイト紹介",
        "caption": caption,
        "hashtags": hashtags,
        "full_caption": full_caption,
        "link": link,
        "image_prompt": image_prompt,
    }
    
    output_file = OUTPUT_DIR / f"post_{today.isoformat()}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    # 結果を表示
    print("\n" + "=" * 60)
    print("📱 本日の投稿案")
    print("=" * 60)
    print(f"\n【テーマ】{theme_label}")
    if item:
        print(f"【ネタ】{item.get('name') or item.get('title') or item.get('productName', '')}")
    print(f"\n【キャプション】\n{full_caption}")
    print(f"\n【リンク】{link}")
    print(f"\n【画像生成プロンプト】\n{image_prompt}")
    print(f"\n💾 保存先: {output_file}")
    
    return output


if __name__ == "__main__":
    result = main()
    print("\n✨ 投稿案の生成が完了しました。")
    print("次のステップ: 画像を生成してInstagramに投稿します。")
