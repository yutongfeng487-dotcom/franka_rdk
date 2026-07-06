import posixpath
import sys

sys.path.insert(0, "pydeps")

import paramiko


HOST = "192.168.127.10"
USER = "root"
PASSWORD = "root"

REMOTE_DIR = "/root/voice_photo"
REMOTE_SCRIPT = posixpath.join(REMOTE_DIR, "voice_vision_daemon.py")
SERVICE_PATH = "/etc/systemd/system/voice-vision-assistant.service"


DAEMON_SCRIPT = r'''#!/usr/bin/env python3
import datetime as dt
import json
import os
import subprocess
import sys
import time
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
MIC_DEVICE = "plughw:CARD=Device,DEV=0"

IMG_SIZE = 640
CONF_THRES = 0.25
NMS_THRES = 0.45
CLASS_NAMES = ["酸奶", "矿泉水"]

DEFAULT_STATE = {"sort_rules": {}, "last_photo": ""}


def log(text):
    print(text, flush=True)


def reply(text):
    log("开发板：" + text)


def now_name(prefix, suffix):
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{stamp}{suffix}"


def normalize(text):
    return text.replace(" ", "").replace("，", "").replace("。", "").replace("？", "").replace("?", "")


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

    def open(self):
        if self.cap is not None and self.cap.isOpened():
            return
        self.cap = cv2.VideoCapture(self.index)
        if not self.cap.isOpened():
            raise RuntimeError("摄像头打不开，请检查 USB 摄像头是否插好")
        # Warm up camera so the first requested frame is usable.
        for _ in range(10):
            self.cap.read()
            time.sleep(0.05)
        log("摄像头已打开，并保持工作。")

    def read(self):
        self.open()
        frame = None
        ret = False
        for _ in range(5):
            ret, frame = self.cap.read()
            time.sleep(0.03)
        if not ret or frame is None:
            self.close()
            raise RuntimeError("摄像头没有读到画面")
        return frame

    def close(self):
        if self.cap is not None:
            self.cap.release()
        self.cap = None


def save_frame(frame):
    os.makedirs(PHOTO_DIR, exist_ok=True)
    path = os.path.join(PHOTO_DIR, now_name("photo", ".jpg"))
    cv2.imwrite(path, frame)
    return path


def record_audio(seconds=4):
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
    if contains_any(text, ["饮料", "可乐", "汽水"]):
        return "饮料"
    if contains_any(text, ["绿色", "绿的", "绿颜色"]):
        return "绿色物体"
    if contains_any(text, ["蓝色", "蓝的", "蓝颜色"]):
        return "蓝色物体"
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
        return "现在还没有设置分拣规则。你可以说，把矿泉水分到左边。"
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


def parse_yolo_output(output, image_shape, scale, pad_x, pad_y):
    if isinstance(output, (list, tuple)):
        output = output[0]
    output = np.squeeze(output)
    if output.ndim != 2:
        raise RuntimeError(f"模型输出维度异常：{output.shape}")
    preds = output.T if output.shape[0] < output.shape[1] and output.shape[0] <= 20 else output

    h0, w0 = image_shape[:2]
    boxes, scores, class_ids = [], [], []
    for row in preds:
        if len(row) < 6:
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
        name = CLASS_NAMES[cid] if 0 <= cid < len(CLASS_NAMES) else f"类别{cid}"
        results.append({"name": name, "score": scores[i], "box": boxes[i]})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


class Vision:
    def __init__(self):
        self.net = None

    def load(self):
        if self.net is not None:
            return
        if not os.path.exists(VISION_MODEL):
            raise RuntimeError(f"视觉模型不存在：{VISION_MODEL}")
        self.net = cv2.dnn.readNetFromONNX(VISION_MODEL)
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        log("视觉模型已加载。")

    def detect(self, frame):
        self.load()
        input_image, scale, pad_x, pad_y = letterbox(frame, IMG_SIZE)
        blob = cv2.dnn.blobFromImage(input_image, 1 / 255.0, (IMG_SIZE, IMG_SIZE), swapRB=True, crop=False)
        self.net.setInput(blob)
        output = self.net.forward()
        return parse_yolo_output(output, frame.shape, scale, pad_x, pad_y)


def describe_detections(detections):
    if not detections:
        return "但是我没有明显识别到酸奶或矿泉水。"
    counts, best = {}, {}
    for det in detections:
        name = det["name"]
        counts[name] = counts.get(name, 0) + 1
        best[name] = max(best.get(name, 0), det["score"])
    parts = []
    for name, count in counts.items():
        if count == 1:
            parts.append(f"1个{name}，置信度{best[name]:.2f}")
        else:
            parts.append(f"{count}个{name}，最高置信度{best[name]:.2f}")
    return "我看到了" + "，".join(parts) + "。"


def handle_command(text, camera, vision):
    state = load_state()
    if not text:
        reply("我没有听清楚，你可以靠近麦克风再说一遍。")
        return True

    log("你说：" + text)

    if contains_any(text, ["退出", "停止", "结束", "再见", "不用听了"]):
        reply("好的，我先停止监听。")
        return False

    if contains_any(text, ["你好", "您好", "哈喽", "在吗"]):
        reply("你好，我在。你可以问我你能看到什么，也可以让我拍照或设置分拣规则。")
        return True

    if contains_any(text, ["帮助", "你会什么", "能做什么", "怎么用"]):
        reply("我可以一直监听语音，保持摄像头工作。你可以说：你能看到什么、拍照、把矿泉水分到左边、当前规则、状态、停止。")
        return True

    if contains_any(text, ["状态", "情况", "准备好了吗", "正常吗"]):
        reply("我正在后台运行，麦克风、摄像头和酸奶矿泉水识别模型都已启动。")
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

    if contains_any(text, ["拍照", "照相", "拍一张", "拍张", "拍个照片", "拍一下"]):
        frame = camera.read()
        path = save_frame(frame)
        state["last_photo"] = path
        save_state(state)
        reply(f"已经拍照，照片保存在 {path}")
        return True

    if contains_any(text, ["你能看到什么", "看到什么", "看见什么", "画面里有什么", "桌子上有什么", "帮我看看", "看一下", "检测", "识别"]):
        frame = camera.read()
        path = save_frame(frame)
        state["last_photo"] = path
        save_state(state)
        detections = vision.detect(frame)
        reply(describe_detections(detections) + f"照片保存在 {path}")
        return True

    if item:
        reply(f"我听到了你提到{item}。如果你想设置规则，可以说：把{item}分到左边。")
        return True

    reply("我听到了，但还没有学会处理这句话。你可以说：你能看到什么、拍照、把矿泉水分到左边、状态、帮助。")
    return True


def main():
    os.makedirs(BASE_DIR, exist_ok=True)
    SetLogLevel(-1)
    if not os.path.isdir(MODEL_DIR):
        raise RuntimeError(f"离线语音模型不存在：{MODEL_DIR}")

    speech_model = Model(MODEL_DIR)
    camera = Camera(0)
    vision = Vision()
    camera.open()
    if os.path.exists(VISION_MODEL):
        vision.load()

    reply("开机语音视觉助手已启动。我会一直监听，并保持摄像头工作。")

    while True:
        try:
            log("开始录音 4 秒，请说话...")
            record_audio(4)
            text = recognize_offline(AUDIO_FILE, speech_model)
            if not handle_command(text, camera, vision):
                break
        except Exception as exc:
            reply(f"运行出错：{exc}")
            time.sleep(2)

    camera.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


SERVICE = f'''[Unit]
Description=RDK X5 Voice Vision Assistant
After=multi-user.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 {REMOTE_SCRIPT}
WorkingDirectory={REMOTE_DIR}
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
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
with sftp.file(SERVICE_PATH, "w") as remote_file:
    remote_file.write(SERVICE)
sftp.close()

cmd = f"""set -e
chmod +x {REMOTE_SCRIPT}
python3 -m py_compile {REMOTE_SCRIPT}
systemctl daemon-reload
systemctl enable voice-vision-assistant.service
systemctl restart voice-vision-assistant.service
sleep 2
systemctl --no-pager --full status voice-vision-assistant.service || true
"""

stdin, stdout, stderr = client.exec_command(cmd, timeout=80)
out = stdout.read().decode(errors="replace")
err = stderr.read().decode(errors="replace")
if out:
    print(out)
if err:
    print("ERR:", err)
print("exit", stdout.channel.recv_exit_status())
client.close()
