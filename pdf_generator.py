"""
PDF Generator
Membuat laporan PDF riwayat pelanggaran siswa
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
from datetime import datetime
import os

from config import NAMA_SEKOLAH, ALAMAT_SEKOLAH, LOGO_SEKOLAH_PATH
from utils import get_current_datetime, format_tanggal, get_kategori_poin

class PDFGenerator:
    """Generator untuk membuat laporan PDF"""
    
    def __init__(self, output_path):
        """
        Inisialisasi PDF Generator
        
        Args:
            output_path: path untuk menyimpan file PDF
        """
        self.output_path = output_path
        self.width, self.height = A4
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom styles untuk PDF"""
        # Style untuk judul
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1a472a'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Style untuk subjudul
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#2d5016'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        
        # Style untuk heading
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#1a472a'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )
        
        # Style untuk teks biasa
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            spaceAfter=6,
            fontName='Helvetica'
        )
    
    def generate_laporan_siswa(self, siswa_data, riwayat_list, total_poin):
        """
        Generate laporan PDF untuk siswa
        
        Args:
            siswa_data: dict data siswa (nis, nama, kelas)
            riwayat_list: list riwayat pelanggaran
            total_poin: total poin pelanggaran
        
        Returns:
            str: path file PDF yang dibuat
        """
        # Buat dokumen PDF
        doc = SimpleDocTemplate(
            self.output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Container untuk elements
        elements = []
        
        # Header dengan logo
        elements.extend(self._create_header())
        
        # Data siswa
        elements.extend(self._create_siswa_info(siswa_data, total_poin))
        
        # Spacer
        elements.append(Spacer(1, 0.5*cm))
        
        # Tabel riwayat pelanggaran
        elements.extend(self._create_riwayat_table(riwayat_list))
        
        # Footer
        elements.extend(self._create_footer())
        
        # Build PDF
        doc.build(elements)
        
        return self.output_path
    
    def _create_header(self):
        """Membuat header PDF dengan logo"""
        elements = []
        
        # Logo (jika ada)
        if os.path.exists(LOGO_SEKOLAH_PATH):
            try:
                logo = Image(LOGO_SEKOLAH_PATH, width=2*cm, height=2*cm)
                logo.hAlign = 'CENTER'
                elements.append(logo)
                elements.append(Spacer(1, 0.3*cm))
            except:
                pass  # Skip jika logo gagal dimuat
        
        # Nama sekolah
        title = Paragraph(NAMA_SEKOLAH, self.title_style)
        elements.append(title)
        
        # Alamat
        subtitle = Paragraph(ALAMAT_SEKOLAH, self.subtitle_style)
        elements.append(subtitle)
        
        # Garis pemisah
        elements.append(Spacer(1, 0.3*cm))
        
        # Judul laporan
        laporan_title = Paragraph(
            "LAPORAN RIWAYAT PELANGGARAN SISWA",
            self.heading_style
        )
        elements.append(laporan_title)
        elements.append(Spacer(1, 0.5*cm))
        
        return elements
    
    def _create_siswa_info(self, siswa_data, total_poin):
        """Membuat tabel info siswa"""
        elements = []
        
        # Data siswa dalam format tabel
        kategori, emoji = get_kategori_poin(total_poin)
        
        data = [
            ['NIS', ':', str(siswa_data.get('NIS', siswa_data.get('nis', '')))],
            ['Nama', ':', str(siswa_data.get('Nama', siswa_data.get('nama', '')))],
            ['Kelas', ':', str(siswa_data.get('Kelas', siswa_data.get('kelas', '')))],
            ['Total Poin Pelanggaran', ':', str(total_poin)],
            ['Kategori', ':', kategori],
        ]
        
        # Style tabel
        table = Table(data, colWidths=[5*cm, 0.5*cm, 10*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        elements.append(table)
        
        return elements
    
    def _create_riwayat_table(self, riwayat_list):
        """Membuat tabel riwayat pelanggaran"""
        elements = []
        
        # Heading
        heading = Paragraph("Riwayat Pelanggaran", self.heading_style)
        elements.append(heading)
        elements.append(Spacer(1, 0.3*cm))
        
        if not riwayat_list:
            no_data = Paragraph("Tidak ada riwayat pelanggaran", self.normal_style)
            elements.append(no_data)
            return elements
        
        # Header tabel
        data = [['No', 'Tanggal', 'Waktu', 'Jenis Pelanggaran', 'Poin', 'Petugas']]
        
        # Data riwayat
        for idx, r in enumerate(riwayat_list, 1):
            row = [
                str(idx),
                str(r.get('tanggal', '')),
                str(r.get('waktu', '')),
                str(r.get('pelanggaran', '')),
                str(r.get('poin', '')),
                str(r.get('petugas', ''))
            ]
            data.append(row)
        
        # Total poin
        total_poin = sum(int(r.get('poin', 0)) for r in riwayat_list)
        data.append(['', '', '', 'TOTAL POIN', str(total_poin), ''])
        
        # Buat tabel
        table = Table(data, colWidths=[1*cm, 2.5*cm, 1.5*cm, 6*cm, 1.5*cm, 3*cm])
        
        # Style tabel
        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a472a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 8),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # No
            ('ALIGN', (1, 1), (2, -2), 'CENTER'),  # Tanggal & Waktu
            ('ALIGN', (4, 1), (4, -2), 'CENTER'),  # Poin
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Total row
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f5e9')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 9),
            ('ALIGN', (3, -1), (4, -1), 'CENTER'),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#1a472a')),
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            
            # Alternating row colors
            *[('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f5f5f5')) 
              for i in range(2, len(data)-1, 2)]
        ]))
        
        elements.append(table)
        
        return elements
    
    def _create_footer(self):
        """Membuat footer PDF"""
        elements = []
        
        elements.append(Spacer(1, 1*cm))
        
        # Tanggal cetak
        now = get_current_datetime()
        tanggal_cetak = format_tanggal(now)
        
        footer_text = f"Dicetak pada: {tanggal_cetak}"
        footer = Paragraph(footer_text, self.normal_style)
        elements.append(footer)
        
        # Catatan
        catatan_style = ParagraphStyle(
            'Catatan',
            parent=self.normal_style,
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER,
            spaceAfter=0
        )
        
        elements.append(Spacer(1, 0.5*cm))
        catatan = Paragraph(
            "Dokumen ini dibuat secara otomatis oleh Sistem Pencatatan Pelanggaran Siswa",
            catatan_style
        )
        elements.append(catatan)
        
        return elements
