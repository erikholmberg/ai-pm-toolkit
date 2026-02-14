#!/usr/bin/env python3
"""
Hallucination / Groundedness Scorer

Score how well AI-generated responses are grounded in provided source material.
Uses multiple complementary methods: token overlap, entailment heuristics,
claim extraction with source coverage, and optional LLM-as-judge.

Produces a per-response groundedness score (0-1) plus an aggregate report
highlighting the most and least grounded responses.

Usage:
    # Score from CSV (source, response pairs)
    python groundedness-scorer.py --csv pairs.csv
    python groundedness-scorer.py --csv pairs.csv --method all --output report.json

    # Score from JSON
    python groundedness-scorer.py --json pairs.json

    # Interactive mode
    python groundedness-scorer.py --interactive

    # Use LLM judge for deeper analysis (requires API key)
    python groundedness-scorer.py --csv pairs.csv --method llm --judge claude-3-5-sonnet-20241022

CSV format (header row required):
    id,source,response
    1,"The Eiffel Tower is 330m tall and located in Paris.","The Eiffel Tower stands at 330 meters in Paris, France."
    2,"Python was created by Guido van Rossum in 1991.","Python was created by James Gosling in 1995."

JSON format:
    [
      {"id": "1", "source": "...", "response": "..."},
      {"id": "2", "source": "...", "response": "..."}
    ]

Requirements:
    None for basic scoring (stdlib only).
    Optional: nltk (for better tokenization), openai/anthropic (for LLM judge).
"""

import argparse
import csv
import json
import math
import re
import string
import sys
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Optional imports
# ---------------------------------------------------------------------------

try:
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.util import ngrams as nltk_ngrams
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

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
# Text utilities
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    """Word-tokenize text. Uses NLTK if available, else simple split."""
    if NLTK_AVAILABLE:
        try:
            return word_tokenize(text.lower())
        except Exception:
            pass
    # Fallback: strip punctuation, lowercase, split
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    return text.split()


def _sent_tokenize(text: str) -> List[str]:
    """Split text into sentences."""
    if NLTK_AVAILABLE:
        try:
            return sent_tokenize(text)
        except Exception:
            pass
    # Fallback: simple regex sentence splitter
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _ngrams(tokens: List[str], n: int) -> List[Tuple[str, ...]]:
    """Generate n-grams from token list."""
    if NLTK_AVAILABLE:
        try:
            return list(nltk_ngrams(tokens, n))
        except Exception:
            pass
    return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


# ---------------------------------------------------------------------------
# Scoring methods
# ---------------------------------------------------------------------------

def token_overlap_score(source: str, response: str) -> Dict[str, float]:
    """
    Compute token-level overlap between response and source.

    Returns precision (what fraction of response tokens appear in source),
    recall (what fraction of source tokens appear in response), and F1.
    """
    src_tokens = set(_tokenize(source))
    resp_tokens = _tokenize(response)

    if not resp_tokens or not src_tokens:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    resp_set = set(resp_tokens)
    overlap = resp_set & src_tokens

    precision = len(overlap) / len(resp_set) if resp_set else 0.0
    recall = len(overlap) / len(src_tokens) if src_tokens else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def ngram_overlap_score(source: str, response: str, n: int = 3) -> float:
    """
    Fraction of response n-grams that appear in source.
    Higher n = stricter check for copied/grounded phrases.
    """
    src_tokens = _tokenize(source)
    resp_tokens = _tokenize(response)

    if len(resp_tokens) < n or len(src_tokens) < n:
        return 0.0

    src_ngrams = set(_ngrams(src_tokens, n))
    resp_ngrams = _ngrams(resp_tokens, n)

    if not resp_ngrams:
        return 0.0

    matched = sum(1 for ng in resp_ngrams if ng in src_ngrams)
    return round(matched / len(resp_ngrams), 4)


def sentence_coverage_score(source: str, response: str, threshold: float = 0.5) -> Dict[str, Any]:
    """
    For each sentence in the response, check if it is "covered" by the source
    (token overlap with any part of the source exceeds threshold).

    Returns fraction of response sentences that are grounded plus details.
    """
    resp_sentences = _sent_tokenize(response)
    if not resp_sentences:
        return {"coverage": 0.0, "grounded": 0, "total": 0, "ungrounded_sentences": []}

    src_tokens = set(_tokenize(source))
    grounded = 0
    ungrounded: List[str] = []

    for sent in resp_sentences:
        sent_tokens = set(_tokenize(sent))
        if not sent_tokens:
            grounded += 1
            continue
        overlap = len(sent_tokens & src_tokens) / len(sent_tokens)
        if overlap >= threshold:
            grounded += 1
        else:
            ungrounded.append(sent)

    coverage = grounded / len(resp_sentences) if resp_sentences else 0.0
    return {
        "coverage": round(coverage, 4),
        "grounded": grounded,
        "total": len(resp_sentences),
        "ungrounded_sentences": ungrounded,
    }


def entity_grounding_score(source: str, response: str) -> Dict[str, Any]:
    """
    Extract "entity-like" tokens from the response (capitalized words, numbers,
    quoted strings) and check what fraction appear in the source.

    This catches hallucinated names, numbers, and proper nouns.
    """
    # Extract entities: capitalized words, numbers, quoted strings
    resp_entities: List[str] = []

    # Numbers (including decimals, percentages)
    resp_entities.extend(re.findall(r'\b\d+(?:\.\d+)?%?\b', response))

    # Capitalized words (likely proper nouns) — skip sentence starters
    sentences = _sent_tokenize(response)
    for sent in sentences:
        words = sent.split()
        for w in words[1:]:  # skip first word of sentence
            cleaned = w.strip(string.punctuation)
            if cleaned and cleaned[0].isupper() and len(cleaned) > 1:
                resp_entities.append(cleaned.lower())

    # Quoted strings
    resp_entities.extend(s.lower() for s in re.findall(r'"([^"]+)"', response))
    resp_entities.extend(s.lower() for s in re.findall(r"'([^']+)'", response))

    if not resp_entities:
        return {"entity_score": 1.0, "total_entities": 0, "grounded": 0, "hallucinated": []}

    source_lower = source.lower()
    grounded = 0
    hallucinated: List[str] = []
    seen = set()

    for ent in resp_entities:
        if ent in seen:
            continue
        seen.add(ent)
        if ent in source_lower:
            grounded += 1
        else:
            hallucinated.append(ent)

    total = len(seen)
    score = grounded / total if total > 0 else 1.0

    return {
        "entity_score": round(score, 4),
        "total_entities": total,
        "grounded": grounded,
        "hallucinated": hallucinated[:10],  # cap for readability
    }


def composite_groundedness(
    source: str,
    response: str,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Compute a composite groundedness score from all heuristic methods.

    Default weights:
        token_overlap (F1): 0.25
        trigram_overlap:     0.25
        sentence_coverage:   0.25
        entity_grounding:    0.25
    """
    if weights is None:
        weights = {
            "token_overlap": 0.25,
            "trigram_overlap": 0.25,
            "sentence_coverage": 0.25,
            "entity_grounding": 0.25,
        }

    tok = token_overlap_score(source, response)
    tri = ngram_overlap_score(source, response, n=3)
    cov = sentence_coverage_score(source, response)
    ent = entity_grounding_score(source, response)

    composite = (
        weights.get("token_overlap", 0.25) * tok["f1"]
        + weights.get("trigram_overlap", 0.25) * tri
        + weights.get("sentence_coverage", 0.25) * cov["coverage"]
        + weights.get("entity_grounding", 0.25) * ent["entity_score"]
    )

    return {
        "composite_score": round(composite, 4),
        "token_overlap": tok,
        "trigram_overlap": round(tri, 4),
        "sentence_coverage": cov,
        "entity_grounding": ent,
    }


# ---------------------------------------------------------------------------
# LLM-as-judge scoring
# ---------------------------------------------------------------------------

def llm_groundedness_score(
    source: str,
    response: str,
    judge_model: str = "claude-3-5-sonnet-20241022",
) -> Dict[str, Any]:
    """
    Use an LLM to evaluate groundedness on a 1-5 scale with reasoning.
    """
    prompt = f"""You are an expert fact-checker evaluating whether an AI response is grounded in the provided source material.

## Source Material:
{source}

## AI Response to Evaluate:
{response}

## Task:
Evaluate the response on these dimensions (score 1-5 each):

1. **Faithfulness**: Does the response only contain information present in the source? (5=perfectly faithful, 1=many fabrications)
2. **Completeness**: Does the response cover the key information from the source? (5=comprehensive, 1=misses critical info)
3. **Accuracy**: Are specific facts (names, numbers, dates) correct per the source? (5=all correct, 1=many errors)

Also identify any specific hallucinated claims (information in the response NOT in the source).

## Output Format (JSON):
{{
  "faithfulness": <1-5>,
  "completeness": <1-5>,
  "accuracy": <1-5>,
  "overall": <1-5>,
  "hallucinated_claims": ["claim 1", "claim 2"],
  "reasoning": "Brief explanation"
}}

Provide your evaluation as valid JSON:"""

    import time
    start = time.time()

    try:
        if "claude" in judge_model.lower():
            if not ANTHROPIC_AVAILABLE:
                return {"error": "anthropic package required. pip install anthropic"}
            client = anthropic.Anthropic()
            resp = client.messages.create(
                model=judge_model,
                max_tokens=1024,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text
            tokens = resp.usage.input_tokens + resp.usage.output_tokens
        elif "gpt" in judge_model.lower():
            if not OPENAI_AVAILABLE:
                return {"error": "openai package required. pip install openai"}
            client = openai.OpenAI()
            resp = client.chat.completions.create(
                model=judge_model,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.choices[0].message.content
            tokens = resp.usage.total_tokens
        else:
            return {"error": f"Unsupported judge model: {judge_model}"}

        latency_ms = (time.time() - start) * 1000

        # Parse JSON from response
        text = text.strip()
        if "```json" in text:
            text = text[text.find("```json") + 7:]
            text = text[:text.find("```")]
        elif "```" in text:
            text = text[text.find("```") + 3:]
            text = text[:text.find("```")]

        parsed = json.loads(text.strip())
        parsed["latency_ms"] = round(latency_ms, 0)
        parsed["tokens_used"] = tokens
        parsed["judge_model"] = judge_model
        # Normalize to 0-1
        overall = parsed.get("overall", 3)
        parsed["normalized_score"] = round((overall - 1) / 4, 4)
        return parsed

    except json.JSONDecodeError:
        return {"error": "Failed to parse LLM judge response", "raw": text[:500]}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _col(fieldnames: List[str], *aliases: str) -> Optional[str]:
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias.lower().strip() in lower_map:
            return lower_map[alias.lower().strip()]
    return None


def load_csv(path: str) -> List[Dict[str, str]]:
    """Load source/response pairs from CSV."""
    pairs: List[Dict[str, str]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        c_id = _col(fields, "id", "case_id", "name")
        c_src = _col(fields, "source", "context", "reference", "ground_truth", "document")
        c_resp = _col(fields, "response", "output", "answer", "prediction", "generated")
        c_query = _col(fields, "query", "question", "input", "prompt")

        for row in reader:
            source = row.get(c_src or "source", "").strip()
            response = row.get(c_resp or "response", "").strip()
            if not source or not response:
                continue
            pairs.append({
                "id": row.get(c_id or "id", str(len(pairs) + 1)).strip(),
                "source": source,
                "response": response,
                "query": row.get(c_query or "", "").strip() if c_query else "",
            })
    return pairs


def load_json(path: str) -> List[Dict[str, str]]:
    """Load source/response pairs from JSON."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("pairs") or data.get("cases") or data.get("test_cases") or []
    pairs = []
    for i, item in enumerate(data):
        source = item.get("source") or item.get("context") or item.get("reference") or ""
        response = item.get("response") or item.get("output") or item.get("answer") or ""
        if source and response:
            pairs.append({
                "id": item.get("id", str(i + 1)),
                "source": source.strip(),
                "response": response.strip(),
                "query": (item.get("query") or item.get("question") or item.get("input") or "").strip(),
            })
    return pairs


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, width: int = 20) -> str:
    filled = int(value * width)
    return "█" * filled + "░" * (width - filled)


def _grade(score: float) -> str:
    if score >= 0.9:
        return "🟢 High"
    elif score >= 0.7:
        return "🟡 Medium"
    elif score >= 0.5:
        return "🟠 Low"
    else:
        return "🔴 Poor"


def print_report(
    results: List[Dict[str, Any]],
    method: str,
) -> None:
    """Pretty-print groundedness analysis."""
    print("\n" + "=" * 78)
    print("📊 HALLUCINATION / GROUNDEDNESS SCORER")
    print("=" * 78)

    n = len(results)
    if method in ("heuristic", "all"):
        scores = [r["scores"]["composite_score"] for r in results]
    elif method == "llm":
        scores = [r["scores"].get("normalized_score", 0) for r in results if "error" not in r["scores"]]
    else:
        scores = [r["scores"].get("composite_score", 0) for r in results]

    avg = sum(scores) / len(scores) if scores else 0
    high = sum(1 for s in scores if s >= 0.9)
    medium = sum(1 for s in scores if 0.7 <= s < 0.9)
    low = sum(1 for s in scores if 0.5 <= s < 0.7)
    poor = sum(1 for s in scores if s < 0.5)

    print(f"\n📋 OVERVIEW:")
    print(f"   • Pairs analyzed:    {n}")
    print(f"   • Method:            {method}")
    print(f"   • Avg groundedness:  {avg:.1%}  {_grade(avg)}")
    print(f"   • 🟢 High (≥90%):    {high}")
    print(f"   • 🟡 Medium (70-89%): {medium}")
    print(f"   • 🟠 Low (50-69%):    {low}")
    print(f"   • 🔴 Poor (<50%):     {poor}")

    # Per-item table
    sorted_results = sorted(results, key=lambda r: r.get("scores", {}).get("composite_score", r.get("scores", {}).get("normalized_score", 0)))

    print(f"\n📈 SCORES (sorted worst → best):\n")

    if method in ("heuristic", "all"):
        print(f"   {'#':<5} {'ID':<12} {'Composite':>10} {'Token F1':>10} {'3-gram':>8} {'Sent Cov':>10} {'Entity':>8}  {'Grade'}")
        print(f"   {'─'*5} {'─'*12} {'─'*10} {'─'*10} {'─'*8} {'─'*10} {'─'*8}  {'─'*12}")
        for i, r in enumerate(sorted_results, 1):
            s = r["scores"]
            comp = s.get("composite_score", 0)
            tok_f1 = s.get("token_overlap", {}).get("f1", 0)
            tri = s.get("trigram_overlap", 0)
            cov = s.get("sentence_coverage", {}).get("coverage", 0)
            ent = s.get("entity_grounding", {}).get("entity_score", 0)
            print(
                f"   {i:<5} {r['id']:<12} {comp:>9.1%} {tok_f1:>9.1%} {tri:>7.1%} "
                f"{cov:>9.1%} {ent:>7.1%}  {_grade(comp)}"
            )
    else:
        print(f"   {'#':<5} {'ID':<12} {'Overall':>8} {'Faith':>7} {'Accur':>7} {'Compl':>7}  {'Grade'}")
        print(f"   {'─'*5} {'─'*12} {'─'*8} {'─'*7} {'─'*7} {'─'*7}  {'─'*12}")
        for i, r in enumerate(sorted_results, 1):
            s = r["scores"]
            if "error" in s:
                print(f"   {i:<5} {r['id']:<12} {'ERROR':>8}")
                continue
            norm = s.get("normalized_score", 0)
            faith = s.get("faithfulness", 0)
            acc = s.get("accuracy", 0)
            compl = s.get("completeness", 0)
            print(
                f"   {i:<5} {r['id']:<12} {norm:>7.1%} {faith:>5}/5 {acc:>5}/5 {compl:>5}/5  {_grade(norm)}"
            )

    # Worst offenders
    worst = sorted_results[:3]
    if worst and scores:
        print(f"\n⚠️  MOST LIKELY HALLUCINATIONS:")
        for r in worst:
            s = r["scores"]
            score_val = s.get("composite_score", s.get("normalized_score", 0))
            print(f"\n   {r['id']} (score: {score_val:.1%}):")
            print(f"   Response: {r['response'][:120]}...")

            if "sentence_coverage" in s:
                ungrounded = s["sentence_coverage"].get("ungrounded_sentences", [])
                if ungrounded:
                    print(f"   Ungrounded sentences:")
                    for sent in ungrounded[:3]:
                        print(f"     • {sent[:100]}")

            if "entity_grounding" in s:
                hallucinated = s["entity_grounding"].get("hallucinated", [])
                if hallucinated:
                    print(f"   Potentially hallucinated entities: {', '.join(hallucinated[:5])}")

            if "hallucinated_claims" in s:
                claims = s["hallucinated_claims"]
                if claims:
                    print(f"   Hallucinated claims (LLM judge):")
                    for claim in claims[:3]:
                        print(f"     • {claim}")

    # Score distribution
    print(f"\n📊 SCORE DISTRIBUTION:")
    buckets = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}
    for s in scores:
        if s < 0.2:
            buckets["0.0-0.2"] += 1
        elif s < 0.4:
            buckets["0.2-0.4"] += 1
        elif s < 0.6:
            buckets["0.4-0.6"] += 1
        elif s < 0.8:
            buckets["0.6-0.8"] += 1
        else:
            buckets["0.8-1.0"] += 1
    max_count = max(buckets.values()) if buckets.values() else 1
    for label, count in buckets.items():
        bar_len = int(count / max(1, max_count) * 30)
        bar = "█" * bar_len
        print(f"   {label}:  {bar} {count}")

    print(f"\n💡 REFERENCE:")
    print(f"   • Composite = avg of token overlap, trigram overlap, sentence coverage, entity grounding")
    print(f"   • Token overlap: word-level precision/recall between response and source")
    print(f"   • Sentence coverage: fraction of response sentences supported by source")
    print(f"   • Entity grounding: fraction of names/numbers in response that appear in source")
    print(f"   • Use --method llm for deeper analysis with an LLM judge")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Score how well AI responses are grounded in source material. "
                    "Detects hallucinations using token overlap, sentence coverage, "
                    "entity grounding, and optional LLM-as-judge.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --csv pairs.csv
  %(prog)s --csv pairs.csv --method all --output report.json
  %(prog)s --json pairs.json --method llm --judge claude-3-5-sonnet-20241022
  %(prog)s --interactive
        """,
    )
    parser.add_argument("--csv", "-c", type=str, help="CSV file with source, response columns")
    parser.add_argument("--json", "-j", type=str, help="JSON file with source/response pairs")
    parser.add_argument("--interactive", "-i", action="store_true", help="Enter pairs interactively")
    parser.add_argument(
        "--method", "-m", type=str, default="heuristic",
        choices=["heuristic", "llm", "all"],
        help="Scoring method: heuristic (fast, no API), llm (LLM judge), all (both) (default: heuristic)",
    )
    parser.add_argument(
        "--judge", type=str, default="claude-3-5-sonnet-20241022",
        help="LLM judge model (for --method llm or all)",
    )
    parser.add_argument("--output", "-o", type=str, help="Write results to JSON file")
    args = parser.parse_args()

    if not args.csv and not args.json and not args.interactive:
        print("Error: provide --csv, --json, or --interactive.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Load pairs
    if args.interactive:
        pairs: List[Dict[str, str]] = []
        print("\n📝 Enter source/response pairs (empty source to finish):\n")
        while True:
            source = input("  Source text: ").strip()
            if not source:
                break
            response = input("  Response:    ").strip()
            if not response:
                continue
            pairs.append({"id": str(len(pairs) + 1), "source": source, "response": response, "query": ""})
            # Quick score
            s = composite_groundedness(source, response)
            print(f"    → Groundedness: {s['composite_score']:.1%}  {_grade(s['composite_score'])}\n")
    elif args.csv:
        try:
            pairs = load_csv(args.csv)
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1
    else:
        try:
            pairs = load_json(args.json)
        except Exception as e:
            print(f"Error loading JSON: {e}", file=sys.stderr)
            return 1

    if not pairs:
        print("Error: no valid source/response pairs found.", file=sys.stderr)
        return 1

    # Score each pair
    results: List[Dict[str, Any]] = []
    for pair in pairs:
        result: Dict[str, Any] = {
            "id": pair["id"],
            "source": pair["source"][:200],
            "response": pair["response"][:200],
        }

        if args.method in ("heuristic", "all"):
            result["scores"] = composite_groundedness(pair["source"], pair["response"])

        if args.method == "llm":
            result["scores"] = llm_groundedness_score(pair["source"], pair["response"], args.judge)

        if args.method == "all":
            llm_result = llm_groundedness_score(pair["source"], pair["response"], args.judge)
            result["scores"]["llm_judge"] = llm_result

        results.append(result)

    # Print report
    print_report(results, args.method)

    # JSON output
    if args.output:
        with open(args.output, "w") as f:
            json.dump({
                "method": args.method,
                "n_pairs": len(results),
                "results": results,
            }, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
