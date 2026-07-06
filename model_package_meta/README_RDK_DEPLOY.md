# RDK YOLO Model Package

This folder contains the ONNX model and label files for RDK X5.

## Files

- `package_sort_best.onnx`: YOLO detection model exported to ONNX.
- `classes.txt`: class names in model output order.
- `model_info.json`: model metadata and suggested sorting logic.

## Class Order

```text
0 box
1 bag
2 shipping_label
3 barcode
```

Do not change this order unless the model is retrained with a different class order.

## Suggested Logic

```text
If voice command says left:
    put current package left
If voice command says right:
    put current package right
Else if object is bag:
    put left
Else if object is box and shipping_label/barcode is visible:
    put right
Else if object is box and shipping_label/barcode is not visible:
    flip package and detect again
```

## Copy To RDK

Upload `package_sort_best.onnx` and `classes.txt` to the RDK model folder, for example:

```bash
/root/voice_photo/vision_models/package_sort_best.onnx
/root/voice_photo/vision_models/classes.txt
```

Then restart the RDK service if your program is running as a service:

```bash
systemctl restart voice-vision-assistant.service
```
