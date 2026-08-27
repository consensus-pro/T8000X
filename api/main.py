from . import create_app
from flask import send_from_directory, request, jsonify
import os
import traceback
import logging

app = create_app()

# 生产环境强制关闭调试
app.debug = False

@app.route('/svg/<path:filename>')
def serve_svg(filename):
    svg_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'svg')
    return send_from_directory(svg_dir, filename)

@app.route('/api/toast.js')
def serve_toast_js():
    return send_from_directory(os.path.dirname(__file__), 'toast.js')

@app.errorhandler(404)
def not_found(e):
    return send_from_directory(os.path.dirname(__file__), "404.html"), 404

@app.after_request
def after_request(response):
    if response.status_code == 200 and request.method == 'GET':
        from .utils import update_page_view
        update_page_view(request.path)
    return response

# 全局异常处理器，确保所有错误返回 JSON
@app.errorhandler(Exception)
def handle_exception(e):
    error_msg = f"服务器内部错误: {str(e)}"
    logging.error(error_msg)
    logging.error(traceback.format_exc())
    return jsonify({"success": False, "error": error_msg}), 500

if __name__ == "__main__":
    # 即使本地运行也关闭调试，避免敏感信息泄露
    app.run(debug=False)