# 提示词模板管理类
class PromptTemplates:
    @staticmethod
    def city_scene_template(city, scene, lang, ratio, num, attrs):
        """
        生成城市景点介绍的提示词模板

        参数:
            city: 城市名称
            scene: 景点名称
            lang: 语言（中文/英文）
            ratio: 图片比例
            num: 生成图片数量
            attrs: 其他属性
        """
        template = f"""请生成一张图片，模拟在一张略带纹理的纸张（比如米黄色或浅棕色）上手写的关于景区 {city}-{scene} 的讲解笔记。图片应呈现旅行日志/拼贴画风格，包含以下元素：

用手写字体（比如蓝色或棕色墨水）书写景区名称、地理位置、最佳游览季节、以及一两句吸引人的标语或简介。 
包含几个主要看点或特色的介绍，使用编号列表或项目符号（例如：列举2-3个具体看点，如"奇特的岩石形态"，"古老的传说"，"独特的植物"等），并配有简短的手写说明。 
用红色笔迹或其他亮色圈出或用箭头指向特别推荐的地点或活动（例如 列举1-2个推荐项）。 
穿插一些与景区特色相关的简单涂鸦式小图画（例如：根据景区特色想1-2个代表性图画，如山峰轮廓、特色动植物、标志性建筑等）。

点缀几张关于该景区的、看起来像是贴上去的小幅照片（可以是风景照、细节照，风格可以略显复古或像宝丽来照片）。 
整体感觉要像一份由热情导游或资深游客精心制作的、生动有趣的个人导览手记。

语言: {lang}，比例: {ratio}，生图数量: {num}，{attrs}"""
        return template

    @staticmethod
    def knowledge_template(topic, lang, ratio, num, attrs):
        """
        生成知识学习小报的提示词模板

        参数:
            topic: 主题
            lang: 语言（中文/英文）
            ratio: 图片比例
            num: 生成图片数量
            attrs: 其他属性
        """
        template = f"""Create concise, visually structured notes on the topic '{topic}'. Notes must fit clearly within a layout ({ratio}), featuring: 
- Moderate Font Size: Comfortable readability. 
- Clear Structure: 
  - Main points highlighted with "background colors" or "wavy underlines~". 
  - Regular notes in standard ink. 
  - Emphasis notes in a different ink color. 
- Illustrations: 
  - Include relevant sketches or hand-drawn style illustrations. 
  - Allow fountain pen-style doodles or annotations directly on illustrations. 
- Annotations: 
  - Simulate notes, corrections, and additional quirky doodles resembling spontaneous annotations, using marker pen style. 
  - Incorporate collage-style photo extracts relevant to the topic, annotated or doodled upon. 
User Settings: 
- Topic: {topic}
- Orientation: Vertical 
- Language: {lang} 
- Color Scheme: highlight style. 
- Illustration Style: Detailed hand-drawn
- {attrs}"""
        return template


prompt_default = PromptTemplates.city_scene_template(
    city="杭州",
    scene="西湖",
    lang="中文",
    ratio="1:1",
    num=4,
    attrs="真实风格，字体置灰",
)


# 生成提示词按钮事件
def create_prompt(city, scene, topic, custom, lang, ratio, num, attrs, template_type):
    if template_type == "city_scene":
        return PromptTemplates.city_scene_template(city, scene, lang, ratio, num, attrs)
    elif template_type == "knowledge":
        return PromptTemplates.knowledge_template(topic, lang, ratio, num, attrs)
    elif template_type == "custom":
        return custom
    return "请先选择一个模板"
