# 仅用于补充清空Prompt TXT的接口，确保app.py能正常导入
from flask import Blueprint

# 创建蓝图，后续在app.py中注册
prompt_bp = Blueprint('prompt', __name__)

# 清空Prompt历史TXT的函数（供app.py调用）
def clear_prompt_history_txt(txt_path):
    try:
        if os.path.exists(txt_path):
            os.remove(txt_path)
        return True, "TXT文件清空成功"
    except Exception as e:
        return False, f"清空失败：{str(e)}"
