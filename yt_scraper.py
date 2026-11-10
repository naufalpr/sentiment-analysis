# -*- coding: utf-8 -*-
"""
Scraper komentar YouTube untuk proyek analisis sentimen isu ekonomi - BPS Kota Malang.

Memakai YouTube Data API v3 (resmi, gratis dengan kuota harian ~10.000 unit/hari).

Cara dapat API key:
1. Buka https://console.cloud.google.com/
2. Buat project baru (atau pakai yang sudah ada).
3. Aktifkan "YouTube Data API v3" di menu APIs & Services > Library.
4. Buat kredensial (Credentials) > API Key.
5. Tempel key tersebut ke variabel API_KEY di bawah, atau simpan sebagai
   environment variable YOUTUBE_API_KEY lalu baca dengan os.environ.

Dependencies:
    pip install google-api-python-client pandas --break-system-packages

Biaya kuota (perkiraan):
    - search.list  : 100 unit per panggilan
    - commentThreads.list : 1 unit per panggilan (per 100 komentar)
    Dengan kuota 10.000 unit/hari, bisa cari ~100 kali & ambil komentar
    dari banyak video. Atur MAKS_VIDEO_PER_KATA_KUNCI agar kuota cukup.
"""

import os
import csv
import time
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from keywords import KEYWORDS

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------

API_KEY = os.environ.get("YOUTUBE_API_KEY", "AIzaSyCAgVEjybvBzxokYyR5zSdWYwV9JrENfxw")

MAKS_VIDEO_PER_KATA_KUNCI = 5      # jumlah video yang dicari per kata kunci
MAKS_KOMENTAR_PER_VIDEO = 100      # jumlah komentar top-level yang diambil per video
OUTPUT_CSV = "data_youtube_mentah.csv"

youtube = build("youtube", "v3", developerKey=API_KEY)


# ---------------------------------------------------------------------------
# 1. Cari video berdasarkan kata kunci
# ---------------------------------------------------------------------------

def cari_video(keyword, maks_hasil=MAKS_VIDEO_PER_KATA_KUNCI):
    """Mengembalikan list video_id dan judul video hasil pencarian kata kunci."""
    hasil = []
    try:
        request = youtube.search().list(
            q=keyword,
            part="snippet",
            type="video",
            maxResults=maks_hasil,
            relevanceLanguage="id",
            regionCode="ID",
            order="relevance",
        )
        response = request.execute()
        for item in response.get("items", []):
            hasil.append({
                "video_id": item["id"]["videoId"],
                "judul_video": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "tanggal_video": item["snippet"]["publishedAt"],
            })
    except HttpError as e:
        print(f"[GAGAL] Cari video untuk '{keyword}': {e}")

    return hasil


# ---------------------------------------------------------------------------
# 2. Ambil komentar dari satu video
# ---------------------------------------------------------------------------

def ambil_komentar(video_id, maks_komentar=MAKS_KOMENTAR_PER_VIDEO):
    """Mengambil komentar top-level (bukan balasan) dari satu video."""
    komentar_list = []
    next_page_token = None

    try:
        while len(komentar_list) < maks_komentar:
            request = youtube.commentThreads().list(
                videoId=video_id,
                part="snippet",
                maxResults=min(100, maks_komentar - len(komentar_list)),
                pageToken=next_page_token,
                textFormat="plainText",
                order="relevance",
            )
            response = request.execute()

            for item in response.get("items", []):
                snippet = item["snippet"]["topLevelComment"]["snippet"]
                komentar_list.append({
                    "komentar_id": item["id"],
                    "teks": snippet.get("textDisplay", ""),
                    "tanggal": snippet.get("publishedAt", ""),
                    "like_count": snippet.get("likeCount", 0),
                    # Catatan privasi: author disimpan sebagai ID anonim,
                    # bukan nama asli, untuk menjaga privasi.
                })

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

    except HttpError as e:
        # Beberapa video menonaktifkan kolom komentar -> wajar error, lewati saja
        print(f"[INFO] Tidak bisa ambil komentar video {video_id}: {e}")

    return komentar_list


# ---------------------------------------------------------------------------
# 3. Gabungkan pencarian video + komentar untuk semua kata kunci
# ---------------------------------------------------------------------------

def kumpulkan_semua_youtube(keywords_dict):
    semua_data = []

    for isu, daftar_kata_kunci in keywords_dict.items():
        for kw in daftar_kata_kunci:
            print(f"\nMencari video untuk: {kw}")
            daftar_video = cari_video(kw)
            time.sleep(1)

            for video in daftar_video:
                print(f"  Mengambil komentar: {video['judul_video'][:60]}...")
                komentar_list = ambil_komentar(video["video_id"])

                for k in komentar_list:
                    semua_data.append({
                        "isu": isu,
                        "kata_kunci": kw,
                        "video_id": video["video_id"],
                        "judul_video": video["judul_video"],
                        "channel": video["channel"],
                        **k,
                    })

                time.sleep(1)

    return semua_data


# ---------------------------------------------------------------------------
# 4. Simpan ke CSV
# ---------------------------------------------------------------------------

def simpan_csv(data, nama_file=OUTPUT_CSV):
    if not data:
        print("Tidak ada data untuk disimpan.")
        return

    kolom = list(data[0].keys())
    with open(nama_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=kolom)
        writer.writeheader()
        writer.writerows(data)

    print(f"Tersimpan {len(data)} baris ke {nama_file}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if API_KEY == "TEMPEL_API_KEY_DI_SINI":
        print("Harap isi API_KEY terlebih dahulu (lihat petunjuk di bagian atas file).")
    else:
        print("=== Mengumpulkan komentar YouTube ===")
        data = kumpulkan_semua_youtube(KEYWORDS)
        simpan_csv(data)
        print(f"\nSelesai. Waktu proses: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")