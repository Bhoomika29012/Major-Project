import os
import torch
import torch.nn as nn
import numpy as np
from PIL import Image
import cv2
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

class GradCAM:
    def __init__(self, model: nn.Module, target_layer: nn.Module):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None
        self._register_hooks()

    def _register_hooks(self):
        def forward_hook(module, input, output):
            self.activations = output.detach()

        def backward_hook(module, grad_input, grad_output):
            self.gradients = grad_output[0].detach()

        self.target_layer.register_forward_hook(forward_hook)
        self.target_layer.register_full_backward_hook(backward_hook)

    def generate(self, input_tensor: torch.Tensor, class_idx: int = None) -> np.ndarray:
        self.model.zero_grad()
        output = self.model(input_tensor)
        if class_idx is None:
            class_idx = output.argmax(dim=1).item()
        target = output[0, class_idx]
        target.backward()

        if self.gradients is None or self.activations is None:
            return None

        weights = self.gradients.mean(dim=(2, 3), keepdim=True)
        cam = (weights * self.activations).sum(dim=1, keepdim=True)
        cam = torch.relu(cam)
        cam = cam.squeeze().cpu().numpy()
        cam = cv2.resize(cam, (input_tensor.shape[3], input_tensor.shape[2]))
        cam = cam - cam.min()
        if cam.max() > 0:
            cam = cam / cam.max()
        return cam


class VisualExplainer:
    def __init__(self, model_path: str, threshold: float = 0.20, device: str = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.threshold = threshold
        self.model = self._load_model(model_path)
        self.model.eval()
        target_layer = self._find_last_conv()
        self.gradcam = GradCAM(self.model, target_layer)
        logger.info(f"VisualExplainer ready on {self.device}, target layer: {target_layer.__class__.__name__}")

    def _load_model(self, model_path: str) -> nn.Module:
        import torchvision.models as models
        model = models.mobilenet_v3_large(weights=None)
        in_features = model.classifier[3].in_features
        model.classifier[3] = nn.Linear(in_features, 2)
        state = torch.load(model_path, map_location=self.device)
        if "model_state_dict" in state:
            model.load_state_dict(state["model_state_dict"])
        else:
            model.load_state_dict(state)
        model = model.to(self.device)
        return model

    def _find_last_conv(self) -> nn.Module:
        last_block = self.model.features[-1]
        last_conv = None
        for module in last_block.modules():
            if isinstance(module, nn.Conv2d):
                last_conv = module
        return last_conv

    def _preprocess(self, image_path: str) -> torch.Tensor:
        from torchvision import transforms
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ])
        img = Image.open(image_path).convert("RGB")
        tensor = transform(img).unsqueeze(0).to(self.device)
        return tensor

    def predict(self, image_path: str) -> dict:
        tensor = self._preprocess(image_path)
        with torch.no_grad():
            output = self.model(tensor)
            prob = torch.softmax(output, dim=1)
            phishing_prob = prob[0, 1].item()
            label = "phishing" if phishing_prob > self.threshold else "legitimate"
            confidence = phishing_prob if label == "phishing" else 1 - phishing_prob
        return {"label": label, "confidence": round(confidence, 4), "phishing_probability": round(phishing_prob, 4)}

    def explain(self, image_path: str, save_path: str = None) -> dict:
        tensor = self._preprocess(image_path)
        with torch.no_grad():
            output = self.model(tensor)
            prob = torch.softmax(output, dim=1)
            phishing_prob = prob[0, 1].item()
            label = "phishing" if phishing_prob > self.threshold else "legitimate"
            confidence = phishing_prob if label == "phishing" else 1 - phishing_prob
        class_idx = 1
        cam = self.gradcam.generate(tensor, class_idx=class_idx)
        if cam is None:
            return None
        img = cv2.imread(image_path)
        img = cv2.resize(img, (224, 224))
        heatmap = cv2.applyColorMap(np.uint8(255 * cam), cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(img, 0.5, heatmap, 0.5, 0)
        result = {
            "label": label,
            "confidence": round(confidence, 4),
            "phishing_probability": round(phishing_prob, 4),
            "heatmap": None,
            "overlay": None,
        }
        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(save_path, overlay)
            result["overlay_path"] = save_path
        else:
            _, buffer = cv2.imencode(".png", overlay)
            result["overlay"] = buffer.tobytes()
        return result

    def explain_batch(self, image_paths: list, output_dir: str) -> list:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        results = []
        for path in image_paths:
            name = Path(path).stem
            save_path = os.path.join(output_dir, f"{name}_gradcam.png")
            res = self.explain(path, save_path=save_path)
            if res:
                filename = Path(path).name
                res["filename"] = filename
                results.append(res)
        return results
