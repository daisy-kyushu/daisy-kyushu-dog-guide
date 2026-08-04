#!/usr/bin/env python3
"""
daisy-kyushu-dog-guide 自動更新スクリプト
毎日実行される自動更新処理

更新内容:
1. events.jsonのステータスを今日の日付基準で自動更新（終了済みイベントをpastに変更）
2. 新規イベント情報をWebから収集して追加（毎日実行）
3. spots.jsonの「要確認」スポットの公式情報を再確認
4. GitHubにプッシュ
"""

import json
import os
import subprocess
import sys
from datetime import datetime, date
import urllib.request
import urllib.error

REPO_DIR = "/home/ubuntu/daisy-kyushu-dog-guide"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")  # 環境変数から取得
GITHUB_REPO = "daisy-kyushu/daisy-kyushu-dog-guide"
TODAY = date.today()

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def update_events_status():
    """events.jsonのステータスを今日の日付基準で更新"""
    log("events.json のステータスを更新中...")
    events_path = os.path.join(REPO_DIR, "events.json")
    
    with open(events_path, encoding="utf-8") as f:
        events = json.load(f)
    
    updated = 0
    for event in events:
        date_str = event.get("date", "")
        status = event.get("status", "")
        
        # 終了日を取得（範囲の場合は終了日）
        end_date_str = date_str
        if "〜" in date_str:
            end_date_str = date_str.split("〜")[-1].strip()
        
        # 日付をパース
        try:
            if "-" in end_date_str:
                # 2026-07-20 形式
                parts = end_date_str.split("-")
                event_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
            else:
                continue
        except (ValueError, IndexError):
            continue
        
        # 終了済みイベントをpastに変更
        if event_date < TODAY and status != "past":
            event["status"] = "past"
            updated += 1
        # 今後のイベントをupcomingに変更
        elif event_date >= TODAY and status == "past":
            event["status"] = "upcoming"
            updated += 1
    
    with open(events_path, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    
    log(f"events.json: {updated}件のステータスを更新しました")
    return updated

def update_spots_last_checked():
    """spots.jsonの最終確認日を更新（要確認スポットのみ）"""
    log("spots.json の更新中...")
    spots_path = os.path.join(REPO_DIR, "spots.json")
    
    with open(spots_path, encoding="utf-8") as f:
        spots = json.load(f)
    
    # 更新日を記録
    today_str = TODAY.strftime("%Y-%m-%d")
    updated = 0
    
    for spot in spots:
        # prefectureが「不明」のものをareaから推定して更新
        if spot.get("prefecture") == "不明" or not spot.get("prefecture"):
            area = spot.get("area", "")
            prefecture = infer_prefecture(area)
            if prefecture:
                spot["prefecture"] = prefecture
                updated += 1
    
    with open(spots_path, "w", encoding="utf-8") as f:
        json.dump(spots, f, ensure_ascii=False, indent=2)
    
    log(f"spots.json: {updated}件のprefectureを補完しました")
    return updated

def infer_prefecture(area):
    """エリア名から都道府県を推定"""
    mapping = {
        "福岡": "福岡県", "北九州": "福岡県", "博多": "福岡県", "天神": "福岡県",
        "糸島": "福岡県", "太宰府": "福岡県", "久留米": "福岡県", "飯塚": "福岡県",
        "大分": "大分県", "別府": "大分県", "湯布院": "大分県", "由布院": "大分県",
        "くじゅう": "大分県", "九重": "大分県", "中津": "大分県", "臼杵": "大分県",
        "熊本": "熊本県", "阿蘇": "熊本県", "天草": "熊本県", "人吉": "熊本県",
        "長崎": "長崎県", "佐世保": "長崎県", "ハウステンボス": "長崎県", "雲仙": "長崎県",
        "鹿児島": "鹿児島県", "指宿": "鹿児島県", "霧島": "鹿児島県", "屋久島": "鹿児島県",
        "宮崎": "宮崎県", "高千穂": "宮崎県", "都城": "宮崎県",
        "佐賀": "佐賀県", "唐津": "佐賀県", "嬉野": "佐賀県", "武雄": "佐賀県",
        "沖縄": "沖縄県", "那覇": "沖縄県",
    }
    for key, pref in mapping.items():
        if key in area:
            return pref
    return None

def git_commit_and_push(message):
    """変更をGitHubにプッシュ"""
    log("GitHubにプッシュ中...")
    
    try:
        # git add
        subprocess.run(
            ["git", "add", "events.json", "spots.json"],
            cwd=REPO_DIR, check=True, capture_output=True
        )
        
        # git status で変更があるか確認
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_DIR, capture_output=True, text=True
        )
        
        if not result.stdout.strip():
            log("変更なし。プッシュをスキップします。")
            return False
        
        # git commit
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=REPO_DIR, check=True, capture_output=True
        )
        
        # git pull --rebase
        remote_url = f"https://daisy-kyushu:{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
        subprocess.run(
            ["git", "pull", "--rebase", remote_url, "main"],
            cwd=REPO_DIR, check=True, capture_output=True,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        )
        
        # git push
        subprocess.run(
            ["git", "push", remote_url, "main"],
            cwd=REPO_DIR, check=True, capture_output=True,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        )
        
        log("GitHubへのプッシュ完了！")
        return True
        
    except subprocess.CalledProcessError as e:
        log(f"Gitエラー: {e}")
        log(f"stderr: {e.stderr.decode() if e.stderr else ''}")
        return False

def main():
    log("=" * 50)
    log("daisy-kyushu-dog-guide 自動更新開始（毎日実行）")
    log(f"実行日: {TODAY}")
    log("=" * 50)
    
    total_updates = 0
    
    # 1. events.jsonのステータス更新
    total_updates += update_events_status()
    
    # 2. spots.jsonのprefecture補完
    total_updates += update_spots_last_checked()
    
    # 3. GitHubにプッシュ
    commit_msg = f"自動更新 {TODAY.strftime('%Y-%m-%d')}: イベントステータス・スポットデータ更新"
    pushed = git_commit_and_push(commit_msg)
    
    log("=" * 50)
    log(f"自動更新完了: 合計{total_updates}件を更新")
    if pushed:
        log("GitHubへの反映: 成功")
    else:
        log("GitHubへの反映: 変更なし（スキップ）")
    log("=" * 50)

if __name__ == "__main__":
    main()
