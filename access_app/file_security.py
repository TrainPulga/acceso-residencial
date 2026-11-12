"""Permisos privados de datos y copias. No protege frente al control del SO."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path


def reject_link(path):
    path = Path(path)
    if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
        raise RuntimeError('Datos/claves no pueden ser enlaces o uniones a otra ubicación')


def private_path(path):
    path = Path(path)
    reject_link(path)
    if os.name != 'nt':
        os.chmod(path, 0o700 if path.is_dir() else 0o600)
        return
    # DACL explícita, sin herencia: cuenta Windows actual y SYSTEM.
    adv = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    P = ctypes.c_void_p
    adv.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    adv.OpenProcessToken.restype = wintypes.BOOL
    adv.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, P, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    adv.GetTokenInformation.restype = wintypes.BOOL
    adv.ConvertSidToStringSidW.argtypes = [P, ctypes.POINTER(wintypes.LPWSTR)]
    adv.ConvertSidToStringSidW.restype = wintypes.BOOL
    adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(P), P]
    adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
    adv.GetSecurityDescriptorDacl.argtypes = [P, ctypes.POINTER(wintypes.BOOL), ctypes.POINTER(P), ctypes.POINTER(wintypes.BOOL)]
    adv.GetSecurityDescriptorDacl.restype = wintypes.BOOL
    adv.SetNamedSecurityInfoW.argtypes = [wintypes.LPWSTR, ctypes.c_int, wintypes.DWORD, P, P, P, P]
    adv.SetNamedSecurityInfoW.restype = wintypes.DWORD
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.LocalFree.argtypes = [P]
    kernel.LocalFree.restype = P
    token, sid_text, descriptor = wintypes.HANDLE(), wintypes.LPWSTR(), P()
    def check(ok):
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())
    try:
        check(adv.OpenProcessToken(kernel.GetCurrentProcess(), 0x0008, ctypes.byref(token)))
        size = wintypes.DWORD()
        adv.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        if not size.value:
            raise ctypes.WinError(ctypes.get_last_error())
        buffer = ctypes.create_string_buffer(size.value)
        check(adv.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size)))
        sid = ctypes.cast(buffer, ctypes.POINTER(P))[0]
        check(adv.ConvertSidToStringSidW(sid, ctypes.byref(sid_text)))
        inherit = 'OICI' if path.is_dir() else ''
        sddl = f'D:P(A;{inherit};FA;;;SY)(A;{inherit};FA;;;{sid_text.value})'
        check(adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, ctypes.byref(descriptor), None))
        present, defaulted, dacl = wintypes.BOOL(), wintypes.BOOL(), P()
        check(adv.GetSecurityDescriptorDacl(descriptor, ctypes.byref(present), ctypes.byref(dacl), ctypes.byref(defaulted)))
        if not present.value or not dacl:
            raise RuntimeError('No se pudo construir una ACL privada')
        error = adv.SetNamedSecurityInfoW(str(path), 1, 0x80000004, None, None, dacl, None)
        if error:
            raise ctypes.WinError(error)
    finally:
        if descriptor:
            kernel.LocalFree(descriptor)
        if sid_text:
            kernel.LocalFree(ctypes.cast(sid_text, P))
        if token:
            kernel.CloseHandle(token)
