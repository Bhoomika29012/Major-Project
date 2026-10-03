import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import os
import json
import logging
from app.services.gradcam_service import VisualExplainer

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models/visual_model/mobilenet_exp_wd_5e-05_best.pth")
TEST_DIR = Path(__file__).resolve().parent.parent / "processed_data" / "test"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs" / "gradcam"

PHISHING_DIR = TEST_DIR / "phishing"
LEGIT_DIR = TEST_DIR / "legitimate"

def get_samples(directory, count=10):
    files = sorted(directory.iterdir())[:count]
    return [str(f) for f in files]

def main():
    if not os.path.exists(MODEL_PATH):
        logger.error(f"Model not found: {MODEL_PATH}")
        sys.exit(1)

    explainer = VisualExplainer(MODEL_PATH)
    phishing_samples = get_samples(PHISHING_DIR, 10)
    legit_samples = get_samples(LEGIT_DIR, 10)
    all_samples = phishing_samples + legit_samples

    phishing_out = str(OUTPUT_DIR / "phishing")
    legit_out = str(OUTPUT_DIR / "legitimate")
    os.makedirs(phishing_out, exist_ok=True)
    os.makedirs(legit_out, exist_ok=True)

    results = {"phishing": [], "legitimate": []}

    logger.info(f"Processing {len(phishing_samples)} phishing samples ...")
    for path in phishing_samples:
        name = Path(path).stem
        save_path = os.path.join(phishing_out, f"{name}_gradcam.png")
        try:
            res = explainer.explain(path, save_path=save_path)
            res["filename"] = Path(path).name
            results["phishing"].append(res)
            logger.info(f"  [PHISHING] {Path(path).name} -> {res['label']} (conf={res['confidence']:.3f})")
        except Exception as e:
            logger.error(f"  [PHISHING] {Path(path).name} FAILED: {e}")

    logger.info(f"Processing {len(legit_samples)} legitimate samples ...")
    for path in legit_samples:
        name = Path(path).stem
        save_path = os.path.join(legit_out, f"{name}_gradcam.png")
        try:
            res = explainer.explain(path, save_path=save_path)
            res["filename"] = Path(path).name
            results["legitimate"].append(res)
            logger.info(f"  [LEGIT]    {Path(path).name} -> {res['label']} (conf={res['confidence']:.3f})")
        except Exception as e:
            logger.error(f"  [LEGIT]    {Path(path).name} FAILED: {e}")

    report_path = OUTPUT_DIR / "gradcam_results.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved to {report_path}")

if __name__ == "__main__":
    main()
