"""
InitGui.py — Entry point GUI NavalWorkbench untuk FreeCAD.
"""

import os
import sys

import FreeCAD
import FreeCADGui

# FreeCAD 1.1+ tidak selalu meng-set __file__ saat load InitGui.py
# Gunakan fallback ke direktori Mod
try:
    _WB_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _WB_DIR = os.path.join(
        FreeCAD.getUserAppDataDir(), "Mod", "NavalWorkbench"
    )

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
