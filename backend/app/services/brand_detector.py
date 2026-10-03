import os
import json
import logging
import re
from pathlib import Path
from typing import List, Tuple, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

PHISHPEDIA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "Phishpedia"
TARGETLIST_DIR = PHISHPEDIA_DIR / "targetlist_fit_copy_half_rename"
BRAND_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "outputs" / "brand_detection"

MIN_MATCHES = 40
MIN_INLIERS = 30
RATIO_THRESH = 0.65
MAX_BRANDS = 5
MIN_BBOX_AREA = 50 * 50

class BrandDetector:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.brand_db = {}
        self.orb = cv2.ORB_create(nfeatures=1000)
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        self._load_brand_templates()
        logger.info(f"BrandDetector ready: {len(self.brand_db)} brands loaded")

    def _load_brand_templates(self):
        if not TARGETLIST_DIR.exists():
            logger.warning(f"Phishpedia targetlist not found at {TARGETLIST_DIR}")
            return
        for brand_dir in sorted(TARGETLIST_DIR.iterdir()):
            if not brand_dir.is_dir():
                continue
            brand_name = brand_dir.name
            logo_paths = sorted(brand_dir.glob("*.png"))
            image_paths = [p for p in logo_paths if p.stem.lstrip("0").isdigit() or p.name == "homepage.png"]
            if not image_paths:
                continue
            template_path = str(image_paths[0])
            img = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            kp, des = self.orb.detectAndCompute(img, None)
            if des is None or len(kp) < 4:
                continue
            self.brand_db[brand_name] = {
                "path": template_path,
                "keypoints": kp,
                "descriptors": des,
                "image_shape": img.shape,
            }

    def detect_brands(self, image_path: str, threshold: float = 0.20) -> dict:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError(f"Could not read image: {image_path}")
        img_h, img_w = img.shape[:2]
        kp_query, des_query = self.orb.detectAndCompute(img, None)
        if des_query is None:
            return self._empty_result()
        detected = []
        for brand_name, data in self.brand_db.items():
            matches = self.bf.knnMatch(des_query, data["descriptors"], k=2)
            good = []
            for pair in matches:
                if len(pair) == 2:
                    m, n = pair
                    if m.distance < RATIO_THRESH * n.distance:
                        good.append(m)

            # Stage 1: minimum good matches
            if len(good) < MIN_MATCHES:
                logger.debug(f"  [BRAND] {brand_name} | Good Matches: {len(good)} | Rejected (stage 1: < {MIN_MATCHES})")
                continue

            src_pts = np.float32([kp_query[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst_pts = np.float32([data["keypoints"][m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
            M, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0)

            # Stage 2: homography must exist
            if M is None:
                logger.debug(f"  [BRAND] {brand_name} | Good Matches: {len(good)} | Rejected (stage 2: no homography)")
                continue

            # Stage 3: count inliers, require minimum
            inliers = int(mask.sum()) if mask is not None else 0
            if inliers < MIN_INLIERS:
                logger.debug(
                    f"  [BRAND] {brand_name} | "
                    f"Good Matches: {len(good)} | Inliers: {inliers} | "
                    f"Rejected (stage 3: inliers < {MIN_INLIERS})"
                )
                continue

            # Stage 4: confidence = inlier ratio
            confidence = inliers / len(good) if len(good) > 0 else 0.0
            if confidence < threshold:
                logger.debug(
                    f"  [BRAND] {brand_name} | "
                    f"Good Matches: {len(good)} | Inliers: {inliers} | "
                    f"Confidence: {confidence:.3f} | "
                    f"Rejected (stage 4: confidence < {threshold})"
                )
                continue

            # Compute bounding box from homography
            th, tw = data["image_shape"]
            corners = np.float32([[0, 0], [0, th - 1], [tw - 1, th - 1], [tw - 1, 0]]).reshape(-1, 1, 2)
            transformed = cv2.perspectiveTransform(corners, M)
            x_coords = transformed[:, 0, 0]
            y_coords = transformed[:, 0, 1]
            x_min, x_max = int(x_coords.min()), int(x_coords.max())
            y_min, y_max = int(y_coords.min()), int(y_coords.max())
            bbox = [x_min, y_min, x_max, y_max]

            # Stage 5: validate bounding box
            bbox_w = x_max - x_min
            bbox_h = y_max - y_min
            valid = True
            if bbox_w <= 0 or bbox_h <= 0:
                valid = False
            elif x_min < -img_w * 0.5 or y_min < -img_h * 0.5 or x_max > img_w * 1.5 or y_max > img_h * 1.5:
                valid = False
            elif bbox_w * bbox_h < MIN_BBOX_AREA:
                valid = False
            if not valid:
                logger.debug(
                    f"  [BRAND] {brand_name} | "
                    f"Good Matches: {len(good)} | Inliers: {inliers} | "
                    f"Confidence: {confidence:.3f} | "
                    f"Rejected (stage 5: invalid bbox {bbox})"
                )
                continue

            logger.info(
                f"  [BRAND] {brand_name} | "
                f"Good Matches: {len(good)} | Inliers: {inliers} | "
                f"Confidence: {confidence:.3f} | "
                f"Accepted"
            )

            detected.append({
                "brand": brand_name,
                "confidence": round(confidence, 4),
                "bounding_box": bbox,
                "status": "Detected",
                "matches": len(good),
                "inliers": inliers,
            })

        detected.sort(key=lambda x: x["confidence"], reverse=True)
        detected = detected[:MAX_BRANDS]
        brand_count = len(detected)
        if brand_count == 0:
            return self._empty_result()
        confidence_scores = [d["confidence"] for d in detected]
        risk_score = self._compute_risk_score(brand_count, confidence_scores)
        return {
            "brands": [
                {"brand": d["brand"], "confidence": d["confidence"]}
                for d in detected
            ],
            "detected_brands": [
                {
                    "brand": d["brand"],
                    "confidence": d["confidence"],
                    "bounding_box": d["bounding_box"],
                    "status": d["status"],
                }
                for d in detected
            ],
            "brand_count": brand_count,
            "confidence_scores": confidence_scores,
            "risk_score": risk_score,
        }

    def _empty_result(self):
        return {
            "brands": [],
            "detected_brands": [{"brand": "Unknown", "confidence": 0.0, "bounding_box": [0,0,0,0], "status": "No Protected Brand Found"}],
            "brand_count": 0,
            "confidence_scores": [],
            "risk_score": "Low",
        }

    @staticmethod
    def _compute_risk_score(brand_count: int, confidence_scores: list = None) -> str:
        if brand_count == 0:
            return "Low"
        avg_conf = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        if brand_count == 1:
            return "Medium" if avg_conf > 0.80 else "Low"
        if brand_count >= 2:
            return "High" if avg_conf > 0.70 else "Medium"
        return "Low"

    def detect_and_annotate(self, image_path: str, output_dir: str = None) -> dict:
        if output_dir is None:
            output_dir = str(BRAND_OUTPUT_DIR)
        json_dir = os.path.join(output_dir, "json")
        annot_dir = os.path.join(output_dir, "annotated")
        os.makedirs(json_dir, exist_ok=True)
        os.makedirs(annot_dir, exist_ok=True)
        result = self.detect_brands(image_path)
        stem = Path(image_path).stem
        json_path = os.path.join(json_dir, f"{stem}_brand.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        annot_path = self._draw_brand_boxes(image_path, result, annot_dir, stem)
        result["json_path"] = json_path
        result["annotated_path"] = annot_path
        return result

    def _draw_brand_boxes(self, image_path: str, result: dict, output_dir: str, stem: str) -> str:
        img = cv2.imread(image_path)
        if img is None:
            return ""
        for det in result.get("detected_brands", []):
            if det["status"] != "Detected":
                continue
            bbox = det["bounding_box"]
            if bbox == [0, 0, 0, 0]:
                continue
            x_min, y_min, x_max, y_max = bbox
            cv2.rectangle(img, (x_min, y_min), (x_max, y_max), (0, 0, 255), 2)
            label = f"{det['brand']} ({det['confidence']:.2f})"
            cv2.putText(img, label, (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        save_path = os.path.join(output_dir, f"{stem}_brand.png")
        cv2.imwrite(save_path, img)
        return save_path

    def detect_batch(self, image_paths: List[str], output_dir: str = None) -> List[dict]:
        results = []
        for path in image_paths:
            try:
                res = self.detect_and_annotate(path, output_dir)
                res["filename"] = Path(path).name
                results.append(res)
                brands = [d["brand"] for d in res.get("detected_brands", []) if d["status"] == "Detected"]
                confs = [d["confidence"] for d in res.get("detected_brands", []) if d["status"] == "Detected"]
                conf_str = ", ".join(f"{c:.3f}" for c in confs) if confs else "-"
                logger.info(f"  [BRAND] {Path(path).name} -> brands={brands or 'None'} conf=[{conf_str}] risk={res['risk_score']}")
            except Exception as e:
                logger.error(f"  [BRAND] {Path(path).name} FAILED: {e}")
        return results


brand_detector = BrandDetector()
