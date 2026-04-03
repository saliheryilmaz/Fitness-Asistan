import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-this-in-production')
DEBUG = os.getenv('DEBUG', 'True') == 'True'

# ALLOWED_HOSTS yapılandırması
ALLOWED_HOSTS_ENV = os.getenv('ALLOWED_HOSTS', '*')
if ALLOWED_HOSTS_ENV == '*':
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_ENV.split(',') if host.strip()]

# Eğer boşsa, güvenli varsayılanlar ekle
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tracker.apps.TrackerConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'kalori_takip.urls'

WSGI_APPLICATION = 'kalori_takip.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('DB_NAME', BASE_DIR / 'db.sqlite3'),
        'USER': os.getenv('DB_USER', ''),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', ''),
        'PORT': os.getenv('DB_PORT', ''),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        } if os.getenv('DB_ENGINE') == 'django.db.backends.mysql' else {},
    }
}

# SQLite için NAME düzeltmesi
if DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
    DATABASES['default']['NAME'] = BASE_DIR / 'db.sqlite3'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
]

LANGUAGE_CODE = 'tr-tr'
TIME_ZONE = 'Europe/Istanbul'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CSRF ayarları (local development için)
if DEBUG:
    CSRF_TRUSTED_ORIGINS = [
        'http://localhost:8000',
        'http://127.0.0.1:8000',
        'http://localhost',
        'http://127.0.0.1',
    ]
    # CSRF cookie ayarları
    CSRF_COOKIE_SECURE = False
    CSRF_COOKIE_HTTPONLY = False
    SESSION_COOKIE_SECURE = False

LOGIN_URL = '/giris/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/giris/'

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
# Google Fit
GOOGLE_FIT_CLIENT_ID = os.getenv('GOOGLE_FIT_CLIENT_ID', '')
GOOGLE_FIT_CLIENT_SECRET = os.getenv('GOOGLE_FIT_CLIENT_SECRET', '')
GOOGLE_FIT_REDIRECT_URI = 'https://caloria.pythonanywhere.com/google-fit/callback/'
import os; os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
CALORIENINJAS_API_KEY = os.getenv('CALORIENINJAS_API_KEY', '')
