# 敏感配置 & 核心参数
# ===================== 必改配置 =====================
MODEL_SCOPE_API_KEY = "your_modelscope_api_key_here"
# ===================== 可选配置 =====================
IMAGE_SAVE_PATH = "./app/generated_images/"
MODEL_SCOPE_BASE_URL = "https://api-inference.modelscope.cn/"
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 9698
# 默认生图参数（新增：Euler/ResMultistep采样器、Simple/SGMUniform调度器）
DEFAULT_IMAGE_PARAMS = {
    "model": "Qwen/Qwen-Image",
    "negative_prompt": "blurry, low res, deformed, 丑陋, 水印",
    "width": 768,
    "height": 768,
    "num_images": 1,
    "seed": -1,
    "cfg_scale": 8,
    "parameters": {
        "sampler": "DPM++ 2M Karras",  # 默认采样器（保留推荐项）
        "schedule": "sgm_uniform",     # 默认调度器（新增，适配多数采样器）
        "steps": 30                    # 默认步数
    }
}
