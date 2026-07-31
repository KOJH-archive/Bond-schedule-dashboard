@echo off
chcp 65001 > nul
echo =========================================================
echo  FICC 채권 수급 및 저축은행 자금동향 파이프라인 시작
echo =========================================================
echo.

echo [1/3] 파이썬 패키지 의존성을 확인 및 설치합니다...
pip install -r requirements.txt
echo.

echo [2/3] API 데이터 추출(ETL) 및 엑셀 저장을 실행합니다...
python main.py
echo.

echo [3/3] Streamlit 대시보드를 실행합니다...
echo (터미널 창을 닫으면 대시보드 서버가 종료됩니다)
echo.
streamlit run app.py
