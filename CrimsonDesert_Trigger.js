// ═══════════════════════════════════════════════
//  🎮 붉은사막 — GitHub Actions 수동 실행
//  Scriptable용
// ═══════════════════════════════════════════════
//
//  📌 설치 방법:
//  1. 아래 YOUR_PAT_HERE 부분에 GitHub PAT 붙여넣기
//  2. Scriptable 앱에서 새 스크립트로 저장
//  3. 홈 화면 위젯 또는 아이콘으로 추가
//     (When Interacting: Run Script)
//
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

  const res = await req.loadString();
  return req.response.statusCode;
}

// ── 실행 결과 알림 ─────────────────────────────
async function run() {
  let alert = new Alert();
  alert.title = "⚔️ 붉은사막 트래커";

  try {
    const status = await triggerWorkflow();

    if (status === 204) {
      // 성공
      alert.message = "✅ GitHub Actions 실행 시작!\n\n보통 1~2분 후 데이터가 갱신됩니다.";
      alert.addAction("확인");
    } else if (status === 401) {
      alert.message = "❌ 인증 실패\nPAT 토큰을 확인해주세요.";
      alert.addAction("확인");
    } else if (status === 404) {
      alert.message = "❌ 워크플로우를 찾을 수 없습니다.\n파일명을 확인해주세요.";
      alert.addAction("확인");
    } else if (status === 422) {
      alert.message = "❌ 워크플로우에 workflow_dispatch 트리거가 없습니다.";
      alert.addAction("확인");
    } else {
      alert.message = `❌ 오류 발생 (status: ${status})`;
      alert.addAction("확인");
    }
  } catch(e) {
    alert.message = `❌ 네트워크 오류\n${e.message}`;
    alert.addAction("확인");
  }

  await alert.present();
  Script.complete();
}

await run();
