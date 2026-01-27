#!/usr/bin/env python3
"""
LLM-as-Judge Evaluator

Uses a stronger LLM (judge) to evaluate outputs from other models on multiple dimensions.

Usage:
    python llm-as-judge-evaluator.py --config eval_config.json
    python llm-as-judge-evaluator.py --interactive
    python llm-as-judge-evaluator.py --input test_cases.json --output results.json

Requirements:
    pip install openai anthropic pandas tqdm
"""

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
import time
import sys

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

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


@dataclass
class TestCase:
    """A test case with input and model output to evaluate."""
    id: str
    input: str
    output: str  # The output from the model being evaluated
    expected_output: Optional[str] = None
    category: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class EvaluationResult:
    """Result of LLM-as-judge evaluation."""
    test_case_id: str
    input: str
    output: str
    expected_output: Optional[str]
    scores: Dict[str, float]  # Dimension -> score
    reasoning: Dict[str, str]  # Dimension -> explanation
    overall_score: Optional[float] = None
    judge_model: str
    timestamp: str
    latency_ms: float
    tokens_used: int


class LLMJudge:
    """LLM-as-judge evaluator using a stronger model."""
    
    # Default evaluation dimensions
    DEFAULT_DIMENSIONS = {
        "accuracy": "Is the output factually correct and accurate?",
        "relevance": "Does the output address the input/question?",
        "completeness": "Does the output cover all required aspects?",
        "coherence": "Is the output well-organized and logical?",
        "fluency": "Is the output grammatically correct and natural?",
    }
    
    def __init__(
        self,
        judge_model: str = "claude-3-sonnet-20240229",
        dimensions: Optional[Dict[str, str]] = None,
        scale: int = 5,
        temperature: float = 0.0
    ):
        """
        Initialize the LLM judge.
        
        Args:
            judge_model: Model to use as judge (e.g., "claude-3-sonnet-20240229", "gpt-4")
            dimensions: Custom evaluation dimensions {name: description}
            scale: Scoring scale (1-5, 1-10, etc.)
            temperature: Temperature for judge model (lower = more consistent)
        """
        self.judge_model = judge_model
        self.dimensions = dimensions or self.DEFAULT_DIMENSIONS
        self.scale = scale
        self.temperature = temperature
        
        # Initialize client based on model
        if "claude" in judge_model.lower():
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("anthropic package required. Run: pip install anthropic")
            self.client = anthropic.Anthropic()
            self.provider = "anthropic"
        elif "gpt" in judge_model.lower():
            if not OPENAI_AVAILABLE:
                raise ImportError("openai package required. Run: pip install openai")
            self.client = openai.OpenAI()
            self.provider = "openai"
        else:
            raise ValueError(f"Unsupported judge model: {judge_model}")
    
    def _call_judge(self, prompt: str) -> tuple:
        """Call the judge model and return (response, latency_ms, tokens)."""
        start_time = time.time()
        
        try:
            if self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.judge_model,
                    max_tokens=2048,
                    temperature=self.temperature,
                    messages=[{"role": "user", "content": prompt}]
                )
                output = response.content[0].text
                tokens = response.usage.input_tokens + response.usage.output_tokens
                
            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.judge_model,
                    temperature=self.temperature,
                    messages=[{"role": "user", "content": prompt}]
                )
                output = response.choices[0].message.content
                tokens = response.usage.total_tokens
            
            latency_ms = (time.time() - start_time) * 1000
            return output, latency_ms, tokens
            
        except Exception as e:
            raise RuntimeError(f"Error calling judge model: {e}")
    
    def _build_evaluation_prompt(
        self,
        test_case: TestCase,
        include_expected: bool = False
    ) -> str:
        """Build the evaluation prompt for the judge."""
        
        prompt_parts = [
            f"You are an expert evaluator assessing the quality of AI-generated outputs.",
            f"",
            f"## Evaluation Task",
            f"Evaluate the following output on a scale of 1-{self.scale} for each dimension.",
            f"",
            f"## Input:",
            f"{test_case.input}",
            f"",
            f"## Output to Evaluate:",
            f"{test_case.output}",
        ]
        
        if include_expected and test_case.expected_output:
            prompt_parts.extend([
                f"",
                f"## Expected Output (for reference):",
                f"{test_case.expected_output}",
            ])
        
        prompt_parts.extend([
            f"",
            f"## Evaluation Dimensions:",
        ])
        
        for i, (dim_name, dim_desc) in enumerate(self.dimensions.items(), 1):
            prompt_parts.append(f"{i}. **{dim_name}**: {dim_desc}")
        
        prompt_parts.extend([
            f"",
            f"## Instructions:",
            f"1. Score each dimension from 1-{self.scale} (where {self.scale} is excellent, 1 is poor)",
            f"2. Provide brief reasoning for each score",
            f"3. Calculate an overall score (weighted average or your judgment)",
            f"",
            f"## Output Format (JSON):",
            f"{{",
            f'  "scores": {{',
        ])
        
        for dim_name in self.dimensions.keys():
            prompt_parts.append(f'    "{dim_name}": <score 1-{self.scale}>,')
        
        prompt_parts.extend([
            f'    "overall": <overall score 1-{self.scale}>',
            f"  }},",
            f'  "reasoning": {{',
        ])
        
        for dim_name in self.dimensions.keys():
            prompt_parts.append(f'    "{dim_name}": "<brief explanation>",')
        
        prompt_parts.extend([
            f'    "overall": "<overall assessment>"',
            f"  }}",
            f"}}",
            f"",
            f"Provide your evaluation as valid JSON:",
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_judge_response(self, response: str) -> Dict[str, Any]:
        """Parse the judge's JSON response."""
        try:
            # Try to extract JSON from response
            response = response.strip()
            
            # Find JSON block if wrapped in markdown
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end].strip()
            
            # Parse JSON
            result = json.loads(response)
            
            # Validate structure
            if "scores" not in result:
                raise ValueError("Missing 'scores' in response")
            if "reasoning" not in result:
                raise ValueError("Missing 'reasoning' in response")
            
            return result
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from judge response: {e}")
        except Exception as e:
            raise ValueError(f"Error parsing judge response: {e}")
    
    def evaluate(
        self,
        test_case: TestCase,
        include_expected: bool = False
    ) -> EvaluationResult:
        """
        Evaluate a single test case.
        
        Args:
            test_case: Test case to evaluate
            include_expected: Whether to include expected output in prompt
        
        Returns:
            EvaluationResult with scores and reasoning
        """
        prompt = self._build_evaluation_prompt(test_case, include_expected)
        
        response_text, latency_ms, tokens = self._call_judge(prompt)
        
        try:
            parsed = self._parse_judge_response(response_text)
        except ValueError as e:
            # Fallback: return error scores
            print(f"Warning: Failed to parse judge response for {test_case.id}: {e}")
            parsed = {
                "scores": {dim: 0.0 for dim in self.dimensions.keys()},
                "reasoning": {dim: f"Parse error: {str(e)}" for dim in self.dimensions.keys()}
            }
        
        scores = parsed.get("scores", {})
        reasoning = parsed.get("reasoning", {})
        overall_score = scores.get("overall")
        
        # Ensure all dimensions are scored
        for dim in self.dimensions.keys():
            if dim not in scores:
                scores[dim] = 0.0
            if dim not in reasoning:
                reasoning[dim] = "No reasoning provided"
        
        return EvaluationResult(
            test_case_id=test_case.id,
            input=test_case.input,
            output=test_case.output,
            expected_output=test_case.expected_output,
            scores=scores,
            reasoning=reasoning,
            overall_score=overall_score,
            judge_model=self.judge_model,
            timestamp=datetime.now().isoformat(),
            latency_ms=latency_ms,
            tokens_used=tokens
        )
    
    def evaluate_batch(
        self,
        test_cases: List[TestCase],
        include_expected: bool = False,
        progress: bool = True
    ) -> List[EvaluationResult]:
        """
        Evaluate a batch of test cases.
        
        Args:
            test_cases: List of test cases to evaluate
            include_expected: Whether to include expected outputs
            progress: Show progress bar
        
        Returns:
            List of evaluation results
        """
        results = []
        iterator = test_cases
        
        if progress and TQDM_AVAILABLE:
            iterator = tqdm(test_cases, desc="Evaluating", unit="case")
        
        for case in iterator:
            try:
                result = self.evaluate(case, include_expected)
                results.append(result)
            except Exception as e:
                print(f"\nError evaluating {case.id}: {e}", file=sys.stderr)
                # Create error result
                error_result = EvaluationResult(
                    test_case_id=case.id,
                    input=case.input,
                    output=case.output,
                    expected_output=case.expected_output,
                    scores={dim: 0.0 for dim in self.dimensions.keys()},
                    reasoning={dim: f"Error: {str(e)}" for dim in self.dimensions.keys()},
                    overall_score=0.0,
                    judge_model=self.judge_model,
                    timestamp=datetime.now().isoformat(),
                    latency_ms=0.0,
                    tokens_used=0
                )
                results.append(error_result)
        
        return results
    
    def compare_outputs(
        self,
        test_cases: List[TestCase],
        outputs_a: Dict[str, str],
        outputs_b: Dict[str, str],
        label_a: str = "Version A",
        label_b: str = "Version B"
    ) -> Dict[str, Any]:
        """
        Compare two sets of outputs on the same test cases.
        
        Args:
            test_cases: Test cases
            outputs_a: Dict of {test_case_id: output} for version A
            outputs_b: Dict of {test_case_id: output} for version B
            label_a: Label for version A
            label_b: Label for version B
        
        Returns:
            Comparison results with statistics
        """
        # Create test cases for each version
        cases_a = [
            TestCase(
                id=f"{tc.id}_a",
                input=tc.input,
                output=outputs_a.get(tc.id, ""),
                expected_output=tc.expected_output,
                category=tc.category
            )
            for tc in test_cases
        ]
        
        cases_b = [
            TestCase(
                id=f"{tc.id}_b",
                input=tc.input,
                output=outputs_b.get(tc.id, ""),
                expected_output=tc.expected_output,
                category=tc.category
            )
            for tc in test_cases
        ]
        
        # Evaluate both
        print(f"Evaluating {label_a}...")
        results_a = self.evaluate_batch(cases_a)
        
        print(f"Evaluating {label_b}...")
        results_b = self.evaluate_batch(cases_b)
        
        # Calculate statistics
        stats_a = self._calculate_stats(results_a)
        stats_b = self._calculate_stats(results_b)
        
        # Compare
        comparison = {
            label_a: stats_a,
            label_b: stats_b,
            "comparison": {}
        }
        
        for dim in self.dimensions.keys():
            avg_a = stats_a["avg_scores"].get(dim, 0)
            avg_b = stats_b["avg_scores"].get(dim, 0)
            diff = avg_b - avg_a
            comparison["comparison"][dim] = {
                f"{label_a}_avg": avg_a,
                f"{label_b}_avg": avg_b,
                "difference": diff,
                "winner": label_b if diff > 0.1 else (label_a if diff < -0.1 else "tie")
            }
        
        return comparison
    
    def _calculate_stats(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """Calculate statistics from evaluation results."""
        if not results:
            return {}
        
        # Aggregate scores by dimension
        dim_scores = {dim: [] for dim in self.dimensions.keys()}
        overall_scores = []
        latencies = []
        tokens = []
        
        for result in results:
            for dim, score in result.scores.items():
                if dim != "overall" and isinstance(score, (int, float)):
                    dim_scores[dim].append(score)
            if result.overall_score:
                overall_scores.append(result.overall_score)
            latencies.append(result.latency_ms)
            tokens.append(result.tokens_used)
        
        avg_scores = {
            dim: sum(scores) / len(scores) if scores else 0.0
            for dim, scores in dim_scores.items()
        }
        
        return {
            "count": len(results),
            "avg_scores": avg_scores,
            "avg_overall": sum(overall_scores) / len(overall_scores) if overall_scores else 0.0,
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0.0,
            "total_tokens": sum(tokens),
            "avg_tokens": sum(tokens) / len(tokens) if tokens else 0.0,
        }


def load_test_cases(filepath: str) -> List[TestCase]:
    """Load test cases from JSON file."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    if isinstance(data, list):
        return [TestCase(**item) if isinstance(item, dict) else item for item in data]
    elif isinstance(data, dict) and "test_cases" in data:
        return [TestCase(**item) for item in data["test_cases"]]
    else:
        raise ValueError("Invalid test case file format")


def save_results(results: List[EvaluationResult], filepath: str):
    """Save evaluation results to file."""
    results_data = [asdict(r) for r in results]
    
    if filepath.endswith(".json"):
        with open(filepath, 'w') as f:
            json.dump(results_data, f, indent=2)
    elif filepath.endswith(".csv") and PANDAS_AVAILABLE:
        # Flatten for CSV
        rows = []
        for r in results:
            row = {
                "test_case_id": r.test_case_id,
                "input": r.input,
                "output": r.output,
                "overall_score": r.overall_score,
                "judge_model": r.judge_model,
                "latency_ms": r.latency_ms,
                "tokens_used": r.tokens_used,
                "timestamp": r.timestamp,
            }
            # Add dimension scores
            for dim, score in r.scores.items():
                if dim != "overall":
                    row[f"score_{dim}"] = score
            rows.append(row)
        
        df = pd.DataFrame(rows)
        df.to_csv(filepath, index=False)
    else:
        raise ValueError(f"Unsupported file format: {filepath}")


def print_summary(results: List[EvaluationResult], judge: LLMJudge):
    """Print a formatted summary of evaluation results."""
    if not results:
        print("No results to summarize.")
        return
    
    stats = judge._calculate_stats(results)
    
    print("\n" + "=" * 70)
    print("📊 LLM-AS-JUDGE EVALUATION SUMMARY")
    print("=" * 70)
    
    print(f"\n📋 OVERVIEW:")
    print(f"   • Test cases evaluated: {stats['count']}")
    print(f"   • Judge model: {judge.judge_model}")
    print(f"   • Average latency: {stats['avg_latency_ms']:.0f}ms")
    print(f"   • Total tokens used: {stats['total_tokens']:,}")
    
    print(f"\n📈 SCORES BY DIMENSION:")
    for dim, avg_score in stats['avg_scores'].items():
        bar_length = int(avg_score / judge.scale * 20)
        bar = "█" * bar_length + "░" * (20 - bar_length)
        print(f"   • {dim:15s}: {avg_score:.2f}/{judge.scale} {bar}")
    
    if stats['avg_overall'] > 0:
        print(f"\n🎯 OVERALL SCORE: {stats['avg_overall']:.2f}/{judge.scale}")
    
    print("\n" + "=" * 70)


def interactive_mode():
    """Run in interactive mode."""
    print("\n🧪 LLM-as-Judge Evaluator")
    print("=" * 50)
    
    # Get judge model
    print("\nSelect judge model:")
    print("1. claude-3-sonnet-20240229 (recommended)")
    print("2. claude-3-opus-20240229 (highest quality)")
    print("3. gpt-4 (OpenAI)")
    print("4. gpt-4-turbo (OpenAI, faster)")
    
    choice = input("\nSelect (1-4, default 1): ").strip() or "1"
    models = {
        "1": "claude-3-sonnet-20240229",
        "2": "claude-3-opus-20240229",
        "3": "gpt-4",
        "4": "gpt-4-turbo"
    }
    judge_model = models.get(choice, "claude-3-sonnet-20240229")
    
    # Get test case file
    test_file = input("\nPath to test cases JSON file: ").strip()
    if not test_file or not Path(test_file).exists():
        print("Invalid file path. Exiting.")
        return
    
    try:
        test_cases = load_test_cases(test_file)
        print(f"Loaded {len(test_cases)} test cases")
    except Exception as e:
        print(f"Error loading test cases: {e}")
        return
    
    # Initialize judge
    try:
        judge = LLMJudge(judge_model=judge_model)
    except Exception as e:
        print(f"Error initializing judge: {e}")
        return
    
    # Run evaluation
    print(f"\n⏳ Evaluating with {judge_model}...")
    results = judge.evaluate_batch(test_cases, progress=True)
    
    # Print summary
    print_summary(results, judge)
    
    # Save results
    save_choice = input("\nSave results? (y/n): ").strip().lower()
    if save_choice == 'y':
        output_file = input("Output file path (default: results.json): ").strip() or "results.json"
        try:
            save_results(results, output_file)
            print(f"Results saved to {output_file}")
        except Exception as e:
            print(f"Error saving results: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="LLM-as-Judge Evaluator for AI outputs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python llm-as-judge-evaluator.py --interactive
  
  # Evaluate from JSON file
  python llm-as-judge-evaluator.py --input test_cases.json --output results.json
  
  # Use specific judge model
  python llm-as-judge-evaluator.py --input test.json --judge gpt-4
        """
    )
    
    parser.add_argument("--input", "-i", help="Input test cases JSON file")
    parser.add_argument("--output", "-o", help="Output results file (JSON or CSV)")
    parser.add_argument("--judge", "-j", default="claude-3-sonnet-20240229",
                       help="Judge model to use")
    parser.add_argument("--interactive", action="store_true",
                       help="Run in interactive mode")
    parser.add_argument("--config", "-c", help="Config JSON file")
    parser.add_argument("--scale", type=int, default=5,
                       help="Scoring scale (default: 5)")
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
    elif args.input:
        try:
            test_cases = load_test_cases(args.input)
            judge = LLMJudge(judge_model=args.judge, scale=args.scale)
            
            print(f"Evaluating {len(test_cases)} test cases with {args.judge}...")
            results = judge.evaluate_batch(test_cases, progress=True)
            
            print_summary(results, judge)
            
            if args.output:
                save_results(results, args.output)
                print(f"\nResults saved to {args.output}")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
