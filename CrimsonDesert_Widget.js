// ═══════════════════════════════════════════════
//  🎮 붉은사막 PS Store 위젯 — Scriptable용
//  크기: 중간(medium) 권장 / 큰(large) 지원
// ═══════════════════════════════════════════════
//
//  📌 설치 방법:
//  1. App Store에서 "Scriptable" 무료 설치
//  2. 이 코드 전체 복사 → Scriptable 앱에서 새 스크립트로 붙여넣기
//  3. 홈 화면 위젯 추가 → Scriptable → 이 스크립트 선택
//     (When Interacting: Run Script)
//
// ═══════════════════════════════════════════════

// ── 설정 ──────────────────────────────────────
const CONFIG = {
  DATA_URL: "https://raw.githubusercontent.com/gonmau/PreOrderBlackDesert/main/rank_history.json",

  // 출시 시각 (KST)
  RELEASE_KST: new Date("2026-03-20T07:00:00+09:00"),

  // 고정 표시 국가 (순서대로 표시, rank_history.json 키와 동일한 한국어)
  PINNED: ["미국","영국","일본","독일","프랑스","캐나다","스페인","이탈리아","호주","한국","브라질"],

  // 국기 이모지
  FLAGS: {
    "미국":"🇺🇸","영국":"🇬🇧","일본":"🇯🇵","독일":"🇩🇪","프랑스":"🇫🇷",
    "캐나다":"🇨🇦","스페인":"🇪🇸","이탈리아":"🇮🇹","호주":"🇦🇺",
    "한국":"🇰🇷","브라질":"🇧🇷",
  },

  // 색상
  C: {
    bg:      new Color("#0a0608", 1),
    surface: new Color("#1e0e13", 1),
    red:     new Color("#c0392b", 1),
    gold:    new Color("#d4a017", 1),
    text:    new Color("#e8ddd5", 1),
    muted:   new Color("#7a6a65", 1),
    up:      new Color("#2ecc71", 1),
    down:    new Color("#e74c3c", 1),
    same:    new Color("#5a5a5a", 1),
    rank1:   new Color("#e74c3c", 1),
    rank2:   new Color("#3498db", 1),
    rank3:   new Color("#f1c40f", 1),
  }
};

// ── 유틸 ──────────────────────────────────────
function pad2(n) { return String(n).padStart(2, "0"); }

function getCountdown() {
  const diff = CONFIG.RELEASE_KST - new Date();
  if (diff <= 0) return null;
  return {
    days:  Math.floor(diff / 86400000),
    hours: Math.floor((diff % 86400000) / 3600000),
    mins:  Math.floor((diff % 3600000) / 60000),
  };
}

function combinedRank(std, dlx) {
  if (std && dlx) return (std + dlx) / 2;
  return std || dlx || null;
}

function arrow(curr, prev) {
  const C = CONFIG.C;
  if (!curr || !prev) return { text: "", color: C.same };
  const d = prev - curr;
  if (d > 0)  return { text: `▲${Number.isInteger(d) ? d : d.toFixed(1)}`, color: C.up };
  if (d < 0)  return { text: `▼${Number.isInteger(Math.abs(d)) ? Math.abs(d) : Math.abs(d).toFixed(1)}`, color: C.down };
  return { text: "=", color: C.same };
}

function rankColor(idx) {
  const C = CONFIG.C;
  if (idx === 0) return C.rank1;
  if (idx === 1) return C.rank2;
  if (idx === 2) return C.rank3;
  return C.text;
}

function crStr(cr) {
  if (!cr) return "—";
  return Number.isInteger(cr) ? `${cr}위` : `${cr.toFixed(1)}위`;
}

// ── 데이터 처리 ───────────────────────────────
function processData(history) {
  if (!history || !history.length) return null;

  const latest = history[history.length - 1];
  const prev   = history.length >= 2 ? history[history.length - 2] : null;
  const raw    = latest.raw_results || {};
  const praw   = prev ? (prev.raw_results || {}) : {};

  // 고정 국가 목록 기준으로 combined rank 계산
  const rows = CONFIG.PINNED.map(name => {
    const d   = raw[name]   || {};
    const pd  = praw[name]  || {};
    const cr  = combinedRank(d.standard,  d.deluxe);
    const pcr = combinedRank(pd.standard, pd.deluxe);
    return { name, flag: CONFIG.FLAGS[name] || "🏳️", cr, pcr, hasData: cr !== null };
  });

  // 차트인 국가를 combined 순위로 정렬, 미진입은 뒤로
  const sorted = [
    ...rows.filter(r => r.hasData).sort((a, b) => a.cr - b.cr),
    ...rows.filter(r => !r.hasData),
  ];

  // 업데이트 시각
  const updatedAt = new Date(latest.timestamp);
  const timeStr = `${updatedAt.getMonth()+1}/${updatedAt.getDate()} ${pad2(updatedAt.getHours())}:${pad2(updatedAt.getMinutes())}`;

  // 전체 차트인 국가 수
  const totalTracked = Object.values(raw).filter(d => combinedRank(d.standard, d.deluxe) !== null).length;

  // 주요국 평균 순위
  const inChart = sorted.filter(r => r.hasData);
  const avgRank = inChart.length
    ? (inChart.reduce((s, r) => s + r.cr, 0) / inChart.length).toFixed(1)
    : null;

  return { sorted, inChart, timeStr, avgRank, totalTracked };
}

// ── 공통 헤더 ─────────────────────────────────
function addHeader(w, countdown) {
  const C = CONFIG.C;
  const header = w.addStack();
  header.layoutHorizontally();
  header.centerAlignContent();

  const ts = header.addStack();
  ts.layoutVertically();
  const t = ts.addText("⚔️ 붉은사막");
  t.font = Font.boldSystemFont(14);
  t.textColor = C.red;
  const sub = ts.addText("PS Store 주요국 순위");
  sub.font = Font.systemFont(9);
  sub.textColor = C.muted;

  header.addSpacer();

  if (countdown) {
    const box = header.addStack();
    box.layoutVertically();
    box.backgroundColor = C.surface;
    box.cornerRadius = 7;
    box.setPadding(4, 9, 4, 9);
    const ct = box.addText(`${countdown.days}일 ${pad2(countdown.hours)}:${pad2(countdown.mins)}`);
    ct.font = Font.boldMonospacedSystemFont(11);
    ct.textColor = C.gold;
    ct.centerAlignText();
    const cl = box.addText("🇰🇷 출시까지");
    cl.font = Font.systemFont(8);
    cl.textColor = C.muted;
    cl.centerAlignText();
  } else {
    const box = header.addStack();
    box.backgroundColor = new Color("#1a3d1a", 1);
    box.cornerRadius = 7;
    box.setPadding(4, 9, 4, 9);
    const rt = box.addText("✅ 출시됨!");
    rt.font = Font.boldSystemFont(12);
    rt.textColor = C.up;
  }
}

// ── MEDIUM 위젯 (상위 5개국) ──────────────────
function buildMedium(data, countdown) {
  const C = CONFIG.C;
  const w = new ListWidget();
  w.backgroundColor = C.bg;
  w.setPadding(12, 14, 10, 14);

  addHeader(w, countdown);
  w.addSpacer(8);

  if (!data) {
    const e = w.addText("⚠️ 데이터 로드 실패");
    e.font = Font.systemFont(12);
    e.textColor = C.down;
    return w;
  }

  for (let i = 0; i < Math.min(5, data.sorted.length); i++) {
    const r = data.sorted[i];
    const rankIdx = data.inChart.indexOf(r);

    const row = w.addStack();
    row.layoutHorizontally();
    row.centerAlignContent();

    // 순위 번호
    const numEl = row.addText(r.hasData ? `${rankIdx + 1}` : "—");
    numEl.font = Font.boldSystemFont(11);
    numEl.textColor = r.hasData ? rankColor(rankIdx) : C.muted;
    row.addSpacer(6);

    // 국기 + 국가명
    const nameEl = row.addText(`${r.flag} ${r.name}`);
    nameEl.font = Font.systemFont(11);
    nameEl.textColor = C.text;
    nameEl.lineLimit = 1;
    row.addSpacer();

    if (r.hasData) {
      // combined 순위
      const crEl = row.addText(crStr(r.cr));
      crEl.font = Font.boldSystemFont(11);
      crEl.textColor = C.gold;
      row.addSpacer(6);
      // 변동
      const a = arrow(r.cr, r.pcr);
      if (a.text) {
        const aEl = row.addText(a.text);
        aEl.font = Font.boldSystemFont(9);
        aEl.textColor = a.color;
      }
    } else {
      const ncEl = row.addText("미진입");
      ncEl.font = Font.systemFont(10);
      ncEl.textColor = C.muted;
    }

    w.addSpacer(3);
  }

  w.addSpacer();
  const footer = w.addText(`🕐 ${data.timeStr}  ·  전체 ${data.totalTracked}개국 차트인`);
  footer.font = Font.systemFont(8);
  footer.textColor = C.muted;

  return w;
}

// ── LARGE 위젯 (전체 11개국) ──────────────────
function buildLarge(data, countdown) {
  const C = CONFIG.C;
  const w = new ListWidget();
  w.backgroundColor = C.bg;
  w.setPadding(14, 16, 12, 16);

  addHeader(w, countdown);
  w.addSpacer(10);

  if (!data) {
    const e = w.addText("⚠️ 데이터 로드 실패");
    e.font = Font.systemFont(12);
    e.textColor = C.down;
    return w;
  }

  // 요약 스탯 행
  const statsRow = w.addStack();
  statsRow.layoutHorizontally();
  statsRow.spacing = 8;

  function statBox(parent, val, label) {
    const box = parent.addStack();
    box.layoutVertically();
    box.backgroundColor = C.surface;
    box.cornerRadius = 8;
    box.setPadding(6, 10, 6, 10);
    const v = box.addText(val);
    v.font = Font.boldSystemFont(16);
    v.textColor = C.text;
    const l = box.addText(label);
    l.font = Font.systemFont(8);
    l.textColor = C.muted;
  }

  const top = data.inChart[0];
  statBox(statsRow, data.avgRank ? `${data.avgRank}위` : "—", "주요국 평균");
  statBox(statsRow, top ? `${top.flag} ${top.name}` : "—", "주요국 1위");
  statBox(statsRow, `${data.totalTracked}개국`, "전체 차트인");
  statsRow.addSpacer();

  w.addSpacer(10);

  // 전체 11개국 목록
  for (let i = 0; i < data.sorted.length; i++) {
    const r = data.sorted[i];
    const rankIdx = data.inChart.indexOf(r);

    const row = w.addStack();
    row.layoutHorizontally();
    row.centerAlignContent();

    // 순위
    const numEl = row.addText(r.hasData ? `${rankIdx + 1}` : "—");
    numEl.font = Font.boldSystemFont(11);
    numEl.textColor = r.hasData ? rankColor(rankIdx) : C.muted;
    numEl.minimumScaleFactor = 0.8;
    row.addSpacer(8);

    // 국기 + 국가명
    const nameEl = row.addText(`${r.flag} ${r.name}`);
    nameEl.font = Font.systemFont(11);
    nameEl.textColor = C.text;
    nameEl.lineLimit = 1;
    nameEl.minimumScaleFactor = 0.8;
    row.addSpacer();

    if (r.hasData) {
      const crEl = row.addText(crStr(r.cr));
      crEl.font = Font.boldSystemFont(11);
      crEl.textColor = C.gold;
      row.addSpacer(8);
      const a = arrow(r.cr, r.pcr);
      const aEl = row.addText(a.text || "=");
      aEl.font = Font.boldSystemFont(9);
      aEl.textColor = a.color;
    } else {
      const ncEl = row.addText("미진입");
      ncEl.font = Font.systemFont(10);
      ncEl.textColor = C.muted;
      row.addSpacer(8);
      const ph = row.addText("  ");
      ph.font = Font.systemFont(9);
    }

    w.addSpacer(3);
  }

  w.addSpacer();
  const footer = w.addText(`🕐 ${data.timeStr}  ·  전체 ${data.totalTracked}개국 차트인`);
  footer.font = Font.systemFont(8);
  footer.textColor = C.muted;

  return w;
}

// ── SMALL 위젯 ────────────────────────────────
function buildSmall(data, countdown) {
  const C = CONFIG.C;
  const w = new ListWidget();
  w.backgroundColor = C.bg;
  w.setPadding(12, 12, 10, 12);

  const title = w.addText("⚔️ 붉은사막");
  title.font = Font.boldSystemFont(13);
  title.textColor = C.red;
  w.addSpacer(4);

  if (countdown) {
    const box = w.addStack();
    box.layoutVertically();
    box.backgroundColor = C.surface;
    box.cornerRadius = 8;
    box.setPadding(6, 8, 6, 8);
    const d = box.addText(`D-${countdown.days}`);
    d.font = Font.boldSystemFont(24);
    d.textColor = C.gold;
    const t = box.addText(`${pad2(countdown.hours)}:${pad2(countdown.mins)}`);
    t.font = Font.monospacedSystemFont(13);
    t.textColor = C.gold;
    const l = box.addText("🇰🇷 출시까지");
    l.font = Font.systemFont(9);
    l.textColor = C.muted;
  } else {
    const box = w.addStack();
    box.backgroundColor = new Color("#1a3d1a", 1);
    box.cornerRadius = 8;
    box.setPadding(6, 8, 6, 8);
    const rt = box.addText("✅ 출시됨!");
    rt.font = Font.boldSystemFont(16);
    rt.textColor = C.up;
  }

  w.addSpacer(6);

  if (data && data.inChart.length) {
    const top = data.inChart[0];
    const topEl = w.addText(`${top.flag} ${top.name} 1위`);
    topEl.font = Font.semiboldSystemFont(10);
    topEl.textColor = C.text;
    const avg = w.addText(`주요국 평균 ${data.avgRank}위`);
    avg.font = Font.systemFont(9);
    avg.textColor = C.muted;
  }

  w.addSpacer();
  const footer = w.addText(data ? `🕐 ${data.timeStr}` : "—");
  footer.font = Font.systemFont(8);
  footer.textColor = C.muted;

  return w;
}

// ── 메인 ──────────────────────────────────────
async function run() {
  let data = null;
  try {
    const req = new Request(CONFIG.DATA_URL);
    req.timeoutInterval = 10;
    data = processData(await req.loadJSON());
  } catch(e) {
    console.error("데이터 로드 실패:", e.message);
  }

  const countdown = getCountdown();
  const family = config.widgetFamily || "medium";

  let widget;
  if      (family === "small") widget = buildSmall(data, countdown);
  else if (family === "large") widget = buildLarge(data, countdown);
  else                         widget = buildMedium(data, countdown);

  if (config.runsInApp) await widget.presentMedium();

  Script.setWidget(widget);
  Script.complete();
}

await run();
