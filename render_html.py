# -*- coding: utf-8 -*-
"""crimson_desert_schedule_analysis.json → steam_rank_timeline.html 렌더러"""
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "crimson_desert_schedule_analysis.json")
CHARTJS_FILE = os.path.join(BASE_DIR, "chartjs_bundle.js")
OUT_FILE = os.path.join(BASE_DIR, "steam_rank_timeline.html")

with open(DATA_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

with open(CHARTJS_FILE, "r", encoding="utf-8") as f:
    chartjs_src = f.read()

data_json = json.dumps(data, ensure_ascii=False)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>붉은사막 — 스팀 순위 × 일정 타임라인</title>
<script>__CHARTJS_INLINE__</script>
<style>
  :root {
    --bg-0:#0d1117; --bg-1:#161b22; --bg-2:#1c2129;
    --tx-1:#e6edf3; --tx-2:#9aa4b2; --tx-3:#6b7280;
    --border:#2a3038;
    --c-rank:#4a9eff;
    --c-sales:#f1c40f;
    --c-update:#2ecc71;
    --c-pa:#ff4757;
  }
  * { box-sizing:border-box; }
  body {
    margin:0; padding:24px; background:var(--bg-0); color:var(--tx-1);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Pretendard,sans-serif;
  }
  h1 { font-size:20px; margin:0 0 4px; }
  .sub { color:var(--tx-2); font-size:13px; margin-bottom:20px; }
  .card {
    background:var(--bg-1); border:1px solid var(--border); border-radius:12px;
    padding:18px; margin-bottom:20px;
  }
  .legend { display:flex; flex-wrap:wrap; gap:14px; margin-bottom:14px; font-size:12px; color:var(--tx-2); }
  .legend span { display:inline-flex; align-items:center; gap:6px; }
  .dot { width:10px; height:10px; border-radius:50%; display:inline-block; }
  .chart-wrap { position:relative; height:460px; }
  table { width:100%; border-collapse:collapse; font-size:12px; margin-top:8px; }
  th, td { text-align:left; padding:6px 8px; border-bottom:1px solid var(--border); }
  th { color:var(--tx-3); font-weight:600; text-transform:uppercase; font-size:10px; letter-spacing:.5px; }
  td.label { color:var(--tx-1); }
  .tag { display:inline-block; padding:1px 7px; border-radius:6px; font-size:10px; font-weight:700; }
  .grid2 { display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; }
  @media (max-width: 900px) { .grid2 { grid-template-columns:1fr; } }
  footer { color:var(--tx-3); font-size:11px; margin-top:18px; }
</style>
</head>
<body>

<h1>붉은사막 — 스팀 Top Seller 평균 순위 × 판매/업데이트/펄어비스 일정</h1>
<div class="sub">source: steam_topseller_history.json · generated: __GENERATED_AT__</div>

<div class="card">
  <div class="legend">
    <span><i class="dot" style="background:var(--c-rank)"></i> 일 평균 순위</span>
    <span><i class="dot" style="background:var(--c-sales)"></i> 판매량 공지</span>
    <span><i class="dot" style="background:var(--c-update)"></i> 게임 업데이트</span>
    <span><i class="dot" style="background:var(--c-pa)"></i> 펄어비스 일정</span>
  </div>
  <div class="chart-wrap"><canvas id="rankChart"></canvas></div>
</div>

<div class="grid2">
  <div class="card">
    <div class="legend"><span><i class="dot" style="background:var(--c-sales)"></i> 판매량 공지</span></div>
    <table><thead><tr><th>일자</th><th>D+</th><th>내용</th></tr></thead><tbody id="tbl-sales"></tbody></table>
  </div>
  <div class="card">
    <div class="legend"><span><i class="dot" style="background:var(--c-update)"></i> 게임 업데이트</span></div>
    <table><thead><tr><th>일자</th><th>내용</th></tr></thead><tbody id="tbl-update"></tbody></table>
  </div>
  <div class="card">
    <div class="legend"><span><i class="dot" style="background:var(--c-pa)"></i> 펄어비스 일정</span></div>
    <table><thead><tr><th>일자</th><th>내용</th></tr></thead><tbody id="tbl-pa"></tbody></table>
  </div>
</div>

<div id="err-banner" style="display:none;background:#3a1a1a;border:1px solid #ff4757;color:#ff9aa2;padding:10px 14px;border-radius:8px;font-size:12px;margin-bottom:16px;"></div>

<footer>average rank = 해당 일자 스냅샷들의 국가별 순위 평균의 일 평균 (숫자가 작을수록 상위). 데이터: crimson_desert_schedule_analysis.json</footer>

<script>
function showError(msg) {
  const el = document.getElementById('err-banner');
  el.style.display = 'block';
  el.textContent = '⚠ ' + msg;
  console.error(msg);
}

const DATA = __DATA_JSON__;

const daily = DATA.daily_average_rank;
const labels = daily.map(d => d.date);
const rankSeries = daily.map(d => d.avg_rank);
const bandLow = daily.map(d => d.best_snapshot_rank);   // 더 좋은(작은) 순위
const bandHigh = daily.map(d => d.worst_snapshot_rank); // 더 나쁜(큰) 순위

function dateIndex(dateStr) {
  // event date(YYYY-MM-DD or ISO) 이후 첫 라벨 인덱스, 없으면 가장 가까운 마지막 인덱스
  const target = dateStr.slice(0, 10);
  let idx = labels.findIndex(l => l >= target);
  if (idx === -1) idx = labels.length - 1;
  return idx;
}

const events = [
  ...DATA.sales_milestones.map(e => ({ idx: dateIndex(e.date), color: 'var(--c-sales)', label: e.label, raw: e.date })),
  ...DATA.game_updates.map(e => ({ idx: dateIndex(e.date), color: 'var(--c-update)', label: e.label, raw: e.date })),
  ...DATA.pearl_abyss_events.map(e => ({ idx: dateIndex(e.date), color: 'var(--c-pa)', label: e.label, raw: e.date })),
];

const verticalLinesPlugin = {
  id: 'verticalLinesPlugin',
  afterDatasetsDraw(chart) {
    const { ctx, chartArea, scales } = chart;
    if (!chartArea) return;
    const xScale = scales.x;
    ctx.save();
    events.forEach(ev => {
      const x = xScale.getPixelForValue(ev.idx);
      if (x < chartArea.left || x > chartArea.right) return;
      ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue(ev.color.replace('var(', '').replace(')', '')) || ev.color;
      ctx.setLineDash([4, 3]);
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, chartArea.top);
      ctx.lineTo(x, chartArea.bottom);
      ctx.stroke();
    });
    ctx.restore();
  }
};

try {
if (typeof Chart === 'undefined') throw new Error('Chart.js 로드 실패 (라이브러리가 내장되어 있어야 하는데 없음)');
const ctx = document.getElementById('rankChart').getContext('2d');
new Chart(ctx, {
  type: 'line',
  data: {
    labels,
    datasets: [
      {
        label: '일 평균 순위',
        data: rankSeries,
        borderColor: '#4a9eff',
        backgroundColor: 'rgba(74,158,255,0.08)',
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.15,
        fill: true,
        order: 1,
      },
      {
        label: '스냅샷 최저(베스트) 순위',
        data: bandLow,
        borderColor: 'rgba(74,158,255,0.35)',
        borderWidth: 1,
        pointRadius: 0,
        borderDash: [2, 2],
        fill: false,
        order: 2,
      },
      {
        label: '스냅샷 최고(워스트) 순위',
        data: bandHigh,
        borderColor: 'rgba(74,158,255,0.35)',
        borderWidth: 1,
        pointRadius: 0,
        borderDash: [2, 2],
        fill: false,
        order: 2,
      },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { labels: { color: '#9aa4b2', font: { size: 11 } } },
      tooltip: {
        callbacks: {
          afterBody(items) {
            const idx = items[0].dataIndex;
            const hit = events.filter(e => e.idx === idx);
            if (!hit.length) return [];
            return ['', '── 일정 ──', ...hit.map(h => '• ' + h.label)];
          }
        }
      }
    },
    scales: {
      x: {
        ticks: { color: '#6b7280', maxRotation: 60, minRotation: 60, autoSkip: true, maxTicksLimit: 30, font: { size: 9 } },
        grid: { color: 'rgba(255,255,255,0.04)' },
      },
      y: {
        reverse: true,
        title: { display: true, text: '순위 (낮을수록 상위)', color: '#9aa4b2' },
        ticks: { color: '#6b7280' },
        grid: { color: 'rgba(255,255,255,0.06)' },
      },
    },
  },
  plugins: [verticalLinesPlugin],
});
} catch (err) {
  showError('차트 렌더링 실패: ' + err.message);
}

try {
  function fillTable(id, rows, cols) {
    const tbody = document.getElementById(id);
    tbody.innerHTML = rows.map(r => '<tr>' + cols.map(c => '<td class="label">' + (r[c] ?? '') + '</td>').join('') + '</tr>').join('');
  }

  fillTable('tbl-sales', DATA.sales_milestones.map(e => ({
    date: e.date.slice(0, 16).replace('T', ' '),
    day: 'D+' + e.day,
    label: e.label,
  })), ['date', 'day', 'label']);

  fillTable('tbl-update', DATA.game_updates.map(e => ({
    date: e.date,
    label: e.label,
  })), ['date', 'label']);

  fillTable('tbl-pa', DATA.pearl_abyss_events.map(e => ({
    date: e.date,
    label: e.label,
  })), ['date', 'label']);
} catch (err) {
  showError('일정 테이블 렌더링 실패: ' + err.message);
}
</script>
</body>
</html>
"""

html = (
    HTML_TEMPLATE
    .replace("__CHARTJS_INLINE__", chartjs_src)
    .replace("__DATA_JSON__", data_json)
    .replace("__GENERATED_AT__", data["generated_at"])
)

with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write(html)

print(f"[OK] {OUT_FILE} 저장 완료 ({os.path.getsize(OUT_FILE)} bytes)")
