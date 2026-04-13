"""Detect foreground window and enumerate running windowed apps.

Windows: ctypes calls to user32/kernel32/psapi.
macOS: Cocoa NSWorkspace via objc runtime.
"""
import sys


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

def _win_get_process_name(hwnd):
    """Get process executable name from a window handle."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return None

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False,
                                  pid.value)
    if not handle:
        return None
    try:
        buf = ctypes.create_unicode_buffer(260)
        size = wintypes.DWORD(260)
        kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size))
        path = buf.value
        if not path:
            return None
        # Extract filename without extension: "C:\...\Photoshop.exe" -> "Photoshop"
        import os
        return os.path.splitext(os.path.basename(path))[0]
    finally:
        kernel32.CloseHandle(handle)


def _win_foreground():
    """Return the process name of the foreground window on Windows."""
    import ctypes
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    if not hwnd:
        return None
    return _win_get_process_name(hwnd)


def _win_list_apps():
    """Enumerate visible top-level windows and return unique process names."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    names = set()

    # Filter out system processes
    _SKIP = {"explorer", "SearchHost", "SearchUI", "ShellExperienceHost",
             "StartMenuExperienceHost", "TextInputHost", "SystemSettings",
             "ApplicationFrameHost", "LockApp", "LogiOverlay"}

    def _enum_callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        name = _win_get_process_name(hwnd)
        if name and name not in _SKIP:
            names.add(name)
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND,
                                      wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(_enum_callback), 0)
    return sorted(names)


# ------------------------------------------------------------------ macOS

def _mac_foreground():
    """Return the process name of the foreground app on macOS."""
    try:
        import ctypes
        import ctypes.util

        objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
        objc.objc_msgSend.restype = ctypes.c_void_p
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.objc_getClass.restype = ctypes.c_void_p

        def sel(name):
            return objc.sel_registerName(name.encode())

        def msg(obj, selector):
            return objc.objc_msgSend(obj, sel(selector))

        NSWorkspace = objc.objc_getClass(b"NSWorkspace")
        ws = msg(NSWorkspace, "sharedWorkspace")
        app = msg(ws, "frontmostApplication")
        name_ns = msg(app, "localizedName")

        # Convert NSString to Python string
        CoreFoundation = ctypes.cdll.LoadLibrary(ctypes.util.find_library(
            "CoreFoundation"))
        CoreFoundation.CFStringGetCStringPtr.restype = ctypes.c_char_p
        CoreFoundation.CFStringGetCStringPtr.argtypes = [
            ctypes.c_void_p, ctypes.c_uint32]
        raw = CoreFoundation.CFStringGetCStringPtr(name_ns, 0)
        return raw.decode("utf-8") if raw else None
    except Exception:
        return None


def _mac_list_apps():
    """List running apps with visible windows on macOS."""
    try:
        import ctypes
        import ctypes.util

        objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
        objc.objc_msgSend.restype = ctypes.c_void_p
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.objc_getClass.restype = ctypes.c_void_p

        CoreFoundation = ctypes.cdll.LoadLibrary(ctypes.util.find_library(
            "CoreFoundation"))
        CoreFoundation.CFStringGetCStringPtr.restype = ctypes.c_char_p
        CoreFoundation.CFStringGetCStringPtr.argtypes = [
            ctypes.c_void_p, ctypes.c_uint32]

        def sel(name):
            return objc.sel_registerName(name.encode())

        def msg(obj, selector):
            return objc.objc_msgSend(obj, sel(selector))

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
