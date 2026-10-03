import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from PIL import Image

from app.services.visual_pipeline import (
    VisualPipeline,
    ImageValidationError,
    PipelineError,
    _detect_format,
    MAX_IMAGE_SIZE_BYTES,
)


# ─── Unit: _detect_format ─────────────────────────────────────────────

class TestDetectFormat:
    def test_jpeg(self):
        assert _detect_format(b'\xff\xd8\xff\xe0') == 'jpeg'

    def test_png(self):
        assert _detect_format(b'\x89PNG\r\n\x1a\n') == 'png'

    def test_gif(self):
        assert _detect_format(b'GIF89a') == 'gif'

    def test_bmp(self):
        assert _detect_format(b'BM\x00\x00') == 'bmp'

    def test_unknown(self):
        assert _detect_format(b'\x00\x01\x02\x03') is None

    def test_empty(self):
        assert _detect_format(b'') is None


# ─── Unit: Image validation ───────────────────────────────────────────

class TestValidateImage:
    def setup_method(self):
        self.pipeline = VisualPipeline("dummy.pth")

    def test_valid_image(self, valid_phishing_image_bytes):
        result = self.pipeline.validate_image(valid_phishing_image_bytes)
        assert result["valid"] is True
        assert result["format"] == "png"

    def test_empty_bytes(self):
        with pytest.raises(ImageValidationError, match="empty"):
            self.pipeline.validate_image(b"")

    def test_invalid_bytes(self, invalid_image_bytes):
        with pytest.raises(ImageValidationError, match="Unsupported image format"):
            self.pipeline.validate_image(invalid_image_bytes)

    def test_unsupported_format(self, unsupported_format_bytes):
        with pytest.raises(ImageValidationError, match="Unsupported image format"):
            self.pipeline.validate_image(unsupported_format_bytes)

    def test_large_image(self, large_image_bytes):
        if len(large_image_bytes) > MAX_IMAGE_SIZE_BYTES:
            with pytest.raises(ImageValidationError, match="exceeds maximum size"):
                self.pipeline.validate_image(large_image_bytes)


# ─── Integration: Pipeline with mocked services ───────────────────────

class TestPipelineRunMocked:
    """Test the pipeline orchestration by mocking the individual services."""

    @patch("app.services.visual_pipeline.VisualExplainer")
    @patch("app.services.visual_pipeline.OCRService")
    @patch("app.services.visual_pipeline.BrandDetector")
    def test_full_success_phishing(
        self, MockBrand, MockOCR, MockExplainer, valid_phishing_image_bytes
    ):
        mock_explainer = MockExplainer.return_value
        mock_explainer.explain.return_value = {
            "label": "phishing",
            "confidence": 0.943,
            "phishing_probability": 0.943,
            "heatmap": None,
            "overlay": b"fake_png_bytes",
        }

        mock_ocr = MockOCR.return_value
        mock_ocr.analyze.return_value = {
            "extracted_text": "login password verify",
            "detections": [],
            "keywords": ["login", "password", "verify"],
            "keyword_count": 3,
            "risk_score": "High",
        }

        mock_brand = MockBrand.return_value
        mock_brand.detect_brands.return_value = {
            "brands": [{"brand": "Microsoft", "confidence": 0.96}],
            "brand_count": 1,
            "confidence_scores": [0.96],
            "risk_score": "Medium",
        }

        pipeline = VisualPipeline("dummy.pth")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(valid_phishing_image_bytes)
            tmp_path = tmp.name

        try:
            result = pipeline.run(tmp_path)
        finally:
            os.unlink(tmp_path)

        assert result["prediction"] in ("Phishing", "Suspicious")
        assert result["risk_level"] in ("Low", "Medium", "High")
        assert result["cnn"]["prediction"] == "Phishing"
        assert result["cnn"]["confidence"] == 94.3
        assert result["ocr"]["keyword_count"] == 3
        assert result["ocr"]["risk_score"] == "High"
        assert result["brand_detection"]["brand_count"] == 1
        assert result["brand_detection"]["brands"] == ["Microsoft"]
        assert result["gradcam"]["image"] is not None
        assert "visual_risk" in result
        assert "score" in result["visual_risk"]
        assert "decision" in result["visual_risk"]
        assert isinstance(result["explanation"], list)
        assert len(result["explanation"]) > 0

    @patch("app.services.visual_pipeline.VisualExplainer")
    @patch("app.services.visual_pipeline.OCRService")
    @patch("app.services.visual_pipeline.BrandDetector")
    def test_full_success_legitimate(
        self, MockBrand, MockOCR, MockExplainer, valid_legitimate_image_bytes
    ):
        mock_explainer = MockExplainer.return_value
        mock_explainer.explain.return_value = {
            "label": "legitimate",
            "confidence": 0.987,
            "phishing_probability": 0.013,
            "heatmap": None,
            "overlay": b"fake_png_bytes",
        }

        mock_ocr = MockOCR.return_value
        mock_ocr.analyze.return_value = {
            "extracted_text": "welcome home",
            "detections": [],
            "keywords": [],
            "keyword_count": 0,
            "risk_score": "Low",
        }

        mock_brand = MockBrand.return_value
        mock_brand.detect_brands.return_value = {
            "brands": [],
            "brand_count": 0,
            "confidence_scores": [],
            "risk_score": "Low",
        }

        pipeline = VisualPipeline("dummy.pth")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(valid_legitimate_image_bytes)
            tmp_path = tmp.name

        try:
            result = pipeline.run(tmp_path)
        finally:
            os.unlink(tmp_path)

        assert result["prediction"] in ("Safe", "Legitimate")
        assert result["cnn"]["prediction"] == "Legitimate"
        assert result["ocr"]["keyword_count"] == 0
        assert result["brand_detection"]["brand_count"] == 0

    @patch("app.services.visual_pipeline.VisualExplainer")
    def test_cnn_failure_graceful(self, MockExplainer, valid_phishing_image_bytes):
        mock_explainer = MockExplainer.return_value
        mock_explainer.explain.side_effect = RuntimeError("CNN crashed")

        pipeline = VisualPipeline("dummy.pth")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(valid_phishing_image_bytes)
            tmp_path = tmp.name

        try:
            result = pipeline.run(tmp_path)
        finally:
            os.unlink(tmp_path)

        assert result["cnn"]["prediction"] == "Error"
        assert "warnings" in result
        assert "cnn" in result["warnings"]

    @patch("app.services.visual_pipeline.VisualExplainer")
    @patch("app.services.visual_pipeline.OCRService")
    def test_ocr_failure_graceful(self, MockOCR, MockExplainer, valid_phishing_image_bytes):
        mock_explainer = MockExplainer.return_value
        mock_explainer.explain.return_value = {
            "label": "phishing",
            "confidence": 0.9,
            "phishing_probability": 0.9,
            "overlay": b"fake",
        }

        mock_ocr = MockOCR.return_value
        mock_ocr.analyze.side_effect = RuntimeError("OCR engine failed")

        pipeline = VisualPipeline("dummy.pth")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(valid_phishing_image_bytes)
            tmp_path = tmp.name

        try:
            result = pipeline.run(tmp_path)
        finally:
            os.unlink(tmp_path)

        assert result["ocr"]["keyword_count"] == 0
        assert result["ocr"]["risk_score"] == "Low"
        assert "warnings" in result
        assert "ocr" in result["warnings"]

    @patch("app.services.visual_pipeline.VisualExplainer")
    @patch("app.services.visual_pipeline.BrandDetector")
    def test_brand_failure_graceful(self, MockBrand, MockExplainer, valid_phishing_image_bytes):
        mock_explainer = MockExplainer.return_value
        mock_explainer.explain.return_value = {
            "label": "phishing",
            "confidence": 0.9,
            "phishing_probability": 0.9,
            "overlay": b"fake",
        }

        mock_brand = MockBrand.return_value
        mock_brand.detect_brands.side_effect = RuntimeError("Brand detection failed")

        pipeline = VisualPipeline("dummy.pth")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(valid_phishing_image_bytes)
            tmp_path = tmp.name

        try:
            result = pipeline.run(tmp_path)
        finally:
            os.unlink(tmp_path)

        assert result["brand_detection"]["brand_count"] == 0
        assert result["brand_detection"]["risk_score"] == "Low"
        assert "warnings" in result
        assert "brand" in result["warnings"]

    @patch("app.services.visual_pipeline.VisualExplainer")
    def test_explain_returns_none(self, MockExplainer, valid_phishing_image_bytes):
        mock_explainer = MockExplainer.return_value
        mock_explainer.explain.return_value = None

        pipeline = VisualPipeline("dummy.pth")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(valid_phishing_image_bytes)
            tmp_path = tmp.name

        try:
            result = pipeline.run(tmp_path)
        finally:
            os.unlink(tmp_path)

        assert result["cnn"]["prediction"] == "Error"
        assert "warnings" in result


# ─── Integration: run_from_bytes ──────────────────────────────────────

class TestRunFromBytes:
    @patch("app.services.visual_pipeline.VisualExplainer")
    @patch("app.services.visual_pipeline.OCRService")
    @patch("app.services.visual_pipeline.BrandDetector")
    def test_run_from_bytes(self, MockBrand, MockOCR, MockExplainer, valid_phishing_image_bytes):
        mock_explainer = MockExplainer.return_value
        mock_explainer.explain.return_value = {
            "label": "phishing",
            "confidence": 0.85,
            "phishing_probability": 0.85,
            "overlay": b"fake",
        }

        mock_ocr = MockOCR.return_value
        mock_ocr.analyze.return_value = {
            "extracted_text": "test",
            "detections": [],
            "keywords": ["login"],
            "keyword_count": 1,
            "risk_score": "Medium",
        }

        mock_brand = MockBrand.return_value
        mock_brand.detect_brands.return_value = {
            "brands": [],
            "brand_count": 0,
            "confidence_scores": [],
            "risk_score": "Low",
        }

        pipeline = VisualPipeline("dummy.pth")
        result = pipeline.run_from_bytes(valid_phishing_image_bytes, "test.png")

        assert result["prediction"] is not None
        assert result["cnn"]["prediction"] == "Phishing"

    @patch("app.services.visual_pipeline.VisualExplainer")
    def test_run_from_bytes_invalid_image(self, MockExplainer, invalid_image_bytes):
        pipeline = VisualPipeline("dummy.pth")
        with pytest.raises(ImageValidationError):
            pipeline.run_from_bytes(invalid_image_bytes, "bad.bin")

    def test_run_from_bytes_empty(self, empty_bytes):
        pipeline = VisualPipeline("dummy.pth")
        with pytest.raises(ImageValidationError):
            pipeline.run_from_bytes(empty_bytes, "empty.png")


# ─── Integration: Response structure ──────────────────────────────────

class TestResponseStructure:
    """Verify the response matches the expected comprehensive format."""

    @patch("app.services.visual_pipeline.VisualExplainer")
    @patch("app.services.visual_pipeline.OCRService")
    @patch("app.services.visual_pipeline.BrandDetector")
    def test_response_has_all_keys(self, MockBrand, MockOCR, MockExplainer, valid_phishing_image_bytes):
        mock_explainer = MockExplainer.return_value
        mock_explainer.explain.return_value = {
            "label": "phishing",
            "confidence": 0.943,
            "phishing_probability": 0.943,
            "overlay": b"fake_png_bytes",
        }

        mock_ocr = MockOCR.return_value
        mock_ocr.analyze.return_value = {
            "extracted_text": "login password",
            "detections": [],
            "keywords": ["login", "password"],
            "keyword_count": 2,
            "risk_score": "Medium",
        }

        mock_brand = MockBrand.return_value
        mock_brand.detect_brands.return_value = {
            "brands": [{"brand": "Microsoft", "confidence": 0.96}],
            "brand_count": 1,
            "confidence_scores": [0.96],
            "risk_score": "Medium",
        }

        pipeline = VisualPipeline("dummy.pth")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(valid_phishing_image_bytes)
            tmp_path = tmp.name

        try:
            result = pipeline.run(tmp_path)
        finally:
            os.unlink(tmp_path)

        required_top_level = [
            "prediction", "confidence", "risk_score", "risk_level",
            "cnn", "ocr", "brand_detection", "gradcam", "visual_risk", "explanation",
        ]
        for key in required_top_level:
            assert key in result, f"Missing top-level key: {key}"

        assert "image" in result["gradcam"]
        assert result["gradcam"]["image"] is not None

        cnn_keys = ["prediction", "confidence"]
        for key in cnn_keys:
            assert key in result["cnn"], f"Missing cnn key: {key}"

        ocr_keys = ["text", "keywords", "keyword_count", "risk_score"]
        for key in ocr_keys:
            assert key in result["ocr"], f"Missing ocr key: {key}"

        brand_keys = ["brands", "brand_count", "confidence", "risk_score"]
        for key in brand_keys:
            assert key in result["brand_detection"], f"Missing brand_detection key: {key}"

        vr_keys = ["score", "decision", "confidence"]
        for key in vr_keys:
            assert key in result["visual_risk"], f"Missing visual_risk key: {key}"

        assert isinstance(result["explanation"], list)
