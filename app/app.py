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
print(f"图片保存路径已确认：{os.path.abspath(IMAGE_SAVE_PATH)}")

common_headers = {
    "Authorization": f"Bearer {MODEL_SCOPE_API_KEY}",
    "Content-Type": "application/json",
}

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# 生图接口（核心：接收前端新增的步数/宽高/生成数量/Seed参数）
@app.route('/generate-image', methods=['POST'])
def generate_image():
    global start_timestamp
    start_timestamp = time.time()
    try:
        req_params = request.get_json() or {}
        user_prompt = req_params.get("prompt", "").strip()
        if not user_prompt:
            return jsonify({"error": "请先填写Prompt再生成！"}), 400

        # 1. 基础参数（CFG/采样器/调度器，逻辑不变）
        cfg_scale = req_params.get("cfgScale", DEFAULT_IMAGE_PARAMS["cfg_scale"])
        if cfg_scale < 1 or cfg_scale > 20:
            return jsonify({"error": "CFG需在1-20之间！"}), 400
        selected_sampler = req_params.get("sampler", DEFAULT_IMAGE_PARAMS["parameters"]["sampler"])
        sampler_steps_map = {
            "DPM++ 2M Karras": 30, "Euler": 22, "ResMultistep": 26,
            "Euler a": 20, "DDIM": 25, "PLMS": 28
        }
        # 新增：前端手动填步数则覆盖自动匹配值，否则用默认
        matched_steps = req_params.get("steps", sampler_steps_map.get(selected_sampler, 30))
        if matched_steps < 10 or matched_steps > 50:  # 限制步数范围，避免无效值
            matched_steps = 30

        # 2. 新增参数：宽高（限制256-1024，默认768）
        width = req_params.get("width", DEFAULT_IMAGE_PARAMS["width"])
        height = req_params.get("height", DEFAULT_IMAGE_PARAMS["height"])
        width = max(256, min(1024, width))
        height = max(256, min(1024, height))

        # 3. 新增参数：生成数量（1-3，默认1）
        num_images = req_params.get("numImages", DEFAULT_IMAGE_PARAMS["num_images"])
        num_images = max(1, min(3, num_images))

        # 4. 新增参数：Seed（前端传-1为随机，否则用指定值）
        seed = req_params.get("seed", DEFAULT_IMAGE_PARAMS["seed"])
        if not isinstance(seed, int) or seed < -1:
            seed = -1

        # 5. 调度器（逻辑不变）
        selected_schedule = req_params.get("schedule", DEFAULT_IMAGE_PARAMS["parameters"]["schedule"])
        valid_schedules = ["simple", "sgm_uniform"]
        if selected_schedule not in valid_schedules:
            selected_schedule = "sgm_uniform"

        # 构造最终参数
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
            f"{MODEL_SCOPE_BASE_URL}v1/images/generations",
            headers={**common_headers, "X-ModelScope-Async-Mode": "true"},
            data=json.dumps(modelscope_params, ensure_ascii=False).encode('utf-8')
        )
        response.raise_for_status()
        task_id = response.json()["task_id"]
        print(f"任务提交成功：TaskID={task_id}，采样器={selected_sampler}，调度器={selected_schedule}，CFG={cfg_scale}，步数={matched_steps}，Seed={seed}，生成数量={num_images}")

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
            "msg": "任务已启动"
        })
    except Exception as e:
        return jsonify({"error": f"生图启动失败：{str(e)}"}), 500

# 进度查询接口（适配多图生成，逻辑不变）
@app.route('/generate-image', methods=['GET'])
def check_status():
    try:
        task_id = request.args.get("task_id")
        if not task_id:
            return jsonify({"error": "缺少TaskID！"}), 400

        # 接收新增参数，用于文件名
        cfg_scale = request.args.get("cfg_scale", 8)
        selected_sampler = request.args.get("sampler", "DPM++ 2M Karras")
        selected_schedule = request.args.get("schedule", "sgm_uniform")
        seed = request.args.get("seed", -1)
        sampler_short_map = {"DPM++ 2M Karras": "DPM2MK", "Euler a": "EulerA", "DDIM": "DDIM", "PLMS": "PLMS", "Euler": "Euler", "ResMultistep": "ResMS"}
        schedule_short_map = {"simple": "Simple", "sgm_uniform": "SGMU"}
        sampler_short = sampler_short_map.get(selected_sampler, "Sampler")
        schedule_short = schedule_short_map.get(selected_schedule, "Schedule")
        seed_short = seed == "-1" ? "Rand" : f"Seed{seed}"  # Seed简化标识（Rand=随机）

        # 查询状态
        result = requests.get(
            f"{MODEL_SCOPE_BASE_URL}v1/tasks/{task_id}",
            headers={**common_headers, "X-ModelScope-Task-Type": "image_generation"},
        )
        result.raise_for_status()
        data = result.json()

        if data["task_status"] == "SUCCEED":
            output_imgs = []
            # 适配多图生成，循环保存
            for idx, img_url in enumerate(data["output_images"], 1):
                img_content = requests.get(img_url).content
                # 文件名含所有新增参数标识
                img_filename = f"img_{task_id}_{int(time.time())}_{sampler_short}_{schedule_short}_{seed_short}_cfg{cfg_scale}_step{request.args.get('steps',30)}_img{idx}.jpg"
                img_save_path = os.path.join(IMAGE_SAVE_PATH, img_filename)
                with Image.open(BytesIO(img_content)) as img:
                    img.save(img_save_path)
                print(f"图片{idx}保存成功：{img_save_path}")

                # 适配URL
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
                "seed": seed
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

# 图片访问接口
@app.route('/images/<filename>')
def get_image(filename):
    return send_from_directory(IMAGE_SAVE_PATH, filename)

# 启动服务
if __name__ == '__main__':
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False)
