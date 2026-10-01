"""Span-preserving baseline and optional pretrained multilingual semantic candidate."""

from __future__ import annotations

import os
import re
import resource
import threading
import time
from pathlib import Path

from .baseline import _context_flags
from .baseline import extract_profile as lexical_extract

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
_lock = threading.Lock()
PROTOTYPES = {
    "activity": "The patient describes dressing, bathing, cooking or work activities.",
    "priority": "The patient wants to achieve a personally important activity and states a preference.",
    "support": "Family or other people provide help with activities.",
    "environment": "The room has a chair, floor rug, desk, doorway or other physical features.",
    "symptom": "The patient describes pain, weakness or fatigue affecting participation.",
    "goal": "The student proposes a measurable functional goal over a defined period.",
}


def extract_profile(text: str, mode: str = "baseline") -> dict:
    if mode == "baseline":
        return lexical_extract(text)
    if mode != "neural":
        raise ValueError("NLP_MODE must be baseline or neural")
    if len(text) > 30000:
        raise ValueError("Profile exceeds 30000 characters")
    started = time.monotonic()
    try:
        import torch
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "Neural NLP dependencies are missing; no neural result was fabricated"
        ) from exc
    clauses = [
        (m.start(), m.end(), m.group())
        for m in re.finditer(r"[^.!?;\n۔؟]+", text)
        if m.group().strip()
    ][:40]
    if not clauses:
        return {
            "entities": [],
            "mode": "pretrained_multilingual_encoder",
            "inference_executed": False,
            "reason": "No nonempty clauses to encode",
        }
    with _lock:
        torch.set_num_threads(max(1, int(os.environ.get("MODEL_CPU_THREADS", "2"))))
        from services.api.config import get_settings

        model = SentenceTransformer(
            MODEL,
            revision=REVISION,
            device="cpu",
            cache_folder=str(Path(get_settings().model_cache_path) / "huggingface"),
            trust_remote_code=False,
            model_kwargs={"use_safetensors": True},
        )
        labels = list(PROTOTYPES)
        vectors = model.encode(
            [c[2] for c in clauses] + list(PROTOTYPES.values()),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        similarities = vectors[: len(clauses)] @ vectors[len(clauses) :].T
        entities = []
        for (start, end, clause), scores in zip(clauses, similarities, strict=True):
            label_index = int(scores.argmax())
            confidence = float(scores[label_index])
            if confidence < 0.32:
                continue
            while start < end and text[start].isspace():
                start += 1
            while end > start and text[end - 1].isspace():
                end -= 1
            negated, uncertain = _context_flags(text, start, end)
            entities.append(
                {
                    "label": labels[label_index],
                    "text": text[start:end],
                    "start": start,
                    "end": end,
                    "negated": negated,
                    "uncertain": uncertain,
                    "similarity": round(confidence, 4),
                }
            )
        del model
    return {
        "entities": entities,
        "mode": "pretrained_multilingual_encoder",
        "inference_executed": True,
        "provenance": {
            "model": MODEL,
            "revision": REVISION,
            "license": "Apache-2.0",
            "task": "nearest-prototype sentence classification, not trained OT extraction",
            "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
            "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "threshold": 0.32,
        },
        "limitations": "Similarity is not a calibrated probability. Prototype taxonomy and threshold are unvalidated; Urdu/Roman Urdu quality requires educator-labelled evaluation. Source clause offsets are preserved.",
    }
