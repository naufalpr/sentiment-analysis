# -*- coding: utf-8 -*-
"""
Preprocessing teks bahasa Indonesia untuk dataset_gabungan.csv
(hasil dari gabung_data.py).

Tahapan:
1. Case folding (huruf kecil)
2. Hapus URL, mention, hashtag, angka, tanda baca berlebih
3. Normalisasi kata slang -> baku
4. Tokenisasi
5. Stopword removal
6. Stemming (Sastrawi)
7. Buang teks yang jadi terlalu pendek/kosong setelah dibersihkan

Dependencies:
    pip install Sastrawi pandas --break-system-packages

Catatan:
    - Kolom 'teks_bersih' untuk dipakai di model klasik (TF-IDF, dll).
    - Kolom 'teks_tanpa_stem' disimpan juga (tanpa stemming) karena model
      berbasis transformer (IndoBERT) biasanya lebih baik TANPA stemming,
      cukup dibersihkan ringan saja.
"""

import re
import csv
import pandas as pd

from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

INPUT_CSV = "dataset_gabungan.csv"
OUTPUT_CSV = "dataset_preprocessed.csv"

# ---------------------------------------------------------------------------
# Kamus normalisasi slang -> baku (contoh awal, silakan ditambah sendiri
# sambil mengecek data; ini bagian yang paling berpengaruh ke kualitas hasil)
# ---------------------------------------------------------------------------

KAMUS_SLANG = {
    "gak": "tidak", "ga": "tidak", "g": "tidak", "nggak": "tidak", "ngga": "tidak",
    "gpp": "tidak apa apa", "gapapa": "tidak apa apa",
    "bgt": "banget", "bngt": "banget",
    "udh": "sudah", "udah": "sudah", "dah": "sudah",
    "blm": "belum", "blom": "belum",
    "yg": "yang", "yng": "yang",
    "dgn": "dengan", "dg": "dengan",
    "krn": "karena", "karna": "karena",
    "tdk": "tidak", "tak": "tidak",
    "jd": "jadi", "jdi": "jadi",
    "jg": "juga", "juga2": "juga",
    "sm": "sama", "ama": "sama",
    "org": "orang", "orng": "orang",
    "skrg": "sekarang", "skrng": "sekarang",
    "trs": "terus", "trus": "terus",
    "kalo": "kalau", "klo": "kalau", "kl": "kalau",
    "gmn": "bagaimana", "gimana": "bagaimana",
    "knp": "kenapa", "knapa": "kenapa",
    "emg": "memang", "emang": "memang",
    "bgini": "begini", "bgitu": "begitu",
    "bener": "benar", "bnr": "benar",
    "duit": "uang", "cuan": "untung",
    "mahal2": "mahal", "naik2": "naik",
    "pdhl": "padahal", "padhal": "padahal",
    "sbnrnya": "sebenarnya", "sbenernya": "sebenarnya",
    "ckp": "cukup",
    "msh": "masih",
    "bs": "bisa", "bisa2": "bisa",
    "dr": "dari",
    "utk": "untuk", "u/": "untuk",
    "spy": "supaya",
    "pemerintah2": "pemerintah",
    "rakyat2": "rakyat",
}


# ---------------------------------------------------------------------------
# Inisialisasi stemmer & stopword remover (Sastrawi)
# ---------------------------------------------------------------------------

stemmer = StemmerFactory().create_stemmer()
stopword_remover = StopWordRemoverFactory().create_stop_word_remover()

# Tambahan stopword khusus domain (kata umum yang tidak membawa sentimen)
STOPWORD_TAMBAHAN = {
    "nya", "yg", "sih", "deh", "dong", "kok", "loh", "lho", "ya", "yaa",
    "min", "kak", "gan", "bro", "sist",
}

# PENTING: kata negasi JANGAN ikut dibuang sebagai stopword, karena mengubah
# makna kalimat secara total untuk tugas sentimen ("tidak bagus" != "bagus").
# Sastrawi's default stopword list biasanya sudah memasukkan "tidak", "bukan",
# dll, jadi kita keluarkan lagi dari daftar yang dibuang.
KATA_NEGASI = {"tidak", "bukan", "jangan", "belum", "tanpa", "tak"}


# ---------------------------------------------------------------------------
# Fungsi-fungsi pembersihan
# ---------------------------------------------------------------------------

def case_folding(teks):
    return str(teks).lower()


def hapus_url_mention_hashtag(teks):
    teks = re.sub(r"http\S+|www\.\S+", " ", teks)          # URL
    teks = re.sub(r"@\w+", " ", teks)                       # mention
    teks = re.sub(r"#\w+", " ", teks)                       # hashtag
    teks = re.sub(r"\S+@\S+", " ", teks)                    # email
    return teks


def hapus_karakter_khusus(teks):
    teks = re.sub(r"[^a-zA-Z\s]", " ", teks)                # hanya huruf
    teks = re.sub(r"\s+", " ", teks).strip()                # spasi berlebih
    return teks


def normalisasi_slang(teks, kamus=KAMUS_SLANG):
    kata_list = teks.split()
    hasil = [kamus.get(k, k) for k in kata_list]
    return " ".join(hasil)


def hapus_stopword(teks):
    # Lindungi kata negasi dulu dengan token sementara, supaya tidak ikut
    # dibuang oleh Sastrawi's stopword remover.
    kata_asli = teks.split()
    teks_terlindungi = " ".join(
        f"NEGASI_{k.upper()}" if k in KATA_NEGASI else k for k in kata_asli
    )

    teks_bersih = stopword_remover.remove(teks_terlindungi)

    # Kembalikan token negasi ke bentuk aslinya
    kata_list = []
    for k in teks_bersih.split():
        if k.startswith("NEGASI_"):
            kata_list.append(k.replace("NEGASI_", "").lower())
        elif k not in STOPWORD_TAMBAHAN:
            kata_list.append(k)

    return " ".join(kata_list)


def stemming(teks):
    return stemmer.stem(teks)


# ---------------------------------------------------------------------------
# Stemming dengan cache per kata unik (JAUH lebih cepat untuk data besar)
# ---------------------------------------------------------------------------
# Sastrawi men-stem per KATA dengan pencarian ke kamus, dan prosesnya murni
# Python (tidak dioptimasi). Kalau dipanggil ulang untuk tiap baris teks,
# kata yang sama (misalnya "mahal", "naik", "pemerintah") di-stem berkali-kali
# secara sia-sia. Cache ini membuat tiap kata unik hanya di-stem SEKALI,
# lalu hasilnya dipakai ulang untuk kemunculan berikutnya. Biasanya ini
# mempercepat proses 5-20x lipat tergantung seberapa berulang kosakatanya.

_cache_stem = {}


def stemming_dengan_cache(teks):
    hasil = []
    for kata in teks.split():
        if kata not in _cache_stem:
            _cache_stem[kata] = stemmer.stem(kata)
        hasil.append(_cache_stem[kata])
    return " ".join(hasil)


# ---------------------------------------------------------------------------
# Pipeline lengkap
# ---------------------------------------------------------------------------

def bersihkan_ringan(teks):
    """Untuk model transformer (IndoBERT dkk) - tanpa stemming/stopword removal
    karena model ini butuh konteks kalimat yang lebih utuh."""
    teks = case_folding(teks)
    teks = hapus_url_mention_hashtag(teks)
    teks = hapus_karakter_khusus(teks)
    teks = normalisasi_slang(teks)
    teks = re.sub(r"\s+", " ", teks).strip()
    return teks


def bersihkan_lengkap(teks):
    """Untuk model klasik (TF-IDF + Naive Bayes/SVM) - full pipeline."""
    teks = bersihkan_ringan(teks)
    teks = hapus_stopword(teks)
    teks = stemming(teks)
    teks = re.sub(r"\s+", " ", teks).strip()
    return teks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"Membaca {INPUT_CSV} ...")
    df = pd.read_csv(INPUT_CSV)
    print(f"Jumlah baris awal: {len(df)}")

    df["teks"] = df["teks"].fillna("").astype(str)

    print("Membersihkan teks (ringan, untuk IndoBERT) ...")
    df["teks_tanpa_stem"] = df["teks"].apply(bersihkan_ringan)

    print("Menghapus stopword ...")
    df["teks_bersih"] = df["teks_tanpa_stem"].apply(hapus_stopword)

    jumlah_kata_unik = len(set(" ".join(df["teks_bersih"]).split()))
    print(f"Stemming {jumlah_kata_unik} kata unik (dengan cache, jauh lebih cepat "
          f"daripada stemming {len(df)} baris penuh satu per satu) ...")
    df["teks_bersih"] = df["teks_bersih"].apply(stemming_dengan_cache)

    # Buang baris yang jadi terlalu pendek setelah dibersihkan (< 3 kata)
    sebelum = len(df)
    df = df[df["teks_tanpa_stem"].str.split().str.len() >= 3]
    print(f"Baris dibuang karena terlalu pendek: {sebelum - len(df)}")

    # Buang duplikat setelah dibersihkan (menangkap duplikat yang beda format tapi sama isi)
    sebelum = len(df)
    df = df.drop_duplicates(subset=["teks_tanpa_stem"])
    print(f"Duplikat dibuang (setelah dibersihkan): {sebelum - len(df)}")

    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\nSelesai. {len(df)} baris tersimpan ke {OUTPUT_CSV}")
    print("\nKolom yang dihasilkan:")
    print("  - teks            : teks asli sebelum dibersihkan")
    print("  - teks_tanpa_stem : dibersihkan ringan, untuk IndoBERT/transformer")
    print("  - teks_bersih     : dibersihkan lengkap + stemming, untuk model klasik")
    print("\nContoh hasil (5 baris pertama):")
    print(df[["teks", "teks_bersih"]].head())


if __name__ == "__main__":
    main()