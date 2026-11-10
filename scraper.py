# -*- coding: utf-8 -*-
"""
Scraper berita untuk proyek analisis sentimen isu ekonomi - BPS Kota Malang.

Pendekatan:
1. Google News RSS -> sumber utama, mencakup banyak portal sekaligus,
   tidak butuh API key, cocok untuk tahap pengumpulan awal.
2. Contoh scraping langsung ke satu situs berita lokal (BeautifulSoup),
   untuk kasus ketika butuh teks lengkap artikel (bukan cuma judul/ringkasan).

Catatan etika & teknis:
- Selalu cek robots.txt dan Ketentuan Layanan (ToS) tiap situs sebelum scraping.
- Beri jeda antar-request (time.sleep) agar tidak membebani server.
- Simpan data mentah apa adanya, baru dibersihkan di tahap preprocessing terpisah.
- Script ini untuk tujuan riset/tugas akademik (PKL), bukan untuk dipakai
  secara masif/komersial tanpa izin pemilik situs.

Dependencies:
    pip install requests beautifulsoup4 feedparser pandas --break-system-packages
"""

import time
import csv
import random
from datetime import datetime
from urllib.parse import quote

import requests
import feedparser
from bs4 import BeautifulSoup

from keywords import KEYWORDS, EXCLUDE_WORDS

# ---------------------------------------------------------------------------
# Konfigurasi umum
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

JEDA_MIN = 2   # detik, jeda minimum antar-request
JEDA_MAX = 5   # detik, jeda maksimum antar-request

OUTPUT_CSV = "data_berita_mentah.csv"


def jeda_random():
    """Jeda acak supaya scraping tidak terlalu agresif ke server."""
    time.sleep(random.uniform(JEDA_MIN, JEDA_MAX))


# ---------------------------------------------------------------------------
# 1. Scraping via Google News RSS
# ---------------------------------------------------------------------------

def ambil_dari_google_news_rss(keyword, bahasa="id", negara="ID"):
    """
    Mengambil daftar berita dari Google News RSS berdasarkan satu kata kunci.
    Mengembalikan list of dict: judul, link, tanggal, sumber, ringkasan, kata_kunci.
    """
    query = quote(keyword)
    url = f"https://news.google.com/rss/search?q={query}&hl={bahasa}&gl={negara}&ceid={negara}:{bahasa}"

    hasil = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            hasil.append({
                "kata_kunci": keyword,
                "judul": entry.get("title", "").strip(),
                "link": entry.get("link", "").strip(),
                "tanggal": entry.get("published", ""),
                "sumber": entry.get("source", {}).get("title", "")
                           if hasattr(entry, "source") else "",
                "ringkasan": BeautifulSoup(
                    entry.get("summary", ""), "html.parser"
                ).get_text().strip(),
            })
    except Exception as e:
        print(f"[GAGAL] Google News RSS untuk '{keyword}': {e}")

    return hasil


def kumpulkan_semua_google_news(keywords_dict):
    """Loop semua kata kunci di semua kategori isu, kumpulkan jadi satu list."""
    semua_hasil = []
    for isu, daftar_kata_kunci in keywords_dict.items():
        for kw in daftar_kata_kunci:
            print(f"Mengambil berita untuk: {kw} ...")
            hasil = ambil_dari_google_news_rss(kw)
            for h in hasil:
                h["isu"] = isu
            semua_hasil.extend(hasil)
            jeda_random()
    return semua_hasil


# ---------------------------------------------------------------------------
# 2. Contoh scraping isi artikel lengkap dari satu situs
#    (sesuaikan selector CSS dengan struktur HTML situs target,
#     karena tiap situs berbeda-beda dan bisa berubah sewaktu-waktu)
# ---------------------------------------------------------------------------

def ambil_isi_artikel(url):
    """
    Mengambil isi teks lengkap satu artikel berdasarkan URL.
    Selector di bawah ini CONTOH GENERIK, harus disesuaikan per situs:
    buka artikelnya di browser, inspect element, cari tag/class pembungkus isi berita.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Contoh umum: banyak situs berita menaruh isi artikel di <article>
        # atau div dengan class seperti "detail-text", "read__content", dll.
        # Sesuaikan salah satu baris di bawah sesuai hasil inspect element.
        kandidat_selector = [
            ("article", {}),
            ("div", {"class": "detail-text"}),
            ("div", {"class": "read__content"}),
            ("div", {"class": "post-content"}),
        ]

        for tag, attrs in kandidat_selector:
            elemen = soup.find(tag, attrs)
            if elemen:
                paragraf = elemen.find_all("p")
                teks = " ".join(p.get_text().strip() for p in paragraf)
                if teks:
                    return teks

        return ""  # selector tidak cocok, perlu disesuaikan manual
    except Exception as e:
        print(f"[GAGAL] Ambil isi artikel {url}: {e}")
        return ""


def lengkapi_isi_artikel(daftar_berita, maks_artikel=None):
    """
    Menambahkan kolom 'isi_lengkap' ke tiap item hasil Google News RSS
    dengan membuka link aslinya satu per satu.
    maks_artikel: batasi jumlah artikel yang diambil isinya (untuk uji coba awal).
    """
    target = daftar_berita[:maks_artikel] if maks_artikel else daftar_berita
    for i, item in enumerate(target, 1):
        print(f"[{i}/{len(target)}] Mengambil isi: {item['judul'][:60]}...")
        item["isi_lengkap"] = ambil_isi_artikel(item["link"])
        jeda_random()
    return target


# ---------------------------------------------------------------------------
# 3. Filter kata eksklusi (buang iklan/promosi)
# ---------------------------------------------------------------------------

def filter_eksklusi(daftar_berita, exclude_words=EXCLUDE_WORDS):
    hasil = []
    for item in daftar_berita:
        teks_cek = (item.get("judul", "") + " " + item.get("ringkasan", "")).lower()
        if not any(ex.lower() in teks_cek for ex in exclude_words):
            hasil.append(item)
    return hasil


# ---------------------------------------------------------------------------
# 4. Simpan ke CSV
# ---------------------------------------------------------------------------

def simpan_csv(daftar_berita, nama_file=OUTPUT_CSV):
    if not daftar_berita:
        print("Tidak ada data untuk disimpan.")
        return

    kolom = list(daftar_berita[0].keys())
    with open(nama_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=kolom)
        writer.writeheader()
        for row in daftar_berita:
            writer.writerow(row)

    print(f"Tersimpan {len(daftar_berita)} baris ke {nama_file}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Tahap 1: Mengumpulkan metadata berita dari Google News RSS ===")
    data_mentah = kumpulkan_semua_google_news(KEYWORDS)
    print(f"Total berita terkumpul (sebelum filter): {len(data_mentah)}")

    print("\n=== Tahap 2: Menyaring kata eksklusi (iklan/promosi) ===")
    data_bersih = filter_eksklusi(data_mentah)
    print(f"Total berita setelah filter: {len(data_bersih)}")

    # Tahap 3 bersifat opsional dan lebih lambat (membuka tiap link artikel).
    # Nonaktifkan dulu saat uji coba, aktifkan kalau sudah yakin dengan hasil Tahap 1-2.
    AMBIL_ISI_LENGKAP = False
    if AMBIL_ISI_LENGKAP:
        print("\n=== Tahap 3: Mengambil isi lengkap tiap artikel ===")
        data_bersih = lengkapi_isi_artikel(data_bersih, maks_artikel=50)

    print("\n=== Tahap 4: Menyimpan ke CSV ===")
    simpan_csv(data_bersih)

    print(f"\nSelesai. Waktu proses: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")