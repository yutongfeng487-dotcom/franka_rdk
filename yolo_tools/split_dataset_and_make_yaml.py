from pathlib import Path
import random
import shutil


DATASET = Path(r"E:\rdk_material_dataset")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}
random.seed(42)

classes = [line.strip() for line in (DATASET / "classes.txt").read_text().splitlines() if line.strip()]

train_img = DATASET / "images" / "train"
val_img = DATASET / "images" / "val"
train_lbl = DATASET / "labels" / "train"
val_lbl = DATASET / "labels" / "val"
val_img.mkdir(parents=True, exist_ok=True)
val_lbl.mkdir(parents=True, exist_ok=True)

stray_classes = train_lbl / "classes.txt"
if stray_classes.exists():
    try:
        stray_classes.unlink()
    except PermissionError:
        print(f"skip_locked={stray_classes}")

images = sorted(p for p in train_img.iterdir() if p.suffix.lower() in IMAGE_EXTS)
val_count = max(1, round(len(images) * 0.2)) if len(images) >= 5 else 0
selected = set(random.sample(images, val_count)) if val_count else set()

for image in selected:
    label = train_lbl / f"{image.stem}.txt"
    shutil.move(str(image), str(val_img / image.name))
    if label.exists():
        shutil.move(str(label), str(val_lbl / label.name))

yaml_lines = [
    "path: E:/rdk_material_dataset",
    "train: images/train",
    "val: images/val",
    "",
    "names:",
]
for idx, name in enumerate(classes):
    yaml_lines.append(f"  {idx}: {name}")

(DATASET / "data.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

print(f"moved_to_val={len(selected)}")
print(f"train_images={len(list(train_img.glob('*')))}")
print(f"val_images={len(list(val_img.glob('*')))}")
print(f"wrote={DATASET / 'data.yaml'}")
