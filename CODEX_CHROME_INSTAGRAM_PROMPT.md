# Codex Chromeプラグイン用：Instagram優先の情報収集・掲載プロンプト

目的：
Daisy Kyushu Dog Guide に掲載するため、Instagramを中心に犬イベントを探し、犬と泊まれるホテル、犬と遊びに行ける場所、くじゅう花公園のようなアウトドア候補も整理して、サイト掲載まで行う。

重要：
Instagramの無断大量スクレイピングはしない。
Chromeで公開されている公式アカウント・主催者アカウント・公式サイトを確認し、必要な情報だけを手動確認に近い形で抽出する。
個人アカウントや口コミだけで掲載しない。

優先順位：
1. Instagramから今後開催予定の犬イベントを探す
2. ホテルは「犬と泊まれる」で探す
3. 犬と遊びに行ける場所を探す
4. くじゅう花公園のようなアウトドア候補を追加する

Instagram検索：
- #大分犬イベント
- #九州犬イベント
- #犬イベント九州
- #ドッグイベント大分
- #犬連れイベント
- #犬マルシェ
- #わんこイベント
- #大分ドッグイベント

検索キーワード：
- 大分 犬イベント
- 大分 ドッグイベント
- 九州 犬イベント
- 犬 マルシェ 大分
- 犬 フェス 大分
- ペットイベント 大分

掲載条件：
- 開催日がある
- 今後開催予定である
- 公式URLまたは公式SNSがある
- 会場が確認できる、または公式で後日発表と分かる
- 犬同伴ルールが不明な場合は「公式サイト・公式SNSで要確認」とする

content-sources.json に追加する形式：

```json
{
  "id": "英数字のID",
  "enabled": true,
  "publish": true,
  "type": "event",
  "sourcePlatform": "instagram",
  "name": "イベント名",
  "area": "大分県○○市",
  "category": "犬イベント",
  "url": "公式サイトURL",
  "snsUrl": "Instagram公式投稿または公式アカウントURL",
  "eventDate": "YYYY-MM-DD〜YYYY-MM-DD",
  "venue": "会場名",
  "trustRank": "B",
  "memo": "開催日・会場・犬同伴ルールは公式サイト・公式SNSで要確認。"
}
```

ホテル候補の形式：

```json
{
  "id": "rakuten-oita-dog-hotel-search",
  "enabled": true,
  "publish": true,
  "type": "hotel",
  "sourcePlatform": "rakuten-travel",
  "name": "楽天トラベルで大分県の犬と泊まれる宿を探す",
  "area": "大分県",
  "category": "犬と泊まれる宿",
  "url": "https://travel.rakuten.co.jp/",
  "searchKeyword": "大分 犬と泊まれる",
  "trustRank": "A",
  "memo": "予約前に犬同伴条件、サイズ制限、頭数制限、ワクチン証明の有無を必ず確認。"
}
```

犬と遊びに行ける場所・アウトドア候補の形式：

```json
{
  "id": "kuju-flower-park-candidate",
  "enabled": true,
  "publish": true,
  "type": "outdoor",
  "sourcePlatform": "official-site",
  "name": "くじゅう花公園",
  "area": "大分県竹田市久住町",
  "category": "花公園 / アウトドア / 散策",
  "url": "https://www.hana-kouen.com/",
  "trustRank": "C",
  "memo": "犬同伴条件・大型犬可否・リードルール・雨天時対応は公式情報で要確認。"
}
```

実行手順：
1. ChromeでInstagramと公式サイトを確認
2. 掲載できる候補だけ content-sources.json に追記
3. JSON構文エラーがないか確認
4. GitHub Actions → Instagram First Auto Publish → Run workflow
5. 公開サイトで確認
6. 確認URL： https://daisy-kyushu.github.io/daisy-kyushu-dog-guide/?v=instagram-first

禁止：
- 個人アカウントの情報だけで掲載
- 犬同伴条件の推測
- 過去イベントの掲載
- 非公開情報やログイン必須情報の転載
- 自動いいね・自動フォロー・DM送信
