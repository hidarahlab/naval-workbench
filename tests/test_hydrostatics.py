"""
Uji validasi modul navalcore.hydrostatics.

Semua nilai yang dicek memiliki jawaban ANALITIK EKSAK sehingga
toleransi sangat ketat (< 0.5%). Ini membuktikan mesin perhitungan
bebas bug satuan dan error integrasi yang signifikan.

Benchmark yang digunakan:
    1. Box Barge — semua permukaan datar, semua Cb=Cp=Cwp=Cm=1.0
    2. Triangular Wedge — penampang segitiga, nilai analitik diketahui
    3. Pembacaan CSV — pastikan offset_reader menghasilkan HullForm
       yang benar sebelum dihitung
"""

import math
import sys
from pathlib import Path

import pytest

# Tambahkan root proyek ke path agar import navalcore berjalan
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from navalcore.hull import HullForm, ShipDimensions, Station
from navalcore.hydrostatics import compute, table, RHO_SW
from navalcore.offset_reader import read_offset_table


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def box_barge(L: float, B: float, T_max: float, n_stations: int = 11) -> HullForm:
    """Buat HullForm kotak (box barge) secara programatik.

    Seluruh sisi vertikal dan alas datar: y_half = B/2 di semua z ≥ 0.
    """
    hull = HullForm(name=f"Box {L}×{B}")
    dx = L / (n_stations - 1)
    for i in range(n_stations):
        x = i * dx
        # Offset: y = B/2 di semua waterline
        offsets = [(0.0, B / 2.0), (T_max, B / 2.0)]
        hull.add_station(Station(x=x, offsets=offsets))
    hull.dimensions = ShipDimensions(LPP=L, LWL=L, B=B, T=T_max)
    return hull


# ---------------------------------------------------------------------------
# 1. Box Barge — jawaban analitik
# ---------------------------------------------------------------------------

class TestBoxBarge:
    """Validasi terhadap box barge (nilai semua bisa dihitung tangan)."""

    L   = 10.0   # Panjang [m]
    B   = 5.0    # Lebar [m]
    T   = 2.0    # Sarat [m]
    rho = RHO_SW # 1.025 t/m³

    @pytest.fixture
    def result(self):
        hull = box_barge(self.L, self.B, self.T + 1.0)  # T_max sedikit lebih besar
        return compute(hull, draft=self.T, rho=self.rho)

    def test_volume(self, result):
        """∇ = L × B × T"""
        expected = self.L * self.B * self.T
        assert abs(result.volume - expected) / expected < 0.005, (
            f"Volume {result.volume:.4f} vs analitik {expected:.4f}"
        )

    def test_displacement(self, result):
        """Δ = ρ × ∇"""
        expected = self.rho * self.L * self.B * self.T
        assert abs(result.displ - expected) / expected < 0.005, (
            f"Displ {result.displ:.4f} vs analitik {expected:.4f}"
        )

    def test_Awp(self, result):
        """Awp = L × B"""
        expected = self.L * self.B
        assert abs(result.Awp - expected) / expected < 0.005, (
            f"Awp {result.Awp:.4f} vs analitik {expected:.4f}"
        )

    def test_KB(self, result):
        """KB = T/2 (titik apung di tengah sarat)"""
        expected = self.T / 2.0
        assert abs(result.KB - expected) / expected < 0.01, (
            f"KB {result.KB:.4f} vs analitik {expected:.4f}"
        )

    def test_LCB(self, result):
        """LCB = L/2 (simetri memanjang)"""
        expected = self.L / 2.0
        assert abs(result.LCB - expected) / expected < 0.005, (
            f"LCB {result.LCB:.4f} vs analitik {expected:.4f}"
        )

    def test_LCF(self, result):
        """LCF = L/2 (simetri memanjang)"""
        expected = self.L / 2.0
        assert abs(result.LCF - expected) / expected < 0.005, (
            f"LCF {result.LCF:.4f} vs analitik {expected:.4f}"
        )

    def test_IT(self, result):
        """IT = L × B³ / 12 (persegi panjang)"""
        expected = self.L * self.B ** 3 / 12.0
        assert abs(result.IT - expected) / expected < 0.005, (
            f"IT {result.IT:.4f} vs analitik {expected:.4f}"
        )

    def test_IL(self, result):
        """IL = B × L³ / 12 (tentang CF = midship untuk kotak)"""
        expected = self.B * self.L ** 3 / 12.0
        assert abs(result.IL - expected) / expected < 0.005, (
            f"IL {result.IL:.4f} vs analitik {expected:.4f}"
        )

    def test_BMt(self, result):
        """BMt = IT / ∇"""
        volume   = self.L * self.B * self.T
        IT       = self.L * self.B ** 3 / 12.0
        expected = IT / volume
        assert abs(result.BMt - expected) / expected < 0.005, (
            f"BMt {result.BMt:.4f} vs analitik {expected:.4f}"
        )

    def test_BMl(self, result):
        """BMl = IL / ∇"""
        volume   = self.L * self.B * self.T
        IL       = self.B * self.L ** 3 / 12.0
        expected = IL / volume
        assert abs(result.BMl - expected) / expected < 0.005, (
            f"BMl {result.BMl:.4f} vs analitik {expected:.4f}"
        )

    def test_TPC(self, result):
        """TPC = ρ × Awp / 100"""
        expected = self.rho * self.L * self.B / 100.0
        assert abs(result.TPC - expected) / expected < 0.005, (
            f"TPC {result.TPC:.4f} vs analitik {expected:.4f}"
        )

    def test_MCT(self, result):
        """MCT = ρ × IL / (100 × L)"""
        IL = self.B * self.L ** 3 / 12.0
        expected = self.rho * IL / (100.0 * self.L)
        assert abs(result.MCT - expected) / expected < 0.005, (
            f"MCT {result.MCT:.5f} vs analitik {expected:.5f}"
        )

    def test_coefficients_unity(self, result):
        """Semua koefisien = 1.0 untuk kotak sempurna."""
        tol = 0.01
        assert abs(result.Cb  - 1.0) < tol, f"Cb = {result.Cb:.4f}"
        assert abs(result.Cwp - 1.0) < tol, f"Cwp = {result.Cwp:.4f}"
        assert abs(result.Cm  - 1.0) < tol, f"Cm = {result.Cm:.4f}"
        # Cp = Cb/Cm, untuk kotak = 1/1 = 1
        assert abs(result.Cp  - 1.0) < tol, f"Cp = {result.Cp:.4f}"


# ---------------------------------------------------------------------------
# 2. Wedge Hull — penampang segitiga
# ---------------------------------------------------------------------------

class TestWedgeHull:
    """Lambung dengan penampang segitiga (V-shape sempurna).

    Half-breadth: y(z) = (B/2) × (z/T)  linear dari keel.
    Nilai analitik:
        A(x) = B × T / 2              (luas segitiga)
        Cb   = Cwp = Cm = 0.5
        KB   = T/3 × (2/3)... hmm

    Untuk penampang segitiga dengan y = (B/2)×(z/T):
        A = ∫₀ᵀ 2y dz = ∫₀ᵀ 2(B/2)(z/T) dz = B/T × T²/2 = B×T/2
        Momen terhadap keel: ∫₀ᵀ 2y·z dz = B/T × ∫₀ᵀ z² dz = B/T × T³/3 = B×T²/3
        KB = (B×T²/3) / (B×T/2) = 2T/3
    """

    L = 10.0
    B = 4.0
    T = 3.0

    @pytest.fixture
    def hull(self):
        h = HullForm(name="Wedge Hull")
        n = 11
        dx = self.L / (n - 1)
        for i in range(n):
            x = i * dx
            # Penampang segitiga: y = B/2 × z/T pada z=T, y=0 pada z=0
            offsets = [
                (0.0, 0.0),
                (self.T * 0.25, self.B / 2.0 * 0.25),
                (self.T * 0.5,  self.B / 2.0 * 0.5),
                (self.T * 0.75, self.B / 2.0 * 0.75),
                (self.T,        self.B / 2.0),
            ]
            h.add_station(Station(x=x, offsets=offsets))
        h.dimensions = ShipDimensions(LPP=self.L, LWL=self.L, B=self.B, T=self.T)
        return h

    def test_section_area(self, hull):
        """Am = B × T / 2 untuk penampang segitiga."""
        r = compute(hull, draft=self.T, rho=RHO_SW)
        expected = self.B * self.T / 2.0
        assert abs(r.Am - expected) / expected < 0.01, (
            f"Am {r.Am:.4f} vs analitik {expected:.4f}"
        )

    def test_volume(self, hull):
        """∇ = L × B × T / 2 (semua station segitiga)"""
        r = compute(hull, draft=self.T, rho=RHO_SW)
        expected = self.L * self.B * self.T / 2.0
        assert abs(r.volume - expected) / expected < 0.01, (
            f"Volume {r.volume:.4f} vs analitik {expected:.4f}"
        )

    def test_KB(self, hull):
        """KB = 2T/3 untuk penampang segitiga."""
        r = compute(hull, draft=self.T, rho=RHO_SW)
        expected = 2.0 * self.T / 3.0
        assert abs(r.KB - expected) / expected < 0.02, (
            f"KB {r.KB:.4f} vs analitik {expected:.4f}"
        )

    def test_Cb(self, hull):
        """Cb = 0.5 untuk wedge hull."""
        r = compute(hull, draft=self.T, rho=RHO_SW)
        assert abs(r.Cb - 0.5) < 0.01, f"Cb = {r.Cb:.4f}"

    def test_Cwp(self, hull):
        """Cwp = 1.0 — waterplane kotak (lebar penuh di draft T)."""
        r = compute(hull, draft=self.T, rho=RHO_SW)
        assert abs(r.Cwp - 1.0) < 0.01, f"Cwp = {r.Cwp:.4f}"


# ---------------------------------------------------------------------------
# 3. Baca CSV dan hitung
# ---------------------------------------------------------------------------

class TestOffsetReader:
    """Pastikan offset_reader menghasilkan HullForm yang benar."""

    FIXTURE = ROOT / "tests" / "fixtures" / "box_barge.csv"

    def test_file_loads(self):
        hull = read_offset_table(self.FIXTURE)
        assert hull.n_stations == 11, f"Harusnya 11 station, dapat {hull.n_stations}"

    def test_dimensions_loaded(self):
        hull = read_offset_table(self.FIXTURE)
        assert hull.dimensions is not None
        assert hull.dimensions.LPP == 10.0
        assert hull.dimensions.B   == 5.0
        assert hull.dimensions.T   == 3.0

    def test_hydrostatics_from_csv(self):
        """Hitung hidrostatik dari CSV dan bandingkan dengan nilai analitik."""
        hull = read_offset_table(self.FIXTURE)
        r = compute(hull, draft=2.0, rho=RHO_SW)

        # Box barge L=10, B=5, T=2
        expected_vol  = 10.0 * 5.0 * 2.0   # = 100 m³
        expected_displ = RHO_SW * expected_vol  # = 102.5 t

        assert abs(r.volume - expected_vol)  / expected_vol  < 0.005
        assert abs(r.displ  - expected_displ) / expected_displ < 0.005
        assert abs(r.Cb - 1.0) < 0.01
        assert abs(r.Cwp - 1.0) < 0.01


# ---------------------------------------------------------------------------
# 4. Tabel hidrostatik
# ---------------------------------------------------------------------------

class TestHydrostaticTable:
    def test_table_ascending(self):
        """Displacement harus naik monoton seiring sarat bertambah."""
        hull = box_barge(L=100.0, B=20.0, T_max=10.0)
        results = table(hull, n_steps=5)
        displmts = [r.displ for r in results]
        for i in range(1, len(displmts)):
            assert displmts[i] > displmts[i - 1], (
                f"Displacement tidak monoton: T={results[i].draft:.2f} "
                f"Δ={displmts[i]:.2f} < Δ_prev={displmts[i-1]:.2f}"
            )

    def test_table_n_steps(self):
        """Tabel harus menghasilkan tepat n_steps baris."""
        hull = box_barge(L=50.0, B=10.0, T_max=5.0)
        results = table(hull, n_steps=8)
        assert len(results) == 8
