# GitHub Pages公開手順

## 1. リポジトリ作成

Repository name:
`daisy-kyushu-dog-guide`

## 2. ファイルをアップロード

このZIPの中身をすべてリポジトリにアップロードします。

## 3. GitHub Pagesを有効化

Settings → Pages → Source: Deploy from a branch → Branch: main → Folder: /root → Save

公開URL:
`https://daisy-kyushu.github.io/daisy-kyushu-dog-guide/`

## 4. 楽天APIのSecretsを入れる

Settings → Secrets and variables → Actions → New repository secret

登録する名前:

- `RAKUTEN_APP_ID`
- `RAKUTEN_AFFILIATE_ID`

## 5. Actionsを実行

Actions → Update Rakuten Products → Run workflow

イベント更新:
Actions → Update Events → Run workflow
