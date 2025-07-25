# order/apps.py
from django.apps import AppConfig

class OrderConfig(AppConfig):
    name = 'order'           # 폴더 이름과 같아야 합니다
    verbose_name = '주문'