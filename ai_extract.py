from __future__ import annotations

import json
import re
from typing import Optional

import streamlit as st
from groq import Groq

from config import JENIS_TEMUAN_OPTIONS, PRIORITAS_OPTIONS

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = f"""Anda adalah asisten analis untuk program Bimbingan Konsultansi (BimKon)
Peningkatan Produktivitas di Industri, yang dijalankan oleh BPVP.

Tugas Anda: membaca catatan lapangan mentah dan tidak terstruktur dari kunjungan ke
sebuah objek industri (bisa berbahasa informal / campur / poin-poin acak), lalu memecahnya
menjadi beberapa TEMUAN terpisah dan menuliskannya ulang secara formal mengikuti format baku
tabel pemetaan permasalahan.

Setiap temuan punya field berikut:
- aspek: nama area/topik temuan tsb, singkat, format Judul (contoh: "Manajemen Persediaan & Pengadaan Produk",
  "Sistem Reservasi & Layanan Pelanggan", "Sumber Daya Manusia & Operasional"). Buat sendiri sesuai konteks jika belum ada contohnya.
- jenis_temuan: SALAH SATU PERSIS dari daftar ini: {JENIS_TEMUAN_OPTIONS} -- "Permasalahan" jika ini adalah
  kelemahan/isu yang perlu diperbaiki, "Kekuatan" jika ini adalah hal positif yang sudah berjalan baik,
  "Peluang" jika ini adalah potensi yang belum tergarap, "Ancaman" jika ini risiko eksternal.
- kondisi_temuan: deskripsi FAKTUAL kondisi di lapangan, ditulis ulang secara formal, jelas, dan lengkap
  (1-3 kalimat), berdasarkan catatan mentah -- JANGAN menambah fakta yang tidak disebutkan.
- permasalahan: inti masalah/isu yang timbul dari kondisi tsb. Isi dengan tanda "—" jika jenis_temuan
  bukan "Permasalahan".
- dampak: akibat/dampak dari kondisi atau masalah tsb terhadap operasional/bisnis.
- rekomendasi: rekomendasi tindak lanjut yang konkret dan actionable.
- prioritas: SALAH SATU PERSIS dari daftar ini: {PRIORITAS_OPTIONS} -- nilai seberapa mendesak/penting
  temuan ini ditindaklanjuti (Tinggi untuk isu yang berisiko hukum/keselamatan/finansial besar atau
  berulang signifikan, Sedang untuk isu operasional menengah, Rendah untuk kekuatan/peluang yang
  sifatnya mempertahankan atau nice-to-have).

Aturan penting:
1. Setiap poin/kalimat berbeda dalam catatan mentah yang membahas hal yang tidak berkaitan langsung
   sebaiknya jadi 1 baris temuan terpisah -- jangan digabung jadi satu baris besar.
   Tapi jika beberapa kalimat jelas membahas satu kondisi yang sama, gabungkan jadi satu temuan.
2. Gunakan bahasa Indonesia formal/laporan, BUKAN bahasa gaul dari catatan mentah.
3. Jangan mengarang angka, nama, atau fakta yang tidak ada di catatan mentah.
4. WAJIB balas HANYA dengan JSON valid, tanpa teks lain, tanpa markdown code fence, dengan struktur
   PERSIS seperti ini:
{{"temuan": [{{"aspek": "...", "jenis_temuan": "...", "kondisi_temuan": "...", "permasalahan": "...",
"dampak": "...", "rekomendasi": "...", "prioritas": "..."}}]}}
"""


def get_api_key() -> Optional[str]:
    if "groq_api_key" in st.secrets:
        return st.secrets["groq_api_key"]
    return st.session_state.get("groq_api_key_input")


def _extract_json(text: str) -> dict:
    """Groq kadang membungkus JSON dengan teks/markdown fence -- ambil blok {...} terluar."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise RuntimeError("Model tidak mengembalikan JSON yang bisa dibaca.")
    return json.loads(match.group(0))


def extract_findings(
    raw_notes: str,
    objek_name: str,
    konteks_industri: str = "",
    existing_aspek: Optional[list[str]] = None,
) -> list[dict]:
    """Panggil Groq (Llama) untuk mengekstrak temuan terstruktur dari catatan mentah."""
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "Groq API key belum diisi. Masukkan lewat sidebar atau "
            "st.secrets['groq_api_key']."
        )

    client = Groq(api_key=api_key)

    context_lines = [f"Objek kunjungan: {objek_name}"]
    if konteks_industri:
        context_lines.append(f"Jenis industri / konteks: {konteks_industri}")
    if existing_aspek:
        context_lines.append(
            "Aspek yang sudah pernah dipakai di objek lain (pakai ulang jika cocok, "
            "jangan dipaksakan): " + ", ".join(sorted(set(existing_aspek)))
        )
    context_lines.append("\nCatatan lapangan mentah:\n" + raw_notes.strip())
    user_message = "\n".join(context_lines)

    completion = client.chat.completions.create(
        model=MODEL,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    raw_text = completion.choices[0].message.content
    if not raw_text:
        raise RuntimeError("Model tidak mengembalikan hasil.")

    data = _extract_json(raw_text)
    temuan = data.get("temuan", [])

    result = []
    for t in temuan:
        jenis = t.get("jenis_temuan", "")
        if jenis not in JENIS_TEMUAN_OPTIONS:
            jenis = "Permasalahan"
        prioritas = t.get("prioritas", "")
        if prioritas not in PRIORITAS_OPTIONS:
            prioritas = "Sedang"
        result.append(
            {
                "ASPEK": t.get("aspek", ""),
                "JENIS_TEMUAN": jenis,
                "KONDISI_TEMUAN": t.get("kondisi_temuan", ""),
                "PERMASALAHAN": t.get("permasalahan", ""),
                "DAMPAK": t.get("dampak", ""),
                "REKOMENDASI": t.get("rekomendasi", ""),
                "PRIORITAS": prioritas,
            }
        )
    return result