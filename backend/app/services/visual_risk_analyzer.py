import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

CNN_WEIGHT = 0.60
OCR_WEIGHT = 0.20
BRAND_WEIGHT = 0.20

RISK_MAP = {"Low": 0, "Medium": 50, "High": 100}
OCR_RISK_MAP = {"Low": 0, "Medium": 40, "High": 80}
BRAND_RISK_MAP = {"Low": 0, "Medium": 50, "High": 100}

class VisualRiskAnalyzer:

    def analyze(
        self,
        cnn_label: str,
        cnn_confidence: float,
        cnn_phishing_prob: float,
        ocr_risk: str,
        ocr_keywords: list,
        ocr_keyword_count: int,
        brand_brands: list,
        brand_confidence: list,
        brand_count: int,
        brand_risk: str,
    ) -> dict:
        cnn_score = self._compute_cnn_score(cnn_label, cnn_confidence, cnn_phishing_prob)
        ocr_score = self._compute_ocr_score(ocr_risk, ocr_keyword_count)
        brand_score = self._compute_brand_score(brand_risk, brand_count)

        raw_score = cnn_score * CNN_WEIGHT + ocr_score * OCR_WEIGHT + brand_score * BRAND_WEIGHT
        final_score = round(min(100, max(0, raw_score)), 1)
        decision = self._decide(final_score)
        risk_level = self._risk_level(final_score)
        explanation = self._build_explanation(
            cnn_label, cnn_confidence, cnn_phishing_prob,
            ocr_risk, ocr_keywords, ocr_keyword_count,
            brand_brands, brand_confidence, brand_count, brand_risk,
            final_score, decision,
        )
        return {
            "score": final_score,
            "decision": decision,
            "risk_level": risk_level,
            "cnn_contribution": round(cnn_score * CNN_WEIGHT, 1),
            "ocr_contribution": round(ocr_score * OCR_WEIGHT, 1),
            "brand_contribution": round(brand_score * BRAND_WEIGHT, 1),
            "explanation": explanation,
        }

    def _compute_cnn_score(self, label: str, confidence: float, phishing_prob: float) -> float:
        return phishing_prob * 100

    def _compute_ocr_score(self, risk: str, keyword_count: int) -> float:
        base = OCR_RISK_MAP.get(risk, 0)
        if keyword_count >= 5:
            base = min(100, base + 20)
        elif keyword_count >= 3:
            base = min(100, base + 10)
        return float(base)

    def _compute_brand_score(self, risk: str, brand_count: int) -> float:
        base = BRAND_RISK_MAP.get(risk, 0)
        if brand_count >= 3:
            base = min(100, base + 20)
        elif brand_count >= 2:
            base = min(100, base + 10)
        return float(base)

    @staticmethod
    def _decide(score: float) -> str:
        if score <= 30:
            return "Safe"
        elif score <= 60:
            return "Suspicious"
        else:
            return "Phishing"

    @staticmethod
    def _risk_level(score: float) -> str:
        if score <= 30:
            return "Low"
        elif score <= 60:
            return "Medium"
        else:
            return "High"

    def _build_explanation(self, *args) -> List[str]:
        cnn_label, cnn_confidence, cnn_phishing_prob = args[0], args[1], args[2]
        ocr_risk, ocr_keywords, ocr_keyword_count = args[3], args[4], args[5]
        brand_brands, brand_confidence, brand_count, brand_risk = args[6], args[7], args[8], args[9]
        final_score, decision = args[10], args[11]
        lines = []
        if cnn_label == "phishing":
            lines.append(f"CNN detected phishing page ({cnn_phishing_prob*100:.1f}% phishing probability)")
        else:
            lines.append(f"CNN classified page as legitimate (phishing probability {cnn_phishing_prob*100:.1f}%)")
        if ocr_keyword_count > 0:
            kw_str = ", ".join(ocr_keywords[:5])
            suffix = f" and {ocr_keyword_count - 5} more" if ocr_keyword_count > 5 else ""
            lines.append(f"OCR found {ocr_keyword_count} suspicious keyword(s): {kw_str}{suffix}")
        elif ocr_risk == "Low":
            lines.append("OCR detected no suspicious keywords")
        if brand_count > 0:
            brand_str = ", ".join(brand_brands[:3])
            suffix = f" and {brand_count - 3} more" if brand_count > 3 else ""
            lines.append(f"Brand detection identified {brand_count} protected brand(s): {brand_str}{suffix}")
        else:
            lines.append("No protected brand logos detected")
        lines.append(f"Final risk score: {final_score}/100 — {decision}")
        return lines


visual_risk_analyzer = VisualRiskAnalyzer()
