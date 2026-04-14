"""TFLite image classification — Teachable Machine water-quality style (camera + شرائح)."""

from pathlib import Path

import numpy as np
from PIL import Image

MODEL_DIR = Path(__file__).resolve().parent / "model"
LABELS_PATH = MODEL_DIR / "labels.txt"

# Prefer new export name; fall back to older humidity demo filename.
def _resolve_model_path() -> Path:
    for name in ("water_quality_model.tflite", "humidity_model.tflite"):
        p = MODEL_DIR / name
        if p.is_file():
            return p
    return MODEL_DIR / "water_quality_model.tflite"


def _load_labels():
    if not LABELS_PATH.is_file():
        return []
    lines = LABELS_PATH.read_text(encoding="utf-8").strip().splitlines()
    return [ln.strip() for ln in lines if ln.strip()]


def run_inference(image_path: str) -> dict:
    """
    Load TFLite model from model/, resize to input size (غالباً 224×224), normalize, run.

    Returns dict with keys: ok, label, confidence, alert (bool), high_humidity (bool, legacy),
    message (str). «alert» يعني أن التنبُّه منطقي عند ثقة كافية (جميع فئات النموذج الحالي
    تمثّل مؤشرات تلوث/مكوّنات في الشرائح).
    """
    path = Path(image_path)
    if not path.is_file():
        return {
            "ok": False,
            "label": "",
            "confidence": 0.0,
            "alert": False,
            "high_humidity": False,
            "message": "ملف الصورة غير موجود.",
        }

    labels = _load_labels()

    mp = _resolve_model_path()
    if not mp.is_file():
        return {
            "ok": False,
            "label": labels[0] if labels else "unknown",
            "confidence": 0.0,
            "alert": False,
            "high_humidity": False,
            "message": "النموذج غير موجود. ضع water_quality_model.tflite أو humidity_model.tflite في model/",
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
                "alert": False,
                "high_humidity": False,
                "message": "تعذر تحميل tflite (ثبّت tflite-runtime أو tensorflow).",
            }

    interpreter = tflite.Interpreter(model_path=str(mp))
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

    # نموذج الشرائح: كل الفئات مؤشرات مكوّنات/تلوث؛ التنبيه يُقيَّد بالثقة في main.py
    alert = True

    msg = f"{label} — ثقة {conf * 100:.1f}%"

    return {
        "ok": True,
        "label": label,
        "confidence": conf,
        "alert": alert,
        "high_humidity": alert,
        "message": msg,
    }
