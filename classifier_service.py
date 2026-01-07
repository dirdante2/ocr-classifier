# classifier_service.py
# Selbstlernender OCR + Bilderkennung Microservice (Version 2.0)

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.requests import Request
import traceback
import io
import hashlib
import uuid
from datetime import datetime
from PIL import Image
import pytesseract
import numpy as np
import cv2
import torch
from transformers import CLIPProcessor, CLIPModel

# Neue Module importieren
from config import config
from models.corner_detector import CornerDetector
from models.ocr_analyzer import OCRAnalyzer
from features.color_analyzer import ColorAnalyzer
from features.line_analyzer import LineAnalyzer
from database.ci4_client import ci4_client
from database.schemas import FeedbackRequest

app = FastAPI(title="Image Classification Service", version="2.0.0")

# ----------------------------
# GLOBAL ERROR HANDLER
# ----------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={
        "error": "Python exception",
        "type": type(exc).__name__,
        "message": str(exc),
        "traceback": traceback.format_exc()
    })

# ----------------------------
# INITIALIZE COMPONENTS
# ----------------------------
# CLIP Model
try:
    clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    MODEL_READY = True
except Exception as e:
    print(f"⚠️ CLIP model loading failed: {e}")
    clip_model = None
    processor = None
    MODEL_READY = False

# Component Instances
corner_detector = CornerDetector()
ocr_analyzer = OCRAnalyzer()
color_analyzer = ColorAnalyzer()
line_analyzer = LineAnalyzer()

LABELS = ["document", "photo", "device type plate"]

# ----------------------------
# HEALTH CHECK
# ----------------------------
@app.get("/health")
def health():
    """Health check endpoint."""
    ci4_status = "enabled" if ci4_client.enabled else "disabled"
    ci4_reachable = ci4_client.health_check() if ci4_client.enabled else None

    return {
        "status": "ok",
        "version": config.VERSION,
        "clip_model": "ready" if MODEL_READY else "not loaded",
        "ci4_integration": ci4_status,
        "ci4_reachable": ci4_reachable
    }

# ----------------------------
# CLIP CLASSIFICATION
# ----------------------------
def classify_clip(image: Image.Image):
    """Klassifiziert Bild mit CLIP."""
    if not MODEL_READY:
        return "unknown", 0.0

    inp = processor(text=LABELS, images=image, return_tensors="pt", padding=True)
    out = clip_model(**inp)
    prob = out.logits_per_image.softmax(dim=1)
    idx = prob.argmax().item()

    return LABELS[idx], float(prob[0][idx])

# ----------------------------
# TYPEPLATE LEGACY FEATURES
# ----------------------------
def detect_typeplate_legacy(image: Image.Image, text: str):
    """Legacy Typeplate-Detektion (für Kompatibilität)."""
    TYPEPLATE_KW = config.OCR_CONFIG["typeplate_keywords"]

    t = text.lower()
    digits = sum(c.isdigit() for c in t)
    digit_ratio = digits / max(len(t), 1)

    kw_hits = sum(1 for kw in TYPEPLATE_KW if kw in t)

    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 80, 200)
    line_density = np.sum(edges > 0) / (image.size[0] * image.size[1])

    score = digit_ratio * 2 + kw_hits * 0.7 + line_density * 600

    return score, digit_ratio, kw_hits, line_density

# ----------------------------
# MAIN CLASSIFICATION ENDPOINT
# ----------------------------
@app.post("/classify")
async def classify_image(file: UploadFile = File(...)):
    """
    Hauptklassifizierungs-Endpunkt.

    Neue Features:
    - 4-Eckpunkte-Erkennung
    - Verbesserte Arbeitsbericht-Erkennung (Keyword "Arbeitsbericht")
    - Farbuniformitäts-Analyse für Typenschilder
    - Gerade-Linien-Analyse
    - CI4-Integration (optional)
    """
    data = await file.read()
    if not data:
        raise ValueError("Leere Datei hochgeladen.")

    # Image laden
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img_array = np.array(img)

    # Image Hash für Deduplizierung
    image_hash = hashlib.sha256(data).hexdigest()

    # ----------------------------
    # 1. OCR ANALYSIS
    # ----------------------------
    ocr_result = ocr_analyzer.analyze(img)
    text = ocr_result["text"]
    text_len = ocr_result["text_length"]
    text_density = ocr_result["text_density"]

    # ----------------------------
    # 2. ARBEITSBERICHT DETECTION
    # ----------------------------
    ar_score, ar_debug = ocr_analyzer.detect_arbeitsbericht(text)

    # ----------------------------
    # 3. CLIP CLASSIFICATION
    # ----------------------------
    clip_label, clip_conf = classify_clip(img)

    # ----------------------------
    # 4. TYPEPLATE FEATURES (NEU)
    # ----------------------------
    typeplate_text_features = ocr_analyzer.analyze_typeplate_features(text)

    # Legacy features (Kompatibilität)
    legacy_score, dr, kw, ld = detect_typeplate_legacy(img, text)

    # Neue Features
    color_info = color_analyzer.analyze_color_uniformity(img)
    line_info = line_analyzer.analyze_straight_lines(img)

    # ----------------------------
    # 5. CORNER DETECTION (NEU)
    # ----------------------------
    corners = corner_detector.detect_4_corners(img_array)

    # ----------------------------
    # 6. SCORING CALCULATION
    # ----------------------------

    # Arbeitsbericht Score (UPDATED mit neuem System)
    AR = ar_score  # Bereits berechnet in ocr_analyzer

    # Typeplate Score (ENHANCED)
    TP = (
        (clip_label == "device type plate") * (clip_conf * config.WEIGHTS["TP"]["clip_factor"])
        + typeplate_text_features["keyword_count"] * config.WEIGHTS["TP"]["keyword_multiplier"]
        + (dr * config.WEIGHTS["TP"]["digit_ratio_factor"])
        + (ld * config.WEIGHTS["TP"]["line_density_factor"])
        + color_info["uniformity_score"] * config.WEIGHTS["TP"]["color_uniformity_factor"]  # NEU
        + line_info["line_score"] * config.WEIGHTS["TP"]["rect_score_factor"]  # NEU
    )

    # Document Score
    DOC = (
        (text_len / config.WEIGHTS["DOC"]["text_length_divisor"])
        + (clip_label == "document") * (clip_conf * config.WEIGHTS["DOC"]["clip_factor"])
    )

    # Photo Score
    PHOTO = (
        (text_len < config.WEIGHTS["PHOTO"]["low_text_threshold"]) * config.WEIGHTS["PHOTO"]["low_text_bonus"]
        + (kw == 0) * 1
        + (dr == 0) * 1
        + (clip_label == "photo") * (clip_conf * config.WEIGHTS["PHOTO"]["clip_factor"])
    )

    # ----------------------------
    # 7. CLASSIFICATION DECISION
    # ----------------------------
    if AR >= config.THRESHOLDS["arbeitsbericht"]:  # >= 5.0
        predicted = "arbeitsbericht"
        confidence = min(AR / 10.0, 0.95)

    elif TP > max(DOC, PHOTO) and TP >= config.THRESHOLDS["typeplate"]:
        predicted = "typeplate"
        confidence = min(TP / 15.0, 0.95)

    elif DOC > PHOTO and DOC >= config.THRESHOLDS["document"]:
        predicted = "document"
        confidence = min(DOC / 8.0, 0.95)

    else:
        predicted = "photo"
        confidence = 0.5

    # ----------------------------
    # 8. RESPONSE CONSTRUCTION
    # ----------------------------
    classification_id = str(uuid.uuid4())

    response = {
        "classification_id": classification_id,
        "predicted": predicted,
        "confidence": round(confidence, 3),
        "scores": {
            "AR": round(AR, 2),
            "TP": round(TP, 2),
            "DOC": round(DOC, 2),
            "PHOTO": round(PHOTO, 2)
        },
        "corners": corners,  # NEU
        "ocr": {
            "text_length": text_len,
            "density": round(text_density, 6),
            "word_count": ocr_result["word_count"],
            "line_count": ocr_result["line_count"],
            "raw_text": text[:500]  # Ersten 500 Zeichen
        },
        "clip": {
            "label": clip_label,
            "confidence": round(clip_conf, 3)
        },
        "arbeitsbericht_debug": ar_debug,  # NEU
        "typeplate_debug": {
            "legacy_score": round(legacy_score, 2),
            "digit_ratio": round(dr, 3),
            "keywords": kw,
            "line_density": round(ld, 6),
            "text_features": typeplate_text_features,
            "color_uniformity": color_info,  # NEU
            "line_analysis": line_info  # NEU
        },
        "model_version": config.VERSION
    }

    # ----------------------------
    # 9. CI4 INTEGRATION (optional)
    # ----------------------------
    if ci4_client.enabled:
        try:
            classification_data = {
                "classification_id": classification_id,
                "timestamp": datetime.now().isoformat(),
                "image_hash": f"sha256:{image_hash}",
                "prediction": {
                    "class": predicted,
                    "confidence": confidence,
                    "scores": response["scores"]
                },
                "features": {
                    "text_length": text_len,
                    "clip_label": clip_label,
                    "clip_confidence": clip_conf,
                    "color_uniformity": color_info["global_std"],
                    "has_rectangular_border": line_info["has_rectangular_border"],
                    "corner_detection_method": corners["detection_method"],
                    "arbeitsbericht_keyword": ar_debug["has_main_keyword"]
                },
                "model_version": config.VERSION,
                "weights_version": config.VERSION
            }

            ci4_client.store_classification(classification_data)

        except Exception as e:
            print(f"⚠️ CI4 storage failed: {e}")

    return response

# ----------------------------
# FEEDBACK ENDPOINT (NEU)
# ----------------------------
@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """
    Nimmt User-Feedback entgegen.

    Body:
    {
        "classification_id": "uuid",
        "corrected_class": "typeplate",
        "user_confidence": "high",
        "correction_reason": "...",
        "corrected_corners": [...]
    }
    """
    if not ci4_client.enabled:
        return {
            "status": "warning",
            "message": "CI4 integration disabled, feedback not stored"
        }

    try:
        feedback_data = {
            "timestamp": datetime.now().isoformat(),
            "user_correction": {
                "corrected_class": feedback.corrected_class,
                "confidence": feedback.user_confidence,
                "reason": feedback.correction_reason
            },
            "corrected_corners": feedback.corrected_corners
        }

        result = ci4_client.store_feedback(
            feedback.classification_id,
            feedback_data
        )

        if result:
            return {"status": "success", "message": "Feedback stored"}
        else:
            return {"status": "error", "message": "Failed to store feedback"}

    except Exception as e:
        return {
            "status": "error",
            "message": f"Feedback processing failed: {str(e)}"
        }

# ----------------------------
# STARTUP EVENT
# ----------------------------
@app.on_event("startup")
async def startup_event():
    """Initialisierung beim Start."""
    print("=" * 60)
    print("Image Classification Service v2.0")
    print("=" * 60)
    print(f"✓ Config loaded: {config.VERSION}")
    print(f"✓ CLIP Model: {'Ready' if MODEL_READY else 'Not loaded'}")
    print(f"✓ CI4 Integration: {'Enabled' if ci4_client.enabled else 'Disabled'}")
    print(f"✓ Corner Detection: Hybrid (Contour + Harris)")
    print(f"✓ Color Analysis: LAB-based uniformity")
    print(f"✓ Line Analysis: Hough transform")
    print("=" * 60)

    # Optional: Gewichte von CI4 laden
    if ci4_client.enabled:
        weights = ci4_client.get_model_weights()
        if weights:
            print("✓ Loaded weights from CI4")
            config.update_weights(weights.get("weights", {}))
            config.update_thresholds(weights.get("thresholds", {}))
