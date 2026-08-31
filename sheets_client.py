"""
Semua interaksi ke Google Sheets lewat Google Sheets API (gspread).
Tidak ada data yang disimpan ke disk lokal -- semua dibaca/ditulis langsung
ke spreadsheet, dan hanya di-cache sementara di memori Streamlit.
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

from config import (
    COLUMNS,
    DEFAULT_SPREADSHEET_ID,
    NON_OBJECT_SHEETS,
    RAW_HEADER,
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


class SheetsError(RuntimeError):
    pass


@st.cache_resource(show_spinner=False)
def get_client() -> gspread.Client:
    """Buat client gspread terautentikasi dari service account di st.secrets."""
    if "gcp_service_account" not in st.secrets:
        raise SheetsError(
            "Kredensial Google belum ada di Secrets. Tambahkan blok "
            "[gcp_service_account] pada .streamlit/secrets.toml (lihat README)."
        )
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=SCOPES
    )
    return gspread.authorize(creds)


def get_spreadsheet_id() -> str:
    return st.secrets.get("spreadsheet_id", DEFAULT_SPREADSHEET_ID)


def get_spreadsheet() -> gspread.Spreadsheet:
    client = get_client()
    try:
        return client.open_by_key(get_spreadsheet_id())
    except gspread.exceptions.APIError as e:
        raise SheetsError(
            "Gagal membuka spreadsheet. Pastikan Spreadsheet ID benar dan "
            "sudah di-share (Editor) ke email service account. Detail: "
            f"{e}"
        ) from e


def _find_header_row(values: list[list[str]]) -> Optional[int]:
    """Cari index (0-based) baris yang kolom pertamanya == 'NO'."""
    for i, row in enumerate(values):
        if row and row[0].strip().upper() == "NO":
            return i
    return None


def _parse_object_sheet(ws: gspread.Worksheet) -> pd.DataFrame:
    """Parse satu sheet objek kunjungan jadi DataFrame rapi."""
    values = ws.get_all_values()
    header_idx = _find_header_row(values)
    if header_idx is None:
        return pd.DataFrame(columns=COLUMNS)

    rows = []
    for row in values[header_idx + 1 :]:
        row = row + [""] * (8 - len(row))  # pad biar aman
        no_val = row[0].strip()
        if no_val == "":
            break  # berhenti di baris kosong pertama setelah data
        rows.append(row[:8])

    df = pd.DataFrame(rows, columns=COLUMNS)
    if not df.empty:
        df["NO"] = pd.to_numeric(df["NO"], errors="coerce")
        df["OBJEK"] = ws.title
    return df


@st.cache_data(ttl=300, show_spinner="Mengambil data dari Google Sheets...")
def load_all_data(_cache_key: str = "") -> tuple[pd.DataFrame, list[str], dt.datetime]:
    """
    Ambil & gabungkan semua sheet objek kunjungan (semua sheet KECUALI
    yang ada di NON_OBJECT_SHEETS) jadi satu DataFrame gabungan.
    `_cache_key` dipakai untuk memaksa refresh (ubah nilainya -> cache miss).
    """
    sh = get_spreadsheet()
    all_ws = sh.worksheets()

    object_sheets = [ws for ws in all_ws if ws.title not in NON_OBJECT_SHEETS]

    frames = []
    for ws in object_sheets:
        df = _parse_object_sheet(ws)
        if not df.empty:
            frames.append(df)

    if frames:
        combined = pd.concat(frames, ignore_index=True)
    else:
        combined = pd.DataFrame(columns=COLUMNS + ["OBJEK"])

    object_names = [ws.title for ws in object_sheets]
    return combined, object_names, dt.datetime.now()


def refresh_data():
    """Bersihkan cache supaya load berikutnya ambil data terbaru dari API."""
    load_all_data.clear()


def object_exists(objek_name: str) -> bool:
    sh = get_spreadsheet()
    return objek_name in [ws.title for ws in sh.worksheets()]


def create_object_sheet(objek_name: str, subtitle: str = "") -> gspread.Worksheet:
    """Buat tab baru untuk objek kunjungan baru, format sama seperti sheet lain."""
    sh = get_spreadsheet()
    ws = sh.add_worksheet(title=objek_name, rows=100, cols=8)
    title_row = [
        f"PEMETAAN PERMASALAHAN BIMBINGAN KONSULTANSI PENINGKATAN PRODUKTIVITAS "
        f"PADA {objek_name.upper()}"
    ]
    rows_to_write = [title_row, [subtitle] if subtitle else [""], [""], RAW_HEADER]
    ws.update(range_name="A1", values=rows_to_write)
    ws.format("A1:A2", {"textFormat": {"bold": True}})
    ws.format("A4:H4", {"textFormat": {"bold": True}})
    return ws


def append_findings(objek_name: str, rows: list[dict], subtitle: str = "") -> int:
    """
    Tambahkan baris temuan baru ke sheet objek (bikin sheet baru dulu kalau
    belum ada). `rows` = list of dict dengan key sesuai COLUMNS (tanpa NO,
    NO akan di-generate otomatis melanjutkan nomor terakhir).
    Return: jumlah baris yang berhasil ditambahkan.
    """
    sh = get_spreadsheet()
    if objek_name in [ws.title for ws in sh.worksheets()]:
        ws = sh.worksheet(objek_name)
    else:
        ws = create_object_sheet(objek_name, subtitle)

    values = ws.get_all_values()
    header_idx = _find_header_row(values)
    if header_idx is None:
        # sheet ada tapi belum ada header -> tulis header dulu
        ws.update(range_name="A4", values=[RAW_HEADER])
        header_idx = 3
        values = ws.get_all_values()

    # cari NO terakhir yang terisi
    last_no = 0
    data_row_count = 0
    for row in values[header_idx + 1 :]:
        if row and row[0].strip() != "":
            try:
                last_no = max(last_no, int(float(row[0])))
            except ValueError:
                pass
            data_row_count += 1
        else:
            break

    start_row = header_idx + 1 + data_row_count + 1  # 1-indexed row utk gspread

    out_rows = []
    for i, r in enumerate(rows, start=1):
        out_rows.append(
            [
                last_no + i,
                r.get("ASPEK", ""),
                r.get("JENIS_TEMUAN", ""),
                r.get("KONDISI_TEMUAN", ""),
                r.get("PERMASALAHAN", ""),
                r.get("DAMPAK", ""),
                r.get("REKOMENDASI", ""),
                r.get("PRIORITAS", ""),
            ]
        )

    ws.update(range_name=f"A{start_row}", values=out_rows)
    refresh_data()
    return len(out_rows)
