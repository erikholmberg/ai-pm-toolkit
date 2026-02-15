#!/usr/bin/env python3
"""
Interview Note Analyzer

Batch-analyze interview transcripts or notes to extract themes, pain points,
feature requests, and quotes with frequency counts. Output feeds directly
into the opportunity scorer for data-driven prioritization.

Supports both heuristic keyword extraction (no API needed) and LLM-powered
deep analysis. Reads from a directory of text files, a CSV, or a JSON file.

Usage:
    # Analyze a directory of interview notes
    python interview-note-analyzer.py --dir ./interviews/

    # Analyze from CSV
    python interview-note-analyzer.py --csv interviews.csv

    # LLM-powered analysis (requires API key)
    python interview-note-analyzer.py --csv interviews.csv --llm

    # Export for opportunity scorer
    python interview-note-analyzer.py --csv interviews.csv --output-opportunity needs.csv

CSV format (header row required):
    id,participant,notes
    1,PM at Acme,"Biggest pain point is onboarding. Took 2 weeks to get team set up. Wishes there was a wizard or template."
    2,Eng Lead at Beta,"Search is too slow. Returns irrelevant results. Would pay more for better search."

JSON format:
    [
      {"id": "1", "participant": "PM at Acme", "notes": "..."},
      ...
    ]

Requirements:
    None for heuristic mode (stdlib only).
    Optional: openai/anthropic (for LLM mode).
"""

import argparse
import csv
import json
import os
import re
import string
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Optional imports
# ---------------------------------------------------------------------------

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# ---------------------------------------------------------------------------
# Theme / keyword dictionaries
# ---------------------------------------------------------------------------

PAIN_POINT_SIGNALS = [
    "pain", "painful", "frustrat", "annoying", "difficult", "hard to",
    "struggle", "confus", "slow", "broken", "bug", "crash", "error",
    "can't", "cannot", "unable", "impossible", "waste", "tedious",
    "manual", "workaround", "hack", "wish", "if only", "hate",
    "terrible", "awful", "nightmare", "blocker", "dealbreaker",
    "takes too long", "time-consuming", "complicated", "clunky",
]

FEATURE_REQUEST_SIGNALS = [
    "would be nice", "wish", "want", "need", "should have",
    "would love", "request", "please add", "missing", "if you could",
    "it would help", "we need", "feature", "capability",
    "integrate", "integration", "support for", "ability to",
    "would pay", "upgrade", "improve", "better",
]

THEME_KEYWORDS = {
    "Onboarding": ["onboarding", "getting started", "setup", "first time", "ramp up", "learning curve", "documentation", "tutorial"],
    "Performance": ["slow", "fast", "speed", "latency", "performance", "lag", "loading", "timeout", "responsive"],
    "Search": ["search", "find", "filter", "query", "discovery", "browse", "lookup"],
    "Pricing": ["price", "pricing", "cost", "expensive", "cheap", "affordable", "plan", "tier", "billing", "value"],
    "Reliability": ["reliable", "uptime", "downtime", "crash", "bug", "error", "stable", "outage"],
    "Integration": ["integration", "api", "connect", "sync", "import", "export", "webhook", "plugin"],
    "Collaboration": ["team", "collaborate", "share", "permission", "role", "access", "invite", "workspace"],
    "Analytics": ["analytics", "report", "dashboard", "metrics", "insight", "data", "chart", "tracking"],
    "AI / ML": ["ai", "ml", "model", "prediction", "recommendation", "suggest", "automat", "intelligent"],
    "Security": ["security", "privacy", "compliance", "gdpr", "sso", "auth", "encrypt", "permission"],
    "Mobile": ["mobile", "phone", "tablet", "app", "ios", "android", "responsive"],
    "Support": ["support", "help", "customer service", "response time", "ticket"],
    "Customization": ["custom", "configur", "personali", "template", "flexible", "workflow"],
    "Export / Reporting": ["export", "report", "pdf", "csv", "download", "print"],
    "Notifications": ["notification", "alert", "email", "notify", "reminder", "digest"],
}

POSITIVE_SIGNALS = [
    "love", "great", "excellent", "amazing", "awesome", "fantastic",
    "helpful", "easy", "intuitive", "powerful", "impressed",
    "game changer", "best", "valuable", "smooth", "clean",
]


# ---------------------------------------------------------------------------
# Text analysis
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    text = text.lower().translate(str.maketrans("", "", string.punctuation.replace("'", "")))
    return text.split()


def _extract_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]


def _contains_signal(text: str, signals: List[str]) -> List[str]:
    """Return which signals appear in the text."""
    text_lower = text.lower()
    return [s for s in signals if s in text_lower]


def detect_themes(text: str) -> List[str]:
    """Detect themes in an interview note."""
    text_lower = text.lower()
    found = []
    for theme, keywords in THEME_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            found.append(theme)
    return found if found else ["General"]


def extract_pain_points(text: str) -> List[str]:
    """Extract sentences that express pain points."""
    sentences = _extract_sentences(text)
    pain_sentences = []
    for sent in sentences:
        if _contains_signal(sent, PAIN_POINT_SIGNALS):
            pain_sentences.append(sent.strip())
    return pain_sentences


def extract_feature_requests(text: str) -> List[str]:
    """Extract sentences that express feature requests."""
    sentences = _extract_sentences(text)
    request_sentences = []
    for sent in sentences:
        if _contains_signal(sent, FEATURE_REQUEST_SIGNALS):
            request_sentences.append(sent.strip())
    return request_sentences


def extract_positive_feedback(text: str) -> List[str]:
    """Extract sentences with positive sentiment."""
    sentences = _extract_sentences(text)
    return [s.strip() for s in sentences if _contains_signal(s, POSITIVE_SIGNALS)]


def analyze_interview(interview: Dict[str, str]) -> Dict[str, Any]:
    """Analyze a single interview note."""
    text = interview.get("notes", "")
    return {
        "id": interview.get("id", ""),
        "participant": interview.get("participant", ""),
        "themes": detect_themes(text),
        "pain_points": extract_pain_points(text),
        "feature_requests": extract_feature_requests(text),
        "positive_feedback": extract_positive_feedback(text),
        "word_count": len(text.split()),
    }


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate across all interviews."""
    theme_counter: Counter = Counter()
    pain_point_list: List[Tuple[str, str]] = []  # (text, participant)
    feature_request_list: List[Tuple[str, str]] = []
    positive_list: List[Tuple[str, str]] = []
    theme_to_participants: Dict[str, List[str]] = defaultdict(list)
    pain_theme_map: Dict[str, List[str]] = defaultdict(list)

    for r in results:
        participant = r["participant"]
        for theme in r["themes"]:
            theme_counter[theme] += 1
            theme_to_participants[theme].append(participant)

        for pp in r["pain_points"]:
            pain_point_list.append((pp, participant))
            # Map pain point to themes
            pp_themes = detect_themes(pp)
            for t in pp_themes:
                pain_theme_map[t].append(pp)

        for fr in r["feature_requests"]:
            feature_request_list.append((fr, participant))

        for pos in r["positive_feedback"]:
            positive_list.append((pos, participant))

    # Deduplicate similar pain points / requests by simple substring matching
    unique_pains = _deduplicate_quotes(pain_point_list)
    unique_requests = _deduplicate_quotes(feature_request_list)

    return {
        "n_interviews": len(results),
        "theme_counts": theme_counter.most_common(),
        "theme_participants": {k: list(set(v)) for k, v in theme_to_participants.items()},
        "pain_points": unique_pains,
        "feature_requests": unique_requests,
        "positive_feedback": positive_list,
        "pain_by_theme": {k: len(v) for k, v in pain_theme_map.items()},
    }


def _deduplicate_quotes(items: List[Tuple[str, str]], sim_threshold: int = 20) -> List[Dict[str, Any]]:
    """Group similar quotes together. Returns list of {text, mentions, participants}."""
    groups: List[Dict[str, Any]] = []
    for text, participant in items:
        text_lower = text.lower()[:sim_threshold]
        found = False
        for group in groups:
            if group["key"] == text_lower:
                group["mentions"] += 1
                group["participants"].add(participant)
                found = True
                break
        if not found:
            groups.append({
                "key": text_lower,
                "text": text,
                "mentions": 1,
                "participants": {participant},
            })

    # Sort by mentions
    groups.sort(key=lambda g: -g["mentions"])
    return [
        {"text": g["text"], "mentions": g["mentions"], "participants": list(g["participants"])}
        for g in groups
    ]


# ---------------------------------------------------------------------------
# LLM analysis
# ---------------------------------------------------------------------------

def llm_analyze_batch(interviews: List[Dict[str, str]], model: str) -> Optional[str]:
    """Use LLM to do deep thematic analysis across all interviews."""
    combined = "\n\n".join(
        f"--- Interview {i.get('id', idx+1)} ({i.get('participant', 'Unknown')}) ---\n{i.get('notes', '')}"
        for idx, i in enumerate(interviews)
    )

    # Truncate if very long
    if len(combined) > 50000:
        combined = combined[:50000] + "\n\n[... truncated ...]"

    prompt = f"""You are a senior UX researcher analyzing {len(interviews)} customer interviews.

{combined}

Analyze ALL interviews and produce a structured synthesis:

1. **Top Themes** (ranked by frequency): List each theme, how many interviews mention it, and a one-line summary.
2. **Pain Points** (ranked by severity/frequency): List each pain point with supporting quotes and participant count.
3. **Feature Requests** (ranked by frequency): List each request with who asked for it.
4. **Positive Feedback**: What's working well? List with quotes.
5. **Opportunity Areas**: Based on the pain points, what are the top 3-5 opportunity areas the product team should focus on?

Be specific. Use actual quotes. Include participant identifiers. Format as clear markdown."""

    try:
        if "claude" in model.lower():
            if not ANTHROPIC_AVAILABLE:
                return "Error: pip install anthropic"
            client = anthropic.Anthropic()
            resp = client.messages.create(
                model=model, max_tokens=4096, temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text
        elif "gpt" in model.lower():
            if not OPENAI_AVAILABLE:
                return "Error: pip install openai"
            client = openai.OpenAI()
            resp = client.chat.completions.create(
                model=model, temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content
        else:
            return f"Error: unsupported model {model}"
    except Exception as e:
        return f"Error: {e}"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_csv(path: str) -> List[Dict[str, str]]:
    """Load interviews from CSV."""
    interviews: List[Dict[str, str]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        lower_map = {fl.lower().strip(): fl for fl in fields}

        def get(row: Dict, *aliases: str) -> str:
            for a in aliases:
                key = lower_map.get(a.lower().strip())
                if key and row.get(key):
                    return row[key].strip()
            return ""

        for row in reader:
            notes = get(row, "notes", "text", "transcript", "feedback", "content", "comment")
            if notes:
                interviews.append({
                    "id": get(row, "id", "case_id", "interview_id") or str(len(interviews) + 1),
                    "participant": get(row, "participant", "name", "user", "interviewee", "respondent"),
                    "notes": notes,
                })
    return interviews


def load_json(path: str) -> List[Dict[str, str]]:
    """Load interviews from JSON."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("interviews") or data.get("notes") or data.get("cases") or []
    return [
        {
            "id": item.get("id", str(i + 1)),
            "participant": item.get("participant", item.get("name", item.get("user", ""))),
            "notes": item.get("notes", item.get("text", item.get("transcript", item.get("feedback", "")))),
        }
        for i, item in enumerate(data)
        if item.get("notes") or item.get("text") or item.get("transcript") or item.get("feedback")
    ]


def load_directory(path: str) -> List[Dict[str, str]]:
    """Load interview notes from a directory of .txt / .md files."""
    interviews: List[Dict[str, str]] = []
    for filename in sorted(os.listdir(path)):
        if filename.startswith("."):
            continue
        if not filename.endswith((".txt", ".md", ".text")):
            continue
        filepath = os.path.join(path, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read().strip()
        if text:
            name = os.path.splitext(filename)[0]
            interviews.append({
                "id": str(len(interviews) + 1),
                "participant": name,
                "notes": text,
            })
    return interviews


# ---------------------------------------------------------------------------
# Opportunity scorer export
# ---------------------------------------------------------------------------

def export_for_opportunity_scorer(agg: Dict[str, Any], path: str) -> None:
    """
    Export themes as needs for the opportunity scorer CSV format.
    Maps theme frequency to importance (more mentions = higher importance).
    Satisfaction is left at 5.0 (neutral) — user fills in from survey data.
    """
    theme_counts = agg["theme_counts"]
    if not theme_counts:
        return

    max_count = theme_counts[0][1]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["need", "importance", "satisfaction", "category", "n_respondents"])
        for theme, count in theme_counts:
            if theme == "General":
                continue
            # Scale count to 1-10 importance
            importance = round(max(1, min(10, (count / max_count) * 10)), 1)
            pain_count = agg["pain_by_theme"].get(theme, 0)
            writer.writerow([
                f"Improve {theme.lower()} experience",
                importance,
                5.0,  # neutral — fill in from survey
                theme,
                count,
            ])
    print(f"\n📁 Opportunity scorer input saved to {path}")
    print(f"   → Run: python opportunity-scorer.py --csv {path}")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(
    results: List[Dict[str, Any]],
    agg: Dict[str, Any],
) -> None:
    """Pretty-print interview analysis."""
    n = agg["n_interviews"]

    print("\n" + "=" * 78)
    print("📊 INTERVIEW NOTE ANALYZER")
    print("=" * 78)

    print(f"\n📋 OVERVIEW:")
    print(f"   • Interviews analyzed:  {n}")
    print(f"   • Themes identified:    {len(agg['theme_counts'])}")
    print(f"   • Pain points found:    {len(agg['pain_points'])}")
    print(f"   • Feature requests:     {len(agg['feature_requests'])}")
    print(f"   • Positive mentions:    {len(agg['positive_feedback'])}")

    total_words = sum(r["word_count"] for r in results)
    print(f"   • Total words analyzed: {total_words:,}")

    # Themes
    print(f"\n🏷️  THEMES (by frequency):\n")
    print(f"   {'Theme':<24} {'Count':>6} {'% of interviews':>16}  Mentioned by")
    print(f"   {'─'*24} {'─'*6} {'─'*16}  {'─'*30}")
    for theme, count in agg["theme_counts"]:
        pct = count / n * 100
        bar_len = int(pct / 100 * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        participants = agg["theme_participants"].get(theme, [])
        who = ", ".join(participants[:3])
        if len(participants) > 3:
            who += f" +{len(participants) - 3}"
        print(f"   {theme:<24} {count:>6} {pct:>14.0f}%  {bar}  {who}")

    # Pain points
    if agg["pain_points"]:
        print(f"\n🔴 PAIN POINTS ({len(agg['pain_points'])} unique, ranked by frequency):")
        for i, pp in enumerate(agg["pain_points"][:10], 1):
            who = ", ".join(pp["participants"][:3])
            count_str = f"({pp['mentions']}x)" if pp["mentions"] > 1 else ""
            print(f"\n   {i}. {count_str} \"{pp['text'][:120]}\"")
            print(f"      — {who}")

    # Feature requests
    if agg["feature_requests"]:
        print(f"\n🟡 FEATURE REQUESTS ({len(agg['feature_requests'])} unique):")
        for i, fr in enumerate(agg["feature_requests"][:10], 1):
            who = ", ".join(fr["participants"][:3])
            count_str = f"({fr['mentions']}x)" if fr["mentions"] > 1 else ""
            print(f"\n   {i}. {count_str} \"{fr['text'][:120]}\"")
            print(f"      — {who}")

    # Positive
    if agg["positive_feedback"]:
        print(f"\n🟢 WHAT'S WORKING ({len(agg['positive_feedback'])} mentions):")
        for text, participant in agg["positive_feedback"][:5]:
            print(f"   • \"{text[:100]}\" — {participant}")

    # Pain by theme
    pain_themes = sorted(agg["pain_by_theme"].items(), key=lambda x: -x[1])
    if pain_themes:
        print(f"\n⚠️  PAIN CONCENTRATION BY THEME:")
        for theme, count in pain_themes[:8]:
            bar_len = min(30, count * 3)
            bar = "█" * bar_len
            print(f"   {theme:<24} {bar} {count}")

    # Per-interview summary
    print(f"\n📐 PER-INTERVIEW SUMMARY:")
    print(f"   {'ID':<6} {'Participant':<24} {'Themes':>7} {'Pains':>7} {'Requests':>9} {'Positive':>9}")
    print(f"   {'─'*6} {'─'*24} {'─'*7} {'─'*7} {'─'*9} {'─'*9}")
    for r in results:
        print(
            f"   {r['id']:<6} {r['participant'][:24]:<24} {len(r['themes']):>7} "
            f"{len(r['pain_points']):>7} {len(r['feature_requests']):>9} {len(r['positive_feedback']):>9}"
        )

    print(f"\n💡 NEXT STEPS:")
    print(f"   • Use --output-opportunity to export themes for the opportunity scorer")
    print(f"   • Use --llm for deeper LLM-powered thematic analysis")
    print(f"   • Cross-reference pain points with product backlog")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Analyze interview notes to extract themes, pain points, and feature requests.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv interviews.csv
  %(prog)s --dir ./interviews/
  %(prog)s --csv interviews.csv --llm --model claude-3-5-sonnet-20241022
  %(prog)s --csv interviews.csv --output-opportunity needs.csv
        """,
    )
    parser.add_argument("--csv", "-c", type=str, help="CSV file with interview notes")
    parser.add_argument("--json", "-j", type=str, help="JSON file with interview notes")
    parser.add_argument("--dir", "-d", type=str, help="Directory of .txt/.md interview files")
    parser.add_argument("--llm", action="store_true", help="Use LLM for deeper analysis")
    parser.add_argument("--model", type=str, default="claude-3-5-sonnet-20241022", help="LLM model for analysis")
    parser.add_argument("--output", "-o", type=str, help="Write full results to JSON file")
    parser.add_argument("--output-opportunity", type=str, help="Export themes as opportunity scorer CSV")
    args = parser.parse_args()

    if not args.csv and not args.json and not args.dir:
        print("Error: provide --csv, --json, or --dir.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Load interviews
    if args.csv:
        try:
            interviews = load_csv(args.csv)
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1
    elif args.json:
        try:
            interviews = load_json(args.json)
        except Exception as e:
            print(f"Error loading JSON: {e}", file=sys.stderr)
            return 1
    else:
        try:
            interviews = load_directory(args.dir)
        except Exception as e:
            print(f"Error loading directory: {e}", file=sys.stderr)
            return 1

    if not interviews:
        print("Error: no valid interview notes found.", file=sys.stderr)
        return 1

    # Analyze
    results = [analyze_interview(i) for i in interviews]
    agg = aggregate_results(results)

    # Print report
    print_report(results, agg)

    # LLM analysis
    if args.llm:
        print(f"\n✍️  LLM THEMATIC ANALYSIS ({args.model}):")
        print("─" * 78)
        narrative = llm_analyze_batch(interviews, args.model)
        print(narrative)
        print("─" * 78)

    # Opportunity scorer export
    if args.output_opportunity:
        export_for_opportunity_scorer(agg, args.output_opportunity)

    # JSON output
    if args.output:
        report = {
            "n_interviews": len(results),
            "theme_counts": agg["theme_counts"],
            "pain_points": agg["pain_points"],
            "feature_requests": agg["feature_requests"],
            "positive_feedback": [{"text": t, "participant": p} for t, p in agg["positive_feedback"]],
            "per_interview": results,
        }
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
