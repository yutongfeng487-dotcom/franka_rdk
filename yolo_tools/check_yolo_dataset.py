from pathlib import Path


DATASET = Path(r"E:\rdk_material_dataset")
CLASSES = [line.strip() for line in (DATASET / "classes.txt").read_text().splitlines() if line.strip()]
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}


def check_split(split):
    image_dir = DATASET / "images" / split
    label_dir = DATASET / "labels" / split
    images = sorted(p for p in image_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    labels = sorted(p for p in label_dir.glob("*.txt") if p.name != "classes.txt")
    missing = []
    empty = []
    bad = []

    for image in images:
        label = label_dir / f"{image.stem}.txt"
        if not label.exists():
            missing.append(image.name)
            continue
        text = label.read_text(encoding="utf-8").strip()
        if not text:
            empty.append(label.name)
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            parts = line.split()
            if len(parts) != 5:
                bad.append(f"{label.name}:{line_no}: expected 5 fields, got {len(parts)}")
                continue
            try:
                cls = int(parts[0])
                nums = [float(x) for x in parts[1:]]
            except ValueError:
                bad.append(f"{label.name}:{line_no}: non-numeric value")
                continue
            if cls < 0 or cls >= len(CLASSES):
                bad.append(f"{label.name}:{line_no}: class id {cls} outside 0..{len(CLASSES)-1}")
            if any(x < 0 or x > 1 for x in nums):
                bad.append(f"{label.name}:{line_no}: bbox value outside 0..1")

    extra = [label.name for label in labels if not any((image_dir / f"{label.stem}{ext}").exists() for ext in IMAGE_EXTS)]
    return {
        "split": split,
        "images": len(images),
        "labels": len(labels),
        "missing": missing,
        "empty": empty,
        "bad": bad,
        "extra": extra,
    }


print("classes:", CLASSES)
for split in ["train", "val"]:
    result = check_split(split)
    print(f"\n[{split}] images={result['images']} labels={result['labels']}")
    for key in ["missing", "empty", "bad", "extra"]:
        items = result[key]
        print(f"{key}: {len(items)}")
        for item in items[:20]:
            print(" -", item)
