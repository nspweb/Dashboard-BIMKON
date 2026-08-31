"""
Konfigurasi & konstanta untuk aplikasi Dashboard Pemetaan Permasalahan BIMKON.
"""

# ID default spreadsheet (bisa dioverride lewat st.secrets["spreadsheet_id"])
DEFAULT_SPREADSHEET_ID = "1bD2DxdwOKqE3hUOHy_9e_2M4h77O1MQjiW3x0hZKAt4"

# Nama sheet yang TIDAK dianggap sebagai "objek kunjungan"
NON_OBJECT_SHEETS = {"Dashboard", "dashboard", "Rekap", "Template"}

# Urutan kolom baku pada setiap sheet objek
COLUMNS = [
    "NO",
    "ASPEK",
    "JENIS_TEMUAN",
    "KONDISI_TEMUAN",
    "PERMASALAHAN",
    "DAMPAK",
    "REKOMENDASI",
    "PRIORITAS",
]

# Header persis seperti yang tertulis di spreadsheet (dipakai saat menulis sheet baru)
RAW_HEADER = [
    "NO",
    "ASPEK",
    "JENIS\nTEMUAN",
    "KONDISI / TEMUAN",
    "PERMASALAHAN",
    "DAMPAK",
    "REKOMENDASI",
    "PRIORITAS",
]

JENIS_TEMUAN_OPTIONS = ["Permasalahan", "Kekuatan", "Peluang", "Ancaman"]
PRIORITAS_OPTIONS = ["Tinggi", "Sedang", "Rendah"]

PRIORITAS_ORDER = {"Tinggi": 0, "Sedang": 1, "Rendah": 2}
PRIORITAS_COLOR = {"Tinggi": "#e05252", "Sedang": "#e0a852", "Rendah": "#52a3e0"}
JENIS_COLOR = {
    "Permasalahan": "#e05252",
    "Kekuatan": "#4caf7d",
    "Peluang": "#4c8ee0",
    "Ancaman": "#a352d6",
}
