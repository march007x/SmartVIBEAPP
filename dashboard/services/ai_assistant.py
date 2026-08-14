"""services/ai_assistant.py — ผู้ช่วย AI วิเคราะห์สถานะโครงสร้าง

รองรับ 4 ผู้ให้บริการผ่าน OpenAI-compatible API ตัวเดียวกัน
สลับได้จาก dropdown

⚠️ กฎเหล็ก: ห้ามเรียก LLM ทุกรอบ auto-refresh (1.5 วิ)
   ไม่งั้นโควตาหมดใน 6 นาที → โมดูลนี้เป็น on-demand + cache เท่านั้น
"""
import hashlib
import json
import requests
import streamlit as st

PROVIDERS = {
    "Groq (เร็วสุด, แนะนำ)": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key": "GROQ_API_KEY",
        "model": "llama-3.3-70b-versatile",
        "note": "ฟรี ~14k req/วัน · latency ต่ำมาก · เหมาะกับ Streamlit Cloud",
    },
    "OpenRouter (ฟรี)": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key": "OPENROUTER_API_KEY",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "note": "โมเดลฟรีหลายตัว แต่โควตาน้อย ~50 req/วัน",
    },
    "Ollama (เครื่องตัวเอง)": {
        "url": "http://localhost:11434/v1/chat/completions",
        "key": None,
        "model": "qwen2.5:7b",
        "note": "ไม่จำกัดโควตา ออฟไลน์ได้ · ต้อง RAM ≥ 8GB · Cloud ใช้ไม่ได้",
    },
}

SYSTEM_PROMPT = """คุณคือวิศวกรผู้เชี่ยวชาญ Structural Health Monitoring
กำลังช่วยครูฟิสิกส์มัธยมปลายวิเคราะห์อาคารจำลอง 3 ชั้น ติด accelerometer
MPU-6050 ชั้นละ 1 ตัว

หลักการที่ต้องยึด:
- fn ∝ sqrt(k/m) → stiffness k ลด ทำให้ fn ลด
- Health = (fn/fn₀)² x 100 = % ของ stiffness ที่เหลืออยู่
- ถ้ากระตุ้นด้วย sine ความถี่เดียวคงที่ แล้วแอมพลิจูดลดลง แปลว่าพีค
  เรโซแนนซ์เลื่อนหนีจากความถี่ลำโพง ไม่ได้แปลว่าแข็งแรงขึ้น และบอก
  ทิศทางไม่ได้ (คลายน็อตหรือขันแน่นก็ทำให้ลดลงทั้งคู่)
- Transmissibility เปลี่ยน = ความเสียหายอยู่ที่จุดต่อระหว่างชั้นนั้น
- coherence ต่ำ = ข้อมูลไม่น่าเชื่อ อย่าเพิ่งสรุป

ตอบภาษาไทย กระชับ ไม่เกิน 5 บรรทัด ใช้ภาษาที่นักเรียน ม.ปลาย เข้าใจ
ถ้าข้อมูลไม่พอ ให้บอกตรง ๆ ว่าต้องเก็บอะไรเพิ่ม"""


def _key(name: str) -> str:
    try:
        return st.secrets.get(name, "")
    except Exception:
        return ""


def chat(provider: str, messages: list, temperature: float = 0.3) -> str:
    cfg = PROVIDERS[provider]
    headers = {"Content-Type": "application/json"}
    if cfg["key"]:
        api_key = _key(cfg["key"])
        if not api_key:
            return f"⚠️ ยังไม่ได้ตั้ง {cfg['key']} ใน .streamlit/secrets.toml"
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        r = requests.post(cfg["url"], headers=headers, timeout=30,
                          json={"model": cfg["model"], "messages": messages,
                                "temperature": temperature, "max_tokens": 700})
    except requests.RequestException as e:
        if "localhost" in cfg["url"]:
            return "⚠️ ต่อ Ollama ไม่ได้ — สั่ง `ollama serve` และ `ollama pull qwen2.5:7b` ก่อน"
        return f"⚠️ เชื่อมต่อไม่สำเร็จ: {e}"

    msgs = {401: "⚠️ API key ไม่ถูกต้อง (401)",
            403: "⚠️ 403 — ยังไม่ได้เปิด API ในโปรเจกต์ หรือ region ไม่รองรับ",
            429: "⚠️ โควตาหมดชั่วคราว (429) รอสักครู่ หรือสลับผู้ให้บริการ"}
    if r.status_code in msgs:
        return msgs[r.status_code]
    if r.status_code != 200:
        return f"⚠️ HTTP {r.status_code}: {r.text[:200]}"

    try:
        return r.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError):
        return "⚠️ อ่านคำตอบไม่ได้ — รูปแบบ response ผิดคาด"


def snapshot(result, ss) -> str:
    """สรุปสถานะปัจจุบันเป็น JSON สำหรับป้อนให้ AI"""
    return json.dumps({
        "โหมด": result.active_mode,
        "fs_Hz": round(result.fs, 2),
        "f_drive_Hz": round(result.f_drive, 3) if result.f_drive else None,
        "fn_ปัจจุบัน": [round(f.fn, 3) if f.fn else None for f in result.floors],
        "fn_baseline": [ss.get(f"base_fn{i}") for i in range(3)],
        "health_pct": [round(f.health, 1) if f.health else None for f in result.floors],
        "สถานะ": [ss.get(f"status{i}") for i in range(3)],
        "RMS": [round(f.rms, 5) for f in result.floors],
        "แอมพลิจูด": [round(f.amp, 5) if f.amp else None for f in result.floors],
        "T21": round(result.T21, 4) if result.T21 else None,
        "T32": round(result.T32, 4) if result.T32 else None,
        "coherence": [round(result.coh21, 2), round(result.coh32, 2)],
        "แรงกระตุ้นพอ": result.excitation_ok,
    }, ensure_ascii=False, indent=1)


@st.cache_data(ttl=300, show_spinner=False)
def analyze_cached(provider: str, snap_hash: str, snap: str) -> str:
    """cache ตาม hash ของ snapshot — สถานะไม่เปลี่ยน = ไม่เรียก API ซ้ำ"""
    return chat(provider, [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content":
            f"ข้อมูลล่าสุด:\n{snap}\n\nสรุปให้: "
            "(1) ตอนนี้โครงสร้างเป็นอย่างไร "
            "(2) ชั้นไหนน่าห่วงที่สุดและเพราะอะไร "
            "(3) ควรทำอะไรต่อ"}])


def hash_of(snap: str) -> str:
    return hashlib.md5(snap.encode()).hexdigest()[:12]


def analyze_trend(history: list, provider: str) -> str:
    """คาดเดาแนวโน้มจากข้อมูลย้อนหลัง (เก็บทุก ~30 วิ ไม่ใช่ทุก refresh)"""
    if len(history) < 6:
        return "ข้อมูลย้อนหลังยังน้อยเกินไป เก็บอีกสักพักแล้วลองใหม่"
    return chat(provider, [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content":
            f"ข้อมูลย้อนหลัง:\n{json.dumps(history[-40:], ensure_ascii=False)}\n\n"
            "Health มีแนวโน้มลดลงต่อเนื่องไหม ถ้าลด ประเมินว่าอีกกี่นาทีจะแตะ "
            "เกณฑ์อันตราย และบอกระดับความมั่นใจด้วย"}], temperature=0.2)
