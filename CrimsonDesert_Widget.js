// ═══════════════════════════════════════════════
//  🎮 붉은사막 PS Store 위젯 — Scriptable용
//  크기: 중간(medium) 권장 / 큰(large) 지원
// ═══════════════════════════════════════════════
//
//  📌 설정 방법:
//  1. App Store에서 "Scriptable" 무료 설치
//  2. 이 코드 전체 복사 → Scriptable 앱에서 새 스크립트로 붙여넣기
//  3. 아래 CONFIG의 DATA_URL을 본인의 rank_history.json URL로 변경
//  4. 홈 화면에서 위젯 추가 → Scriptable 선택 → 스크립트 선택
//
// ═══════════════════════════════════════════════

// ── 설정 ──────────────────────────────────────
const CONFIG = {
  // ⚠️ 본인의 rank_history.json 공개 URL로 반드시 변경!
  // 예: GitHub Raw URL, Cloudflare Pages URL 등
  DATA_URL: "https://raw.githubusercontent.com/gonmau/PreOrderBlackDesert/main/rank_history.json",

  // 출시 시각 (KST)
  RELEASE_KST: new Date("2026-03-20T07:00:00+09:00"),

  // 위젯에 표시할 상위 국가 수
  TOP_N: 5,

  // 색상
  COLORS: {
    bg:        new Color("#0a0608", 1),
    surface:   new Color("#1a0d10", 1),
    red:       new Color("#c0392b", 1),
    redGlow:   new Color("#e74c3c", 1),
    gold:      new Color("#d4a017", 1),
    text:      new Color("#e8ddd5", 1),
    muted:     new Color("#7a6a65", 1),
    up:        new Color("#2ecc71", 1),
    down:      new Color("#e74c3c", 1),
    same:      new Color("#5a5a5a", 1),
    accent:    new Color("#8b1a2b", 1),
  }
};

// ── 유틸 함수 ──────────────────────────────────
function pad2(n) { return String(n).padStart(2, "0"); }

function getCountdown() {
  const now = new Date();
  const diff = CONFIG.RELEASE_KST - now;
  if (diff <= 0) return null; // 출시됨
  const days  = Math.floor(diff / 86400000);
  const hours = Math.floor((diff % 86400000) / 3600000);
  const mins  = Math.floor((diff % 3600000) / 60000);
  return { days, hours, mins };
}

function combinedRank(std, dlx) {
  if (std && dlx) return (std + dlx) / 2;
  return std || dlx || null;
}

function fmtRank(n) {
  if (!n) return "—";
  return `${n}위`;
}

function diffArrow(curr, prev) {
  if (!curr || !prev) return { text: "", color: CONFIG.COLORS.same };
  const d = prev - curr; // 순위는 작을수록 좋으니 prev > curr = 상승
  if (d > 0)  return { text: `▲${d}`, color: CONFIG.COLORS.up };
  if (d < 0)  return { text: `▼${Math.abs(d)}`, color: CONFIG.COLORS.down };
  return { text: "=", color: CONFIG.COLORS.same };
}

// ── 데이터 처리 ───────────────────────────────
function processData(history) {
  if (!history || history.length === 0) return null;

  const latest = history[history.length - 1];
  const prev   = history.length >= 2 ? history[history.length - 2] : null;

  const raw  = latest.raw_results || {};
  const praw = prev?.raw_results  || {};

  // 국가별 combined rank 계산 후 정렬
  const countries = Object.entries(raw)
    .map(([country, d]) => {
      const cr  = combinedRank(d.standard, d.deluxe);
      const pd  = praw[country] || {};
      const pcr = combinedRank(pd.standard, pd.deluxe);
      return { country, std: d.standard, dlx: d.deluxe, cr, pcr };
    })
    .filter(c => c.cr !== null)
    .sort((a, b) => a.cr - b.cr);

  // 전체 평균 순위 계산 (가중치 없이 단순 평균)
  let sum = 0, cnt = 0;
  for (const c of countries) {
    if (c.cr) { sum += c.cr; cnt++; }
  }
  const avgRank = cnt ? (sum / cnt).toFixed(1) : null;

  // 이전 평균
  let psum = 0, pcnt = 0;
  for (const [, pd] of Object.entries(praw)) {
    const pcr = combinedRank(pd.standard, pd.deluxe);
    if (pcr) { psum += pcr; pcnt++; }
  }
  const prevAvgRank = pcnt ? (psum / pcnt).toFixed(1) : null;

  // 업데이트 시각
  const updatedAt = new Date(latest.timestamp);
  const timeStr = `${updatedAt.getMonth()+1}/${updatedAt.getDate()} ${pad2(updatedAt.getHours())}:${pad2(updatedAt.getMinutes())}`;

  return {
    top: countries.slice(0, CONFIG.TOP_N),
    all: countries,
    avgRank,
    prevAvgRank,
    timeStr,
    trackingCount: countries.length,
  };
}

// ── 위젯 빌더 (중간 크기) ─────────────────────
function buildMediumWidget(data, countdown) {
  const w = new ListWidget();
  w.backgroundColor = CONFIG.COLORS.bg;
  w.setPadding(12, 14, 10, 14);
  w.url = CONFIG.DATA_URL.replace("rank_history.json", ""); // 탭하면 대시보드 오픈

  // ── 헤더 ──
  const header = w.addStack();
  header.layoutHorizontally();
  header.centerAlignContent();

  const titleStack = header.addStack();
  titleStack.layoutVertically();

  const title = titleStack.addText("⚔️ 붉은사막");
  title.font = Font.boldSystemFont(14);
  title.textColor = CONFIG.COLORS.red;

  const sub = titleStack.addText("PS Store 글로벌 랭킹");
  sub.font = Font.systemFont(9);
  sub.textColor = CONFIG.COLORS.muted;

  header.addSpacer();

  // 카운트다운 or 출시
  if (countdown) {
    const cdStack = header.addStack();
    cdStack.layoutVertically();
    cdStack.backgroundColor = CONFIG.COLORS.surface;
    cdStack.cornerRadius = 6;
    cdStack.setPadding(3, 7, 3, 7);

    const cdTime = cdStack.addText(`${countdown.days}일 ${pad2(countdown.hours)}:${pad2(countdown.mins)}`);
    cdTime.font = Font.boldMonospacedSystemFont(11);
    cdTime.textColor = CONFIG.COLORS.gold;

    const cdLabel = cdStack.addText("출시까지");
    cdLabel.font = Font.systemFont(8);
    cdLabel.textColor = CONFIG.COLORS.muted;
    cdLabel.centerAlignText();
  } else {
    const relStack = header.addStack();
    relStack.backgroundColor = new Color("#1a3d1a", 1);
    relStack.cornerRadius = 6;
    relStack.setPadding(3, 7, 3, 7);
    const relText = relStack.addText("✅ 출시됨");
    relText.font = Font.boldSystemFont(11);
    relText.textColor = CONFIG.COLORS.up;
  }

  w.addSpacer(8);

  // ── 요약 스탯 ──
  if (data) {
    const statsRow = w.addStack();
    statsRow.layoutHorizontally();

    // 평균 순위
    const avgBox = statsRow.addStack();
    avgBox.layoutVertically();
    avgBox.backgroundColor = CONFIG.COLORS.surface;
    avgBox.cornerRadius = 6;
    avgBox.setPadding(5, 8, 5, 8);

    const avgVal = avgBox.addText(data.avgRank ? `${data.avgRank}위` : "—");
    avgVal.font = Font.boldSystemFont(16);
    avgVal.textColor = CONFIG.COLORS.text;

    const avgLabel = avgBox.addText("가중 평균 순위");
    avgLabel.font = Font.systemFont(8);
    avgLabel.textColor = CONFIG.COLORS.muted;

    // 평균 변동
    if (data.avgRank && data.prevAvgRank) {
      const d = parseFloat(data.prevAvgRank) - parseFloat(data.avgRank);
      const diffText = d > 0 ? `▲ ${d.toFixed(1)} 상승` : d < 0 ? `▼ ${Math.abs(d).toFixed(1)} 하락` : "변동없음";
      const diffColor = d > 0 ? CONFIG.COLORS.up : d < 0 ? CONFIG.COLORS.down : CONFIG.COLORS.same;
      const diffEl = avgBox.addText(diffText);
      diffEl.font = Font.systemFont(8);
      diffEl.textColor = diffColor;
    }

    statsRow.addSpacer(8);

    // 추적 국가 수
    const cntBox = statsRow.addStack();
    cntBox.layoutVertically();
    cntBox.backgroundColor = CONFIG.COLORS.surface;
    cntBox.cornerRadius = 6;
    cntBox.setPadding(5, 8, 5, 8);

    const cntVal = cntBox.addText(`${data.trackingCount}개국`);
    cntVal.font = Font.boldSystemFont(16);
    cntVal.textColor = CONFIG.COLORS.text;

    const cntLabel = cntBox.addText("차트인 국가");
    cntLabel.font = Font.systemFont(8);
    cntLabel.textColor = CONFIG.COLORS.muted;

    statsRow.addSpacer();

    w.addSpacer(8);

    // ── 상위 N개국 랭킹 ──
    const rankTitle = w.addText(`🏆 TOP ${CONFIG.TOP_N} 국가 (combined 순위)`);
    rankTitle.font = Font.semiboldSystemFont(9);
    rankTitle.textColor = CONFIG.COLORS.muted;

    w.addSpacer(4);

    for (const c of data.top) {
      const row = w.addStack();
      row.layoutHorizontally();
      row.centerAlignContent();

      // 국가명
      const nameText = row.addText(c.country);
      nameText.font = Font.systemFont(10);
      nameText.textColor = CONFIG.COLORS.text;
      nameText.lineLimit = 1;
      nameText.minimumScaleFactor = 0.7;

      row.addSpacer();

      // 스탠다드
      if (c.std) {
        const stdText = row.addText(`S:${c.std}위`);
        stdText.font = Font.systemFont(10);
        stdText.textColor = CONFIG.COLORS.redGlow;
      }

      if (c.std && c.dlx) row.addSpacer(4);

      // 디럭스
      if (c.dlx) {
        const dlxText = row.addText(`D:${c.dlx}위`);
        dlxText.font = Font.systemFont(10);
        dlxText.textColor = CONFIG.COLORS.gold;
      }

      row.addSpacer(8);

      // 변동
      const arrow = diffArrow(c.cr, c.pcr);
      if (arrow.text) {
        const arrowText = row.addText(arrow.text);
        arrowText.font = Font.boldSystemFont(9);
        arrowText.textColor = arrow.color;
      }

      w.addSpacer(2);
    }
  } else {
    // 데이터 없음
    const errText = w.addText("⚠️ 데이터 로드 실패\nCONFIG.DATA_URL을 확인하세요");
    errText.font = Font.systemFont(11);
    errText.textColor = CONFIG.COLORS.down;
  }

  w.addSpacer();

  // ── 푸터 ──
  const footer = w.addText(data ? `🕐 ${data.timeStr} 업데이트` : "데이터 없음");
  footer.font = Font.systemFont(8);
  footer.textColor = CONFIG.COLORS.muted;

  return w;
}

// ── 큰 위젯 (large) ───────────────────────────
function buildLargeWidget(data, countdown) {
  const w = new ListWidget();
  w.backgroundColor = CONFIG.COLORS.bg;
  w.setPadding(14, 16, 12, 16);

  // ── 헤더 ──
  const header = w.addStack();
  header.layoutHorizontally();
  header.centerAlignContent();

  const titleStack = header.addStack();
  titleStack.layoutVertically();
  const title = titleStack.addText("⚔️ 붉은사막 (Crimson Desert)");
  title.font = Font.boldSystemFont(15);
  title.textColor = CONFIG.COLORS.red;
  const sub = titleStack.addText("PlayStation Store 글로벌 랭킹 트래커");
  sub.font = Font.systemFont(9);
  sub.textColor = CONFIG.COLORS.muted;

  header.addSpacer();

  // 카운트다운
  if (countdown) {
    const cdStack = header.addStack();
    cdStack.layoutVertically();
    cdStack.backgroundColor = CONFIG.COLORS.surface;
    cdStack.cornerRadius = 8;
    cdStack.setPadding(5, 10, 5, 10);

    const cdTime = cdStack.addText(`${countdown.days}d ${pad2(countdown.hours)}:${pad2(countdown.mins)}`);
    cdTime.font = Font.boldMonospacedSystemFont(13);
    cdTime.textColor = CONFIG.COLORS.gold;
    const cdLabel = cdStack.addText("🇰🇷 출시까지");
    cdLabel.font = Font.systemFont(8);
    cdLabel.textColor = CONFIG.COLORS.muted;
    cdLabel.centerAlignText();
  } else {
    const relStack = header.addStack();
    relStack.backgroundColor = new Color("#1a3d1a", 1);
    relStack.cornerRadius = 8;
    relStack.setPadding(5, 10, 5, 10);
    const relText = relStack.addText("✅ 출시됨!");
    relText.font = Font.boldSystemFont(13);
    relText.textColor = CONFIG.COLORS.up;
  }

  w.addSpacer(10);

  if (data) {
    // ── 요약 스탯 행 ──
    const statsRow = w.addStack();
    statsRow.layoutHorizontally();
    statsRow.spacing = 8;

    function addStatBox(parent, value, label, diff) {
      const box = parent.addStack();
      box.layoutVertically();
      box.backgroundColor = CONFIG.COLORS.surface;
      box.cornerRadius = 8;
      box.setPadding(7, 10, 7, 10);

      const valEl = box.addText(value);
      valEl.font = Font.boldSystemFont(18);
      valEl.textColor = CONFIG.COLORS.text;

      const lbEl = box.addText(label);
      lbEl.font = Font.systemFont(8);
      lbEl.textColor = CONFIG.COLORS.muted;

      if (diff) {
        const dEl = box.addText(diff.text);
        dEl.font = Font.systemFont(8);
        dEl.textColor = diff.color;
      }
    }

    // 평균 순위 변동
    let avgDiff = null;
    if (data.avgRank && data.prevAvgRank) {
      const d = parseFloat(data.prevAvgRank) - parseFloat(data.avgRank);
      avgDiff = { text: d > 0 ? `▲ ${d.toFixed(1)}` : d < 0 ? `▼ ${Math.abs(d).toFixed(1)}` : "=", color: d > 0 ? CONFIG.COLORS.up : d < 0 ? CONFIG.COLORS.down : CONFIG.COLORS.same };
    }

    addStatBox(statsRow, data.avgRank ? `${data.avgRank}위` : "—", "평균 순위", avgDiff);
    addStatBox(statsRow, `${data.trackingCount}개국`, "차트인 국가", null);
    addStatBox(statsRow, data.top[0] ? data.top[0].country : "—", "1위 국가", null);
    statsRow.addSpacer();

    w.addSpacer(10);

    // ── 상위 국가 랭킹 테이블 ──
    const rankHeader = w.addStack();
    rankHeader.layoutHorizontally();
    const rTitle = rankHeader.addText(`🏆 상위 ${Math.min(10, data.all.length)}개국 순위`);
    rTitle.font = Font.semiboldSystemFont(10);
    rTitle.textColor = CONFIG.COLORS.muted;

    w.addSpacer(5);

    const topList = data.all.slice(0, 10);
    for (let i = 0; i < topList.length; i++) {
      const c = topList[i];
      const row = w.addStack();
      row.layoutHorizontally();
      row.centerAlignContent();

      // 순위 뱃지
      const rankNum = row.addText(`${i + 1}`);
      rankNum.font = Font.boldSystemFont(10);
      rankNum.textColor = i === 0 ? new Color("#e74c3c") : i === 1 ? new Color("#3498db") : i === 2 ? new Color("#f1c40f") : CONFIG.COLORS.muted;
      rankNum.minimumScaleFactor = 0.8;

      row.addSpacer(6);

      // 국가명
      const nameText = row.addText(c.country);
      nameText.font = Font.systemFont(11);
      nameText.textColor = CONFIG.COLORS.text;
      nameText.lineLimit = 1;

      row.addSpacer();

      // 스탠다드
      if (c.std) {
        const stdText = row.addText(`S:${c.std}`);
        stdText.font = Font.systemFont(10);
        stdText.textColor = CONFIG.COLORS.redGlow;
      }

      if (c.std && c.dlx) { row.addSpacer(4); }

      // 디럭스
      if (c.dlx) {
        const dlxText = row.addText(`D:${c.dlx}`);
        dlxText.font = Font.systemFont(10);
        dlxText.textColor = CONFIG.COLORS.gold;
      }

      row.addSpacer(8);

      // 변동
      const arrow = diffArrow(c.cr, c.pcr);
      if (arrow.text) {
        const arrowText = row.addText(arrow.text);
        arrowText.font = Font.boldSystemFont(9);
        arrowText.textColor = arrow.color;
      } else {
        const placeholder = row.addText("  ");
        placeholder.font = Font.systemFont(9);
      }

      w.addSpacer(3);
    }
  } else {
    const errText = w.addText("⚠️ 데이터를 불러올 수 없습니다.\nCONFIG.DATA_URL을 확인하세요.");
    errText.font = Font.systemFont(12);
    errText.textColor = CONFIG.COLORS.down;
  }

  w.addSpacer();

  // ── 푸터 ──
  const footer = w.addText(data ? `🕐 마지막 업데이트: ${data.timeStr}  |  30분마다 자동 갱신` : "데이터 없음");
  footer.font = Font.systemFont(8);
  footer.textColor = CONFIG.COLORS.muted;

  return w;
}

// ── 작은 위젯 (small) ─────────────────────────
function buildSmallWidget(data, countdown) {
  const w = new ListWidget();
  w.backgroundColor = CONFIG.COLORS.bg;
  w.setPadding(12, 12, 10, 12);

  const title = w.addText("⚔️ 붉은사막");
  title.font = Font.boldSystemFont(13);
  title.textColor = CONFIG.COLORS.red;

  w.addSpacer(4);

  // 카운트다운
  if (countdown) {
    const cdBox = w.addStack();
    cdBox.layoutVertically();
    cdBox.backgroundColor = CONFIG.COLORS.surface;
    cdBox.cornerRadius = 8;
    cdBox.setPadding(6, 8, 6, 8);

    const dayText = cdBox.addText(`${countdown.days}일`);
    dayText.font = Font.boldSystemFont(22);
    dayText.textColor = CONFIG.COLORS.gold;

    const timeText = cdBox.addText(`${pad2(countdown.hours)}시 ${pad2(countdown.mins)}분`);
    timeText.font = Font.systemFont(12);
    timeText.textColor = CONFIG.COLORS.gold;

    const lbText = cdBox.addText("🇰🇷 출시까지");
    lbText.font = Font.systemFont(9);
    lbText.textColor = CONFIG.COLORS.muted;
  } else {
    const relBox = w.addStack();
    relBox.backgroundColor = new Color("#1a3d1a", 1);
    relBox.cornerRadius = 8;
    relBox.setPadding(6, 8, 6, 8);
    const relText = relBox.addText("✅ 출시됨!");
    relText.font = Font.boldSystemFont(16);
    relText.textColor = CONFIG.COLORS.up;
  }

  w.addSpacer(6);

  if (data) {
    const avgText = w.addText(data.avgRank ? `평균 ${data.avgRank}위` : "데이터 없음");
    avgText.font = Font.semiboldSystemFont(11);
    avgText.textColor = CONFIG.COLORS.text;

    const cntText = w.addText(`${data.trackingCount}개국 차트인`);
    cntText.font = Font.systemFont(9);
    cntText.textColor = CONFIG.COLORS.muted;
  }

  w.addSpacer();

  const footer = w.addText(data ? `🕐 ${data.timeStr}` : "—");
  footer.font = Font.systemFont(8);
  footer.textColor = CONFIG.COLORS.muted;

  return w;
}

// ── 메인 실행 ─────────────────────────────────
async function run() {
  let data = null;

  // 데이터 패치
  try {
    const req = new Request(CONFIG.DATA_URL);
    req.timeoutInterval = 10;
    const json = await req.loadJSON();
    data = processData(json);
  } catch (e) {
    console.error("데이터 로드 실패:", e.message);
  }

  const countdown = getCountdown();
  const family = config.widgetFamily || "medium";

  let widget;
  if (family === "small") {
    widget = buildSmallWidget(data, countdown);
  } else if (family === "large") {
    widget = buildLargeWidget(data, countdown);
  } else {
    widget = buildMediumWidget(data, countdown);
  }

  // Scriptable 앱 내 미리보기
  if (config.runsInApp) {
    await widget.presentMedium();
  }

  Script.setWidget(widget);
  Script.complete();
}

await run();
