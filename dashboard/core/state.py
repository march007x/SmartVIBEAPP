"""core/state.py — จัดการ st.session_state ที่เดียว

รวมไว้ที่นี่เพื่อไม่ให้ setdefault กระจายเต็มโค้ด
"""
import config as C


def init(ss):
    ss.setdefault("last_uptime", 0)
    ss.setdefault("stuck_counter", 0)
    ss.setdefault("base_T21", None)
    ss.setdefault("base_T32", None)
    ss.setdefault("T_hist21", [])
    ss.setdefault("T_hist32", [])
    ss.setdefault("health_log", [])
    for i in range(C.N_FLOORS):
        ss.setdefault(f"base_fn{i}", None)
        ss.setdefault(f"fn_hist{i}", [])
        ss.setdefault(f"amp_hist{i}", [])
        ss.setdefault(f"status{i}", "green")
        ss.setdefault(f"consec{i}", 0)
        ss.setdefault(f"consec_dir{i}", None)


def lock_baseline(ss, result) -> bool:
    """ล็อกค่าอ้างอิงตอนโครงสร้างสมบูรณ์ คืน False ถ้าเงื่อนไขไม่พร้อม"""
    if not result.excitation_ok:
        return False
    if any(f.fn is None for f in result.floors):
        return False
    if result.active_mode == "sine" and result.T21 is None:
        return False

    for i, fr in enumerate(result.floors):
        ss[f"base_fn{i}"] = fr.fn
        ss[f"status{i}"] = "green"
        ss[f"consec{i}"] = 0
        ss[f"consec_dir{i}"] = None
    ss["base_T21"], ss["base_T32"] = result.T21, result.T32
    return True


def reset_all(ss):
    for i in range(C.N_FLOORS):
        ss[f"base_fn{i}"] = None
        ss[f"fn_hist{i}"] = []
        ss[f"amp_hist{i}"] = []
        ss[f"status{i}"] = "green"
        ss[f"consec{i}"] = 0
        ss[f"consec_dir{i}"] = None
    ss["base_T21"] = ss["base_T32"] = None
    ss["T_hist21"], ss["T_hist32"] = [], []
    ss["health_log"] = []


def update_stuck(ss, df) -> int:
    """นับว่าข้อมูลไม่ขยับมากี่รอบแล้ว"""
    cur = df["uptime_ms"].iloc[-1]
    if cur == ss.last_uptime:
        ss.stuck_counter += 1
    else:
        ss.stuck_counter, ss.last_uptime = 0, cur
    return ss.stuck_counter
