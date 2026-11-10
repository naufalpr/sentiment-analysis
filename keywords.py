# -*- coding: utf-8 -*-
"""
Daftar kata kunci final untuk pengumpulan data sentimen ekonomi
Konteks: BPS Kota Malang
"""

LOKASI = ["Malang", "Kota Malang", "Malang Raya"]

KEYWORDS = {
    "beras": [
        "harga beras Malang",
        "beras mahal Malang",
        "beras naik Malang",
        "beras langka Malang",
        "stok beras Malang",
        "SPHP Malang",
        "operasi pasar beras Malang",
    ],
    "inflasi": [
        "inflasi Kota Malang",
        "inflasi Malang Raya",
        "IHK Malang",
        "daya beli Malang",
        "harga kebutuhan pokok Malang",
        "rilis BPS Malang inflasi",
    ],
    "minyak_goreng": [
        "minyak goreng langka Malang",
        "MinyaKita Malang",
        "harga minyak goreng Malang",
        "minyak goreng mahal Malang",
    ],
    "cabai_bawang_telur": [
        "harga cabai Malang",
        "cabai mahal Malang",
        "harga bawang Malang",
        "harga telur Malang",
        "harga ayam Malang",
        "Pasar Dinoyo harga",
        "Pasar Besar Malang harga",
    ],
    "bbm_energi": [
        "harga BBM Malang",
        "Pertalite Malang",
        "gas melon langka Malang",
        "elpiji 3 kg Malang",
        "tarif angkot Malang naik",
    ],
    "tenaga_kerja": [
        "PHK Malang",
        "UMK Malang",
        "cari kerja Malang",
        "pengangguran Malang",
        "bansos Malang",
    ],
    "sembako_umum": [
        "harga sembako Malang",
        "sembako naik Malang",
        "harga pasar Malang naik",
    ],
}

# Kata kunci eksklusi untuk menyaring iklan/promosi saat filtering hasil
EXCLUDE_WORDS = ["giveaway", "promo", "diskon", "jual", "loker", "lowongan iklan"]

# Sumber berita lokal yang bisa dipakai sebagai filter domain (opsional)
SUMBER_LOKAL = [
    "malangtimes.com",
    "radarmalang.jawapos.com",
    "malang-post.com",
    "timesindonesia.co.id",
    "suryamalang.tribunnews.com",
]