"""TFLite image classification for humidity (Teachable Machine style)."""

from pathlib import Path

import numpy as np
from PIL import Image

MODEL_DIR = Path(__file__).resolve().parent / "model"
MODEL_PATH = MODEL_DIR / "humidity_model.tflite"
LABELS_PATH = MODEL_DIR / "labels.txt"

HIGH_HUMIDITY_KEYWORDS = ("high", "رطوبة", "humid", "wet", "moist")


def _load_labels():
    if not LABELS_PATH.is_file():
        return []
    lines = LABELS_PATH.read_text(encoding="utf-8").strip().splitlines()
    return [ln.strip() for ln in lines if ln.strip()]


def run_inference(image_path: str) -> dict:
    """
    Load model/humidity_model.tflite, resize to 224x224, normalize, run inference.

    Returns dict with keys: ok (bool), label (str), confidence (float),
    high_humidity (bool), message (str).
    """
    path = Path(image_path)
    if not path.is_file():
        return {
            "ok": False,
            "label": "",
            "confidence": 0.0,
            "high_humidity": False,
            "message": "ملف الصورة غير موجود.",
        }

    labels = _load_labels()

    if not MODEL_PATH.is_file():
        return {
            "ok": False,
            "label": labels[0] if labels else "unknown",
            "confidence": 0.0,
            "high_humidity": False,
            "message": "النموذج غير موجود. ضع humidity_model.tflite في مجلد model/",
        }

    try:
        import tflite_runtime.interpreter as tflite
    except ImportError:
        try:
            import tensorflow.lite as tflite  # type: ignore
        except ImportError:
            return {
                "ok": False,
                "label": "",
                "confidence": 0.0,
                "high_humidity": False,
                "message": "تعذر تحميل tflite (ثبّت tflite-runtime أو tensorflow).",
            }

    interpreter = tflite.Interpreter(model_path=str(MODEL_PATH))
    interpreter.allocate_tensors()
    in_det = interpreter.get_input_details()[0]
    out_det = interpreter.get_output_details()[0]

    shape = tuple(int(x) for x in in_det["shape"])
    if len(shape) == 4:
        _, h, w, _ = shape
    else:
        h, w = 224, 224

    img = Image.open(path).convert("RGB").resize((w, h), Image.Resampling.BILINEAR)
    arr = np.asarray(img, dtype=np.float32)

    if in_det["dtype"] == np.uint8:
        scale, zero_point = in_det["quantization"]
        if scale:
            arr = arr / 255.0
            arr = arr / scale + zero_point
        arr = np.clip(np.round(arr), 0, 255).astype(np.uint8)
    else:
        arr = arr / 255.0

    batch = np.expand_dims(arr, axis=0)
    if batch.shape != shape:
        batch = np.reshape(batch, shape)

    interpreter.set_tensor(in_det["index"], batch)
    interpreter.invoke()
    out = interpreter.get_tensor(out_det["index"])[0].astype(np.float32)

    if np.max(out) > 1.5 or np.sum(out) > 1.5:
        e = np.exp(out - np.max(out))
        out = e / (np.sum(e) + 1e-8)

    idx = int(np.argmax(out))
    conf = float(out[idx])
    label = labels[idx] if idx < len(labels) else f"class_{idx}"

    low = label.lower()
    high = any(kw.lower() in low for kw in HIGH_HUMIDITY_KEYWORDS)
    if not high and len(labels) >= 2 and idx == len(labels) - 1:
        high = True

    if high:
        msg = "الرطوبة عالية، الغرفة تحتاج تهوية فورية"
    else:
        msg = f"{label} — ثقة {conf * 100:.1f}%"

    return {
        "ok": True,
        "label": label,
        "confidence": conf,
        "high_humidity": high,
        "message": msg,
    }
