"""config.py — ค่าตั้งต้นทั้งหมดของ dashboard

แก้ค่าการทำงานที่ไฟล์นี้ที่เดียว ส่วนความลับ (token) อยู่ใน
.streamlit/secrets.toml ซึ่งไม่ถูก push ขึ้น GitHub
"""
from dataclasses import dataclass
import streamlit as st


def _secret(key: str, default: str = "") -> str:
    """อ่าน secrets แบบไม่พังถ้ายังไม่มีไฟล์ secrets.toml

    ⚠️ st.secrets.get() จะ raise ถ้าไม่มีไฟล์เลย ไม่ได้คืน default
    จึงต้องห่อ try/except ไว้
    """
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


# ---------- Firebase ----------
# ⚠️⚠️ ต้องตรงกับ FIREBASE_HOST และ DB_PATH ในเฟิร์มแวร์เป๊ะ ๆ
#      บั๊กตัวหลักของเวอร์ชันเดิมคือสองฝั่งชี้คนละฐานข้อมูลกัน
FIREBASE_DOMAIN = _secret("FIREBASE_DOMAIN", "")
FIREBASE_TOKEN  = _secret("FIREBASE_TOKEN", "")
DB_PATH   = "History3F"
META_PATH = "History3F_meta"

# ---------- การดึงข้อมูล ----------
BUFFER_SIZE   = 900    # เก็บใน RAM ฝั่ง client (18 วินาที @ 50 Hz)
FIRST_FETCH   = 600    # ดึงครั้งแรกเท่านี้ ครั้งต่อไปดึงเฉพาะของใหม่
INCR_LIMIT    = 400    # เพดานต่อรอบ incremental
REFRESH_MS    = 1500
HTTP_TIMEOUT  = 3.0

# ---------- DSP ----------
NPERSEG    = 512    # ⚠️ ต้องคงที่! ถ้าแปรผันตามจำนวนจุด df จะแกว่ง
                    #    ทำให้แอมพลิจูดกระโดดเองโดยโครงสร้างไม่ได้เปลี่ยน
NOMINAL_FS = 50.0
SEARCH_LO  = 2.0
SEARCH_HI  = 24.0   # จะถูกบังคับไม่ให้เกิน 0.45*fs อีกชั้นใน dsp.py
TRACK_HALF = 2.0    # หน้าต่างตามล่าพีค ±Hz
COH_MIN    = 0.75   # coherence ต่ำกว่านี้ = ข้อมูลไม่น่าเชื่อ

# ---------- ตรรกะสถานะ ----------
HISTORY_SIZE = 7    # median filter กี่จุด
MIN_CONSEC   = 3    # ต้องเข้าเงื่อนไขติดกันกี่รอบถึงเปลี่ยนสถานะ
SINE_SHARP   = 40   # sharpness เกินนี้ = น่าจะเป็น sine ความถี่เดียว

FLOOR_NAMES = ["ชั้น 1 (ฐานราก)", "ชั้น 2 (กลาง)", "ชั้น 3 (ยอด)"]
N_FLOORS = 3


@dataclass
class Thresholds:
    """เกณฑ์เปลี่ยนสถานะ — ผู้ใช้ปรับได้จาก sidebar"""
    g2y: float = 90.0   # 🟢→🟡 เมื่อ Health ต่ำกว่า
    y2r: float = 70.0   # 🟡→🔴
    y2g: float = 94.0   # 🟡→🟢 (ขาฟื้น)
    r2y: float = 75.0   # 🔴→🟡 (ขาฟื้น)
    rms_min: float = 0.010   # RMS ขั้นต่ำที่ถือว่ามีแรงกระตุ้นพอ
