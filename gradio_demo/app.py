# app.py
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.wsgi import WSGIMiddleware
from starlette.middleware.sessions import SessionMiddleware
import gradio as gr
from itsdangerous import URLSafeSerializer

SECRET_KEY = "a_very_secret_key"
serializer = URLSafeSerializer(SECRET_KEY, salt="login-salt")

app = FastAPI()
# 如果想用 SessionMiddleware 也可以，这里用 itsdangerous 直发签名 token
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)


# 1) 登录接口：校验账户密码，发 token/cookie
@app.post("/login")
async def login(request: Request):
    data = await request.json()
    username = data.get("username", "")
    password = data.get("password", "")
    # TODO: 换成你自己的用户验证逻辑
    if username == "alice" and password == "a1b2c3":
        token = serializer.dumps({"user": username})
        resp = Response(content="ok")
        # httponly: 前端 JS 读不到；你也可以设置 max_age, path, secure...
        resp.set_cookie("token", token, httponly=True)
        return resp
    raise HTTPException(status_code=401, detail="用户名或密码错误")


# 2) 全局中间件：检查 Cookie token
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # 如果访问 /login，就放行
    if request.url.path == "/login":
        return await call_next(request)

    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="请先登录")
    try:
        data = serializer.loads(token)
        request.state.user = data["user"]
    except Exception:
        raise HTTPException(status_code=401, detail="无效的登录态")
    return await call_next(request)


# 3) 准备你的 Gradio 接口
def predict(text):
    return f"[{request.state.user}] 你发的：{text}"


gradio_app = gr.Interface(fn=predict, inputs="text", outputs="text")
# 把 Gradio 的 WSGI App 挂到 FastAPI
app.mount("/gradio", WSGIMiddleware(gradio_app.app))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
