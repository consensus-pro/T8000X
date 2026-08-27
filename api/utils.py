import os
import re
import json
import time
import random
import psycopg2
import resend
from flask import g
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

resend.api_key = os.environ.get("RESEND_API_KEY")

# ---------- 自定义异常 ----------
class PoolConnectionError(Exception):
    """连接池连接无效异常"""
    pass

# ---------- 连接池（全局单例） ----------
_db_pool = None

def get_pool():
    global _db_pool
    if _db_pool is None:
        _db_pool = psycopg2.pool.SimpleConnectionPool(
            1, 20,
            host=os.environ.get("DATA_POSTGRES_HOST"),
            database=os.environ.get("DATA_POSTGRES_DATABASE"),
            user=os.environ.get("DATA_POSTGRES_USER"),
            password=os.environ.get("DATA_POSTGRES_PASSWORD"),
            sslmode="require",
            connect_timeout=5
        )
    return _db_pool

def get_db():
    """从池中获取连接，并通过心跳检测确保连接存活"""
    if 'db_conn' not in g:
        conn = get_pool().getconn()
        try:
            # 心跳检测：执行极简查询验证连接是否有效
            with conn.cursor() as cur:
                cur.execute('SELECT 1')
        except Exception:
            # 连接已失效，销毁并抛出异常
            get_pool().putconn(conn, close=True)
            raise PoolConnectionError("数据库连接已失效，请刷新重试")
        g.db_conn = conn
    else:
        # 检查缓存的连接是否依然存活（避免在请求过程中被服务端断开）
        try:
            with g.db_conn.cursor() as cur:
                cur.execute('SELECT 1')
        except Exception:
            # 缓存连接失效，销毁并抛出异常
            get_pool().putconn(g.db_conn, close=True)
            raise PoolConnectionError("数据库连接已失效，请刷新重试")
    return g.db_conn

def return_db_conn():
    """请求结束时归还连接"""
    conn = g.pop('db_conn', None)
    if conn is not None:
        get_pool().putconn(conn)

# ---------- 原有工具函数（完全不变） ----------
def generate_code():
    return str(random.randint(100000, 999999))

def is_code_valid(codes_dict, email, code):
    record = codes_dict.get(email)
    if not record:
        return False
    if record["code"] != code:
        return False
    if time.time() > record["expires"]:
        return False
    return True

def is_valid_email(email):
    return re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email) is not None

def load_allowed_domains():
    try:
        with open(os.path.join(os.path.dirname(__file__), '..', 'TrueEmail.json'), 'r', encoding='utf-8') as f:
            domains = json.load(f)
        return domains
    except FileNotFoundError:
        raise Exception("FILE_NOT_FOUND")
    except json.JSONDecodeError:
        raise Exception("FILE_FORMAT_ERROR")

def is_allowed_email(email):
    domains = load_allowed_domains()
    domain = email.split('@')[-1].lower()
    return domain in domains

def update_page_view(page_path):
    if not page_path or page_path.startswith('/api') or page_path.startswith('/svg') or page_path.startswith('/static') or page_path.startswith('/user'):
        return
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO page_views (page_path, view_count, last_visited)
        VALUES (%s, 1, CURRENT_TIMESTAMP)
        ON CONFLICT (page_path)
        DO UPDATE SET view_count = page_views.view_count + 1, last_visited = CURRENT_TIMESTAMP
    """, (page_path,))
    conn.commit()

def get_page_views():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT page_path, view_count, last_visited FROM page_views ORDER BY view_count DESC")
    rows = cur.fetchall()
    return rows