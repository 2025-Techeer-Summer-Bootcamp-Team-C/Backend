from pathlib import Path
import pymysql
from datetime import timedelta
from dotenv import load_dotenv
from kombu import Queue
from datetime import timedelta

pymysql.install_as_MySQLdb()
load_dotenv()


import os
api_key = os.environ.get("OPENAI_API_KEY")


BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "insecure-key")

AUTH_USER_MODEL = 'user.User'  

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    'rest_framework',
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    'drf_yasg',
    'user',
    'django_celery_results',
    'django_celery_beat',
    'storages',
    'fitting',
    'product',
    'category',
    'django_prometheus',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:8000",
    "https://techeerfashion.shop",
    "https://api.techeerfashion.shop",
]
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://techeerfashion.shop",
    "https://api.techeerfashion.shop",
]
CORS_ALLOW_HEADERS = [
    'authorization',
    'x-password',
    'content-type',
    'x-csrftoken',
    'accept',
    'origin',
    'user-agent',
]
CORS_ALLOW_METHODS = [
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'OPTIONS',
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

SIMPLE_JWT = {
    # 🔑 JWT 설정
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),   # ✅ access 토큰 1일
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),  # 보통 7일~14일 정도

    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),

    # 🍪 쿠키 관련 커스텀 설정 (이미 있는 값 유지 + 필요시 추가)
    "AUTH_COOKIE_ACCESS": "access",      # access 토큰을 담는 쿠키 이름
    "AUTH_COOKIE_REFRESH": "refresh",    # refresh 토큰을 담는 쿠키 이름
    "AUTH_COOKIE_SAMESITE": "Lax",       
    "AUTH_COOKIE_SECURE": False,         # 운영에서는 True 권장 (HTTPS일 때)
    "AUTH_COOKIE_HTTP_ONLY": True,       # JS 접근 방지용
    "AUTH_COOKIE_PATH": "/",
    "AUTH_COOKIE_DOMAIN": None,          # 필요하면 도메인 명시
    "AUTH_COOKIE_ACCESS_MAX_AGE": 60 * 60 * 24,  # ✅ access 쿠키 유지 1일
    "AUTH_COOKIE_REFRESH_MAX_AGE": 60 * 60 * 24 * 7,  # refresh 쿠키 유지 7일
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "user.authentication.CookieJWTAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

if os.getenv('ENVIRONMENT') == 'prod':
    default_api_url = 'https://techeerfashion.shop/api/v1'
else:
    default_api_url = 'http://localhost:8000/api/v1'

SWAGGER_SETTINGS = {
    'DEFAULT_API_URL': default_api_url,
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'JWT 토큰을 입력하세요. 예: "Bearer {토큰}"',
        }
    },
    'USE_SESSION_AUTH': False,
    'FETCH_WITH_CREDENTIALS': True,
}



SOCIALACCOUNT_STORE_TOKENS = True


LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "static"

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"



# Celery 설정 추가
CELERY_BROKER_URL = 'amqp://guest:guest@rabbitmq:5672/'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Seoul'

CELERY_TASK_TIME_LIMIT = 30 * 60

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
# Celery task를 종료 가능하게 해주는 세팅 (굉장히 중요)
CELERY_TASK_REVOKE = True

CELERYD_HIJACK_ROOT_LOGGER = False
CELERYD_REDIRECT_STDOUTS = False

CELERY_FLOWER_USER = 'root'  # Flower 웹 인터페이스 사용자 이름
CELERY_FLOWER_PASSWORD = 'root'  # Flower 웹 인터페이스 비밀번호

# CELERY_RESULT_BACKEND = 'rpc://'
CELERY_RESULT_BACKEND = "django-db"

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = None

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_S3_CUSTOM_DOMAIN = os.getenv('AWS_S3_CUSTOM_DOMAIN')

DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}

AWS_DEFAULT_ACL = None

MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'

if os.getenv('ENVIRONMENT') == 'prod':
    # HTTPS 인식 설정
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
else:
    SECURE_PROXY_SSL_HEADER = None
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
