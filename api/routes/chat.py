from flask import Blueprint, request, jsonify, session, render_template, redirect
from psycopg2.extras import RealDictCursor
from ..utils import get_db_connection
import html
import pusher
import os
import base64
import requests
from werkzeug.utils import secure_filename
import oss2
import uuid
from datetime import datetime

chat_bp = Blueprint('chat', __name__)

pusher_client = pusher.Pusher(
    app_id=os.environ.get("PUSHER_APP_ID"),
    key=os.environ.get("PUSHER_KEY"),
    secret=os.environ.get("PUSHER_SECRET"),
    cluster=os.environ.get("PUSHER_CLUSTER"),
    ssl=True
)

@chat_bp.route("/chat")
def chat_page():
    return redirect("/")

@chat_bp.route("/api/messages", methods=["GET"])
def get_messages():
    username = session.get("username")
    if not username:
        return jsonify({"success": False, "error": "未登录"}), 401

    limit = request.args.get("limit", default=50, type=int)
    offset = request.args.get("offset", default=0, type=int)
    if limit > 100:
        limit = 100
    if limit < 1:
        limit = 1
    if offset < 0:
        offset = 0

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT m.username, m.content, m.created_at, u.qq_number
        FROM messages m
        LEFT JOIN users u ON m.username = u.username
        ORDER BY m.created_at DESC
        LIMIT %s OFFSET %s
    """, (limit, offset))
    messages = cur.fetchall()
    messages.reverse()
    cur.close()
    conn.close()

    for msg in messages:
        if msg.get("qq_number"):
            msg["avatar_url"] = f"https://q1.qlogo.cn/g?b=qq&nk={msg['qq_number']}&s=640"
        else:
            msg["avatar_url"] = None
    return jsonify({"success": True, "messages": messages})

@chat_bp.route("/api/send-message", methods=["POST"])
def send_message():
    username = session.get("username")
    if not username:
        return jsonify({"success": False, "error": "未登录"}), 401

    data = request.get_json()
    content = data.get("content", "").strip()
    if not content:
        return jsonify({"success": False, "error": "消息不能为空"}), 400
    if len(content) > 500:
        return jsonify({"success": False, "error": "消息太长"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users 
        SET last_message_time = NOW() 
        WHERE username = %s 
          AND (last_message_time IS NULL OR last_message_time < NOW() - INTERVAL '1 second')
    """, (username,))
    if cur.rowcount == 0:
        cur.close()
        conn.close()
        return jsonify({"success": False, "error": "发送过于频繁"}), 429
    conn.commit()
    cur.close()
    conn.close()

    content = html.escape(content)
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT qq_number FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    if not user:
        cur.close()
        conn.close()
        session.pop("username", None)
        return jsonify({"success": False, "error": "用户不存在，请重新登录"}), 401

    avatar_url = None
    if user.get("qq_number"):
        avatar_url = f"https://q1.qlogo.cn/g?b=qq&nk={user['qq_number']}&s=640"

    cur.execute(
        "INSERT INTO messages (username, content) VALUES (%s, %s) RETURNING id",
        (username, content)
    )
    inserted_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()

    try:
        pusher_client.trigger("chat", "new-message", {
            "username": username,
            "content": content,
            "avatar_url": avatar_url
        })
    except Exception as e:
        pass

    return jsonify({"success": True, "message": "发送成功", "id": inserted_id})

@chat_bp.route("/api/pusher/config", methods=["GET"])
def pusher_config():
    return jsonify({
        "success": True,
        "key": os.environ.get("PUSHER_KEY", ""),
        "cluster": os.environ.get("PUSHER_CLUSTER", "ap1")
    })

@chat_bp.route("/api/upload-image", methods=["POST"])
def upload_image():
    username = session.get("username")
    if not username:
        return jsonify({"success": False, "error": "未登录"}), 401

    if 'image' not in request.files:
        return jsonify({"success": False, "error": "未选择图片"}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({"success": False, "error": "文件名为空"}), 400

    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > 7.5 * 1024 * 1024:
        return jsonify({"success": False, "error": "图片不能超过7.5MB"}), 400

    access_key_id = os.environ.get("ALIYUN_OSS_ID")
    access_key_secret = os.environ.get("ALIYUN_OSS_SECRET")
    bucket_name = "t6cc"
    endpoint = "oss-cn-hongkong.aliyuncs.com"

    if not access_key_id or not access_key_secret:
        return jsonify({"success": False, "error": "OSS密钥未配置"}), 500

    try:
        auth = oss2.Auth(access_key_id, access_key_secret)
        bucket = oss2.Bucket(auth, endpoint, bucket_name)

        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
        if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg']:
            ext = 'jpg'
        filename = f"chat/{datetime.now().strftime('%Y/%m/%d')}/{uuid.uuid4().hex}.{ext}"

        file_bytes = file.read()
        result = bucket.put_object(filename, file_bytes, headers={
            'Content-Type': file.content_type or f'image/{ext}'
        })

        if result.status != 200:
            return jsonify({
                "success": False,
                "error": f"OSS上传失败，状态码: {result.status}",
                "detail": f"响应头: {result.headers}"
            }), 500

        image_url = f"https://{bucket_name}.{endpoint}/{filename}"

        img_markdown = f"![图片]({image_url})"

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE users 
            SET last_message_time = NOW() 
            WHERE username = %s 
              AND (last_message_time IS NULL OR last_message_time < NOW() - INTERVAL '1 second')
        """, (username,))
        if cur.rowcount == 0:
            cur.close()
            conn.close()
            return jsonify({"success": False, "error": "发送过于频繁"}), 429
        conn.commit()
        cur.close()
        conn.close()

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT qq_number FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        if not user:
            cur.close()
            conn.close()
            session.pop("username", None)
            return jsonify({"success": False, "error": "用户不存在"}), 401

        avatar_url = None
        if user.get("qq_number"):
            avatar_url = f"https://q1.qlogo.cn/g?b=qq&nk={user['qq_number']}&s=640"

        cur.execute(
            "INSERT INTO messages (username, content) VALUES (%s, %s) RETURNING id",
            (username, img_markdown)
        )
        msg_id = cur.fetchone()["id"]
        conn.commit()
        cur.close()
        conn.close()

        try:
            pusher_client.trigger("chat", "new-message", {
                "username": username,
                "content": img_markdown,
                "avatar_url": avatar_url
            })
        except Exception as e:
            pass

        return jsonify({"success": True, "message": "图片已发送", "id": msg_id})

    except oss2.exceptions.OssError as e:
        return jsonify({
            "success": False,
            "error": "OSS服务错误",
            "detail": f"错误代码: {e.code}, 消息: {e.message}, 请求ID: {e.request_id}"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "上传失败",
            "detail": str(e)
        }), 500