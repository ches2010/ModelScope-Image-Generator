# 敏感配置 & 核心参数（本地/云服务器都在此修改）
# ===================== 必改配置 =====================
MODEL_SCOPE_API_KEY = "your_modelscope_api_key_here"  # 替换为你的API Key
# ===================== 可选配置 =====================
# 1. 图片保存路径（本地：相对路径；云服务器：绝对路径如/root/images/）
IMAGE_SAVE_PATH = "./app/generated_images/"
# 2. ModelScope基础地址（固定不变）
MODEL_SCOPE_BASE_URL = "https://api-inference.modelscope.cn/"
# 3. Flask服务配置（云服务器设为0.0.0.0）
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
# 4. 默认生图参数（新增cfg_scale，默认8，适配多数场景）
DEFAULT_IMAGE_PARAMS = {
    "model": "Qwen/Qwen-Image",
    "negative_prompt": "blurry, low res, deformed, 丑陋, 水印",
    "width": 768,
    "height": 768,
    "num_images": 1,
    "seed": -1,
    "cfg_scale": 8,  # 新增：CFG默认值，1-20之间
    "parameters": {"sampler": "DPM++ 2M Karras", "steps": 30}
}
