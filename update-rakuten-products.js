const fs = require("fs/promises");
const path = require("path");

const AFF_ID = process.env.RAKUTEN_AFFILIATE_ID;
const DATA_PATH = path.join(__dirname, "products.json");

function encodeUrl(value) {
  return encodeURIComponent(String(value || ""));
}

function buildRakutenSearchUrl(product) {
  const keyword = product.searchKeyword || product.productName || "犬 おでかけ 用品";
  return `https://search.rakuten.co.jp/search/mall/${encodeUrl(keyword)}/`;
}

function buildAffiliateUrl(destinationUrl) {
  if (!AFF_ID) return "";
  if (!destinationUrl || !/^https:\/\/[^\s]+/.test(destinationUrl)) return "";

  // 楽天APIが不安定な場合でも、楽天アフィリエイトIDだけで楽天遷移リンクを生成する。
  // pc と m の両方に遷移先URLを入れて、PC/モバイルどちらでも楽天側へ送る。
  const encodedDestination = encodeUrl(destinationUrl);
  return `https://hb.afl.rakuten.co.jp/hgc/${AFF_ID}/?pc=${encodedDestination}&m=${encodedDestination}`;
}

async function main() {
  const raw = await fs.readFile(DATA_PATH, "utf8");
  const products = JSON.parse(raw);

  if (!Array.isArray(products)) {
    throw new Error("products.json must be an array");
  }

  const today = new Date().toISOString().slice(0, 10);
  let updatedCount = 0;

  const updatedProducts = products.map((product) => {
    const normalUrl = product.normalUrl || buildRakutenSearchUrl(product);
    const rakutenAffiliateUrl = product.rakutenAffiliateUrl || buildAffiliateUrl(normalUrl);
    const affiliateStatus = rakutenAffiliateUrl
      ? "affiliate-active"
      : normalUrl
        ? "search-only"
        : "link-missing";

    if (rakutenAffiliateUrl && rakutenAffiliateUrl !== product.rakutenAffiliateUrl) {
      updatedCount += 1;
    }

    return {
      ...product,
      normalUrl,
      rakutenAffiliateUrl,
      affiliateStatus,
      lastChecked: today,
      status: rakutenAffiliateUrl
        ? "楽天アフィリエイトリンク設定済み"
        : "楽天検索リンクあり / アフィリエイトリンク未設定",
      memo: rakutenAffiliateUrl
        ? "楽天アフィリエイトIDを使ったリンクです。価格・在庫・評価は変動するため、購入前に楽天側で確認してください。"
        : "楽天検索リンクのみ。RAKUTEN_AFFILIATE_ID を設定すると自動でアフィリエイトリンク化します。"
    };
  });

  await fs.writeFile(DATA_PATH, JSON.stringify(updatedProducts, null, 2) + "\n", "utf8");

  if (!AFF_ID) {
    console.log("RAKUTEN_AFFILIATE_ID が未設定です。products.json は検索リンクのみ整備しました。");
    return;
  }

  console.log(`products.json の楽天アフィリエイトリンクを ${updatedCount} 件生成しました。`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
