import os
import io
import base64
import logging
import tempfile
from pathlib import Path
from typing import Optional

from PIL import Image

from app.services.gradcam_service import VisualExplainer
from app.services.ocr_service import OCRService
from app.services.brand_detector import BrandDetector
from app.services.visual_risk_analyzer import visual_risk_analyzer

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {
    b'\xff\xd8\xff': 'jpeg',
    b'\x89PNG\r\n\x1a\n': 'png',
    b'GIF87a': 'gif',
    b'GIF89a': 'gif',
    b'BM': 'bmp',
    b'RIFF': 'webp',
}

MAX_IMAGE_SIZE_MB = 20
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024


def _detect_format(contents: bytes) -> Optional[str]:
    for magic, fmt in SUPPORTED_FORMATS.items():
        if contents.startswith(magic):
            if fmt == 'webp' and not contents.startswith(b'RIFF....WEBP'):
                continue
            return fmt
    return None


class PipelineError(Exception):
    pass


class ImageValidationError(PipelineError):
    pass


class CNNFailure(PipelineError):
    pass


class VisualPipeline:
    """Orchestrates the complete visual analysis pipeline.

    Flow: Image Validation -> CNN + Grad-CAM -> OCR -> Brand Detection -> Visual Risk Analyzer
    """

    def __init__(self, model_path: str):
        self.model_path = model_path
        self._explainer: Optional[VisualExplainer] = None
        self._ocr: Optional[OCRService] = None
        self._brand: Optional[BrandDetector] = None

    # ── Lazy initializers ────────────────────────────────────────────

    def _get_explainer(self) -> VisualExplainer:
        if self._explainer is None:
            self._explainer = VisualExplainer(self.model_path)
        return self._explainer

    def _get_ocr(self) -> OCRService:
        if self._ocr is None:
            self._ocr = OCRService()
        return self._ocr

    def _get_brand(self) -> BrandDetector:
        if self._brand is None:
            self._brand = BrandDetector()
        return self._brand

    # ── Image validation ─────────────────────────────────────────────

    def validate_image(self, contents: bytes) -> dict:
        if not contents or len(contents) == 0:
            raise ImageValidationError("Uploaded file is empty")

        if len(contents) > MAX_IMAGE_SIZE_BYTES:
            raise ImageValidationError(
                f"Image exceeds maximum size of {MAX_IMAGE_SIZE_MB}MB "
                f"(got {len(contents) / 1024 / 1024:.1f}MB)"
            )

        fmt = _detect_format(contents)
        if fmt is None:
            raise ImageValidationError(
                "Unsupported image format. Supported: JPEG, PNG, GIF, BMP, WEBP"
            )

        try:
            img = Image.open(io.BytesIO(contents))
            img.verify()
        except Exception as e:
            raise ImageValidationError(f"Corrupted or invalid image: {e}")

        return {"format": fmt, "size_bytes": len(contents), "valid": True}

    # ── Core pipeline ────────────────────────────────────────────────

    def run(self, image_path: str) -> dict:
        """Run the full visual analysis pipeline on an image file.

        Args:
            image_path: Path to the image file on disk.

        Returns:
            dict with keys: prediction, confidence, risk_score, risk_level,
                cnn, gradcam, ocr, brand_detection, visual_risk, explanation
        """
        cnn_result = None
        gradcam_result = None
        ocr_result = None
        brand_result = None
        risk_result = None
        errors = {}

        # ── 1. CNN Prediction + Grad-CAM ─────────────────────────────
        try:
            explainer = self._get_explainer()
            gradcam_result = explainer.explain(image_path)
            if gradcam_result is None:
                raise CNNFailure("Grad-CAM generation returned None")
            cnn_result = {
                "prediction": "Phishing" if gradcam_result["label"] == "phishing" else "Legitimate",
                "confidence": round(gradcam_result["confidence"] * 100, 1),
                "phishing_probability": gradcam_result["phishing_probability"],
            }
        except Exception as e:
            logger.error(f"[Pipeline] CNN/Grad-CAM failed: {e}")
            errors["cnn"] = str(e)
            cnn_result = {"prediction": "Error", "confidence": 0.0, "phishing_probability": 0.0}

        # ── 2. OCR ──────────────────────────────────────────────────
        try:
            ocr = self._get_ocr()
            raw_ocr = ocr.analyze(image_path)
            ocr_result = {
                "text": raw_ocr["extracted_text"],
                "keywords": raw_ocr["keywords"],
                "keyword_count": raw_ocr["keyword_count"],
                "risk_score": raw_ocr["risk_score"],
            }
        except Exception as e:
            logger.warning(f"[Pipeline] OCR failed: {e}")
            errors["ocr"] = str(e)
            ocr_result = {"text": "", "keywords": [], "keyword_count": 0, "risk_score": "Low"}

        # ── 3. Brand Detection ──────────────────────────────────────
        try:
            brand = self._get_brand()
            raw_brand = brand.detect_brands(image_path)
            brand_result = {
                "brands": [b["brand"] for b in raw_brand.get("brands", [])],
                "brand_count": raw_brand["brand_count"],
                "confidence": [b["confidence"] for b in raw_brand.get("brands", [])],
                "risk_score": raw_brand["risk_score"],
            }
        except Exception as e:
            logger.warning(f"[Pipeline] Brand detection failed: {e}")
            errors["brand"] = str(e)
            brand_result = {"brands": [], "brand_count": 0, "confidence": [], "risk_score": "Low"}

        # ── 4. Visual Risk Analyzer ─────────────────────────────────
        try:
            risk_result = visual_risk_analyzer.analyze(
                cnn_label=gradcam_result["label"] if gradcam_result else "legitimate",
                cnn_confidence=gradcam_result["confidence"] if gradcam_result else 0.0,
                cnn_phishing_prob=gradcam_result["phishing_probability"] if gradcam_result else 0.0,
                ocr_risk=ocr_result["risk_score"],
                ocr_keywords=ocr_result["keywords"],
                ocr_keyword_count=ocr_result["keyword_count"],
                brand_brands=brand_result["brands"],
                brand_confidence=brand_result["confidence"],
                brand_count=brand_result["brand_count"],
                brand_risk=brand_result["risk_score"],
            )
        except Exception as e:
            logger.error(f"[Pipeline] Visual risk analysis failed: {e}")
            errors["visual_risk"] = str(e)
            risk_result = {
                "score": 0.0,
                "decision": "Error",
                "risk_level": "Unknown",
                "explanation": ["Risk analysis failed"],
            }

        # ── 5. Grad-CAM image (base64) ──────────────────────────────
        gradcam_image = None
        if gradcam_result and gradcam_result.get("overlay"):
            gradcam_image = base64.b64encode(gradcam_result["overlay"]).decode("utf-8")

        # ── 6. Assemble final response ──────────────────────────────
        final_prediction = risk_result["decision"]
        final_confidence = cnn_result["confidence"]

        response = {
            "prediction": final_prediction,
            "confidence": final_confidence,
            "risk_score": risk_result["score"],
            "risk_level": risk_result["risk_level"],
            "cnn": cnn_result,
            "ocr": ocr_result,
            "brand_detection": brand_result,
            "gradcam": {"image": gradcam_image},
            "visual_risk": {
                "score": risk_result["score"],
                "decision": risk_result["decision"],
                "confidence": final_confidence,
            },
            "explanation": risk_result.get("explanation", []),
        }

        if errors:
            response["warnings"] = errors

        return response

    def run_from_bytes(self, contents: bytes, filename: str = "upload.png") -> dict:
        """Validate and run the pipeline from raw byte content."""
        self.validate_image(contents)

        suffix = Path(filename).suffix or ".png"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(contents)
            temp_path = tmp.name

        try:
            return self.run(temp_path)
        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass
