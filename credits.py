import os
import time
import random
import string
import hashlib
import requests
from datetime import datetime
import logging
from tools import logger
from config import Config

config_base = Config()
# 支付网关配置
GATEWAY = config_base.zpay_gateway
PID = config_base.zpay_pid
KEY = config_base.zpay_key


class CreditsManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def get_user_credits(self, username):
        """获取用户点数"""
        return self.db_manager.get_user_credits(username)

    def check_credits_sufficient(self, username, required_credits=5):
        """检查用户点数是否足够"""
        current_credits = self.get_user_credits(username)
        return current_credits >= required_credits

    def consume_credits(self, username, amount=5, description="生成图片"):
        """消费点数"""
        return self.db_manager.update_user_credits(
            username, -amount, "consume", description
        )

    def refund_credits(self, username, amount=5, description="生成失败退回"):
        """退回点数"""
        return self.db_manager.update_user_credits(
            username, amount, "refund", description
        )

    def add_credits(self, username, amount, description="充值"):
        """添加点数"""
        return self.db_manager.update_user_credits(
            username, amount, "recharge", description
        )

    def create_payment_url(self, username, money, pay_type="alipay", callback_url=None):
        """创建支付链接"""
        # 生成订单号 (时间戳+随机字符)
        out_trade_no = time.strftime("%Y%m%d%H%M%S") + "".join(
            random.choices(string.ascii_letters + string.digits, k=8)
        )

        # 商品名称
        goods_name = f"点数充值 - {money}元"

        # 回调地址
        if callback_url:
            host = callback_url.rstrip("/")
        else:
            host = config_base.pay_callback_host  # Gradio默认地址

        notify_url = f"{host}/notify"
        return_url = f"{host}/add_credits"

        # 网站名称
        web_name = "深度记事插画系统"

        # 构建支付请求
        payment_url = self._build_payment_url(
            money,
            username,
            notify_url,
            out_trade_no,
            pay_type,
            PID,
            return_url,
            web_name,
            KEY,
        )

        # 记录订单信息
        logger.info(f"创建支付订单: {username}, 金额: {money}, 订单号: {out_trade_no}")

        return payment_url, out_trade_no

    def _build_payment_url(
        self,
        money,
        name,
        notify_url,
        out_trade_no,
        pay_type,
        pid,
        return_url,
        web_name,
        key,
    ):
        """构建支付URL"""
        # 对参数进行排序，生成待签名字符串
        sg = f"money={money}&name={name}&notify_url={notify_url}&out_trade_no={out_trade_no}&pid={pid}&return_url={return_url}&sitename={web_name}&type={pay_type}"

        # MD5加密--进行签名
        sign = hashlib.md5((sg + key).encode(encoding="UTF-8")).hexdigest()

        # 构建完整的支付URL
        url = f"{GATEWAY}submit.php?{sg}&sign={sign}&sign_type=MD5"

        return url

    def query_order_status(self, out_trade_no):
        """查询订单状态"""
        url = f"{GATEWAY}api.php?act=order&pid={PID}&key={KEY}&out_trade_no={out_trade_no}"
        try:
            res = requests.get(url).json()
            return res
        except Exception as e:
            logger.error(f"查询订单状态失败: {e}")
            return None

    def handle_payment_success(self, username, money, out_trade_no):
        """处理支付成功"""
        # 计算点数 1元=10点数
        credits_to_add = int(float(money) * 10)

        # 添加点数
        new_credits = self.add_credits(
            username,
            credits_to_add,
            f"充值 {money}元 获得{credits_to_add}点数 订单号:{out_trade_no}",
        )

        logger.info(
            f"支付成功: 用户 {username}, 金额 {money}元, 获得 {credits_to_add}点数, 当前点数 {new_credits}"
        )
        return credits_to_add, new_credits

    def process_payment_success(self, out_trade_no, trade_no, username):
        """处理支付成功逻辑"""
        try:
            # 查询订单信息
            order_info = self.query_order_status(out_trade_no)
            if not order_info or order_info.get("status") != 1:
                logger.warning(f"支付处理失败: 订单 {out_trade_no} 状态无效")
                return {"success": False, "message": "订单状态无效"}

            # 获取订单金额
            money = order_info.get("money", "0")

            # 处理充值
            credits_to_add, new_credits = credits_manager.handle_payment_success(
                username, money, out_trade_no
            )

            logger.info(
                f"手动处理支付成功: 用户 {username}, 订单 {out_trade_no}, 金额 {money}元, 增加 {credits_to_add}点"
            )

            return {
                "success": True,
                "message": f"充值成功！增加{credits_to_add}点数，当前点数: {new_credits}",
            }
        except Exception as e:
            logger.error(f"处理支付失败: {str(e)}")
            return {"success": False, "message": f"处理支付失败: {str(e)}"}


if __name__ == "__main__":
    from login import DatabaseManager

    db = DatabaseManager()
    credit = CreditsManager(db)
    res = credit.query_order_status(out_trade_no="20250510220706R9slEfXQ")
    print(res["status"])
