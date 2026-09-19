"""
InitGui.py — Entry point GUI NavalWorkbench untuk FreeCAD.

File ini di-load otomatis oleh FreeCAD saat startup. Mendaftarkan
kelas workbench dan menambahkan toolbar + menu.
"""

import os
import sys

import FreeCAD
import FreeCADGui

# Pastikan direktori workbench ada di sys.path agar navalcore & commands
# bisa di-import tanpa path absolut.
_WB_DIR = os.path.dirname(os.path.abspath(__file__))
if _WB_DIR not in sys.path:
    sys.path.insert(0, _WB_DIR)


class NavalWorkbench(FreeCADGui.Workbench):
    """Naval Design Workbench — perancangan kapal di FreeCAD."""

    MenuText = "Naval"
    ToolTip  = "Naval Design Workbench — hidrostatik, tabel offset, stabilitas"
    Icon     = os.path.join(_WB_DIR, "icons", "naval_wb.svg")

    def Initialize(self):
        """Dipanggil sekali saat workbench pertama kali diaktifkan."""
        import commands.cmd_import_offsets   # mendaftarkan Naval_ImportOffsets
        import commands.cmd_hydrostatics     # mendaftarkan Naval_Hydrostatics

        # Daftar command yang masuk toolbar dan menu
        tools = [
            "Naval_ImportOffsets",
            "Naval_Hydrostatics",
        ]

        self.appendToolbar("Naval Tools", tools)
        self.appendMenu("Naval", tools)

        FreeCAD.Console.PrintLog(
            "[Naval] NavalWorkbench v0.1.0 dimuat.\n"
        )

    def Activated(self):
        """Dipanggil setiap kali pengguna berpindah ke workbench ini."""
        FreeCAD.Console.PrintMessage(
            "[Naval] NavalWorkbench aktif. "
            "Mulai dengan: Naval → Impor Tabel Offset.\n"
        )

    def Deactivated(self):
        """Dipanggil saat pengguna berpindah ke workbench lain."""
        pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"


FreeCADGui.addWorkbench(NavalWorkbench())
