import asyncio
from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Any, Optional, Callable
import httpx
import icalendar
import recurring_ical_events
from app.services.settings_service import settings_manager
from app.core.logger import get_logger

log = get_logger("Calendar")

class CalendarService:
    def __init__(self):
        self.cached_events: List[Dict[str, Any]] = []
        self.last_sync_time: Optional[datetime] = None
        self._speech_executor: Optional[Callable] = None
        self._reminded_event_ids: set = set()
        self._last_summary_date: Optional[date] = None
        self._scheduler_task: Optional[asyncio.Task] = None

    def set_speech_executor(self, executor: Callable):
        self._speech_executor = executor

    def start_background_scheduler(self):
        if self._scheduler_task is None or self._scheduler_task.done():
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def fetch_and_parse(self, ical_url: str) -> List[Dict[str, Any]]:
        if not ical_url:
            return []
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(ical_url)
                if resp.status_code != 200:
                    log.warning(f"Failed to fetch iCal: HTTP {resp.status_code} for {ical_url[:40]}...")
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
            log.error(f"Calendar fetch/parse error: {e}", exc_info=True)
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
        log.info(f"Calendar sync complete: {len(all_events)} event(s) cached.")
        return all_events

    def get_current_meeting_titles(self, include_all_day: bool = False) -> List[str]:
        now = datetime.now()
        titles = []
        for ev in self.cached_events:
            if ev.get("isAllDay") and not include_all_day:
                continue
            if ev["start"] <= now <= ev["end"]:
                titles.append(ev["summary"])
        return titles

    def get_current_meeting_title(self) -> Optional[str]:
        dnd_conf = settings_manager.get().get("dnd", {})
        include_all_day = bool(dnd_conf.get("calendarIncludeAllDay", False))
        titles = self.get_current_meeting_titles(include_all_day=include_all_day)
        return titles[0] if titles else None

    def get_today_events(self) -> List[Dict[str, Any]]:
        today = date.today()
        res = []
        for ev in self.cached_events:
            s_date = ev["start"].date()
            e_date = ev["end"].date()
            if ev.get("isAllDay"):
                # 終日予定: start <= today < end (end が start と同じなら start == today)
                if s_date <= today < e_date or (s_date == e_date and s_date == today):
                    res.append(ev)
            else:
                # 時間指定予定: 今日を跨いでいるか、今日開始・終了
                if s_date <= today <= e_date:
                    res.append(ev)
        return res

    # ================= 朝の予定まとめサマリー発話 =================
    async def speak_daily_summary(self, config_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self._speech_executor:
            log.warning("Speech executor not set for calendar summary.")
            return {"success": False, "error": "Speech executor not registered"}

        cal_conf = config_override or settings_manager.get().get("calendar", {})
        await self.sync_all()
        today_events = self.get_today_events()

        from app.services.disaster_service import disaster_service
        weather_info = None
        disaster_conf = settings_manager.get().get("disaster", {})
        if disaster_conf.get("enabled", True) and disaster_conf.get("dailyWeather", {}).get("enabled", True):
            try:
                weather_info = await disaster_service.get_today_weather()
            except Exception as e:
                log.warning(f"Failed to fetch weather for daily summary: {e}")

        # AI 要約
        ai_conf = settings_manager.get().get("ai", {})
        from app.services.ai_service import ai_service
        use_ai = ai_conf.get("enabled", True) and ai_conf.get("summarizeDailyCalendar", True) and ai_service.is_available()

        message = ""
        if use_ai and (today_events or weather_info):
            try:
                log.info("Generating AI calendar daily summary...")
                message = await ai_service.summarize_calendar_events(
                    today_events,
                    weather_info=weather_info,
                    custom_prompt=ai_conf.get("dailyCalendarPrompt")
                )
            except Exception as e:
                log.warning(f"AI summary failed, falling back to standard template: {e}")
                message = ""

        if not message:
            weather_prefix = f"{weather_info.get('summaryText', '')} " if weather_info and weather_info.get("summaryText") else ""
            if not today_events:
                message = f"{weather_prefix}おはようございます。本日の予定は登録されていません。良い一日を！"
            else:
                message = f"{weather_prefix}おはようございます。本日の予定は {len(today_events)} 件あります。"
                for ev in today_events:
                    if ev.get("isAllDay"):
                        message += f" 終日、{ev['summary']}。"
                    else:
                        st = ev["start"]
                        time_str = f"{st.hour}時{'' if st.minute == 0 else f'{st.minute}分'}"
                        message += f" {time_str}から、{ev['summary']}。"
                message += " 今日も一日がんばりましょう！"

        targets = cal_conf.get("targetDevices") or ["default"]
        voice = cal_conf.get("voice") or "ja-JP-NanamiNeural"
        rate = cal_conf.get("rate") or "+0%"
        pitch = cal_conf.get("pitch") or "+0Hz"
        volume_level = cal_conf.get("volumeLevel")

        log.info(f"Speaking calendar daily summary: '{message[:40]}...' to targets: {targets}")
        res = await self._speech_executor(
            text=message,
            targets=targets,
            voice=voice,
            rate=rate,
            pitch=pitch,
            volume_level=volume_level,
            client_name="カレンダー通知 (朝の予定まとめ)",
            source="calendar",
            source_label="カレンダー (朝の予定まとめ)"
        )
        return {"success": True, "text": message, "result": res}

    # ================= バックグラウンド 定期スケジューラー =================
    async def _scheduler_loop(self):
        log.info("Starting Calendar reminder & daily summary scheduler...")
        while True:
            try:
                now = datetime.now()
                cal_conf = settings_manager.get().get("calendar", {})
                if cal_conf.get("enabled", True):
                    # 1. リマインダー通知 (予定開始の N 分前)
                    if cal_conf.get("remindEnabled", True):
                        await self._check_reminders(cal_conf, now)

                    # 2. 毎朝のデイリーサマリー (指定時刻 HH:MM)
                    if cal_conf.get("dailySummaryEnabled", True):
                        sched_time = cal_conf.get("dailySummaryTime", "07:30")
                        current_hm = now.strftime("%H:%M")
                        if current_hm == sched_time and self._last_summary_date != now.date():
                            self._last_summary_date = now.date()
                            log.info(f"Triggering scheduled daily calendar summary for {current_hm}")
                            asyncio.create_task(self.speak_daily_summary(cal_conf))

            except Exception as e:
                log.error(f"Calendar scheduler error: {e}", exc_info=True)

            await asyncio.sleep(60)

    async def _check_reminders(self, cal_conf: Dict[str, Any], now: datetime):
        remind_mins = int(cal_conf.get("remindMinutesBefore", 10))
        for ev in self.cached_events:
            if ev.get("isAllDay"):
                continue
            ev_start = ev.get("start")
            if not isinstance(ev_start, datetime):
                continue

            diff = (ev_start - now).total_seconds() / 60.0
            # 予定の開始 0分前 〜 remind_mins 分前の間にあり、未通知なら通知
            ev_key = f"{ev_start.isoformat()}_{ev.get('summary')}"
            if 0 <= diff <= remind_mins and ev_key not in self._reminded_event_ids:
                self._reminded_event_ids.add(ev_key)
                # キャッシュ肥大化防止
                if len(self._reminded_event_ids) > 500:
                    self._reminded_event_ids.clear()

                mins_str = f"あと{int(diff)}分で、" if diff >= 1 else "間もなく、"
                st_time_str = f"{ev_start.hour}時{'' if ev_start.minute == 0 else f'{ev_start.minute}分'}"
                remind_text = f"予定のリマインダーです。{mins_str}{st_time_str}から「{ev['summary']}」が始まります。"
                log.info(f"Event reminder triggered: {remind_text}")

                if self._speech_executor:
                    targets = cal_conf.get("targetDevices") or ["default"]
                    await self._speech_executor(
                        text=remind_text,
                        targets=targets,
                        voice=cal_conf.get("voice") or "ja-JP-NanamiNeural",
                        rate=cal_conf.get("rate") or "+0%",
                        pitch=cal_conf.get("pitch") or "+0Hz",
                        volume_level=cal_conf.get("volumeLevel"),
                        client_name="カレンダー通知 (リマインダー)",
                        source="calendar",
                        source_label="カレンダー (リマインダー)"
                    )

calendar_service = CalendarService()
