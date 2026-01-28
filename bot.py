"""
Bot Telegram - Sistem Pencatatan Pelanggaran Siswa
SMAN 1 Lamongan

File utama bot dengan semua fitur dan handler
"""

import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from config import TELEGRAM_BOT_TOKEN, DAFTAR_KELAS, PESAN_SELAMAT_DATANG, PESAN_TIDAK_ADA_AKSES
from database import DatabaseHandler
from pdf_generator import PDFGenerator
from utils import (
    format_card_siswa,
    format_riwayat_pelanggaran,
    format_pesan_duplikasi,
    format_pesan_sukses_catat,
    get_current_datetime
)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States untuk conversation handler
(
    PILIH_TINGKAT,
    PILIH_KELAS,
    PILIH_SISWA,
    PILIH_PELANGGARAN,
    UPLOAD_FOTO,
    KONFIRMASI_DUPLIKASI,
    INPUT_NIS_RIWAYAT,
    INPUT_NIS_EXPORT
) = range(8)

# Inisialisasi database handler
db = DatabaseHandler()


# ==========================================
# FUNGSI HELPER
# ==========================================

def is_admin(user_id):
    """Cek apakah user adalah admin"""
    is_adm, nama = db.is_admin(user_id)
    return is_adm, nama


def create_menu_utama(is_admin_user=False):
    """Membuat keyboard menu utama"""
    keyboard = []
    
    if is_admin_user:
        keyboard.append([InlineKeyboardButton("📝 Catat Pelanggaran", callback_data="catat")])
    
    keyboard.append([InlineKeyboardButton("🔍 Cari Riwayat Siswa", callback_data="cari")])
    keyboard.append([InlineKeyboardButton("📄 Export Laporan PDF", callback_data="export")])
    keyboard.append([InlineKeyboardButton("ℹ️ Bantuan", callback_data="help")])
    
    return InlineKeyboardMarkup(keyboard)


# ==========================================
# COMMAND HANDLERS
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /start"""
    user = update.effective_user
    user_id = user.id
    
    # Cek apakah admin
    is_adm, nama_admin = is_admin(user_id)
    
    if is_adm:
        welcome_msg = PESAN_SELAMAT_DATANG.format(nama=nama_admin)
        welcome_msg += "\n🔐 Status: Administrator"
    else:
        welcome_msg = PESAN_SELAMAT_DATANG.format(nama=user.first_name)
        welcome_msg += "\n👤 Status: User (Akses Terbatas)"
    
    await update.message.reply_text(
        welcome_msg,
        reply_markup=create_menu_utama(is_adm)
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /menu"""
    user_id = update.effective_user.id
    is_adm, _ = is_admin(user_id)
    
    await update.message.reply_text(
        "📋 MENU UTAMA\n\nSilakan pilih menu:",
        reply_markup=create_menu_utama(is_adm)
    )


# ==========================================
# CATAT PELANGGARAN (ADMIN ONLY)
# ==========================================

async def catat_pelanggaran_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mulai proses pencatatan pelanggaran - Pilih tingkat kelas"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    is_adm, nama_admin = is_admin(user_id)
    
    if not is_adm:
        await query.edit_message_text(PESAN_TIDAK_ADA_AKSES)
        return ConversationHandler.END
    
    # Simpan nama admin
    context.user_data['nama_admin'] = nama_admin
    
    # Keyboard pilihan tingkat
    keyboard = [
        [InlineKeyboardButton("🎓 Kelas X", callback_data="tingkat_X")],
        [InlineKeyboardButton("🎓 Kelas XI", callback_data="tingkat_XI")],
        [InlineKeyboardButton("🎓 Kelas XII", callback_data="tingkat_XII")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel")]
    ]
    
    await query.edit_message_text(
        "📚 PILIH TINGKAT KELAS\n\nSilakan pilih tingkat kelas:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return PILIH_TINGKAT


async def pilih_tingkat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk pilih tingkat kelas"""
    query = update.callback_query
    await query.answer()
    
    tingkat = query.data.replace("tingkat_", "")
    context.user_data['tingkat'] = tingkat
    
    # Buat keyboard pilihan kelas (3 kolom)
    kelas_list = DAFTAR_KELAS[tingkat]
    keyboard = []
    
    # Buat grid 3 kolom
    for i in range(0, len(kelas_list), 3):
        row = [
            InlineKeyboardButton(kelas, callback_data=f"kelas_{kelas}")
            for kelas in kelas_list[i:i+3]
        ]
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data="back_tingkat")])
    keyboard.append([InlineKeyboardButton("❌ Batal", callback_data="cancel")])
    
    await query.edit_message_text(
        f"📚 PILIH KELAS {tingkat}\n\n"
        f"Silakan pilih kelas:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return PILIH_KELAS


async def pilih_kelas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk pilih kelas - tampilkan daftar siswa"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "back_tingkat":
        return await catat_pelanggaran_start(update, context)
    
    kelas = query.data.replace("kelas_", "")
    context.user_data['kelas'] = kelas
    
    # Ambil daftar siswa di kelas tersebut
    siswa_list = db.get_siswa_by_kelas(kelas)
    
    if not siswa_list:
        await query.edit_message_text(
            f"❌ Tidak ada data siswa di kelas {kelas}\n\n"
            f"Pastikan data siswa sudah diinput di spreadsheet.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Kembali", callback_data=f"tingkat_{context.user_data['tingkat']}")
            ]])
        )
        return PILIH_TINGKAT
    
    # Buat keyboard daftar siswa
    keyboard = []
    for siswa in siswa_list:
        nis = siswa.get('NIS', '')
        nama = siswa.get('Nama', '')
        button_text = f"{nama} ({nis})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"siswa_{nis}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data=f"tingkat_{context.user_data['tingkat']}")])
    keyboard.append([InlineKeyboardButton("❌ Batal", callback_data="cancel")])
    
    await query.edit_message_text(
        f"👥 DAFTAR SISWA KELAS {kelas}\n\n"
        f"Total: {len(siswa_list)} siswa\n\n"
        f"Silakan pilih siswa:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return PILIH_SISWA


async def pilih_siswa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk pilih siswa - tampilkan jenis pelanggaran"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("tingkat_"):
        return await pilih_tingkat(update, context)
    
    nis = query.data.replace("siswa_", "")
    context.user_data['nis'] = nis
    
    # Ambil data siswa
    siswa = db.get_siswa_by_nis(nis)
    context.user_data['siswa'] = siswa
    
    # Ambil daftar jenis pelanggaran
    pelanggaran_list = db.get_all_pelanggaran()
    
    if not pelanggaran_list:
        await query.edit_message_text(
            "❌ Data jenis pelanggaran tidak ditemukan\n\n"
            "Pastikan data pelanggaran sudah diinput di spreadsheet.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Kembali", callback_data=f"kelas_{context.user_data['kelas']}")
            ]])
        )
        return PILIH_KELAS
    
    # Tampilkan info siswa
    total_poin = db.hitung_total_poin(nis)
    siswa_card = format_card_siswa(siswa, total_poin)
    
    # Buat keyboard jenis pelanggaran
    keyboard = []
    for p in pelanggaran_list:
        kode = p.get('Kode', '')
        jenis = p.get('Jenis Pelanggaran', '')
        poin = p.get('Poin', '')
        button_text = f"{jenis} ({poin} poin)"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"pelanggaran_{kode}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Kembali", callback_data=f"kelas_{context.user_data['kelas']}")])
    keyboard.append([InlineKeyboardButton("❌ Batal", callback_data="cancel")])
    
    await query.edit_message_text(
        f"{siswa_card}\n"
        f"⚠️ PILIH JENIS PELANGGARAN\n\n"
        f"Silakan pilih jenis pelanggaran:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return PILIH_PELANGGARAN


async def pilih_pelanggaran(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk pilih pelanggaran - minta upload foto"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("kelas_"):
        return await pilih_kelas(update, context)
    
    kode = query.data.replace("pelanggaran_", "")
    context.user_data['kode_pelanggaran'] = kode
    
    # Ambil data pelanggaran
    pelanggaran = db.get_pelanggaran_by_kode(kode)
    context.user_data['pelanggaran'] = pelanggaran
    
    # Cek duplikasi
    nis = context.user_data['nis']
    is_duplicate, waktu_sebelumnya = db.cek_duplikasi(nis, kode)
    
    if is_duplicate:
        # Ada duplikasi, minta konfirmasi
        siswa = context.user_data['siswa']
        pesan = format_pesan_duplikasi(
            siswa.get('Nama', ''),
            pelanggaran.get('Jenis Pelanggaran', ''),
            waktu_sebelumnya
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Ya, Tetap Catat", callback_data="confirm_yes")],
            [InlineKeyboardButton("❌ Tidak, Batal", callback_data="confirm_no")]
        ]
        
        await query.edit_message_text(
            pesan,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return KONFIRMASI_DUPLIKASI
    else:
        # Tidak ada duplikasi, langsung minta foto
        await query.edit_message_text(
            "📸 UPLOAD FOTO BUKTI\n\n"
            f"Siswa: {context.user_data['siswa'].get('Nama', '')}\n"
            f"Pelanggaran: {pelanggaran.get('Jenis Pelanggaran', '')}\n\n"
            "Silakan kirim foto bukti pelanggaran.\n\n"
            "💡 Tips: Pastikan foto jelas dan terlihat dengan baik.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Batal", callback_data="cancel")
            ]])
        )
        
        return UPLOAD_FOTO


async def konfirmasi_duplikasi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk konfirmasi duplikasi"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_no":
        # Batal, kembali ke menu
        await query.edit_message_text(
            "❌ Pencatatan dibatalkan.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")
            ]])
        )
        return ConversationHandler.END
    
    # Lanjut minta foto
    pelanggaran = context.user_data['pelanggaran']
    await query.edit_message_text(
        "📸 UPLOAD FOTO BUKTI\n\n"
        f"Siswa: {context.user_data['siswa'].get('Nama', '')}\n"
        f"Pelanggaran: {pelanggaran.get('Jenis Pelanggaran', '')}\n\n"
        "⚠️ Pelanggaran duplikat - tetap dicatat sesuai permintaan\n\n"
        "Silakan kirim foto bukti pelanggaran.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Batal", callback_data="cancel")
        ]])
    )
    
    return UPLOAD_FOTO


async def upload_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk upload foto bukti"""
    # Kirim status processing
    processing_msg = await update.message.reply_text(
        "🔄 Memproses...\n"
        "📤 Mengupload foto ke Google Drive\n"
        "💾 Menyimpan data ke spreadsheet\n\n"
        "Mohon tunggu sebentar..."
    )
    
    try:
        # Download foto
        photo = update.message.photo[-1]  # Ambil foto resolusi tertinggi
        file = await context.bot.get_file(photo.file_id)
        
        # Simpan sementara
        temp_photo_path = f"/tmp/temp_photo_{update.effective_user.id}.jpg"
        await file.download_to_drive(temp_photo_path)
        
        # Upload ke Google Drive
        siswa = context.user_data['siswa']
        kelas = siswa.get('Kelas', '')
        nis = siswa.get('NIS', '')
        
        link_foto = db.upload_foto_bukti(temp_photo_path, kelas, nis)
        
        if not link_foto:
            await processing_msg.edit_text(
                "❌ Gagal mengupload foto ke Google Drive\n\n"
                "Silakan coba lagi atau hubungi administrator.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")
                ]])
            )
            return ConversationHandler.END
        
        # Simpan riwayat pelanggaran
        pelanggaran = context.user_data['pelanggaran']
        success = db.tambah_riwayat_pelanggaran(
            nis=nis,
            nama=siswa.get('Nama', ''),
            kelas=kelas,
            kode_pelanggaran=pelanggaran.get('Kode', ''),
            jenis_pelanggaran=pelanggaran.get('Jenis Pelanggaran', ''),
            poin=pelanggaran.get('Poin', 0),
            link_foto=link_foto,
            petugas=context.user_data['nama_admin']
        )
        
        # Hapus file temp
        if os.path.exists(temp_photo_path):
            os.remove(temp_photo_path)
        
        if success:
            pesan_sukses = format_pesan_sukses_catat(
                siswa.get('Nama', ''),
                pelanggaran.get('Jenis Pelanggaran', ''),
                pelanggaran.get('Poin', 0)
            )
            pesan_sukses += f"\n📸 [Lihat Foto Bukti]({link_foto})"
            
            await processing_msg.edit_text(
                pesan_sukses,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📝 Catat Lagi", callback_data="catat"),
                    InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")
                ]])
            )
        else:
            await processing_msg.edit_text(
                "❌ Gagal menyimpan data ke spreadsheet\n\n"
                "Silakan coba lagi atau hubungi administrator.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")
                ]])
            )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error upload foto: {e}")
        await processing_msg.edit_text(
            f"❌ Terjadi kesalahan: {str(e)}\n\n"
            "Silakan coba lagi atau hubungi administrator.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")
            ]])
        )
        return ConversationHandler.END


# ==========================================
# CARI RIWAYAT (SEMUA USER)
# ==========================================

async def cari_riwayat_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mulai proses cari riwayat - minta input NIS"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🔍 CARI RIWAYAT SISWA\n\n"
        "Silakan ketik NIS siswa yang ingin dicari.\n\n"
        "Contoh: 2024001\n\n"
        "Ketik /cancel untuk membatalkan.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Batal", callback_data="cancel")
        ]])
    )
    
    return INPUT_NIS_RIWAYAT


async def input_nis_riwayat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk input NIS - tampilkan riwayat"""
    nis = update.message.text.strip()
    
    # Cek data siswa
    siswa = db.get_siswa_by_nis(nis)
    
    if not siswa:
        await update.message.reply_text(
            f"❌ Data siswa dengan NIS {nis} tidak ditemukan.\n\n"
            "Pastikan NIS yang diinput benar.\n\n"
            "Silakan coba lagi atau ketik /cancel untuk membatalkan."
        )
        return INPUT_NIS_RIWAYAT
    
    # Ambil riwayat
    riwayat = db.get_riwayat_by_nis(nis)
    total_poin = db.hitung_total_poin(nis)
    
    # Format tampilan
    siswa_card = format_card_siswa(siswa, total_poin)
    riwayat_text = format_riwayat_pelanggaran(riwayat)
    
    pesan = f"{siswa_card}\n\n{riwayat_text}"
    
    await update.message.reply_text(
        pesan,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 Export PDF", callback_data=f"export_nis_{nis}")],
            [InlineKeyboardButton("🔍 Cari Lagi", callback_data="cari")],
            [InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")]
        ])
    )
    
    return ConversationHandler.END


# ==========================================
# EXPORT PDF (SEMUA USER)
# ==========================================

async def export_pdf_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mulai proses export PDF - minta input NIS"""
    query = update.callback_query
    await query.answer()
    
    # Cek apakah dari callback dengan NIS
    if query.data.startswith("export_nis_"):
        nis = query.data.replace("export_nis_", "")
        context.user_data['export_nis'] = nis
        return await proses_export_pdf(update, context)
    
    await query.edit_message_text(
        "📄 EXPORT LAPORAN PDF\n\n"
        "Silakan ketik NIS siswa yang ingin diexport.\n\n"
        "Contoh: 2024001\n\n"
        "Ketik /cancel untuk membatalkan.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Batal", callback_data="cancel")
        ]])
    )
    
    return INPUT_NIS_EXPORT


async def input_nis_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk input NIS export"""
    nis = update.message.text.strip()
    context.user_data['export_nis'] = nis
    
    # Buat Update object dummy untuk proses export
    return await proses_export_pdf(update, context)


async def proses_export_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Proses generate dan kirim PDF"""
    nis = context.user_data.get('export_nis')
    
    # Kirim status processing
    if update.callback_query:
        processing_msg = await update.callback_query.message.reply_text(
            "🔄 Membuat laporan PDF...\n"
            "Mohon tunggu sebentar..."
        )
    else:
        processing_msg = await update.message.reply_text(
            "🔄 Membuat laporan PDF...\n"
            "Mohon tunggu sebentar..."
        )
    
    try:
        # Cek data siswa
        siswa = db.get_siswa_by_nis(nis)
        
        if not siswa:
            await processing_msg.edit_text(
                f"❌ Data siswa dengan NIS {nis} tidak ditemukan.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")
                ]])
            )
            return ConversationHandler.END
        
        # Ambil riwayat
        riwayat = db.get_riwayat_by_nis(nis)
        total_poin = db.hitung_total_poin(nis)
        
        # Generate PDF
        pdf_path = f"/tmp/laporan_{nis}_{get_current_datetime().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_gen = PDFGenerator(pdf_path)
        pdf_gen.generate_laporan_siswa(siswa, riwayat, total_poin)
        
        # Kirim PDF
        with open(pdf_path, 'rb') as pdf_file:
            caption = (
                f"📄 Laporan Pelanggaran Siswa\n\n"
                f"NIS: {siswa.get('NIS', '')}\n"
                f"Nama: {siswa.get('Nama', '')}\n"
                f"Kelas: {siswa.get('Kelas', '')}\n"
                f"Total Poin: {total_poin}"
            )
            
            if update.callback_query:
                await update.callback_query.message.reply_document(
                    document=pdf_file,
                    filename=f"Laporan_{siswa.get('Nama', 'Siswa')}_{nis}.pdf",
                    caption=caption
                )
            else:
                await update.message.reply_document(
                    document=pdf_file,
                    filename=f"Laporan_{siswa.get('Nama', 'Siswa')}_{nis}.pdf",
                    caption=caption
                )
        
        # Hapus file temp
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        
        await processing_msg.delete()
        
        # Kirim menu
        if update.callback_query:
            await update.callback_query.message.reply_text(
                "✅ PDF berhasil dibuat!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")
                ]])
            )
        else:
            await update.message.reply_text(
                "✅ PDF berhasil dibuat!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")
                ]])
            )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error export PDF: {e}")
        await processing_msg.edit_text(
            f"❌ Gagal membuat PDF: {str(e)}\n\n"
            "Silakan coba lagi atau hubungi administrator.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")
            ]])
        )
        return ConversationHandler.END


# ==========================================
# HANDLER LAINNYA
# ==========================================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk bantuan"""
    query = update.callback_query
    
    help_text = """
ℹ️ BANTUAN - Sistem Pencatatan Pelanggaran

📝 FITUR ADMIN:
• Catat Pelanggaran - Mencatat pelanggaran siswa dengan foto bukti

🔍 FITUR SEMUA USER:
• Cari Riwayat - Melihat riwayat pelanggaran siswa berdasarkan NIS
• Export PDF - Membuat laporan PDF riwayat pelanggaran

💡 CARA PENGGUNAAN:
1. Pilih menu yang diinginkan
2. Ikuti instruksi yang diberikan
3. Input data sesuai permintaan

📞 BANTUAN TEKNIS:
Jika mengalami kendala, hubungi administrator sekolah.

🏫 SMAN 1 Lamongan
"""
    
    if query:
        await query.answer()
        await query.edit_message_text(
            help_text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")
            ]])
        )
    else:
        await update.message.reply_text(
            help_text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")
            ]])
        )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk callback menu"""
    query = update.callback_query
    user_id = update.effective_user.id
    is_adm, _ = is_admin(user_id)
    
    await query.answer()
    await query.edit_message_text(
        "📋 MENU UTAMA\n\nSilakan pilih menu:",
        reply_markup=create_menu_utama(is_adm)
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk cancel conversation"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "❌ Proses dibatalkan.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")
            ]])
        )
    else:
        await update.message.reply_text(
            "❌ Proses dibatalkan.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Menu Utama", callback_data="menu")
            ]])
        )
    
    return ConversationHandler.END


# ==========================================
# MAIN
# ==========================================

def main():
    """Fungsi utama untuk menjalankan bot"""
    # Buat application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Conversation handler untuk catat pelanggaran
    conv_catat = ConversationHandler(
        entry_points=[CallbackQueryHandler(catat_pelanggaran_start, pattern="^catat$")],
        states={
            PILIH_TINGKAT: [CallbackQueryHandler(pilih_tingkat, pattern="^tingkat_")],
            PILIH_KELAS: [CallbackQueryHandler(pilih_kelas)],
            PILIH_SISWA: [CallbackQueryHandler(pilih_siswa)],
            PILIH_PELANGGARAN: [CallbackQueryHandler(pilih_pelanggaran)],
            KONFIRMASI_DUPLIKASI: [CallbackQueryHandler(konfirmasi_duplikasi)],
            UPLOAD_FOTO: [MessageHandler(filters.PHOTO, upload_foto)],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern="^cancel$"),
            CommandHandler("cancel", cancel)
        ],
    )
    
    # Conversation handler untuk cari riwayat
    conv_cari = ConversationHandler(
        entry_points=[CallbackQueryHandler(cari_riwayat_start, pattern="^cari$")],
        states={
            INPUT_NIS_RIWAYAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_nis_riwayat)],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern="^cancel$"),
            CommandHandler("cancel", cancel)
        ],
    )
    
    # Conversation handler untuk export PDF
    conv_export = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(export_pdf_start, pattern="^export$"),
            CallbackQueryHandler(export_pdf_start, pattern="^export_nis_")
        ],
        states={
            INPUT_NIS_EXPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_nis_export)],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern="^cancel$"),
            CommandHandler("cancel", cancel)
        ],
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(conv_catat)
    application.add_handler(conv_cari)
    application.add_handler(conv_export)
    application.add_handler(CallbackQueryHandler(help_command, pattern="^help$"))
    application.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu$"))
    
    # Run bot
    logger.info("Bot started...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
