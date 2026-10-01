"""Optional actual pretrained SSDLite inference, separate from case annotations."""

from __future__ import annotations

import hashlib
import io
import os
import resource
import threading
import time
from pathlib import Path

from PIL import Image, ImageOps

_lock = threading.Lock()


def _read_image(path: Path) -> Image.Image:
    if path.suffix.lower() == ".svg":
        root = Path(__file__).resolve().parents[1]
        if path.resolve().parent != (root / "data/demo/assets").resolve():
            raise ValueError("Only authored repository SVGs may be rasterized")
        # Safe: no uploaded SVG/XML is admitted; only fixed original demo assets.
        import cairosvg

        image = Image.open(
            io.BytesIO(cairosvg.svg2png(url=str(path), output_width=1000, output_height=650))
        )
    else:
        image = Image.open(path)
    if image.width * image.height > 12000000:
        raise ValueError("Image exceeds 12 megapixel inference limit")
    return ImageOps.exif_transpose(image).convert("RGB")


def analyze_asset(path: str | Path, mode: str = "baseline", threshold: float = 0.5) -> dict:
    if mode in {"baseline", "reference_only"}:
        return {
            "mode": "reference_only",
            "predictions": [],
            "review_status": "provisional",
            "provenance": {
                "inference_executed": False,
                "reason": "Neural inference is not configured. Authored annotations are supplied separately and require educator review.",
            },
        }
    if mode != "neural":
        raise ValueError("CV_MODE must be baseline or neural")
    if not 0 < threshold < 1:
        raise ValueError("Confidence threshold must be between 0 and 1")
    path = Path(path)
    started = time.monotonic()
    try:
        import torch
        from torchvision.models.detection import (
            SSDLite320_MobileNet_V3_Large_Weights,
            ssdlite320_mobilenet_v3_large,
        )
    except ImportError as exc:
        raise RuntimeError(
            "Neural CV dependencies are missing; no detector result was fabricated"
        ) from exc
    # Serialize CPU inference within each process and release weights after use.
    with _lock:
        torch.set_num_threads(max(1, int(os.environ.get("MODEL_CPU_THREADS", "2"))))
        from services.api.config import get_settings

        cache = Path(get_settings().model_cache_path)
        torch.hub.set_dir(str(cache / "torch"))
        weights = SSDLite320_MobileNet_V3_Large_Weights.COCO_V1
        image = _read_image(path)
        model = ssdlite320_mobilenet_v3_large(weights=weights, progress=False).eval()
        with torch.inference_mode():
            prediction = model([weights.transforms()(image)])[0]
        predictions = [
            {
                "label": weights.meta["categories"][int(label)],
                "confidence": round(float(score), 5),
                "box": [round(float(v), 2) for v in box],
            }
            for box, label, score in zip(
                prediction["boxes"], prediction["labels"], prediction["scores"], strict=True
            )
            if float(score) >= threshold
        ]
        weight_file = cache / "torch/checkpoints" / Path(weights.url).name
        weight_hash = (
            hashlib.sha256(weight_file.read_bytes()).hexdigest() if weight_file.exists() else None
        )
        del model
    return {
        "mode": "pretrained_ssdlite",
        "predictions": predictions[:30],
        "width": image.width,
        "height": image.height,
        "coordinate_system": "pixel_xyxy",
        "review_status": "provisional",
        "provenance": {
            "inference_executed": True,
            "model": "torchvision/ssdlite320_mobilenet_v3_large",
            "revision": "COCO_V1",
            "weights_url": weights.url,
            "weights_sha256": weight_hash,
            "torch": torch.__version__,
            "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "threshold": threshold,
            "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
            "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "limitations": "COCO detector; predictions do not establish barriers, suitability, safety, or diagnosis. Authored schematics differ from the photographic training domain. No local accuracy evaluation is claimed.",
        },
    }
