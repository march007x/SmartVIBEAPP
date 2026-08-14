"""ui/charts.py — กราฟแอมพลิจูดและสเปกตรัม"""
import pandas as pd
import streamlit as st

import config as C


def amplitude_bar(result):
    amps = [f.amp for f in result.floors]
    if not all(a is not None for a in amps):
        return
    st.subheader("แอมพลิจูดการแกว่งแต่ละชั้น")
    df = pd.DataFrame({"แอมพลิจูด": amps}, index=["ชั้น 1", "ชั้น 2", "ชั้น 3"])
    try:
        st.bar_chart(df, y_label="แอมพลิจูด (RMS ณ ความถี่อ้างอิง)", horizontal=True)
    except TypeError:            # Streamlit เวอร์ชันเก่ายังไม่มี y_label
        st.bar_chart(df)
    st.caption("💡 ปกติชั้นบนแกว่งแรงกว่าชั้นล่าง (พฤติกรรมโหมดที่ 1) — "
               "แอมพลิจูดใช้ดูพฤติกรรม ส่วนการตัดสินความเสียหายใช้ Health % "
               "เพราะแอมพลิจูดเดี่ยว ๆ เปลี่ยนตามระดับเสียงลำโพงได้")


def spectrum(result):
    if result.freqs is None or any(f.psd is None for f in result.floors):
        return
    st.subheader("กราฟสเปกตรัม (PSD) แยกตามชั้น")
    valid = result.freqs >= 0.5
    df = pd.DataFrame(
        {C.FLOOR_NAMES[i]: result.floors[i].psd[valid] for i in range(C.N_FLOORS)},
        index=result.freqs[valid])
    nyq = result.fs * 0.5
    st.line_chart(df[df.index <= nyq], x_label="Frequency (Hz)", y_label="PSD (g²/Hz)")
    st.caption(f"แกน x แสดงถึง Nyquist = {nyq:.1f} Hz — เหนือกว่านี้อ่านไม่ได้")
