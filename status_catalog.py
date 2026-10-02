from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StandardStatus:
    id: str
    en: str
    th: str

    def dropdown_label(self, language: str) -> str:
        return self.text_for(language)

    def text_for(self, language: str) -> str:
        return self.th if str(language).upper() == "TH" else self.en


STANDARD_STATUSES = (
    StandardStatus("available", "Available", "พร้อมคุย"),
    StandardStatus("busy", "Busy", "ไม่ว่าง"),
    StandardStatus("away", "Away for a while", "ไม่อยู่ชั่วคราว"),
    StandardStatus("be_right_back", "Be right back", "เดี๋ยวกลับมา"),
    StandardStatus("do_not_disturb", "Please do not disturb", "กรุณาอย่ารบกวน"),
    StandardStatus("at_work", "At work", "กำลังทำงาน"),
    StandardStatus("in_a_meeting", "In a meeting", "กำลังประชุม"),
    StandardStatus("studying", "Studying", "กำลังเรียน"),
    StandardStatus("taking_a_break", "Taking a short break", "พักสักครู่"),
    StandardStatus("resting", "Taking some rest", "กำลังพักผ่อน"),
    StandardStatus("online_to_chat", "Online and happy to chat", "ออนไลน์และยินดีคุย"),
    StandardStatus("meet_people", "Here to meet new friends", "มาทำความรู้จักเพื่อนใหม่"),
    StandardStatus("listening", "Just listening", "เข้ามาฟัง"),
    StandardStatus("watching_room", "Keeping an eye on the room", "กำลังติดตามห้อง"),
    StandardStatus("enjoying_music", "Enjoying the music", "กำลังฟังเพลง"),
    StandardStatus("gaming", "Gaming right now", "กำลังเล่นเกม"),
    StandardStatus("creating", "Working on something creative", "กำลังทำงานสร้างสรรค์"),
    StandardStatus("reading", "Reading a book", "กำลังอ่านหนังสือ"),
    StandardStatus("watching_movie", "Watching a movie", "กำลังดูภาพยนตร์"),
    StandardStatus("coffee_break", "Taking a coffee break", "กำลังพักดื่มกาแฟ"),
    StandardStatus("lunch", "Taking a lunch break", "กำลังพักทานอาหารกลางวัน"),
    StandardStatus("dinner", "Having dinner", "กำลังทานอาหารเย็น"),
    StandardStatus("walk", "Out for a walk", "ออกไปเดินเล่น"),
    StandardStatus("traveling", "Traveling at the moment", "กำลังเดินทาง"),
    StandardStatus("on_the_road", "On the road", "อยู่ระหว่างเดินทาง"),
    StandardStatus("at_home", "Relaxing at home", "พักผ่อนอยู่ที่บ้าน"),
    StandardStatus("back_soon", "I'll be back soon", "จะกลับมาเร็ว ๆ นี้"),
    StandardStatus("offline_briefly", "Offline for a little while", "ออฟไลน์สักครู่"),
    StandardStatus("quiet_day", "Having a quiet day", "วันนี้ขอพักเงียบ ๆ"),
    StandardStatus("positive_day", "Feeling positive today", "วันนี้รู้สึกดี"),
    StandardStatus("kind_words", "Let's keep it kind", "มาพูดคุยกันด้วยความใจดี"),
    StandardStatus("respectful_chat", "Let's be respectful", "ขอให้สุภาพต่อกัน"),
    StandardStatus("good_vibes", "Good vibes only", "ส่งต่อพลังบวก"),
    StandardStatus("friendly_chat", "Let's keep the chat friendly", "มาคุยกันอย่างเป็นมิตร"),
    StandardStatus("welcome", "Welcome everyone", "ยินดีต้อนรับทุกคน"),
    StandardStatus("thanks_visit", "Thanks for stopping by", "ขอบคุณที่แวะมา"),
    StandardStatus("nice_to_meet", "Nice to meet you", "ยินดีที่ได้รู้จัก"),
    StandardStatus("hello", "Hello there", "สวัสดี"),
    StandardStatus("hope_well", "Hope you're doing well", "หวังว่าคุณสบายดี"),
    StandardStatus("great_day", "Wishing you a great day", "ขอให้วันนี้เป็นวันที่ดี"),
    StandardStatus("good_evening", "Wishing you a lovely evening", "ขอให้มีค่ำคืนที่ดี"),
    StandardStatus("happy_weekend", "Have a happy weekend", "สุขสันต์วันหยุดสุดสัปดาห์"),
    StandardStatus("kindness", "Let's share some kindness", "มาร่วมส่งต่อความใจดี"),
    StandardStatus("open_to_chat", "Open to a friendly conversation", "ยินดีพูดคุยอย่างเป็นมิตร"),
    StandardStatus("listening_first", "Mostly listening today", "วันนี้ขอฟังเป็นหลัก"),
    StandardStatus("recharging", "Relaxing and recharging", "กำลังพักผ่อนเติมพลัง"),
    StandardStatus("personal_time", "Taking a little personal time", "ขอเวลาส่วนตัวสักครู่"),
    StandardStatus("short_break", "On a short break", "กำลังพักสั้น ๆ"),
    StandardStatus("good_company", "Thanks for the good company", "ขอบคุณที่มาร่วมพูดคุย"),
    StandardStatus("peaceful_day", "Wishing everyone a peaceful day", "ขอให้ทุกคนมีวันที่สงบสดใส"),
)

DEFAULT_STANDARD_STATUS_ID = "available"
STANDARD_STATUS_BY_ID = {status.id: status for status in STANDARD_STATUSES}
STANDARD_STATUS_IDS = frozenset(STANDARD_STATUS_BY_ID)

STATUS_CATEGORY_IDS = {
    "availability": frozenset({
        "available", "busy", "away", "be_right_back", "do_not_disturb",
        "taking_a_break", "resting", "back_soon", "offline_briefly",
        "quiet_day", "recharging", "personal_time", "short_break",
    }),
    "work_study": frozenset({
        "at_work", "in_a_meeting", "studying", "creating", "reading",
    }),
    "activities": frozenset({
        "listening", "watching_room", "enjoying_music", "gaming", "watching_movie",
        "coffee_break", "lunch", "dinner", "walk", "traveling", "on_the_road",
        "at_home", "listening_first",
    }),
    "social": frozenset({
        "online_to_chat", "meet_people", "positive_day", "kind_words", "respectful_chat",
        "good_vibes", "friendly_chat", "welcome", "thanks_visit", "nice_to_meet", "hello",
        "hope_well", "great_day", "good_evening", "happy_weekend", "kindness",
        "open_to_chat", "good_company", "peaceful_day",
    }),
}

STATUS_CATEGORY_LABELS = {
    "all": {"EN": "All statuses", "TH": "สถานะทั้งหมด"},
    "favorites": {"EN": "Favorites", "TH": "รายการโปรด"},
    "availability": {"EN": "Availability", "TH": "ความพร้อม"},
    "work_study": {"EN": "Work & study", "TH": "งานและการเรียน"},
    "activities": {"EN": "Activities", "TH": "กิจกรรม"},
    "social": {"EN": "Social", "TH": "สังคม"},
}

STANDARD_STATUS_CATEGORY_BY_ID = {
    status_id: category
    for category, status_ids in STATUS_CATEGORY_IDS.items()
    for status_id in status_ids
}


def get_standard_status(status_id: str) -> StandardStatus | None:
    return STANDARD_STATUS_BY_ID.get(str(status_id or ""))


def find_standard_status_by_label(label: str, language: str) -> StandardStatus | None:
    text = str(label or "")
    return next((status for status in STANDARD_STATUSES if status.text_for(language) == text), None)


def standard_status_dropdown_values(language: str) -> list[str]:
    return [status.dropdown_label(language) for status in STANDARD_STATUSES]


def standard_status_category_values(language: str) -> list[str]:
    lang = "TH" if str(language).upper() == "TH" else "EN"
    return [labels[lang] for labels in STATUS_CATEGORY_LABELS.values()]


def category_key_from_label(label: str, language: str) -> str:
    lang = "TH" if str(language).upper() == "TH" else "EN"
    return next((key for key, labels in STATUS_CATEGORY_LABELS.items() if labels[lang] == label), "all")


def filter_standard_statuses(
    search: str = "",
    category: str = "all",
    favorite_ids=(),
) -> list[StandardStatus]:
    query = str(search or "").strip().casefold()
    favorites = {str(status_id) for status_id in favorite_ids}
    category_ids = STATUS_CATEGORY_IDS.get(category)
    statuses = STANDARD_STATUSES
    if category == "favorites":
        statuses = tuple(status for status in statuses if status.id in favorites)
    elif category_ids is not None:
        statuses = tuple(status for status in statuses if status.id in category_ids)
    if query:
        statuses = tuple(
            status for status in statuses
            if query in status.id.casefold() or query in status.en.casefold() or query in status.th.casefold()
        )
    return list(statuses)
