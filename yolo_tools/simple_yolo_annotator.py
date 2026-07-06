import json
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageTk


DATASET = Path(r"E:\rdk_package_dataset")
IMAGE_DIR = DATASET / "images" / "train"
LABEL_DIR = DATASET / "labels" / "train"
CLASSES = ["box", "bag", "shipping_label", "barcode"]
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}


class Annotator:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple YOLO Annotator - RDK Dataset")
        self.root.geometry("1200x820")

        LABEL_DIR.mkdir(parents=True, exist_ok=True)
        self.images = sorted(p for p in IMAGE_DIR.iterdir() if p.suffix.lower() in IMAGE_EXTS)
        if not self.images:
            messagebox.showerror("No images", f"No images found in {IMAGE_DIR}")
            root.destroy()
            return

        self.index = 0
        self.current_class = 0
        self.boxes = []
        self.drag_start = None
        self.temp_rect = None
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.image = None
        self.tk_image = None

        top = tk.Frame(root)
        top.pack(side=tk.TOP, fill=tk.X)

        self.status = tk.Label(top, text="", anchor="w", font=("Arial", 11))
        self.status.pack(side=tk.LEFT, padx=8, pady=6, fill=tk.X, expand=True)

        tk.Button(top, text="Prev (Left)", command=self.prev_image).pack(side=tk.RIGHT, padx=4)
        tk.Button(top, text="Next (Right)", command=self.next_image).pack(side=tk.RIGHT, padx=4)
        tk.Button(top, text="Save (Ctrl+S)", command=self.save_labels).pack(side=tk.RIGHT, padx=4)
        tk.Button(top, text="Undo (U)", command=self.undo_box).pack(side=tk.RIGHT, padx=4)

        self.canvas = tk.Canvas(root, bg="#222")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        key_help = ", ".join(f"{i + 1}={name}" for i, name in enumerate(CLASSES))
        self.help = tk.Label(
            root,
            text=f"Keys: {key_help}, drag=draw box, Ctrl+S=save, U=undo, Left/Right=switch image",
            anchor="w",
        )
        self.help.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.root.bind("<Control-s>", lambda event: self.save_labels())
        self.root.bind("<Left>", lambda event: self.prev_image())
        self.root.bind("<Right>", lambda event: self.next_image())
        self.root.bind("u", lambda event: self.undo_box())
        self.root.bind("U", lambda event: self.undo_box())
        for i in range(min(len(CLASSES), 9)):
            self.root.bind(str(i + 1), lambda event, cls=i: self.set_class(cls))
        self.root.bind("<Configure>", self.on_resize)

        self.root.after(100, self.load_image)

    def label_path(self):
        return LABEL_DIR / f"{self.images[self.index].stem}.txt"

    def load_image(self):
        self.image = Image.open(self.images[self.index]).convert("RGB")
        self.boxes = self.load_existing_labels()
        self.redraw()

    def load_existing_labels(self):
        path = self.label_path()
        if not path.exists():
            return []
        boxes = []
        width, height = self.image.size
        for line in path.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split()
            if len(parts) != 5:
                continue
            cls, xc, yc, bw, bh = int(parts[0]), *map(float, parts[1:])
            x1 = (xc - bw / 2) * width
            y1 = (yc - bh / 2) * height
            x2 = (xc + bw / 2) * width
            y2 = (yc + bh / 2) * height
            boxes.append({"class": cls, "box": [x1, y1, x2, y2]})
        return boxes

    def redraw(self):
        if self.canvas.winfo_width() <= 1 or self.canvas.winfo_height() <= 1:
            self.root.after(100, self.redraw)
            return
        self.canvas.delete("all")
        canvas_w = max(1, self.canvas.winfo_width())
        canvas_h = max(1, self.canvas.winfo_height())
        img_w, img_h = self.image.size
        self.scale = min(canvas_w / img_w, canvas_h / img_h, 1.0)
        disp_w = int(img_w * self.scale)
        disp_h = int(img_h * self.scale)
        self.offset_x = (canvas_w - disp_w) // 2
        self.offset_y = (canvas_h - disp_h) // 2

        resized = self.image.resize((disp_w, disp_h), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized)
        self.canvas.create_image(self.offset_x, self.offset_y, anchor=tk.NW, image=self.tk_image)

        for item in self.boxes:
            self.draw_box(item["box"], item["class"])

        cls_name = CLASSES[self.current_class]
        self.status.config(
            text=f"{self.index + 1}/{len(self.images)}  {self.images[self.index].name}  "
            f"class={self.current_class}:{cls_name}  boxes={len(self.boxes)}"
        )

    def to_image_xy(self, x, y):
        ix = (x - self.offset_x) / self.scale
        iy = (y - self.offset_y) / self.scale
        w, h = self.image.size
        return max(0, min(w, ix)), max(0, min(h, iy))

    def to_canvas_box(self, box):
        x1, y1, x2, y2 = box
        return (
            self.offset_x + x1 * self.scale,
            self.offset_y + y1 * self.scale,
            self.offset_x + x2 * self.scale,
            self.offset_y + y2 * self.scale,
        )

    def draw_box(self, box, cls):
        x1, y1, x2, y2 = self.to_canvas_box(box)
        colors = ["#00d084", "#3b82f6", "#f59e0b", "#ef4444", "#a855f7", "#14b8a6"]
        color = colors[cls % len(colors)]
        self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=2)
        self.canvas.create_text(
            x1 + 4,
            max(10, y1 - 10),
            anchor=tk.W,
            text=CLASSES[cls],
            fill=color,
            font=("Arial", 12, "bold"),
        )

    def on_press(self, event):
        self.drag_start = self.to_image_xy(event.x, event.y)
        if self.temp_rect:
            self.canvas.delete(self.temp_rect)
            self.temp_rect = None

    def on_drag(self, event):
        if not self.drag_start:
            return
        x1, y1 = self.drag_start
        x2, y2 = self.to_image_xy(event.x, event.y)
        cbox = self.to_canvas_box([x1, y1, x2, y2])
        if self.temp_rect:
            self.canvas.coords(self.temp_rect, *cbox)
        else:
            self.temp_rect = self.canvas.create_rectangle(*cbox, outline="#ffcc00", width=2)

    def on_release(self, event):
        if not self.drag_start:
            return
        x1, y1 = self.drag_start
        x2, y2 = self.to_image_xy(event.x, event.y)
        self.drag_start = None
        if self.temp_rect:
            self.canvas.delete(self.temp_rect)
            self.temp_rect = None
        x1, x2 = sorted([x1, x2])
        y1, y2 = sorted([y1, y2])
        if (x2 - x1) < 5 or (y2 - y1) < 5:
            return
        self.boxes.append({"class": self.current_class, "box": [x1, y1, x2, y2]})
        self.redraw()

    def set_class(self, cls):
        self.current_class = cls
        self.redraw()

    def undo_box(self):
        if self.boxes:
            self.boxes.pop()
            self.redraw()

    def save_labels(self):
        width, height = self.image.size
        lines = []
        for item in self.boxes:
            x1, y1, x2, y2 = item["box"]
            xc = ((x1 + x2) / 2) / width
            yc = ((y1 + y2) / 2) / height
            bw = (x2 - x1) / width
            bh = (y2 - y1) / height
            lines.append(f"{item['class']} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
        self.label_path().write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        self.status.config(text=f"Saved {self.label_path()}")

    def next_image(self):
        self.save_labels()
        self.index = min(len(self.images) - 1, self.index + 1)
        self.load_image()

    def prev_image(self):
        self.save_labels()
        self.index = max(0, self.index - 1)
        self.load_image()

    def on_resize(self, event):
        if self.image and event.widget == self.root:
            self.root.after_idle(self.redraw)


if __name__ == "__main__":
    root = tk.Tk()
    app = Annotator(root)
    root.mainloop()
