from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel
from typing import Literal, List, Union, Optional
from app.services.qr_analyzer import QRAnalyzer
from app.services.sms_detector import SMIShingDetector
from app.services.threat_intel import ThreatIntelModule
from app.services.inference_module import inference_module
from app.services.db_service import db_service
from app.services.auth_service import get_current_user
from app.services.visual_pipeline import VisualPipeline, ImageValidationError, PipelineError
from app.services.gradcam_service import VisualExplainer
from app.services.ocr_service import OCRService
from app.services.brand_detector import BrandDetector
from app.services.visual_risk_analyzer import visual_risk_analyzer
from app.routes.auth import router as auth_router
from fastapi.middleware.cors import CORSMiddleware
from concurrent.futures import ThreadPoolExecutor
import base64
import os
import uvicorn

app = FastAPI(title="AI Cybersecurity System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include auth routes
app.include_router(auth_router)

# Initialize detectors
qr_analyzer = QRAnalyzer()
sms_detector = SMIShingDetector()
threat_intel = ThreatIntelModule()

# Visual pipeline singleton (lazy-loaded on first use)
_pipeline = None
MODELS_DIR = os.path.join(os.path.dirname(__file__), '../models/visual_model')
VISUAL_MODEL_PATH = os.path.join(MODELS_DIR, 'mobilenet_exp_wd_5e-05_best.pth')

def get_visual_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = VisualPipeline(VISUAL_MODEL_PATH)
    return _pipeline

# Legacy lazy-loaders — delegate to pipeline for singleton consistency
def get_visual_explainer():
    return get_visual_pipeline()._get_explainer()

def get_ocr_service():
    return get_visual_pipeline()._get_ocr()

def get_brand_detector():
    return get_visual_pipeline()._get_brand()


class URLRequest(BaseModel):
    url: str


class SMSRequest(BaseModel):
    message: str


class PredictionRequest(BaseModel):
    input_type: Literal["url", "sms", "url_batch", "qr"]
    data: Union[str, List[str]]


class PredictionResponse(BaseModel):
    label: str
    confidence: float
    explanation: Optional[List[dict]] = None
    threat_intel: Optional[dict] = None


@app.get("/")
async def root():
    return {"message": "AI Cybersecurity System API is running"}


# ─── Extension endpoints (no auth — used by Chrome extension) ───

class ExtensionURLRequest(BaseModel):
    url: str


class ExtensionQRRequest(BaseModel):
    image_url: str


@app.post("/extension/check-url")
async def extension_check_url(request: ExtensionURLRequest):
    try:
        result = inference_module.predict("url", request.url)
        pred = result.get("label", "unknown")
        conf = result.get("confidence", 0)
        db_service.log_prediction("url", request.url, {}, pred, conf, user_id="anonymous")
        return {
            "url": request.url,
            "prediction": pred,
            "confidence_score": conf,
            "latency_ms": result.get("latency_ms", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extension/analyze-qr")
async def extension_analyze_qr(request: ExtensionQRRequest):
    """Receive image URL, download it, decode QR, and check the extracted URL."""
    try:
        import requests as http_requests
        resp = http_requests.get(request.image_url, timeout=10)
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to download image")
        result = qr_analyzer.analyze(resp.content)
        if "error" in result:
            return result
        # Also run URL check on the extracted URL
        url_check = inference_module.predict("url", result["extracted_url"])
        result["url_prediction"] = url_check.get("label", "unknown")
        result["url_confidence"] = url_check.get("confidence", 0)
        db_service.log_prediction("qr", request.image_url,
                                  {"extracted_url": result["extracted_url"]},
                                  result["url_prediction"], result["url_confidence"],
                                  user_id="anonymous")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extension/analyze-sms")
async def extension_analyze_sms(request: ExtensionURLRequest):
    try:
        result = sms_detector.predict(request.url)
        db_service.log_prediction("sms", request.url, {}, result.get("prediction", "unknown"),
                                  result.get("confidence_score", 0), user_id="anonymous")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extension/visual-scan")
async def extension_visual_scan(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        pipeline = get_visual_pipeline()
        pipeline.validate_image(contents)

        import tempfile as _tempfile
        suffix = os.path.splitext(file.filename or "upload.png")[1] or ".png"
        with _tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(contents)
            temp_path = tmp.name

        try:
            pipe_result = pipeline.run(temp_path)
        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass

        cnn = pipe_result["cnn"]
        ocr = pipe_result["ocr"]
        brand = pipe_result["brand_detection"]
        vr = pipe_result["visual_risk"]
        expl = pipe_result["explanation"]

        risk_score_val = vr["score"]
        risk_level_val = pipe_result["risk_level"]

        risk = visual_risk_analyzer.analyze(
            cnn_label="phishing" if cnn["prediction"] == "Phishing" else "legitimate",
            cnn_confidence=cnn.get("phishing_probability", cnn["confidence"] / 100),
            cnn_phishing_prob=cnn.get("phishing_probability", cnn["confidence"] / 100),
            ocr_risk=ocr["risk_score"],
            ocr_keywords=ocr["keywords"],
            ocr_keyword_count=ocr["keyword_count"],
            brand_brands=brand["brands"],
            brand_confidence=brand["confidence"],
            brand_count=brand["brand_count"],
            brand_risk=brand["risk_score"],
        )

        return {
            "label": risk["decision"],
            "confidence": cnn.get("phishing_probability", cnn["confidence"] / 100),
            "phishing_probability": cnn.get("phishing_probability", cnn["confidence"] / 100),
            "risk_score": risk_score_val,
            "risk_level": risk_level_val,
            "ocr": ocr,
            "brand_detection": brand,
            "risk_analysis": {
                "score": risk["score"],
                "decision": risk["decision"],
                "risk_level": risk["risk_level"],
                "cnn_contribution": risk["cnn_contribution"],
                "ocr_contribution": risk["ocr_contribution"],
                "brand_contribution": risk["brand_contribution"],
                "explanation": expl,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Auth-protected endpoints ───

@app.post("/analyze-url")
async def analyze_url(request: URLRequest, user: dict = Depends(get_current_user)):
    try:
        result = inference_module.predict("url", request.url)
        pred = result.get("label", "unknown")
        conf = result.get("confidence", 0)
        db_service.log_prediction("url", request.url, {}, pred, conf, user_id=user.get("id", "unknown"))

        return {
            "url": request.url,
            "prediction": pred,
            "confidence_score": conf,
            "latency_ms": result.get("latency_ms", 0)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze-qr")
async def analyze_qr(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    try:
        contents = await file.read()
        result = qr_analyzer.analyze(contents)
        db_service.log_prediction("qr", file.filename or "qr_image",
                                  {"extracted_url": result.get("extracted_url", "")},
                                  result.get("prediction", "unknown"),
                                  result.get("confidence_score", 0),
                                  user_id=user.get("id", "unknown"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze-sms")
async def analyze_sms(request: SMSRequest, user: dict = Depends(get_current_user)):
    try:
        result = sms_detector.predict(request.message)
        db_service.log_prediction("sms", request.message, {},
                                  result.get("prediction", "unknown"),
                                  result.get("confidence_score", 0),
                                  user_id=user.get("id", "unknown"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict")
async def predict(request: PredictionRequest, user: dict = Depends(get_current_user)):
    uid = user.get("id", "unknown")
    try:
        if request.input_type == "url_batch":
            if not isinstance(request.data, list):
                raise HTTPException(status_code=400, detail="data must be a list for url_batch")

            def process_url(url):
                r = inference_module.predict("url", url)
                label = r.get("label", "unknown")
                conf = r.get("confidence", 0.0)
                db_service.log_prediction("url", url, {}, label, conf, user_id=uid)
                return {
                    "url": url,
                    "label": label,
                    "confidence": conf,
                    "threat_intel": r.get("threat_intel", {})
                }

            with ThreadPoolExecutor(max_workers=5) as executor:
                results = list(executor.map(process_url, request.data))

            return {"results": results}

        data_to_predict = request.data

        if request.input_type == "qr":
            try:
                img_data = request.data
                if isinstance(img_data, str) and "," in img_data:
                    img_data = img_data.split(",")[1]

                image_bytes = base64.b64decode(img_data)
                decoded_url = qr_analyzer.decode_qr(image_bytes)

                if not decoded_url:
                    return {"error": "No QR code could be decoded from the provided image."}

                data_to_predict = decoded_url
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid base64/QR data: {e}")

        result = inference_module.predict(
            input_type="url" if request.input_type == "qr" else request.input_type,
            data=data_to_predict
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        actual_type = "qr" if request.input_type == "qr" else request.input_type
        db_service.log_prediction(actual_type, str(data_to_predict), {},
                                  result["label"], result["confidence"],
                                  user_id=uid)

        return PredictionResponse(
            label=result["label"],
            confidence=result["confidence"],
            explanation=result.get("explanation", []),
            threat_intel=result.get("threat_intel", {})
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Visual Scan endpoint (comprehensive pipeline) ───


@app.post("/api/visual_scan")
async def visual_scan(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    try:
        contents = await file.read()
        pipeline = get_visual_pipeline()
        result = pipeline.run_from_bytes(contents, file.filename or "upload.png")

        return result
    except ImageValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PipelineError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)