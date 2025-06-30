import pymysql
import os
from time import time, sleep
import logging
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

def mysql_is_ready():
    check_timeout = 120  # 최대 대기 시간
    check_interval = 5   # 재시도 간격
    start_time = time()

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())

    host = os.getenv("DATABASE_HOST", "localhost")
    port = int(os.getenv("DATABASE_PORT", 3306))  # 기본 포트는 3306
    user = os.getenv("DATABASE_USER")
    password = os.getenv("DATABASE_PASSWORD")
    db = os.getenv("DATABASE_NAME")

    while time() - start_time < check_timeout:
        try:
            pymysql.connect(host=host, port=port, user=user, password=password, db=db)
            print("Connected to MySQL successfully.")
            return True
        except Exception as e:
            logger.warning(f"⏳ Waiting for MySQL... ({e})")
            sleep(check_interval)

    logger.error(f" Could not connect to {host}:{port} within {check_timeout} seconds.")
    return False

mysql_is_ready()
