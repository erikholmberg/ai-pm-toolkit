#!/usr/bin/env python3
"""
Customer Feedback Sentiment Analysis Tool

A practical tool for Product Managers to:
1. Analyze sentiment of customer feedback
2. Categorize feedback by theme
3. Generate summary reports

Usage:
    python sentiment-analysis.py --file feedback.csv
    python sentiment-analysis.py --interactive

Requirements:
    pip install textblob pandas nltk
    python -m textblob.download_corpora
"""

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path

try:
    from textblob import TextBlob
    import pandas as pd
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    print("⚠️  textblob or pandas not installed. Install with: pip install textblob pandas")


@dataclass
class FeedbackItem:
    """Represents a piece of customer feedback with analysis."""
    text: str
    sentiment_score: float  # -1 to 1
    sentiment_label: str    # Negative, Neutral, Positive
    subjectivity: float     # 0 to 1
    themes: List[str]
    source: Optional[str] = None
    date: Optional[str] = None


# Common themes to look for in feedback
THEME_KEYWORDS = {
    'Performance': ['slow', 'fast', 'speed', 'performance', 'lag', 'loading', 'quick', 'responsive'],
    'Usability': ['confusing', 'intuitive', 'easy', 'hard', 'difficult', 'simple', 'complicated', 'user-friendly', 'ux', 'ui'],
    'Features': ['feature', 'functionality', 'capability', 'missing', 'need', 'want', 'wish', 'add', 'include'],
    'Bug': ['bug', 'error', 'crash', 'broken', 'fix', 'issue', 'problem', 'glitch', 'doesn\'t work'],
    'Documentation': ['documentation', 'docs', 'guide', 'tutorial', 'help', 'instructions', 'example'],
    'Support': ['support', 'help', 'response', 'team', 'customer service', 'contact'],
    'Pricing': ['price', 'cost', 'expensive', 'cheap', 'affordable', 'value', 'subscription', 'free'],
    'Onboarding': ['onboarding', 'getting started', 'setup', 'install', 'configuration', 'first time'],
    'Integration': ['integration', 'api', 'connect', 'sync', 'import', 'export', 'webhook'],
    'Reliability': ['reliable', 'uptime', 'downtime', 'stable', 'unstable', 'outage', 'availability'],
}


def analyze_sentiment(text: str) -> tuple:
    """
    Analyze sentiment of text using TextBlob.
    
    Returns:
        Tuple of (polarity, subjectivity, label)
    """
    if not TEXTBLOB_AVAILABLE:
        return (0, 0, 'Unknown')
    
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    subjectivity = blob.sentiment.subjectivity
    
    if polarity > 0.1:
        label = 'Positive'
    elif polarity < -0.1:
        label = 'Negative'
    else:
        label = 'Neutral'
    
    return (polarity, subjectivity, label)


def detect_themes(text: str) -> List[str]:
    """Detect themes present in the feedback text."""
    text_lower = text.lower()
    detected = []
    
    for theme, keywords in THEME_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            detected.append(theme)
    
    return detected if detected else ['General']


def analyze_feedback(text: str, source: str = None, date: str = None) -> FeedbackItem:
    """Analyze a single piece of feedback."""
    polarity, subjectivity, label = analyze_sentiment(text)
    themes = detect_themes(text)
    
    return FeedbackItem(
        text=text,
        sentiment_score=polarity,
        sentiment_label=label,
        subjectivity=subjectivity,
        themes=themes,
        source=source,
        date=date
    )


def analyze_batch(feedback_list: List[Dict]) -> List[FeedbackItem]:
    """Analyze a batch of feedback items."""
    results = []
    for item in feedback_list:
        if isinstance(item, str):
            results.append(analyze_feedback(item))
        elif isinstance(item, dict):
            results.append(analyze_feedback(
                text=item.get('text', ''),
                source=item.get('source'),
                date=item.get('date')
            ))
    return results


def generate_summary(feedback_items: List[FeedbackItem]) -> Dict:
    """Generate a summary report from analyzed feedback."""
    if not feedback_items:
        return {'error': 'No feedback to analyze'}
    
    # Sentiment distribution
    sentiment_counts = Counter(item.sentiment_label for item in feedback_items)
    
    # Theme distribution
    theme_counts = Counter()
    for item in feedback_items:
        for theme in item.themes:
            theme_counts[theme] += 1
    
    # Average scores
    avg_sentiment = sum(item.sentiment_score for item in feedback_items) / len(feedback_items)
    avg_subjectivity = sum(item.subjectivity for item in feedback_items) / len(feedback_items)
    
    # Find most positive and negative
    sorted_by_sentiment = sorted(feedback_items, key=lambda x: x.sentiment_score)
    most_negative = sorted_by_sentiment[:3] if len(sorted_by_sentiment) >= 3 else sorted_by_sentiment
    most_positive = sorted_by_sentiment[-3:][::-1] if len(sorted_by_sentiment) >= 3 else sorted_by_sentiment[::-1]
    
    # Negative feedback themes (for priority action)
    negative_items = [item for item in feedback_items if item.sentiment_label == 'Negative']
    negative_theme_counts = Counter()
    for item in negative_items:
        for theme in item.themes:
            negative_theme_counts[theme] += 1
    
    return {
        'total_feedback': len(feedback_items),
        'sentiment_distribution': dict(sentiment_counts),
        'sentiment_percentages': {
            k: f"{v/len(feedback_items)*100:.1f}%" 
            for k, v in sentiment_counts.items()
        },
        'average_sentiment': avg_sentiment,
        'average_subjectivity': avg_subjectivity,
        'theme_distribution': dict(theme_counts.most_common()),
        'top_themes': theme_counts.most_common(5),
        'negative_theme_priorities': negative_theme_counts.most_common(5),
        'most_positive_feedback': [item.text[:100] for item in most_positive],
        'most_negative_feedback': [item.text[:100] for item in most_negative],
    }


def print_report(summary: Dict, feedback_items: List[FeedbackItem]):
    """Print a formatted report."""
    print("\n" + "=" * 70)
    print("📊 CUSTOMER FEEDBACK SENTIMENT ANALYSIS REPORT")
    print("=" * 70)
    
    print(f"\n📋 OVERVIEW")
    print(f"   Total feedback analyzed: {summary['total_feedback']}")
    print(f"   Average sentiment score: {summary['average_sentiment']:.2f} (scale: -1 to 1)")
    print(f"   Average subjectivity: {summary['average_subjectivity']:.2f} (0=objective, 1=subjective)")
    
    print(f"\n📈 SENTIMENT DISTRIBUTION")
    for sentiment, pct in summary['sentiment_percentages'].items():
        bar_length = int(float(pct.rstrip('%')) / 5)
        bar = "█" * bar_length
        emoji = "😊" if sentiment == "Positive" else ("😐" if sentiment == "Neutral" else "😞")
        print(f"   {emoji} {sentiment:10} {bar:20} {pct}")
    
    print(f"\n🏷️  TOP THEMES (all feedback)")
    for theme, count in summary['top_themes']:
        print(f"   • {theme}: {count} mentions")
    
    if summary['negative_theme_priorities']:
        print(f"\n⚠️  PRIORITY AREAS (themes in negative feedback)")
        for theme, count in summary['negative_theme_priorities']:
            print(f"   • {theme}: {count} negative mentions")
    
    print(f"\n😊 MOST POSITIVE FEEDBACK")
    for i, text in enumerate(summary['most_positive_feedback'], 1):
        print(f"   {i}. \"{text}...\"")
    
    print(f"\n😞 MOST NEGATIVE FEEDBACK (requires attention)")
    for i, text in enumerate(summary['most_negative_feedback'], 1):
        print(f"   {i}. \"{text}...\"")
    
    print("\n" + "=" * 70)
    print("💡 RECOMMENDATIONS")
    print("-" * 70)
    
    # Generate recommendations
    if summary['negative_theme_priorities']:
        top_negative_theme = summary['negative_theme_priorities'][0][0]
        print(f"   1. Focus on '{top_negative_theme}' - most common theme in negative feedback")
    
    negative_pct = float(summary['sentiment_percentages'].get('Negative', '0%').rstrip('%'))
    if negative_pct > 30:
        print(f"   2. ⚠️  High negative sentiment ({negative_pct:.0f}%) - consider urgent review")
    elif negative_pct > 15:
        print(f"   2. Moderate negative sentiment ({negative_pct:.0f}%) - monitor closely")
    else:
        print(f"   2. ✅ Low negative sentiment ({negative_pct:.0f}%) - good health indicator")
    
    print(f"   3. Review the most negative feedback items for specific action items")
    print(f"   4. Consider reaching out to customers with negative feedback")
    
    print("\n" + "=" * 70)


def load_from_csv(filepath: str) -> List[Dict]:
    """Load feedback from a CSV file."""
    feedback = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Try common column names
            text = row.get('feedback') or row.get('text') or row.get('comment') or row.get('message', '')
            if text:
                feedback.append({
                    'text': text,
                    'source': row.get('source'),
                    'date': row.get('date')
                })
    return feedback


def interactive_mode():
    """Run in interactive mode."""
    print("\n📝 Customer Feedback Sentiment Analyzer")
    print("=" * 45)
    print("\nEnter customer feedback (one per line).")
    print("Type 'done' when finished, or 'example' for sample data.\n")
    
    feedback_list = []
    
    while True:
        text = input("Feedback: ").strip()
        
        if text.lower() == 'done':
            break
        elif text.lower() == 'example':
            # Sample feedback for demonstration
            feedback_list = [
                "Love this product! The new UI is so intuitive and fast.",
                "The app keeps crashing whenever I try to export data. Very frustrating.",
                "Good overall, but wish there was better documentation for the API.",
                "Pricing is too high compared to competitors. Might switch.",
                "Support team was incredibly helpful and resolved my issue quickly!",
                "Performance has degraded significantly since the last update. It's so slow now.",
                "The onboarding experience is confusing. Took me forever to figure out basic setup.",
                "Great integration with Slack! Made our workflow much smoother.",
                "Missing key features that your competitors have. Please add bulk import.",
                "Reliable service, never had any downtime issues.",
                "The new dashboard is a massive improvement. Thank you!",
                "Bug in the reporting module - dates are showing incorrectly.",
            ]
            print(f"\n✅ Loaded {len(feedback_list)} example feedback items\n")
            break
        elif text:
            feedback_list.append(text)
    
    if feedback_list:
        print("\n⏳ Analyzing feedback...\n")
        analyzed = analyze_batch(feedback_list)
        summary = generate_summary(analyzed)
        print_report(summary, analyzed)
    else:
        print("\n⚠️  No feedback to analyze")


def main():
    parser = argparse.ArgumentParser(description="Analyze customer feedback sentiment")
    parser.add_argument("--file", "-f", help="Path to CSV file with feedback")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--text", "-t", help="Analyze a single text string")
    parser.add_argument("--output", "-o", help="Output file for JSON results")
    
    args = parser.parse_args()
    
    if not TEXTBLOB_AVAILABLE:
        print("\n❌ Required packages not installed.")
        print("   Run: pip install textblob pandas")
        print("   Then: python -m textblob.download_corpora")
        return
    
    if args.text:
        # Single text analysis
        result = analyze_feedback(args.text)
        print(f"\n📊 Sentiment: {result.sentiment_label} ({result.sentiment_score:.2f})")
        print(f"📋 Themes: {', '.join(result.themes)}")
        print(f"📝 Subjectivity: {result.subjectivity:.2f}")
        
    elif args.file:
        # File-based analysis
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"❌ File not found: {args.file}")
            return
        
        print(f"\n⏳ Loading feedback from {args.file}...")
        feedback_list = load_from_csv(args.file)
        
        if not feedback_list:
            print("❌ No feedback found in file")
            return
        
        print(f"✅ Loaded {len(feedback_list)} feedback items")
        print("⏳ Analyzing...")
        
        analyzed = analyze_batch(feedback_list)
        summary = generate_summary(analyzed)
        print_report(summary, analyzed)
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(summary, f, indent=2)
            print(f"\n✅ Results saved to {args.output}")
    
    else:
        interactive_mode()


if __name__ == "__main__":
    main()

