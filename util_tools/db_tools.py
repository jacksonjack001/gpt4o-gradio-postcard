import sqlite3
import datetime
import os
from config import Config
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s",
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler("logs/ai_tools_1.log"),  # 同时保存到文件
    ],
)
config_base = Config()
sql_lite_db_file = config_base.sql_lite_db_file


# 在文件顶部添加数据库初始化
def init_database():
    """初始化数据库表"""
    db_path = sql_lite_db_file
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS model_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            model_name TEXT NOT NULL,
            question TEXT NOT NULL,
            response TEXT NOT NULL,
            content text not null,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'success'
        )
    """
    )

    conn.commit()
    conn.close()


def save_to_database(
    session_id, model_name, question, response, content, status="success"
):
    """保存模型响应到数据库"""
    try:
        db_path = sql_lite_db_file
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO model_responses (session_id, model_name, question, response,content, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (session_id, model_name, question, response, content, status),
        )

        conn.commit()
        conn.close()
        logging.info(f"Successfully saved response from {model_name} to database")
    except Exception as e:
        logging.error(f"Failed to save to database: {str(e)}")


if __name__ == "__main__":
    # 在模块加载时初始化数据库
    init_database()
