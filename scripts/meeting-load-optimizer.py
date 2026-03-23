#!/usr/bin/env python3
"""
Meeting load optimizer

Analyze a calendar-style export (meetings with start/end times) to surface
meeting-heavy days, fragmented focus time, and recurring-meeting candidates.
Uses your local work window (default 09:00–17:00 Mon–Fri) and clips meetings
to that window.

Usage:
    python meeting-load-optimizer.py --csv scripts/samples/sample-meetings.csv
    python meeting-load-optimizer.py --csv week.csv --min-focus-minutes 90 --heavy-pct 0.55
    python meeting-load-optimizer.py --csv week.csv --work-start 08:30 --work-end 18:00 --json

CSV (header row):
    start,end,title,team,recurring
    2025-03-17T09:00:00,2025-03-17T09:30:00,Standup,Core,yes

Required: either **start** and **end** (datetime), or **start_date** + **start_time**
+ **end_date** + **end_time** (Google Calendar–style). Optional: title, subject,
team, recurring (yes/true/1).

Tips:
    Export from Google Calendar as CSV and map columns, or paste from a
    spreadsheet. Times without timezone are treated as one consistent local zone.

Requirements:
    None (stdlib only). Optional: python-dateutil for flexible date parsing.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

Interval = Tuple[datetime, datetime]


def _col(fieldnames: Sequence[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        key = alias.lower().strip()
        if key in lower_map:
            return lower_map[key]
    return None


def parse_datetime(s: str) -> Optional[datetime]:
    if not s or not str(s).strip():
        return None
    s = str(s).strip()
    try:
        from dateutil import parser as date_parser

        return date_parser.parse(s)
    except ImportError:
        pass
    except Exception:
        pass
    for fmt, trim in [
        ("%Y-%m-%dT%H:%M:%S", 19),
        ("%Y-%m-%d %H:%M:%S", 19),
        ("%Y-%m-%dT%H:%M", 16),
        ("%Y-%m-%d %H:%M", 16),
        ("%Y-%m-%d", 10),
    ]:
        try:
            return datetime.strptime(s[:trim].strip(), fmt)
        except ValueError:
            continue
    return None


def parse_date_only(s: str) -> Optional[date]:
    if not s or not str(s).strip():
        return None
    s = str(s).strip()
    try:
        from dateutil import parser as date_parser

        return date_parser.parse(s).date()
    except ImportError:
        pass
    except Exception:
        pass
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_time_only(s: str) -> Optional[time]:
    if not s or not str(s).strip():
        return None
    s = str(s).strip()
    try:
        from dateutil import parser as date_parser

        return date_parser.parse(s).time()
    except ImportError:
        pass
    except Exception:
        pass
    m = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", s)
    if m:
        h, mm = int(m.group(1)), int(m.group(2))
        sec = int(m.group(3) or 0)
        if h <= 23 and mm <= 59 and sec <= 59:
            return time(h, mm, sec)
    return None


def combine_split_start_end(row: Dict[str, str], sd: str, st: str, ed: str, et: str) -> Optional[Interval]:
    """Build start/end from Start Date + Start Time + End Date + End Time (e.g. Google CSV)."""
    d1 = parse_date_only(row.get(sd, "") or "")
    d2 = parse_date_only(row.get(ed, "") or "")
    t1 = parse_time_only(row.get(st, "") or "")
    t2 = parse_time_only(row.get(et, "") or "")
    if not d1 or not d2 or not t1 or not t2:
        return None
    a = datetime.combine(d1, t1)
    b = datetime.combine(d2, t2)
    if b <= a:
        return None
    return (a, b)


def parse_hhmm(s: str) -> time:
    s = str(s).strip()
    m = re.match(r"^(\d{1,2}):(\d{2})$", s)
    if not m:
        raise ValueError(f"invalid time (use HH:MM): {s!r}")
    h, mm = int(m.group(1)), int(m.group(2))
    if h > 23 or mm > 59:
        raise ValueError(f"invalid time: {s!r}")
    return time(h, mm)


def weekday_index(d: date) -> int:
    return d.weekday()  # Mon=0


def merge_intervals(intervals: List[Interval]) -> List[Interval]:
    if not intervals:
        return []
    sorted_iv = sorted(intervals, key=lambda x: x[0])
    out: List[Interval] = [sorted_iv[0]]
    for s, e in sorted_iv[1:]:
        ls, le = out[-1]
        if s <= le:
            out[-1] = (ls, max(le, e))
        else:
            out.append((s, e))
    return out


def clip_interval(
    start: datetime, end: datetime, win_start: datetime, win_end: datetime
) -> Optional[Interval]:
    s = max(start, win_start)
    e = min(end, win_end)
    if e <= s:
        return None
    return (s, e)


def work_window_for_day(
    d: date, work_start_t: time, work_end_t: time
) -> Tuple[datetime, datetime]:
    ws = datetime.combine(d, work_start_t)
    we = datetime.combine(d, work_end_t)
    if we <= ws:
        we += timedelta(days=1)
    return ws, we


def split_meeting_into_days(
    start: datetime,
    end: datetime,
    work_start_t: time,
    work_end_t: time,
    work_weekdays: Optional[set[int]],
) -> List[Tuple[date, Interval]]:
    """Split [start,end) into per-day clipped intervals within work hours."""
    out: List[Tuple[date, Interval]] = []
    if end <= start:
        return out
    cur = start.date()
    end_d = end.date()
    one = timedelta(days=1)
    while cur <= end_d:
        if work_weekdays is not None and weekday_index(cur) not in work_weekdays:
            cur += one
            continue
        ws, we = work_window_for_day(cur, work_start_t, work_end_t)
        clipped = clip_interval(start, end, ws, we)
        if clipped:
            out.append((cur, clipped))
        cur += one
    return out


def max_free_minutes_merged(merged_meetings: List[Interval], win_start: datetime, win_end: datetime) -> float:
    """Longest contiguous free segment inside [win_start, win_end) after merged meetings."""
    if win_end <= win_start:
        return 0.0
    gaps: List[Interval] = []
    t = win_start
    for s, e in merged_meetings:
        if s > t:
            gaps.append((t, min(s, win_end)))
        t = max(t, e)
    if t < win_end:
        gaps.append((t, win_end))
    best = 0.0
    for a, b in gaps:
        if b > a:
            best = max(best, (b - a).total_seconds() / 60.0)
    return best


def normalize_title(title: str) -> str:
    t = title.strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t[:200]


def is_recurring_flag(raw: str) -> bool:
    s = str(raw).strip().lower()
    return s in ("1", "true", "yes", "y", "recurring", "weekly", "daily")


def analyze(
    rows: List[Dict[str, str]],
    start_col: str,
    end_col: str,
    title_col: Optional[str],
    team_col: Optional[str],
    recurring_col: Optional[str],
    work_start_t: time,
    work_end_t: time,
    work_weekdays: set[int],
    min_focus_minutes: float,
    heavy_pct: float,
) -> Dict[str, Any]:
    """
    Build per-team per-day stats and rollups.
    """
    # (team_key, date) -> list of intervals (already clipped to that day's work window)
    day_meetings: Dict[Tuple[str, date], List[Interval]] = defaultdict(list)
    title_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    recurring_titles: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for row in rows:
        raw_s = row.get(start_col, "")
        raw_e = row.get(end_col, "")
        st = parse_datetime(raw_s)
        en = parse_datetime(raw_e)
        if not st or not en:
            continue
        if en <= st:
            continue

        team = (row.get(team_col, "") or "").strip() if team_col else ""
        team_key = team if team else "__all__"

        tit = ""
        if title_col:
            tit = (row.get(title_col, "") or "").strip()
        rec = False
        if recurring_col:
            rec = is_recurring_flag(row.get(recurring_col, "") or "")

        parts = split_meeting_into_days(st, en, work_start_t, work_end_t, work_weekdays)
        for d, iv in parts:
            day_meetings[(team_key, d)].append(iv)
            if tit:
                nk = normalize_title(tit)
                title_counts[team_key][nk] += 1
                if rec:
                    recurring_titles[team_key][nk] += 1

    if not day_meetings:
        return {"error": "no valid meeting rows (need parseable start/end with end > start)"}

    work_minutes_per_day = (
        datetime.combine(date.today(), work_end_t) - datetime.combine(date.today(), work_start_t)
    ).total_seconds() / 60.0
    if work_minutes_per_day <= 0:
        return {"error": "work end must be after work start"}

    teams = sorted({k[0] for k in day_meetings.keys()})

    per_team: Dict[str, Any] = {}
    for team_key in teams:
        days_stats: List[Dict[str, Any]] = []
        heavy_days: List[str] = []
        focus_violations: List[str] = []

        team_days = sorted({d for (tk, d) in day_meetings if tk == team_key})
        for d in team_days:
            ws, we = work_window_for_day(d, work_start_t, work_end_t)
            raw_ivs = day_meetings.get((team_key, d), [])
            merged = merge_intervals(raw_ivs)
            meet_min = sum((e - s).total_seconds() / 60.0 for s, e in merged)
            pct = meet_min / work_minutes_per_day if work_minutes_per_day else 0.0
            max_focus = max_free_minutes_merged(merged, ws, we)

            flagged_heavy = pct >= heavy_pct
            flagged_focus = max_focus < min_focus_minutes
            ds = d.isoformat()
            if flagged_heavy:
                heavy_days.append(ds)
            if flagged_focus:
                focus_violations.append(ds)

            days_stats.append(
                {
                    "date": ds,
                    "meeting_minutes": round(meet_min, 1),
                    "work_minutes": round(work_minutes_per_day, 1),
                    "meeting_pct_of_day": round(pct * 100, 1),
                    "max_focus_block_minutes": round(max_focus, 1),
                    "meeting_heavy": flagged_heavy,
                    "maker_schedule_risk": flagged_focus,
                }
            )

        total_meet = sum(x["meeting_minutes"] for x in days_stats)
        total_work = sum(x["work_minutes"] for x in days_stats)
        avg_pct = (total_meet / total_work * 100) if total_work else 0.0

        top_titles = sorted(
            title_counts[team_key].items(), key=lambda x: (-x[1], x[0])
        )[:12]
        recurring_top = sorted(
            recurring_titles[team_key].items(), key=lambda x: (-x[1], x[0])
        )[:8]

        suggestions: List[str] = []
        if heavy_days:
            suggestions.append(
                f"Meeting-heavy days (≥{heavy_pct * 100:.0f}% of work window): {len(heavy_days)} day(s) — consider moving or shortening blocks on {', '.join(heavy_days[:5])}"
                + (" …" if len(heavy_days) > 5 else "")
            )
        if focus_violations:
            suggestions.append(
                f"No contiguous focus block ≥{min_focus_minutes:.0f} min on {len(focus_violations)} day(s) — protect a maker block or batch meetings."
            )
        for name, cnt in top_titles:
            if cnt >= 3 and len(suggestions) < 6:
                suggestions.append(
                    f"Frequent meeting title ({cnt}×): “{name}” — audit recurrence length and necessity."
                )

        per_team[team_key] = {
            "days": days_stats,
            "summary": {
                "days_analyzed": len(days_stats),
                "total_meeting_hours": round(total_meet / 60.0, 2),
                "avg_meeting_pct_of_workday": round(avg_pct, 1),
                "meeting_heavy_day_count": len(heavy_days),
                "maker_schedule_risk_day_count": len(focus_violations),
            },
            "suggestions": suggestions,
            "top_meeting_titles": [{"title": n, "count": c} for n, c in top_titles],
            "recurring_flagged_titles": [{"title": n, "count": c} for n, c in recurring_top],
        }

    return {
        "work_window": {
            "start": work_start_t.isoformat(timespec="minutes"),
            "end": work_end_t.isoformat(timespec="minutes"),
            "weekdays": sorted(work_weekdays) if work_weekdays is not None else list(range(5)),
        },
        "thresholds": {
            "min_focus_minutes": min_focus_minutes,
            "meeting_heavy_pct": heavy_pct,
        },
        "teams": per_team,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze meeting CSV for load, focus blocks, and recurring-meeting signals."
    )
    parser.add_argument("--csv", required=True, help="Meetings CSV path")
    parser.add_argument(
        "--work-start",
        default="09:00",
        help="Workday start (HH:MM, default 09:00)",
    )
    parser.add_argument(
        "--work-end",
        default="17:00",
        help="Workday end (HH:MM, default 17:00)",
    )
    parser.add_argument(
        "--weekends",
        action="store_true",
        help="Include Sat–Sun in analysis (default: Mon–Fri only)",
    )
    parser.add_argument(
        "--min-focus-minutes",
        type=float,
        default=120.0,
        help="Flag days with no contiguous free block at least this long (default 120)",
    )
    parser.add_argument(
        "--heavy-pct",
        type=float,
        default=0.5,
        help="Flag day as meeting-heavy if meeting time fraction ≥ this (default 0.5)",
    )
    parser.add_argument("--json", action="store_true", help="JSON only")
    args = parser.parse_args()

    try:
        work_start_t = parse_hhmm(args.work_start)
        work_end_t = parse_hhmm(args.work_end)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not 0 < args.heavy_pct <= 1:
        print("Error: --heavy-pct must be in (0, 1]", file=sys.stderr)
        return 1
    if args.min_focus_minutes <= 0:
        print("Error: --min-focus-minutes must be positive", file=sys.stderr)
        return 1

    work_weekdays: Optional[set[int]] = None if args.weekends else {0, 1, 2, 3, 4}
    weekday_set = work_weekdays if work_weekdays is not None else set(range(7))

    try:
        with open(args.csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("CSV has no header")
            fields = list(reader.fieldnames)
            start_col = _col(
                fields, "start", "startdatetime", "begin", "start datetime"
            )
            end_col = _col(fields, "end", "enddatetime", "finish", "end datetime")
            sd_col = _col(fields, "start_date", "start date")
            st_col = _col(fields, "start_time", "start time")
            ed_col = _col(fields, "end_date", "end date")
            et_col = _col(fields, "end_time", "end time")

            if start_col and end_col:
                pass
            elif sd_col and st_col and ed_col and et_col:
                start_col = "__start__"
                end_col = "__end__"
            else:
                raise ValueError(
                    "CSV needs either start+end datetimes, or start_date/start_time/end_date/end_time"
                )

            title_col = _col(fields, "title", "subject", "meeting", "name", "summary")
            team_col = _col(fields, "team", "person", "owner", "calendar")
            recurring_col = _col(fields, "recurring", "repeat", "recurrence")
            rows = [dict(r) for r in reader]

            if start_col == "__start__":
                for row in rows:
                    comb = combine_split_start_end(row, sd_col, st_col, ed_col, et_col)
                    if comb:
                        a, b = comb
                        row["__start__"] = a.isoformat(sep=" ")
                        row["__end__"] = b.isoformat(sep=" ")
    except OSError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    result = analyze(
        rows,
        start_col,
        end_col,
        title_col,
        team_col,
        recurring_col,
        work_start_t,
        work_end_t,
        weekday_set,
        args.min_focus_minutes,
        args.heavy_pct,
    )

    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print("\n" + "=" * 62)
    print("MEETING LOAD OPTIMIZER")
    print("=" * 62)
    ww = result["work_window"]
    th = result["thresholds"]
    print(f"\nWork window: {ww['start']}–{ww['end']} (weekdays: {ww['weekdays']})")
    print(
        f"Thresholds: focus block ≥ {th['min_focus_minutes']:.0f} min; "
        f"heavy day ≥ {th['meeting_heavy_pct'] * 100:.0f}% of work time in meetings"
    )

    for team_key, block in sorted(result["teams"].items()):
        label = "All meetings" if team_key == "__all__" else f"Team / person: {team_key}"
        print(f"\n── {label} ──")
        sm = block["summary"]
        print(
            f"   Days in range: {sm['days_analyzed']}  |  "
            f"Total meeting time: {sm['total_meeting_hours']:.1f} h  |  "
            f"Avg meeting % of workday: {sm['avg_meeting_pct_of_workday']:.1f}%"
        )
        print(
            f"   Meeting-heavy days: {sm['meeting_heavy_day_count']}  |  "
            f"Maker-schedule risk days (no ≥{th['min_focus_minutes']:.0f} min block): "
            f"{sm['maker_schedule_risk_day_count']}"
        )
        if block["suggestions"]:
            print("\n   Suggestions:")
            for s in block["suggestions"]:
                print(f"   • {s}")
        risky = [d for d in block["days"] if d["maker_schedule_risk"] or d["meeting_heavy"]]
        if risky:
            print("\n   Flagged days:")
            for d in risky[:14]:
                flags = []
                if d["meeting_heavy"]:
                    flags.append("heavy")
                if d["maker_schedule_risk"]:
                    flags.append("focus")
                print(
                    f"   • {d['date']}: {d['meeting_pct_of_day']:.0f}% meetings, "
                    f"max focus {d['max_focus_block_minutes']:.0f} min [{', '.join(flags)}]"
                )
            if len(risky) > 14:
                print(f"   … +{len(risky) - 14} more")

    print("\n" + "=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
