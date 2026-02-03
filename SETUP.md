# GitHub 저장소 설정 가이드

## 1. 저장소 생성
1. GitHub에서 새 저장소 생성
2. 로컬에서 파일들 추가

## 2. 파일 업로드
```bash
git init
git add .
git commit -m "Initial commit: Ranking visualization project"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

## 3. GitHub Actions 권한 설정 (plots 자동 커밋용)
1. GitHub 저장소 → Settings → Actions → General
2. "Workflow permissions" 섹션에서
3. ✅ "Read and write permissions" 선택
4. ✅ "Allow GitHub Actions to create and approve pull requests" 체크
5. Save 버튼 클릭

## 4. 워크플로우 실행
### 자동 실행
- `rank_history__2_.json` 파일을 푸시하면 자동 실행

### 수동 실행
1. 저장소 → Actions 탭
2. "Generate Ranking Plots" 워크플로우 선택
3. "Run workflow" 버튼 클릭

## 5. 결과 확인
### Artifacts로 다운로드
1. Actions 탭 → 완료된 워크플로우 클릭
2. Artifacts 섹션에서 "ranking-plots" 다운로드

### Git 저장소에서 확인
- 자동 커밋이 활성화된 경우 `output/` 폴더 확인

## 6. README 뱃지 추가 (선택사항)
README.md 상단에 다음 추가:
```markdown
![Generate Ranking Plots](https://github.com/<USERNAME>/<REPO>/workflows/Generate%20Ranking%20Plots/badge.svg)
```

## 트러블슈팅

### 그래프가 생성되지 않는 경우
- Actions 탭에서 워크플로우 로그 확인
- `rank_history__2_.json` 파일이 저장소에 있는지 확인

### 자동 커밋이 안 되는 경우
- Workflow permissions 설정 확인
- 변경사항이 있는지 확인 (이미 최신이면 커밋 안 됨)

### 한글이 깨지는 경우
- 현재 스크립트는 DejaVu Sans 폰트 사용 (영문)
- 한글 표시가 필요하면 스크립트에서 폰트 설정 변경 필요
