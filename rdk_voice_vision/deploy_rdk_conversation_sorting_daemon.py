import posixpath
import sys

sys.path.insert(0, "pydeps")

import paramiko


HOST = "192.168.127.10"
USER = "root"
PASSWORD = "root"
REMOTE_DIR = "/root/voice_photo"
REMOTE_SCRIPT = posixpath.join(REMOTE_DIR, "voice_vision_daemon.py")


DAEMON = r'''#!/usr/bin/env python3
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import wave

import cv2
import numpy as np
from vosk import KaldiRecognizer, Model, SetLogLevel


BASE_DIR = "/root/voice_photo"
PHOTO_DIR = os.path.join(BASE_DIR, "photos")
AUDIO_FILE = os.path.join(BASE_DIR, "command.wav")
STATE_FILE = os.path.join(BASE_DIR, "assistant_state.json")
ASR_MODEL_DIR = os.path.join(BASE_DIR, "models", "vosk-model-small-cn-0.22")
PACKAGE_MODEL = os.path.join(BASE_DIR, "vision_models", "package_sort_best.onnx")
SAY_SCRIPT = os.path.join(BASE_DIR, "say.py")
ROBOT_LOG = os.path.join(BASE_DIR, "robot_commands.log")

IMG_SIZE = 640
CONF_THRES = 0.25
NMS_THRES = 0.45
PACKAGE_CLASSES = ["box", "bag", "shipping_label", "barcode"]

DEFAULT_STATE = {
    "camera_enabled": False,
    "sorting_enabled": False,
    "pending_flip": False,
    "sort_rules": {},
    "last_photo": "",
    "last_scene": {},
    "last_auto_action_at": 0,
}


def log(message):
    print(message, flush=True)


def normalize(text):
    return re.sub(r"\s+", "", text or "").strip()


def contains_any(text, words):
    return any(w in text for w in words)


def strip_thinking(text):
    text = text or ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I)
    text = re.sub(r"思考[:：].*", "", text, flags=re.S)
    return text.strip() or "我暂时没有想好怎么回答。"


def load_state():
    state = dict(DEFAULT_STATE)
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        if isinstance(saved, dict):
            state.update(saved)
    except Exception:
        pass
    return state


def save_state(state):
    os.makedirs(BASE_DIR, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def reply(text, speak=True):
    text = strip_thinking(text)
    log("开发板：" + text)
    if not speak:
        return
    if not os.path.exists(SAY_SCRIPT):
        return
    try:
        subprocess.Popen(
            ["python3", SAY_SCRIPT, text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def now_name(prefix, suffix):
    return prefix + "_" + time.strftime("%Y%m%d_%H%M%S") + suffix


def choose_mic_device():
    try:
        devices = subprocess.check_output(["arecord", "-l"], text=True, stderr=subprocess.STDOUT)
    except Exception:
        return "default"
    if "card 0: Device" in devices or "USB Audio Device" in devices:
        return "plughw:CARD=Device,DEV=0"
    if "duplexaudio" in devices:
        return "plughw:CARD=duplexaudio,DEV=0"
    return "default"


def record_audio(seconds=5):
    device = choose_mic_device()
    cmd = [
        "arecord",
        "-D", device,
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
        rec = KaldiRecognizer(model, wf.getframerate())
        while True:
            data = wf.readframes(4000)
            if not data:
                break
            rec.AcceptWaveform(data)
    result = json.loads(rec.FinalResult())
    return normalize(result.get("text", ""))


class Camera:
    def __init__(self, index=0):
        self.index = index
        self.cap = None
        self.enabled = False

    def start(self):
        if self.enabled and self.cap is not None and self.cap.isOpened():
            return
        self.cap = cv2.VideoCapture(self.index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        if not self.cap.isOpened():
            raise RuntimeError("摄像头打开失败")
        self.enabled = True

    def read(self):
        self.start()
        ok, frame = self.cap.read()
        if not ok or frame is None:
            raise RuntimeError("摄像头读取失败")
        return frame

    def stop(self):
        if self.cap is not None:
            self.cap.release()
        self.cap = None
        self.enabled = False


def save_frame(frame):
    os.makedirs(PHOTO_DIR, exist_ok=True)
    path = os.path.join(PHOTO_DIR, now_name("photo", ".jpg"))
    cv2.imwrite(path, frame)
    return path


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
        class_scores = row[4:]
        cid = int(np.argmax(class_scores))
        score = float(class_scores[cid])
        if score < CONF_THRES:
            continue
        cx, cy, bw, bh = map(float, row[:4])
        x1 = int((cx - bw / 2 - pad_x) / scale)
        y1 = int((cy - bh / 2 - pad_y) / scale)
        x2 = int((cx + bw / 2 - pad_x) / scale)
        y2 = int((cy + bh / 2 - pad_y) / scale)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w0 - 1, x2), min(h0 - 1, y2)
        boxes.append([x1, y1, max(1, x2 - x1), max(1, y2 - y1)])
        scores.append(score)
        class_ids.append(cid)

    if not boxes:
        return []
    idxs = cv2.dnn.NMSBoxes(boxes, scores, CONF_THRES, NMS_THRES)
    results = []
    if len(idxs) == 0:
        return []
    for i in np.array(idxs).reshape(-1).tolist():
        cid = class_ids[i]
        name = class_names[cid] if 0 <= cid < len(class_names) else f"class_{cid}"
        results.append({"name": name, "score": float(scores[i]), "box": boxes[i]})
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
        if self.net is None:
            if not self.available():
                raise RuntimeError("视觉模型不存在：" + self.model_path)
            self.net = cv2.dnn.readNetFromONNX(self.model_path)
            log("视觉模型已加载：" + self.model_path)

    def detect(self, frame):
        self.load()
        input_image, scale, pad_x, pad_y = letterbox(frame, IMG_SIZE)
        blob = cv2.dnn.blobFromImage(input_image, 1 / 255.0, (IMG_SIZE, IMG_SIZE), swapRB=True, crop=False)
        self.net.setInput(blob)
        output = self.net.forward()
        return parse_yolo_output(output, frame.shape, scale, pad_x, pad_y, self.class_names)


def send_robot_command(command, item="", target=""):
    record = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "command": command,
        "item": item,
        "target": target,
        "source": "rdk_voice",
    }
    try:
        with open(ROBOT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass

    bridge_path = "/root/robot_bridge/robot_client.py"
    if not os.path.exists(bridge_path):
        log("机械臂桥接未部署，已记录高层指令：" + json.dumps(record, ensure_ascii=False))
        return {"ok": False, "message": "机械臂桥接程序还没有部署"}
    try:
        spec = importlib.util.spec_from_file_location("robot_client", bridge_path)
        robot_client = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(robot_client)
        return robot_client.send_command(command, item=item, target=target, source="rdk_voice")
    except Exception as exc:
        return {"ok": False, "message": f"机械臂指令发送失败：{exc}"}


def summarize_scene(detections):
    names = [d["name"] for d in detections]
    has_box = "box" in names
    has_bag = "bag" in names
    has_label = "shipping_label" in names or "barcode" in names
    has_package = has_box or has_bag or has_label
    if has_box:
        item = "快递盒子"
        item_key = "box"
    elif has_bag:
        item = "快递袋子"
        item_key = "bag"
    elif has_label:
        item = "快递件"
        item_key = "package"
    else:
        item = ""
        item_key = ""
    orientation = "正面" if has_label else "反面" if has_package else ""
    return {
        "has_package": has_package,
        "item": item,
        "item_key": item_key,
        "orientation": orientation,
        "has_label": has_label,
        "detections": detections,
    }


def detect_scene(camera, vision, save_photo=False):
    if not vision.available():
        return {"has_package": False, "item": "", "orientation": "", "detections": []}, ""
    frame = camera.read()
    path = save_frame(frame) if save_photo else ""
    detections = vision.detect(frame)
    return summarize_scene(detections), path


def scene_sentence(scene):
    if not scene.get("has_package"):
        return "我暂时没有明显看到快递盒子或袋子。"
    text = f"我看到了{scene['item']}，并且它是{scene['orientation']}向上的。"
    if scene["orientation"] == "反面":
        text += "需要我帮你翻过来吗？"
    return text


def ask_moss(user_text, state, camera):
    try:
        with open("/root/.openclaw/openclaw.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        provider = cfg["models"]["providers"]["custom-gateway"]
        base_url = provider["baseUrl"].rstrip("/")
        api_key = provider["apiKey"]
        model = provider["models"][0]["id"]
    except Exception:
        return "这个问题有点复杂，但我现在连接不上本地大模型。"

    camera_status = "已打开" if camera.enabled else "未打开"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是RDK机器人上的物流识别分拣助手。"
                    "只用简短中文回答，不要输出思考过程，不要输出<think>标签。"
                    "回答尽量不超过60个字。"
                ),
            },
            {"role": "user", "content": f"摄像头{camera_status}。用户说：{user_text}"},
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
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return strip_thinking(data["choices"][0]["message"]["content"])
    except Exception:
        return "这个问题我暂时回答不了，可以先继续让我识别快递。"


def set_sort_rules_from_text(text, state):
    changed = []
    targets = {
        "左": "左边",
        "右": "右边",
        "前": "前方",
        "后": "后方",
    }
    item_words = {
        "box": ["快递盒", "盒子", "纸箱", "箱子"],
        "bag": ["快递袋", "袋子", "软包"],
    }
    for key, words in item_words.items():
        pos = min([text.find(w) for w in words if w in text] or [-1])
        if pos < 0:
            continue
        near = text[pos:pos + 14]
        for k, target in targets.items():
            if k in near:
                state.setdefault("sort_rules", {})[key] = target
                changed.append(("快递盒" if key == "box" else "快递袋", target))
                break
    return changed


def basic_dialogue(text):
    if contains_any(text, ["你好", "您好", "哈喽", "hello", "嗨"]):
        return "你好呀，很高兴见到你。"
    if contains_any(text, ["你是谁", "你是干什么", "你能做什么", "介绍一下你自己"]):
        return "我是RDK机器人，负责识别和分拣物流快递。"
    if contains_any(text, ["谁是最帅的男人", "最帅的男人是谁", "你觉得谁最帅"]):
        return "最帅的男人当然是然哥啦。"
    if contains_any(text, ["谢谢", "辛苦了"]):
        return "不客气，我会继续帮你盯着快递。"
    if contains_any(text, ["你好吗", "状态怎么样"]):
        return "我状态很好，麦克风正在监听，随时可以开始识别。"
    return ""


def is_yes(text):
    return contains_any(text, ["是", "要", "需要", "可以", "好", "好的", "帮我", "翻", "确认"])


def is_no(text):
    return contains_any(text, ["不用", "不要", "否", "算了", "先不"])


def is_camera_start(text):
    return contains_any(text, ["打开摄像头", "开启摄像头", "开始拍照", "开始识别", "开始检测", "打开视觉"])


def is_camera_stop(text):
    return contains_any(text, ["关闭摄像头", "停止拍照", "停止识别", "停止分拣", "退出分拣"])


def is_photo(text):
    return contains_any(text, ["拍照", "照相", "拍一张", "拍张照片"])


def is_see(text):
    return contains_any(text, ["你可以看见什么", "你看到了什么", "你能看到什么", "你眼前有什么", "看到什么", "看见什么"])


def is_sort_mode(text):
    return contains_any(text, ["进入快递分拣模式", "开始快递分拣", "进入分拣模式", "开始自动分拣"])


def auto_sort_tick(state, camera, vision):
    if not state.get("sorting_enabled"):
        return
    now = time.time()
    if now - float(state.get("last_auto_action_at", 0)) < 8:
        return
    try:
        scene, _ = detect_scene(camera, vision, save_photo=False)
        state["last_scene"] = scene
        state["last_auto_action_at"] = now
        save_state(state)
    except Exception as exc:
        log("自动识别失败：" + repr(exc))
        return

    if not scene.get("has_package"):
        return
    if scene.get("orientation") == "反面":
        send_robot_command("flip_package", item=scene.get("item", "快递件"), target="翻面")
        reply("检测到快递反面向上，我已发送自动翻面指令。")
        return

    item_key = scene.get("item_key")
    target = state.get("sort_rules", {}).get(item_key)
    if target:
        command = "sort_box" if item_key == "box" else "sort_bag" if item_key == "bag" else "sort_package"
        send_robot_command(command, item=scene.get("item", "快递件"), target=target)
        reply(f"检测到{scene.get('item')}正面向上，我会把它放到{target}。")


def handle_command(text, camera, vision):
    state = load_state()
    if not text:
        return True

    log("你说：" + text)

    if state.get("pending_flip"):
        if is_yes(text):
            send_robot_command("flip_package", item="快递件", target="翻面")
            state["pending_flip"] = False
            save_state(state)
            reply("好的，我已发送翻面指令。")
            return True
        if is_no(text):
            state["pending_flip"] = False
            save_state(state)
            reply("好的，那我先不翻面。")
            return True

    changed = set_sort_rules_from_text(text, state)
    if changed:
        save_state(state)
        reply("好的，我记住了：" + "，".join([f"{item}放{target}" for item, target in changed]) + "。")
        return True

    if contains_any(text, ["退出", "结束监听", "再见"]):
        reply("好的，我先停止监听。")
        camera.stop()
        return False

    if is_camera_stop(text):
        camera.stop()
        state["camera_enabled"] = False
        state["sorting_enabled"] = False
        state["pending_flip"] = False
        save_state(state)
        reply("好的，我已关闭摄像头并停止分拣。")
        return True

    if is_sort_mode(text):
        camera.start()
        state["camera_enabled"] = True
        state["sorting_enabled"] = True
        state["pending_flip"] = False
        save_state(state)
        reply("好的，已进入快递分拣模式。我会保持摄像头开启，自动识别并处理反面快递。")
        return True

    if is_camera_start(text):
        camera.start()
        state["camera_enabled"] = True
        save_state(state)
        reply("好的，摄像头已打开，我会保持开启并持续识别快递。")
        return True

    if is_photo(text):
        camera.start()
        frame = camera.read()
        path = save_frame(frame)
        state["camera_enabled"] = True
        state["last_photo"] = path
        save_state(state)
        reply("已拍照，照片保存在" + path + "。")
        return True

    if is_see(text) or contains_any(text, ["识别一下", "检测一下"]):
        camera.start()
        scene, path = detect_scene(camera, vision, save_photo=True)
        state["camera_enabled"] = True
        state["last_photo"] = path
        state["last_scene"] = scene
        state["pending_flip"] = scene.get("orientation") == "反面"
        save_state(state)
        reply(scene_sentence(scene))
        return True

    if contains_any(text, ["状态", "准备好了吗", "正常吗"]):
        cam = "已打开" if camera.enabled else "未打开"
        mode = "已进入" if state.get("sorting_enabled") else "未进入"
        reply(f"麦克风正在监听，摄像头{cam}，快递分拣模式{mode}。")
        return True

    answer = basic_dialogue(text)
    if answer:
        reply(answer)
        return True

    answer = ask_moss(text, state, camera)
    reply(answer)
    return True


def main():
    SetLogLevel(-1)
    os.makedirs(PHOTO_DIR, exist_ok=True)
    speech_model = Model(ASR_MODEL_DIR)
    camera = Camera(0)
    vision = Vision(PACKAGE_MODEL, PACKAGE_CLASSES)
    if vision.available():
        try:
            vision.load()
        except Exception as exc:
            log("快递模型加载失败：" + repr(exc))

    state = load_state()
    state["camera_enabled"] = False
    state["sorting_enabled"] = False
    state["pending_flip"] = False
    save_state(state)
    reply("系统已启动，我正在监听语音。你可以对我说你好，或者说打开摄像头。")

    while True:
        try:
            state = load_state()
            if state.get("camera_enabled") and not camera.enabled:
                camera.start()

            log("开始录音 5 秒，请说话...")
            record_audio(5)
            text = recognize_offline(AUDIO_FILE, speech_model)
            if not handle_command(text, camera, vision):
                break

            state = load_state()
            if state.get("camera_enabled") and not state.get("sorting_enabled"):
                try:
                    scene, _ = detect_scene(camera, vision, save_photo=False)
                    state["last_scene"] = scene
                    save_state(state)
                except Exception as exc:
                    log("持续识别失败：" + repr(exc))
            auto_sort_tick(state, camera, vision)
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

cmd = f"mkdir -p {REMOTE_DIR}"
stdin, stdout, stderr = client.exec_command(cmd, timeout=20)
stdout.channel.recv_exit_status()

sftp = client.open_sftp()
with sftp.file(REMOTE_SCRIPT, "w") as f:
    f.write(DAEMON)
sftp.close()

cmd = f"""set -e
chmod +x {REMOTE_SCRIPT}
python3 -m py_compile {REMOTE_SCRIPT}
systemctl restart voice-vision-assistant.service
sleep 8
systemctl --no-pager --full status voice-vision-assistant.service || true
journalctl -u voice-vision-assistant -n 35 --no-pager || true
"""

stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
out = stdout.read().decode(errors="replace")
err = stderr.read().decode(errors="replace")
if out:
    print(out)
if err:
    print("ERR:", err)
print("exit", stdout.channel.recv_exit_status())
client.close()
