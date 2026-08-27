from flask import Blueprint, request, jsonify, session, render_template, redirect
from werkzeug.security import generate_password_hash
from psycopg2.extras import RealDictCursor
from ..utils import get_db
from datetime import timedelta
import time
import os

admin_bp = Blueprint('admin', __name__)
admin_login_attempts = {}

@admin_bp.route("/admin")
def admin_login_page():
    return render_template("admin.html")

@admin_bp.route("/admin/dashboard")
def admin_dashboard_page():
    if not session.get("admin"):
        return redirect("/admin")
    return render_template("admin_dashboard.html")

@admin_bp.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"success": False, "error": "账号和密码必填"}), 400

    now = time.time()
    if username in admin_login_attempts:
        record = admin_login_attempts[username]
        if record.get("permanent_locked"):
            return jsonify({"success": False, "error": "该账号已被永久锁定，请联系管理员"}), 403

    admin_user = os.environ.get("ADMIN_ACCOUNT")
    admin_pass = os.environ.get("ADMIN_PASSWORD")

    if username == admin_user and password == admin_pass:
        admin_login_attempts.pop(username, None)
        session["admin"] = username
        return jsonify({"success": True, "message": "登录成功 账号密码有效"})
    else:
        record = admin_login_attempts.get(username, {"count": 0, "permanent_locked": False})
        record["count"] += 1
        if record["count"] >= 10:
            record["permanent_locked"] = True
            admin_login_attempts[username] = record
            return jsonify({"success": False, "error": "该账号已被永久锁定，请联系管理员"}), 403
        else:
            remaining_attempts = 10 - record["count"]
            admin_login_attempts[username] = record
            return jsonify({"success": False, "error": f"账号或密码错误 你还可再试 {remaining_attempts} 次"}), 401

@admin_bp.route("/api/admin/users", methods=["GET"])
def admin_get_users():
    admin_username = session.get("admin")
    if not admin_username:
        return jsonify({"success": False, "error": "未登录"}), 401

    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id, username, email, created_at FROM users ORDER BY id DESC")
    users = cur.fetchall()

    for user in users:
        if user.get("created_at"):
            user["created_at"] = (user["created_at"] + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    return jsonify({"success": True, "users": users})

@admin_bp.route("/api/admin/users/<int:user_id>", methods=["DELETE"])
def admin_delete_user(user_id):
    admin_username = session.get("admin")
    if not admin_username:
        return jsonify({"success": False, "error": "未登录"}), 401

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
    if not cur.fetchone():
        return jsonify({"success": False, "error": "用户不存在"}), 404

    cur.execute("DELETE FROM user_stats WHERE user_id = %s", (user_id,))
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    return jsonify({"success": True, "message": "用户已删除"})

@admin_bp.route("/api/admin/users/<int:user_id>/reset-password", methods=["POST"])
def admin_reset_password(user_id):
    admin_username = session.get("admin")
    if not admin_username:
        return jsonify({"success": False, "error": "未登录"}), 401

    data = request.get_json()
    new_password = data.get("new_password", "").strip()
    if len(new_password) < 6:
        return jsonify({"success": False, "error": "密码至少6位"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
    if not cur.fetchone():
        return jsonify({"success": False, "error": "用户不存在"}), 404

    password_hash = generate_password_hash(new_password)
    cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user_id))
    conn.commit()
    return jsonify({"success": True, "message": "密码已修改"})

@admin_bp.route("/api/admin/users/<int:user_id>/update-points", methods=["POST"])
def admin_update_points(user_id):
    admin_username = session.get("admin")
    if not admin_username:
        return jsonify({"success": False, "error": "未登录"}), 401

    data = request.get_json()
    points_str = data.get("points")
    if points_str is None:
        return jsonify({"success": False, "error": "积分不能为空"}), 400

    try:
        points = int(points_str)
    except ValueError:
        return jsonify({"success": False, "error": "积分必须是整数"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
    if not cur.fetchone():
        return jsonify({"success": False, "error": "用户不存在"}), 404

    cur.execute("UPDATE user_stats SET total_points = %s WHERE user_id = %s", (points, user_id))
    if cur.rowcount == 0:
        cur.execute("INSERT INTO user_stats (user_id, total_points, checkin_days) VALUES (%s, %s, 0)", (user_id, points))
    conn.commit()
    return jsonify({"success": True, "message": "积分已修改"})

@admin_bp.route("/api/admin/messages", methods=["GET"])
def admin_get_messages():
    admin_username = session.get("admin")
    if not admin_username:
        return jsonify({"success": False, "error": "未登录"}), 401

    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT id, username, content, created_at FROM messages ORDER BY created_at DESC")
    messages = cur.fetchall()

    for msg in messages:
        if msg.get("created_at"):
            msg["created_at"] = (msg["created_at"] + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    return jsonify({"success": True, "messages": messages})

@admin_bp.route("/api/admin/messages/<int:msg_id>", methods=["DELETE"])
def admin_delete_message(msg_id):
    admin_username = session.get("admin")
    if not admin_username:
        return jsonify({"success": False, "error": "未登录"}), 401

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM messages WHERE id = %s", (msg_id,))
    conn.commit()
    return jsonify({"success": True, "message": "消息已删除"})

@admin_bp.route("/api/admin/page-views", methods=["GET"])
def admin_get_page_views():
    admin_username = session.get("admin")
    if not admin_username:
        return jsonify({"success": False, "error": "未登录"}), 401
    from ..utils import get_page_views
    rows = get_page_views()
    total = sum(row[1] for row in rows)
    return jsonify({
        "success": True,
        "total": total,
        "views": [{"path": r[0], "count": r[1], "last_visited": r[2].strftime("%Y-%m-%d %H:%M:%S") if r[2] else None} for r in rows]
    })