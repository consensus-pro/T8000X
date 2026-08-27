from flask import Blueprint, request, jsonify
from psycopg2.extras import RealDictCursor
from ..utils import get_db_connection
import os
import time
import requests
from datetime import datetime, timezone, timedelta

ai_bp = Blueprint('ai', __name__)

JISHI_USERNAME = "纪失"

AI_API_KEY = os.environ.get("API_KEY")
AI_SYSTEM_PROMPT = os.environ.get("SYSTEM_PROMPT")
AI_MODEL = "deepseek-chat"
AI_TIMEOUT = 60
AI_MAX_HISTORY = 10

# 全局最后调用时间锁
_last_ai_call_time = 0

def ai_get_history(username, limit=AI_MAX_HISTORY):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT role, content FROM ai_conversations WHERE username = %s ORDER BY created_at DESC LIMIT %s",
        (username, limit)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return list(reversed(rows))

def ai_save_conversation(username, role, content):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO ai_conversations (username, role, content) VALUES (%s, %s, %s)",
        (username, role, content)
    )
    conn.commit()
    cur.close()
    conn.close()

def ai_clean_old_history(username, keep=AI_MAX_HISTORY):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM ai_conversations WHERE username = %s AND id NOT IN (SELECT id FROM ai_conversations WHERE username = %s ORDER BY created_at DESC LIMIT %s)",
        (username, username, keep)
    )
    conn.commit()
    cur.close()
    conn.close()

def ai_call_deepseek(messages):
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": AI_MODEL,
        "messages": messages,
        "stream": False,
        "max_tokens": 7500,
        "temperature": 0.7
    }
    try:
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=AI_TIMEOUT
        )
        if resp.status_code == 200:
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        else:
            return f"API错误: {resp.status_code}"
    except requests.exceptions.Timeout:
        return "请求超时，请稍后再试。"
    except Exception as e:
        return f"请求异常: {str(e)}"

def ai_handle_request(username, question):
    if username == JISHI_USERNAME:
        return None
    if not AI_API_KEY:
        return "API密钥未配置"
    if not AI_SYSTEM_PROMPT:
        return "系统提示词未配置"
    history = ai_get_history(username)
    messages = [{"role": "system", "content": AI_SYSTEM_PROMPT}]
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    current_time = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    user_msg = f"当前用户：{username}\n当前时间：{current_time}\n问题：{question}"
    messages.append({"role": "user", "content": user_msg})
    reply = ai_call_deepseek(messages)
    if not reply.startswith("API错误") and not reply.startswith("请求超时") and not reply.startswith("请求异常"):
        ai_save_conversation(username, "user", question)
        ai_save_conversation(username, "assistant", reply)
        ai_clean_old_history(username, AI_MAX_HISTORY)
    return reply

@ai_bp.route("/api/ai-ask", methods=["POST"])
def ai_ask():
    global _last_ai_call_time
    now = time.time()
    if now - _last_ai_call_time < 3:
        return jsonify({"success": False, "error": "AI 正在思考中，请稍后再试"}), 429
    _last_ai_call_time = now

    data = request.get_json()
    username = data.get("username")
    question = data.get("question")
    if not username or not question:
        return jsonify({"success": False, "error": "参数不足"}), 400

    if username == JISHI_USERNAME:
        return jsonify({"success": False, "error": "身份冲突"}), 400

    reply = ai_handle_request(username, question)
    if reply is None:
        return jsonify({"success": False, "error": "请求被忽略"}), 400

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT qq_number FROM users WHERE username = %s", (JISHI_USERNAME,))
    jishi = cur.fetchone()
    jishi_avatar = None
    if jishi and jishi.get("qq_number"):
        jishi_avatar = f"https://q1.qlogo.cn/g?b=qq&nk={jishi['qq_number']}&s=640"

    cur.execute(
        "INSERT INTO messages (username, content) VALUES (%s, %s) RETURNING id",
        (JISHI_USERNAME, reply)
    )
    msg_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()

    try:
        import pusher
        pusher_client = pusher.Pusher(
            app_id=os.environ.get("PUSHER_APP_ID"),
            key=os.environ.get("PUSHER_KEY"),
            secret=os.environ.get("PUSHER_SECRET"),
            cluster=os.environ.get("PUSHER_CLUSTER"),
            ssl=True
        )
        pusher_client.trigger("chat", "new-message", {
            "username": JISHI_USERNAME,
            "content": reply,
            "avatar_url": jishi_avatar
        })
    except Exception as e:
        pass

    return jsonify({"success": True, "message": "AI 回复已发送", "id": msg_id})