import os
import sqlite3
import gradio as gr
from datetime import datetime
import logging
from tools import logger


class GalleryManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.images_dir = "generated_images"
        self.init_db()

    def init_db(self):
        """初始化用户图片表"""
        try:
            with sqlite3.connect(self.db_manager.db_name) as conn:
                c = conn.cursor()
                # 用户图片表
                c.execute(
                    """CREATE TABLE IF NOT EXISTS user_images
                            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                             username TEXT,
                             image_path TEXT,
                             prompt TEXT,
                             size TEXT,
                             created_at TEXT,
                             FOREIGN KEY (username) REFERENCES users(username))"""
                )
                conn.commit()
        except Exception as e:
            logger.error(f"数据库初始化错误: {e}")
            raise

    def record_image(self, username, image_path, prompt, size):
        """记录用户生成的图片"""
        try:
            with sqlite3.connect(self.db_manager.db_name) as conn:
                c = conn.cursor()
                now = datetime.now()
                c.execute(
                    """INSERT INTO user_images 
                           (username, image_path, prompt, size, created_at)
                           VALUES (?, ?, ?, ?, ?)""",
                    (username, image_path, prompt, size, now),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"记录图片信息错误: {e}")
            return False

    def get_user_images(self, username):
        """获取用户的所有图片"""
        try:
            with sqlite3.connect(self.db_manager.db_name) as conn:
                c = conn.cursor()
                c.execute(
                    """SELECT id, image_path, prompt, size, created_at 
                           FROM user_images 
                           WHERE username = ?
                           ORDER BY created_at DESC""",
                    (username,),
                )
                return c.fetchall()
        except Exception as e:
            logger.error(f"获取用户图片错误: {e}")
            return []


def create_gallery_tab(app, session_id):
    """创建画廊选项卡UI"""
    gallery_manager = GalleryManager(app.db_manager)

    with gr.Column() as gallery_tab:
        with gr.Row():
            gr.Markdown("## 我的画廊")

        with gr.Row():
            refresh_btn = gr.Button("刷新画廊")

        gallery_status = gr.Markdown("请登录后查看您的画廊")
        gallery_images = gr.Gallery(label="我生成的图片", columns=3, rows=2, height=600)
        image_details = gr.Textbox(label="图片详情", interactive=False)

        def load_gallery(curr_session_id):
            # 验证用户是否已登录
            username = app.require_auth(curr_session_id)
            if not username:
                return "请先登录后查看画廊", None, ""

            # 获取用户图片
            user_images = gallery_manager.get_user_images(username)
            if not user_images:
                return f"您还没有生成过图片", None, ""

            # 准备图片路径列表
            image_paths = [img[1] for img in user_images]

            # 准备图片详情
            details = f"找到 {len(user_images)} 张图片"

            return details, image_paths, ""

        def show_image_details(curr_session_id, evt: gr.SelectData):

            # 添加空值检查
            if evt is None:
                return "事件数据为空"

            # 获取选中的图片索引
            index = evt.index

            # 验证用户是否已登录
            username = app.require_auth(curr_session_id)
            if not username:
                return "请先登录"

            # 获取用户图片
            user_images = gallery_manager.get_user_images(username)
            if not user_images or index >= len(user_images):
                return "无法获取图片详情"

            # 获取选中图片的详情
            image = user_images[index]
            details = f"图片ID: {image[0]}\n生成时间: {image[4]}\n提示词: {image[2]}\n尺寸: {image[3]}"

            return details

        # 绑定事件
        refresh_btn.click(
            load_gallery,
            inputs=[session_id],
            outputs=[gallery_status, gallery_images, image_details],
        )
        gallery_images.select(
            show_image_details, inputs=[session_id], outputs=[image_details]
        )

        # 初始加载
        refresh_btn.click(fn=None)

    return gallery_tab


def record_generated_image(gallery_manager, username, image_path, prompt, size):
    """记录生成的图片到数据库"""
    return gallery_manager.record_image(username, image_path, prompt, size)
