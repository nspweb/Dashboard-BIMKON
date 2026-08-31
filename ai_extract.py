from __future__ import annotations

import json
from typing import Optional

import streamlit as st
from google import genai
from google.genai import types

from config import JENIS_TEMUAN_OPTIONS, PRIORITAS_OPTIONS

# "gemini-flash-latest" otomatis mengikuti versi Flash terbaru yang stabil,
# jadi tidak perlu diubah manual tiap kali Google merilis model baru.
MODEL = "gemini-flash-latest"

SYSTEM_PROMPT = f"""Anda adalah asisten analis untuk program Bimbingan Konsultansi (BimKon)
Peningkatan Produktivitas di Industri, yang dijalankan oleh BPVP.

Tugas Anda: membaca catatan lapangan mentah dan tidak terstruktur dari kunjungan ke
sebuah objek industri (bisa berbahasa informal / campur / poin-poin acak), lalu memecahnya
menjadi beberapa TEMUAN terpisah dan menuliskannya ulang secara formal mengikuti format baku
tabel pemetaan permasalahan.

Setiap temuan punya field berikut:
- aspek: nama area/topik temuan tsb, singkat, format Judul (contoh: "Manajemen Persediaan & Pengadaan Produk",
  "Sistem Reservasi & Layanan Pelanggan", "Sumber Daya Manusia & Operasional"). Buat sendiri sesuai konteks jika belum ada contohnya.
- jenis_temuan: salah satu dari {JENIS_TEMUAN_OPTIONS} -- "Permasalahan" jika ini adalah kelemahan/isu yang
  perlu diperbaiki, "Kekuatan" jika ini adalah hal positif yang sudah berjalan baik, "Peluang" jika ini
  adalah potensi yang belum tergarap, "Ancaman" jika ini risiko eksternal.
- kondisi_temuan: deskripsi FAKTUAL kondisi di lapangan, ditulis ulang secara formal, jelas, dan lengkap
  (1-3 kalimat), berdasarkan catatan mentah -- JANGAN menambah fakta yang tidak disebutkan.
- permasalahan: inti masalah/isu yang timbul dari kondisi tsb. Isi dengan tanda "—" jika jenis_temuan
  bukan "Permasalahan".
- dampak: akibat/dampak dari kondisi atau masalah tsb terhadap operasional/bisnis.
- rekomendasi: rekomendasi tindak lanjut yang konkret dan actionable.
- prioritas: salah satu dari {PRIORITAS_OPTIONS} -- nilai seberapa mendesak/penting temuan ini
  ditindaklanjuti (Tinggi untuk isu yang berisiko hukum/keselamatan/finansial besar atau berulang
  signifikan, Sedang untuk isu operasional menengah, Rendah untuk kekuatan/peluang yang sifatnya
  mempertahankan atau nice-to-have).

Aturan penting:
1. Setiap poin/kalimat berbeda dalam catatan mentah yang membahas hal yang tidak berkaitan langsung
   sebaiknya jadi 1 baris temuan terpisah -- jangan digabung jadi satu baris besar.
   Tapi jika beberapa kalimat jelas membahas satu kondisi yang sama, gabungkan jadi satu temuan.
2. Gunakan bahasa Indonesia formal/laporan, BUKAN bahasa gaul dari catatan mentah.
3. Jangan mengarang angka, nama, atau fakta yang tidak ada di catatan mentah.
4. Keluarkan HANYA JSON sesuai skema yang diberikan, tanpa teks lain.
"""

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "temuan": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "aspek": {"type": "STRING"},
                    "jenis_temuan": {
                        "type": "STRING",
                        "enum": JENIS_TEMUAN_OPTIONS,
                    },
                    "kondisi_temuan": {"type": "STRING"},
                    "permasalahan": {"type": "STRING"},
                    "dampak": {"type": "STRING"},
                    "rekomendasi": {"type": "STRING"},
                    "prioritas": {
                        "type": "STRING",
                        "enum": PRIORITAS_OPTIONS,
                    },
                },
                "required": [
                    "aspek",
                    "jenis_temuan",
                    "kondisi_temuan",
                    "permasalahan",
                    "dampak",
                    "rekomendasi",
                    "prioritas",
                ],
            },
        }
    },
    "required": ["temuan"],
}


def get_api_key() -> Optional[str]:
    if "gemini_api_key" in st.secrets:
        return st.secrets["gemini_api_key"]
    return st.session_state.get("gemini_api_key_input")


def extract_findings(
    raw_notes: str,
    objek_name: str,
    konteks_industri: str = "",
    existing_aspek: Optional[list[str]] = None,
) -> list[dict]:
    """Panggil Gemini untuk mengekstrak temuan terstruktur dari catatan mentah."""
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "Gemini API key belum diisi. Masukkan lewat sidebar atau "
            "st.secrets['gemini_api_key']."
        )

    client = genai.Client(api_key=api_key)

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

    response = client.models.generate_content(
        model=MODEL,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
            temperature=0.2,
        ),
    )

    if not response.text:
        raise RuntimeError(
            "Model tidak mengembalikan hasil (kemungkinan diblokir oleh safety filter)."
        )

    data = json.loads(response.text)
    temuan = data.get("temuan", [])

    result = []
    for t in temuan:
        result.append(
            {
                "ASPEK": t.get("aspek", ""),
                "JENIS_TEMUAN": t.get("jenis_temuan", ""),
                "KONDISI_TEMUAN": t.get("kondisi_temuan", ""),
                "PERMASALAHAN": t.get("permasalahan", ""),
                "DAMPAK": t.get("dampak", ""),
                "REKOMENDASI": t.get("rekomendasi", ""),
                "PRIORITAS": t.get("prioritas", ""),
            }
        )
    return result
