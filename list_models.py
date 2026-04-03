#!/usr/bin/env python
"""Mevcut Gemini modellerini listele"""
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')

print("=" * 60)
print("🔍 Gemini API - Mevcut Modeller")
print("=" * 60)
print()

if not api_key:
    print("❌ GEMINI_API_KEY bulunamadı!")
    exit(1)

print(f"API Key: {'*' * 20}...{api_key[-4:]}")
print()

try:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    
    print("Mevcut modeller:")
    print()
    
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(f"✅ {model.name}")
            print(f"   Display Name: {model.display_name}")
            print(f"   Description: {model.description[:100]}...")
            print()
    
except Exception as e:
    print(f"❌ Hata: {e}")
    print()
    print("Bu API key ile model listesi alınamıyor.")
    print("Muhtemelen API key'in Gemini API erişimi yok.")
    print()
    print("Çözüm:")
    print("1. https://aistudio.google.com/apikey adresine git")
    print("2. Yeni bir API key oluştur")
    print("3. 'Generative Language API' erişimi olduğundan emin ol")

print("=" * 60)
