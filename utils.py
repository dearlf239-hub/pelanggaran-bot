"""
Utility Functions
Berisi fungsi-fungsi helper untuk formatting dan validasi
"""

from datetime import datetime
import pytz
from config import TIMEZONE, KATEGORI_POIN

def get_current_datetime():
    """Mendapatkan waktu saat ini di timezone Indonesia"""
    tz = pytz.timezone(TIMEZONE)
    return datetime.now(tz)

def format_tanggal(dt):
    """Format tanggal: 28 Januari 2026"""
    bulan = [
        "Januari", "Februari", "Maret", "April", "Mai", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]
    return f"{dt.day} {bulan[dt.month-1]} {dt.year}"

def format_waktu(dt):
    """Format waktu: 08:30"""
    return dt.strftime("%H:%M")

def format_datetime_lengkap(dt):
    """Format datetime lengkap: 28 Januari 2026, 08:30"""
    return f"{format_tanggal(dt)}, {format_waktu(dt)}"

def format_card_siswa(siswa_data, total_poin=0):
    """
    Format card untuk menampilkan data siswa
    
    Args:
        siswa_data: dict dengan key 'nis', 'nama', 'kelas'
        total_poin: total poin pelanggaran siswa
    
    Returns:
        String formatted card
    """
    kategori, emoji = get_kategori_poin(total_poin)
    progress_bar = get_progress_bar(total_poin)
    
    card = f"""
╔══════════════════════════════╗
║      📋 DATA SISWA           ║
╠══════════════════════════════╣
║ 🆔 NIS   : {siswa_data['nis']:<15} ║
║ 👤 Nama  : {siswa_data['nama']:<15} ║
║ 🏫 Kelas : {siswa_data['kelas']:<15} ║
║ ⭐ Poin  : {total_poin:<15} ║
╚══════════════════════════════╝

{progress_bar}
{emoji} Kategori: {kategori}
"""
    return card

def get_kategori_poin(total_poin):
    """
    Mendapatkan kategori berdasarkan total poin
    
    Returns:
        tuple: (nama_kategori, emoji)
    """
    if total_poin >= KATEGORI_POIN['sangat_berat'][0]:
        return ("Sangat Berat", "🔴")
    elif total_poin >= KATEGORI_POIN['berat'][0]:
        return ("Berat", "🟠")
    elif total_poin >= KATEGORI_POIN['sedang'][0]:
        return ("Sedang", "🟡")
    else:
        return ("Ringan", "🟢")

def get_progress_bar(total_poin, max_poin=100):
    """
    Membuat progress bar visual
    
    Args:
        total_poin: poin saat ini
        max_poin: poin maksimal untuk full bar
    
    Returns:
        String progress bar
    """
    persen = min(int((total_poin / max_poin) * 100), 100)
    filled = int(persen / 20)  # 5 blok total
    empty = 5 - filled
    
    bar = "■" * filled + "□" * empty
    return f"[{bar}] {persen}%"

def format_riwayat_pelanggaran(riwayat_list):
    """
    Format list riwayat pelanggaran menjadi tabel rapi
    
    Args:
        riwayat_list: list of dict riwayat pelanggaran
    
    Returns:
        String formatted table
    """
    if not riwayat_list:
        return "📭 Tidak ada riwayat pelanggaran"
    
    hasil = "📜 RIWAYAT PELANGGARAN\n"
    hasil += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for idx, item in enumerate(riwayat_list, 1):
        hasil += f"#{idx}\n"
        hasil += f"📅 {item['tanggal']} | ⏰ {item['waktu']}\n"
        hasil += f"⚠️ {item['pelanggaran']}\n"
        hasil += f"📊 Poin: {item['poin']}\n"
        if item.get('link_foto'):
            hasil += f"📸 [Lihat Bukti]({item['link_foto']})\n"
        hasil += f"👮 Petugas: {item['petugas']}\n"
        hasil += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    return hasil

def format_pesan_duplikasi(siswa_nama, pelanggaran, waktu_sebelumnya):
    """
    Format pesan warning duplikasi pelanggaran
    
    Returns:
        String formatted warning message
    """
    pesan = f"""
⚠️ PELANGGARAN DUPLIKAT TERDETEKSI!

👤 Siswa: {siswa_nama}
⚠️ Pelanggaran: {pelanggaran}
⏰ Sudah tercatat pada: {waktu_sebelumnya}

Apakah Anda tetap ingin mencatat pelanggaran ini?
"""
    return pesan

def format_pesan_sukses_catat(siswa_nama, pelanggaran, poin):
    """Format pesan sukses mencatat pelanggaran"""
    return f"""
✅ PELANGGARAN BERHASIL DICATAT!

👤 Siswa: {siswa_nama}
⚠️ Pelanggaran: {pelanggaran}
📊 Poin: {poin}
⏰ Waktu: {format_datetime_lengkap(get_current_datetime())}

Data telah tersimpan di database.
"""

def format_list_pelanggaran(pelanggaran_list):
    """
    Format list jenis pelanggaran untuk ditampilkan
    
    Args:
        pelanggaran_list: list of dict jenis pelanggaran
    
    Returns:
        String formatted list
    """
    hasil = "⚠️ JENIS PELANGGARAN\n"
    hasil += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for item in pelanggaran_list:
        hasil += f"📌 {item['jenis']}\n"
        hasil += f"   Poin: {item['poin']}\n"
        hasil += f"   Kode: {item['kode']}\n\n"
    
    return hasil

def sanitize_filename(text):
    """
    Membersihkan string untuk dijadikan nama file
    Menghapus karakter yang tidak valid untuk nama file
    """
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        text = text.replace(char, '_')
    return text

def format_nama_file_foto(kelas, nis, timestamp):
    """
    Format nama file foto: Kelas_NIS_Timestamp.jpg
    
    Args:
        kelas: kelas siswa (contoh: X-1)
        nis: NIS siswa
        timestamp: datetime object
    
    Returns:
        String nama file
    """
    ts = timestamp.strftime("%Y%m%d_%H%M%S")
    kelas_clean = sanitize_filename(kelas)
    return f"{kelas_clean}_{nis}_{ts}.jpg"

def format_nama_folder_hari(tanggal):
    """
    Format nama folder berdasarkan tanggal: 2026-01-28
    
    Args:
        tanggal: datetime object
    
    Returns:
        String nama folder
    """
    return tanggal.strftime("%Y-%m-%d")

def validasi_jam_duplikasi(waktu):
    """
    Cek apakah waktu masih dalam range jam duplikasi (05:00-18:00)
    
    Args:
        waktu: datetime object
    
    Returns:
        bool: True jika masih dalam range
    """
    jam = waktu.hour
    return 5 <= jam <= 18
