"""
Konfigurasi Bot Pencatatan Pelanggaran Siswa
File ini berisi semua pengaturan yang diperlukan
"""

# ============================================
# KONFIGURASI TELEGRAM BOT
# ============================================
# Token bot dari BotFather (akan diisi nanti di TAHAP 3)
TELEGRAM_BOT_TOKEN = "8402667316:AAFMWI5ZDCchqCsVaRB-tFvA32ZIWAV-CXA"

# ============================================
# KONFIGURASI GOOGLE SHEETS
# ============================================
# ID Spreadsheet (akan diisi nanti di TAHAP 4)
SPREADSHEET_ID = "1M0DT913dzlgY2VGdEx4gvNIL_8KO-1_7wJOR5Ow_w5I"

# Nama-nama sheet di spreadsheet
SHEET_SISWA = "DataSiswa"
SHEET_PELANGGARAN = "JenisPelanggaran"
SHEET_RIWAYAT = "RiwayatPelanggaran"
SHEET_ADMIN = "DataAdmin"

# ============================================
# KONFIGURASI GOOGLE DRIVE
# ============================================
# ID Folder Google Drive untuk menyimpan foto (akan diisi nanti di TAHAP 4)
GOOGLE_DRIVE_FOLDER_ID = "1GO9rckor4W4966MLYPyupakIE0UsX9fn"

# ============================================
# KONFIGURASI TIMEZONE
# ============================================
TIMEZONE = "Asia/Jakarta"

# ============================================
# KONFIGURASI VALIDASI PELANGGARAN
# ============================================
# Waktu untuk cek duplikasi pelanggaran (dalam format jam)
DUPLIKASI_JAM_MULAI = 5  # 05:00
DUPLIKASI_JAM_SELESAI = 18  # 18:00

# ============================================
# KONFIGURASI PDF
# ============================================
# Path ke logo sekolah (akan diisi nanti)
LOGO_SEKOLAH_PATH = "logo_sekolah.png"

# Nama sekolah untuk header PDF
NAMA_SEKOLAH = "SMAN 1 LAMONGAN"
ALAMAT_SEKOLAH = "Jl. Veteran No. 7, Lamongan, Jawa Timur"

# ============================================
# DAFTAR KELAS
# ============================================
DAFTAR_KELAS = {
    "X": [f"X-{i}" for i in range(1, 13)],      # X-1 sampai X-12
    "XI": [f"XI-{i}" for i in range(1, 13)],    # XI-1 sampai XI-12
    "XII": [f"XII-{i}" for i in range(1, 13)]   # XII-1 sampai XII-12
}

# ============================================
# KATEGORI POIN PELANGGARAN
# ============================================
KATEGORI_POIN = {
    "ringan": (0, 20),      # 0-20 poin
    "sedang": (21, 50),     # 21-50 poin
    "berat": (51, 100),     # 51-100 poin
    "sangat_berat": (101, float('inf'))  # > 100 poin
}

# ============================================
# PESAN TEMPLATE
# ============================================
PESAN_SELAMAT_DATANG = """
╔══════════════════════════════╗
║  🎓 SISTEM PENCATATAN        ║
║     PELANGGARAN SISWA        ║
╚══════════════════════════════╝

Selamat datang, {nama}!

Silakan pilih menu di bawah ini:
"""

PESAN_TIDAK_ADA_AKSES = """
⛔ Akses Ditolak

Maaf, Anda tidak memiliki akses ke sistem ini.
Hubungi administrator untuk informasi lebih lanjut.
"""
