"""ui/debug.py — แผงข้อมูลสำหรับไล่จับปัญหา"""
import time
import numpy as np
import streamlit as st

import config as C


def render(result, df, t0, client, stuck):
    with st.expander("ℹ️ debug"):
        dts = np.diff(df["uptime_ms"].values.astype(float))
        good = dts[(dts >= 5) & (dts <= 150)]
        st.write(f"URL: `{C.FIREBASE_DOMAIN}/{C.DB_PATH}.json`")
        st.write(f"จุดในบัฟเฟอร์: {len(df)} | last_key: `{client.last_key}` | stuck: {stuck}")
        st.write(f"dt median: {np.median(good):.1f} ms | fs: {result.fs:.2f} Hz "
                 f"| Nyquist: {result.fs/2:.1f} Hz")
        st.write(f"sine_detected: {result.sine_detected} | โหมดที่ใช้: {result.active_mode} "
                 f"| sharpness: {[f'{f.sharpness:.0f}' for f in result.floors]}")
        st.write(f"fn: {[f'{f.fn:.2f}' if f.fn else '—' for f in result.floors]} | "
                 f"amp: {[f'{f.amp:.4f}' if f.amp else '—' for f in result.floors]}")
        st.write(f"T21: {result.T21} (coh {result.coh21:.2f}) | "
                 f"T32: {result.T32} (coh {result.coh32:.2f})")
        st.write(f"⏱️ เวลาประมวลผล: {(time.perf_counter()-t0)*1000:.0f} ms "
                 f"(ต้องน้อยกว่า {C.REFRESH_MS} ms)")
