"""tests/test_vision_and_cameras.py — modelos reales sin identidades y validación de fuentes."""
from pathlib import Path
import numpy as np
import pytest
from access_app.cameras import validate_source
from access_app.vision import Vision


def test_actual_models_load_and_reject_empty_scene():
    models = Path(__file__).resolve().parents[1]/"models"
    engine = Vision(models)
    blank = np.zeros((480, 640, 3), np.uint8)
    assert engine.detect(blank) == []
    with pytest.raises(ValueError):
        engine.template(blank)


def test_recognition_graph_and_alignment_execute_on_artificial_pixels():
    # Ejecuta los operadores reales sin usar el rostro ni identidad de una persona.
    models = Path(__file__).resolve().parents[1]/"models"
    engine = Vision(models)
    image = np.tile(np.arange(256, dtype=np.uint8), (256, 1))
    image = np.stack([image, image.T, image], axis=2)
    landmarks = np.array([60, 50, 150, 160, 100, 100, 160, 100, 130, 135,
                          110, 170, 150, 170, .99], dtype=np.float32)
    crop = engine.recognizer.alignCrop(image, landmarks)
    feature = engine.recognizer.feature(crop)
    assert crop.shape == (112, 112, 3)
    assert feature.size == 128 and np.isfinite(feature).all()


@pytest.mark.parametrize("source", ["usb:0", "usb:3", "rtsp://192.168.1.2:554/live", "rtsps://10.0.0.2:322/video"])
def test_private_sources(source):
    validate_source(source)


@pytest.mark.parametrize("source", ["usb:-1", "file:///etc/passwd", "https://example.com", "http://8.8.8.8", "rtsp://169.254.169.254/feed"])
def test_public_or_invalid_sources_rejected(source):
    with pytest.raises(ValueError):
        validate_source(source)
