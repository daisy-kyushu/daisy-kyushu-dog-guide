const fs = require("fs/promises");

const AFF_BASE = "https://hb.afl.rakuten.co.jp/hgc/";
const DEFAULT_RAKUTEN_TRAVEL_URL = "https://travel.rakuten.co.jp/pet/";
const CAUTION = "料金・空室・犬同伴条件・頭数制限・サイズ制限・ワクチン証明の条件は変動するため、予約前に楽天トラベル側・宿公式側で必ず確認してください。";
const NOTE_ACTIVE = "楽天トラベルのアフィリエイト導線を設定済みです。";
const NOTE_SEARCH = "楽天トラベルの通常導線のみです。";

function sanitizeMemo(memo) {
  return String(memo || "")
    .replaceAll(NOTE_ACTIVE, "")
    .replaceAll(NOTE_SEARCH, "")
    .replaceAll(CAUTION, "")
    .replaceAll("楽天トラベルのペット同伴宿ページへ誘導します。", "")
    .replaceAll("地域別の楽天トラベル宿一覧へ誘導します。", "")
    .replaceAll("宿泊施設ごとの楽天トラベルページへ誘導します。", "")
    .replace(/\s+/g, " ")
    .trim();
}

function canonicalHotelUrlFromId(hotelId) {
  if (!hotelId) return "";
  return `https://travel.rakuten.co.jp/HOTEL/${hotelId}/${hotelId}.html`;
}

function normalizeRakutenTravelUrl(url) {
  const value = String(url || "").trim();
  if (!value || value.includes("/keyword/Search.do") || value.includes("search.travel.rakuten.co.jp")) return "";

  try {
    const parsed = new URL(value);

    // 公式宿ページはこの形式に統一する。
    // 例: https://travel.rakuten.co.jp/HOTEL/14985/14985.html
    if (parsed.hostname === "travel.rakuten.co.jp") {
      const hotelMatch = parsed.pathname.match(/\/HOTEL\/(\d+)\//);
      if (hotelMatch) return canonicalHotelUrlFromId(hotelMatch[1]);
      const generic = parsed.toString().replace(/\/+$/, "/");
      return generic === "https://travel.rakuten.co.jp/" ? DEFAULT_RAKUTEN_TRAVEL_URL : parsed.toString();
    }

    // hotel.travel.rakuten.co.jp 側の hinfo/pet/plan などは、宿IDを抜いて安定した HOTEL 形式へ変換する。
    if (parsed.hostname === "hotel.travel.rakuten.co.jp") {
      const idMatch = parsed.pathname.match(/\/(?:hinfo|hotelinfo\/plan)\/(\d+)/);
      if (idMatch) return canonicalHotelUrlFromId(idMatch[1]);
    }

    return "";
  } catch (error) {
    return "";
  }
}

function isGenericTravelUrl(url) {
  const value = String(url || "").trim().replace(/\/+$/, "/");
  return !value || value === "https://travel.rakuten.co.jp/" || value === DEFAULT_RAKUTEN_TRAVEL_URL;
}

function buildDestination(hotel) {
  const explicitUrl = normalizeRakutenTravelUrl(hotel.rakutenTravelUrl);

  // 宿ごとの楽天トラベルURLがある場合は、検索URLやペット宿トップよりも必ず優先する。
  if (explicitUrl && !isGenericTravelUrl(explicitUrl)) return explicitUrl;

  return DEFAULT_RAKUTEN_TRAVEL_URL;
}

function buildAffiliateUrl(destination, affiliateId) {
  if (!affiliateId || !destination) return "";
  const encodedDest = encodeURIComponent(destination);
  return `${AFF_BASE}${affiliateId}/?pc=${encodedDest}&m=${encodedDest}`;
}

function buildMemo(currentMemo, affiliateActive, destination) {
  const clean = sanitizeMemo(currentMemo);
  const lead = affiliateActive ? NOTE_ACTIVE : NOTE_SEARCH;
  const destinationNote = destination !== DEFAULT_RAKUTEN_TRAVEL_URL
    ? "宿泊施設ごとの楽天トラベルページへ誘導します。"
    : "楽天トラベルのペット同伴宿ページへ誘導します。";
  return `${lead} ${destinationNote} ${clean ? clean + " " : ""}${CAUTION}`.trim();
}

async function main() {
  const affiliateId = process.env.RAKUTEN_AFFILIATE_ID || "";
  const today = new Date().toISOString().slice(0, 10);
  const hotels = JSON.parse(await fs.readFile("hotels.json", "utf8"));

  const updated = hotels.map((hotel) => {
    const destination = buildDestination(hotel);
    const affiliateUrl = buildAffiliateUrl(destination, affiliateId);

    let affiliateStatus = "link-missing";
    if (affiliateUrl) affiliateStatus = "affiliate-active";
    else if (destination) affiliateStatus = "search-only";

    return {
      ...hotel,
      rakutenTravelUrl: destination,
      rakutenTravelAffiliateUrl: affiliateUrl,
      affiliateStatus,
      lastChecked: today,
      memo: buildMemo(hotel.memo, affiliateStatus === "affiliate-active", destination)
    };
  });

  await fs.writeFile("hotels.json", JSON.stringify(updated, null, 2) + "\n", "utf8");
  console.log(`hotels updated: ${updated.length}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
