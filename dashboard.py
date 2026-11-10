# -*- coding: utf-8 -*-
"""
Dashboard analisis sentimen isu ekonomi - BPS Kota Malang
Dijalankan dengan: streamlit run dashboard.py

Dependencies:
    pip install streamlit pandas plotly wordcloud matplotlib --break-system-packages

Input yang diharapkan: dataset_labeled_indobert.csv (atau sesuaikan nama
file di DATA_PATH) dengan kolom minimal:
    - tanggal, isu, platform, teks (atau teks_tanpa_stem), sentimen, skor_keyakinan

Kalau file belum ada, dashboard tetap jalan memakai DATA CONTOH (dummy)
supaya tata letak bisa langsung dicoba sebelum data asli siap.
"""

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
from wordcloud import WordCloud
import matplotlib
matplotlib.use("Agg")  # backend non-GUI, penting untuk server/headless
import matplotlib.pyplot as plt
from datetime import timedelta

# ---------------------------------------------------------------------------
# Konfigurasi halaman
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Dashboard Sentimen Ekonomi - Kota Malang",
    page_icon="📊",
    layout="wide",
)

DATA_PATH = "dataset_labeled_indobert.csv"
DATA_INFLASI_PATH = "data_inflasi_malang.csv"  # opsional, lihat bagian korelasi


# ---------------------------------------------------------------------------
# Memuat data (dengan fallback ke data contoh kalau file belum ada)
# ---------------------------------------------------------------------------

@st.cache_data
def buat_data_contoh(n=1500):
    """Data contoh acak supaya tata letak dashboard bisa langsung dicoba."""
    rng = np.random.default_rng(42)

    isu_list = ["beras", "inflasi", "minyak_goreng", "cabai_bawang_telur",
                "bbm_energi", "tenaga_kerja"]
    platform_list = ["berita", "youtube"]
    sentimen_list = ["negatif", "netral", "positif"]
    # Bias supaya lebih realistis: lebih banyak negatif untuk isu harga
    probabilitas_sentimen = [0.55, 0.30, 0.15]

    tanggal_mulai = pd.Timestamp("2026-04-01")
    tanggal = [tanggal_mulai + timedelta(days=int(d)) for d in rng.integers(0, 180, n)]

    contoh_teks = {
        "negatif": [
            "Harga beras naik terus, susah banget buat emak-emak",
            "Minyak goreng langka lagi di minimarket",
            "Gaji nggak naik tapi harga-harga pada naik semua",
        ],
        "netral": [
            "BPS merilis data inflasi bulan ini",
            "Harga cabai di Pasar Dinoyo hari ini segini",
            "Pemerintah mengumumkan kebijakan harga pangan",
        ],
        "positif": [
            "Alhamdulillah harga telur mulai turun",
            "Operasi pasar beras membantu warga Malang",
            "Stok minyak goreng sudah kembali normal",
        ],
    }

    sentimen = rng.choice(sentimen_list, size=n, p=probabilitas_sentimen)
    teks = [rng.choice(contoh_teks[s]) for s in sentimen]

    df = pd.DataFrame({
        "tanggal": tanggal,
        "isu": rng.choice(isu_list, size=n),
        "platform": rng.choice(platform_list, size=n),
        "teks": teks,
        "sentimen": sentimen,
        "skor_confidence": rng.uniform(0.55, 0.98, n).round(3),
    })
    return df.sort_values("tanggal").reset_index(drop=True)


@st.cache_data
def muat_data():
    try:
        df = pd.read_csv(DATA_PATH)
        sumber_data = "file"
    except FileNotFoundError:
        df = buat_data_contoh()
        sumber_data = "contoh"

    # Konversi eksplisit ke datetime, apa pun sumbernya. Beberapa hal yang
    # ditangani di sini:
    #   - format="mixed": tanpa ini, pandas mengunci ke format baris pertama
    #     dan menganggap baris lain dengan format BERBEDA (meski valid)
    #     sebagai gagal. Penting karena data gabungan dari berita + YouTube
    #     + sumber lain sering punya format tanggal yang tidak seragam.
    #   - utc=True lalu tz_localize(None): sebagian sumber (terutama API
    #     YouTube) mengembalikan tanggal dengan info zona waktu (format
    #     ...Z / ISO8601 dengan offset), sebagian lain tidak. Tanpa ini,
    #     pandas melempar error "Mixed timezones detected".
    #   - errors="coerce": nilai yang tetap tidak bisa diparsing (kosong,
    #     teks bukan tanggal, dll) diubah jadi NaT alih-alih bikin proses gagal.
    df["tanggal"] = pd.to_datetime(
        df["tanggal"], errors="coerce", format="mixed", utc=True
    ).dt.tz_localize(None)

    jumlah_sebelum = len(df)
    df = df.dropna(subset=["tanggal"])
    jumlah_dibuang = jumlah_sebelum - len(df)

    return df, sumber_data, jumlah_dibuang


df, sumber_data, jumlah_tanggal_invalid = muat_data()

if jumlah_tanggal_invalid > 0:
    st.warning(
        f"{jumlah_tanggal_invalid} baris dibuang karena kolom 'tanggal' "
        "tidak bisa dibaca sebagai format tanggal yang valid. Cek kembali "
        "format tanggal di file sumbermu, idealnya YYYY-MM-DD "
        "(contoh: 2026-09-12)."
    )

if df.empty:
    st.error(
        "Tidak ada baris dengan tanggal valid setelah pembersihan. "
        "Dashboard tidak bisa ditampilkan. Periksa kembali kolom 'tanggal' "
        f"di file `{DATA_PATH}`."
    )
    st.stop()

if sumber_data == "contoh":
    st.warning(
        f"File `{DATA_PATH}` belum ditemukan. Dashboard ini sementara "
        "menampilkan DATA CONTOH (acak) supaya tata letak bisa dicoba. "
        "Ganti dengan data asli hasil pelabelan untuk analisis sesungguhnya."
    )


# ---------------------------------------------------------------------------
# Sidebar: filter
# ---------------------------------------------------------------------------

st.sidebar.header("Filter Data")

tanggal_min = df["tanggal"].min().date()
tanggal_max = df["tanggal"].max().date()

rentang_tanggal = st.sidebar.date_input(
    "Rentang tanggal",
    value=(tanggal_min, tanggal_max),
    min_value=tanggal_min,
    max_value=tanggal_max,
)

daftar_isu = sorted(df["isu"].unique())
isu_dipilih = st.sidebar.multiselect("Isu", daftar_isu, default=daftar_isu)

daftar_platform = sorted(df["platform"].unique())
platform_dipilih = st.sidebar.multiselect(
    "Platform", daftar_platform, default=daftar_platform
)

ambang_keyakinan = st.sidebar.slider(
    "Minimal skor keyakinan model", 0.0, 1.0, 0.5, 0.05
)

# Terapkan filter
if len(rentang_tanggal) == 2:
    mulai, akhir = rentang_tanggal
else:
    mulai, akhir = tanggal_min, tanggal_max

df_filtered = df[
    (df["tanggal"].dt.date >= mulai)
    & (df["tanggal"].dt.date <= akhir)
    & (df["isu"].isin(isu_dipilih))
    & (df["platform"].isin(platform_dipilih))
    & (df["skor_confidence"] >= ambang_keyakinan)
]

st.sidebar.markdown(f"**{len(df_filtered)}** dari {len(df)} baris ditampilkan")


# ---------------------------------------------------------------------------
# Judul
# ---------------------------------------------------------------------------

st.title("📊 Dashboard Sentimen Isu Ekonomi - Kota Malang")
st.caption("Analisis sentimen media sosial/berita terhadap isu beras, inflasi, dan harga komoditas")

if df_filtered.empty:
    st.error("Tidak ada data yang cocok dengan filter yang dipilih.")
    st.stop()


# ---------------------------------------------------------------------------
# KPI cards
# ---------------------------------------------------------------------------

kolom1, kolom2, kolom3, kolom4 = st.columns(4)

total_data = len(df_filtered)
pct_negatif = (df_filtered["sentimen"] == "negatif").mean() * 100
pct_netral = (df_filtered["sentimen"] == "netral").mean() * 100
pct_positif = (df_filtered["sentimen"] == "positif").mean() * 100

kolom1.metric("Total Data", f"{total_data:,}")
kolom2.metric("Sentimen Negatif", f"{pct_negatif:.1f}%")
kolom3.metric("Sentimen Netral", f"{pct_netral:.1f}%")
kolom4.metric("Sentimen Positif", f"{pct_positif:.1f}%")

st.divider()


# ---------------------------------------------------------------------------
# Tren sentimen dari waktu ke waktu
# ---------------------------------------------------------------------------

st.subheader("Tren Sentimen dari Waktu ke Waktu")

df_tren = (
    df_filtered.groupby([pd.Grouper(key="tanggal", freq="W"), "sentimen"])
    .size()
    .reset_index(name="jumlah")
)
df_tren_pct = df_tren.copy()
total_per_minggu = df_tren.groupby("tanggal")["jumlah"].transform("sum")
df_tren_pct["persentase"] = df_tren["jumlah"] / total_per_minggu * 100

warna_sentimen = {"negatif": "#d62728", "netral": "#7f7f7f", "positif": "#2ca02c"}

fig_tren = px.area(
    df_tren_pct,
    x="tanggal",
    y="persentase",
    color="sentimen",
    color_discrete_map=warna_sentimen,
    labels={"persentase": "Persentase (%)", "tanggal": "Minggu"},
)
st.plotly_chart(fig_tren, width='stretch')


# ---------------------------------------------------------------------------
# Perbandingan antar isu dan platform
# ---------------------------------------------------------------------------

kolom_kiri, kolom_kanan = st.columns(2)

with kolom_kiri:
    st.subheader("Sentimen per Isu")
    df_isu = (
        df_filtered.groupby(["isu", "sentimen"]).size().reset_index(name="jumlah")
    )
    fig_isu = px.bar(
        df_isu,
        x="isu",
        y="jumlah",
        color="sentimen",
        color_discrete_map=warna_sentimen,
        barmode="stack",
    )
    st.plotly_chart(fig_isu, width='stretch')

with kolom_kanan:
    st.subheader("Sentimen per Platform")
    df_platform = (
        df_filtered.groupby(["platform", "sentimen"]).size().reset_index(name="jumlah")
    )
    fig_platform = px.bar(
        df_platform,
        x="platform",
        y="jumlah",
        color="sentimen",
        color_discrete_map=warna_sentimen,
        barmode="group",
    )
    st.plotly_chart(fig_platform, width='stretch')


# ---------------------------------------------------------------------------
# Word cloud per sentimen
# ---------------------------------------------------------------------------

st.subheader("Kata yang Sering Muncul per Sentimen")

tab_negatif, tab_netral, tab_positif = st.tabs(["Negatif", "Netral", "Positif"])


def tampilkan_wordcloud(teks_gabungan, kolom_container):
    if not teks_gabungan.strip():
        kolom_container.info("Tidak ada data untuk ditampilkan.")
        return
    wc = WordCloud(
        width=800, height=350, background_color="white", colormap="viridis"
    ).generate(teks_gabungan)
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    kolom_container.pyplot(fig)


kolom_teks = "teks_tanpa_stem" if "teks_tanpa_stem" in df_filtered.columns else "teks"

with tab_negatif:
    teks_negatif = " ".join(df_filtered.loc[df_filtered["sentimen"] == "negatif", kolom_teks].astype(str))
    tampilkan_wordcloud(teks_negatif, tab_negatif)

with tab_netral:
    teks_netral = " ".join(df_filtered.loc[df_filtered["sentimen"] == "netral", kolom_teks].astype(str))
    tampilkan_wordcloud(teks_netral, tab_netral)

with tab_positif:
    teks_positif = " ".join(df_filtered.loc[df_filtered["sentimen"] == "positif", kolom_teks].astype(str))
    tampilkan_wordcloud(teks_positif, tab_positif)


# ---------------------------------------------------------------------------
# Contoh komentar per sentimen (untuk validasi manual)
# ---------------------------------------------------------------------------

st.subheader("Contoh Komentar per Sentimen")

sentimen_dipilih_tabel = st.selectbox(
    "Pilih sentimen untuk dilihat contohnya", ["negatif", "netral", "positif"]
)

df_contoh = (
    df_filtered[df_filtered["sentimen"] == sentimen_dipilih_tabel]
    .sort_values("skor_confidence", ascending=False)
    .head(10)
)
st.dataframe(
    df_contoh[["tanggal", "isu", "platform", kolom_teks, "skor_confidence"]],
    width='stretch',
    hide_index=True,
)


# ---------------------------------------------------------------------------
# Korelasi dengan data inflasi BPS (opsional, perlu data_inflasi_malang.csv)
# ---------------------------------------------------------------------------

st.subheader("Korelasi dengan Inflasi Resmi BPS")

try:
    df_inflasi = pd.read_csv(DATA_INFLASI_PATH, parse_dates=["tanggal"])

    df_sentimen_bulanan = (
        df_filtered.assign(bulan=df_filtered["tanggal"].dt.to_period("M").dt.to_timestamp())
        .groupby("bulan")
        .apply(lambda g: (g["sentimen"] == "negatif").mean() * 100)
        .reset_index(name="pct_sentimen_negatif")
    )

    df_gabung = pd.merge(
        df_sentimen_bulanan, df_inflasi, left_on="bulan", right_on="tanggal", how="inner"
    )

    if not df_gabung.empty:
        fig_korelasi = px.line(
            df_gabung,
            x="bulan",
            y=["pct_sentimen_negatif", "inflasi_persen"],
            labels={"value": "Nilai", "variable": "Indikator"},
        )
        st.plotly_chart(fig_korelasi, width='stretch')

        korelasi = df_gabung["pct_sentimen_negatif"].corr(df_gabung["inflasi_persen"])
        st.caption(f"Koefisien korelasi: {korelasi:.2f} "
                   "(mendekati 1 = sentimen negatif naik seiring inflasi naik)")
    else:
        st.info("Tidak ada bulan yang cocok antara data sentimen dan data inflasi.")

except FileNotFoundError:
    st.info(
        f"Belum ada file `{DATA_INFLASI_PATH}`. Siapkan file ini dengan kolom "
        "`tanggal` (awal bulan) dan `inflasi_persen` dari rilis BPS Kota Malang "
        "untuk mengaktifkan grafik korelasi ini."
    )