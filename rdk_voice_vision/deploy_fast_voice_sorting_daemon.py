import posixpath
import sys

sys.path.insert(0, "pydeps")

import paramiko


HOST = "192.168.127.10"
USER = "root"
PASSWORD = "root"

REMOTE_DIR = "/root/voice_photo"
REMOTE_SCRIPT = posixpath.join(REMOTE_DIR, "voice_vision_daemon.py")


DAEMON_SCRIPT = r'''#!/usr/bin/env python3
import datetime as dt
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import wave

import cv2
import numpy as np
from vosk import KaldiRecognizer, Model, SetLogLevel


BASE_DIR = "/root/voice_photo"
PHOTO_DIR = os.path.join(BASE_DIR, "photos")
AUDIO_FILE = os.path.join(BASE_DIR, "command.wav")
MODEL_DIR = os.path.join(BASE_DIR, "models", "vosk-model-small-cn-0.22")
STATE_FILE = os.path.join(BASE_DIR, "assistant_state.json")
VISION_MODEL = os.path.join(BASE_DIR, "vision_models", "yogurt_water_best.onnx")
PACKAGE_MODEL = "/root/voice_photo/vision_models/package_sort_best.onnx"
MIC_DEVICE = "plughw:CARD=Device,DEV=0"
SAY_SCRIPT = "/root/voice_photo/say.py"

IMG_SIZE = 640
CONF_THRES = 0.25
NMS_THRES = 0.45
PACKAGE_CLASSES = ["box", "bag", "shipping_label", "barcode"]
OLD_CLASSES = ["酸奶", "矿泉水"]

DEFAULT_STATE = {
    "sort_rules": {},
    "last_photo": "",
    "camera_enabled": False,
    "sorting_enabled": False,
}


def log(text):
    print(text, flush=True)


def strip_thinking(text):
    if not text:
        return ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I)
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return text.strip()


def speak_reply(text):
    text = strip_thinking(text)
    if not text:
        return
    # Avoid repeated noisy feedback while the room is silent.
    if any(p in text for p in ["我没有听清楚", "运行出错"]):
        return
    if not os.path.exists(SAY_SCRIPT):
        return
    try:
        subprocess.Popen(
            ["python3", SAY_SCRIPT, text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        log("语音播报启动失败：" + repr(exc))


def reply(text, speak=True):
    text = strip_thinking(text)
    log("开发板：" + text)
    if speak:
        speak_reply(text)


def now_name(prefix, suffix):
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{stamp}{suffix}"


def normalize(text):
    return (
        text.replace(" ", "")
        .replace("，", "")
        .replace("。", "")
        .replace("？", "")
        .replace("?", "")
        .replace("！", "")
        .replace("!", "")
    )


def contains_any(text, words):
    return any(word in text for word in words)


def load_state():
    if not os.path.exists(STATE_FILE):
        return dict(DEFAULT_STATE)
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        state = dict(DEFAULT_STATE)
        state.update(data)
        return state
    except Exception:
        return dict(DEFAULT_STATE)


def save_state(state):
    os.makedirs(BASE_DIR, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


class Camera:
    def __init__(self, index=0):
        self.index = index
        self.cap = None
        self.enabled = False
        self.last_frame = None

    def start(self):
        if self.cap is not None and self.cap.isOpened():
            self.enabled = True
            return
        self.cap = cv2.VideoCapture(self.index)
        if not self.cap.isOpened():
            self.cap = None
            raise RuntimeError("摄像头打不开，请检查 USB 摄像头是否插好")
        for _ in range(12):
            self.cap.read()
            time.sleep(0.04)
        self.enabled = True
        log("摄像头已打开，并保持拍摄状态。")

    def stop(self):
        if self.cap is not None:
            self.cap.release()
        self.cap = None
        self.enabled = False
        self.last_frame = None
        log("摄像头已关闭。")

    def read(self):
        if not self.enabled:
            raise RuntimeError("摄像头还没有启动。请先说：打开摄像头，或者开始分拣。")
        if self.cap is None or not self.cap.isOpened():
            self.start()
        frame = None
        ret = False
        for _ in range(4):
            ret, frame = self.cap.read()
            time.sleep(0.02)
        if not ret or frame is None:
            self.stop()
            raise RuntimeError("摄像头没有读到画面，请重新说：打开摄像头")
        self.last_frame = frame
        return frame


def save_frame(frame):
    os.makedirs(PHOTO_DIR, exist_ok=True)
    path = os.path.join(PHOTO_DIR, now_name("photo", ".jpg"))
    cv2.imwrite(path, frame)
    return path


def record_audio(seconds=3):
    cmd = [
        "arecord",
        "-D", MIC_DEVICE,
        "-f", "S16_LE",
        "-r", "16000",
        "-c", "1",
        "-d", str(seconds),
        AUDIO_FILE,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return AUDIO_FILE


def recognize_offline(path, model):
    with wave.open(path, "rb") as wf:
        recognizer = KaldiRecognizer(model, wf.getframerate())
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            recognizer.AcceptWaveform(data)
    result = json.loads(recognizer.FinalResult())
    return normalize(result.get("text", ""))


def infer_item(text):
    if contains_any(text, ["矿泉水", "水瓶", "瓶装水", "水"]):
        return "矿泉水"
    if contains_any(text, ["酸奶", "奶"]):
        return "酸奶"
    if contains_any(text, ["快递盒", "纸箱", "箱子", "盒子"]):
        return "快递盒"
    if contains_any(text, ["快递袋", "袋子", "袋"]):
        return "快递袋"
    if contains_any(text, ["快递", "包裹", "物流件"]):
        return "快递件"
    return ""


def infer_side(text):
    if contains_any(text, ["左边", "左侧", "左面", "左"]):
        return "左边"
    if contains_any(text, ["右边", "右侧", "右面", "右"]):
        return "右边"
    if contains_any(text, ["前面", "前方", "前"]):
        return "前方"
    if contains_any(text, ["后面", "后方", "后"]):
        return "后方"
    return ""


def describe_rules(state):
    rules = state.get("sort_rules", {})
    if not rules:
        return "现在还没有设置分拣规则。你可以说，把快递盒分到左边。"
    return "当前分拣规则是：" + "，".join([f"{k}分到{v}" for k, v in rules.items()]) + "。"


def letterbox(image, new_shape=640, color=(114, 114, 114)):
    h, w = image.shape[:2]
    scale = min(new_shape / h, new_shape / w)
    nh, nw = int(round(h * scale)), int(round(w * scale))
    resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((new_shape, new_shape, 3), color, dtype=np.uint8)
    top = (new_shape - nh) // 2
    left = (new_shape - nw) // 2
    canvas[top:top + nh, left:left + nw] = resized
    return canvas, scale, left, top


def parse_yolo_output(output, image_shape, scale, pad_x, pad_y, class_names):
    if isinstance(output, (list, tuple)):
        output = output[0]
    output = np.squeeze(output)
    if output.ndim != 2:
        raise RuntimeError(f"模型输出维度异常：{output.shape}")
    preds = output.T if output.shape[0] < output.shape[1] and output.shape[0] <= 32 else output

    h0, w0 = image_shape[:2]
    boxes, scores, class_ids = [], [], []
    for row in preds:
        if len(row) < 5:
            continue
        cx, cy, bw, bh = row[:4]
        cls_scores = row[4:]
        cid = int(np.argmax(cls_scores))
        score = float(cls_scores[cid])
        if score < CONF_THRES:
            continue
        x1 = (cx - bw / 2 - pad_x) / scale
        y1 = (cy - bh / 2 - pad_y) / scale
        x2 = (cx + bw / 2 - pad_x) / scale
        y2 = (cy + bh / 2 - pad_y) / scale
        x1 = max(0, min(w0 - 1, int(round(x1))))
        y1 = max(0, min(h0 - 1, int(round(y1))))
        x2 = max(0, min(w0 - 1, int(round(x2))))
        y2 = max(0, min(h0 - 1, int(round(y2))))
        if x2 <= x1 or y2 <= y1:
            continue
        boxes.append([x1, y1, x2 - x1, y2 - y1])
        scores.append(score)
        class_ids.append(cid)

    if not boxes:
        return []
    idxs = cv2.dnn.NMSBoxes(boxes, scores, CONF_THRES, NMS_THRES)
    if len(idxs) == 0:
        return []
    results = []
    for i in np.array(idxs).reshape(-1).tolist():
        cid = class_ids[i]
        name = class_names[cid] if 0 <= cid < len(class_names) else f"类别{cid}"
        results.append({"name": name, "score": scores[i], "box": boxes[i]})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


class Vision:
    def __init__(self, model_path, class_names):
        self.model_path = model_path
        self.class_names = class_names
        self.net = None

    def available(self):
        return os.path.exists(self.model_path)

    def load(self):
        if self.net is not None:
            return
        if not self.available():
            raise RuntimeError(f"视觉模型不存在：{self.model_path}")
        self.net = cv2.dnn.readNetFromONNX(self.model_path)
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        log("视觉模型已加载：" + self.model_path)

    def detect(self, frame):
        self.load()
        input_image, scale, pad_x, pad_y = letterbox(frame, IMG_SIZE)
        blob = cv2.dnn.blobFromImage(input_image, 1 / 255.0, (IMG_SIZE, IMG_SIZE), swapRB=True, crop=False)
        self.net.setInput(blob)
        output = self.net.forward()
        return parse_yolo_output(output, frame.shape, scale, pad_x, pad_y, self.class_names)


def send_robot_command(command, item="", target=""):
    bridge_path = "/root/robot_bridge/robot_client.py"
    if not os.path.exists(bridge_path):
        return {"ok": False, "message": "机械臂桥接程序还没有部署"}
    try:
        spec = importlib.util.spec_from_file_location("robot_client", bridge_path)
        robot_client = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(robot_client)
        return robot_client.send_command(command, item=item, target=target, source="rdk_voice")
    except Exception as exc:
        return {"ok": False, "message": f"机械臂指令发送失败：{exc}"}


def package_decision(detections):
    names = [d["name"] for d in detections]
    has_package = any(n in ["box", "bag"] for n in names)
    has_label = any(n in ["shipping_label", "barcode"] for n in names)
    package_type = "box" if "box" in names else "bag" if "bag" in names else "package"
    if not has_package and has_label:
        has_package = True
    if not has_package:
        return "no_package", "我没有明显看到快递件。"
    if has_label:
        return f"sort_{package_type}", "我看到快递面单，判断为正面朝上，可以直接分拣。"
    return "flip_package", "我看到了快递件，但没有看到面单，判断需要先翻面。"


def describe_package_detections(detections):
    if not detections:
        return "没有明显识别到快递件或面单。"
    zh = {"box": "快递盒", "bag": "快递袋", "shipping_label": "快递面单", "barcode": "条码"}
    parts = []
    for d in detections[:4]:
        parts.append(f"{zh.get(d['name'], d['name'])}，置信度{d['score']:.2f}")
    return "我看到了" + "；".join(parts) + "。"


def ask_moss(user_text, state, camera):
    try:
        with open("/root/.openclaw/openclaw.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        provider = cfg["models"]["providers"]["custom-gateway"]
        base_url = provider["baseUrl"].rstrip("/")
        api_key = provider["apiKey"]
        model = provider["models"][0]["id"]
    except Exception:
        return "我现在无法连接复杂对话模型。"

    camera_status = "已打开" if camera.enabled else "未打开"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是RDK X5上的物流识别分拣助手。"
                    "不要输出思考过程，不要输出<think>标签。"
                    "回答必须简短中文，不超过60字。"
                ),
            },
            {
                "role": "user",
                "content": f"摄像头{camera_status}。用户说：{user_text}",
            },
        ],
        "temperature": 0.2,
        "max_tokens": 120,
    }
    req = urllib.request.Request(
        base_url + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return strip_thinking(data["choices"][0]["message"]["content"])
    except Exception:
        return "复杂对话暂时没有响应。"


def is_camera_start_command(text):
    return text in ["开", "打开", "开启", "启动"] or contains_any(text, [
        "开始拍照", "开始照相", "开始识别", "开始检测", "打开摄像头",
        "启动摄像头", "开启摄像头", "开始工作", "准备拍照", "进入拍照模式",
        "打开视觉", "启动视觉", "开启视觉", "开始分拣", "启动分拣", "开始物流分拣",
    ])


def is_camera_stop_command(text):
    return contains_any(text, [
        "停止拍照", "停止照相", "关闭摄像头", "关掉摄像头", "停止识别",
        "停止检测", "关闭视觉", "退出拍照模式", "摄像头休息", "停止分拣",
    ])


def handle_command(text, camera, package_vision, old_vision):
    state = load_state()
    if not text:
        reply("我没有听清楚，你可以靠近麦克风再说一遍。", speak=False)
        return True

    log("你说：" + text)

    if contains_any(text, ["退出", "结束", "再见", "不用听了"]):
        reply("好的，我先停止监听。")
        camera.stop()
        return False

    if is_camera_stop_command(text):
        camera.stop()
        state["camera_enabled"] = False
        state["sorting_enabled"] = False
        save_state(state)
        reply("好的，我已关闭摄像头并停止分拣。")
        return True

    if is_camera_start_command(text):
        camera.start()
        state["camera_enabled"] = True
        state["sorting_enabled"] = True
        save_state(state)
        reply("好的，摄像头已打开，我会保持拍摄状态，可以开始识别分拣。")
        return True

    if contains_any(text, ["你好", "您好", "哈喽", "在吗"]):
        reply("你好，我是物流识别分拣助手。")
        return True

    if contains_any(text, ["帮助", "你会什么", "能做什么", "怎么用"]):
        reply("你可以说：打开摄像头、开始分拣、你看到了什么、拍照、停止分拣。")
        return True

    if contains_any(text, ["状态", "情况", "准备好了吗", "正常吗"]):
        cam = "已打开" if camera.enabled else "未打开"
        model = "已部署" if package_vision.available() else "未部署"
        reply(f"麦克风正在监听，摄像头{cam}，快递识别模型{model}。")
        return True

    if contains_any(text, ["规则", "分拣标准", "分类标准", "怎么分"]):
        reply(describe_rules(state))
        return True

    item, side = infer_item(text), infer_side(text)
    if item and side and contains_any(text, ["分", "放", "归", "送", "移", "到"]):
        state.setdefault("sort_rules", {})[item] = side
        save_state(state)
        reply(f"好的，我记住了：{item}分到{side}。")
        return True

    if contains_any(text, ["拍照", "照相", "拍一张", "拍张", "拍个照片", "拍一下", "拍着"]):
        if not camera.enabled:
            camera.start()
            state["camera_enabled"] = True
            save_state(state)
        frame = camera.read()
        path = save_frame(frame)
        state["last_photo"] = path
        save_state(state)
        reply(f"已拍照，照片保存在 {path}")
        return True

    if contains_any(text, ["你能看到什么", "看到什么", "看见什么", "画面里有什么", "桌子上有什么", "帮我看看", "看一下", "检测", "识别", "分拣"]):
        if not camera.enabled:
            reply("摄像头还没打开。请先说：打开摄像头。")
            return True
        frame = camera.read()
        path = save_frame(frame)
        state["last_photo"] = path
        save_state(state)

        if package_vision.available():
            detections = package_vision.detect(frame)
            decision, decision_text = package_decision(detections)
            if decision == "flip_package":
                send_robot_command("flip_package", item="快递件", target="翻面")
            elif decision.startswith("sort_"):
                send_robot_command(decision, item="快递件", target="分拣")
            reply(describe_package_detections(detections) + decision_text)
        elif old_vision.available():
            detections = old_vision.detect(frame)
            reply("我还没有快递模型，当前只能使用旧模型检测。")
        else:
            reply(f"我已拍照，照片保存在 {path}，但还没有可用视觉模型。")
        return True

    if contains_any(text, ["停止"]):
        send_robot_command("stop")
        reply("已发送停止指令。")
        return True

    if item:
        reply(f"我听到了{item}。如果要设置规则，可以说：把{item}分到左边。")
        return True

    answer = ask_moss(text, state, camera)
    reply(answer)
    return True


def main():
    os.makedirs(BASE_DIR, exist_ok=True)
    SetLogLevel(-1)
    if not os.path.isdir(MODEL_DIR):
        raise RuntimeError(f"离线语音模型不存在：{MODEL_DIR}")

    speech_model = Model(MODEL_DIR)
    camera = Camera(0)
    package_vision = Vision(PACKAGE_MODEL, PACKAGE_CLASSES)
    old_vision = Vision(VISION_MODEL, OLD_CLASSES)

    if package_vision.available():
        try:
            package_vision.load()
        except Exception as exc:
            log("快递模型加载失败：" + repr(exc))
    elif old_vision.available():
        try:
            old_vision.load()
        except Exception as exc:
            log("旧视觉模型加载失败：" + repr(exc))

    state = load_state()
    state["camera_enabled"] = False
    state["sorting_enabled"] = False
    save_state(state)
    reply("系统已启动，我正在监听语音。需要分拣时请说：打开摄像头。")

    while True:
        try:
            log("开始录音 3 秒，请说话...")
            record_audio(3)
            text = recognize_offline(AUDIO_FILE, speech_model)
            if not handle_command(text, camera, package_vision, old_vision):
                break
        except Exception as exc:
            reply(f"运行出错：{exc}", speak=False)
            time.sleep(1)

    camera.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(
    HOST,
    username=USER,
    password=PASSWORD,
    timeout=8,
    auth_timeout=8,
    look_for_keys=False,
    allow_agent=False,
)

stdin, stdout, stderr = client.exec_command(f"mkdir -p {REMOTE_DIR}", timeout=20)
stdout.channel.recv_exit_status()

sftp = client.open_sftp()
with sftp.file(REMOTE_SCRIPT, "w") as remote_file:
    remote_file.write(DAEMON_SCRIPT)
sftp.close()

cmd = f"""set -e
chmod +x {REMOTE_SCRIPT}
python3 -m py_compile {REMOTE_SCRIPT}
systemctl restart voice-vision-assistant.service
sleep 2
systemctl --no-pager --full status voice-vision-assistant.service || true
journalctl -u voice-vision-assistant -n 20 --no-pager || true
"""

stdin, stdout, stderr = client.exec_command(cmd, timeout=90)
out = stdout.read().decode(errors="replace")
err = stderr.read().decode(errors="replace")
if out:
    print(out)
if err:
    print("ERR:", err)
print("exit", stdout.channel.recv_exit_status())
client.close()
