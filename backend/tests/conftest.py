import io
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from PIL import Image, ImageDraw
import numpy as np


@pytest.fixture
def valid_phishing_image_bytes():
    """Create a synthetic RGB image (224x224) that simulates a phishing page."""
    img = Image.new("RGB", (224, 224), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 200, 60], fill=(0, 0, 200))
    draw.rectangle([50, 100, 180, 140], fill=(200, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def valid_legitimate_image_bytes():
    """Create a synthetic RGB image (224x224) that simulates a legitimate page."""
    img = Image.new("RGB", (224, 224), color=(240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def invalid_image_bytes():
    """Random bytes that is not a valid image."""
    return b"\x00\x01\x02\x03\x04\x05" * 100


@pytest.fixture
def empty_bytes():
    return b""


@pytest.fixture
def large_image_bytes():
    """Create an image larger than the 20MB limit."""
    n = 3000
    arr = np.random.randint(0, 255, (n, n, 3), dtype=np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def unsupported_format_bytes():
    """Bytes with an unsupported magic header."""
    return b"\x00\x00\x00\x00" + b"test" * 100
