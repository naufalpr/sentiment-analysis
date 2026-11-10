# -*- coding: utf-8 -*-
"""
Pelabelan sentimen otomatis memakai model berbasis IndoBERT/RoBERTa Indonesia
yang SUDAH di-fine-tune untuk klasifikasi sentimen (tidak perlu training
dari nol -- langsung pakai untuk prediksi/inference).

Model yang dipakai: w11wo/indonesian-roberta-base-sentiment-classifier
(publik di Hugging Face, 3 kelas: positive, neutral, negative)

Kenapa pakai teks_tanpa_stem (bukan teks_bersih)?
    Model berbasis transformer seperti IndoBERT/RoBERTa dilatih dengan
    kalimat utuh, bukan kata-kata yang sudah di-stem dan dibuang stopword-nya.
    Stemming justru bisa MERUSAK konteks yang dipahami model ini.

Dependencies:
    pip install transformers torch pandas --break-system-packages

Catatan performa:
    - Di CPU: untuk beberapa ribu baris bisa memakan waktu beberapa menit.
    - Kalau ada GPU (CUDA), script otomatis memakainya dan jauh lebih cepat.
    - Pertama kali dijalankan, model (~500 MB) akan diunduh otomatis dari
      Hugging Face dan disimpan di cache lokal -- butuh koneksi internet
      untuk sekali unduh ini saja, setelahnya bisa dipakai offline.
"""

import pandas as pd
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification

INPUT_CSV = "dataset_preprocessed.csv"
OUTPUT_CSV = "dataset_labeled_indobert.csv"

MODEL_NAME = "w11wo/indonesian-roberta-base-sentiment-classifier"

BATCH_SIZE = 16          # naikkan kalau pakai GPU dengan memori besar
MAKS_PANJANG_TOKEN = 128  # potong teks yang terlalu panjang

# Pemetaan label mentah dari model -> label bahasa Indonesia yang konsisten
# dengan sisa proyek (positif/negatif/netral)
PETA_LABEL = {
    "positive": "positif",
    "negative": "negatif",
    "neutral": "netral",
}


def siapkan_pipeline():
    device = 0 if torch.cuda.is_available() else -1
    print(f"Memuat model {MODEL_NAME} ...")
    print(f"Perangkat: {'GPU (CUDA)' if device == 0 else 'CPU'}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)

    pipe = pipeline(
        "sentiment-analysis",
        model=model,
        tokenizer=tokenizer,
        device=device,
        truncation=True,
        max_length=MAKS_PANJANG_TOKEN,
    )
    return pipe


def beri_label_batch(pipe, daftar_teks, batch_size=BATCH_SIZE):
    """Memproses teks per batch untuk efisiensi, mengembalikan list (label, skor)."""
    hasil = []
    total = len(daftar_teks)

    for i in range(0, total, batch_size):
        batch = daftar_teks[i:i + batch_size]
        # Ganti teks kosong dengan spasi supaya tidak error, nanti diberi label netral
        batch_aman = [t if isinstance(t, str) and t.strip() else " " for t in batch]

        prediksi = pipe(batch_aman)
        for p in prediksi:
            label_mentah = p["label"].lower()
            label_rapi = PETA_LABEL.get(label_mentah, label_mentah)
            hasil.append((label_rapi, round(p["score"], 4)))

        selesai = min(i + batch_size, total)
        print(f"  Diproses: {selesai}/{total}", end="\r")

    print()  # newline setelah progress selesai
    return hasil


def main():
    print(f"Membaca {INPUT_CSV} ...")
    df = pd.read_csv(INPUT_CSV)
    print(f"Jumlah baris: {len(df)}")

    # Pakai teks_tanpa_stem (dibersihkan ringan, tanpa stemming) -- lihat
    # penjelasan di docstring atas kenapa bukan teks_bersih.
    kolom_teks = "teks_tanpa_stem" if "teks_tanpa_stem" in df.columns else "teks"
    daftar_teks = df[kolom_teks].fillna("").astype(str).tolist()

    pipe = siapkan_pipeline()

    print("Melabeli sentimen ...")
    hasil_label = beri_label_batch(pipe, daftar_teks)

    df["label_indobert"] = [h[0] for h in hasil_label]
    df["skor_confidence"] = [h[1] for h in hasil_label]

    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\nSelesai. Tersimpan ke {OUTPUT_CSV}")

    print("\nDistribusi label:")
    print(df["label_indobert"].value_counts())

    print("\nContoh hasil (10 baris acak):")
    kolom_tampil = [kolom_teks, "label_indobert", "skor_confidence"]
    print(df[kolom_tampil].sample(min(10, len(df))).to_string(index=False))

    print("\nRata-rata confidence score per label:")
    print(df.groupby("label_indobert")["skor_confidence"].mean().round(3))


if __name__ == "__main__":
    main()