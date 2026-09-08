# H.265 → H.264 변환기

HEVC(H.265) 영상을 호환성이 높은 H.264(MP4)로 변환하는 Streamlit 웹 앱입니다.

## 로컬 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

ffmpeg가 시스템에 설치되어 있어야 합니다.

## Docker 실행

```bash
docker build -t h265toh264 .
docker run -p 7860:7860 h265toh264
```

브라우저에서 http://localhost:7860 접속.

## Render 배포

1. https://render.com 가입 (GitHub 계정으로 로그인 가능)
2. New → Web Service → 이 GitHub 저장소 선택
3. Render가 `Dockerfile`을 자동 감지 — Runtime을 "Docker"로 두고 그대로 배포
4. main 브랜치에 push할 때마다 자동으로 재배포됨
