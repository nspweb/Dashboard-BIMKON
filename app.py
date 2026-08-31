import datetime as dt

import pandas as pd
import plotly.express as px
import streamlit as st

import ai_extract
import sheets_client as sc
from config import (
    JENIS_COLOR,
    JENIS_TEMUAN_OPTIONS,
    PRIORITAS_COLOR,
    PRIORITAS_OPTIONS,
    PRIORITAS_ORDER,
)

st.set_page_config(
    page_title="Dashboard Pemetaan Permasalahan BIMKON",
    page_icon="📋",
    layout="wide",
)

# ----------------------------------------------------------------------------
# Sidebar: koneksi & kontrol global
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Koneksi")

    if "gemini_api_key_input" not in st.session_state:
        st.session_state["gemini_api_key_input"] = ""

    if "gemini_api_key" not in st.secrets:
        st.session_state["gemini_api_key_input"] = st.text_input(
            "Gemini API Key (gratis, untuk fitur AI)",
            type="password",
            value=st.session_state["gemini_api_key_input"],
            help="Ambil gratis di aistudio.google.com/apikey (tanpa kartu kredit). "
            "Hanya disimpan di memori sesi browser ini, tidak ditulis ke disk. "
            "Untuk deployment permanen, isi lewat Streamlit Secrets sebagai "
            "gemini_api_key.",
        )
    else:
        st.success("Gemini API key: terhubung lewat Secrets ✅")

    if st.button("🔄 Refresh data dari Google Sheets", use_container_width=True):
        sc.refresh_data()
        st.rerun()

    st.caption(
        "Data dashboard ini dibaca langsung dari Google Sheets lewat Google Sheets API "
        "setiap beberapa menit (cache 5 menit), tidak disimpan permanen di server."
    )

# ----------------------------------------------------------------------------
# Load data
# ----------------------------------------------------------------------------
try:
    df, object_names, loaded_at = sc.load_all_data()
except sc.SheetsError as e:
    st.error(str(e))
    st.stop()

with st.sidebar:
    st.caption(f"🕒 Data terakhir diambil: {loaded_at.strftime('%H:%M:%S')}")
    st.caption(f"📁 {len(object_names)} objek kunjungan terdeteksi")

st.title("📋 Dashboard Pemetaan Permasalahan BIMKON")
st.caption(
    "Bimbingan Konsultansi (BimKon) Peningkatan Produktivitas di Industri — data live dari Google Sheets"
)

tab_labels = ["📊 Dashboard"] + [f"🏢 {name}" for name in object_names] + ["➕ Input Temuan Baru (AI)"]
tabs = st.tabs(tab_labels)

# ----------------------------------------------------------------------------
# TAB: Dashboard
# ----------------------------------------------------------------------------
with tabs[0]:
    if df.empty:
        st.info("Belum ada data temuan di spreadsheet ini.")
    else:
        total_temuan = len(df)
        total_permasalahan = (df["JENIS_TEMUAN"] == "Permasalahan").sum()
        prioritas_tinggi = (df["PRIORITAS"] == "Tinggi").sum()
        jumlah_objek = df["OBJEK"].nunique()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Temuan", total_temuan)
        c2.metric("Permasalahan", int(total_permasalahan))
        c3.metric("Prioritas Tinggi", int(prioritas_tinggi))
        c4.metric("Objek Dipetakan", int(jumlah_objek))

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Ringkasan per Prioritas")
            prio_count = (
                df["PRIORITAS"]
                .value_counts()
                .reindex(PRIORITAS_OPTIONS)
                .fillna(0)
                .reset_index()
            )
            prio_count.columns = ["PRIORITAS", "JUMLAH"]
            fig = px.bar(
                prio_count,
                x="PRIORITAS",
                y="JUMLAH",
                color="PRIORITAS",
                color_discrete_map=PRIORITAS_COLOR,
                text="JUMLAH",
            )
            fig.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Ringkasan per Jenis Temuan")
            jenis_count = df["JENIS_TEMUAN"].value_counts().reset_index()
            jenis_count.columns = ["JENIS_TEMUAN", "JUMLAH"]
            fig2 = px.pie(
                jenis_count,
                names="JENIS_TEMUAN",
                values="JUMLAH",
                color="JENIS_TEMUAN",
                color_discrete_map=JENIS_COLOR,
                hole=0.4,
            )
            fig2.update_layout(height=350)
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Ringkasan per Objek Kunjungan x Prioritas")
        cross = (
            df.groupby(["OBJEK", "PRIORITAS"])
            .size()
            .reset_index(name="JUMLAH")
        )
        fig3 = px.bar(
            cross,
            x="OBJEK",
            y="JUMLAH",
            color="PRIORITAS",
            color_discrete_map=PRIORITAS_COLOR,
            category_orders={"PRIORITAS": PRIORITAS_OPTIONS},
            barmode="stack",
            text="JUMLAH",
        )
        fig3.update_layout(height=400)
        st.plotly_chart(fig3, use_container_width=True)

        st.subheader("Ringkasan per Aspek")
        aspek_count = (
            df.groupby(["ASPEK", "JENIS_TEMUAN"]).size().reset_index(name="JUMLAH")
        )
        fig4 = px.bar(
            aspek_count,
            y="ASPEK",
            x="JUMLAH",
            color="JENIS_TEMUAN",
            color_discrete_map=JENIS_COLOR,
            orientation="h",
        )
        fig4.update_layout(height=max(300, 30 * aspek_count["ASPEK"].nunique()))
        st.plotly_chart(fig4, use_container_width=True)

        st.divider()
        st.subheader("🔍 Cari & Filter Semua Temuan")
        fc1, fc2, fc3, fc4 = st.columns(4)
        f_objek = fc1.multiselect("Objek", sorted(df["OBJEK"].unique()))
        f_jenis = fc2.multiselect("Jenis Temuan", JENIS_TEMUAN_OPTIONS)
        f_prio = fc3.multiselect("Prioritas", PRIORITAS_OPTIONS)
        f_search = fc4.text_input("Cari kata kunci")

        filtered = df.copy()
        if f_objek:
            filtered = filtered[filtered["OBJEK"].isin(f_objek)]
        if f_jenis:
            filtered = filtered[filtered["JENIS_TEMUAN"].isin(f_jenis)]
        if f_prio:
            filtered = filtered[filtered["PRIORITAS"].isin(f_prio)]
        if f_search:
            mask = (
                filtered.drop(columns=["NO"])
                .apply(lambda col: col.astype(str).str.contains(f_search, case=False, na=False))
                .any(axis=1)
            )
            filtered = filtered[mask]

        st.dataframe(
            filtered[
                ["OBJEK", "NO", "ASPEK", "JENIS_TEMUAN", "KONDISI_TEMUAN", "PRIORITAS"]
            ],
            use_container_width=True,
            hide_index=True,
        )

# ----------------------------------------------------------------------------
# TAB: per objek
# ----------------------------------------------------------------------------
def render_object_tab(objek: str, sub_df: pd.DataFrame):
    if sub_df.empty:
        st.info("Belum ada temuan untuk objek ini.")
        return

    sub_df = sub_df.sort_values(
        by="PRIORITAS", key=lambda s: s.map(PRIORITAS_ORDER)
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Temuan", len(sub_df))
    c2.metric("Permasalahan", int((sub_df["JENIS_TEMUAN"] == "Permasalahan").sum()))
    c3.metric("Prioritas Tinggi", int((sub_df["PRIORITAS"] == "Tinggi").sum()))

    for _, row in sub_df.iterrows():
        prio = row["PRIORITAS"] or "-"
        badge_color = PRIORITAS_COLOR.get(prio, "#999")
        with st.expander(
            f"#{int(row['NO']) if pd.notna(row['NO']) else '?'} · {row['ASPEK']} "
            f"· {row['JENIS_TEMUAN']} · Prioritas: {prio}"
        ):
            st.markdown(
                f"<span style='background:{badge_color};color:white;padding:2px 8px;"
                f"border-radius:4px;font-size:12px'>{prio.upper()}</span>",
                unsafe_allow_html=True,
            )
            st.markdown(f"**Kondisi / Temuan:** {row['KONDISI_TEMUAN']}")
            st.markdown(f"**Permasalahan:** {row['PERMASALAHAN']}")
            st.markdown(f"**Dampak:** {row['DAMPAK']}")
            st.markdown(f"**Rekomendasi:** {row['REKOMENDASI']}")


for i, objek in enumerate(object_names, start=1):
    with tabs[i]:
        render_object_tab(objek, df[df["OBJEK"] == objek])

# ----------------------------------------------------------------------------
# TAB: Input Temuan Baru (AI)
# ----------------------------------------------------------------------------
with tabs[-1]:
    st.subheader("➕ Tambah Temuan Baru dari Catatan Kunjungan")
    st.caption(
        "Paste catatan lapangan mentah (boleh berantakan / poin-poin acak / bahasa "
        "sehari-hari). AI akan memecahnya jadi temuan terstruktur mengikuti format "
        "tabel yang sudah ada, lalu Anda bisa review/edit sebelum disimpan ke Google Sheets."
    )

    colA, colB = st.columns([2, 1])
    with colA:
        pilihan_objek = ["(Objek baru)"] + object_names
        pilih = st.selectbox("Objek kunjungan", pilihan_objek)
        if pilih == "(Objek baru)":
            objek_name = st.text_input("Nama objek kunjungan baru", "")
            konteks = st.text_input(
                "Konteks / jenis industri (opsional, jadi subjudul sheet baru)",
                "",
                placeholder="mis. Jasa Kecantikan & Perawatan (Salon) — BPVP Kendari",
            )
        else:
            objek_name = pilih
            konteks = ""

    with colB:
        st.markdown("&nbsp;")
        st.info(f"Aspek yang sudah ada:\n\n" + ("\n".join(f"- {a}" for a in sorted(df['ASPEK'].dropna().unique())) if not df.empty else "belum ada"))

    raw_notes = st.text_area(
        "Catatan lapangan mentah",
        height=280,
        placeholder="Tempel catatan kunjungan di sini...",
    )

    if st.button("🤖 Proses dengan AI", type="primary", disabled=not raw_notes.strip() or not objek_name.strip()):
        try:
            with st.spinner("Menganalisis catatan dengan Gemini..."):
                hasil = ai_extract.extract_findings(
                    raw_notes=raw_notes,
                    objek_name=objek_name,
                    konteks_industri=konteks,
                    existing_aspek=list(df["ASPEK"].dropna().unique()) if not df.empty else [],
                )
            st.session_state["draft_temuan"] = pd.DataFrame(hasil)
            st.session_state["draft_objek_name"] = objek_name
            st.session_state["draft_konteks"] = konteks
            st.success(f"AI menghasilkan {len(hasil)} temuan. Silakan review di bawah sebelum disimpan.")
        except Exception as e:
            st.error(f"Gagal memproses dengan AI: {e}")

    if "draft_temuan" in st.session_state and not st.session_state["draft_temuan"].empty:
        st.divider()
        st.markdown(f"#### Review Temuan — {st.session_state.get('draft_objek_name', '')}")
        st.caption("Silakan koreksi teks / kategori sebelum menyimpan ke Google Sheets.")

        edited = st.data_editor(
            st.session_state["draft_temuan"],
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "JENIS_TEMUAN": st.column_config.SelectboxColumn(
                    "JENIS_TEMUAN", options=JENIS_TEMUAN_OPTIONS
                ),
                "PRIORITAS": st.column_config.SelectboxColumn(
                    "PRIORITAS", options=PRIORITAS_OPTIONS
                ),
                "ASPEK": st.column_config.TextColumn("ASPEK", width="medium"),
                "KONDISI_TEMUAN": st.column_config.TextColumn("KONDISI_TEMUAN", width="large"),
                "PERMASALAHAN": st.column_config.TextColumn("PERMASALAHAN", width="large"),
                "DAMPAK": st.column_config.TextColumn("DAMPAK", width="large"),
                "REKOMENDASI": st.column_config.TextColumn("REKOMENDASI", width="large"),
            },
            key="editor_draft",
        )

        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("💾 Simpan ke Google Sheets", type="primary"):
                try:
                    with st.spinner("Menulis ke Google Sheets..."):
                        n = sc.append_findings(
                            objek_name=st.session_state["draft_objek_name"],
                            rows=edited.to_dict(orient="records"),
                            subtitle=st.session_state.get("draft_konteks", ""),
                        )
                    st.success(f"{n} temuan berhasil disimpan ke sheet '{st.session_state['draft_objek_name']}'.")
                    del st.session_state["draft_temuan"]
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menyimpan: {e}")
        with c2:
            if st.button("🗑️ Batalkan draft"):
                del st.session_state["draft_temuan"]
                st.rerun()
