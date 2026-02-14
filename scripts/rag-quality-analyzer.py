#!/usr/bin/env python3
"""
RAG Quality Analyzer

Evaluate retrieval-augmented generation pipelines on three dimensions:
  1. Retrieval quality  — Are the right documents being retrieved?
  2. Answer faithfulness — Is the answer grounded in the retrieved context?
  3. Answer relevance    — Does the answer actually address the question?

Works with a JSON/CSV of RAG results containing the query, retrieved contexts,
generated answer, and (optionally) ground-truth answer / relevant doc IDs.

Usage:
    python rag-quality-analyzer.py --json rag_results.json
    python rag-quality-analyzer.py --csv rag_results.csv
    python rag-quality-analyzer.py --json rag_results.json --output report.json
    python rag-quality-analyzer.py --interactive

JSON format:
    [
      {
        "id": "q1",
        "query": "What is the capital of France?",
        "retrieved_contexts": [
          "Paris is the capital and largest city of France.",
          "France is a country in Western Europe."
        ],
        "answer": "The capital of France is Paris.",
        "ground_truth": "Paris",
        "relevant_doc_ids": [0]
      }
    ]

CSV format (header row required):
    id,query,retrieved_contexts,answer,ground_truth
    q1,"What is the capital of France?","Paris is the capital of France.|France is in Europe.","The capital is Paris.","Paris"

    Note: multiple contexts separated by | in CSV mode.

Requirements:
    None (stdlib only). Optional: nltk (better tokenization).
"""

import argparse
import csv
import json
import re
import string
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Optional imports
# ---------------------------------------------------------------------------

try:
    from nltk.tokenize import sent_tokenize, word_tokenize
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    if NLTK_AVAILABLE:
        try:
            return word_tokenize(text.lower())
        except Exception:
            pass
    text = text.lower().translate(str.maketrans("", "", string.punctuation))
    return text.split()


def _sent_tokenize(text: str) -> List[str]:
    if NLTK_AVAILABLE:
        try:
            return sent_tokenize(text)
        except Exception:
            pass
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _token_overlap_f1(text_a: str, text_b: str) -> float:
    """Token-level F1 between two texts."""
    tokens_a = set(_tokenize(text_a))
    tokens_b = set(_tokenize(text_b))
    if not tokens_a or not tokens_b:
        return 0.0
    overlap = tokens_a & tokens_b
    precision = len(overlap) / len(tokens_b)
    recall = len(overlap) / len(tokens_a)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


# ---------------------------------------------------------------------------
# 1. Retrieval quality metrics
# ---------------------------------------------------------------------------

def retrieval_precision_at_k(
    relevant_ids: List[int],
    retrieved_count: int,
) -> float:
    """
    Precision@K: fraction of retrieved documents that are relevant.
    relevant_ids are 0-based indices into the retrieved list.
    """
    if retrieved_count <= 0:
        return 0.0
    relevant_in_retrieved = sum(1 for rid in relevant_ids if 0 <= rid < retrieved_count)
    return relevant_in_retrieved / retrieved_count


def retrieval_recall(
    relevant_ids: List[int],
    total_relevant: int,
) -> float:
    """Recall: fraction of all relevant documents that were retrieved."""
    if total_relevant <= 0:
        return 0.0
    return len(relevant_ids) / total_relevant


def mean_reciprocal_rank(relevant_ids: List[int], retrieved_count: int) -> float:
    """MRR: 1/rank of the first relevant document."""
    for rank in range(retrieved_count):
        if rank in relevant_ids:
            return 1.0 / (rank + 1)
    return 0.0


def context_relevance_score(query: str, contexts: List[str]) -> Dict[str, Any]:
    """
    Heuristic: how relevant are retrieved contexts to the query?
    Uses token overlap between query and each context.
    """
    if not contexts:
        return {"avg_relevance": 0.0, "per_context": []}

    per_context = []
    for i, ctx in enumerate(contexts):
        f1 = _token_overlap_f1(query, ctx)
        per_context.append({"index": i, "relevance": round(f1, 4)})

    avg = sum(p["relevance"] for p in per_context) / len(per_context)
    return {"avg_relevance": round(avg, 4), "per_context": per_context}


# ---------------------------------------------------------------------------
# 2. Answer faithfulness metrics
# ---------------------------------------------------------------------------

def answer_faithfulness(answer: str, contexts: List[str]) -> Dict[str, Any]:
    """
    How well is the answer grounded in the retrieved contexts?

    Checks:
    - Token overlap between answer and combined context
    - Sentence-level coverage (what fraction of answer sentences are supported)
    - Entity grounding (names/numbers in answer that appear in contexts)
    """
    combined_context = " ".join(contexts)
    context_tokens = set(_tokenize(combined_context))

    # Token overlap
    answer_tokens = set(_tokenize(answer))
    if not answer_tokens:
        return {"faithfulness": 0.0, "token_overlap": 0.0, "sentence_coverage": 0.0, "entity_score": 0.0}

    overlap = answer_tokens & context_tokens
    token_overlap = len(overlap) / len(answer_tokens)

    # Sentence coverage
    answer_sents = _sent_tokenize(answer)
    covered = 0
    ungrounded_sents: List[str] = []
    for sent in answer_sents:
        sent_tokens = set(_tokenize(sent))
        if not sent_tokens:
            covered += 1
            continue
        sent_overlap = len(sent_tokens & context_tokens) / len(sent_tokens)
        if sent_overlap >= 0.5:
            covered += 1
        else:
            ungrounded_sents.append(sent)
    sentence_coverage = covered / len(answer_sents) if answer_sents else 0.0

    # Entity grounding
    entities: List[str] = []
    entities.extend(re.findall(r'\b\d+(?:\.\d+)?%?\b', answer))
    for sent in answer_sents:
        words = sent.split()
        for w in words[1:]:
            cleaned = w.strip(string.punctuation)
            if cleaned and cleaned[0].isupper() and len(cleaned) > 1:
                entities.append(cleaned.lower())

    context_lower = combined_context.lower()
    seen = set()
    grounded_ents = 0
    hallucinated_ents: List[str] = []
    for ent in entities:
        ent_l = ent.lower()
        if ent_l in seen:
            continue
        seen.add(ent_l)
        if ent_l in context_lower:
            grounded_ents += 1
        else:
            hallucinated_ents.append(ent_l)
    entity_score = grounded_ents / len(seen) if seen else 1.0

    # Composite faithfulness
    faithfulness = (token_overlap * 0.4 + sentence_coverage * 0.35 + entity_score * 0.25)

    return {
        "faithfulness": round(faithfulness, 4),
        "token_overlap": round(token_overlap, 4),
        "sentence_coverage": round(sentence_coverage, 4),
        "entity_score": round(entity_score, 4),
        "ungrounded_sentences": ungrounded_sents[:5],
        "hallucinated_entities": hallucinated_ents[:10],
    }


# ---------------------------------------------------------------------------
# 3. Answer relevance metrics
# ---------------------------------------------------------------------------

def answer_relevance(query: str, answer: str, ground_truth: Optional[str] = None) -> Dict[str, Any]:
    """
    How well does the answer address the query?

    - Query-answer token overlap (does the answer talk about what was asked?)
    - Ground-truth match (if provided)
    """
    qa_f1 = _token_overlap_f1(query, answer)

    result: Dict[str, Any] = {
        "query_answer_f1": round(qa_f1, 4),
    }

    if ground_truth:
        gt_tokens = set(_tokenize(ground_truth))
        ans_tokens = set(_tokenize(answer))

        # Exact containment
        contains_gt = ground_truth.strip().lower() in answer.strip().lower()

        # Token F1 with ground truth
        gt_f1 = _token_overlap_f1(ground_truth, answer)

        result["ground_truth_contained"] = contains_gt
        result["ground_truth_f1"] = round(gt_f1, 4)
        result["relevance_score"] = round((qa_f1 * 0.3 + gt_f1 * 0.5 + (1.0 if contains_gt else 0.0) * 0.2), 4)
    else:
        result["relevance_score"] = round(qa_f1, 4)

    return result


# ---------------------------------------------------------------------------
# Full pipeline evaluation
# ---------------------------------------------------------------------------

def evaluate_rag_case(case: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a single RAG result across all three dimensions."""
    query = case.get("query", "")
    contexts = case.get("retrieved_contexts", [])
    answer = case.get("answer", "")
    ground_truth = case.get("ground_truth")
    relevant_ids = case.get("relevant_doc_ids", [])

    # 1. Retrieval quality
    retrieval: Dict[str, Any] = {}
    ctx_rel = context_relevance_score(query, contexts)
    retrieval["context_relevance"] = ctx_rel["avg_relevance"]
    retrieval["per_context_relevance"] = ctx_rel["per_context"]

    if relevant_ids:
        total_relevant = case.get("total_relevant", len(relevant_ids))
        retrieval["precision_at_k"] = round(retrieval_precision_at_k(relevant_ids, len(contexts)), 4)
        retrieval["recall"] = round(retrieval_recall(relevant_ids, total_relevant), 4)
        retrieval["mrr"] = round(mean_reciprocal_rank(relevant_ids, len(contexts)), 4)
        retrieval["retrieval_score"] = round(
            (retrieval["precision_at_k"] + retrieval["recall"] + retrieval["mrr"]) / 3, 4
        )
    else:
        # No ground truth for retrieval — use context relevance as proxy
        retrieval["retrieval_score"] = ctx_rel["avg_relevance"]

    # 2. Answer faithfulness
    faith = answer_faithfulness(answer, contexts)

    # 3. Answer relevance
    rel = answer_relevance(query, answer, ground_truth)

    # Composite RAG score
    composite = (
        retrieval["retrieval_score"] * 0.30
        + faith["faithfulness"] * 0.40
        + rel["relevance_score"] * 0.30
    )

    return {
        "id": case.get("id", ""),
        "query": query[:120],
        "answer": answer[:200],
        "n_contexts": len(contexts),
        "retrieval": retrieval,
        "faithfulness": faith,
        "relevance": rel,
        "composite_score": round(composite, 4),
    }


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_json(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("results") or data.get("cases") or data.get("queries") or []
    return data


def load_csv(path: str) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
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
            query = get(row, "query", "question", "input")
            answer = get(row, "answer", "response", "output", "generated")
            contexts_raw = get(row, "retrieved_contexts", "contexts", "context", "documents")
            ground_truth = get(row, "ground_truth", "expected", "reference", "expected_output") or None
            relevant_raw = get(row, "relevant_doc_ids", "relevant_ids")

            contexts = [c.strip() for c in contexts_raw.split("|") if c.strip()] if contexts_raw else []
            relevant_ids = []
            if relevant_raw:
                try:
                    relevant_ids = [int(x.strip()) for x in relevant_raw.split(",") if x.strip()]
                except ValueError:
                    pass

            if query and answer:
                cases.append({
                    "id": get(row, "id", "case_id", "name") or str(len(cases) + 1),
                    "query": query,
                    "retrieved_contexts": contexts,
                    "answer": answer,
                    "ground_truth": ground_truth,
                    "relevant_doc_ids": relevant_ids,
                })
    return cases


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _bar(value: float, width: int = 20) -> str:
    filled = int(value * width)
    return "█" * filled + "░" * (width - filled)


def _grade(score: float) -> str:
    if score >= 0.8:
        return "🟢 Good"
    elif score >= 0.6:
        return "🟡 Fair"
    elif score >= 0.4:
        return "🟠 Weak"
    else:
        return "🔴 Poor"


def print_report(results: List[Dict[str, Any]]) -> None:
    n = len(results)
    composites = [r["composite_score"] for r in results]
    retrievals = [r["retrieval"]["retrieval_score"] for r in results]
    faiths = [r["faithfulness"]["faithfulness"] for r in results]
    relevances = [r["relevance"]["relevance_score"] for r in results]

    avg_comp = sum(composites) / n if n else 0
    avg_ret = sum(retrievals) / n if n else 0
    avg_faith = sum(faiths) / n if n else 0
    avg_rel = sum(relevances) / n if n else 0

    print("\n" + "=" * 78)
    print("📊 RAG QUALITY ANALYZER")
    print("=" * 78)

    print(f"\n📋 OVERVIEW:")
    print(f"   • Queries analyzed:      {n}")
    print(f"   • Avg RAG quality:       {avg_comp:.1%}  {_grade(avg_comp)}")

    print(f"\n📈 DIMENSION AVERAGES:")
    print(f"   • Retrieval quality:     {avg_ret:.1%}  {_bar(avg_ret)}  {_grade(avg_ret)}")
    print(f"   • Answer faithfulness:   {avg_faith:.1%}  {_bar(avg_faith)}  {_grade(avg_faith)}")
    print(f"   • Answer relevance:      {avg_rel:.1%}  {_bar(avg_rel)}  {_grade(avg_rel)}")

    # Per-query table
    sorted_results = sorted(results, key=lambda r: r["composite_score"])

    print(f"\n📐 PER-QUERY SCORES (sorted worst → best):\n")
    print(f"   {'#':<4} {'ID':<10} {'Retrieval':>10} {'Faithful':>10} {'Relevant':>10} {'RAG Score':>10}  {'Grade'}")
    print(f"   {'─'*4} {'─'*10} {'─'*10} {'─'*10} {'─'*10} {'─'*10}  {'─'*10}")

    for i, r in enumerate(sorted_results, 1):
        ret = r["retrieval"]["retrieval_score"]
        faith = r["faithfulness"]["faithfulness"]
        rel = r["relevance"]["relevance_score"]
        comp = r["composite_score"]
        print(
            f"   {i:<4} {r['id']:<10} {ret:>9.1%} {faith:>9.1%} "
            f"{rel:>9.1%} {comp:>9.1%}  {_grade(comp)}"
        )

    # Problem areas
    weak_retrieval = [r for r in results if r["retrieval"]["retrieval_score"] < 0.5]
    weak_faith = [r for r in results if r["faithfulness"]["faithfulness"] < 0.5]
    weak_rel = [r for r in results if r["relevance"]["relevance_score"] < 0.5]

    if weak_retrieval or weak_faith or weak_rel:
        print(f"\n⚠️  PROBLEM AREAS:")
        if weak_retrieval:
            print(f"\n   🔍 Weak Retrieval ({len(weak_retrieval)} queries):")
            for r in weak_retrieval[:3]:
                print(f"      • {r['id']}: {r['query'][:60]}... (retrieval: {r['retrieval']['retrieval_score']:.1%})")

        if weak_faith:
            print(f"\n   🏗️  Low Faithfulness ({len(weak_faith)} queries):")
            for r in weak_faith[:3]:
                print(f"      • {r['id']}: {r['query'][:60]}... (faith: {r['faithfulness']['faithfulness']:.1%})")
                ungrounded = r["faithfulness"].get("ungrounded_sentences", [])
                if ungrounded:
                    print(f"        Ungrounded: \"{ungrounded[0][:80]}...\"")
                halluc = r["faithfulness"].get("hallucinated_entities", [])
                if halluc:
                    print(f"        Hallucinated entities: {', '.join(halluc[:5])}")

        if weak_rel:
            print(f"\n   🎯 Low Relevance ({len(weak_rel)} queries):")
            for r in weak_rel[:3]:
                print(f"      • {r['id']}: {r['query'][:60]}... (relevance: {r['relevance']['relevance_score']:.1%})")

    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    if avg_ret < 0.6:
        print(f"   • 🔍 Retrieval is weak ({avg_ret:.0%}): tune chunk size, embedding model, or top-k")
    if avg_faith < 0.6:
        print(f"   • 🏗️  Faithfulness is low ({avg_faith:.0%}): add citation instructions, reduce temperature")
    if avg_rel < 0.6:
        print(f"   • 🎯 Relevance is low ({avg_rel:.0%}): improve query understanding or prompt template")
    if avg_comp >= 0.8:
        print(f"   • ✅ RAG pipeline quality looks good ({avg_comp:.0%})")

    print(f"\n📖 REFERENCE:")
    print(f"   • RAG Score = 30% Retrieval + 40% Faithfulness + 30% Relevance")
    print(f"   • Retrieval: are the right docs being found? (precision, recall, MRR)")
    print(f"   • Faithfulness: is the answer grounded in retrieved context?")
    print(f"   • Relevance: does the answer address the question?")
    print("\n" + "=" * 78)


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

def interactive() -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    print("\n📝 Enter RAG results (empty query to finish):\n")
    while True:
        query = input("  Query: ").strip()
        if not query:
            break
        contexts_raw = input("  Retrieved contexts (separate with |): ").strip()
        answer = input("  Generated answer: ").strip()
        ground_truth = input("  Ground truth (optional, press Enter to skip): ").strip() or None

        contexts = [c.strip() for c in contexts_raw.split("|") if c.strip()]

        case = {
            "id": str(len(cases) + 1),
            "query": query,
            "retrieved_contexts": contexts,
            "answer": answer,
            "ground_truth": ground_truth,
            "relevant_doc_ids": [],
        }
        result = evaluate_rag_case(case)
        cases.append(case)
        print(
            f"    → RAG Score: {result['composite_score']:.1%}  "
            f"(Retrieval: {result['retrieval']['retrieval_score']:.1%}, "
            f"Faith: {result['faithfulness']['faithfulness']:.1%}, "
            f"Relevance: {result['relevance']['relevance_score']:.1%})\n"
        )
    return cases


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate RAG pipeline quality: retrieval precision/recall, "
                    "answer faithfulness, and answer relevance.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --json rag_results.json
  %(prog)s --csv rag_results.csv --output report.json
  %(prog)s --interactive
        """,
    )
    parser.add_argument("--json", "-j", type=str, help="JSON file with RAG results")
    parser.add_argument("--csv", "-c", type=str, help="CSV file with RAG results")
    parser.add_argument("--interactive", "-i", action="store_true", help="Enter results interactively")
    parser.add_argument("--output", "-o", type=str, help="Write report to JSON file")
    args = parser.parse_args()

    if not args.json and not args.csv and not args.interactive:
        print("Error: provide --json, --csv, or --interactive.", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    # Load cases
    if args.interactive:
        cases = interactive()
    elif args.json:
        try:
            cases = load_json(args.json)
        except Exception as e:
            print(f"Error loading JSON: {e}", file=sys.stderr)
            return 1
    else:
        try:
            cases = load_csv(args.csv)
        except Exception as e:
            print(f"Error loading CSV: {e}", file=sys.stderr)
            return 1

    if not cases:
        print("Error: no valid RAG results found.", file=sys.stderr)
        return 1

    # Evaluate
    results = [evaluate_rag_case(case) for case in cases]

    # Report
    print_report(results)

    # JSON output
    if args.output:
        n = len(results)
        composites = [r["composite_score"] for r in results]
        report = {
            "n_queries": n,
            "avg_rag_score": round(sum(composites) / n, 4) if n else 0,
            "avg_retrieval": round(sum(r["retrieval"]["retrieval_score"] for r in results) / n, 4) if n else 0,
            "avg_faithfulness": round(sum(r["faithfulness"]["faithfulness"] for r in results) / n, 4) if n else 0,
            "avg_relevance": round(sum(r["relevance"]["relevance_score"] for r in results) / n, 4) if n else 0,
            "results": results,
        }
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📁 Report saved to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
