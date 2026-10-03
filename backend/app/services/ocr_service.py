import os
import json
import logging
import re
from pathlib import Path
from typing import List, Tuple, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

KEYWORDS_PATH = Path(__file__).resolve().parent / "ocr_keywords.json"
OCR_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "outputs" / "ocr"

class OCRService:
    _reader = None

    def __init__(self, lang: list = None, gpu: bool = True):
        self.lang = lang or ["en"]
        self.gpu = gpu and self._cuda_available()
        self.keywords = self._load_keywords()
        self._get_reader()

    @staticmethod
    def _cuda_available() -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def _get_reader(self):
        if OCRService._reader is None:
            import easyocr
            logger.info(f"Initialising EasyOCR reader (lang={self.lang}, gpu={self.gpu}) ...")
            OCRService._reader = easyocr.Reader(self.lang, gpu=self.gpu)
            logger.info("EasyOCR reader ready.")
        return OCRService._reader

    @staticmethod
    def _load_keywords() -> list:
        try:
            with open(KEYWORDS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("phishing_keywords", [])
        except Exception as e:
            logger.warning(f"Could not load keywords from {KEYWORDS_PATH}: {e}")
            return []

    def extract_text(self, image_path: str) -> List[dict]:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        reader = self._get_reader()
        results = reader.readtext(image_path)
        detections = []
        for bbox, text, confidence in results:
            detections.append({
                "bbox": [[float(coord) for coord in point] for point in bbox],
                "text": text.strip(),
                "confidence": round(float(confidence), 4),
            })
        return detections

    def get_full_text(self, image_path: str) -> str:
        detections = self.extract_text(image_path)
        texts = [d["text"] for d in detections if d["text"]]
        return " ".join(texts)

    def detect_keywords(self, text: str) -> List[dict]:
        text_lower = text.lower()
        found = []
        for kw in self.keywords:
            pattern = re.compile(re.escape(kw.lower()))
            if pattern.search(text_lower):
                found.append({"keyword": kw, "matched": True})
        return found

    def compute_risk_score(self, keyword_count: int) -> str:
        if keyword_count == 0:
            return "Low"
        elif keyword_count <= 2:
            return "Medium"
        else:
            return "High"

    def analyze(self, image_path: str) -> dict:
        detections = self.extract_text(image_path)
        full_text = " ".join(d["text"] for d in detections if d["text"])
        keywords = self.detect_keywords(full_text)
        keyword_count = len(keywords)
        risk_score = self.compute_risk_score(keyword_count)
        return {
            "extracted_text": full_text,
            "detections": detections,
            "keywords": [k["keyword"] for k in keywords],
            "keyword_count": keyword_count,
            "risk_score": risk_score,
        }

    def analyze_and_save(self, image_path: str, output_dir: str = None) -> dict:
        if output_dir is None:
            output_dir = str(OCR_OUTPUT_DIR)
        json_dir = os.path.join(output_dir, "json")
        annot_dir = os.path.join(output_dir, "annotated")
        os.makedirs(json_dir, exist_ok=True)
        os.makedirs(annot_dir, exist_ok=True)

        result = self.analyze(image_path)
        stem = Path(image_path).stem

        # Save JSON
        json_path = os.path.join(json_dir, f"{stem}_ocr.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # Save annotated image
        annot_path = self._draw_boxes(image_path, result["detections"], annot_dir, stem)
        result["json_path"] = json_path
        result["annotated_path"] = annot_path
        return result

    def _draw_boxes(self, image_path: str, detections: List[dict], output_dir: str, stem: str) -> str:
        img = cv2.imread(image_path)
        if img is None:
            return ""
        for det in detections:
            bbox = np.array(det["bbox"], dtype=np.int32)
            text = det["text"]
            conf = det["confidence"]
            cv2.polylines(img, [bbox], isClosed=True, color=(0, 255, 0), thickness=2)
            x, y = int(bbox[0][0]), int(bbox[0][1]) - 10
            label = f"{text} ({conf:.2f})"
            cv2.putText(img, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        save_path = os.path.join(output_dir, f"{stem}_annotated.png")
        cv2.imwrite(save_path, img)
        return save_path

    def analyze_batch(self, image_paths: List[str], output_dir: str = None) -> List[dict]:
        results = []
        for path in image_paths:
            try:
                res = self.analyze_and_save(path, output_dir)
                res["filename"] = Path(path).name
                results.append(res)
                logger.info(f"  [OCR] {Path(path).name} -> {res['keyword_count']} keywords, risk={res['risk_score']}")
            except Exception as e:
                logger.error(f"  [OCR] {Path(path).name} FAILED: {e}")
        return results


ocr_service = OCRService()
