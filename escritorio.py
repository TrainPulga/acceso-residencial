"""escritorio.py — ventana nativa Windows/Qt para el prototipo local."""
import os
from pathlib import Path
import sys

os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")
os.environ.setdefault("OPENCV_FFMPEG_LOGLEVEL", "-8")

from PySide6.QtCore import QLockFile, QTimer, QUrl, Qt
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (QApplication, QDialog, QFileDialog, QHBoxLayout, QLabel,
                               QLineEdit, QMainWindow, QMessageBox, QPushButton, QVBoxLayout)
from PySide6.QtWebEngineCore import (QWebEnginePage, QWebEnginePermission, QWebEngineProfile,
                                    QWebEngineUrlRequestInterceptor)
from PySide6.QtWebEngineWidgets import QWebEngineView

from access_app.backups import create_backup, import_data
from access_app.main import create_app
from access_app.paths import APP_VERSION, default_data_directory, resource_root
from access_app.runtime import LocalServer


def same_origin(url, origin):
    return url.scheme() == origin.scheme() and url.host() == origin.host() and url.port() == origin.port()


class PrivateRequests(QWebEngineUrlRequestInterceptor):
    def __init__(self, origin, parent):
        super().__init__(parent)
        self.origin = origin

    def interceptRequest(self, info):
        url = info.requestUrl()
        if url.scheme() not in {"data", "blob", "about"} and not same_origin(url, self.origin):
            info.block(True)


class LocalPage(QWebEnginePage):
    def __init__(self, profile, parent, origin):
        super().__init__(profile, parent)
        self.origin = origin

    def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
        return same_origin(url, self.origin) or url.toString() == "about:blank"

    def createWindow(self, window_type):
        return None


class DesktopWindow(QMainWindow):
    def __init__(self, service, data_directory):
        super().__init__()
        self.service, self.data_directory = service, data_directory
        self.setWindowTitle("Acceso Residencial · Escritorio "+APP_VERSION)
        self.resize(1440, 940)
        self.setMinimumSize(1000, 700)
        self.origin = QUrl(service.origin)
        self.profile = QWebEngineProfile(self)  # Perfil efímero: no persiste cookies ni caché.
        self.interceptor = PrivateRequests(self.origin, self.profile)
        self.profile.setUrlRequestInterceptor(self.interceptor)
        self.profile.downloadRequested.connect(self.download)
        self.view = QWebEngineView(self)
        self.page = LocalPage(self.profile, self.view, self.origin)
        self.page.permissionRequested.connect(self.permission)
        self.view.setPage(self.page)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.setCentralWidget(self.view)
        menu = self.menuBar().addMenu("Aplicación")
        for title, callback in (("Clave de configuración inicial", self.show_key),
                                ("Crear respaldo…", lambda: self.with_admin(self.backup)),
                                ("Abrir carpeta de datos", lambda: self.with_admin(self.open_data)),
                                ("Información de la versión", self.about)):
            action = QAction(title, self)
            action.triggered.connect(callback)
            menu.addAction(action)
        self.statusBar().showMessage("Procesamiento local · Datos persistentes · Piloto sin apertura física")
        self.view.loadFinished.connect(self.loaded)
        self.first_load = True
        self.view.setUrl(self.origin)

    def loaded(self, ok):
        if not ok:
            self.statusBar().showMessage("No se pudo cargar el panel. Cerrá y volvé a abrir la aplicación.")
        elif self.first_load:
            self.first_load = False
            if self.service.app.state.accounts.setup_required():
                QTimer.singleShot(150, self.show_key)

    def show_key(self):
        if not self.service.app.state.accounts.setup_required():
            QMessageBox.information(self, "Cuentas configuradas", "Ingresá con tu usuario y contraseña. "
                                    "La clave inicial ya no inicia sesión ni crea nuevas cuentas.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Clave de configuración inicial")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Copiá esta clave y usala en Crear primer administrador.\n"
                                "Después ingresarás con tu usuario y contraseña. No compartas esta clave."))
        field = QLineEdit(self.service.app.state.store.admin_token)
        field.setReadOnly(True)
        field.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(field)
        buttons = QHBoxLayout()
        copy = QPushButton("Copiar clave")
        def copy_key():
            secret = field.text()
            QApplication.clipboard().setText(secret)
            QTimer.singleShot(30000, lambda: QApplication.clipboard().clear()
                              if QApplication.clipboard().text() == secret else None)
            copy.setText("Copiada")
        copy.clicked.connect(copy_key)
        close = QPushButton("Cerrar y entrar al panel")
        close.clicked.connect(dialog.accept)
        buttons.addWidget(copy)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        dialog.exec()

    def permission(self, request):
        if (same_origin(request.origin(), self.origin) and
                request.permissionType() == QWebEnginePermission.PermissionType.MediaVideoCapture):
            answer = QMessageBox.question(self, "Permiso de cámara", "¿Permitir que esta aplicación use la cámara?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            request.grant() if answer == QMessageBox.StandardButton.Yes else request.deny()
        else:
            request.deny()

    def with_admin(self, callback):
        def checked(token):
            try:
                user = self.service.app.state.accounts.resolve(token or "")
                if user["role"] != "admin" or user["force_change"]:
                    raise ValueError("Esta opción requiere una sesión de Administración")
                callback()
            except Exception as exc:
                QMessageBox.warning(self, "Permiso requerido", str(exc))
        self.page.runJavaScript("sessionStorage.getItem('access-token') || ''", checked)

    def download(self, request):
        if request.url().scheme() != "blob" and not same_origin(request.url(), self.origin):
            request.cancel()
            return
        suggested = request.suggestedFileName()
        file_filter = ("Video WebM (*.webm)" if suggested.lower().endswith(".webm") else
                       "Informe HTML (*.html)" if suggested.lower().endswith(".html") else "JSON (*.json)")
        path, _ = QFileDialog.getSaveFileName(self, "Guardar evidencia experimental", suggested, file_filter)
        if path:
            request.setDownloadDirectory(str(Path(path).parent))
            request.setDownloadFileName(Path(path).name)
            request.accept()
        else:
            request.cancel()

    def backup(self):
        destination = QFileDialog.getExistingDirectory(self, "Elegí dónde guardar el respaldo privado")
        if not destination:
            return
        try:
            with self.service.app.state.store.lock:
                result = create_backup(self.data_directory, destination)
            QMessageBox.information(self, "Respaldo creado", "Base y claves verificadas en:\n"+str(result)+
                                    "\nProtegé esta carpeta: permite recuperar datos personales.")
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo crear el respaldo", str(exc))

    def open_data(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.data_directory)))

    def about(self):
        QMessageBox.information(self, "Acerca de Acceso Residencial", "Versión "+APP_VERSION+
            "\nEscritorio local. Modelo SFace conservado.\nNo abre puertas ni incluye PAD validado.\n"
            "Visitas, usuarios, restricciones revisables y auditoría local disponibles.\nDatos: "+str(self.data_directory))

    def closeEvent(self, event):
        self.view.stop()
        self.page.deleteLater()
        self.service.stop()
        event.accept()


def prepare_first_run(directory):
    if (directory/"access.sqlite3").exists():
        return True
    legacy = resource_root()/"data"
    if (legacy/"access.sqlite3").exists() and legacy.resolve() != directory.resolve():
        question = "Se encontraron datos de la versión anterior junto al programa. ¿Querés importarlos?"
    else:
        question = "¿Tenés registros o un respaldo de una versión anterior para importar?"
    answer = QMessageBox.question(None, "Primera apertura", question,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
        QMessageBox.StandardButton.Yes)
    if answer == QMessageBox.StandardButton.Cancel:
        return False
    if answer == QMessageBox.StandardButton.Yes:
        source = str(legacy) if (legacy/"access.sqlite3").exists() else QFileDialog.getExistingDirectory(
            None, "Elegí la carpeta data anterior o un respaldo verificado")
        if not source:
            return False
        import_data(source, directory)
        QMessageBox.information(None, "Importación completada", "Se copiaron los datos. La carpeta original se conservó.")
    return True


def main():
    gui = QApplication(sys.argv)
    gui.setApplicationName("Acceso Residencial")
    gui.setApplicationVersion(APP_VERSION)
    directory = default_data_directory()
    directory.parent.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(directory.parent/"desktop.lock"))
    if not lock.tryLock(0):
        QMessageBox.information(None, "Aplicación abierta", "Ya hay una instancia usando esta instalación. "
                                "Cerrá la ventana de la versión anterior y volvé a abrir esta versión.")
        return 1
    service = None
    try:
        if not prepare_first_run(directory):
            return 0
        app = create_app(directory)
        service = LocalServer(app)
        service.start()
        window = DesktopWindow(service, directory)
        window.show()
        return gui.exec()
    except Exception as exc:
        QMessageBox.critical(None, "No se pudo iniciar", str(exc))
        return 1
    finally:
        if service is not None and service.thread.is_alive():
            service.stop()
        lock.unlock()


if __name__ == "__main__":
    sys.exit(main())
