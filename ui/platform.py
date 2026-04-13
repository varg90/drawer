# ui/platform.py
"""Platform-specific window tweaks (macOS native resize, etc.)."""
import sys


def setup_frameless_native(widget):
    """On macOS, convert a frameless Qt window to a native 'fake frameless'
    window that keeps OS-managed resize handles while hiding the titlebar.

    Call AFTER the widget has been shown (so winId() is valid).
    On non-macOS platforms this is a no-op.
    """
    if sys.platform != "darwin":
        return False

    try:
        import ctypes
        import ctypes.util

        objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
        objc.objc_msgSend.restype = ctypes.c_void_p
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        objc.sel_registerName.restype = ctypes.c_void_p

        def sel(name):
            return objc.sel_registerName(name.encode())

        def msg(obj, selector, *args):
            return objc.objc_msgSend(obj, sel(selector), *args)

        # Bool-returning variant
        msg_bool = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        # Get NSView -> NSWindow
        view_ptr = int(widget.winId())
        ns_window = msg(view_ptr, "window")
        if not ns_window:
            return False

        # Get current style mask
        msg_ulong = ctypes.CFUNCTYPE(
            ctypes.c_ulong, ctypes.c_void_p, ctypes.c_void_p)
        current_mask = msg_ulong(objc.objc_msgSend)(ns_window, sel("styleMask"))

        # NSWindowStyleMask flags
        Titled = 1 << 0
        Resizable = 1 << 3
        FullSizeContentView = 1 << 15

        new_mask = current_mask | Titled | Resizable | FullSizeContentView

        # setStyleMask:
        msg_set = ctypes.CFUNCTYPE(
            None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong)
        msg_set(objc.objc_msgSend)(ns_window, sel("setStyleMask:"), new_mask)

        # setTitlebarAppearsTransparent: YES
        msg_set_bool = ctypes.CFUNCTYPE(
            None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool)
        msg_set_bool(objc.objc_msgSend)(
            ns_window, sel("setTitlebarAppearsTransparent:"), True)

        # setTitleVisibility: NSWindowTitleHidden (1)
        msg_set_int = ctypes.CFUNCTYPE(
            None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long)
        msg_set_int(objc.objc_msgSend)(
            ns_window, sel("setTitleVisibility:"), 1)

        # setMovableByWindowBackground: NO (we handle drag ourselves)
        msg_set_bool(objc.objc_msgSend)(
            ns_window, sel("setMovableByWindowBackground:"), False)

        # Hide the standard window buttons (close/minimize/zoom)
        for button_type in range(3):  # 0=close, 1=miniaturize, 2=zoom
            msg_get_btn = ctypes.CFUNCTYPE(
                ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                ctypes.c_ulong)
            btn = msg_get_btn(objc.objc_msgSend)(
                ns_window,
                sel("standardWindowButton:"),
                button_type)
            if btn:
                msg_set_bool(objc.objc_msgSend)(
                    btn, sel("setHidden:"), True)

        return True
    except Exception:
        return False
