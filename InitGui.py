"""
InitGui.py — Entry point GUI NavalWorkbench untuk FreeCAD.

CATATAN PENTING soal FreeCAD 1.1
--------------------------------
FreeCAD menjalankan file ini dengan exec() memakai dict globals dan locals
yang TERPISAH. Konsekuensinya:

  1. Variabel/fungsi yang didefinisikan di level modul masuk ke dict LOCALS.
  2. Class body dan fungsi mencari nama di dict GLOBALS (LOAD_NAME /
     LOAD_GLOBAL), sehingga TIDAK melihat isi dict locals tersebut.

Artinya:
  - Class body tidak boleh mereferensikan variabel level-modul.
  - Fungsi level-modul tidak boleh memanggil fungsi level-modul lain.

Solusi: SEMUA logika ditaruh dalam satu fungsi mandiri (_register), yang
melakukan import-nya sendiri. Pemanggilan _register() di baris terakhir
aman karena statement di level modul memakai LOAD_NAME yang memeriksa
dict locals terlebih dahulu.
"""


def _register():
    """Daftarkan NavalWorkbench ke FreeCAD. Sepenuhnya mandiri."""
    import os
    import sys

    import FreeCAD
    import FreeCADGui

    # -----------------------------------------------------------------
    # Tentukan direktori workbench tanpa bergantung pada __file__
    # -----------------------------------------------------------------
    wb_dir = None

    # Cara 1: __file__ tersedia (FreeCAD lama atau dijalankan normal)
    try:
        wb_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        pass

    # Cara 2: telusuri sys.path mencari folder berisi InitGui.py
    if not wb_dir or not os.path.isdir(wb_dir):
        for p in list(sys.path):
            try:
                candidate = os.path.join(p, "NavalWorkbench")
                if os.path.isfile(os.path.join(candidate, "InitGui.py")):
                    wb_dir = candidate
                    break
            except (TypeError, ValueError):
                continue

    # Cara 3: telusuri direktori Mod yang dikenal FreeCAD
    if not wb_dir or not os.path.isdir(wb_dir):
        bases = []
        try:
            bases.append(FreeCAD.getUserAppDataDir())
        except Exception:
            pass
        try:
            bases.append(FreeCAD.getHomePath())
        except Exception:
            pass
        for base in bases:
            candidate = os.path.join(base, "Mod", "NavalWorkbench")
            if os.path.isdir(candidate):
                wb_dir = candidate
                break

    if not wb_dir:
        FreeCAD.Console.PrintError(
            "[Naval] Gagal menemukan direktori NavalWorkbench.\n"
        )
        return

    if wb_dir not in sys.path:
        sys.path.insert(0, wb_dir)

    icon_path = os.path.join(wb_dir, "icons", "naval_wb.svg")

    # -----------------------------------------------------------------
    # Definisi workbench
    # -----------------------------------------------------------------
    class NavalWorkbench(FreeCADGui.Workbench):
        # Hanya nilai literal di sini — tidak ada referensi ke variabel luar.
        MenuText = "Naval"
        ToolTip = "Naval Design Workbench — hidrostatik, tabel offset, stabilitas"
        Icon = ""  # diisi setelah class didefinisikan

        def Initialize(self):
            import FreeCAD as _FC
            import traceback

            try:
                import commands.cmd_import_offsets  # noqa: F401
                import commands.cmd_hydrostatics    # noqa: F401
            except Exception:
                _FC.Console.PrintError(
                    "[Naval] Gagal memuat perintah:\n"
                    + traceback.format_exc()
                    + "\n"
                )
                return

            tools = [
                "Naval_ImportOffsets",
                "Naval_Hydrostatics",
            ]
            self.appendToolbar("Naval Tools", tools)
            self.appendMenu("Naval", tools)
            _FC.Console.PrintLog("[Naval] NavalWorkbench v0.1.0 dimuat.\n")

        def Activated(self):
            import FreeCAD as _FC
            _FC.Console.PrintMessage(
                "[Naval] NavalWorkbench aktif. "
                "Mulai dengan: Naval → Impor Tabel Offset.\n"
            )

        def Deactivated(self):
            pass

        def GetClassName(self):
            return "Gui::PythonWorkbench"

    # Isi Icon di luar class body — di sini variabel lokal fungsi terlihat.
    NavalWorkbench.Icon = icon_path

    FreeCADGui.addWorkbench(NavalWorkbench())


_register()
