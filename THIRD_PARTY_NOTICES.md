# Componentes externos

Se incluyen los siguientes pesos y textos de licencia de OpenCV Zoo y Open Model Zoo:

| Componente | Archivo | Licencia incluida |
|---|---|---|
| YuNet | face_detection_yunet_2023mar.onnx | MIT, models/face_detection_yunet_LICENSE |
| SFace | face_recognition_sface_2021dec.onnx | Apache-2.0, models/face_recognition_sface_LICENSE |
| anti-spoof-mn3 (Prokofev Kirill / Open Model Zoo) | models/pad/anti-spoof-mn3.onnx | MIT, models/pad/LICENSE-MIT.txt |

Los hashes y fuentes están en models/manifest.json. No modificar o quitar los avisos de licencia al redistribuir los pesos. Las métricas publicadas por sus autores no se presentan como métricas de este proyecto.

Las dependencias Python se instalan desde requirements.txt y conservan sus respectivas licencias. No se incluyen datasets de residentes, fotografías de terceros, claves ni contraseñas en esta distribución. El código específico del proyecto no se publica automáticamente en ningún repositorio o sitio mediante esta entrega.

## Escritorio 0.3

PySide6/Qt y Qt WebEngine se instalan desde requirements-desktop.txt; sus bibliotecas no se incluyen dentro de este ZIP de código fuente. Conservar sus licencias, avisos de terceros y obligaciones aplicables al preparar una distribución binaria. Qt WebEngine incorpora Chromium y componentes con avisos propios. No se afirma que la receta de build por sí sola complete una revisión de distribución.

Fuentes oficiales: https://doc.qt.io/qtforpython-6/licenses.html y https://doc.qt.io/qt-6/qtwebengine-licensing.html . PyInstaller se usa únicamente en la receta de compilación opcional; consultar su licencia oficial al redistribuir.

## PAD 0.7

anti-spoof-mn3 model from Open Model Zoo (OpenVINO Toolkit). Aviso MIT del autor incluido sin modificar. Descargado como ONNX original desde la fuente de Open Model Zoo; tamaño y SHA-384 coinciden con model.yml publicado. SHA-256, origen y contrato en models/pad/manifest.json. No se convierte ni se redistribuye el dataset CelebA-Spoof: se incluyen solo los pesos publicados. Las métricas de referencia del autor no son resultados locales ni una garantía comercial.

Fuente: https://github.com/openvinotoolkit/open_model_zoo/tree/master/models/public/anti-spoof-mn3 ; autor: https://github.com/kprokofi/light-weight-face-anti-spoofing . No usar las marcas Intel/OpenVINO como marca de este producto.
