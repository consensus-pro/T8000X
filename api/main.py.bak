from . import create_app
from flask import send_from_directory
import os

app = create_app()

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

if __name__ == "__main__":
    app.run(debug=True)