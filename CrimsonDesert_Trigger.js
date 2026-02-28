// ═══════════════════════════════════════════════
//  🎮 붉은사막 — GitHub Actions 수동 실행
//  Scriptable용 (단축어/Siri 호환)
// ═══════════════════════════════════════════════

// ── 설정 ──────────────────────────────────────
const GITHUB_TOKEN = "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"; // ← 여기에 PAT 붙여넣기
const OWNER        = "gonmau";
const REPO         = "PreOrderBlackDesert";
const WORKFLOW     = "combined_tracker.yml";
const BRANCH       = "main";

// ── API 호출 ───────────────────────────────────
async function triggerWorkflow() {
  const url = `https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW}/dispatches`;
  const req = new Request(url);
  req.method = "POST";
  req.headers = {
    "Authorization": `Bearer ${GITHUB_TOKEN}`,
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "Content-Type": "application/json",
  };
  req.body = JSON.stringify({ ref: BRANCH });
  await req.loadString();
  return req.response.statusCode;
}

// ── 푸시 알림으로 결과 전달 ────────────────────
async function notify(title, body) {
  const n = new Notification();
  n.title = title;
  n.body = body;
  n.sound = "default";
  await n.schedule();
}

// ── 메인 ──────────────────────────────────────
async function run() {
  try {
    const status = await triggerWorkflow();

    if (status === 204) {
      await notify("⚔️ 붉은사막 트래커", "✅ 액션 실행 시작! 1~2분 후 데이터가 갱신됩니다.");
    } else if (status === 401) {
      await notify("⚔️ 붉은사막 트래커", "❌ 인증 실패 — PAT 토큰을 확인해주세요.");
    } else if (status === 404) {
      await notify("⚔️ 붉은사막 트래커", "❌ 워크플로우를 찾을 수 없습니다.");
    } else if (status === 422) {
      await notify("⚔️ 붉은사막 트래커", "❌ workflow_dispatch 트리거가 없습니다.");
    } else {
      await notify("⚔️ 붉은사막 트래커", `❌ 오류 발생 (status: ${status})`);
    }
  } catch(e) {
    await notify("⚔️ 붉은사막 트래커", `❌ 네트워크 오류: ${e.message}`);
  }

  Script.complete();
}

await run();
