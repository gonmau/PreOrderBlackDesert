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
    --c-rank-ps:#ffa726;
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
  .badge {
    display:inline-flex; align-items:center; justify-content:center;
    width:18px; height:18px; border-radius:50%; color:#0d1117;
    font-size:10px; font-weight:800; flex-shrink:0;
  }
  td.num { width:26px; }
  .grid2 { display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; }
  @media (max-width: 900px) { .grid2 { grid-template-columns:1fr; } }
  footer { color:var(--tx-3); font-size:11px; margin-top:18px; }
</style>
</head>
<body>

<h1>붉은사막 — 스팀 × PS Store 평균 순위 × 판매/업데이트/펄어비스 일정</h1>
<div class="sub">source: steam_topseller_history.json, bestseller_history.json · generated: __GENERATED_AT__</div>

<div class="card">
  <div class="legend">
    <span><i class="dot" style="background:var(--c-rank)"></i> Steam 일 평균 순위</span>
    <span><i class="dot" style="background:var(--c-rank-ps)"></i> PS Store 일 평균 순위</span>
    <span><i class="dot" style="background:var(--c-sales)"></i> 판매량 공지</span>
    <span><i class="dot" style="background:var(--c-update)"></i> 게임 업데이트</span>
    <span><i class="dot" style="background:var(--c-pa)"></i> 펄어비스 일정</span>
  </div>
  <div class="chart-wrap"><canvas id="rankChart"></canvas></div>
</div>

<div class="grid2">
  <div class="card">
    <div class="legend"><span><i class="dot" style="background:var(--c-sales)"></i> 판매량 공지</span></div>
    <table><thead><tr><th></th><th>일자</th><th>D+</th><th>내용</th></tr></thead><tbody id="tbl-sales"></tbody></table>
  </div>
  <div class="card">
    <div class="legend"><span><i class="dot" style="background:var(--c-update)"></i> 게임 업데이트</span></div>
    <table><thead><tr><th></th><th>일자</th><th>내용</th></tr></thead><tbody id="tbl-update"></tbody></table>
  </div>
  <div class="card">
    <div class="legend"><span><i class="dot" style="background:var(--c-pa)"></i> 펄어비스 일정</span></div>
    <table><thead><tr><th></th><th>일자</th><th>내용</th></tr></thead><tbody id="tbl-pa"></tbody></table>
  </div>
</div>

<div id="err-banner" style="display:none;background:#3a1a1a;border:1px solid #ff4757;color:#ff9aa2;padding:10px 14px;border-radius:8px;font-size:12px;margin-bottom:16px;"></div>

<footer>daily average rank = 해당 일자 스냅샷들의 국가별 순위 평균의 일 평균 (숫자가 작을수록 상위, Steam·PS Store 각각 동일 방식 계산). 데이터: crimson_desert_schedule_analysis.json</footer>

<script>
function showError(msg) {
  const el = document.getElementById('err-banner');
  el.style.display = 'block';
  el.textContent = '⚠ ' + msg;
  console.error(msg);
}

const DATA = __DATA_JSON__;

const dailySteam = DATA.daily_average_rank_steam;
const dailyPs = DATA.daily_average_rank_ps;

// 두 소스의 날짜를 합쳐 하나의 x축으로 사용 (없는 날은 null → 선이 끊김)
const labelSet = new Set([...dailySteam.map(d => d.date), ...dailyPs.map(d => d.date)]);
const labels = [...labelSet].sort();

const steamByDate = Object.fromEntries(dailySteam.map(d => [d.date, d.avg_rank]));
const psByDate = Object.fromEntries(dailyPs.map(d => [d.date, d.avg_rank]));

const steamSeries = labels.map(d => steamByDate[d] ?? null);
const psSeries = labels.map(d => psByDate[d] ?? null);

function dateIndex(dateStr) {
  // event date(YYYY-MM-DD or ISO) 이후 첫 라벨 인덱스, 없으면 가장 가까운 마지막 인덱스
  const target = dateStr.slice(0, 10);
  let idx = labels.findIndex(l => l >= target);
  if (idx === -1) idx = labels.length - 1;
  return idx;
}

function withNum(list, color, lane) {
  return list.map((e, i) => ({
    ...e,
    num: i + 1,
    idx: dateIndex(e.date),
    color,
    lane,
    raw: e.date,
  }));
}

const salesEvents = withNum(DATA.sales_milestones, 'var(--c-sales)', 0);
const updateEvents = withNum(DATA.game_updates, 'var(--c-update)', 1);
const paEvents = withNum(DATA.pearl_abyss_events, 'var(--c-pa)', 2);
const events = [...salesEvents, ...updateEvents, ...paEvents];

const verticalLinesPlugin = {
  id: 'verticalLinesPlugin',
  afterDatasetsDraw(chart) {
    const { ctx, chartArea, scales } = chart;
    if (!chartArea) return;
    const xScale = scales.x;
    const laneY = [chartArea.top - 44, chartArea.top - 26, chartArea.top - 8]; // 판매공지 / 업데이트 / 펄어비스 (상단 여백에 배치)
    ctx.save();
    events.forEach(ev => {
      const x = xScale.getPixelForValue(ev.idx);
      if (x < chartArea.left || x > chartArea.right) return;
      const color = getComputedStyle(document.documentElement).getPropertyValue(ev.color.replace('var(', '').replace(')', '')) || ev.color;
      const y = laneY[ev.lane];

      // 세로 점선 (뱃지 아래부터 차트 하단까지)
      ctx.strokeStyle = color;
      ctx.setLineDash([4, 3]);
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, y + 9);
      ctx.lineTo(x, chartArea.bottom);
      ctx.stroke();

      // 번호 뱃지 (원 + 숫자)
      ctx.setLineDash([]);
      ctx.beginPath();
      ctx.arc(x, y, 8, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.fillStyle = '#0d1117';
      ctx.font = 'bold 10px -apple-system,sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(String(ev.num), x, y + 0.5);
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
        label: 'Steam 일 평균 순위',
        data: steamSeries,
        borderColor: '#4a9eff',
        backgroundColor: 'rgba(74,158,255,0.08)',
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.15,
        fill: true,
        spanGaps: true,
        order: 1,
      },
      {
        label: 'PS Store 일 평균 순위',
        data: psSeries,
        borderColor: '#ffa726',
        backgroundColor: 'rgba(255,167,38,0.08)',
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.15,
        fill: true,
        spanGaps: true,
        order: 1,
      },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    layout: { padding: { top: 56 } },
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { labels: { color: '#9aa4b2', font: { size: 11 } } },
      tooltip: {
        callbacks: {
          afterBody(items) {
            const idx = items[0].dataIndex;
            const hit = events.filter(e => e.idx === idx);
            if (!hit.length) return [];
            const laneTag = ['판매', '업데이트', '펄어비스'];
            return ['', '── 일정 ──', ...hit.map(h => `${laneTag[h.lane]}#${h.num} ${h.label}`)];
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
    tbody.innerHTML = rows.map(r => '<tr>' + cols.map(c => {
      if (c === 'num') {
        return '<td class="num"><span class="badge" style="background:' + r.color + '">' + r.num + '</span></td>';
      }
      return '<td class="label">' + (r[c] ?? '') + '</td>';
    }).join('') + '</tr>').join('');
  }

  fillTable('tbl-sales', salesEvents.map(e => ({
    num: e.num,
    color: e.color,
    date: e.date.slice(0, 16).replace('T', ' '),
    day: 'D+' + e.day,
    label: e.label,
  })), ['num', 'date', 'day', 'label']);

  fillTable('tbl-update', updateEvents.map(e => ({
    num: e.num,
    color: e.color,
    date: e.date,
    label: e.label,
  })), ['num', 'date', 'label']);

  fillTable('tbl-pa', paEvents.map(e => ({
    num: e.num,
    color: e.color,
    date: e.date,
    label: e.label,
  })), ['num', 'date', 'label']);
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
