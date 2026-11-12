"""lanzar_escritorio.pyw — errores visibles aun cuando Python no tiene consola."""
import sys

try:
    from escritorio import main
    sys.exit(main())
except Exception as exc:
    message = "No se pudo abrir Acceso Residencial.\n\n"+type(exc).__name__+": "+str(exc)
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, "Acceso Residencial", 0x10)
    else:
        print(message, file=sys.stderr)
    sys.exit(1)
