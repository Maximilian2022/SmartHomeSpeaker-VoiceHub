import asyncio
from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Any, Optional
import httpx
import icalendar
import recurring_ical_events
from app.services.settings_service import settings_manager

class CalendarService:
    def __init__(self):
        self.cached_events: List[Dict[str, Any]] = []
        self.last_sync_time: Optional[datetime] = None

    async def fetch_and_parse(self, ical_url: str) -> List[Dict[str, Any]]:
        if not ical_url:
            return []
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(ical_url)
                if resp.status_code != 200:
                    return []
                cal_data = resp.content

            cal = icalendar.Calendar.from_ical(cal_data)
            now = datetime.now()
            start_range = now - timedelta(days=1)
            end_range = now + timedelta(days=2)

            events = recurring_ical_events.of(cal).between(start_range, end_range)
            parsed_list = []

            for ev in events:
                summary = str(ev.get("summary", "予定なし"))
                dtstart = ev.get("dtstart").dt
                dtend = ev.get("dtend").dt if ev.get("dtend") else dtstart

                is_all_day = isinstance(dtstart, date) and not isinstance(dtstart, datetime)

                # タイムゾーンをローカルに揃える
                if isinstance(dtstart, datetime):
                    if dtstart.tzinfo is not None:
                        dtstart = dtstart.astimezone().replace(tzinfo=None)
                else:
                    dtstart = datetime.combine(dtstart, datetime.min.time())

                if isinstance(dtend, datetime):
                    if dtend.tzinfo is not None:
                        dtend = dtend.astimezone().replace(tzinfo=None)
                else:
                    dtend = datetime.combine(dtend, datetime.max.time())

                parsed_list.append({
                    "summary": summary,
                    "start": dtstart,
                    "end": dtend,
                    "isAllDay": is_all_day,
                    "location": str(ev.get("location", ""))
                })

            parsed_list.sort(key=lambda x: x["start"])
            return parsed_list
        except Exception as e:
            print(f"[CalendarService] Fetch error: {e}")
            return []

    async def sync_all(self) -> List[Dict[str, Any]]:
        cal_conf = settings_manager.get().get("calendar", {})
        calendars = cal_conf.get("calendars", [])
        if not calendars and cal_conf.get("icalUrl"):
            calendars = [{"id": "default", "name": "メイン", "icalUrl": cal_conf["icalUrl"], "enabled": True}]

        all_events = []
        for c in calendars:
            if not c.get("enabled", True) or not c.get("icalUrl"):
                continue
            evs = await self.fetch_and_parse(c["icalUrl"])
            for e in evs:
                e["calendarId"] = c.get("id")
                e["calendarName"] = c.get("name")
            all_events.extend(evs)

        all_events.sort(key=lambda x: x["start"])
        self.cached_events = all_events
        self.last_sync_time = datetime.now()
        return all_events

    def get_current_meeting_title(self) -> Optional[str]:
        now = datetime.now()
        for ev in self.cached_events:
            if ev.get("isAllDay"):
                continue
            if ev["start"] <= now <= ev["end"]:
                return ev["summary"]
        return None

    def get_today_events(self) -> List[Dict[str, Any]]:
        today = date.today()
        return [
            ev for ev in self.cached_events
            if ev["start"].date() == today
        ]

calendar_service = CalendarService()
