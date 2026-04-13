"""Detect foreground window and enumerate running windowed apps.

Windows: ctypes calls to user32/kernel32/psapi.
macOS: Cocoa NSWorkspace via objc runtime.
"""
import os
import sys

# System processes that are never meaningful app targets
_WIN_SYSTEM_APPS = {
    "explorer", "SearchHost", "SearchUI", "ShellExperienceHost",
    "StartMenuExperienceHost", "TextInputHost", "SystemSettings",
    "ApplicationFrameHost", "LockApp", "LogiOverlay",
}


def get_foreground_app():
    """Return the process name of the currently focused window, or None."""
    if sys.platform == "win32":
        return _win_foreground()
    if sys.platform == "darwin":
        return _mac_foreground()
    return None


def list_window_apps():
    """Return sorted list of unique app names with visible windows."""
    if sys.platform == "win32":
        return _win_list_apps()
    if sys.platform == "darwin":
        return _mac_list_apps()
    return []


# ------------------------------------------------------------------ Windows

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes
    _user32 = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32
    _PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def _win_get_process_name(hwnd):
    """Get process executable name from a window handle."""
    pid = wintypes.DWORD()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return None

    handle = _kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False,
                                   pid.value)
    if not handle:
        return None
    try:
        buf = ctypes.create_unicode_buffer(260)
        size = wintypes.DWORD(260)
        _kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size))
        path = buf.value
        if not path:
            return None
        return os.path.splitext(os.path.basename(path))[0]
    finally:
        _kernel32.CloseHandle(handle)


def _win_foreground():
    """Return the process name of the foreground window on Windows."""
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return None
    return _win_get_process_name(hwnd)


def _win_list_apps():
    """Enumerate visible top-level windows and return unique process names."""
    names = set()

    def _enum_callback(hwnd, _):
        if not _user32.IsWindowVisible(hwnd):
            return True
        if _user32.GetWindowTextLengthW(hwnd) == 0:
            return True
        name = _win_get_process_name(hwnd)
        if name and name not in _WIN_SYSTEM_APPS:
            names.add(name)
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND,
                                      wintypes.LPARAM)
    _user32.EnumWindows(WNDENUMPROC(_enum_callback), 0)
    return sorted(names)


# ------------------------------------------------------------------ macOS

def _mac_objc_bridge():
    """Load and configure the ObjC runtime and CoreFoundation libraries.

    Returns (objc, CoreFoundation, sel, msg) ready for use, or raises on
    any import / load failure.
    """
    import ctypes
    import ctypes.util

    objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
    objc.objc_msgSend.restype = ctypes.c_void_p
    objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    objc.sel_registerName.restype = ctypes.c_void_p
    objc.objc_getClass.restype = ctypes.c_void_p

    CoreFoundation = ctypes.cdll.LoadLibrary(
        ctypes.util.find_library("CoreFoundation"))
    CoreFoundation.CFStringGetCStringPtr.restype = ctypes.c_char_p
    CoreFoundation.CFStringGetCStringPtr.argtypes = [
        ctypes.c_void_p, ctypes.c_uint32]

    def sel(name):
        return objc.sel_registerName(name.encode())

    def msg(obj, selector):
        return objc.objc_msgSend(obj, sel(selector))

    return objc, CoreFoundation, sel, msg


def _mac_foreground():
    """Return the process name of the foreground app on macOS."""
    try:
        objc, CoreFoundation, sel, msg = _mac_objc_bridge()

        NSWorkspace = objc.objc_getClass(b"NSWorkspace")
        ws = msg(NSWorkspace, "sharedWorkspace")
        app = msg(ws, "frontmostApplication")
        name_ns = msg(app, "localizedName")

        raw = CoreFoundation.CFStringGetCStringPtr(name_ns, 0)
        return raw.decode("utf-8") if raw else None
    except Exception:
        return None


def _mac_list_apps():
    """List running apps with visible windows on macOS."""
    try:
        import ctypes
        objc, CoreFoundation, sel, msg = _mac_objc_bridge()

        # NSRunningApplication activation policy: 0 = regular (has UI)
        msg_int = ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_void_p,
                                   ctypes.c_void_p)

        NSWorkspace = objc.objc_getClass(b"NSWorkspace")
        ws = msg(NSWorkspace, "sharedWorkspace")
        apps = msg(ws, "runningApplications")
        count = msg_int(objc.objc_msgSend)(apps, sel("count"))

        msg_at = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_void_p, ctypes.c_ulong)
        names = set()
        for i in range(count):
            app = msg_at(objc.objc_msgSend)(apps, sel("objectAtIndex:"), i)
            policy = msg_int(objc.objc_msgSend)(app, sel("activationPolicy"))
            if policy != 0:
                continue
            name_ns = msg(app, "localizedName")
            if not name_ns:
                continue
            raw = CoreFoundation.CFStringGetCStringPtr(name_ns, 0)
            if raw:
                name = raw.decode("utf-8")
                if name and name not in ("Finder", "Dock"):
                    names.add(name)
        return sorted(names)
    except Exception:
        return []
