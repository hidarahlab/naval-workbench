"""
InitGui.py — Entry point GUI NavalWorkbench untuk FreeCAD.
"""

import os
import sys

import FreeCAD
import FreeCADGui


def _get_wb_dir():
    """Dapatkan direktori workbench secara aman tanpa bergantung pada __file__."""
    # Cara 1: __file__ tersedia (FreeCAD lama / dev mode)
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        pass
    # Cara 2: cari di sys.path berdasarkan keberadaan InitGui.py
    for p in sys.path:
        candidate = os.path.join(p, "NavalWorkbench")
        if os.path.isfile(os.path.join(candidate, "InitGui.py")):
            return candidate
    # Cara 3: fallback ke direktori Mod standar
    return os.path.join(FreeCAD.getUserAppDataDir(), "Mod", "NavalWorkbench")


_WB_DIR = _get_wb_dir()

if _WB_DIR not in sys.path:
    sys.path.insert(0, _WB_DIR)


class NavalWorkbench(FreeCADGui.Workbench):
    MenuText = "Naval"
    ToolTip  = "Naval Design Workbench — hidrostatik, tabel offset, stabilitas"
    Icon     = os.path.join(_WB_DIR, "icons", "naval_wb.svg")

    def Initialize(self):
        import commands.cmd_import_offsets
        import commands.cmd_hydrostatics

        tools = [
            "Naval_ImportOffsets",
            "Naval_Hydrostatics",
        ]
        self.appendToolbar("Naval Tools", tools)
        self.appendMenu("Naval", tools)
        FreeCAD.Console.PrintLog("[Naval] NavalWorkbench v0.1.0 dimuat.\n")

    def Activated(self):
        FreeCAD.Console.PrintMessage(
            "[Naval] NavalWorkbench aktif. "
            "Mulai dengan: Naval → Impor Tabel Offset.\n"
        )

    def Deactivated(self):
        pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"


FreeCADGui.addWorkbench(NavalWorkbench())
