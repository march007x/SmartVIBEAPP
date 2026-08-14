"""ui/floors.py — การ์ดแสดงผลรายชั้น"""
import streamlit as st

import config as C
from core.damage import next_status
from services import telegram


def _render_status(status, pct, cnt):
    if status == "green":
        st.success(f"🟢 ปกติ: {pct:.1f}%")
    elif status == "yellow":
        st.warning(f"🟡 เฝ้าระวัง: {pct:.1f}%  [{cnt}/{C.MIN_CONSEC}]")
    else:
        st.error(f"🔴 อันตราย: {pct:.1f}%  [{cnt}/{C.MIN_CONSEC}]")


def render(result, ss, th):
    amp_max = max([f.amp for f in result.floors if f.amp], default=0.0)
    cols = st.columns(C.N_FLOORS)

    for i, fr in enumerate(result.floors):
        with cols[i]:
            st.subheader(C.FLOOR_NAMES[i])
            st.markdown(f"RMS: `{fr.rms:.4f}`")

            if fr.fn is None:
                st.warning("ไม่มีข้อมูลช่องนี้ / หาพีคไม่เจอ")
                continue

            # ---- แอมพลิจูด ----
            if fr.amp is not None:
                ratio = (f"× {fr.amp/result.floors[0].amp:.2f} ของชั้น 1"
                         if i > 0 and result.floors[0].amp else None)
                st.metric("แอมพลิจูดการแกว่ง", f"{fr.amp:.4f}",
                          delta=ratio, delta_color="off")
                if amp_max > 0:
                    st.progress(min(int(fr.amp / amp_max * 100), 100))

            # ---- ตัวชี้วัดหลักตามโหมด ----
            if result.active_mode == "fn":
                base = ss.get(f"base_fn{i}")
                st.metric("ความถี่ธรรมชาติ fn", f"{fr.fn:.2f} Hz",
                          delta=(f"{fr.fn - base:+.2f} Hz" if base else None))
                if fr.f_peak and abs(fr.df_shift) > 0.01:
                    st.caption(f"พีคที่ตามล่าได้ {fr.f_peak:.2f} Hz "
                               f"(เลื่อน {fr.df_shift:+.2f} Hz)")
            else:
                if i == 0:
                    st.metric("บทบาท", "จุดอ้างอิง (ฐาน)")
                    st.caption("โหมดไซน์วัดการเปลี่ยนแปลง 'ระหว่างชั้น' — ชั้นฐานเป็นตัวหาร")
                    continue
                T_now = result.T21 if i == 1 else result.T32
                T_base = ss.get("base_T21") if i == 1 else ss.get("base_T32")
                coh = result.coh21 if i == 1 else result.coh32
                label = "T ชั้น2/ชั้น1" if i == 1 else "T ชั้น3/ชั้น2"
                if T_now is not None:
                    st.metric(f"Transmissibility ({label})", f"{T_now:.3f}",
                              delta=(f"{T_now - T_base:+.3f}" if T_base else None))
                    st.caption(f"coherence {coh:.2f}")
                else:
                    st.warning(f"coherence ต่ำ ({coh:.2f}) — ข้อมูลยังเชื่อไม่ได้")

            # ---- Health + สถานะ ----
            pct = fr.health
            if pct is None:
                st.info("กด 🔒 ล็อก Baseline ขณะโครงสร้างสมบูรณ์")
                continue

            st.metric("Health เทียบ Baseline", f"{pct:.1f}%")
            st.progress(min(int(pct), 100))

            if result.excitation_ok:
                new_s, cnt, direction = next_status(
                    ss[f"status{i}"], ss[f"consec{i}"], ss[f"consec_dir{i}"], pct, th)
                ss[f"status{i}"], ss[f"consec{i}"], ss[f"consec_dir{i}"] = new_s, cnt, direction
                # 🔔 แจ้งเตือนเฉพาะตอนตัดสินสถานะจริง ไม่ใช่ตอนพักการตัดสิน
                telegram.on_status_change(i, new_s, pct)
                telegram.on_health_sample(i, pct)
            else:
                st.info("⏸️ แรงกระตุ้นต่ำ — คงสถานะเดิม")
                new_s, cnt = ss[f"status{i}"], ss[f"consec{i}"]

            _render_status(new_s, pct, cnt)
