@echo off
echo ========================================
echo   Fitness Asistan Uygulamasi Baslatiliyor
echo ========================================
echo.

REM Virtual environment'i aktif et
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment aktif
) else (
    echo [HATA] Virtual environment bulunamadi!
    echo Lutfen once 'python -m venv venv' komutunu calistirin.
    pause
    exit /b 1
)

echo.
echo [1/3] Paketler kontrol ediliyor...
pip install -q -r requirements.txt
if %errorlevel% neq 0 (
    echo [HATA] Paket yukleme basarisiz!
    pause
    exit /b 1
)
echo [OK] Paketler hazir

echo.
echo [2/3] Veritabani kontrol ediliyor...
python manage.py migrate --no-input
if %errorlevel% neq 0 (
    echo [HATA] Migration basarisiz!
    pause
    exit /b 1
)
echo [OK] Veritabani hazir

echo.
echo [2.5/3] Ayarlar kontrol ediliyor...
python test_server.py
echo.
echo [3/3] Sunucu baslatiliyor...
echo.
echo ========================================
echo   Tarayicida ac: http://127.0.0.1:8000
echo   Durdurmak icin: CTRL+C
echo ========================================
echo.

python manage.py runserver
