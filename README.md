# 📊 한국 주식시장 AI 대시보드

매일 오전 8시(KST) Claude AI가 자동으로 최신 시장 데이터를 수집·분석하여 대시보드를 생성합니다.

---

## ⚡ 설정 (딱 4단계)

### 1. 이 레포 Fork
GitHub에서 **Fork** 버튼 클릭

### 2. Anthropic API 키 등록
```
레포 → Settings → Secrets and variables → Actions → New repository secret
Name:  ANTHROPIC_API_KEY
Value: sk-ant-xxxxx (본인 API 키)
```
> API 키 발급: https://console.anthropic.com

### 3. GitHub Pages 활성화
```
레포 → Settings → Pages
Source: Deploy from a branch
Branch: main / (root)
→ Save
```

### 4. 첫 실행 (수동)
```
레포 → Actions → 매일 대시보드 자동 생성 → Run workflow
```

---

## 🌐 URL 확인
Pages 설정 후 약 1~2분 뒤:
```
https://{GitHub유저명}.github.io/{레포이름}/
```

---

## ⏰ 자동 실행 시간
- **평일 오전 8:00 KST** 자동 생성
- Actions 탭에서 수동 실행도 가능

## 💰 비용
- GitHub Actions: **무료** (public 레포 기준)
- Anthropic API: 1회 실행당 약 **$0.03~0.05** (월 ~$1)

## 📁 파일 구조
```
├── index.html                          ← 매일 자동 생성되는 대시보드
├── scripts/
│   └── generate_dashboard.py           ← 생성 스크립트
└── .github/
    └── workflows/
        └── daily_dashboard.yml         ← 스케줄러
```
