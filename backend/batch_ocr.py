import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import os
import json
import logging
from app.services.ocr_service import OCRService

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

TEST_DIR = Path(__file__).resolve().parent.parent / "processed_data" / "test"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs" / "ocr"

PHISHING_DIR = TEST_DIR / "phishing"
LEGIT_DIR = TEST_DIR / "legitimate"

def get_samples(directory, count=10):
    files = sorted(directory.iterdir())[:count]
    return [str(f) for f in files]

def main():
    ocr = OCRService()

    phishing_samples = get_samples(PHISHING_DIR, 10)
    legit_samples = get_samples(LEGIT_DIR, 10)
    all_samples = phishing_samples + legit_samples

    results = {"phishing": [], "legitimate": []}

    logger.info(f"Processing {len(phishing_samples)} phishing samples ...")
    for path in phishing_samples:
        try:
            res = ocr.analyze_and_save(path)
            res["filename"] = Path(path).name
            results["phishing"].append(res)
            logger.info(f"  [PHISHING] {Path(path).name} -> keywords={res['keyword_count']}, risk={res['risk_score']}")
        except Exception as e:
            logger.error(f"  [PHISHING] {Path(path).name} FAILED: {e}")

    logger.info(f"Processing {len(legit_samples)} legitimate samples ...")
    for path in legit_samples:
        try:
            res = ocr.analyze_and_save(path)
            res["filename"] = Path(path).name
            results["legitimate"].append(res)
            logger.info(f"  [LEGIT]    {Path(path).name} -> keywords={res['keyword_count']}, risk={res['risk_score']}")
        except Exception as e:
            logger.error(f"  [LEGIT]    {Path(path).name} FAILED: {e}")

    report_path = os.path.join(OUTPUT_DIR, "ocr_results.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"Results saved to {report_path}")

if __name__ == "__main__":
    main()
