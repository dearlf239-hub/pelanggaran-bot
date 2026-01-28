"""
Database Handler
Mengelola koneksi dan operasi ke Google Sheets dan Google Drive
"""

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from datetime import datetime, timedelta
import os
from config import (
    SPREADSHEET_ID, 
    SHEET_SISWA, 
    SHEET_PELANGGARAN, 
    SHEET_RIWAYAT,
    SHEET_ADMIN,
    GOOGLE_DRIVE_FOLDER_ID,
    DUPLIKASI_JAM_MULAI,
    DUPLIKASI_JAM_SELESAI
)
from utils import (
    get_current_datetime,
    format_tanggal,
    format_waktu,
    format_nama_file_foto,
    format_nama_folder_hari
)

class DatabaseHandler:
    """Handler untuk operasi database Google Sheets dan Google Drive"""
    
    def __init__(self, credentials_file='credentials.json'):
        """
        Inisialisasi koneksi ke Google Sheets dan Drive
        
        Args:
            credentials_file: path ke file JSON credentials
        """
        # Setup credentials dengan scope yang diperlukan
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file'
        ]
        
        self.creds = Credentials.from_service_account_file(
            credentials_file, 
            scopes=self.scopes
        )
        
        # Koneksi ke Google Sheets
        self.gc = gspread.authorize(self.creds)
        self.spreadsheet = self.gc.open_by_key(SPREADSHEET_ID)
        
        # Koneksi ke Google Drive
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        
        # Cache untuk sheets
        self._sheets = {}
        self._load_sheets()
    
    def _load_sheets(self):
        """Load semua sheets yang diperlukan"""
        try:
            self._sheets['siswa'] = self.spreadsheet.worksheet(SHEET_SISWA)
            self._sheets['pelanggaran'] = self.spreadsheet.worksheet(SHEET_PELANGGARAN)
            self._sheets['riwayat'] = self.spreadsheet.worksheet(SHEET_RIWAYAT)
            self._sheets['admin'] = self.spreadsheet.worksheet(SHEET_ADMIN)
        except Exception as e:
            print(f"Error loading sheets: {e}")
            raise
    
    # ==========================================
    # FUNGSI UNTUK ADMIN
    # ==========================================
    
    def is_admin(self, telegram_id):
        """
        Cek apakah user adalah admin
        
        Args:
            telegram_id: ID Telegram user
        
        Returns:
            tuple: (is_admin: bool, nama_admin: str)
        """
        try:
            admin_sheet = self._sheets['admin']
            all_admins = admin_sheet.get_all_records()
            
            for admin in all_admins:
                if str(admin.get('ID Telegram')) == str(telegram_id):
                    if admin.get('Status', '').lower() == 'aktif':
                        return True, admin.get('Nama Admin', 'Admin')
            
            return False, None
        except Exception as e:
            print(f"Error checking admin: {e}")
            return False, None
    
    # ==========================================
    # FUNGSI UNTUK DATA SISWA
    # ==========================================
    
    def get_siswa_by_kelas(self, kelas):
        """
        Mendapatkan daftar siswa berdasarkan kelas
        
        Args:
            kelas: nama kelas (contoh: "X-1")
        
        Returns:
            list: list of dict siswa
        """
        try:
            siswa_sheet = self._sheets['siswa']
            all_siswa = siswa_sheet.get_all_records()
            
            siswa_kelas = [
                s for s in all_siswa 
                if str(s.get('Kelas', '')).strip() == kelas.strip()
            ]
            
            return siswa_kelas
        except Exception as e:
            print(f"Error getting siswa by kelas: {e}")
            return []
    
    def get_siswa_by_nis(self, nis):
        """
        Mendapatkan data siswa berdasarkan NIS
        
        Args:
            nis: NIS siswa
        
        Returns:
            dict: data siswa atau None
        """
        try:
            siswa_sheet = self._sheets['siswa']
            all_siswa = siswa_sheet.get_all_records()
            
            for siswa in all_siswa:
                if str(siswa.get('NIS', '')).strip() == str(nis).strip():
                    return siswa
            
            return None
        except Exception as e:
            print(f"Error getting siswa by NIS: {e}")
            return None
    
    # ==========================================
    # FUNGSI UNTUK JENIS PELANGGARAN
    # ==========================================
    
    def get_all_pelanggaran(self):
        """
        Mendapatkan semua jenis pelanggaran
        
        Returns:
            list: list of dict jenis pelanggaran
        """
        try:
            pelanggaran_sheet = self._sheets['pelanggaran']
            all_pelanggaran = pelanggaran_sheet.get_all_records()
            return all_pelanggaran
        except Exception as e:
            print(f"Error getting all pelanggaran: {e}")
            return []
    
    def get_pelanggaran_by_kode(self, kode):
        """
        Mendapatkan data pelanggaran berdasarkan kode
        
        Args:
            kode: kode pelanggaran (contoh: "P001")
        
        Returns:
            dict: data pelanggaran atau None
        """
        try:
            all_pelanggaran = self.get_all_pelanggaran()
            
            for p in all_pelanggaran:
                if str(p.get('Kode', '')).strip() == str(kode).strip():
                    return p
            
            return None
        except Exception as e:
            print(f"Error getting pelanggaran by kode: {e}")
            return None
    
    # ==========================================
    # FUNGSI UNTUK RIWAYAT PELANGGARAN
    # ==========================================
    
    def cek_duplikasi(self, nis, kode_pelanggaran, tanggal=None):
        """
        Cek apakah ada pelanggaran duplikat di hari yang sama
        antara jam 05:00 - 18:00
        
        Args:
            nis: NIS siswa
            kode_pelanggaran: kode pelanggaran
            tanggal: tanggal untuk dicek (default: hari ini)
        
        Returns:
            tuple: (is_duplicate: bool, waktu_sebelumnya: str)
        """
        try:
            if tanggal is None:
                tanggal = get_current_datetime()
            
            riwayat_sheet = self._sheets['riwayat']
            all_riwayat = riwayat_sheet.get_all_records()
            
            # Filter riwayat untuk siswa dan tanggal yang sama
            tanggal_str = format_tanggal(tanggal)
            
            for r in all_riwayat:
                # Cek NIS sama
                if str(r.get('NIS', '')).strip() != str(nis).strip():
                    continue
                
                # Cek tanggal sama
                if str(r.get('Tanggal', '')).strip() != tanggal_str:
                    continue
                
                # Cek kode pelanggaran sama
                if str(r.get('Kode', '')).strip() != str(kode_pelanggaran).strip():
                    continue
                
                # Cek waktu dalam range 05:00 - 18:00
                waktu_str = str(r.get('Waktu', ''))
                if waktu_str:
                    try:
                        jam = int(waktu_str.split(':')[0])
                        if DUPLIKASI_JAM_MULAI <= jam <= DUPLIKASI_JAM_SELESAI:
                            return True, waktu_str
                    except:
                        continue
            
            return False, None
            
        except Exception as e:
            print(f"Error checking duplikasi: {e}")
            return False, None
    
    def tambah_riwayat_pelanggaran(self, nis, nama, kelas, kode_pelanggaran, 
                                   jenis_pelanggaran, poin, link_foto, petugas):
        """
        Menambahkan riwayat pelanggaran baru
        
        Args:
            nis: NIS siswa
            nama: nama siswa
            kelas: kelas siswa
            kode_pelanggaran: kode pelanggaran
            jenis_pelanggaran: nama jenis pelanggaran
            poin: poin pelanggaran
            link_foto: link foto bukti di Google Drive
            petugas: nama admin yang mencatat
        
        Returns:
            bool: True jika berhasil
        """
        try:
            now = get_current_datetime()
            tanggal = format_tanggal(now)
            waktu = format_waktu(now)
            
            row = [
                tanggal,
                waktu,
                str(nis),
                nama,
                kelas,
                kode_pelanggaran,
                jenis_pelanggaran,
                poin,
                link_foto,
                petugas
            ]
            
            riwayat_sheet = self._sheets['riwayat']
            riwayat_sheet.append_row(row)
            
            return True
            
        except Exception as e:
            print(f"Error adding riwayat: {e}")
            return False
    
    def get_riwayat_by_nis(self, nis):
        """
        Mendapatkan semua riwayat pelanggaran siswa berdasarkan NIS
        
        Args:
            nis: NIS siswa
        
        Returns:
            list: list of dict riwayat pelanggaran
        """
        try:
            riwayat_sheet = self._sheets['riwayat']
            all_riwayat = riwayat_sheet.get_all_records()
            
            riwayat_siswa = [
                {
                    'tanggal': r.get('Tanggal', ''),
                    'waktu': r.get('Waktu', ''),
                    'pelanggaran': r.get('Jenis Pelanggaran', ''),
                    'poin': r.get('Poin', 0),
                    'link_foto': r.get('Link Foto', ''),
                    'petugas': r.get('Petugas', '')
                }
                for r in all_riwayat 
                if str(r.get('NIS', '')).strip() == str(nis).strip()
            ]
            
            return riwayat_siswa
            
        except Exception as e:
            print(f"Error getting riwayat by NIS: {e}")
            return []
    
    def hitung_total_poin(self, nis):
        """
        Menghitung total poin pelanggaran siswa
        
        Args:
            nis: NIS siswa
        
        Returns:
            int: total poin
        """
        try:
            riwayat = self.get_riwayat_by_nis(nis)
            total = sum(int(r.get('poin', 0)) for r in riwayat)
            return total
        except Exception as e:
            print(f"Error calculating total poin: {e}")
            return 0
    
    # ==========================================
    # FUNGSI UNTUK GOOGLE DRIVE
    # ==========================================
    
    def _get_or_create_folder(self, folder_name, parent_folder_id):
        """
        Mendapatkan folder atau membuat jika belum ada
        
        Args:
            folder_name: nama folder
            parent_folder_id: ID folder parent
        
        Returns:
            str: ID folder
        """
        try:
            # Cari folder dengan nama tersebut
            query = f"name='{folder_name}' and '{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            folders = results.get('files', [])
            
            if folders:
                return folders[0]['id']
            else:
                # Buat folder baru
                file_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [parent_folder_id]
                }
                folder = self.drive_service.files().create(
                    body=file_metadata,
                    fields='id'
                ).execute()
                
                return folder.get('id')
                
        except Exception as e:
            print(f"Error getting/creating folder: {e}")
            return None
    
    def upload_foto_bukti(self, file_path, kelas, nis):
        """
        Upload foto bukti ke Google Drive
        Otomatis membuat folder per hari
        
        Args:
            file_path: path file foto di local
            kelas: kelas siswa
            nis: NIS siswa
        
        Returns:
            str: link foto di Google Drive atau None
        """
        try:
            now = get_current_datetime()
            
            # Nama folder hari ini
            folder_hari = format_nama_folder_hari(now)
            
            # Dapatkan/buat folder hari ini
            folder_id = self._get_or_create_folder(
                folder_hari, 
                GOOGLE_DRIVE_FOLDER_ID
            )
            
            if not folder_id:
                print("Failed to get/create folder")
                return None
            
            # Nama file
            file_name = format_nama_file_foto(kelas, nis, now)
            
            # Upload file
            file_metadata = {
                'name': file_name,
                'parents': [folder_id]
            }
            
            media = MediaFileUpload(
                file_path,
                mimetype='image/jpeg',
                resumable=True
            )
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            # Set permission agar bisa diakses siapa saja dengan link
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            self.drive_service.permissions().create(
                fileId=file.get('id'),
                body=permission
            ).execute()
            
            # Return link
            return file.get('webViewLink')
            
        except Exception as e:
            print(f"Error uploading foto: {e}")
            return None
