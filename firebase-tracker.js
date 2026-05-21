// ============================================================
// Daisy Kyushu Dog Guide - Firebase Tracker
// アクセスログ・楽天クリック・ページ人気度をFirestoreに記録
// ============================================================

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
import { getFirestore, doc, setDoc, updateDoc, increment, collection, addDoc, serverTimestamp, getDoc } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js";

const firebaseConfig = {
  apiKey: "AIzaSyDRVtANI251gyQjY-okPAzlSYXTGpslwnQ",
  authDomain: "daisysamoyed-86dd8.firebaseapp.com",
  projectId: "daisysamoyed-86dd8",
  storageBucket: "daisysamoyed-86dd8.firebasestorage.app",
  messagingSenderId: "1061044129374",
  appId: "1:1061044129374:web:a117a6ed94a0eb6491aecf",
  measurementId: "G-E1XSFE7LXG"
};

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

// ページIDを取得（URLのパスから生成）
function getPageId() {
  const path = location.pathname.replace(/.*\//, '').replace('.html', '') || 'index';
  return path;
}

// 現在の時間帯を取得（0〜23）
function getHour() {
  return new Date().getHours();
}

// ページビューを記録
async function trackPageView(pageId, pageTitle) {
  try {
    const pid = pageId || getPageId();
    const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
    const hour = getHour();

    // ページ別の累計PV・時間帯PVを更新
    const pageRef = doc(db, "pageStats", pid);
    await setDoc(pageRef, {
      pageId: pid,
      title: pageTitle || document.title,
      totalViews: increment(1),
      [`hourly.h${hour}`]: increment(1),
      lastSeen: serverTimestamp()
    }, { merge: true });

    // 日別ログ
    const dailyRef = doc(db, "dailyStats", today);
    await setDoc(dailyRef, {
      date: today,
      totalViews: increment(1),
      [`pages.${pid}`]: increment(1),
      [`hourly.h${hour}`]: increment(1)
    }, { merge: true });

  } catch (e) {
    // トラッキングエラーはサイレントに無視
    console.debug("Tracker:", e.message);
  }
}

// 楽天アフィリエイトクリックを記録
async function trackRakutenClick(itemId, itemTitle, itemType) {
  try {
    const pageId = getPageId();

    // アイテム別クリック数を更新
    const itemRef = doc(db, "clickStats", itemId);
    await setDoc(itemRef, {
      itemId: itemId,
      title: itemTitle || itemId,
      type: itemType || 'unknown', // 'hotel', 'spot', 'product', 'banner'
      totalClicks: increment(1),
      lastClicked: serverTimestamp()
    }, { merge: true });

    // ページ別クリックログ
    const pageRef = doc(db, "pageStats", pageId);
    await setDoc(pageRef, {
      [`rakutenClicks.${itemId}`]: increment(1)
    }, { merge: true });

    // クリックイベントログ（詳細履歴）
    await addDoc(collection(db, "clickEvents"), {
      itemId: itemId,
      itemTitle: itemTitle || itemId,
      itemType: itemType || 'unknown',
      fromPage: pageId,
      timestamp: serverTimestamp(),
      hour: getHour()
    });

  } catch (e) {
    console.debug("Click Tracker:", e.message);
  }
}

// 楽天リンクに自動でクリックトラッキングを付与
function attachRakutenTracking() {
  document.querySelectorAll('a[href*="rakuten"], a[href*="hb.afl"]').forEach(link => {
    if (link.dataset.tracked) return;
    link.dataset.tracked = "1";

    const href = link.href;
    // ホテルIDを抽出（HOTEL/XXXXX/XXXXX.html）
    const hotelMatch = href.match(/HOTEL\/(\d+)/);
    // バナーかどうか
    const isBanner = link.classList.contains('rk-banner') || link.closest('.rk-banner') !== null;

    let itemId, itemTitle, itemType;
    if (hotelMatch) {
      itemId = `hotel_${hotelMatch[1]}`;
      itemTitle = link.textContent.trim() || `ホテル${hotelMatch[1]}`;
      itemType = 'hotel';
    } else if (isBanner) {
      itemId = `banner_${getPageId()}`;
      itemTitle = link.querySelector('.rk-title')?.textContent || 'バナー';
      itemType = 'banner';
    } else {
      itemId = `rakuten_${btoa(href).slice(0, 16)}`;
      itemTitle = link.textContent.trim() || '楽天リンク';
      itemType = 'product';
    }

    link.addEventListener('click', () => {
      trackRakutenClick(itemId, itemTitle, itemType);
    });
  });
}

// 人気スポット/ホテルデータを取得（ホーム表示順ソート用）
async function getPopularItems(type, limit = 10) {
  try {
    const { getDocs, query, where, orderBy, limit: fsLimit } = await import(
      "https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js"
    );
    const q = query(
      collection(db, "clickStats"),
      where("type", "==", type),
      orderBy("totalClicks", "desc"),
      fsLimit(limit)
    );
    const snap = await getDocs(q);
    return snap.docs.map(d => ({ id: d.id, ...d.data() }));
  } catch (e) {
    return [];
  }
}

// 初期化（DOMContentLoaded後に自動実行）
function initTracker(pageTitle) {
  trackPageView(null, pageTitle);
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attachRakutenTracking);
  } else {
    attachRakutenTracking();
    // 動的に追加されるリンクにも対応
    const observer = new MutationObserver(attachRakutenTracking);
    observer.observe(document.body, { childList: true, subtree: true });
  }
}

export { initTracker, trackRakutenClick, trackPageView, getPopularItems, db };
