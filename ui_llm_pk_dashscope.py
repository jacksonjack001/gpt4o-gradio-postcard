import gradio as gr
from openai import OpenAI
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import logging
import os
import re
import uuid
import json
from openai_tools import client_dashscope as client
from util_tools.db_tools import init_database, save_to_database, logging

init_database()
os.environ["PYTHONUNBUFFERED"] = "1"  # 在代码开头设置
load_dotenv()


conv_map = {}

# 定义可选的模型列表
MODELS = [
    "qwen2.5-3b-instruct",
    "qwen2.5-0.5b-instruct",
    "qwen2-0.5b-instruct",
    "qwen1.5-0.5b-chat",
]
print(MODELS)


def query_model(question, model_name, session_id):
    """调用单个模型进行回答"""
    logging.info(f"Querying model {model_name} with question: {question[:100]}...")
    res_str = "{}"
    try:
        if model_name.startswith("qwen3"):
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": question}],
                timeout=30,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
        else:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": question}],
                timeout=30,
            )
        logging.info(f"Successfully received response from {model_name}")
        res_json = response.to_dict()
        res_str = json.dumps(res_json, ensure_ascii=False)

        logging.info(res_str)

        if model_name in ["gpt-4o-search-preview", "gpt-4o-mini-search-preview"]:
            text = response.choices[0].message.content
        else:
            text = response.choices[0].message.content

        save_to_database(
            str(session_id), model_name, question, res_str, text, status="success"
        )
        return text
    except TimeoutError:
        logging.error(f"Timeout error for model {model_name}")
        save_to_database(
            session_id, model_name, question, res_str, "", status="timeout"
        )
        return "接口超时，请重试或者联系管理员"
    except Exception as e:
        save_to_database(
            session_id, model_name, question, res_str, str(e), status="fail"
        )
        logging.error(f"Error querying {model_name}: {str(e)}")
        return f"Error with {model_name}: {str(e)}"


async def async_query_model(question, model_name, session_id):
    """异步调用单个模型"""
    with ThreadPoolExecutor() as executor:
        result = await asyncio.get_event_loop().run_in_executor(
            executor, query_model, question, model_name, session_id
        )
        return result


async def multi_model_query(question, model1, model2, model4):

    logging.info(
        f"Starting multi-model query with models: {model1}, {model2}, {model4}"
    )
    """异步查询多个模型"""

    current_conversation_id = uuid.uuid4()

    tasks_dict = {
        asyncio.create_task(
            async_query_model(question, model1, current_conversation_id)
        ): 0,
        asyncio.create_task(
            async_query_model(question, model2, current_conversation_id)
        ): 1,
        asyncio.create_task(
            async_query_model(question, model4, current_conversation_id)
        ): 2,
    }

    results = ["等待响应中..."] * 3
    pending = set(tasks_dict.keys())

    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

        for done_task in done:
            index = tasks_dict[done_task]
            try:
                results[index] = await done_task
                logging.info(f"Received response from model at index {index}")
            except Exception as e:
                logging.error(f"Error in model at index {index}: {str(e)}")
                results[index] = f"Error: {str(e)}"

            if not pending:
                logging.info("All models have responded")
                models = [model1, model2, model4, ""]

            yield tuple(results)


# 创建Gradio界面
# with gr.Blocks() as demo:
def multi_search_pk():
    css_str = """
    .model-container {
        border-right: 2px solid #ddd;
        padding-right: 15px;
        margin-right: 15px;
    }
    .model-output {
        min-height: 300px;
    }
    """

    with gr.Blocks(css=css_str) as demo:
        # gr.Markdown("# 搜索模型竞技场")
        # 初始化数据库
        print("dab")

        # 创建状态变量来跟踪每个模型的可见性
        model1_visible = gr.State(True)
        model2_visible = gr.State(True)
        model3_visible = gr.State(True)

        with gr.Row():
            question = gr.Textbox(label="请输入你的问题:", lines=5)

        with gr.Row():
            model1 = gr.Dropdown(
                choices=MODELS,
                value=MODELS[0],
                label="模型1",
                interactive=True,
            )
            model2 = gr.Dropdown(
                choices=MODELS, value=MODELS[1], label="模型2", interactive=True
            )
            model4 = gr.Dropdown(
                choices=MODELS,
                value=MODELS[2],
                label="模型3",
                interactive=True,
            )

        with gr.Row():
            submit_btn = gr.Button("提交")
            show_all_btn = gr.Button("全部显示")

        # 创建一个函数来更新UI布局
        def update_layout(
            m1_visible, m2_visible, m3_visible, result1, result2, result3
        ):
            outputs = []
            if m1_visible:
                outputs.append(gr.Column(visible=True, scale=1))
            else:
                outputs.append(gr.Column(visible=False, scale=0))

            if m2_visible:
                outputs.append(gr.Column(visible=True, scale=1))
            else:
                outputs.append(gr.Column(visible=False, scale=0))

            if m3_visible:
                outputs.append(gr.Column(visible=True, scale=1))
            else:
                outputs.append(gr.Column(visible=False, scale=0))

            return outputs

        # 创建切换可见性的函数
        def toggle_visibility(visible_state):
            return not visible_state, gr.update(
                value="显示" if not visible_state else "隐藏"
            )

        # 创建显示所有模型的函数
        def show_all_models():
            return (
                True,
                True,
                True,  # 所有模型可见性状态设为True
                gr.update(value="隐藏"),
                gr.update(value="隐藏"),
                gr.update(value="隐藏"),  # 所有按钮文本设为"隐藏"
                gr.update(visible=True, scale=1),
                gr.update(visible=True, scale=1),
                gr.update(visible=True, scale=1),  # 所有列可见且等宽
            )

        # 创建最大化模型的函数
        def maximize_model(model_index):
            if model_index == 1:
                return (
                    True,
                    False,
                    False,  # 只有模型1可见
                    gr.update(value="隐藏"),
                    gr.update(value="显示"),
                    gr.update(value="显示"),
                    gr.update(visible=True, scale=12),
                    gr.update(visible=False, scale=0),
                    gr.update(visible=False, scale=0),
                )
            elif model_index == 2:
                return (
                    False,
                    True,
                    False,  # 只有模型2可见
                    gr.update(value="显示"),
                    gr.update(value="隐藏"),
                    gr.update(value="显示"),
                    gr.update(visible=False, scale=0),
                    gr.update(visible=True, scale=12),
                    gr.update(visible=False, scale=0),
                )
            else:  # model_index == 3
                return (
                    False,
                    False,
                    True,  # 只有模型3可见
                    gr.update(value="显示"),
                    gr.update(value="显示"),
                    gr.update(value="隐藏"),
                    gr.update(visible=False, scale=0),
                    gr.update(visible=False, scale=0),
                    gr.update(visible=True, scale=12),
                )

        # 创建结果行
        with gr.Row() as results_row:
            # 默认消息
            default_message = ""

            # 模型1列
            with gr.Column(elem_classes=["model-container"]) as model1_col:
                with gr.Row():
                    toggle_btn1 = gr.Button("隐藏", size="sm")
                    maximize_btn1 = gr.Button("最大化", size="sm")
                output1 = gr.Markdown(
                    value=default_message, elem_classes=["model-output"]
                )

            # 模型2列
            with gr.Column(elem_classes=["model-container"]) as model2_col:
                with gr.Row():
                    toggle_btn2 = gr.Button("隐藏", size="sm")
                    maximize_btn2 = gr.Button("最大化", size="sm")
                output2 = gr.Markdown(
                    value=default_message, elem_classes=["model-output"]
                )

            # 模型3列
            with gr.Column(elem_classes=["model-container"]) as model3_col:
                with gr.Row():
                    toggle_btn3 = gr.Button("隐藏", size="sm")
                    maximize_btn3 = gr.Button("最大化", size="sm")
                output4 = gr.Markdown(
                    value=default_message, elem_classes=["model-output"]
                )

        # 设置按钮点击事件
        toggle_btn1.click(
            fn=toggle_visibility,
            inputs=[model1_visible],
            outputs=[model1_visible, toggle_btn1],
        ).then(
            fn=lambda m1_vis, m2_vis, m3_vis: [
                gr.update(visible=m1_vis, scale=1 if m1_vis else 0),
                gr.update(
                    visible=m2_vis,
                    scale=(12 / (m1_vis + m2_vis + m3_vis)) if m2_vis else 0,
                ),
                gr.update(
                    visible=m3_vis,
                    scale=(12 / (m1_vis + m2_vis + m3_vis)) if m3_vis else 0,
                ),
            ],
            inputs=[model1_visible, model2_visible, model3_visible],
            outputs=[model1_col, model2_col, model3_col],
        )

        toggle_btn2.click(
            fn=toggle_visibility,
            inputs=[model2_visible],
            outputs=[model2_visible, toggle_btn2],
        ).then(
            fn=lambda m1_vis, m2_vis, m3_vis: [
                gr.update(
                    visible=m1_vis,
                    scale=(12 / (m1_vis + m2_vis + m3_vis)) if m1_vis else 0,
                ),
                gr.update(visible=m2_vis, scale=1 if m2_vis else 0),
                gr.update(
                    visible=m3_vis,
                    scale=(12 / (m1_vis + m2_vis + m3_vis)) if m3_vis else 0,
                ),
            ],
            inputs=[model1_visible, model2_visible, model3_visible],
            outputs=[model1_col, model2_col, model3_col],
        )

        toggle_btn3.click(
            fn=toggle_visibility,
            inputs=[model3_visible],
            outputs=[model3_visible, toggle_btn3],
        ).then(
            fn=lambda m1_vis, m2_vis, m3_vis: [
                gr.update(
                    visible=m1_vis,
                    scale=(12 / (m1_vis + m2_vis + m3_vis)) if m1_vis else 0,
                ),
                gr.update(
                    visible=m2_vis,
                    scale=(12 / (m1_vis + m2_vis + m3_vis)) if m2_vis else 0,
                ),
                gr.update(visible=m3_vis, scale=1 if m3_vis else 0),
            ],
            inputs=[model1_visible, model2_visible, model3_visible],
            outputs=[model1_col, model2_col, model3_col],
        )

        # 设置最大化按钮点击事件
        maximize_btn1.click(
            fn=lambda: maximize_model(1),
            inputs=[],
            outputs=[
                model1_visible,
                model2_visible,
                model3_visible,
                toggle_btn1,
                toggle_btn2,
                toggle_btn3,
                model1_col,
                model2_col,
                model3_col,
            ],
        )

        maximize_btn2.click(
            fn=lambda: maximize_model(2),
            inputs=[],
            outputs=[
                model1_visible,
                model2_visible,
                model3_visible,
                toggle_btn1,
                toggle_btn2,
                toggle_btn3,
                model1_col,
                model2_col,
                model3_col,
            ],
        )

        maximize_btn3.click(
            fn=lambda: maximize_model(3),
            inputs=[],
            outputs=[
                model1_visible,
                model2_visible,
                model3_visible,
                toggle_btn1,
                toggle_btn2,
                toggle_btn3,
                model1_col,
                model2_col,
                model3_col,
            ],
        )

        # 设置"全部显示"按钮点击事件
        show_all_btn.click(
            fn=show_all_models,
            inputs=[],
            outputs=[
                model1_visible,
                model2_visible,
                model3_visible,
                toggle_btn1,
                toggle_btn2,
                toggle_btn3,
                model1_col,
                model2_col,
                model3_col,
            ],
        )

        submit_btn.click(
            fn=multi_model_query,
            inputs=[question, model1, model2, model4],
            outputs=[output1, output2, output4],
            api_name="predict",
        )

        return demo


# 启动应用
if __name__ == "__main__":
    demo = multi_search_pk()
    demo.queue().launch(server_name="0.0.0.0", server_port=8080, share=False)
