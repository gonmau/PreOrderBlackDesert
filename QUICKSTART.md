# 🚀 빠른 시작 가이드

## GitHub에 업로드하기

### 1️⃣ GitHub 저장소 생성
1. GitHub에 로그인
2. 우측 상단 `+` → `New repository`
3. 저장소 이름 입력 (예: `ranking-visualization`)
4. Public/Private 선택
5. `Create repository` 클릭

### 2️⃣ 로컬에서 업로드
```bash
# 다운로드한 파일이 있는 디렉토리로 이동
cd ranking-visualization

# Git 초기화 및 커밋
git init
git add .
git commit -m "Initial commit"

# GitHub 저장소와 연결 (YOUR-USERNAME와 YOUR-REPO를 실제 값으로 변경)
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
git branch -M main
git push -u origin main
```

### 3️⃣ GitHub Actions 활성화

#### 자동 커밋 권한 설정 (선택사항)
그래프를 저장소에 자동으로 커밋하려면:

1. 저장소 페이지 → `Settings`
2. 좌측 메뉴 → `Actions` → `General`
3. "Workflow permissions" 섹션 찾기
4. ✅ `Read and write permissions` 선택
5. ✅ `Allow GitHub Actions to create and approve pull requests` 체크
6. `Save` 클릭

> **참고**: 이 설정을 하지 않으면 그래프는 Artifacts로만 다운로드 가능하고, 저장소에는 자동 커밋되지 않습니다.

### 4️⃣ 데이터 파일 추가
```bash
# rank_history__2_.json 파일을 저장소 루트에 복사
cp /path/to/rank_history__2_.json .

# 커밋 및 푸시
git add rank_history__2_.json
git commit -m "Add ranking data"
git push
```

이제 GitHub Actions가 자동으로 실행되어 그래프를 생성합니다! 🎉

### 5️⃣ 디스코드 알림 설정 (선택사항)

그래프 생성 완료 시 디스코드로 알림을 받으려면:

1. **디스코드 웹훅 생성**
   - 디스코드 채널 설정 → 연동 → 웹훅 → 새 웹훅
   - 웹훅 URL 복사

2. **GitHub Secrets에 등록**
   - 저장소 → Settings → Secrets and variables → Actions
   - New repository secret 클릭
   - Name: `DISCORD_WEBHOOK_URL`
   - Secret: 복사한 웹훅 URL
   - Add secret 클릭

자세한 방법은 **[DISCORD_SETUP.md](DISCORD_SETUP.md)** 참고

---

## 결과 확인하기

### 방법 1: Artifacts 다운로드
1. 저장소 → `Actions` 탭
2. 최신 워크플로우 실행 클릭
3. 아래로 스크롤하여 `Artifacts` 섹션 찾기
4. `ranking-plots` 다운로드 (zip 파일)

### 방법 2: 저장소에서 확인 (자동 커밋 설정한 경우)
1. 저장소 메인 페이지
2. `output/` 폴더 클릭
3. 그래프 이미지 파일들 확인

---

## 수동으로 실행하기

### GitHub에서 수동 실행
1. 저장소 → `Actions` 탭
2. 좌측에서 `Generate Ranking Plots` 워크플로우 선택
3. 우측 상단 `Run workflow` 버튼
4. `Run workflow` 확인

### 로컬에서 실행
```bash
# Python 가상환경 생성 (선택사항)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 스크립트 실행
python plot_rankings.py
```

생성된 그래프는 `output/` 폴더에 저장됩니다.

---

## 자동 실행 스케줄

현재 설정:
- ✅ `rank_history__2_.json` 파일 업데이트 시
- ✅ `plot_rankings.py` 파일 수정 시
- ✅ 6시간마다 자동 실행

### 스케줄 변경하기
`.github/workflows/generate_plots.yml` 파일에서:

```yaml
schedule:
  - cron: '0 */6 * * *'  # 현재: 6시간마다
```

변경 예시:
- 매일 오전 9시: `'0 9 * * *'`
- 12시간마다: `'0 */12 * * *'`
- 매주 월요일 오전 9시: `'0 9 * * 1'`

---

## 문제 해결

### 워크플로우가 실행되지 않아요
- `rank_history__2_.json` 파일이 저장소에 있는지 확인
- Actions 탭에서 워크플로우가 활성화되어 있는지 확인

### 그래프가 생성되지 않아요
- Actions 탭 → 실패한 워크플로우 → 로그 확인
- JSON 파일 형식이 올바른지 확인

### 자동 커밋이 안 돼요
- Workflow permissions 설정 확인 (위의 3️⃣ 참고)
- 이미 최신 상태면 커밋이 생성되지 않음 (정상)

### 한글이 깨져요
- 현재는 영문 폰트 사용 (정상)
- 한글 폰트가 필요하면 스크립트 수정 필요

---

## 다음 단계

✅ **완료했다면:**
- [ ] GitHub 저장소 생성 및 파일 업로드
- [ ] Actions 권한 설정
- [ ] 첫 워크플로우 실행 확인
- [ ] 그래프 다운로드 및 확인
- [ ] 디스코드 알림 설정 (선택)

📚 **더 알아보기:**
- `README.md`: 프로젝트 전체 설명
- `SETUP.md`: 상세 설정 가이드
- `DISCORD_SETUP.md`: 디스코드 알림 설정 가이드
- `.github/workflows/generate_plots.yml`: 워크플로우 설정

---

## 🎯 요약

1. GitHub 저장소 만들기
2. 파일 업로드하기
3. Actions 권한 설정하기
4. 데이터 파일 추가하기
5. 디스코드 알림 설정하기 (선택)
6. 결과 확인하기

**끝!** 이제 자동으로 그래프가 생성되고 디스코드로 알림을 받습니다! 🎉
