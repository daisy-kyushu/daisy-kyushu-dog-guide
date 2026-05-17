# DATA_RULES (Daisy Kyushu Dog Guide)

## 1. 公式情報の定義
公式情報として扱ってよいもの：
- 店舗公式Webサイト
- 施設公式Webサイト
- 店舗公式Instagram
- 施設公式Instagram
- 主催者公式Instagram
- 運営会社公式Instagram
- 自治体・観光協会ページ

公式扱いしないもの：
- 個人投稿
- 口コミ投稿
- まとめアカウント投稿
- ハッシュタグ投稿
- 開けないInstagram URL
- 店名が似ているだけで本人運営と確認できないアカウント

## 2. Instagramを公式情報として使う条件
- 店舗名・施設名・主催者名と一致する
- プロフィールや投稿内容から公式アカウントと判断できる
- URLが実際に開ける
- 最新情報確認先として使える

## 3. 登録ルール
- 公式Webサイトがある場合は `officialUrl` に入れる
- 公式Instagramしかない場合は `instagramUrl` に入れる
- 公式Instagramを確認できた場合、`status` は「公式Instagram確認」にする
- URLが開けないInstagramは登録しない
- 開けないURLは `officialUrl` / `instagramUrl` から外す
- 不明な場合は `status` を「要確認」にする

## 4. 表示ルール
- `officialUrl` がある場合は「公式情報」ボタンを表示
- `instagramUrl` がある場合は「公式Instagramを見る」ボタンを表示
- 開けないInstagramリンクは表示しない

## 5. 既存JSONキーとの対応
このリポジトリには `officialUrl` / `instagramUrl` が未統一のファイルもあるため、当面は以下対応で扱う：
- `officialUrl` 相当：`officialUrl` または `url`
- `instagramUrl` 相当：`instagramUrl` または `snsUrl`（Instagram URLのみ）
- `status` は既存の `status` キーを利用

新規追加・更新時は、可能な限り `officialUrl` / `instagramUrl` / `status` の意味を崩さないこと。
