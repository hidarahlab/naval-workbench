"""
navalcore.offset_reader — Baca tabel offset dari file CSV.

Mendukung dua format umum yang dipakai di buku teks perkapalan Indonesia:

Format 1 — Matrix (paling umum di buku teks):
    Baris pertama: "waterline,AP,1,2,...,FP"
    Baris berikut: nilai_wl,y_AP,y_1,...,y_FP

    Contoh:
        waterline,AP,1,2,3,4,5,6,7,8,9,FP
        0.0,0.00,0.85,1.92,2.50,2.80,2.80,2.50,1.92,0.85,0.20,0.00
        1.0,0.00,1.50,2.80,3.50,3.80,3.80,3.50,2.80,1.50,0.40,0.00

Format 2 — Long format:
    Header: "station_x,waterline_z,half_breadth_y"
    Satu titik per baris.

    Contoh:
        station_x,waterline_z,half_breadth_y
        0.0,0.0,0.0
        0.0,1.0,0.5
        10.0,0.0,0.0

Format dideteksi otomatis dari header.

Metadata opsional (diawali '#' sebagai komentar):
    # LPP=100.0
    # B=20.0
    # T=8.0
    # name=Kapal Kontainer ABC
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .hull import HullForm, ShipDimensions, Station


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_metadata(lines: List[str]) -> Dict[str, str]:
    """Ambil metadata dari baris komentar '#'."""
    meta: Dict[str, str] = {}
    pattern = re.compile(r"#\s*(\w+)\s*=\s*(.+)")
    for line in lines:
        m = pattern.match(line.strip())
        if m:
            meta[m.group(1).upper()] = m.group(2).strip()
    return meta


def _station_x_from_label(
    label: str, lpp: Optional[float], idx: int, total: int
) -> float:
    """Konversi label station (AP, FP, 1..20, 0.5, dll.) ke koordinat x [m].

    Jika LPP diketahui, konversi dari nomor station ke meter.
    Jika tidak, gunakan nomor station mentah sebagai x.
    """
    label = label.strip().upper()

    # AP = x=0, FP = x=LPP
    if label in ("AP", "0", "APP"):
        return 0.0
    if label in ("FP", "FPP"):
        return lpp if lpp is not None else float(total - 1)

    # Coba parse sebagai float (nomor station, mis. 1, 2, ..., 10 atau 0.5)
    try:
        n = float(label)
    except ValueError:
        # Label tidak dikenal — gunakan indeks
        return float(idx)

    if lpp is None:
        return n

    # Asumsi: station 0 = AP, station N = FP (N = nilai station maksimum)
    # Deteksi jumlah station berdasarkan nilai maksimum
    return (n / (total - 1)) * lpp


# ---------------------------------------------------------------------------
# Format 1 — Matrix
# ---------------------------------------------------------------------------

def _read_matrix_format(
    rows: List[List[str]],
    lpp: Optional[float],
) -> Tuple[List[float], List[float], List[List[float]]]:
    """Parse format matrix.

    Returns:
        (waterlines, x_stations, grid)
        grid[i][j] = half-breadth di waterline i, station j
    """
    header = rows[0]  # ["waterline", "AP", "1", ..., "FP"]
    station_labels = header[1:]
    n_stations = len(station_labels)

    waterlines: List[float] = []
    grid: List[List[float]] = []

    for row in rows[1:]:
        if not row or not row[0]:
            continue
        try:
            wl = float(row[0])
        except ValueError:
            continue  # Skip baris yang tidak valid

        y_values: List[float] = []
        for j in range(n_stations):
            try:
                y = float(row[j + 1]) if j + 1 < len(row) else 0.0
            except ValueError:
                y = 0.0
            y_values.append(y)

        waterlines.append(wl)
        grid.append(y_values)

    x_stations = [
        _station_x_from_label(label, lpp, idx, n_stations)
        for idx, label in enumerate(station_labels)
    ]
    return waterlines, x_stations, grid


# ---------------------------------------------------------------------------
# Format 2 — Long format
# ---------------------------------------------------------------------------

def _read_long_format(
    rows: List[List[str]],
) -> Tuple[List[float], Dict[float, List[Tuple[float, float]]]]:
    """Parse format long.

    Returns:
        (sorted_x_list, {x: [(z, y_half), ...]})
    """
    stations_dict: Dict[float, List[Tuple[float, float]]] = {}

    for row in rows[1:]:  # Skip header
        if len(row) < 3:
            continue
        try:
            x = float(row[0])
            z = float(row[1])
            y = float(row[2])
        except ValueError:
            continue

        if x not in stations_dict:
            stations_dict[x] = []
        stations_dict[x].append((z, y))

    sorted_xs = sorted(stations_dict.keys())
    return sorted_xs, stations_dict


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def read_offset_table(filepath: str | Path) -> HullForm:
    """Baca tabel offset dari file CSV dan kembalikan HullForm.

    Args:
        filepath: Path ke file CSV tabel offset.

    Returns:
        HullForm siap dipakai untuk perhitungan hidrostatik.

    Raises:
        FileNotFoundError: File tidak ditemukan.
        ValueError: Format file tidak dikenal atau data tidak valid.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {path}")

    raw_lines = path.read_text(encoding="utf-8-sig").splitlines()
    # Pisahkan komentar metadata dari data
    comment_lines = [l for l in raw_lines if l.strip().startswith("#")]
    data_lines = [l for l in raw_lines if not l.strip().startswith("#") and l.strip()]

    meta = _parse_metadata(comment_lines)

    # Ambil metadata ukuran utama
    lpp: Optional[float] = float(meta["LPP"]) if "LPP" in meta else None
    lwl: Optional[float] = float(meta["LWL"]) if "LWL" in meta else lpp
    b:   Optional[float] = float(meta["B"]) if "B" in meta else None
    t:   Optional[float] = float(meta["T"]) if "T" in meta else None
    name: str = meta.get("NAME", path.stem)

    # Parse CSV
    reader = csv.reader(data_lines)
    rows = list(reader)
    if not rows:
        raise ValueError("File CSV kosong atau tidak ada data setelah komentar.")

    # Deteksi format dari header
    header = [h.strip().upper() for h in rows[0]]
    is_long_format = (
        len(header) >= 3
        and header[0] in ("STATION_X", "STATION", "X")
        and header[1] in ("WATERLINE_Z", "WATERLINE", "Z", "WL")
    )

    hull = HullForm(name=name)

    if is_long_format:
        # Format 2 — Long
        sorted_xs, stations_dict = _read_long_format(rows)
        for x in sorted_xs:
            st = Station(x=x, offsets=stations_dict[x])
            hull.add_station(st)
    else:
        # Format 1 — Matrix
        waterlines, x_stations, grid = _read_matrix_format(rows, lpp)
        for j, x in enumerate(x_stations):
            offsets = [(waterlines[i], grid[i][j]) for i in range(len(waterlines))]
            st = Station(x=x, offsets=offsets)
            hull.add_station(st)

    # Set dimensi kalau metadata tersedia
    if lpp and b and t:
        hull.dimensions = ShipDimensions(
            LPP=lpp,
            LWL=lwl or lpp,
            B=b,
            T=t,
        )
    elif hull.stations:
        # Estimasi dari data jika metadata tidak ada
        xs = hull.x_stations
        est_lpp = xs[-1] - xs[0]
        wls = hull.all_waterlines
        est_t = max(wls) if wls else 1.0
        # Estimasi B dari setengah-lebar maksimum
        max_y = max(
            st.y_at(est_t) for st in hull.stations
        )
        est_b = max_y * 2
        if est_lpp > 0:
            hull.dimensions = ShipDimensions(
                LPP=est_lpp,
                LWL=est_lpp,
                B=est_b,
                T=est_t,
            )

    return hull


def write_offset_table_matrix(hull: HullForm, filepath: str | Path) -> None:
    """Tulis HullForm ke CSV format matrix.

    Berguna untuk ekspor / verifikasi data.
    """
    path = Path(filepath)
    wls = hull.all_waterlines
    if not wls or not hull.stations:
        raise ValueError("HullForm kosong, tidak ada data untuk ditulis.")

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Metadata
        if hull.dimensions:
            d = hull.dimensions
            f.write(f"# LPP={d.LPP}\n")
            f.write(f"# LWL={d.LWL}\n")
            f.write(f"# B={d.B}\n")
            f.write(f"# T={d.T}\n")
        f.write(f"# name={hull.name}\n")

        # Header: waterline, station_0, station_1, ...
        header = ["waterline"] + [f"{x:.4f}" for x in hull.x_stations]
        writer.writerow(header)

        for z in wls:
            row = [f"{z:.4f}"] + [
                f"{st.y_at(z):.4f}" for st in hull.stations
            ]
            writer.writerow(row)
