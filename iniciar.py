"""iniciar.py — arranque local sin credenciales distribuidas ni red pública."""
import socket
import os
import threading
import webbrowser

if __name__ == "__main__":
    os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")
    os.environ.setdefault("OPENCV_FFMPEG_LOGLEVEL", "-8")
    from access_app.main import create_app
    import uvicorn
    from access_app.paths import default_data_directory, resource_root
    from access_app.backups import import_data
    directory = default_data_directory()
    legacy = resource_root()/"data"
    if not (directory/"access.sqlite3").exists() and (legacy/"access.sqlite3").exists() and directory.resolve() != legacy.resolve():
        import_data(legacy, directory)
        print("Datos anteriores importados. La carpeta original se conservó.")
    app = create_app(directory)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    print("\nACCESO RESIDENCIAL · PILOTO LOCAL")
    print("La puerta es simulada. No hay prueba de vida validada.")
    if app.state.accounts.setup_required():
        print("Clave inicial (solo para crear la primera cuenta):")
        print(app.state.store.admin_token)
    print(f"\nPanel: http://127.0.0.1:{port}\nNo compartas esta clave ni cierres esta ventana.\n")
    threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    # No se expone al edificio/internet hasta definir autenticación por roles y TLS.
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False,
                           proxy_headers=False, limit_concurrency=32, timeout_keep_alive=5)
    uvicorn.Server(config).run(sockets=[sock])
