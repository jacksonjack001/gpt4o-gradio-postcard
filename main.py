import gradio as gr
from login import AuthenticatedApp
from openai_tools import generate_illustration
from prompt_templates import PromptTemplates, prompt_default
from tools import logger
from credits import CreditsManager
import uvicorn
from fastapi.responses import RedirectResponse
from fastapi import FastAPI, Request as FastAPIRequest
from fastapi.responses import HTMLResponse, RedirectResponse
from ui_llm_pk_dashscope import multi_search_pk
from prompt_templates import create_prompt
from gallery import create_gallery_tab, GalleryManager, record_generated_image
from config import Config

config_base = Config()
fastapi_app = FastAPI()
app = AuthenticatedApp()
templates = PromptTemplates()
credits_manager = CreditsManager(app.db_manager)


def create_gradio_interface():

    with gr.Blocks(theme=gr.themes.Soft()) as demo:
        session_id = gr.State("")
        current_template = gr.State("city_scene")  # 新增：记录当前模板类型
        current_username = gr.State("")  # 新增：记录当前用户名
        gr.Markdown("# 深度记事-AI定制明信片")

        with gr.Tab("账户"):
            with gr.Row():
                with gr.Column(scale=1):
                    with gr.Group():
                        gr.Markdown("#### 账户信息")
                        username_input = gr.Textbox(label="用户名", value=111)
                        password_input = gr.Textbox(
                            label="密码", type="password", value=111
                        )
                        with gr.Row():
                            register_btn = gr.Button("注册", scale=1)
                            login_btn = gr.Button("登录", scale=1)
                            logout_btn = gr.Button("登出", scale=1)
                        account_status = gr.Textbox(label="状态", interactive=False)
                        user_credits = gr.Textbox(
                            label="我的点数", value="未登录", interactive=False
                        )
                with gr.Column(scale=1):
                    with gr.Group():
                        gr.Markdown("#### 点数充值")
                        gr.Markdown("1元 = 10点数，生成1张图片消耗5点数")
                        recharge_amount = gr.Number(
                            label="充值金额(元)", value=1, precision=2, step=0.5
                        )
                        pay_type = gr.Dropdown(
                            ["支付宝(alipay)", "微信支付(wxpay)", "QQ钱包(qqpay)"],
                            label="支付方式",
                            value="支付宝(alipay)",
                        )
                        recharge_btn = gr.Button("充值点数", variant="primary")
                        payment_result = gr.Textbox(label="充值结果")
                        payment_frame = gr.HTML(visible=False)

            def handle_register(username, password):
                result = app.register(username, password)
                if result["success"]:
                    current_credits = credits_manager.get_user_credits(username)
                    return (
                        result["message"],
                        result["session_id"],
                        username,
                        f"{current_credits} 点",
                    )
                return result["message"], "", "", "未登录"

            def handle_login(username, password):
                result = app.login(username, password)
                if result["success"]:
                    current_credits = credits_manager.get_user_credits(username)
                    return (
                        result["message"],
                        result["session_id"],
                        username,
                        f"{current_credits} 点",
                    )
                return result["message"], "", "", "未登录"

            def handle_logout(curr_session_id):
                result = app.logout(curr_session_id)
                return result["message"], "", "未登录"

            # 新增：处理充值函数
            def handle_recharge(amount, payment_method, curr_username):
                if not curr_username:
                    return "请先登录后再充值", gr.update(visible=False)

                if amount <= 0:
                    return "充值金额必须大于0", gr.update(visible=False)

                # 提取支付方式的值(如：支付宝(alipay) -> alipay)
                pay_type_value = payment_method.split("(")[1].rstrip(")")

                # 创建支付链接
                host_url = (
                    config_base.pay_callback_host  # Gradio默认地址，实际应用中可能需要修改
                )
                payment_url, out_trade_no = credits_manager.create_payment_url(
                    curr_username, amount, pay_type_value, host_url
                )

                # 返回支付iframe
                # iframe_html = f'<iframe src="{payment_url}" style="width:100%;height:600px;border:none;"></iframe>'
                iframe_html = f'<iframe src="{payment_url}" style="width:100%;height:600px;border:none;" onload="this.onload=function(){{}}"></iframe>'

                return f"正在跳转到支付页面，订单号: {out_trade_no}", gr.update(
                    visible=True, value=iframe_html
                )

            register_btn.click(
                handle_register,
                inputs=[username_input, password_input],
                outputs=[account_status, session_id, current_username, user_credits],
            )

            login_btn.click(
                handle_login,
                inputs=[username_input, password_input],
                outputs=[account_status, session_id, current_username, user_credits],
            )

            logout_btn.click(
                handle_logout,
                inputs=[session_id],
                outputs=[account_status, current_username, user_credits],
            )

            # 绑定充值按钮事件
            recharge_btn.click(
                handle_recharge,
                inputs=[recharge_amount, pay_type, username_input],
                outputs=[payment_result, payment_frame],
            )

        # 添加深度记事插画生成选项卡
        with gr.Tab("深度记事-明信片插画生成"):
            with gr.Row():
                with gr.Column(scale=1):
                    # 左侧功能按钮区
                    with gr.Group():
                        city_scene_btn = gr.Button("城市景点介绍", variant="secondary")
                    with gr.Group():
                        knowledge_btn = gr.Button("知识学习小报", variant="secondary")
                    with gr.Group():
                        custom_template_btn = gr.Button(
                            "新增提示词词模版", variant="secondary"
                        )

                    # 添加空行分隔
                    gr.Markdown("&nbsp;")
                    gr.Markdown("&nbsp;")
                    gr.Markdown("&nbsp;")

                    with gr.Group():
                        generate_prompt_btn = gr.Button("生成提示词", variant="primary")
                    with gr.Group():
                        generate_image_btn = gr.Button("一键生图", variant="primary")

                with gr.Column(scale=1):
                    # 中间参数设置区
                    with gr.Group(visible=True) as city_scene_group:
                        gr.Markdown("### 城市景点介绍")
                        city_input = gr.Textbox(label="城市", value="杭州")
                        scene_input = gr.Textbox(label="景区", value="西湖")

                    with gr.Group(visible=False) as knowledge_group:
                        gr.Markdown("### 知识学习小报")
                        topic_input = gr.Textbox(label="主题", value="AI强化学习")

                    with gr.Group(visible=False) as custom_template_group:
                        gr.Markdown("### 自定义提示词")
                        custom_prompt = gr.Textbox(label="自定义提示词", lines=15)

                with gr.Column(scale=1):
                    with gr.Group() as params_group:
                        gr.Markdown("### 通用参数")
                        language = gr.Dropdown(
                            ["中文", "英文"], label="语言", value="中文"
                        )
                        ratio = gr.Dropdown(
                            ["1*1", "3*2", "2*3"], label="比例", value="2*3"
                        )
                        num_images = gr.Dropdown(
                            ["1", "2", "4"], label="生图数量", value="4"
                        )
                        other_attrs = gr.Textbox(
                            label="其他属性", value="真实风格，字体置灰"
                        )

                # 提示词和图像输出区
                with gr.Column(scale=1):
                    prompt_output = gr.Textbox(
                        label="生成的提示词/输出结果", lines=15, value=prompt_default
                    )
            image_output = gr.Gallery(label="生成的图像", columns=2, height=600)

            # 模板切换函数
            def show_city_scene():
                return (
                    gr.update(visible=True),
                    gr.update(visible=False),
                    gr.update(visible=False),
                )

            def show_knowledge():
                return (
                    gr.update(visible=False),
                    gr.update(visible=True),
                    gr.update(visible=False),
                )

            def show_custom_template():
                return (
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=True),
                )

            # 生成图像函数
            def generate_images(prompt, num, ratio, curr_session_id):
                # 验证用户是否已登录
                username = app.require_auth(curr_session_id)
                logger.info(
                    f"生图请求 - 用户: {username}, session_id: {curr_session_id}, prompt: {prompt}, num: {num}, ratio: {ratio}"
                )
                if not username:
                    logger.warning("生图请求失败：未登录")
                    return "请先登录后再生成图像", None

                # 计算需要消耗的点数
                required_credits = int(num) * 5  # 每张图5点

                # 检查点数是否足够
                if not credits_manager.check_credits_sufficient(
                    username, required_credits
                ):
                    current_credits = credits_manager.get_user_credits(username)
                    logger.warning(
                        f"生图请求失败：点数不足 - 用户: {username}, 当前点数: {current_credits}, 需要点数: {required_credits}"
                    )
                    return (
                        f"点数不够，请充值！当前点数: {current_credits}，需要: {required_credits}",
                        None,
                    )

                try:
                    # 设置图像尺寸
                    # '1024x1024', '1024x1536', '1536x1024'
                    if ratio == "1*1":
                        size = "1024x1024"
                    elif ratio == "3*2":
                        size = "1536x1024"
                    elif ratio == "2*3":
                        size = "1024x1536"
                    else:
                        size = "1024x1024"

                    # 先扣除点数
                    credits_manager.consume_credits(
                        username, required_credits, f"生成{num}张图片 - {ratio}"
                    )

                    # 调用OpenAI API生成图像
                    image_urls = generate_illustration(
                        prompt=prompt,
                        n=int(num),
                        size=size,
                        save_path="/data_ext/trae_gradio_gpt4o_img/generated_images",
                    )

                    logger.info(
                        f"生图输出 - 用户: {username}, 返回图片数量: {len(image_urls) if image_urls else 0}"
                    )

                    if not image_urls:
                        # 生成失败，退回点数
                        credits_manager.refund_credits(
                            username, required_credits, "生成失败退回点数"
                        )
                        logger.error("图像生成失败，API未返回图片，已退回点数")
                        return "图像生成失败，请检查API设置或重试。已退回点数。", None

                    # 记录生成的图片到数据库
                    gallery_manager = GalleryManager(app.db_manager)
                    for img_path in image_urls:
                        record_generated_image(
                            gallery_manager, username, img_path, prompt, size
                        )

                    # 获取当前点数
                    current_credits = credits_manager.get_user_credits(username)
                    return (
                        f"图像生成成功，消耗{required_credits}点数，当前剩余: {current_credits}点",
                        image_urls,
                    )

                except Exception as e:
                    # 发生错误，退回点数
                    credits_manager.refund_credits(
                        username, required_credits, f"生成错误退回点数: {str(e)}"
                    )
                    logger.exception(f"生成图像时出错: {str(e)}，已退回点数")
                    return f"生成图像时出错: {str(e)}。已退回点数。", None

            # 按钮事件绑定
            city_scene_btn.click(
                show_city_scene,
                inputs=[],
                outputs=[city_scene_group, knowledge_group, custom_template_group],
            ).then(
                lambda: "city_scene", None, current_template  # 更新模板状态
            )

            knowledge_btn.click(
                show_knowledge,
                inputs=[],
                outputs=[city_scene_group, knowledge_group, custom_template_group],
            ).then(lambda: "knowledge", None, current_template)

            custom_template_btn.click(
                show_custom_template,
                inputs=[],
                outputs=[city_scene_group, knowledge_group, custom_template_group],
            ).then(lambda: "custom", None, current_template)

            generate_prompt_btn.click(
                create_prompt,
                inputs=[
                    city_input,
                    scene_input,
                    topic_input,
                    custom_prompt,
                    language,
                    ratio,
                    num_images,
                    other_attrs,
                    current_template,
                ],
                outputs=[prompt_output],
            )

            # 生成图像按钮事件
            generate_image_btn.click(
                generate_images,
                inputs=[prompt_output, num_images, ratio, session_id],
                outputs=[prompt_output, image_output],
            )

        # 添加深度记事插画生成选项卡
        with gr.Tab("我的画廊"):
            create_gallery_tab(app, session_id)
        with gr.Tab("基于小模型的提示词生成工具"):
            multi_search_pk()

    return demo


@fastapi_app.get("/notify")
async def add_notify(request: FastAPIRequest):
    redirect_url = f"/"
    return RedirectResponse(url=redirect_url)


@fastapi_app.get("/add_credits")
async def add_credits(request: FastAPIRequest):
    # 1. 获取所有支付参数
    params = request.query_params
    out_trade_no = params.get("out_trade_no", "")
    trade_no = params.get("trade_no", "")
    username = params.get("name", "")
    money = params.get("money", "")
    trade_status = params.get("trade_status", "FAIL")
    order_status = credits_manager.query_order_status(out_trade_no=out_trade_no)

    # 2. 调用充值处理逻辑
    result_msg = "充值失败，请重试！"
    if (
        out_trade_no
        and trade_no
        and username
        and trade_status == "TRADE_SUCCESS"
        and order_status
    ):
        credits_to_add, new_credits = credits_manager.handle_payment_success(
            username, money, out_trade_no
        )
        result_msg = f"充值成功！已添加 {credits_to_add} 积分，当前积分余额：{new_credits}；即将跳转回主页，请重新登录！"

    # 3. 返回带有弹窗和跳转的HTML
    redirect_url = "/"
    html_content = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>支付结果</title>
            <script>
                alert("{result_msg}");
                window.location.href = "{redirect_url}";
            </script>
        </head>
        <body>
            <p>正在跳转回主页...请重新登录</p>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":

    gradio_app_instance = create_gradio_interface()
    fastapi_app = gr.mount_gradio_app(fastapi_app, gradio_app_instance, path="/")
    logger.info("Starting Gradio app with FastAPI server on http://localhost:7890")
    # Run with Uvicorn
    uvicorn.run(fastapi_app, host="0.0.0.0", port=7890)
