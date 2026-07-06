from pathlib import Path

DATASET = Path(r"E:\rdk_material_dataset")
classes = [line.strip() for line in (DATASET / "classes.txt").read_text().splitlines() if line.strip()]

yaml_lines = [
    "path: E:/rdk_material_dataset",
    "train: images/train",
    "val: images/train",
    "",
    "names:",
]
for idx, name in enumerate(classes):
    yaml_lines.append(f"  {idx}: {name}")

(DATASET / "data.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")
print(DATASET / "data.yaml")
