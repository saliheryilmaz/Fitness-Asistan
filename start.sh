#!/bin/bash

echo "========================================"
echo "  Kalori Takip Uygulaması Başlatılıyor"
echo "========================================"
echo ""

# Virtual environment'i aktif et
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
    echo "[OK] Virtual environment aktif"
else
    echo "[HATA] Virtual environment bulunamadı!"
    echo "Lütfen önce 'python -m venv venv' komutunu çalıştırın."
    exit 1
fi

echo ""
echo "[1/3] Paketler kontrol ediliyor..."
pip install -q -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[HATA] Paket yükleme başarısız!"
    exit 1
fi
echo "[OK] Paketler hazır"

echo ""
echo "[2/3] Veritabanı kontrol ediliyor..."
python manage.py migrate --no-input
if [ $? -ne 0 ]; then
    echo "[HATA] Migration başarısız!"
    exit 1
fi
echo "[OK] Veritabanı hazır"

echo ""
echo "[3/3] Sunucu başlatılıyor..."
echo ""
echo "========================================"
echo "  Tarayıcıda aç: http://127.0.0.1:8000"
echo "  Durdurmak için: CTRL+C"
echo "========================================"
echo ""

python manage.py runserver
