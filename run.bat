@echo off
chcp 65001 > nul
echo ======================================================================
echo    HỆ THỐNG THI TRẮC NGHIỆM TRỰC TUYẾN (QUIZNET PRO) - BTL MẠNG
echo ======================================================================
echo.
echo Đang khởi động máy chủ FastAPI tại http://127.0.0.1:8000 ...
echo Vui lòng mở trình duyệt và truy cập: http://127.0.0.1:8000
echo.
echo Nhấn Ctrl+C để dừng máy chủ bất cứ lúc nào.
echo ----------------------------------------------------------------------

py -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
pause
