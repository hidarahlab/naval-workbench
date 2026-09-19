"""
navalcore.hull — Representasi bentuk lambung kapal.

Sistem koordinat (right-hand):
    x  : ke depan, nol di AP (aft perpendicular), positif ke FP
    y  : ke kanan (starboard), nol di garis tengah (centerline)
    z  : ke atas, nol di lunas/baseline

Kelas utama:
    Station        — Penampang melintang di satu posisi x
    ShipDimensions — Ukuran utama kapal
    HullForm       — Kumpulan stations yang membentuk lambung
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class Station:
    """Penampang melintang (transverse section) di posisi x dari AP.

    Menyimpan setengah-lebar (half-breadth) pada berbagai garis air.
    Nilai y adalah SETENGAH lebar — sisi kanan saja. Perhitungan
    luas/volume akan mengalikan dengan 2 untuk port + starboard.

    Args:
        x       : Jarak dari AP [m]
        offsets : Daftar (z, y_half) diurutkan z ascending [m, m]
                  z = tinggi dari baseline, y_half = setengah lebar
    """
    x: float
    offsets: List[Tuple[float, float]] = field(default_factory=list)

    def __post_init__(self):
        # Pastikan offsets terurut berdasarkan z (waterline height)
        self.offsets = sorted(self.offsets, key=lambda o: o[0])

    @property
    def z_values(self) -> List[float]:
        return [o[0] for o in self.offsets]

    @property
    def y_values(self) -> List[float]:
        return [o[1] for o in self.offsets]

    def y_at(self, z: float) -> float:
        """Interpolasi setengah-lebar pada tinggi waterline z [m].

        Di bawah offset terendah: diasumsikan y = 0 (sharp keel).
        Di atas offset tertinggi: diasumsikan y konstan (deck edge).
        Di antara: interpolasi linear.
        """
        zs = self.z_values
        ys = self.y_values

        if not zs:
            return 0.0
        if z <= zs[0]:
            # Interpolasi ke bawah menuju 0 (keel lancip)
            if zs[0] == 0.0:
                return ys[0]
            t = z / zs[0]
            return t * ys[0]
        if z >= zs[-1]:
            return ys[-1]

        # Interpolasi linear di antara dua titik terdekat
        for i in range(len(zs) - 1):
            if zs[i] <= z <= zs[i + 1]:
                dz = zs[i + 1] - zs[i]
                if dz == 0.0:
                    return ys[i]
                t = (z - zs[i]) / dz
                return ys[i] + t * (ys[i + 1] - ys[i])
        return 0.0

    def wetted_half_perimeter(self, draft: float) -> float:
        """Perkiraan setengah keliling basah (tanpa garis air) [m].

        Menghitung panjang kurva penampang dari baseline sampai draft,
        menggunakan panjang tali busur antar titik offset.
        """
        pts: List[Tuple[float, float]] = []

        # Mulai dari (z=0, y=0) kalau offset terendah bukan di baseline
        zs = self.z_values
        ys = self.y_values
        if zs and zs[0] > 0.0:
            pts.append((0.0, 0.0))

        for z, y in self.offsets:
            if z > draft:
                # Interpolasi titik tepat di waterline
                y_wl = self.y_at(draft)
                pts.append((draft, y_wl))
                break
            pts.append((z, y))
        else:
            # Semua offset di bawah draft: tambahkan titik di waterline
            y_wl = self.y_at(draft)
            pts.append((draft, y_wl))

        length = 0.0
        for i in range(len(pts) - 1):
            dz = pts[i + 1][0] - pts[i][0]
            dy = pts[i + 1][1] - pts[i][1]
            length += (dz ** 2 + dy ** 2) ** 0.5
        return length


@dataclass
class ShipDimensions:
    """Ukuran utama kapal.

    Args:
        LPP : Panjang antara garis tegak (Length Between Perpendiculars) [m]
        LWL : Panjang garis air (Length on Waterline) [m]
        B   : Lebar moulded maksimum [m]
        T   : Sarat rencana (design draught) [m]
    """
    LPP: float
    LWL: float
    B: float
    T: float

    def __post_init__(self):
        if self.LPP <= 0:
            raise ValueError(f"LPP harus positif, diterima: {self.LPP}")
        if self.B <= 0:
            raise ValueError(f"B harus positif, diterima: {self.B}")
        if self.T <= 0:
            raise ValueError(f"T harus positif, diterima: {self.T}")
        if self.LWL <= 0:
            self.LWL = self.LPP


@dataclass
class HullForm:
    """Bentuk lambung yang didefinisikan oleh kumpulan stations.

    Stations diurutkan dari AP (x=0) ke FP (x=LPP).

    Args:
        stations   : Daftar penampang melintang
        dimensions : Ukuran utama (opsional, diisi manual atau dari tabel offset)
        name       : Nama lambung / proyek
    """
    stations: List[Station] = field(default_factory=list)
    dimensions: Optional[ShipDimensions] = None
    name: str = "Unnamed Hull"

    def add_station(self, station: Station) -> None:
        """Tambah station dan pertahankan urutan x."""
        self.stations.append(station)
        self.stations.sort(key=lambda s: s.x)

    @property
    def n_stations(self) -> int:
        return len(self.stations)

    @property
    def x_stations(self) -> List[float]:
        return [s.x for s in self.stations]

    @property
    def all_waterlines(self) -> List[float]:
        """Semua ketinggian garis air unik dari seluruh stations, terurut."""
        zs: set = set()
        for st in self.stations:
            for z, _ in st.offsets:
                zs.add(z)
        return sorted(zs)

    @property
    def max_draft_defined(self) -> float:
        """Draft maksimum yang terdefinisi dari offset."""
        wls = self.all_waterlines
        return max(wls) if wls else 0.0

    def half_breadths_at_wl(self, z: float) -> Tuple[List[float], List[float]]:
        """Setengah-lebar di semua stations pada tinggi z.

        Returns:
            (x_list, y_half_list)
        """
        xs = self.x_stations
        ys = [st.y_at(z) for st in self.stations]
        return xs, ys

    def validate(self) -> List[str]:
        """Validasi sederhana dan kembalikan daftar peringatan."""
        warnings: List[str] = []
        if self.n_stations < 5:
            warnings.append(
                f"Jumlah station ({self.n_stations}) terlalu sedikit — "
                "akurasi integrasi rendah. Disarankan minimal 11 station."
            )
        if self.n_stations > 0:
            xs = self.x_stations
            if xs[0] != 0.0:
                warnings.append(
                    f"Station pertama ada di x={xs[0]:.3f}m, bukan di AP (x=0)."
                )
        if self.dimensions is not None:
            t_max = self.max_draft_defined
            if t_max < self.dimensions.T:
                warnings.append(
                    f"Sarat rencana T={self.dimensions.T}m melebihi "
                    f"waterline tertinggi di tabel offset ({t_max}m)."
                )
        return warnings
