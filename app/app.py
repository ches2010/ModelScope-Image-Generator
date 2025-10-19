import os
import time
import json
import requests
from PIL import Image
from io import BytesIO
from flask import Flask, request, jsonify, send_from_directory
from config import (
    MODEL_SCOPE_API_KEY, MODEL_SCOPE_BASE_URL,
    FLASK_HOST, FLASK_PORT, IMAGE_SAVE_PATH, DEFAULT_IMAGE_PARAMS
)

app = Flask(__name__, static_folder="../frontend")
os.makedirs(IMAGE_SAVE_PATH, exist_ok=True)
# 定义Prompt历史TXT文件路径（在app目录下，自动创建）
PROMPT_HISTORY_TXT = "./app/prompt_history.txt"
print(f"图片保存路径：{os.path.abspath(IMAGE_SAVE_PATH)}")
print(f"Prompt历史TXT路径：{os.path.abspath(PROMPT_HISTORY_TXT)}")

common_headers = {
    "Authorization": f"Bearer {MODEL_SCOPE_API_KEY}",
    "Content-Type": "application/json",
}

# 新增：将Prompt写入TXT文件（持久化，去重，保留最后10条）
def save_prompt_to_txt(prompt):
    if not prompt.strip():
        return
    # 1. 读取现有TXT中的Prompt（无则创建空列表）
    existing_prompts = []
    if os.path.exists(PROMPT_HISTORY_TXT):
        with open(PROMPT_HISTORY_TXT, "r", encoding="utf-8") as f:
            existing_prompts = [line.strip() for line in f if line.strip()]
    # 2. 去重：避免重复保存相同Prompt
    existing_prompts = [p for p in existing_prompts if p != prompt.strip()]
    # 3. 新增Prompt放最前面，保留最后10条
    existing_prompts.insert(0, prompt.strip())
    if len(existing_prompts) > 10:
        existing_prompts = existing_prompts[:10]
    # 4. 写入TXT（覆盖原有内容）
    with open(PROMPT_HISTORY_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(existing_prompts))

# 新增：读取TXT中的Prompt（供前端初始化加载，避免清缓存丢失）
def get_prompt_from_txt():
    if os.path.exists(PROMPT_HISTORY_TXT):
        with open(PROMPT_HISTORY_TXT, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    return []

# 新增：前端获取TXT中的Prompt接口（页面加载时调用）
@app.route('/get-prompt-history', methods=['GET'])
def get_prompt_history():
    try:
        txt_prompts = get_prompt_from_txt()
        return jsonify({"prompt_history": txt_prompts}), 200
    except Exception as e:
        return jsonify({"error": f"读取Prompt历史失败：{str(e)}"}), 500

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# 生图接口（核心修改：1. 宽高取消限制；2. 调用函数写入TXT）
@app.route('/generate-image', methods=['POST'])
def generate_image():
    global start_timestamp
    start_timestamp = time.time()
    try:
        req_params = request.get_json() or {}
        user_prompt = req_params.get("prompt", "").strip()
        if not user_prompt:
            return jsonify({"error": "请先填写Prompt再生成！"}), 400

        # 1. 基础参数（逻辑不变）
        cfg_scale = req_params.get("cfgScale", DEFAULT_IMAGE_PARAMS["cfg_scale"])
        if cfg_scale < 1 or cfg_scale > 20:
            return jsonify({"error": "CFG需在1-20之间！"}), 400
        selected_sampler = req_params.get("sampler", DEFAULT_IMAGE_PARAMS["parameters"]["sampler"])
        sampler_steps_map = {
            "DPM++ 2M Karras": 30, "Euler": 22, "ResMultistep": 26,
            "Euler a": 20, "DDIM": 25, "PLMS": 28
        }
        matched_steps = req_params.get("steps", sampler_steps_map.get(selected_sampler, 30))
        if matched_steps < 10 or matched_steps > 50:
            matched_steps = 30

        # 2. 核心修改：宽高取消限制（不做min/max修正，完全按用户输入）
        width = req_params.get("width", DEFAULT_IMAGE_PARAMS["width"])
        height = req_params.get("height", DEFAULT_IMAGE_PARAMS["height"])
        # 仅确保是正整数（避免非数字输入报错）
        width = int(width) if isinstance(width, (int, str)) and str(width).isdigit() else 768
        height = int(height) if isinstance(height, (int, str)) and str(height).isdigit() else 768

        # 3. 生成数量（逻辑不变，1-3限制保留，避免超ModelScope多数模型上限）
        num_images = req_params.get("numImages", DEFAULT_IMAGE_PARAMS["num_images"])
        num_images = max(1, min(3, num_images))

        # 4. Seed（逻辑不变）
        seed = req_params.get("seed", DEFAULT_IMAGE_PARAMS["seed"])
        if not isinstance(seed, int) or seed < -1:
            seed = -1

        # 5. 调度器（逻辑不变）
        selected_schedule = req_params.get("schedule", DEFAULT_IMAGE_PARAMS["parameters"]["schedule"])
        valid_schedules = ["simple", "sgm_uniform"]
        if selected_schedule not in valid_schedules:
            selected_schedule = "sgm_uniform"

        # 6. 新增：将当前Prompt写入TXT（持久化存储）
        save_prompt_to_txt(user_prompt)

        # 构造参数
        modelscope_params = {
            **DEFAULT_IMAGE_PARAMS,
            "prompt": user_prompt,
            "negative_prompt": req_params.get("negativePrompt", DEFAULT_IMAGE_PARAMS["negative_prompt"]),
            "cfg_scale": cfg_scale,
            "width": width,
            "height": height,
            "num_images": num_images,
            "seed": seed,
            "parameters": {
                "sampler": selected_sampler,
                "schedule": selected_schedule,
                "steps": matched_steps
            }
        }

        # 发起请求
        response = requests.post(
            f"{MODEL_SCOPE_BASE_URL}v1/generations",
            headers={**common_headers, "X-ModelScope-Async-Mode": "true"},
            data=json.dumps(modelscope_params, ensure_ascii=False).encode('utf-8')
        )
        response.raise_for_status()
        task_id = response.json()["task_id"]
        print(f"任务提交成功：TaskID={task_id}，宽高={width}x{height}，Seed={seed}，Prompt={user_prompt[:30]}...")

        return jsonify({
            "task_id": task_id,
            "user_prompt": user_prompt,
            "cfg_scale": cfg_scale,
            "sampler": selected_sampler,
            "schedule": selected_schedule,
            "steps": matched_steps,
            "width": width,
            "height": height,
            "num_images": num_images,
            "seed": seed,
            "save_path": os.path.abspath(IMAGE_SAVE_PATH),
            "prompt_txt_path": os.path.abspath(PROMPT_HISTORY_TXT),  # 回传TXT路径给前端显示
            "msg": "任务已启动"
        })
    except Exception as e:
        return jsonify({"error": f"生图启动失败：{str(e)}"}), 500

# 进度查询接口（逻辑不变，适配宽高取消限制后的文件名）
@app.route('/generate-image', methods=['GET'])
def check_status():
    try:
        task_id = request.args.get("task_id")
        if not task_id:
            return jsonify({"error": "缺少TaskID！"}), 400

        cfg_scale = request.args.get("cfg_scale", 8)
        selected_sampler = request.args.get("sampler", "DPM++ 2M Karras")
        selected_schedule = request.args.get("schedule", "sgm_uniform")
        seed = request.args.get("seed", -1)
        width = request.args.get("width", 768)
        height = request.args.get("height", 768)
        sampler_short_map = {"DPM++ 2M Karras": "DPM2MK", "Euler a": "EulerA", "DDIM": "DDIM", "PLMS": "PLMS", "Euler": "Euler", "ResMultistep": "ResMS"}
        schedule_short_map = {"simple": "Simple", "sgm_uniform": "SGMU"}
        sampler_short = sampler_short_map.get(selected_sampler, "Sampler")
        schedule_short = schedule_short_map.get(selected_schedule, "Schedule")
        seed_short = seed == "-1" ? "Rand" : f"Seed{seed}"
        size_short = f"{width}x{height}"  # 文件名含实际宽高，方便追溯

        result = requests.get(
            f"{MODEL_SCOPE_BASE_URL}v1/tasks/{task_id}",
            headers={**common_headers, "X-ModelScope-Task-Type": "image_generation"},
        )
        result.raise_for_status()
        data = result.json()

        if data["task_status"] == "SUCCEED":
            output_imgs = []
            for idx, img_url in enumerate(data["output_images"], 1):
                img_content = requests.get(img_url).content
                # 文件名含宽高（取消限制后，标识实际尺寸）
                img_filename = f"img_{task_id}_{int(time.time())}_{sampler_short}_{schedule_short}_{seed_short}_{size_short}_cfg{cfg_scale}_step{request.args.get('steps',30)}_img{idx}.jpg"
                img_save_path = os.path.join(IMAGE_SAVE_PATH, img_filename)
                with Image.open(BytesIO(img_content)) as img:
                    img.save(img_save_path)
                print(f"图片{idx}保存成功：{img_save_path}")

                if FLASK_HOST == "127.0.0.1":
                    output_imgs.append(f"/images/{img_filename}")
                else:
                    output_imgs.append(f"http://{request.host}/images/{img_filename}")

            return jsonify({
                "task_status": "SUCCEED",
                "output_images": output_imgs,
                "save_path": os.path.abspath(IMAGE_SAVE_PATH),
                "user_prompt": request.args.get("user_prompt"),
                "cfg_scale": cfg_scale,
                "sampler": selected_sampler,
                "schedule": selected_schedule,
                "seed": seed,
                "width": width,
                "height": height
            })

        elif data["task_status"] == "FAILED":
            return jsonify({"task_status": "FAILED", "error_msg": data.get("error_msg", "无原因")})
        else:
            return jsonify({"task_status": data["task_status"], "msg": "生成中..."})
    except Exception as e:
        return jsonify({"error": f"查询失败：{str(e)}"}), 500

@app.route('/images/<filename>')
def get_image(filename):
    return send_from_directory(IMAGE_SAVE_PATH, filename)

if __name__ == '__main__':
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False)
