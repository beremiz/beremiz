#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

_developer_mode = False
_sdk_path = None

def GetDeveloperMode():
    global _developer_mode
    return _developer_mode

def SetDeveloperMode():
    global _developer_mode
    _developer_mode = True
    
def GetSDKPath():
    global _sdk_path
    return _sdk_path

def SetSDKPath(path):
    global _sdk_path
    _sdk_path = path
    # add path to sys.path
    if path not in sys.path:
        sys.path.insert(0, path)


# prevent garbage collection of the ctypes callback
_gtk_log_writer_ref = None


def SuppressGTKDiagnostics():
    """Install GLib structured log writer to suppress GTK WARNING/CRITICAL messages.

    wxWidgets + GTK3 known issue: AUI layout causes transient 0-size widget
    allocations that trigger GTK CSS assertions (GtkScrollbar/GtkNotebook)
    and layout loop warnings (gdk-frame-clock). These are harmless but
    produce noisy stderr output.

    Must be called before importing wx so that our writer is installed first.
    Uses g_log_set_writer_func via ctypes since wx.App.GTKSuppressDiagnostics
    is ineffective on GLib >= 2.50 when the structured logging API is active.
    """
    global _gtk_log_writer_ref

    if not sys.platform.startswith('linux'):
        return

    import ctypes
    import ctypes.util

    glib_path = ctypes.util.find_library('glib-2.0')
    if not glib_path:
        return

    glib = ctypes.CDLL(glib_path)

    GLogWriterFunc = ctypes.CFUNCTYPE(
        ctypes.c_int,       # GLogWriterOutput return
        ctypes.c_uint,      # GLogLevelFlags log_level
        ctypes.c_void_p,    # const GLogField *fields
        ctypes.c_size_t,    # gsize n_fields
        ctypes.c_void_p     # gpointer user_data
    )

    G_LOG_WRITER_HANDLED = 1
    G_LOG_LEVEL_CRITICAL = 1 << 3
    G_LOG_LEVEL_WARNING = 1 << 4

    glib.g_log_writer_default.restype = ctypes.c_int
    glib.g_log_writer_default.argtypes = [
        ctypes.c_uint, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p
    ]

    @GLogWriterFunc
    def gtk_log_writer(log_level, fields, n_fields, user_data):
        if log_level & (G_LOG_LEVEL_CRITICAL | G_LOG_LEVEL_WARNING):
            return G_LOG_WRITER_HANDLED
        return glib.g_log_writer_default(log_level, fields, n_fields, user_data)

    _gtk_log_writer_ref = gtk_log_writer

    try:
        glib.g_log_set_writer_func(gtk_log_writer, None, None)
    except Exception:
        pass