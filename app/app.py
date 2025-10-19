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

# 初始化Flask服务
app = Flask(__name__, static_folder="../frontend")
os.makedirs(IMAGE_SAVE_PATH, exist_ok=True)
print(f"图片保存路径已确认：{os.path.abspath(IMAGE_SAVE_PATH)}")

# ModelScope请求头
common_headers = {
    "Authorization": f"Bearer {MODEL_SCOPE_API_KEY}",
    "Content-Type": "application/json",
}

# 前端页面访问接口
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# 生图接口（核心新增：接收前端传的CFG参数）
@app.route('/generate-image', methods=['POST'])
def generate_image():
    global start_timestamp
    start_timestamp = time.time()
    try:
        req_params = request.get_json() or {}
        user_prompt = req_params.get("prompt", "").strip()
        if not user_prompt:
            return jsonify({"error": "请先填写Prompt再生成！"}), 400

        # 构造生图参数（新增：前端传了CFG就用前端的，否则用默认8）
        modelscope_params = {
            **DEFAULT_IMAGE_PARAMS,
            "prompt": user_prompt,
            "negative_prompt": req_params.get("negative_prompt", DEFAULT_IMAGE_PARAMS["negative_prompt"]),
            "cfg_scale": req_params.get("cfgScale", DEFAULT_IMAGE_PARAMS["cfg_scale"])  # 新增CFG参数接收
        }

        # 发起ModelScope异步请求（自动将CFG传给API）
        response = requests.post(
            f"{MODEL_SCOPE_BASE_URL}v1/images/generations",
            headers={**common_headers, "X-ModelScope-Async-Mode": "true"},
            data=json.dumps(modelscope_params, ensure_ascii=False).encode('utf-8')
        )
        response.raise_for_status()
        task_id = response.json()["task_id"]
        print(f"生图任务提交成功，TaskID：{task_id}，Prompt：{user_prompt}，CFG：{modelscope_params['cfg_scale']}")

        return jsonify({
            "task_id": task_id,
            "user_prompt": user_prompt,
            "cfg_scale": modelscope_params["cfg_scale"],  # 回传CFG给前端显示
            "save_path": os.path.abspath(IMAGE_SAVE_PATH),
            "msg": "任务已启动，等待生成..."
        })
    except Exception as e:
        return jsonify({"error": f"生图启动失败：{str(e)}"}), 500

# 进度查询+图片保存接口（新增：回传CFG给前端）
@app.route('/generate-image', methods=['GET'])
def check_status():
    try:
        task_id = request.args.get("task_id")
        if not task_id:
            return jsonify({"error": "缺少TaskID！"}), 400

        result = requests.get(
            f"{MODEL_SCOPE_BASE_URL}v1/tasks/{task_id}",
            headers={**common_headers, "X-ModelScope-Task-Type": "image_generation"},
        )
        result.raise_for_status()
        data = result.json()

        if data["task_status"] == "SUCCEED":
            img_url = data["output_images"][0]
            img_content = requests.get(img_url).content
            img_filename = f"img_{task_id}_{int(time.time())}_cfg{request.args.get('cfg_scale',8)}.jpg"  # 文件名加CFG标识，方便对比
            img_save_path = os.path.join(IMAGE_SAVE_PATH, img_filename)
            
            with Image.open(BytesIO(img_content)) as img:
                img.save(img_save_path)
            print(f"图片保存成功：{img_save_path}（CFG：{request.args.get('cfg_scale',8)}）")

            # 适配本地/云服务器的图片访问URL
            if FLASK_HOST == "127.0.0.1":
                frontend_img_url = f"/images/{img_filename}"
            else:
                frontend_img_url = f"http://{request.host}/images/{img_filename}"

            return jsonify({
                "task_status": "SUCCEED",
                "img_url": frontend_img_url,
                "save_path": img_save_path,
                "user_prompt": request.args.get("user_prompt"),
                "cfg_scale": request.args.get("cfg_scale", 8)  # 回传CFG，前端显示
            })

        elif data["task_status"] == "FAILED":
            return jsonify({"task_status": "FAILED", "error_msg": data.get("error_msg", "无原因")})
        else:
            return jsonify({"task_status": data["task_status"], "msg": "生成中..."})
    except Exception as e:
        return jsonify({"error": f"查询失败：{str(e)}"}), 500

# 图片访问接口
@app.route('/images/<filename>')
def get_image(filename):
    return send_from_directory(IMAGE_SAVE_PATH, filename)

# 启动服务
if __name__ == '__main__':
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False)
