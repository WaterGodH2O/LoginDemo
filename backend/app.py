import sqlite3
from pathlib import Path

from flask import Flask, g, jsonify, request
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"

app = Flask(__name__)
CORS(
    app,
    resources={r"/api/*": {"origins": ["http://localhost:5173", "http://localhost:5174"]}},
)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
        """
    )
    db.commit()
    db.close()


def read_account():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, (jsonify(message="请求体必须是 JSON"), 400)

    username = data.get("username")
    password = data.get("password")
    if not isinstance(username, str) or not username.strip():
        return None, (jsonify(message="请输入用户名"), 400)
    if not isinstance(password, str) or password == "":
        return None, (jsonify(message="请输入密码"), 400)

    # 用户名只去掉首尾空格。长度是否达到 6 位不在这里检查。
    # 密码按原样保存和比对，暂不加密。
    return {"username": username.strip(), "password": password}, None


@app.get("/api/health")
def health():
    return jsonify(ok=True)


@app.post("/api/register")
def register():
    account, error = read_account()
    if error:
        return error

    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (account["username"], account["password"]),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify(message="用户名已存在"), 409

    return jsonify(message="注册成功"), 201


@app.post("/api/login")
def login():
    account, error = read_account()
    if error:
        return error

    row = get_db().execute(
        "SELECT password FROM users WHERE username = ?",
        (account["username"],),
    ).fetchone()
    if row is None or row["password"] != account["password"]:
        return jsonify(message="用户名或密码错误"), 401

    return jsonify(message="登录成功", username=account["username"])


if __name__ == "__main__":
    init_db()
    app.run(port=5000, debug=True)
