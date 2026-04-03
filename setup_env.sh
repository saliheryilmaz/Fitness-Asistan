#!/bin/bash
# PythonAnywhere .env dosyası oluşturma scripti

cat > .env << 'EOF'
SECRET_KEY=pythonanywhere-super-secret-key-buraya-rastgele-uzun-bir-sey-yaz-123456789
DEBUG=False
ALLOWED_HOSTS=kalori.pythonanywhere.com

# SQLite kullanıyoruz (MySQL ayarları yok!)

# Gemini API Key
GEMINI_API_KEY=AIzaSyBdAdudvatXWEIxj3jWcYowCk_CQhvYUDk
EOF

echo "✅ .env dosyası oluşturuldu!"
echo "📝 İçeriği kontrol et: cat .env"
