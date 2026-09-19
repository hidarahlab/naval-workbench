"""
navalcore.hydrostatics — Perhitungan sifat hidrostatik lambung kapal.

Semua integrasi numerik menggunakan Aturan Simpson 1/3 (Simpson's Rule),
metode yang sama yang diajarkan di mata kuliah Teori Bangunan Kapal (TBK).

Variabel yang dihitung untuk setiap sarat (draft T):
    V         : Volume displacement [m³]  (notasi: ∇)
    displ     : Displacement [tonnes]      (notasi: Δ)
    Awp       : Luas bidang garis air (Waterplane Area) [m²]
    WSA       : Luas permukaan basah (Wetted Surface Area) [m²]  *perkiraan*
    LCB       : Letak titik apung longitudinal dari AP [m]
    KB        : Tinggi titik apung dari lunas [m]
    LCF       : Letak pusat bidang garis air dari AP [m]
    BMt       : Jari-jari metasentrum melintang [m]
    BMl       : Jari-jari metasentrum memanjang [m]
    KMt       : Tinggi metasentrum melintang dari lunas [m]
    KMl       : Tinggi metasentrum memanjang dari lunas [m]
    TPC       : Tonnes Per Centimetre Immersion [t/cm]
    MCT       : Moment to Change Trim 1 cm [t·m/cm]
    Cb        : Koefisien blok (Block Coefficient)
    Cp        : Koefisien prismatik (Prismatic Coefficient)
    Cwp       : Koefisien bidang garis air (Waterplane Coefficient)
    Cm        : Koefisien midship (Midship Section Coefficient)
    Am        : Luas penampang midship [m²]

Referensi:
    Barras, C.B. (2004). Ship Stability for Masters and Mates, 6th Ed.
    Lewis, E.V. (1988). Principles of Naval Architecture, Vol. I.
    Fyson, J. (1985). Design of Small Fishing Vessels. FAO.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .hull import HullForm


# ---------------------------------------------------------------------------
# Konstanta
# ---------------------------------------------------------------------------

RHO_SW = 1.025   # Massa jenis air laut [t/m³]
RHO_FW = 1.000   # Massa jenis air tawar [t/m³]
G      = 9.807   # Percepatan gravitasi [m/s²]


# ---------------------------------------------------------------------------
# Integrasi numerik — Aturan Simpson
# ---------------------------------------------------------------------------

def _simpsons(ys: List[float], h: float) -> float:
    """Integrasi Aturan Simpson 1/3 dengan jarak titik seragam.

    ∫f(x)dx ≈ (h/3) × [f₀ + 4f₁ + 2f₂ + 4f₃ + ... + 4fₙ₋₁ + fₙ]
    n harus genap (jumlah titik ganjil).

    Args:
        ys : Nilai fungsi di titik-titik yang seragam
        h  : Jarak antar titik

    Returns:
        Perkiraan integral numerik.
    """
    n = len(ys) - 1  # jumlah interval
    if n < 1:
        return 0.0
    if n == 1:
        return h * (ys[0] + ys[1]) / 2.0  # Trapesium

    # Kalau interval ganjil: bagi menjadi Simpson + Trapesium untuk sisa
    if n % 2 == 1:
        # Simpson untuk n-1 interval pertama, trapesium untuk terakhir
        result  = _simpsons(ys[:-1], h)
        result += h * (ys[-2] + ys[-1]) / 2.0
        return result

    # n genap: Simpson 1/3 murni
    total = ys[0] + ys[-1]
    for i in range(1, n):
        total += (4.0 if i % 2 == 1 else 2.0) * ys[i]
    return (h / 3.0) * total


def _trapz(xs: List[float], ys: List[float]) -> float:
    """Integrasi trapesium untuk jarak tidak seragam."""
    result = 0.0
    for i in range(len(xs) - 1):
        dx = xs[i + 1] - xs[i]
        result += dx * (ys[i] + ys[i + 1]) / 2.0
    return result


def _is_uniform(xs: List[float], tol: float = 1e-6) -> Tuple[bool, float]:
    """Periksa apakah titik-titik berjarak seragam.

    Returns:
        (is_uniform, spacing)
    """
    if len(xs) < 2:
        return True, 0.0
    h = xs[1] - xs[0]
    for i in range(2, len(xs)):
        if abs((xs[i] - xs[i - 1]) - h) > tol:
            return False, h
    return True, h


def _integrate_stations(
    xs: List[float], ys: List[float]
) -> float:
    """Integrasikan ys terhadap xs, pilih Simpson jika seragam."""
    uniform, h = _is_uniform(xs)
    if uniform:
        return _simpsons(ys, h)
    return _trapz(xs, ys)


# ---------------------------------------------------------------------------
# Perhitungan per-station
# ---------------------------------------------------------------------------

def _section_area(station, draft: float) -> float:
    """Luas penampang basah di station pada sarat tertentu [m²].

    Mengintegrasikan 2×y(z) dari z=0 sampai z=draft.
    Faktor 2 untuk port + starboard.
    """
    zs = [o[0] for o in station.offsets if o[0] <= draft]
    if not zs:
        # Semua offset di atas draft: interpolasi satu titik
        y = station.y_at(draft)
        return 2.0 * draft * y / 2.0  # Segitiga kasar
    if zs[-1] < draft:
        zs.append(draft)

    y_vals = [station.y_at(z) for z in zs]
    uniform, h = _is_uniform(zs)
    if uniform and len(zs) >= 3:
        area_half = _simpsons(y_vals, h)
    else:
        area_half = _trapz(zs, y_vals)
    return 2.0 * area_half  # port + starboard


def _section_first_moment_z(station, draft: float) -> float:
    """Momen pertama luas penampang terhadap baseline [m³].

    ∫₀ᵀ 2y(z)·z dz  — digunakan untuk menghitung KB.
    """
    zs = [o[0] for o in station.offsets if o[0] <= draft]
    if not zs:
        y = station.y_at(draft)
        return 2.0 * draft * draft * y / 4.0  # Kasar
    if zs[-1] < draft:
        zs.append(draft)

    y_times_z = [station.y_at(z) * z for z in zs]
    uniform, h = _is_uniform(zs)
    if uniform and len(zs) >= 3:
        moment_half = _simpsons(y_times_z, h)
    else:
        moment_half = _trapz(zs, y_times_z)
    return 2.0 * moment_half


def _wetted_half_perimeter(station, draft: float) -> float:
    """Setengah keliling basah di station [m]."""
    return station.wetted_half_perimeter(draft)


# ---------------------------------------------------------------------------
# Dataclass hasil
# ---------------------------------------------------------------------------

@dataclass
class HydrostaticResult:
    """Sifat hidrostatik pada satu sarat.

    Semua satuan SI (meter, tonne, t·m/cm) kecuali disebutkan lain.
    """
    draft:  float   # Sarat T [m]

    # Displacement
    volume: float   # Volume displacement ∇ [m³]
    displ:  float   # Displacement Δ [tonnes]

    # Luas permukaan
    Awp:    float   # Luas bidang garis air [m²]
    WSA:    float   # Luas permukaan basah (approx) [m²]
    Am:     float   # Luas penampang midship [m²]

    # Titik-titik referensi
    LCB:    float   # Letak B dari AP [m]
    KB:     float   # Tinggi B dari baseline [m]
    LCF:    float   # Letak pusat garis air dari AP [m]

    # Jari-jari metasentrum
    BMt:    float   # Jari-jari metasentrum melintang [m]
    BMl:    float   # Jari-jari metasentrum memanjang [m]

    # Tinggi metasentrum dari lunas
    KMt:    float   # KB + BMt [m]
    KMl:    float   # KB + BMl [m]

    # Derivative
    TPC:    float   # Tonnes Per Centimetre [t/cm]
    MCT:    float   # Moment to Change Trim 1 cm [t·m/cm]

    # Koefisien bentuk
    Cb:     float   # Koefisien blok
    Cp:     float   # Koefisien prismatik
    Cwp:    float   # Koefisien garis air
    Cm:     float   # Koefisien midship

    # Momen inersia bidang garis air
    IT:     float   # Momen inersia melintang terhadap CL [m⁴]
    IL:     float   # Momen inersia memanjang terhadap CF [m⁴]

    rho:    float   # Massa jenis air yang digunakan [t/m³]

    def to_dict(self) -> Dict[str, float]:
        """Konversi ke dict untuk ekspor."""
        return {
            "Draft [m]":       self.draft,
            "Vol [m³]":        round(self.volume, 3),
            "Displ [t]":       round(self.displ,  2),
            "Awp [m²]":        round(self.Awp,    2),
            "WSA [m²]":        round(self.WSA,    2),
            "Am [m²]":         round(self.Am,     3),
            "LCB [m]":         round(self.LCB,    3),
            "KB [m]":          round(self.KB,     3),
            "LCF [m]":         round(self.LCF,    3),
            "BMt [m]":         round(self.BMt,    3),
            "BMl [m]":         round(self.BMl,    3),
            "KMt [m]":         round(self.KMt,    3),
            "KMl [m]":         round(self.KMl,    3),
            "TPC [t/cm]":      round(self.TPC,    3),
            "MCT [t·m/cm]":    round(self.MCT,    4),
            "Cb":              round(self.Cb,     4),
            "Cp":              round(self.Cp,     4),
            "Cwp":             round(self.Cwp,    4),
            "Cm":              round(self.Cm,     4),
            "IT [m⁴]":         round(self.IT,     3),
            "IL [m⁴]":         round(self.IL,     3),
        }

    def summary(self) -> str:
        """Ringkasan teks untuk Report View FreeCAD."""
        return (
            f"\n{'='*56}\n"
            f"  HIDROSTATIK  T = {self.draft:.3f} m  "
            f"(ρ = {self.rho:.3f} t/m³)\n"
            f"{'='*56}\n"
            f"  Volume ∇      : {self.volume:>10.3f}  m³\n"
            f"  Displacement Δ: {self.displ:>10.2f}  t\n"
            f"  Awp           : {self.Awp:>10.2f}  m²\n"
            f"  WSA (approx)  : {self.WSA:>10.2f}  m²\n"
            f"  Am (midship)  : {self.Am:>10.3f}  m²\n"
            f"{'─'*56}\n"
            f"  LCB dari AP   : {self.LCB:>10.3f}  m\n"
            f"  KB            : {self.KB:>10.3f}  m\n"
            f"  LCF dari AP   : {self.LCF:>10.3f}  m\n"
            f"{'─'*56}\n"
            f"  BMt           : {self.BMt:>10.3f}  m\n"
            f"  BMl           : {self.BMl:>10.3f}  m\n"
            f"  KMt           : {self.KMt:>10.3f}  m\n"
            f"  KMl           : {self.KMl:>10.3f}  m\n"
            f"{'─'*56}\n"
            f"  TPC           : {self.TPC:>10.3f}  t/cm\n"
            f"  MCT           : {self.MCT:>10.4f}  t·m/cm\n"
            f"{'─'*56}\n"
            f"  Cb            : {self.Cb:>10.4f}\n"
            f"  Cp            : {self.Cp:>10.4f}\n"
            f"  Cwp           : {self.Cwp:>10.4f}\n"
            f"  Cm            : {self.Cm:>10.4f}\n"
            f"{'='*56}\n"
        )


# ---------------------------------------------------------------------------
# Fungsi utama
# ---------------------------------------------------------------------------

def compute(
    hull: HullForm,
    draft: float,
    rho: float = RHO_SW,
    midship_x: Optional[float] = None,
) -> HydrostaticResult:
    """Hitung sifat hidrostatik pada satu sarat.

    Args:
        hull      : HullForm hasil baca tabel offset
        draft     : Sarat yang dihitung [m]
        rho       : Massa jenis air [t/m³], default air laut 1.025
        midship_x : Posisi midship dari AP [m]. Default = LPP/2.

    Returns:
        HydrostaticResult berisi semua sifat hidrostatik.

    Raises:
        ValueError: Jika hull kosong atau draft ≤ 0.
    """
    if not hull.stations:
        raise ValueError("HullForm kosong — tidak ada stations.")
    if draft <= 0.0:
        raise ValueError(f"Draft harus positif, diterima: {draft}")

    xs = hull.x_stations
    lpp = xs[-1] - xs[0] if len(xs) > 1 else xs[0]
    if lpp <= 0:
        raise ValueError("LPP tidak valid — periksa koordinat x stations.")

    if midship_x is None:
        midship_x = xs[0] + lpp / 2.0

    # -----------------------------------------------------------------------
    # 1. Luas penampang dan momen di setiap station
    # -----------------------------------------------------------------------
    areas: List[float]        = []  # A(x) — luas penampang
    moments_z: List[float]    = []  # A(x)·z_bar — momen terhadap keel
    half_perims: List[float]  = []  # Setengah keliling basah

    for st in hull.stations:
        a  = _section_area(st, draft)
        mz = _section_first_moment_z(st, draft)
        hp = _wetted_half_perimeter(st, draft)
        areas.append(a)
        moments_z.append(mz)
        half_perims.append(hp)

    # -----------------------------------------------------------------------
    # 2. Volume dan momen volume terhadap baseline dan AP
    # -----------------------------------------------------------------------
    # Volume: ∇ = ∫ A(x) dx
    volume = _integrate_stations(xs, areas)
    if volume <= 0.0:
        volume = 1e-9  # Hindari division-by-zero

    # Momen volume terhadap keel: ∫ ∫₀ᵀ 2y·z dz dx = ∫ Mz(x) dx
    vol_moment_z = _integrate_stations(xs, moments_z)

    # Momen volume terhadap AP: ∫ A(x)·x dx
    areas_times_x = [a * x for a, x in zip(areas, xs)]
    vol_moment_x = _integrate_stations(xs, areas_times_x)

    # -----------------------------------------------------------------------
    # 3. Titik apung B
    # -----------------------------------------------------------------------
    KB  = vol_moment_z / volume
    LCB = vol_moment_x / volume

    # -----------------------------------------------------------------------
    # 4. Bidang garis air (waterplane)
    # -----------------------------------------------------------------------
    y_wl = [st.y_at(draft) for st in hull.stations]  # setengah-lebar di WL

    # Awp: 2 × ∫ y(x, T) dx
    Awp = 2.0 * _integrate_stations(xs, y_wl)

    # LCF: ∫ y·x dx / ∫ y dx
    y_times_x = [y * x for y, x in zip(y_wl, xs)]
    Awp_half = Awp / 2.0  # = ∫ y dx
    if Awp_half > 0.0:
        LCF = _integrate_stations(xs, y_times_x) / Awp_half
    else:
        LCF = midship_x

    # Momen inersia melintang bidang garis air (terhadap centerline)
    # IT = (2/3) ∫ y³ dx
    y_cubed = [y ** 3 for y in y_wl]
    IT = (2.0 / 3.0) * _integrate_stations(xs, y_cubed)

    # Momen inersia memanjang bidang garis air (terhadap CF)
    # IL_CF = 2 ∫ y·(x - LCF)² dx
    y_times_dx2 = [y * (x - LCF) ** 2 for y, x in zip(y_wl, xs)]
    IL = 2.0 * _integrate_stations(xs, y_times_dx2)

    # -----------------------------------------------------------------------
    # 5. Jari-jari metasentrum
    # -----------------------------------------------------------------------
    BMt = IT / volume
    BMl = IL / volume
    KMt = KB + BMt
    KMl = KB + BMl

    # -----------------------------------------------------------------------
    # 6. Luas midship
    # -----------------------------------------------------------------------
    # Cari station terdekat dengan midship_x
    mid_st = min(hull.stations, key=lambda s: abs(s.x - midship_x))
    Am = _section_area(mid_st, draft)

    # -----------------------------------------------------------------------
    # 7. WSA — luas permukaan basah (perkiraan via keliling basah)
    # -----------------------------------------------------------------------
    # WSA ≈ 2 × ∫ half_perimeter(x) dx + Awp_if_enclosed
    # Ini perkiraan; untuk akurasi lebih baik dibutuhkan mesh 3D.
    WSA = 2.0 * _integrate_stations(xs, half_perims)

    # -----------------------------------------------------------------------
    # 8. Displacement
    # -----------------------------------------------------------------------
    displ = rho * volume  # [tonnes]

    # -----------------------------------------------------------------------
    # 9. TPC dan MCT
    # -----------------------------------------------------------------------
    TPC = (rho * Awp) / 100.0          # [t/cm]
    MCT = (rho * IL) / (100.0 * lpp)  # [t·m/cm]  = BML×Δ/(100×L)

    # -----------------------------------------------------------------------
    # 10. Koefisien bentuk
    # -----------------------------------------------------------------------
    dim = hull.dimensions
    b_ref = dim.B if dim else (2.0 * max(y_wl) if y_wl else 1.0)
    t_ref = draft

    Cb  = volume / (lpp * b_ref * t_ref) if (lpp * b_ref * t_ref) > 0 else 0.0
    Cwp = Awp / (lpp * b_ref) if (lpp * b_ref) > 0 else 0.0
    Cm  = Am / (b_ref * t_ref) if (b_ref * t_ref) > 0 else 0.0
    Cp  = volume / (Am * lpp) if (Am * lpp) > 0 else 0.0

    return HydrostaticResult(
        draft=draft, volume=volume, displ=displ,
        Awp=Awp, WSA=WSA, Am=Am,
        LCB=LCB, KB=KB, LCF=LCF,
        BMt=BMt, BMl=BMl, KMt=KMt, KMl=KMl,
        TPC=TPC, MCT=MCT,
        Cb=Cb, Cp=Cp, Cwp=Cwp, Cm=Cm,
        IT=IT, IL=IL,
        rho=rho,
    )


def table(
    hull: HullForm,
    drafts: Optional[List[float]] = None,
    n_steps: int = 10,
    rho: float = RHO_SW,
) -> List[HydrostaticResult]:
    """Hitung tabel hidrostatik untuk rentang sarat.

    Args:
        hull    : HullForm
        drafts  : Daftar sarat yang ingin dihitung. Jika None, dibuat
                  otomatis dari 10% sampai 100% sarat maksimum.
        n_steps : Jumlah langkah (digunakan jika drafts=None)
        rho     : Massa jenis air [t/m³]

    Returns:
        Daftar HydrostaticResult, terurut dari sarat terkecil.
    """
    if drafts is None:
        t_max = hull.max_draft_defined
        if t_max <= 0:
            raise ValueError(
                "Tidak dapat menentukan sarat maksimum dari tabel offset. "
                "Berikan parameter 'drafts' secara eksplisit."
            )
        step = t_max / n_steps
        drafts = [step * i for i in range(1, n_steps + 1)]

    results = []
    for t in sorted(drafts):
        try:
            r = compute(hull, t, rho=rho)
            results.append(r)
        except Exception as e:
            # Log tapi jangan hentikan tabel
            print(f"[NavalCore] Peringatan: gagal menghitung T={t:.3f}m — {e}")
    return results
