"""
commands.cmd_hydrostatics — Hitung tabel hidrostatik dan tampilkan hasilnya.

Perintah ini:
1. Mengambil objek lambung yang dipilih (atau yang ada di dokumen)
2. Menghitung tabel hidrostatik untuk rentang sarat
3. Membuat FreeCAD Spreadsheet berisi hasil
4. Mencetak ringkasan ke Report View
"""

import os
import sys

import FreeCAD
import FreeCADGui
from PySide2 import QtWidgets, QtCore

_WB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WB_DIR not in sys.path:
    sys.path.insert(0, _WB_DIR)

from navalcore.hydrostatics import compute, table, RHO_SW, RHO_FW, HydrostaticResult
from navalcore.hull import HullForm
from commands.cmd_import_offsets import NavalHullObject


# ---------------------------------------------------------------------------
# Dialog input sarat
# ---------------------------------------------------------------------------

class HydrostaticsDialog(QtWidgets.QDialog):
    """Dialog sederhana untuk memilih rentang sarat dan jenis air."""

    def __init__(self, t_max: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hitung Hidrostatik")
        self.setMinimumWidth(320)

        layout = QtWidgets.QFormLayout(self)

        self.spin_t_min = QtWidgets.QDoubleSpinBox()
        self.spin_t_min.setRange(0.01, t_max)
        self.spin_t_min.setValue(round(t_max * 0.3, 2))
        self.spin_t_min.setSuffix(" m")
        layout.addRow("Sarat minimum:", self.spin_t_min)

        self.spin_t_max = QtWidgets.QDoubleSpinBox()
        self.spin_t_max.setRange(0.01, t_max)
        self.spin_t_max.setValue(round(t_max, 2))
        self.spin_t_max.setSuffix(" m")
        layout.addRow("Sarat maksimum:", self.spin_t_max)

        self.spin_steps = QtWidgets.QSpinBox()
        self.spin_steps.setRange(2, 50)
        self.spin_steps.setValue(10)
        layout.addRow("Jumlah langkah:", self.spin_steps)

        self.combo_water = QtWidgets.QComboBox()
        self.combo_water.addItem("Air Laut  (ρ = 1.025 t/m³)", RHO_SW)
        self.combo_water.addItem("Air Tawar (ρ = 1.000 t/m³)", RHO_FW)
        layout.addRow("Jenis air:", self.combo_water)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    @property
    def t_min(self) -> float:
        return self.spin_t_min.value()

    @property
    def t_max(self) -> float:
        return self.spin_t_max.value()

    @property
    def n_steps(self) -> int:
        return self.spin_steps.value()

    @property
    def rho(self) -> float:
        return self.combo_water.currentData()


# ---------------------------------------------------------------------------
# Tulis ke FreeCAD Spreadsheet
# ---------------------------------------------------------------------------

def _write_to_spreadsheet(
    results: list,
    name: str = "Hidrostatik",
) -> object:
    """Buat atau ganti spreadsheet di dokumen aktif."""
    doc = FreeCAD.ActiveDocument
    if doc is None:
        return None

    # Hapus spreadsheet lama jika ada
    existing = doc.getObjectsByLabel(name)
    for obj in existing:
        doc.removeObject(obj.Name)

    sheet = doc.addObject("Spreadsheet::Sheet", name)
    sheet.Label = name

    if not results:
        return sheet

    headers = list(results[0].to_dict().keys())

    # Baris header
    for col, h in enumerate(headers):
        cell = _col_letter(col) + "1"
        sheet.set(cell, h)

    # Data
    for row, r in enumerate(results):
        data = r.to_dict()
        for col, key in enumerate(headers):
            cell = _col_letter(col) + str(row + 2)
            sheet.set(cell, str(data[key]))

    doc.recompute()
    return sheet


def _col_letter(n: int) -> str:
    """Konversi indeks kolom (0-based) ke huruf Excel: 0→A, 25→Z, 26→AA."""
    result = ""
    n += 1
    while n > 0:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


# ---------------------------------------------------------------------------
# Dapatkan HullForm dari dokumen
# ---------------------------------------------------------------------------

def _get_hull_from_doc() -> HullForm | None:
    """Cari objek lambung di dokumen aktif."""
    doc = FreeCAD.ActiveDocument
    if doc is None:
        return None

    # Cek seleksi aktif dulu
    sel = FreeCADGui.Selection.getSelection()
    for obj in sel:
        if hasattr(obj, "Proxy") and isinstance(obj.Proxy, NavalHullObject):
            return obj.Proxy.hull()

    # Cari di seluruh dokumen
    for obj in doc.Objects:
        if hasattr(obj, "Proxy") and isinstance(obj.Proxy, NavalHullObject):
            return obj.Proxy.hull()

    return None


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class HydrostaticsCommand:
    """Hitung tabel hidrostatik dari lambung aktif."""

    def GetResources(self):
        icon = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "icons", "naval_wb.svg"
        )
        return {
            "MenuText": "Hitung Hidrostatik",
            "ToolTip":  (
                "Hitung tabel hidrostatik (volume, displacement, KM, TPC, MCT, "
                "koefisien blok, dll.) untuk rentang sarat yang dipilih."
            ),
            "Pixmap":   icon,
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        hull = _get_hull_from_doc()

        if hull is None:
            QtWidgets.QMessageBox.warning(
                FreeCADGui.getMainWindow(),
                "Tidak Ada Lambung",
                "Tidak ditemukan objek lambung di dokumen.\n"
                "Impor tabel offset terlebih dahulu.",
            )
            return

        t_max = hull.max_draft_defined
        if hull.dimensions and hull.dimensions.T > 0:
            t_max = max(t_max, hull.dimensions.T)

        dlg = HydrostaticsDialog(
            t_max   = t_max,
            parent  = FreeCADGui.getMainWindow(),
        )
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        rho    = dlg.rho
        n      = dlg.n_steps
        t_min  = dlg.t_min
        t_range = dlg.t_max

        step = (t_range - t_min) / max(n - 1, 1)
        drafts = [t_min + i * step for i in range(n)]

        FreeCAD.Console.PrintMessage(
            f"\n[Naval] Menghitung hidrostatik '{hull.name}' "
            f"T={t_min:.2f}..{t_range:.2f}m ({n} langkah) "
            f"ρ={rho} t/m³...\n"
        )

        results = table(hull, drafts=drafts, rho=rho)

        # Tulis ke spreadsheet
        sheet = _write_to_spreadsheet(results, name=f"Hidro_{hull.name}")
        if sheet:
            FreeCAD.Console.PrintMessage(
                f"[Naval] ✓ Tabel ditulis ke Spreadsheet '{sheet.Label}'\n"
            )

        # Cetak satu baris ringkasan untuk sarat rencana (atau sarat tengah)
        if hull.dimensions and hull.dimensions.T > 0:
            t_design = hull.dimensions.T
        else:
            t_design = drafts[len(drafts) // 2]

        try:
            r_design = compute(hull, draft=t_design, rho=rho)
            FreeCAD.Console.PrintMessage(r_design.summary())
        except Exception as e:
            FreeCAD.Console.PrintWarning(
                f"[Naval] Tidak dapat mencetak ringkasan sarat rencana: {e}\n"
            )


FreeCADGui.addCommand("Naval_Hydrostatics", HydrostaticsCommand())
