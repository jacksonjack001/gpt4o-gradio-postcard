from flask import Flask, render_template, request, redirect
import hashlib
import requests
import time
import random
import string
from config import Config

app = Flask(__name__)

# 支付网关配置

config_base = Config()
# 支付网关配置
GATEWAY = config_base.zpay_gateway
PID = config_base.zpay_pid
KEY = config_base.zpay_key


# 首页 - 显示支付表单
@app.route("/")
def index():
    return render_template("index.html")


# 处理支付请求
@app.route("/pay", methods=["POST"])
def create_payment():
    # 获取表单数据
    money = request.form.get("money", "0.01")
    pay_type = request.form.get("pay_type", "alipay")

    # 生成订单号 (时间戳+随机字符)
    out_trade_no = time.strftime("%Y%m%d%H%M%S") + "".join(
        random.choices(string.ascii_letters + string.digits, k=8)
    )

    # 商品名称
    name = "测试商品"

    # 回调地址 (实际使用时需要修改为您的服务器地址)
    host = request.host_url.rstrip("/")
    notify_url = f"{host}/notify"
    return_url = f"{host}"

    # 网站名称
    web_name = "测试网站"

    # 构建支付请求
    payment_url = pay(
        money, name, notify_url, out_trade_no, pay_type, PID, return_url, web_name, KEY
    )

    # 重定向到支付网关
    return redirect(payment_url)


# 支付成功回调
@app.route("/return")
def return_url():
    # 处理支付成功后的跳转
    return render_template("success.html")


# 支付异步通知
@app.route("/notify", methods=["POST"])
def notify_url():
    # 处理支付平台的异步通知
    # 实际应用中需要验证签名并更新订单状态
    return "success"


# 发起支付请求
def pay(
    money, name, notify_url, out_trade_no, pay_type, pid, return_url, web_name, key
):
    # 对参数进行排序，生成待签名字符串
    sg = f"money={money}&name={name}&notify_url={notify_url}&out_trade_no={out_trade_no}&pid={pid}&return_url={return_url}&sitename={web_name}&type={pay_type}"

    # MD5加密--进行签名
    sign = hashlib.md5((sg + key).encode(encoding="UTF-8")).hexdigest()

    # 构建完整的支付URL
    url = f"{GATEWAY}submit.php?{sg}&sign={sign}&sign_type=MD5"

    return url


# 查询订单状态
@app.route("/query/<out_trade_no>")
def query_order(out_trade_no):
    url = f"{GATEWAY}api.php?act=order&pid={PID}&key={KEY}&out_trade_no={out_trade_no}"
    res = requests.get(url).json()
    return res


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
