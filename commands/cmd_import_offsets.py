"""
commands.cmd_import_offsets — Impor tabel offset dari CSV ke dokumen FreeCAD.

Perintah ini membuka dialog file, membaca CSV tabel offset,
menyimpan data ke dokumen FreeCAD sebagai objek Python, dan
mencetak ringkasan ke Report View.
"""

import os
import sys

import FreeCAD
import FreeCADGui
from PySide2 import QtWidgets

# Tambahkan root workbench ke sys.path
_WB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WB_DIR not in sys.path:
    sys.path.insert(0, _WB_DIR)

from navalcore.offset_reader import read_offset_table
from navalcore.hull import HullForm


# ---------------------------------------------------------------------------
# FreeCAD Document Object — menyimpan HullForm
# ---------------------------------------------------------------------------

class NavalHullObject:
    """Objek FreeCAD yang menyimpan data lambung kapal."""

    def __init__(self, obj, hull: HullForm):
        obj.Proxy = self
        self._hull = hull
        obj.addProperty(
            "App::PropertyString", "HullName", "Naval", "Nama lambung"
        ).HullName = hull.name
        obj.addProperty(
            "App::PropertyInteger", "NStations", "Naval", "Jumlah station"
        ).NStations = hull.n_stations
        if hull.dimensions:
            d = hull.dimensions
            obj.addProperty(
                "App::PropertyFloat", "LPP", "Naval", "Panjang antara garis tegak [m]"
            ).LPP = d.LPP
            obj.addProperty(
                "App::PropertyFloat", "Breadth", "Naval", "Lebar moulded [m]"
            ).Breadth = d.B
            obj.addProperty(
                "App::PropertyFloat", "DesignDraft", "Naval", "Sarat rencana [m]"
            ).DesignDraft = d.T

    def hull(self) -> HullForm:
        return self._hull

    def execute(self, obj):
        pass


class NavalHullViewObject:
    """View provider untuk NavalHullObject."""

    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        icon = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "icons", "naval_wb.svg"
        )
        return icon

    def attach(self, vobj):
        pass

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None


def create_hull_object(hull: HullForm) -> object:
    """Buat NavalHullObject di dokumen aktif dan kembalikan proxy-nya."""
    doc = FreeCAD.ActiveDocument
    if doc is None:
        doc = FreeCAD.newDocument("NavalProject")

    obj = doc.addObject("App::FeaturePython", "HullForm")
    NavalHullObject(obj, hull)
    NavalHullViewObject(obj.ViewObject)
    doc.recompute()
    return obj


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class ImportOffsetsCommand:
    """Impor tabel offset kapal dari file CSV."""

    def GetResources(self):
        icon = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "icons", "naval_wb.svg"
        )
        return {
            "MenuText": "Impor Tabel Offset",
            "ToolTip":  (
                "Baca tabel offset (setengah lebar) dari file CSV "
                "dan simpan sebagai objek lambung kapal."
            ),
            "Pixmap":   icon,
        }

    def IsActive(self):
        return True

    def Activated(self):
        # Buka dialog pemilih file
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent    = FreeCADGui.getMainWindow(),
            caption   = "Buka Tabel Offset",
            filter    = "CSV Files (*.csv);;All Files (*)",
        )
        if not filepath:
            return  # Pengguna batal

        try:
            hull = read_offset_table(filepath)
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                FreeCADGui.getMainWindow(),
                "Error: Baca Tabel Offset",
                f"Gagal membaca file:\n{e}",
            )
            return

        # Tampilkan peringatan jika ada
        warnings = hull.validate()
        for w in warnings:
            FreeCAD.Console.PrintWarning(f"[Naval] ⚠ {w}\n")

        # Buat objek di dokumen
        obj = create_hull_object(hull)

        # Ringkasan ke Report View
        d = hull.dimensions
        dim_str = (
            f"LPP={d.LPP}m  B={d.B}m  T={d.T}m"
            if d else "ukuran tidak diketahui"
        )
        FreeCAD.Console.PrintMessage(
            f"\n[Naval] ✓ Tabel offset '{hull.name}' berhasil dimuat.\n"
            f"         {hull.n_stations} stations — {dim_str}\n"
            f"         Objek: {obj.Name}\n"
        )

        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(obj)


FreeCADGui.addCommand("Naval_ImportOffsets", ImportOffsetsCommand())
