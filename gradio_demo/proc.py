# main_app.py
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware  # 用于会话
import gradio as gr


# --- 你的 Gradio App ---
def greet_user(name, request: gr.Request):
    # 尝试从 FastAPI 的会话中获取用户信息
    # 注意：直接访问 FastAPI session 可能需要一些技巧或自定义 gr.Request
    # 更常见的是在 FastAPI 端点中处理，然后传递给 Gradio
    session_data = getattr(
        request, "session", {}
    )  # FastAPI session 通常在 request.session
    username = session_data.get("username")
    if username:
        return f"Hello {name}! You are logged in as {username}."
    else:
        return f"Hello {name}! You are not logged in."


io = gr.Interface(fn=greet_user, inputs="text", outputs="text")
gradio_app = gr.routes.App.create_app(io)  # 获取 Gradio 的 FastAPI app 实例

# --- FastAPI 主应用 ---
app = FastAPI()

# 添加会话中间件 (需要 secret_key)
app.add_middleware(SessionMiddleware, secret_key="super-secret-key")


@app.get("/login_page", response_class=HTMLResponse)
async def login_page():
    # 返回一个登录表单
    return """
    <html><body>
        <form action="/login" method="post">
            Username: <input type="text" name="username"><br>
            Password: <input type="password" name="password"><br>
            <input type="submit" value="Login">
        </form>
    </body></html>
    """


@app.post("/login")
async def login_submit(request: Request):
    form_data = await request.form()
    username = form_data.get("username")
    password = form_data.get("password")
    # 简单的认证逻辑
    if username == "testuser" and password == "testpass":
        request.session["username"] = username  # 在 FastAPI 会话中设置登录状态
        return {"message": "Login successful, go to /gradio_interface"}
    return {"message": "Login failed"}


@app.get("/logout")
async def logout(request: Request):
    request.session.pop("username", None)
    return {"message": "Logged out"}


# 挂载 Gradio 应用
# 注意：需要确保 Gradio 内部的请求也能访问到 FastAPI 的 session
# 这可能需要对 Gradio 的请求处理或 FastAPI 的中间件做一些调整
# 或者，在调用 Gradio 函数前，从 FastAPI 的 request 中提取信息，然后作为参数传入
app.mount("/gradio_interface", gradio_app)


# 假设你有一个方法可以在 FastAPI 端点中预先获取会话信息
# 然后用这些信息初始化 Gradio 界面或 State
def get_current_username(request: Request):
    return request.session.get("username")


def create_gradio_interface_for_user(username: str = Depends(get_current_username)):
    # 这个函数会在每次请求时被调用，并基于当前用户创建或配置 Gradio 界面
    # 这里的挑战是如何动态地将 username 注入到 Gradio 的处理函数中
    # 一种可能是通过 gr.State 在 Gradio 界面加载时设置
    if not username:
        return HTMLResponse("Please login first <a href='/login_page'>Login</a>")

    # 这里可以动态创建或配置 Gradio 界面
    # 例如，将 username 传递给 Gradio 的函数
    def my_gradio_func(text_input):
        return f"Hello {text_input}, from {username} (FastAPI Session)"

    io_dynamic = gr.Interface(fn=my_gradio_func, inputs="text", outputs="text")
    # 此处返回的是Gradio的FastAPI应用，需要挂载
    return gr.routes.App.create_app(io_dynamic)


# 实际应用中，你可能需要更复杂的挂载逻辑
# 或者修改 Gradio 函数使其能接受 FastAPI Request 对象，或者通过其他方式传递会话信息

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
    # 启动会比较复杂，因为 Gradio 自己也想启动服务器
    # 通常做法是： FastAPI 运行，Gradio 作为其中一个 app 被挂载
    # 在上面的 app.mount("/gradio_interface", gradio_app) 就是这样
    # 那么你只需要运行 FastAPI: uvicorn main_app:app --reload
    print("Run with: uvicorn main_app:app --reload")
    print("Access login at: http://localhost:8000/login_page")
    print("Access Gradio at: http://localhost:8000/gradio_interface (after login)")
