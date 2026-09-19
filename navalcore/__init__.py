"""
navalcore — Mesin perhitungan perancangan kapal.

Modul ini sepenuhnya Python murni; tidak ada import FreeCAD di sini.
Tujuannya: bisa diuji dengan pytest tanpa FreeCAD, dan bisa dipakai
dari script / Jupyter Notebook secara mandiri.

Modul utama:
    hull          — Representasi bentuk lambung (stations + offsets)
    offset_reader — Baca tabel offset dari CSV
    hydrostatics  — Hitung sifat hidrostatik
"""

__version__ = "0.1.0"
__author__  = "Rahmad Hidayat"
__license__ = "LGPL-2.1"
