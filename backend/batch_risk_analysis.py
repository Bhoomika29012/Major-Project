import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import os
import json
import logging
from app.services.gradcam_service import VisualExplainer
from app.services.ocr_service import OCRService
from app.services.brand_detector import BrandDetector
from app.services.visual_risk_analyzer import visual_risk_analyzer

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

TEST_DIR = Path(__file__).resolve().parent.parent / "processed_data" / "test"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs" / "risk_analysis"

PHISHING_DIR = TEST_DIR / "phishing"
LEGIT_DIR = TEST_DIR / "legitimate"
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models/visual_model/mobilenet_exp_wd_5e-05_best.pth")

def get_samples(directory, count=10):
    files = sorted(directory.iterdir())[:count]
    return [str(f) for f in files]

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    explainer = VisualExplainer(MODEL_PATH)
    ocr = OCRService()
    brand = BrandDetector()

    phishing_samples = get_samples(PHISHING_DIR, 10)
    legit_samples = get_samples(LEGIT_DIR, 10)
    all_samples = phishing_samples + legit_samples

    results = {"phishing": [], "legitimate": []}

    logger.info(f"Processing {len(phishing_samples)} phishing samples ...")
    for path in phishing_samples:
        try:
            cnn = explainer.explain(path)
            ocr_res = ocr.analyze(path)
            brand_res = brand.detect_brands(path)
            risk = visual_risk_analyzer.analyze(
                cnn_label=cnn["label"], cnn_confidence=cnn["confidence"],
                cnn_phishing_prob=cnn["phishing_probability"],
                ocr_risk=ocr_res["risk_score"], ocr_keywords=ocr_res["keywords"],
                ocr_keyword_count=ocr_res["keyword_count"],
                brand_brands=[b["brand"] for b in brand_res.get("brands", [])],
                brand_confidence=[b["confidence"] for b in brand_res.get("brands", [])],
                brand_count=brand_res["brand_count"], brand_risk=brand_res["risk_score"],
            )
            entry = {
                "filename": Path(path).name,
                "cnn_label": cnn["label"],
                "cnn_confidence": cnn["confidence"],
                "ocr_keywords": ocr_res["keywords"],
                "ocr_risk": ocr_res["risk_score"],
                "brand_count": brand_res["brand_count"],
                "brand_risk": brand_res["risk_score"],
                "risk_score": risk["score"],
                "decision": risk["decision"],
                "risk_level": risk["risk_level"],
                "explanation": risk["explanation"],
            }
            results["phishing"].append(entry)
            logger.info(f"  [PHISHING] {Path(path).name} -> risk={risk['score']}, decision={risk['decision']}")
        except Exception as e:
            logger.error(f"  [PHISHING] {Path(path).name} FAILED: {e}")

    logger.info(f"Processing {len(legit_samples)} legitimate samples ...")
    for path in legit_samples:
        try:
            cnn = explainer.explain(path)
            ocr_res = ocr.analyze(path)
            brand_res = brand.detect_brands(path)
            risk = visual_risk_analyzer.analyze(
                cnn_label=cnn["label"], cnn_confidence=cnn["confidence"],
                cnn_phishing_prob=cnn["phishing_probability"],
                ocr_risk=ocr_res["risk_score"], ocr_keywords=ocr_res["keywords"],
                ocr_keyword_count=ocr_res["keyword_count"],
                brand_brands=[b["brand"] for b in brand_res.get("brands", [])],
                brand_confidence=[b["confidence"] for b in brand_res.get("brands", [])],
                brand_count=brand_res["brand_count"], brand_risk=brand_res["risk_score"],
            )
            entry = {
                "filename": Path(path).name,
                "cnn_label": cnn["label"],
                "cnn_confidence": cnn["confidence"],
                "ocr_keywords": ocr_res["keywords"],
                "ocr_risk": ocr_res["risk_score"],
                "brand_count": brand_res["brand_count"],
                "brand_risk": brand_res["risk_score"],
                "risk_score": risk["score"],
                "decision": risk["decision"],
                "risk_level": risk["risk_level"],
                "explanation": risk["explanation"],
            }
            results["legitimate"].append(entry)
            logger.info(f"  [LEGIT]    {Path(path).name} -> risk={risk['score']}, decision={risk['decision']}")
        except Exception as e:
            logger.error(f"  [LEGIT]    {Path(path).name} FAILED: {e}")

    report_path = os.path.join(OUTPUT_DIR, "risk_results.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"Results saved to {report_path}")

if __name__ == "__main__":
    main()
