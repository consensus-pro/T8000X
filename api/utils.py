import os
import re
import psycopg2
import resend
import random
import time
from psycopg2.extras import RealDictCursor

resend.api_key = os.environ.get("RESEND_API_KEY")

def get_db_connection():
    return psycopg2.connect(
        host=os.environ.get("DATA_POSTGRES_HOST"),
        database=os.environ.get("DATA_POSTGRES_DATABASE"),
        user=os.environ.get("DATA_POSTGRES_USER"),
        password=os.environ.get("DATA_POSTGRES_PASSWORD"),
        sslmode="require",
        connect_timeout=5
    )

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
        import json
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