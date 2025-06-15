from openai import OpenAI
import json
import os
import base64
import os
from datetime import datetime
from tools import logger
from util_tools.py_base import config_base


client = OpenAI(
    api_key=config_base.openai_api_key, base_url=config_base.openai_api_base
)

# 初始化OpenAI客户端
client_dashscope = OpenAI(
    api_key=config_base.openai_api_key_dashscope,
    base_url=config_base.openai_api_base_dashscope,
)


def get_title_description(page_content):
    msg = [
        {
            "role": "system",
            "content": """你是一论文阅读工具，请根据下面的描述提取论文中的相关信息。
        请从论文第一页提取论文标题、论文的主要思想以及主要作者所属机构、公司或者学校(为了脱敏请忽略人名)，输出成json格式，
        并翻译成中文：
        论文的主要思想控制在100字以内。
        ```
        格式如下
       {"title": "", "main_desciption": "", "title_ch": "", "main_desciption_ch": "", "author": ""}
        """,
        },
        {
            "role": "user",
            "content": page_content,
        },
    ]
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=msg,
        max_tokens=6000,
        response_format={"type": "json_object"},
        temperature=0,
    )
    res_cont = response.choices[0].message.content
    print(res_cont)
    res_json = json.loads(res_cont)
    return res_cont, res_json


def get_json_string(page_content):
    msg = [
        {
            "role": "system",
            "content": """帮我提取出文本中的json，注意只需要json部分，不需要其他的说明。
        """,
        },
        {
            "role": "user",
            "content": page_content,
        },
    ]
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=msg,
        response_format={"type": "json_object"},
        temperature=0,
    )
    res_cont = response.choices[0].message.content
    print(res_cont)
    res_json = json.loads(res_cont)
    return res_cont, res_json


def get_gpt_result(page_content):
    msg = [{"role": "user", "content": page_content}]
    response = client.chat.completions.create(
        model="claude-3-5-sonnet-latest",
        messages=msg,
    )
    print(response.to_json())
    res_cont = response.choices[0].message.content
    return res_cont


def translate_to_english(text):
    """将中文文本翻译成英文"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的中英翻译。请将用户输入的中文翻译成英文，保持原意的同时使翻译更加自然流畅。请直接输出翻译后的英文结果，不要附加其他内容！",
                },
                {"role": "user", "content": f"请将以下文本翻译成英文：\n\n{text}"},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"翻译过程中出错: {e}")
        return text


def generate_illustration(
    prompt, n=1, size="1024x1024", model="gpt-image-1", save_path=None
):
    logger.info(f"generate_illustration: {prompt}")
    try:
        response = client.images.generate(model=model, prompt=prompt, n=n, size=size)
        results = []
        for item in response.data:
            # 检查返回的是URL还是base64
            if hasattr(item, "url") and item.url:
                results.append(item.url)
            elif hasattr(item, "b64_json") and item.b64_json:
                # 如果需要保存图片
                if save_path:
                    # 确保目录存在
                    os.makedirs(save_path, exist_ok=True)
                    # 生成唯一文件名
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    file_path = os.path.join(
                        save_path, f"image_{timestamp}_{len(results)}.png"
                    )
                    # 保存base64为图片文件
                    with open(file_path, "wb") as f:
                        f.write(base64.b64decode(item.b64_json))
                    results.append(file_path)
                else:
                    results.append(item.b64_json)
            else:
                # 处理可能的其他返回格式
                logger.warning(f"未知的响应格式: {item}")
                if hasattr(item, "revised_prompt"):
                    logger.info(f"修改后的提示词: {item.revised_prompt}")

        return results
    except Exception as e:
        logger.error(f"插画生成出错: {e}")
        return []


if __name__ == "__main__":
    # 测试保存图片
    prompt = """请生成一张图片，模拟在一张略带纹理的纸张（比如米黄色或浅棕色）上手写的关于景区 杭州-西湖 的讲解笔记。图片应呈现旅行日志/拼贴画风格，包含以下元素：

用手写字体（比如蓝色或棕色墨水）书写景区名称、地理位置、最佳游览季节、以及一两句吸引人的标语或简介。 
包含几个主要看点或特色的介绍，使用编号列表或项目符号（例如：列举2-3个具体看点，如"奇特的岩石形态"，"古老的传说"，"独特的植物"等），并配有简短的手写说明。 
用红色笔迹或其他亮色圈出或用箭头指向特别推荐的地点或活动（例如 列举1-2个推荐项）。 
穿插一些与景区特色相关的简单涂鸦式小图画（例如：根据景区特色想1-2个代表性图画，如山峰轮廓、特色动植物、标志性建筑等）。

点缀几张关于该景区的、看起来像是贴上去的小幅照片（可以是风景照、细节照，风格可以略显复古或像宝丽来照片）。 
整体感觉要像一份由热情导游或资深游客精心制作的、生动有趣的个人导览手记。

语言: 中文，比例: 1*1，生图数量: 4，真实风格，字体置灰"""
    res = generate_illustration(
        prompt,
        model="gpt-image-1",
        save_path="/data_ext/trae_gradio_gpt4o_img/generated_images",
        n=3,
    )
    print(f"生成的图片保存在: {res}")
