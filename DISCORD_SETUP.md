# 🔔 디스코드 알림 설정 가이드

GitHub Actions에서 그래프 생성이 완료되면 자동으로 디스코드 채널에 알림을 보냅니다.

## 📋 목차
1. [디스코드 웹훅 URL 생성](#1-디스코드-웹훅-url-생성)
2. [GitHub Secrets에 웹훅 URL 등록](#2-github-secrets에-웹훅-url-등록)
3. [알림 내용](#3-알림-내용)
4. [테스트하기](#4-테스트하기)

---

## 1. 디스코드 웹훅 URL 생성

### 1️⃣ 디스코드 서버 설정 열기
1. 디스코드 서버에서 알림을 받을 채널 선택
2. 채널 이름 옆의 ⚙️ (설정) 아이콘 클릭

### 2️⃣ 웹훅 생성
1. 좌측 메뉴에서 **"연동"** (Integrations) 클릭
2. **"웹훅"** (Webhooks) 섹션에서 **"새 웹훅"** 클릭
3. 웹훅 이름 설정 (예: "Ranking Bot")
4. 원하는 경우 아바타 이미지 설정
5. **"웹훅 URL 복사"** 버튼 클릭

⚠️ **중요**: 이 URL은 비밀번호와 같으니 절대 공개하지 마세요!

예시 URL 형식:
```
https://discord.com/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz
```

---

## 2. GitHub Secrets에 웹훅 URL 등록

### 1️⃣ GitHub 저장소 설정으로 이동
1. GitHub 저장소 페이지 접속
2. 상단 메뉴에서 **"Settings"** 클릭

### 2️⃣ Secrets 추가
1. 좌측 메뉴에서 **"Secrets and variables"** → **"Actions"** 클릭
2. **"New repository secret"** 버튼 클릭
3. Secret 정보 입력:
   - **Name**: `DISCORD_WEBHOOK_URL`
   - **Secret**: 앞서 복사한 디스코드 웹훅 URL 붙여넣기
4. **"Add secret"** 버튼 클릭

✅ 완료! 이제 GitHub Actions에서 디스코드 웹훅을 사용할 수 있습니다.

---

## 3. 알림 내용

디스코드 알림에는 다음 정보가 포함됩니다:

### 📊 기본 정보
- **Date Range**: 데이터 기간
- **Countries**: 분석된 국가 수
- **Total Graphs**: 생성된 그래프 파일 수

### 🔥 순위 변화
- **Top Ranking Changes**: 최근 순위 변화가 큰 상위 5개 국가
  - 국가명
  - 현재 순위
  - 변화량

### 예시 알림 메시지
```
📊 Ranking Graphs Generated!
새로운 순위 그래프가 생성되었습니다.

📅 Date Range
2026-01-12 to 2026-02-03

🌍 Countries: 49
📈 Total Graphs: 51 files

🔥 Top Ranking Changes (Standard)
**한국**: Rank 3 (±5)
**일본**: Rank 8 (±4)
**미국**: Rank 15 (±3)
```

---

## 4. 테스트하기

### 로컬에서 테스트
```bash
# 웹훅 URL을 환경 변수로 설정
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"

# 스크립트 실행
python plot_rankings.py
```

디스코드 채널에 알림이 오는지 확인하세요!

### GitHub Actions에서 테스트
1. 저장소에 작은 변경사항 커밋 (예: README 수정)
   ```bash
   git commit --allow-empty -m "Test Discord notification"
   git push
   ```
2. **Actions** 탭에서 워크플로우 실행 확인
3. 디스코드 채널에서 알림 확인

---

## 🔧 커스터마이징

알림 내용을 변경하고 싶다면 `plot_rankings.py`의 `send_discord_notification()` 함수를 수정하세요.

### 알림 색상 변경
```python
"color": 5814783,  # 파란색
# 빨간색: 15158332
# 초록색: 3066993
# 노란색: 16776960
# 보라색: 10181046
```

### 추가 정보 포함
```python
embed["fields"].append({
    "name": "📌 Custom Info",
    "value": "Your custom text here",
    "inline": False
})
```

### 그래프 이미지 첨부 (선택사항)
Discord Webhooks는 embeds에 이미지를 첨부할 수 있지만, 
이미지를 업로드하려면 파일을 전송해야 합니다.

---

## ❓ 문제 해결

### 알림이 오지 않아요
- [ ] `DISCORD_WEBHOOK_URL`이 GitHub Secrets에 정확히 등록되었는지 확인
- [ ] 웹훅 URL이 올바른지 확인 (discord.com/api/webhooks/로 시작)
- [ ] Actions 로그에서 에러 메시지 확인
- [ ] 디스코드 채널에 봇이 메시지를 보낼 권한이 있는지 확인

### 일부 정보만 표시돼요
- 정상입니다! 데이터가 부족하면 일부 정보는 생략됩니다.

### 웹훅이 삭제되었어요
- 디스코드에서 새 웹훅을 생성하고 GitHub Secrets를 업데이트하세요.

---

## 🎯 체크리스트

설정 완료 확인:
- [ ] 디스코드 웹훅 URL 생성
- [ ] GitHub Secrets에 `DISCORD_WEBHOOK_URL` 등록
- [ ] 테스트 알림 전송 성공
- [ ] 알림 내용이 정상적으로 표시됨

완료되었다면 이제 자동으로 알림을 받을 수 있습니다! 🎉

---

## 💡 팁

### 여러 채널에 알림 보내기
각 채널마다 다른 웹훅을 생성하고, 스크립트에서 여러 웹훅으로 전송하도록 수정하세요.

### 조건부 알림
특정 조건에서만 알림을 보내고 싶다면:
```python
# 예: 순위 변화가 5 이상인 경우만 알림
if max(change for _, change, _ in top_changes) >= 5:
    send_discord_notification(webhook_url, country_data, dates)
```

### 멘션 추가
특정 역할이나 사용자를 멘션하려면:
```python
payload = {
    "content": "<@&ROLE_ID> 새로운 그래프가 생성되었습니다!",
    "embeds": [embed]
}
```

역할 ID는 디스코드에서 역할을 우클릭 → "역할 ID 복사"로 확인할 수 있습니다.
(개발자 모드가 활성화되어 있어야 합니다)
