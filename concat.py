# -*- coding: utf-8 -*-
"""
Menggabungkan hasil dari semua sumber (Google News, Bing News, situs lokal,
YouTube) menjadi satu dataset final dengan skema kolom yang seragam.

Jalankan setelah scraper_berita.py, scraper_berita_tambahan.py, dan
scraper_youtube.py sudah menghasilkan file CSV masing-masing.

Dependencies:
    pip install pandas --break-system-packages
"""

import pandas as pd
import os

FILES = {
    "berita_google": "data_berita_mentah.csv",
    "youtube": "data_youtube_mentah.csv",
}

OUTPUT = "dataset_gabungan.csv"


def muat_dan_rapikan(nama_sumber, path_file):
    if not os.path.exists(path_file):
        print(f"[LEWATI] {path_file} tidak ditemukan.")
        return pd.DataFrame()

    df = pd.read_csv(path_file)

    # Skema kolom seragam: isu, kata_kunci, teks, tanggal, platform, link_atau_id
    if nama_sumber in ("berita_google", "berita_tambahan"):
        df_rapi = pd.DataFrame({
            "isu": df.get("isu", ""),
            "kata_kunci": df.get("kata_kunci", ""),
            "teks": df.get("judul", "").fillna("") + ". " + df.get("ringkasan", "").fillna(""),
            "tanggal": df.get("tanggal", ""),
            "platform": "berita",
            "referensi": df.get("link", ""),
        })
    elif nama_sumber == "youtube":
        df_rapi = pd.DataFrame({
            "isu": df.get("isu", ""),
            "kata_kunci": df.get("kata_kunci", ""),
            "teks": df.get("teks", ""),
            "tanggal": df.get("tanggal", ""),
            "platform": "youtube",
            "referensi": df.get("video_id", ""),
        })
    else:
        df_rapi = pd.DataFrame()

    df_rapi["sumber_asal"] = nama_sumber
    return df_rapi


def main():
    semua_df = []
    for nama_sumber, path_file in FILES.items():
        df = muat_dan_rapikan(nama_sumber, path_file)
        if not df.empty:
            semua_df.append(df)
            print(f"{nama_sumber}: {len(df)} baris")

    if not semua_df:
        print("Tidak ada data yang bisa digabungkan.")
        return

    gabungan = pd.concat(semua_df, ignore_index=True)

    # Buang baris dengan teks kosong
    gabungan = gabungan[gabungan["teks"].str.strip().astype(bool)]

    # Buang duplikat berdasarkan teks yang identik
    sebelum = len(gabungan)
    gabungan = gabungan.drop_duplicates(subset=["teks"])
    print(f"Duplikat dibuang: {sebelum - len(gabungan)}")

    gabungan.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"\nDataset gabungan final: {len(gabungan)} baris -> {OUTPUT}")
    print("\nRingkasan per isu:")
    print(gabungan["isu"].value_counts())
    print("\nRingkasan per platform:")
    print(gabungan["platform"].value_counts())


if __name__ == "__main__":
    main()