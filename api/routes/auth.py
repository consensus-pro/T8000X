from flask import Blueprint, request, jsonify, session, render_template, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from psycopg2.extras import RealDictCursor
from ..utils import get_db, generate_code, is_code_valid, is_valid_email, is_allowed_email
import time
import re

auth_bp = Blueprint('auth', __name__)
verification_codes = {}
code_send_cooldown = {}

@auth_bp.route("/")
def index():
    if session.get("username"):
        return render_template("index.html")
    return redirect("/login")

@auth_bp.route("/register")
def register_page():
    return render_template("register.html")

@auth_bp.route("/login")
def login_page():
    return render_template("login.html")

@auth_bp.route("/api/send-code", methods=["POST"])
def send_code():
    data = request.get_json()
    email_raw = data.get("email")
    if not email_raw:
        return jsonify({"success": False, "error": "请输入邮箱"}), 400

    email = email_raw.lower().strip()
    if not is_valid_email(email):
        return jsonify({"success": False, "error": "邮箱格式错误"}), 400

    try:
        if not is_allowed_email(email):
            return jsonify({"success": False, "error": "请使用正规邮箱注册"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": "检测器加载失败"}), 500

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE LOWER(email) = %s", (email,))
    existing = cur.fetchone()
    if existing:
        return jsonify({"success": False, "error": "该邮箱已被注册"}), 400

    last_send = code_send_cooldown.get(email, 0)
    if time.time() - last_send < 60:
        remaining = int(60 - (time.time() - last_send))
        return jsonify({"success": False, "error": f"请等待 {remaining} 秒后再试"}), 429

    code = generate_code()
    expires = time.time() + 5 * 60
    verification_codes[email] = {"code": code, "expires": expires}
    code_send_cooldown[email] = time.time()

    try:
        import resend
        resend.Emails.send(
            params={
                "from": "T8000X网络 <noreply@t8000x.top>",
                "to": email,
                "subject": "注册验证码",
                "html": f"<p>您的验证码是：<strong>{code}</strong>，有效期5分钟。</p>"
            }
        )
        return jsonify({"success": True, "message": "验证码已发送"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@auth_bp.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    email_raw = data.get("email")
    code = data.get("code")

    if not all([username, password, email_raw, code]):
        return jsonify({"success": False, "error": "请填写所有内容"}), 400

    email = email_raw.lower().strip()
    if not is_valid_email(email):
        return jsonify({"success": False, "error": "邮箱格式错误"}), 400

    if not is_code_valid(verification_codes, email, code):
        return jsonify({"success": False, "error": "验证码过期或错误"}), 400

    try:
        if not is_allowed_email(email):
            return jsonify({"success": False, "error": "请使用正规邮箱注册"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": "检测器加载失败"}), 500

    if not re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9]+$', username):
        return jsonify({"success": False, "error": "用户名只能包含中文、字母、数字"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
    existing = cur.fetchone()
    if existing:
        return jsonify({"success": False, "error": "账号已存在"}), 400

    password_hash = generate_password_hash(password)
    try:
        cur.execute(
            "INSERT INTO users (username, password_hash, email, created_at) VALUES (%s, %s, %s, NOW())",
            (username, password_hash, email)
        )
        conn.commit()
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO user_stats (user_id, total_points, checkin_days) VALUES (%s, 0, 0)",
            (user_id,)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        if "email" in str(e):
            return jsonify({"success": False, "error": "该邮箱已被注册"}), 400
        else:
            return jsonify({"success": False, "error": "注册失败，请重试"}), 400

    verification_codes.pop(email, None)
    return jsonify({"success": True, "message": "注册成功"})

@auth_bp.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"success": False, "error": "账号或密码未填"}), 400

    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cur.fetchone()

    if not user:
        return jsonify({"success": False, "error": "账号或密码错误"}), 401

    if not check_password_hash(user["password_hash"], password):
        return jsonify({"success": False, "error": "账号或密码错误"}), 401

    session["username"] = username
    return jsonify({"success": True, "message": "登录成功"})

@auth_bp.route("/api/logout", methods=["POST"])
def logout():
    session.pop("username", None)
    session.pop("admin", None)
    return jsonify({"success": True, "message": "已退出登录"})