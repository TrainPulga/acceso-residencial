"""access_app/vision.py — YuNet/SFace, sin PAD ni afirmaciones de identidad infalible."""
import base64
import hashlib
import io
import json
import threading
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from access_app.domain import unit


def decode_image(encoded):
    if len(encoded) > 5_600_000:
        raise ValueError("Imagen demasiado grande. Usá una captura de hasta 4 MB.")
    try:
        if encoded.startswith("data:"):
            encoded = encoded.split(",", 1)[1]
        data = base64.b64decode(encoded, validate=True)
        with Image.open(io.BytesIO(data)) as im:
            if im.format not in {'JPEG', 'PNG'}:
                raise ValueError('Solo se admiten imágenes JPEG o PNG')
            if im.width * im.height > 12_000_000 or min(im.size) < 64:
                raise ValueError("Resolución no admitida")
            im.verify()
        image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Archivo no reconocido")
        return image
    except (ValueError, OSError, IndexError, Image.DecompressionBombError, cv2.error) as exc:
        raise ValueError("La captura no es una imagen válida o tiene resolución excesiva") from exc


class Vision:
    def __init__(self, models):
        models = Path(models)
        for item in json.loads((models / "manifest.json").read_text()):
            data = (models / item["file"]).read_bytes()
            if hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise RuntimeError("Modelo facial incompleto o modificado. Restaurá el paquete.")
        self.detector = cv2.FaceDetectorYN.create(
            str(models / "face_detection_yunet_2023mar.onnx"), "", (320, 320), 0.85, 0.3, 5000)
        self.recognizer = cv2.FaceRecognizerSF.create(
            str(models / "face_recognition_sface_2021dec.onnx"), "")
        self.lock = threading.RLock()

    def detect(self, image):
        h, w = image.shape[:2]
        scale = min(1.0, 1280 / max(h, w))
        small = cv2.resize(image, (round(w * scale), round(h * scale))) if scale < 1 else image
        with self.lock:
            self.detector.setInputSize((small.shape[1], small.shape[0]))
            _, faces = self.detector.detect(small)
        if faces is None:
            return []
        faces = faces.copy()
        faces[:, :14] /= scale
        return list(faces)

    @staticmethod
    def boxes(faces):
        return [{"x": float(f[0]), "y": float(f[1]), "w": float(f[2]), "h": float(f[3])}
                for f in faces]

    def template(self, image):
        faces = self.detect(image)
        if len(faces) != 1:
            raise ValueError("Debe verse exactamente un rostro, sin otras personas en el encuadre")
        face = faces[0]
        if min(face[2], face[3]) < 80:
            raise ValueError("Acercate: el rostro ocupa muy pocos píxeles")
        h, w = image.shape[:2]
        x, y, fw, fh = (int(v) for v in face[:4])
        if x < 0 or y < 0 or x + fw > w or y + fh > h:
            raise ValueError("Se ve un rostro recortado. Centrate en el encuadre")
        gray = cv2.cvtColor(image[y:y+fh, x:x+fw], cv2.COLOR_BGR2GRAY)
        if gray.mean() < 35 or gray.mean() > 225:
            raise ValueError("Ajustá la iluminación del rostro")
        if cv2.Laplacian(gray, cv2.CV_64F).var() < 35:
            raise ValueError("La imagen está poco definida. Mantené la cámara estable")
        with self.lock:
            crop = self.recognizer.alignCrop(image, face)
            feature = self.recognizer.feature(crop).flatten()
        return unit(feature), self.boxes(faces)
