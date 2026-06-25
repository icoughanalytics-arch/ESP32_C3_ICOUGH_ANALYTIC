"""
LINE Messaging API Bot Module for iCough Analytic
==================================================
จัดการ Webhook events, สร้าง Flex Message การ์ดสวยงาม,
และส่ง Push Notification ไปยังผู้ปกครองผ่าน LINE OA

การใช้งาน:
  1. เรียก configure() ตอน startup เพื่อตั้งค่า credentials
  2. เรียก handle_webhook_events() จาก /webhook/line endpoint
  3. เรียก notify_cough_alert() เมื่อตรวจพบเสียงไอ (Test Mode)
  4. เรียก run_daily_summary() จาก cron ทุกเช้า 06:00 น.
"""

import base64
import hashlib
import hmac
import datetime
from typing import List, Dict, Tuple

import requests

# ==========================================
# Configuration (set via configure())
# ==========================================
LINE_CHANNEL_SECRET = ""
LINE_CHANNEL_ACCESS_TOKEN = ""
LINE_REGISTER_CODE = "123456"
LINE_API_BASE = "https://api.line.me/v2/bot"

SUPABASE_URL = ""
SUPABASE_KEY = ""
DEFAULT_DEVICE_CODE = "ICOUGH-REAL-MOCK-001"


def configure(channel_secret: str, channel_access_token: str,
              supabase_url: str, supabase_key: str,
              register_code: str = "123456",
              default_device_code: str = "ICOUGH-REAL-MOCK-001"):
    """ตั้งค่า credentials ทั้งหมดสำหรับ LINE bot"""
    global LINE_CHANNEL_SECRET, LINE_CHANNEL_ACCESS_TOKEN, LINE_REGISTER_CODE
    global SUPABASE_URL, SUPABASE_KEY, DEFAULT_DEVICE_CODE
    LINE_CHANNEL_SECRET = channel_secret or ""
    LINE_CHANNEL_ACCESS_TOKEN = channel_access_token or ""
    LINE_REGISTER_CODE = register_code or "123456"
    SUPABASE_URL = supabase_url or ""
    SUPABASE_KEY = supabase_key or ""
    DEFAULT_DEVICE_CODE = default_device_code or "ICOUGH-REAL-MOCK-001"


def is_configured() -> bool:
    """ตรวจสอบว่า LINE bot ถูกตั้งค่าแล้วหรือยัง"""
    return bool(LINE_CHANNEL_SECRET and LINE_CHANNEL_ACCESS_TOKEN)


# ==========================================
# LINE API Core Functions
# ==========================================
def verify_signature(body: bytes, signature: str) -> bool:
    """ตรวจสอบลายเซ็น Webhook จาก LINE Platform"""
    if not LINE_CHANNEL_SECRET:
        return False
    hash_val = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        body,
        hashlib.sha256
    ).digest()
    expected = base64.b64encode(hash_val).decode("utf-8")
    return hmac.compare_digest(signature, expected)


def reply_message(reply_token: str, messages: list) -> bool:
    """ตอบกลับข้อความผ่าน Reply Token (ใช้ภายใน webhook เท่านั้น)"""
    url = f"{LINE_API_BASE}/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    data = {"replyToken": reply_token, "messages": messages[:5]}
    try:
        res = requests.post(url, headers=headers, json=data, timeout=10)
        if res.status_code != 200:
            print(f"[LINE] Reply error: {res.status_code} {res.text}")
        return res.status_code == 200
    except Exception as e:
        print(f"[LINE] Reply exception: {e}")
        return False


def push_message(user_id: str, messages: list) -> bool:
    """ส่งข้อความ Push ไปหา user โดยตรง"""
    url = f"{LINE_API_BASE}/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    data = {"to": user_id, "messages": messages[:5]}
    try:
        res = requests.post(url, headers=headers, json=data, timeout=10)
        if res.status_code != 200:
            print(f"[LINE] Push failed ({user_id[:10]}...): {res.status_code} {res.text}")
        return res.status_code == 200
    except Exception as e:
        print(f"[LINE] Push exception: {e}")
        return False


def push_to_many(user_ids: List[str], messages: list) -> int:
    """ส่ง Push Message ไปหาหลายคน, คืนจำนวนที่สำเร็จ"""
    success = 0
    for uid in user_ids:
        if push_message(uid, messages):
            success += 1
    return success


# ==========================================
# Supabase Helpers
# ==========================================
def _sb_headers():
    return {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json"
    }


def add_line_user_to_device(line_user_id: str, device_code: str = None) -> Tuple[bool, str]:
    """เพิ่ม LINE user ID เข้า array ของ device (ผ่าน RPC function)"""
    code = device_code or DEFAULT_DEVICE_CODE
    try:
        res = requests.post(
            f"{SUPABASE_URL}/rest/v1/rpc/add_line_user_id",
            headers=_sb_headers(),
            json={"p_device_code": code, "p_line_user_id": line_user_id},
            timeout=8
        )
        if res.status_code in (200, 204):
            print(f"[LINE] Registered {line_user_id[:10]}... to device {code}")
            return True, f"ลงทะเบียนสำเร็จกับอุปกรณ์ {code}"
        else:
            print(f"[LINE] RPC add error: {res.status_code} {res.text}")
            return False, "เกิดข้อผิดพลาดในการลงทะเบียน"
    except Exception as e:
        print(f"[LINE] Registration exception: {e}")
        return False, f"เกิดข้อผิดพลาด: {e}"


def remove_line_user_from_device(line_user_id: str, device_code: str = None) -> bool:
    """ลบ LINE user ID ออกจาก array ของ device"""
    code = device_code or DEFAULT_DEVICE_CODE
    try:
        res = requests.post(
            f"{SUPABASE_URL}/rest/v1/rpc/remove_line_user_id",
            headers=_sb_headers(),
            json={"p_device_code": code, "p_line_user_id": line_user_id},
            timeout=8
        )
        return res.status_code in (200, 204)
    except Exception as e:
        print(f"[LINE] Unregister exception: {e}")
        return False


def get_device_line_users(device_code: str) -> List[str]:
    """ดึง LINE user IDs ทั้งหมดของ device"""
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/device?device_code=eq.{device_code}&select=line_user_ids",
            headers=_sb_headers(),
            timeout=8
        )
        if res.status_code == 200 and len(res.json()) > 0:
            return res.json()[0].get("line_user_ids") or []
        return []
    except Exception as e:
        print(f"[LINE] Get users exception: {e}")
        return []


def get_all_devices_with_users() -> List[Dict]:
    """ดึง device ทั้งหมดที่มี LINE users ลงทะเบียนอยู่"""
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/device?select=*",
            headers=_sb_headers(),
            timeout=8
        )
        if res.status_code == 200:
            return [d for d in res.json()
                    if d.get("line_user_ids") and len(d["line_user_ids"]) > 0]
        return []
    except Exception as e:
        print(f"[LINE] Get devices exception: {e}")
        return []


def get_overnight_records(device_id: str, from_now: bool = False) -> List[Dict]:
    """ดึงประวัติเสียงไอของเมื่อคืน (ย้อนหลัง 24 ชั่วโมง จนถึง 06:00 วันนี้ หรือ ณ ปัจจุบัน)"""
    tz_th = datetime.timezone(datetime.timedelta(hours=7))
    now_th = datetime.datetime.now(tz_th)
    if from_now:
        today_6am = now_th
        yesterday_6am = today_6am - datetime.timedelta(hours=24)
    else:
        today_6am = now_th.replace(hour=6, minute=0, second=0, microsecond=0)
        yesterday_6am = today_6am - datetime.timedelta(hours=24)

    start_utc = yesterday_6am.astimezone(datetime.timezone.utc).isoformat()
    end_utc = today_6am.astimezone(datetime.timezone.utc).isoformat()

    # ใช้ params เพื่อป้องกันปัญหาเครื่องหมาย '+' ใน URL
    params = [
        ("device_id", f"eq.{device_id}"),
        ("created_at", f"gte.{start_utc}"),
        ("created_at", f"lt.{end_utc}"),
        ("order", "created_at.asc")
    ]

    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/cough_record",
            params=params,
            headers=_sb_headers(),
            timeout=10
        )
        if res.status_code != 200:
            print(f"[LINE] Get records error status {res.status_code}: {res.text}")
        return res.json() if res.status_code == 200 else []
    except Exception as e:
        print(f"[LINE] Get records exception: {e}")
        return []


# ==========================================
# Thai Helper & Constants
# ==========================================
def _thai_now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))


def _thai_time_str(dt=None):
    if dt is None:
        dt = _thai_now()
    return dt.strftime("%d/%m/%Y %H:%M น.")


DISEASE_TH = {
    "pneumonia": "ปอดบวม",
    "bronchitis": "หลอดลมอักเสบ",
    "croup": "โรคครูป",
    "normal": "ปกติ",
}

DISEASE_EMOJI = {
    "pneumonia": "🫁",
    "bronchitis": "💨",
    "croup": "🗣️",
    "normal": "💚",
}

RISK_CFG = {
    "high":     {"color": "#DC2626", "label": "🔴 อันตรายสูง"},
    "moderate": {"color": "#F59E0B", "label": "🟡 เฝ้าระวัง"},
    "low":      {"color": "#10B981", "label": "🟢 ปลอดภัย"},
}


# ==========================================
# Flex Message Builders
# ==========================================
def build_alert_flex(record_id: str, risk_level: str,
                     predictions: Dict[str, float],
                     mode: str = "normal",
                     report_url: str = "") -> dict:
    """สร้าง Flex Message การ์ดแจ้งเตือนเมื่อตรวจพบเสียงไอ"""
    rc = RISK_CFG.get(risk_level, RISK_CFG["moderate"])
    color = rc["color"]
    label = rc["label"]
    sorted_preds = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
    mode_text = "🧪 ทดสอบ" if mode == "test" else "🌙 ปกติ"
    time_str = _thai_time_str()

    pred_rows = []
    for disease, score in sorted_preds:
        th = DISEASE_TH.get(disease, disease)
        em = DISEASE_EMOJI.get(disease, "•")
        pred_rows.append({
            "type": "box", "layout": "horizontal", "margin": "sm",
            "contents": [
                {"type": "text", "text": f"{em} {th}", "size": "sm",
                 "color": "#555555", "flex": 4},
                {"type": "text", "text": f"{score*100:.1f}%", "size": "sm",
                 "color": "#111111", "align": "end", "weight": "bold", "flex": 2}
            ]
        })

    body_contents = [
        {"type": "text", "text": label, "weight": "bold",
         "size": "xl", "color": color},
        {"type": "text", "text": "ตรวจพบเสียงไอและวิเคราะห์ด้วย AI เรียบร้อย",
         "size": "xs", "color": "#999999", "margin": "sm", "wrap": True},
        {"type": "separator", "margin": "lg"},
        {"type": "text", "text": "📊 ผลการวิเคราะห์",
         "weight": "bold", "size": "sm", "margin": "lg", "color": "#333333"},
    ]
    body_contents.extend(pred_rows)
    body_contents.extend([
        {"type": "separator", "margin": "lg"},
        {
            "type": "box", "layout": "horizontal", "margin": "md",
            "contents": [
                {"type": "text", "text": "🕒 เวลา", "size": "xs",
                 "color": "#999999", "flex": 2},
                {"type": "text", "text": time_str, "size": "xs",
                 "color": "#555555", "align": "end", "flex": 5}
            ]
        }
    ])

    footer_contents = []
    if report_url:
        footer_contents.append({
            "type": "button", "style": "primary", "height": "sm",
            "action": {"type": "uri",
                       "label": "📋 ดูรายงานเต็ม + Checklist",
                       "uri": report_url},
            "color": color
        })

    bubble = {
        "type": "bubble", "size": "giga",
        "header": {
            "type": "box", "layout": "vertical",
            "contents": [{
                "type": "box", "layout": "horizontal",
                "contents": [
                    {"type": "text", "text": "🩺 iCough Alert",
                     "weight": "bold", "color": "#FFFFFF", "size": "lg", "flex": 4},
                    {"type": "text", "text": mode_text,
                     "color": "#FFFFFFAA", "size": "xxs",
                     "align": "end", "flex": 3, "gravity": "center"}
                ]
            }],
            "backgroundColor": color, "paddingAll": "16px"
        },
        "body": {
            "type": "box", "layout": "vertical",
            "contents": body_contents, "paddingAll": "16px"
        },
    }
    if footer_contents:
        bubble["footer"] = {
            "type": "box", "layout": "vertical", "spacing": "sm",
            "contents": footer_contents, "paddingAll": "12px"
        }

    return {
        "type": "flex",
        "altText": f"🩺 iCough Alert - {label}",
        "contents": bubble
    }


def build_daily_summary_flex(device_name: str, total_coughs: int,
                              highest_risk: str, top_disease: str,
                              top_score: float, period_text: str,
                              report_url: str = "") -> dict:
    """สร้าง Flex Message การ์ดสรุปรายวัน (ส่งตอนเช้า 06:00 น.)"""
    rc = RISK_CFG.get(highest_risk, RISK_CFG["low"])
    risk_label = rc["label"]
    risk_color = rc["color"]
    disease_th = DISEASE_TH.get(top_disease, top_disease)
    disease_em = DISEASE_EMOJI.get(top_disease, "•")

    if total_coughs == 0:
        count_comment = "ไม่พบเสียงไอเลยตลอดคืน 🎉"
        count_color = "#10B981"
    elif total_coughs <= 3:
        count_comment = "พบเสียงไอเล็กน้อย"
        count_color = "#F59E0B"
    else:
        count_comment = "พบเสียงไอบ่อย ควรเฝ้าระวัง"
        count_color = "#DC2626"

    body_contents = [
        {"type": "text",
         "text": f"📊 จำนวนครั้งที่ไอ: {total_coughs} ครั้ง",
         "weight": "bold", "size": "md", "color": count_color},
        {"type": "text", "text": count_comment,
         "size": "xs", "color": "#999999", "margin": "sm"},
        {"type": "separator", "margin": "lg"},
    ]

    if total_coughs > 0:
        body_contents.extend([
            {"type": "text", "text": "สรุปผลวิเคราะห์",
             "weight": "bold", "size": "sm", "margin": "lg", "color": "#333333"},
            {
                "type": "box", "layout": "horizontal", "margin": "sm",
                "contents": [
                    {"type": "text", "text": "ระดับความเสี่ยงสูงสุด",
                     "size": "xs", "color": "#999999", "flex": 4},
                    {"type": "text", "text": risk_label, "size": "xs",
                     "color": risk_color, "align": "end",
                     "weight": "bold", "flex": 4}
                ]
            },
            {
                "type": "box", "layout": "horizontal", "margin": "sm",
                "contents": [
                    {"type": "text", "text": "โรคที่พบมากที่สุด",
                     "size": "xs", "color": "#999999", "flex": 4},
                    {"type": "text",
                     "text": f"{disease_em} {disease_th} ({top_score*100:.0f}%)",
                     "size": "xs", "color": "#555555", "align": "end",
                     "weight": "bold", "flex": 5}
                ]
            },
            {"type": "separator", "margin": "lg"},
        ])

    body_contents.extend([
        {
            "type": "box", "layout": "horizontal", "margin": "md",
            "contents": [
                {"type": "text", "text": "📅 ช่วงเวลา",
                 "size": "xs", "color": "#999999", "flex": 2},
                {"type": "text", "text": period_text, "size": "xs",
                 "color": "#555555", "align": "end", "flex": 6, "wrap": True}
            ]
        },
        {
            "type": "box", "layout": "horizontal", "margin": "sm",
            "contents": [
                {"type": "text", "text": "🏷️ อุปกรณ์",
                 "size": "xs", "color": "#999999", "flex": 2},
                {"type": "text", "text": device_name or "iCough Device",
                 "size": "xs", "color": "#555555", "align": "end", "flex": 5}
            ]
        }
    ])

    footer_contents = []
    if report_url:
        footer_contents.append({
            "type": "button", "style": "primary", "height": "sm",
            "action": {"type": "uri",
                       "label": "📈 ดูสถิติและประวัติทั้งหมด",
                       "uri": report_url},
            "color": "#1E40AF"
        })

    bubble = {
        "type": "bubble", "size": "giga",
        "header": {
            "type": "box", "layout": "vertical",
            "contents": [
                {"type": "text", "text": "☀️ สรุปการไอเมื่อคืน",
                 "weight": "bold", "color": "#FFFFFF", "size": "lg"},
                {"type": "text", "text": _thai_time_str(),
                 "color": "#FFFFFFAA", "size": "xxs", "margin": "sm"}
            ],
            "backgroundColor": "#1E40AF", "paddingAll": "16px"
        },
        "body": {
            "type": "box", "layout": "vertical",
            "contents": body_contents, "paddingAll": "16px"
        },
    }
    if footer_contents:
        bubble["footer"] = {
            "type": "box", "layout": "vertical", "spacing": "sm",
            "contents": footer_contents, "paddingAll": "12px"
        }

    return {
        "type": "flex",
        "altText": f"☀️ สรุปการไอเมื่อคืน - {total_coughs} ครั้ง",
        "contents": bubble
    }


def build_welcome_flex() -> dict:
    """การ์ดต้อนรับเมื่อผู้ใช้ Follow LINE OA"""
    bubble = {
        "type": "bubble", "size": "giga",
        "header": {
            "type": "box", "layout": "vertical",
            "contents": [
                {"type": "text", "text": "🩺 iCough Analytic",
                 "weight": "bold", "color": "#FFFFFF", "size": "lg"},
                {"type": "text", "text": "ระบบวิเคราะห์เสียงไอเด็กอัจฉริยะ",
                 "color": "#FFFFFFAA", "size": "xs", "margin": "sm"}
            ],
            "backgroundColor": "#0284C7", "paddingAll": "16px"
        },
        "body": {
            "type": "box", "layout": "vertical",
            "contents": [
                {"type": "text", "text": "ยินดีต้อนรับ! 👋",
                 "weight": "bold", "size": "lg", "color": "#333333"},
                {"type": "text", "wrap": True, "size": "sm", "color": "#666666",
                 "margin": "md",
                 "text": "ระบบ iCough จะคอยวิเคราะห์เสียงไอของลูกน้อย"
                         "และแจ้งเตือนให้คุณทราบเมื่อพบความผิดปกติ"},
                {"type": "separator", "margin": "lg"},
                {"type": "text", "text": "📝 วิธีลงทะเบียน",
                 "weight": "bold", "size": "sm", "margin": "lg",
                 "color": "#333333"},
                {"type": "text", "wrap": True, "size": "xs",
                 "color": "#999999", "margin": "sm",
                 "text": "พิมพ์รหัสอุปกรณ์ที่ได้รับมา เพื่อเชื่อมต่อบัญชี LINE "
                         "กับอุปกรณ์ iCough ของคุณ"},
                {"type": "separator", "margin": "lg"},
                {"type": "text", "text": "💡 คำสั่งที่ใช้ได้",
                 "weight": "bold", "size": "sm", "margin": "lg",
                 "color": "#333333"},
                {
                    "type": "box", "layout": "vertical",
                    "margin": "sm", "spacing": "xs",
                    "contents": [
                        {"type": "text", "wrap": True, "size": "xs",
                         "color": "#666666",
                         "text": "• พิมพ์รหัสอุปกรณ์ → ลงทะเบียนรับแจ้งเตือน"},
                        {"type": "text", "wrap": True, "size": "xs",
                         "color": "#666666",
                         "text": "• พิมพ์ \"ยกเลิก\" → ยกเลิกการรับแจ้งเตือน"},
                        {"type": "text", "wrap": True, "size": "xs",
                         "color": "#666666",
                         "text": "• พิมพ์ \"สถานะ\" → ตรวจสอบสถานะ"},
                    ]
                }
            ],
            "paddingAll": "16px"
        }
    }
    return {
        "type": "flex",
        "altText": "ยินดีต้อนรับสู่ iCough Analytic 🩺",
        "contents": bubble
    }


def build_register_success_flex(device_code: str) -> dict:
    """การ์ดลงทะเบียนสำเร็จ"""
    bubble = {
        "type": "bubble",
        "header": {
            "type": "box", "layout": "vertical",
            "contents": [
                {"type": "text", "text": "✅ ลงทะเบียนสำเร็จ!",
                 "weight": "bold", "color": "#FFFFFF", "size": "md"}
            ],
            "backgroundColor": "#10B981", "paddingAll": "16px"
        },
        "body": {
            "type": "box", "layout": "vertical",
            "contents": [
                {"type": "text", "wrap": True, "size": "sm", "color": "#333333",
                 "text": f"เชื่อมต่อกับอุปกรณ์ {device_code} เรียบร้อยแล้ว"},
                {"type": "text", "wrap": True, "size": "xs",
                 "color": "#999999", "margin": "lg",
                 "text": "คุณจะได้รับแจ้งเตือนเมื่อ:"},
                {
                    "type": "box", "layout": "vertical",
                    "margin": "sm", "spacing": "xs",
                    "contents": [
                        {"type": "text", "wrap": True, "size": "xs",
                         "color": "#666666",
                         "text": "• ตรวจพบเสียงไอ (โหมดทดสอบ)"},
                        {"type": "text", "wrap": True, "size": "xs",
                         "color": "#666666",
                         "text": "• สรุปรายงานทุกเช้า 06:00 น."},
                    ]
                }
            ],
            "paddingAll": "16px"
        }
    }
    return {
        "type": "flex",
        "altText": "✅ ลงทะเบียน iCough สำเร็จ!",
        "contents": bubble
    }


def _simple_flex(text: str, alt: str) -> dict:
    """สร้าง Flex bubble ง่ายๆ สำหรับข้อความสั้น"""
    return {
        "type": "flex", "altText": alt,
        "contents": {
            "type": "bubble",
            "body": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {"type": "text", "text": text, "size": "sm",
                     "color": "#333333", "wrap": True}
                ],
                "paddingAll": "16px"
            }
        }
    }


def build_help_flex() -> dict:
    """การ์ดช่วยเหลือ / ตอบกลับอัตโนมัติ"""
    bubble = {
        "type": "bubble",
        "body": {
            "type": "box", "layout": "vertical",
            "contents": [
                {"type": "text", "text": "🩺 iCough Analytic",
                 "weight": "bold", "size": "md", "color": "#0284C7"},
                {"type": "separator", "margin": "md"},
                {"type": "text", "text": "💡 คำสั่งที่ใช้ได้:",
                 "weight": "bold", "size": "sm", "margin": "lg",
                 "color": "#333333"},
                {
                    "type": "box", "layout": "vertical",
                    "margin": "sm", "spacing": "xs",
                    "contents": [
                        {"type": "text", "wrap": True, "size": "xs",
                         "color": "#666666",
                         "text": "• พิมพ์รหัสอุปกรณ์ → ลงทะเบียน"},
                        {"type": "text", "wrap": True, "size": "xs",
                         "color": "#666666",
                         "text": "• \"ยกเลิก\" → ยกเลิกการแจ้งเตือน"},
                        {"type": "text", "wrap": True, "size": "xs",
                         "color": "#666666",
                         "text": "• \"สถานะ\" → ตรวจสอบสถานะ"},
                    ]
                }
            ],
            "paddingAll": "16px"
        }
    }
    return {
        "type": "flex",
        "altText": "iCough - คำสั่งที่ใช้ได้",
        "contents": bubble
    }


# ==========================================
# Webhook Event Handlers
# ==========================================
def handle_webhook_events(events: list):
    """ประมวลผล events ทั้งหมดจาก LINE webhook"""
    for event in events:
        etype = event.get("type")
        if etype == "follow":
            _handle_follow(event)
        elif etype == "unfollow":
            _handle_unfollow(event)
        elif etype == "message":
            _handle_message(event)


def _handle_follow(event: dict):
    reply_token = event.get("replyToken")
    user_id = event.get("source", {}).get("userId", "?")
    print(f"[LINE] New follower: {user_id[:10]}...")
    if reply_token:
        reply_message(reply_token, [build_welcome_flex()])


def _handle_unfollow(event: dict):
    user_id = event.get("source", {}).get("userId")
    if user_id:
        remove_line_user_from_device(user_id)
        print(f"[LINE] Unfollowed & unregistered: {user_id[:10]}...")


def _handle_message(event: dict):
    msg = event.get("message", {})
    if msg.get("type") != "text":
        return

    text = msg.get("text", "").strip()
    reply_token = event.get("replyToken")
    user_id = event.get("source", {}).get("userId", "")
    if not reply_token or not user_id:
        return

    # --- คำสั่งลงทะเบียน ---
    if text == LINE_REGISTER_CODE:
        ok, _ = add_line_user_to_device(user_id)
        if ok:
            reply_message(reply_token,
                          [build_register_success_flex(DEFAULT_DEVICE_CODE)])
        else:
            reply_message(reply_token,
                          [_simple_flex("❌ เกิดข้อผิดพลาดในการลงทะเบียน "
                                        "กรุณาลองใหม่อีกครั้ง",
                                        "❌ ลงทะเบียนล้มเหลว")])
        return

    # --- คำสั่งยกเลิก ---
    if text in ("ยกเลิก", "unregister", "cancel"):
        remove_line_user_from_device(user_id)
        reply_message(reply_token,
                      [_simple_flex("🔕 ยกเลิกการรับแจ้งเตือนแล้ว\n"
                                    "หากต้องการลงทะเบียนใหม่ ให้พิมพ์รหัสอุปกรณ์อีกครั้ง",
                                    "🔕 ยกเลิกแล้ว")])
        return

    # --- คำสั่งตรวจสอบสถานะ ---
    if text in ("สถานะ", "status"):
        users = get_device_line_users(DEFAULT_DEVICE_CODE)
        if user_id in users:
            reply_message(reply_token,
                          [_simple_flex(f"✅ คุณลงทะเบียนกับอุปกรณ์ "
                                        f"{DEFAULT_DEVICE_CODE} อยู่แล้ว",
                                        "✅ สถานะ: ลงทะเบียนแล้ว")])
        else:
            reply_message(reply_token,
                          [_simple_flex("❌ ยังไม่ได้ลงทะเบียน\n"
                                        "กรุณาพิมพ์รหัสอุปกรณ์เพื่อลงทะเบียน",
                                        "❌ สถานะ: ยังไม่ลงทะเบียน")])
        return

    # --- Default: ช่วยเหลือ ---
    reply_message(reply_token, [build_help_flex()])


# ==========================================
# Public Notification Functions
# ==========================================
def notify_cough_alert(device_code: str, record_id: str,
                       risk_level: str, predictions: Dict[str, float],
                       mode: str = "normal",
                       report_url: str = "") -> int:
    """ส่ง Flex Message แจ้งเตือนเสียงไอไปยังทุก LINE user ของ device
    คืนค่าจำนวนข้อความที่ส่งสำเร็จ"""
    if not is_configured():
        print("[LINE] Bot not configured, skipping notification")
        return 0

    user_ids = get_device_line_users(device_code)
    if not user_ids:
        print(f"[LINE] No registered users for device {device_code}")
        return 0

    flex = build_alert_flex(record_id, risk_level, predictions,
                            mode, report_url)
    sent = push_to_many(user_ids, [flex])
    print(f"[LINE] Alert sent to {sent}/{len(user_ids)} users "
          f"(device={device_code}, risk={risk_level})")
    return sent


def run_daily_summary(from_now: bool = False) -> Dict:
    """รันสรุปรายวัน: ดึงข้อมูลไอเมื่อคืนแล้วส่ง Flex Message ไปหาทุกคน"""
    if not is_configured():
        return {"error": "LINE bot not configured"}

    devices = get_all_devices_with_users()
    results = {"devices_processed": 0, "messages_sent": 0, "errors": []}

    now_th = _thai_now()
    if from_now:
        today_6am = now_th
        yesterday_6am = today_6am - datetime.timedelta(hours=24)
    else:
        today_6am = now_th.replace(hour=6, minute=0, second=0, microsecond=0)
        yesterday_6am = today_6am - datetime.timedelta(hours=24)
        
    period_text = (f"{yesterday_6am.strftime('%d/%m %H:%M')} - "
                   f"{today_6am.strftime('%d/%m %H:%M น.')}")

    risk_priority = {"high": 3, "moderate": 2, "low": 1}

    for device in devices:
        dev_id = device["id"]
        dev_name = device.get("device_name", "iCough Device")
        dev_code = device.get("device_code", "")
        user_ids = device.get("line_user_ids", [])
        if not user_ids:
            continue

        try:
            records = get_overnight_records(dev_id, from_now=from_now)
            total = len(records)
            highest_risk = "low"
            top_disease = "normal"
            top_score = 0.0

            for r in records:
                rl = r.get("risk_level", "low")
                if risk_priority.get(rl, 0) > risk_priority.get(highest_risk, 0):
                    highest_risk = rl
                for disease in ("pneumonia", "bronchitis", "croup", "normal"):
                    sc = float(r.get(f"{disease}_score", 0) or 0)
                    if sc > top_score:
                        top_score = sc
                        top_disease = disease

            flex = build_daily_summary_flex(
                device_name=dev_name,
                total_coughs=total,
                highest_risk=highest_risk,
                top_disease=top_disease,
                top_score=top_score,
                period_text=period_text,
                report_url=f"https://i-cough.vercel.app/result?device={dev_code}"
            )

            sent = push_to_many(user_ids, [flex])
            results["devices_processed"] += 1
            results["messages_sent"] += sent
            print(f"[LINE] Daily summary for {dev_code}: "
                  f"{total} coughs, sent to {sent}/{len(user_ids)} users")

        except Exception as e:
            err = f"Error device {dev_code}: {e}"
            print(f"[LINE] {err}")
            results["errors"].append(err)

    return results
