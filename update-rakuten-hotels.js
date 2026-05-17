const fs = require("fs/promises");

const AFF_BASE = "https://hb.afl.rakuten.co.jp/hgc/";
const CAUTION = "料金・空室・犬同伴条件・頭数制限・サイズ制限・ワクチン証明の条件は変動するため、予約前に楽天トラベル側・宿公式側で必ず確認してください。";
const NOTE_ACTIVE = "楽天トラベルのアフィリエイト導線を設定済みです。";
const NOTE_SEARCH = "楽天トラベルの通常導線のみです。";

function sanitizeMemo(memo) {
  return String(memo || "")
    .replaceAll(NOTE_ACTIVE, "")
    .replaceAll(NOTE_SEARCH, "")
    .replaceAll(CAUTION, "")
    .replace(/\s+/g, " ")
    .trim();
}

function isSpecificHotelUrl(url) {
  const u = String(url || "").trim();
  if (!u) return false;
  return /travel\.rakuten\.co\.jp\/(HOTEL|hotel\.travel\.rakuten\.co\.jp\/hinfo|hotel\.travel\.rakuten\.co\.jp\/hotelinfo)/i.test(u)
    && !/^https?:\/\/travel\.rakuten\.co\.jp\/?$/i.test(u);
}

function buildDestination(hotel) {
  const base = hotel.rakutenTravelUrl || "https://travel.rakuten.co.jp/";
  if (isSpecificHotelUrl(base)) return base;
  const keyword = String(hotel.searchKeyword || "").trim();
  if (keyword) {
    return `https://travel.rakuten.co.jp/keyword/Search.do?f_teikei=&f_query=${encodeURIComponent(keyword)}`;
  }
  return base;
}

function buildAffiliateUrl(destination, affiliateId) {
  if (!affiliateId || !destination) return "";
  const encodedDest = encodeURIComponent(destination);
  return `${AFF_BASE}${affiliateId}/?pc=${encodedDest}&m=${encodedDest}`;
}

function buildMemo(currentMemo, affiliateActive) {
  const clean = sanitizeMemo(currentMemo);
  const lead = affiliateActive ? NOTE_ACTIVE : NOTE_SEARCH;
  return `${lead} ${clean ? clean + " " : ""}${CAUTION}`.trim();
}

async function main() {
  const affiliateId = process.env.RAKUTEN_AFFILIATE_ID || "";
  const today = new Date().toISOString().slice(0, 10);
  const hotels = JSON.parse(await fs.readFile("hotels.json", "utf8"));

  const updated = hotels.map((hotel) => {
    const normalUrl = hotel.rakutenTravelUrl || "https://travel.rakuten.co.jp/";
    const destination = buildDestination(hotel);
    const affiliateUrl = buildAffiliateUrl(destination || normalUrl, affiliateId);

    let affiliateStatus = "link-missing";
    if (affiliateUrl) affiliateStatus = "affiliate-active";
    else if (normalUrl) affiliateStatus = "search-only";

    return {
      ...hotel,
      rakutenTravelUrl: normalUrl,
      rakutenTravelAffiliateUrl: affiliateUrl,
      affiliateStatus,
      lastChecked: today,
      memo: buildMemo(hotel.memo, affiliateStatus === "affiliate-active")
    };
  });

  await fs.writeFile("hotels.json", JSON.stringify(updated, null, 2) + "\n", "utf8");
  console.log(`hotels updated: ${updated.length}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
