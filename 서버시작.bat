@echo off
chcp 65001 > nul
title H.265 → H.264 변환기 서버

echo.
echo ======================================
echo   H.265 to H.264 변환기 서버 시작
echo ======================================
echo.

:: Streamlit 설치 확인
pip show streamlit > nul 2>&1
if errorlevel 1 (
    echo [설치 중] streamlit 설치 중입니다. 잠시 기다려주세요...
    pip install streamlit
    echo.
)

echo [안내] 브라우저에서 아래 주소로 접속하세요:
echo.
echo   내 PC:       http://localhost:8501
echo   같은 망 PC:  http://[이 PC의 IP주소]:8501
echo.
echo [안내] 서버를 끄려면 이 창을 닫으세요.
echo.

streamlit run app.py --server.port 8501

pause
