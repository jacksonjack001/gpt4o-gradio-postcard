import sqlite3
from datetime import datetime, timedelta
import logging
from uuid import uuid4
import hashlib
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="logs/app.log",
)
logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_name="data/users2.db"):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        try:
            with sqlite3.connect(self.db_name) as conn:
                c = conn.cursor()
                # 用户表
                c.execute(
                    """CREATE TABLE IF NOT EXISTS users
                            (username TEXT PRIMARY KEY,
                             password_hash TEXT,
                             created_at TEXT,
                             last_login TEXT,
                             credits INTEGER DEFAULT 100)"""
                )
                # 会话表
                c.execute(
                    """CREATE TABLE IF NOT EXISTS sessions
                            (session_id TEXT PRIMARY KEY,
                             username TEXT,
                             expires TEXT,
                             FOREIGN KEY (username) REFERENCES users(username))"""
                )

                # 点数交易记录表
                c.execute(
                    """CREATE TABLE IF NOT EXISTS credits_transactions
                            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                             username TEXT,
                             amount INTEGER,
                             transaction_type TEXT,
                             description TEXT,
                             created_at TEXT,
                             FOREIGN KEY (username) REFERENCES users(username))"""
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise

    def save_user(self, username, password_hash):
        try:
            with sqlite3.connect(self.db_name) as conn:
                c = conn.cursor()
                now = datetime.now()
                c.execute(
                    """INSERT INTO users 
                           (username, password_hash, created_at, last_login)
                           VALUES (?, ?, ?, ?)""",
                    (username, password_hash, now, now),
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            logger.error(f"Error saving user: {e}")
            return False

    def verify_user(self, username, password_hash):
        try:
            with sqlite3.connect(self.db_name) as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT password_hash FROM users WHERE username = ?", (username,)
                )
                result = c.fetchone()
                if result and result[0] == password_hash:
                    self.update_last_login(username)
                    return True
                return False
        except Exception as e:
            logger.error(f"Error verifying user: {e}")
            return False

    def update_last_login(self, username):
        try:
            with sqlite3.connect(self.db_name) as conn:
                c = conn.cursor()
                c.execute(
                    "UPDATE users SET last_login = ? WHERE username = ?",
                    (datetime.now(), username),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error updating last login: {e}")
            raise

    def get_user_credits(self, username):
        """获取用户点数"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                c = conn.cursor()
                c.execute("SELECT credits FROM users WHERE username = ?", (username,))
                result = c.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting user credits: {e}")
            return 0

    def update_user_credits(self, username, amount, transaction_type, description):
        """更新用户点数"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                c = conn.cursor()
                # 获取当前点数
                c.execute("SELECT credits FROM users WHERE username = ?", (username,))
                current_credits = c.fetchone()[0]

                # 计算新的点数
                new_credits = current_credits + amount

                # 更新用户点数
                c.execute(
                    "UPDATE users SET credits = ? WHERE username = ?",
                    (new_credits, username),
                )

                # 记录交易
                now = datetime.now()
                c.execute(
                    """INSERT INTO credits_transactions 
                           (username, amount, transaction_type, description, created_at)
                           VALUES (?, ?, ?, ?, ?)""",
                    (username, amount, transaction_type, description, now),
                )

                conn.commit()
                return new_credits
        except Exception as e:
            logger.error(f"Error updating user credits: {e}")
            return None


class SessionManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.session_duration = timedelta(hours=24)

    def create_session(self, username):
        try:
            session_id = str(uuid4())
            expires = datetime.now() + self.session_duration

            with sqlite3.connect(self.db_manager.db_name) as conn:
                c = conn.cursor()
                c.execute(
                    """INSERT INTO sessions (session_id, username, expires)
                           VALUES (?, ?, ?)""",
                    (session_id, username, expires),
                )
                conn.commit()
            return session_id
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise

    def verify_session(self, session_id):
        try:
            with sqlite3.connect(self.db_manager.db_name) as conn:
                c = conn.cursor()
                c.execute(
                    """SELECT username, expires FROM sessions 
                           WHERE session_id = ?""",
                    (session_id,),
                )
                result = c.fetchone()

                if result and datetime.now() < datetime.fromisoformat(result[1]):
                    return result[0]
                return None
        except Exception as e:
            logger.error(f"Error verifying session: {e}")
            return None

    def clear_session(self, session_id):
        try:
            with sqlite3.connect(self.db_manager.db_name) as conn:
                c = conn.cursor()
                c.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"Error clearing session: {e}")
            raise


class AuthenticatedApp:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.session_manager = SessionManager(self.db_manager)
        self.rate_limit = {}
        self.rate_limit_duration = timedelta(minutes=1)
        self.max_attempts = 5

    def hash_password(self, password):
        """使用SHA-256哈希密码"""
        return hashlib.sha256(password.encode()).hexdigest()

    def check_rate_limit(self, username):
        now = datetime.now()
        if username in self.rate_limit:
            attempts, first_attempt = self.rate_limit[username]
            if now - first_attempt > self.rate_limit_duration:
                self.rate_limit[username] = (1, now)
                return True
            if attempts >= self.max_attempts:
                return False
            self.rate_limit[username] = (attempts + 1, first_attempt)
        else:
            self.rate_limit[username] = (1, now)
        return True

    def register(self, username, password):
        try:
            if not username or not password:
                return {"success": False, "message": "用户名和密码不能为空"}

            if not self.check_rate_limit(username):
                return {"success": False, "message": "请求过于频繁，请稍后重试"}

            password_hash = self.hash_password(password)
            if self.db_manager.save_user(username, password_hash):
                session_id = self.session_manager.create_session(username)
                return {
                    "success": True,
                    "session_id": session_id,
                    "username": username,
                    "message": f"注册成功: {username}",
                }
            return {"success": False, "message": "用户名已存在"}
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return {"success": False, "message": "注册过程发生错误"}

    def login(self, username, password):
        try:
            if not username or not password:
                return {"success": False, "message": "用户名和密码不能为空"}

            if not self.check_rate_limit(username):
                return {"success": False, "message": "请求过于频繁，请稍后重试"}

            password_hash = self.hash_password(password)
            if self.db_manager.verify_user(username, password_hash):
                session_id = self.session_manager.create_session(username)
                return {
                    "success": True,
                    "session_id": session_id,
                    "username": username,
                    "message": f"登录成功: {username}",
                }
            return {"success": False, "message": "用户名或密码错误"}
        except Exception as e:
            logger.error(f"Login error: {e}")
            return {"success": False, "message": "登录过程发生错误"}

    def logout(self, session_id):
        try:
            self.session_manager.clear_session(session_id)
            return {"success": True, "message": "已成功登出"}
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return {"success": False, "message": "登出过程发生错误"}

    def require_auth(self, session_id):
        """验证会话并返回用户名"""
        if not session_id:
            return None
        return self.session_manager.verify_session(session_id)

    def protected_function(self, text, session_id):
        """受保护的功能函数"""
        try:
            username = self.require_auth(session_id)
            if not username:
                return {"success": False, "message": "请先登录"}

            return {"success": True, "message": f"用户 {username} 执行操作: {text}"}
        except Exception as e:
            logger.error(f"Protected function error: {e}")
            return {"success": False, "message": "操作执行失败"}

    def get_user_credits(self, session_id):
        """获取用户点数"""
        username = self.require_auth(session_id)
        if not username:
            return {"success": False, "message": "请先登录", "credits": 0}

        credits = self.db_manager.get_user_credits(username)
        return {"success": True, "message": f"当前点数: {credits}", "credits": credits}


# 如果直接运行此文件，则导入ui模块并启动界面
if __name__ == "__main__":
    from ui import create_gradio_interface

    demo = create_gradio_interface()
    demo.launch(server_name="0.0.0.0")
