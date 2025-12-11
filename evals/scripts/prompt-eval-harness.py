#!/usr/bin/env python3
"""
Prompt Evaluation Harness

A simple framework for evaluating and comparing prompts.

Usage:
    python prompt-eval-harness.py --config eval_config.json
    python prompt-eval-harness.py --interactive

Requirements:
    pip install openai anthropic pandas tqdm
"""

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Callable
import time

# Try to import LLM clients
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

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


@dataclass
class TestCase:
    """A single test case for evaluation."""
    id: str
    input: str
    expected_output: Optional[str] = None
    category: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class EvalResult:
    """Result of evaluating a single test case."""
    test_case_id: str
    prompt_version: str
    input: str
    output: str
    expected_output: Optional[str]
    latency_ms: float
    tokens_used: int
    scores: Dict[str, float]
    timestamp: str


class PromptEvaluator:
    """Evaluate prompts against test cases."""
    
    def __init__(self, model: str = "claude-3-haiku-20240307"):
        self.model = model
        self.results: List[EvalResult] = []
        
        # Initialize client based on model
        if "claude" in model.lower():
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("anthropic package required. Run: pip install anthropic")
            self.client = anthropic.Anthropic()
            self.provider = "anthropic"
        elif "gpt" in model.lower():
            if not OPENAI_AVAILABLE:
                raise ImportError("openai package required. Run: pip install openai")
            self.client = openai.OpenAI()
            self.provider = "openai"
        else:
            raise ValueError(f"Unsupported model: {model}")
    
    def run_prompt(self, system_prompt: str, user_input: str) -> tuple:
        """Run a prompt and return (output, latency_ms, tokens)."""
        start_time = time.time()
        
        if self.provider == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_input}]
            )
            output = response.content[0].text
            tokens = response.usage.input_tokens + response.usage.output_tokens
            
        elif self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ]
            )
            output = response.choices[0].message.content
            tokens = response.usage.total_tokens
        
        latency_ms = (time.time() - start_time) * 1000
        return output, latency_ms, tokens
    
    def evaluate_case(
        self,
        test_case: TestCase,
        system_prompt: str,
        prompt_version: str,
        scorers: Optional[Dict[str, Callable]] = None
    ) -> EvalResult:
        """Evaluate a single test case."""
        
        output, latency_ms, tokens = self.run_prompt(system_prompt, test_case.input)
        
        # Run scorers
        scores = {}
        if scorers:
            for name, scorer in scorers.items():
                try:
                    scores[name] = scorer(
                        input=test_case.input,
                        output=output,
                        expected=test_case.expected_output
                    )
                except Exception as e:
                    scores[name] = -1  # Error indicator
        
        result = EvalResult(
            test_case_id=test_case.id,
            prompt_version=prompt_version,
            input=test_case.input,
            output=output,
            expected_output=test_case.expected_output,
            latency_ms=latency_ms,
            tokens_used=tokens,
            scores=scores,
            timestamp=datetime.now().isoformat()
        )
        
        self.results.append(result)
        return result
    
    def evaluate_batch(
        self,
        test_cases: List[TestCase],
        system_prompt: str,
        prompt_version: str,
        scorers: Optional[Dict[str, Callable]] = None,
        progress: bool = True
    ) -> List[EvalResult]:
        """Evaluate a batch of test cases."""
        
        results = []
        iterator = test_cases
        
        if progress:
            try:
                from tqdm import tqdm
                iterator = tqdm(test_cases, desc=f"Evaluating {prompt_version}")
            except ImportError:
                pass
        
        for case in iterator:
            result = self.evaluate_case(case, system_prompt, prompt_version, scorers)
            results.append(result)
        
        return results
    
    def compare_prompts(
        self,
        test_cases: List[TestCase],
        prompts: Dict[str, str],  # version -> prompt
        scorers: Optional[Dict[str, Callable]] = None
    ) -> Dict:
        """Compare multiple prompt versions on the same test cases."""
        
        all_results = {}
        for version, prompt in prompts.items():
            print(f"\n📊 Evaluating: {version}")
            results = self.evaluate_batch(test_cases, prompt, version, scorers)
            all_results[version] = results
        
        return all_results
    
    def summary(self) -> Dict:
        """Generate summary statistics from results."""
        
        if not self.results:
            return {}
        
        # Group by prompt version
        by_version = {}
        for result in self.results:
            if result.prompt_version not in by_version:
                by_version[result.prompt_version] = []
            by_version[result.prompt_version].append(result)
        
        summary = {}
        for version, results in by_version.items():
            latencies = [r.latency_ms for r in results]
            tokens = [r.tokens_used for r in results]
            
            # Aggregate scores
            score_sums = {}
            score_counts = {}
            for r in results:
                for name, score in r.scores.items():
                    if score >= 0:  # Ignore errors
                        score_sums[name] = score_sums.get(name, 0) + score
                        score_counts[name] = score_counts.get(name, 0) + 1
            
            avg_scores = {
                name: score_sums[name] / score_counts[name]
                for name in score_sums
            }
            
            summary[version] = {
                "count": len(results),
                "avg_latency_ms": sum(latencies) / len(latencies),
                "avg_tokens": sum(tokens) / len(tokens),
                "avg_scores": avg_scores,
            }
        
        return summary
    
    def export_results(self, filepath: str):
        """Export results to JSON or CSV."""
        
        results_data = [asdict(r) for r in self.results]
        
        if filepath.endswith(".json"):
            with open(filepath, "w") as f:
                json.dump(results_data, f, indent=2)
        elif filepath.endswith(".csv") and PANDAS_AVAILABLE:
            df = pd.DataFrame(results_data)
            df.to_csv(filepath, index=False)
        else:
            print(f"Unsupported format or pandas not available: {filepath}")


# Example scorers
def exact_match(input: str, output: str, expected: str) -> float:
    """Score 1 if output matches expected exactly."""
    if expected is None:
        return 0
    return 1.0 if output.strip() == expected.strip() else 0.0


def contains_expected(input: str, output: str, expected: str) -> float:
    """Score 1 if output contains expected text."""
    if expected is None:
        return 0
    return 1.0 if expected.lower() in output.lower() else 0.0


def length_score(input: str, output: str, expected: str, target: int = 500) -> float:
    """Score based on how close to target length."""
    diff = abs(len(output) - target)
    return max(0, 1 - (diff / target))


def print_summary(summary: Dict):
    """Print formatted summary."""
    print("\n" + "=" * 60)
    print("📊 EVALUATION SUMMARY")
    print("=" * 60)
    
    for version, stats in summary.items():
        print(f"\n📌 {version}")
        print(f"   Cases: {stats['count']}")
        print(f"   Avg Latency: {stats['avg_latency_ms']:.0f}ms")
        print(f"   Avg Tokens: {stats['avg_tokens']:.0f}")
        
        if stats['avg_scores']:
            print("   Scores:")
            for name, score in stats['avg_scores'].items():
                print(f"      {name}: {score:.2f}")


def demo():
    """Run a simple demonstration."""
    
    print("🧪 Prompt Evaluation Demo")
    print("-" * 40)
    
    # Example test cases
    test_cases = [
        TestCase(
            id="tc1",
            input="What is the capital of France?",
            expected_output="Paris",
            category="geography"
        ),
        TestCase(
            id="tc2",
            input="What is 2 + 2?",
            expected_output="4",
            category="math"
        ),
        TestCase(
            id="tc3",
            input="Who wrote Romeo and Juliet?",
            expected_output="Shakespeare",
            category="literature"
        ),
    ]
    
    # Example prompts to compare
    prompts = {
        "baseline": "You are a helpful assistant. Answer questions concisely.",
        "detailed": "You are a helpful assistant. Answer questions with detailed explanations.",
        "minimal": "Answer briefly."
    }
    
    # Initialize evaluator
    print("Note: This demo requires an API key (ANTHROPIC_API_KEY or OPENAI_API_KEY)")
    print("Running with simulated results for demonstration...\n")
    
    # Simulate results for demo
    for prompt_name, prompt in prompts.items():
        print(f"Would evaluate '{prompt_name}' prompt on {len(test_cases)} test cases")
    
    print("\nTo run actual evaluation:")
    print("1. Set ANTHROPIC_API_KEY or OPENAI_API_KEY")
    print("2. Run: python prompt-eval-harness.py --interactive")


def interactive_mode():
    """Run in interactive mode."""
    
    print("\n🧪 Prompt Evaluation Harness")
    print("=" * 40)
    
    # Get model selection
    print("\nAvailable models:")
    print("1. claude-3-haiku-20240307 (fast, cheap)")
    print("2. claude-3-sonnet-20240229 (balanced)")
    print("3. gpt-3.5-turbo (fast)")
    print("4. gpt-4 (quality)")
    
    choice = input("\nSelect model (1-4, default 1): ").strip() or "1"
    models = {
        "1": "claude-3-haiku-20240307",
        "2": "claude-3-sonnet-20240229",
        "3": "gpt-3.5-turbo",
        "4": "gpt-4"
    }
    model = models.get(choice, "claude-3-haiku-20240307")
    
    print(f"\nUsing model: {model}")
    
    try:
        evaluator = PromptEvaluator(model=model)
    except Exception as e:
        print(f"Error initializing evaluator: {e}")
        return
    
    # Get prompt
    print("\nEnter your system prompt (end with empty line):")
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)
    system_prompt = "\n".join(lines)
    
    # Get test inputs
    print("\nEnter test inputs (one per line, empty line to finish):")
    test_cases = []
    idx = 1
    while True:
        test_input = input(f"Test {idx}: ").strip()
        if test_input == "":
            break
        test_cases.append(TestCase(id=f"tc{idx}", input=test_input))
        idx += 1
    
    if not test_cases:
        print("No test cases provided. Exiting.")
        return
    
    # Run evaluation
    print(f"\n⏳ Evaluating {len(test_cases)} test cases...")
    results = evaluator.evaluate_batch(
        test_cases,
        system_prompt,
        "custom",
        progress=True
    )
    
    # Print results
    print("\n📋 Results:")
    for result in results:
        print(f"\n--- Test: {result.test_case_id} ---")
        print(f"Input: {result.input}")
        print(f"Output: {result.output[:200]}...")
        print(f"Latency: {result.latency_ms:.0f}ms | Tokens: {result.tokens_used}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prompt Evaluation Harness")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--demo", "-d", action="store_true", help="Run demo")
    parser.add_argument("--config", "-c", help="Path to config JSON file")
    
    args = parser.parse_args()
    
    if args.demo:
        demo()
    elif args.interactive:
        interactive_mode()
    elif args.config:
        print(f"Loading config from {args.config}...")
        # Config-based evaluation would go here
    else:
        demo()

