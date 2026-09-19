# NavalWorkbench

**Workbench perancangan kapal untuk FreeCAD — gratis, terbuka, berbahasa Indonesia.**

Ditujukan untuk mahasiswa, profesional, dan peneliti perkapalan di Indonesia.

---

## Fitur (v0.1.0)

| Fitur | Status |
|---|---|
| Impor tabel offset dari CSV (format matrix & long) | ✅ |
| Hitung hidrostatik lengkap (∇, Δ, Awp, KB, KM, TPC, MCT, Cb, Cp, Cwp, Cm) | ✅ |
| Tabel hidrostatik untuk rentang sarat | ✅ |
| Ekspor ke FreeCAD Spreadsheet | ✅ |
| Air laut & air tawar | ✅ |
| Suite validasi benchmark (box barge, wedge hull) | ✅ |

---

## Instalasi

1. Buka FreeCAD → **Tools → Addon Manager**
2. Cari "NavalWorkbench" → Install
3. Restart FreeCAD
4. Pilih workbench **"Naval"** dari dropdown

**Atau manual:**

```bash
cd ~/.FreeCAD/Mod
git clone https://github.com/hidarahlab/naval-workbench NavalWorkbench
```

---

## Cara Pakai

### 1. Siapkan tabel offset (CSV)

Format matrix (paling umum di buku teks):

```csv
# LPP=100.0
# B=20.0
# T=8.0
# name=KM Nusantara
waterline,AP,1,2,3,4,5,6,7,8,9,FP
0.0,0.00,1.85,3.92,5.50,6.80,6.80,5.50,3.92,1.85,0.50,0.00
2.0,0.00,3.20,5.80,7.50,8.90,8.90,7.50,5.80,3.20,1.20,0.00
4.0,0.00,4.50,7.20,8.90,9.60,9.60,8.90,7.20,4.50,2.00,0.00
```

- `waterline` : tinggi garis air dari lunas (baseline) [m]
- Kolom berikutnya : setengah lebar (*half-breadth*) di setiap station [m]

### 2. Impor ke FreeCAD

**Naval → Impor Tabel Offset** → pilih file CSV.

Objek `HullForm` muncul di model tree dengan properti LPP, B, T.

### 3. Hitung hidrostatik

**Naval → Hitung Hidrostatik** → atur rentang sarat → OK.

Hasil muncul di:
- **Spreadsheet** `Hidro_<nama>` — tabel lengkap
- **Report View** — ringkasan sarat rencana

---

## Variabel yang Dihitung

| Simbol | Nama | Satuan |
|---|---|---|
| ∇ | Volume displacement | m³ |
| Δ | Displacement | t |
| Awp | Luas bidang garis air | m² |
| WSA | Luas permukaan basah (approx) | m² |
| LCB | Letak titik apung dari AP | m |
| KB | Tinggi titik apung dari lunas | m |
| LCF | Letak pusat garis air dari AP | m |
| BMt | Jari-jari metasentrum melintang | m |
| BMl | Jari-jari metasentrum memanjang | m |
| KMt | Tinggi metasentrum melintang | m |
| KMl | Tinggi metasentrum memanjang | m |
| TPC | Tonnes Per Centimetre | t/cm |
| MCT | Moment to Change Trim 1 cm | t·m/cm |
| Cb | Koefisien blok | — |
| Cp | Koefisien prismatik | — |
| Cwp | Koefisien garis air | — |
| Cm | Koefisien midship | — |

---

## Untuk Developer

```bash
git clone https://github.com/hidarahlab/naval-workbench
cd naval-workbench

# Jalankan suite validasi (tidak perlu FreeCAD)
python3 -m pytest tests/ -v
```

Mesin perhitungan (`navalcore/`) adalah Python murni — tidak ada
dependensi FreeCAD. Bisa dipakai langsung dari script atau Jupyter Notebook.

---

## Lisensi

LGPL-2.1 — sama dengan FreeCAD. Gratis untuk semua penggunaan.

## Kontribusi

Issue dan pull request sangat disambut di
[github.com/hidarahlab/naval-workbench](https://github.com/hidarahlab/naval-workbench).
