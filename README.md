# Dashboard Pemetaan Permasalahan BIMKON

Aplikasi Streamlit yang membaca & menulis data **langsung dari Google Sheets**
lewat Google Sheets API (tidak ada data yang disimpan permanen di lokal/server),
dilengkapi fitur input temuan baru berbasis AI memakai **Google Gemini API**
(gratis, tanpa kartu kredit).

## Fitur

- **Dashboard** — KPI, grafik prioritas, jenis temuan, dan rekap per objek, dihitung live dari data sheet.
- **Tab per objek kunjungan** — detail semua temuan, otomatis muncul untuk setiap tab baru di spreadsheet.
- **➕ Input Temuan Baru (AI)** — paste catatan lapangan mentah, AI (Gemini) otomatis mengklasifikasikannya
  jadi baris-baris terstruktur (Aspek, Jenis Temuan, Kondisi, Permasalahan, Dampak, Rekomendasi, Prioritas),
  bisa direview/diedit, lalu disimpan langsung ke Google Sheets.

## Kenapa Gemini (dan bukan yang berbayar)?

Google AI Studio menyediakan API key **gratis tanpa kartu kredit** dengan kuota harian yang
lebih dari cukup untuk pemakaian seperti ini (beberapa kali proses per hari saat kunjungan
industri baru). Model yang dipakai (`gemini-flash-latest`) otomatis mengikuti versi Flash
terbaru yang stabil dari Google, jadi tidak perlu update kode setiap ada rilis model baru.

## 1. Setup Google Sheets API (wajib, untuk baca & tulis data)

1. Buka [Google Cloud Console](https://console.cloud.google.com/) → buat project baru (atau pakai yang sudah ada).
2. Aktifkan **Google Sheets API** dan **Google Drive API** (menu "APIs & Services" → "Enable APIs").
3. Buat **Service Account**: "APIs & Services" → "Credentials" → "Create Credentials" → "Service Account".
4. Setelah service account dibuat, buka tab **Keys** → "Add Key" → "Create new key" → pilih **JSON**. File JSON akan terdownload.
5. Buka spreadsheet BIMKON Anda di Google Sheets → klik **Share** → tambahkan **email service account**
   (formatnya `xxxx@nama-project.iam.gserviceaccount.com`, ada di dalam file JSON) dengan akses **Editor**
   (harus Editor, bukan Viewer, karena aplikasi ini juga menulis data baru).
6. Salin isi file JSON tadi ke `.streamlit/secrets.toml` pada bagian `[gcp_service_account]`
   (lihat `.streamlit/secrets.toml.example`).

## 2. Setup Gemini API Key (gratis, untuk fitur AI)

1. Buka [aistudio.google.com/apikey](https://aistudio.google.com/apikey), login dengan akun Google,
   klik **"Create API key"**. Tidak perlu kartu kredit / tidak ada tagihan selama pakai kuota gratis.
2. Isi ke `secrets.toml` sebagai `gemini_api_key = "AIza..."`, **atau** biarkan kosong dan
   masukkan manual lewat kolom di sidebar tiap kali membuka aplikasi (tidak disimpan ke disk).
3. Kuota gratis (per Agustus 2026) untuk model Flash biasanya ada di kisaran ratusan hingga
   ribuan request/hari — jauh lebih dari cukup untuk pemakaian internal seperti ini. Kalau suatu
   saat kena limit, tunggu reset harian atau cek kuota terbaru di halaman rate limits Google AI.

## 3. Jalankan secara lokal

```bash
pip install -r requirements.txt
mkdir -p .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit .streamlit/secrets.toml, isi kredensial Anda
streamlit run app.py
```

## 4. Deploy ke Streamlit Community Cloud

1. Push folder ini (**tanpa** `secrets.toml` yang sudah terisi — hanya file `.example`) ke repo GitHub.
2. Buka [share.streamlit.io](https://share.streamlit.io/) → "New app" → pilih repo & `app.py`.
3. Di menu **Settings → Secrets** pada dashboard Streamlit Cloud, paste isi `secrets.toml` yang sudah
   Anda isi lengkap (spreadsheet_id, gemini_api_key, dan blok `[gcp_service_account]`).
4. Deploy. Aplikasi akan langsung membaca data live dari spreadsheet Anda.

## Struktur data yang diharapkan di spreadsheet

- Setiap **tab/sheet** (selain "Dashboard") dianggap sebagai satu **objek kunjungan**
  (misalnya "Salon Prima", "Hotel Qubah 9", dst).
- Di dalam tiap sheet objek, aplikasi mencari baris dengan kolom pertama bertuliskan `NO`
  sebagai baris header, lalu membaca kolom: `NO, ASPEK, JENIS TEMUAN, KONDISI/TEMUAN,
  PERMASALAHAN, DAMPAK, REKOMENDASI, PRIORITAS`.
- Kalau Anda menambah tab baru untuk objek kunjungan baru secara manual di Google Sheets
  (atau lewat fitur "Input Temuan Baru (AI)" di aplikasi ini), tab tersebut otomatis
  terdeteksi dan muncul sebagai tab baru di dashboard — tidak perlu ubah kode.

## Catatan keamanan

- Jangan commit `secrets.toml` (yang sudah terisi kredensial asli) ke Git manapun. File
  `.gitignore` sederhana disarankan berisi `.streamlit/secrets.toml`.
- Service account hanya perlu akses ke spreadsheet ini saja (jangan share ke seluruh Drive).
