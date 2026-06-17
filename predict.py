import json
import base64
import tempfile
import os
import time
import requests
from cog import BasePredictor, Input, Path
import subprocess

# ⚠️ 请确保 workflows/flux2_img2img.json 文件已存在
WORKFLOW_FILE = "workflows/flux2_img2img.json"

class Predictor(BasePredictor):
    def setup(self):
        # 启动 ComfyUI 后台服务
        self.comfyui_process = subprocess.Popen(
            ["python", "main.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(15)  # 等待服务启动

    def predict(
        self,
        image: Path = Input(description="用户上传的图片"),
        prompt: str = Input(description="修改指令"),
    ) -> Path:
        # 1. 读取工作流 JSON
        with open(WORKFLOW_FILE, "r") as f:
            workflow = json.load(f)

        # 2. 将用户图片转为 Base64
        with open(image, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode("utf-8")

        # 3. 注入参数到工作流节点
        for node in workflow["nodes"]:
            if node["id"] == 63:  # 您的图片输入节点
                node["widgets_values"] = [img_base64]
            if node["id"] == 19:  # 您的提示词输入节点
                node["widgets_values"] = [prompt]

        # 4. 保存修改后的工作流为临时文件
        temp_workflow = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(workflow, temp_workflow)
        temp_workflow.close()

        # 5. 调用 ComfyUI API
        api_url = "http://127.0.0.1:8188/prompt"
        with open(temp_workflow.name, "r") as f:
            payload = json.load(f)

        response = requests.post(api_url, json={"prompt": payload})
        response.raise_for_status()
        run_id = response.json()["prompt_id"]

        # 6. 等待并获取输出图片
        output_dir = "output"
        timeout = 300
        start_time = time.time()
        result_image = None

        while time.time() - start_time < timeout:
            files = os.listdir(output_dir)
            if files:
                result_image = os.path.join(output_dir, sorted(files)[-1])
                if os.path.getsize(result_image) > 0:
                    break
            time.sleep(2)

        if not result_image:
            raise Exception("生成超时或未找到输出图片")

        return Path(result_image)