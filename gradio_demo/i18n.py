import gradio as gr

# 定义不同语言的文本
translations = {
    "English": {
        "title": "Simple Calculator",
        "num1_label": "First Number",
        "num2_label": "Second Number",
        "op_label": "Operation",
        "calculate": "Calculate",
        "result": "Result",
    },
    "中文": {
        "title": "简易计算器",
        "num1_label": "第一个数字",
        "num2_label": "第二个数字",
        "op_label": "运算",
        "calculate": "计算",
        "result": "结果",
    },
    "Español": {
        "title": "Calculadora Simple",
        "num1_label": "Primer Número",
        "num2_label": "Segundo Número",
        "op_label": "Operación",
        "calculate": "Calcular",
        "result": "Resultado",
    },
}


def calculate(num1, num2, op):
    if op == "+":
        return num1 + num2
    elif op == "-":
        return num1 - num2
    elif op == "*":
        return num1 * num2
    elif op == "/" and num2 != 0:
        return num1 / num2
    else:
        return "Error"


def change_language(lang):
    return [
        translations[lang]["title"],
        translations[lang]["num1_label"],
        translations[lang]["num2_label"],
        translations[lang]["op_label"],
        translations[lang]["calculate"],
        translations[lang]["result"],
    ]


with gr.Blocks() as demo:
    # 默认语言为英语
    current_lang = "English"

    # 语言选择器
    lang_dropdown = gr.Dropdown(
        choices=list(translations.keys()),
        value=current_lang,
        label="Language/语言/Idioma",
    )

    # 动态文本元素
    title = gr.Markdown(translations[current_lang]["title"])

    with gr.Row():
        num1 = gr.Number(label=translations[current_lang]["num1_label"])
        num2 = gr.Number(label=translations[current_lang]["num2_label"])
        op = gr.Dropdown(
            choices=["+", "-", "*", "/"], label=translations[current_lang]["op_label"]
        )

    calculate_btn = gr.Button(translations[current_lang]["calculate"])
    result = gr.Textbox(label=translations[current_lang]["result"])

    # 计算功能
    calculate_btn.click(fn=calculate, inputs=[num1, num2, op], outputs=result)

    # 语言切换功能
    lang_dropdown.change(
        fn=change_language,
        inputs=lang_dropdown,
        outputs=[title, num1, num2, op, calculate_btn, result],
    )

demo.launch()
