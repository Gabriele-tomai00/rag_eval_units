"""
eval_perplexity.py
==================
Evaluates Perplexity answers against ground truth using a local LLM judge.
Answers are read directly from the 'perplexity_answer' field in questions_answares.py.

HOW TO USE:
  1. Fill 'perplexity_answer' in questions_answares.py for each sample.
  2. Run: python eval_perplexity.py
  3. Results are printed to console and saved to evals/experiments/perplexity_results.csv
"""

import os
import re
import csv
import time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

from questions_answares import samples

load_dotenv()

OUTPUT_CSV = Path("evals/experiments/perplexity_results.csv")

# ==============================================================================
# JUDGE
# ==============================================================================

_judge_client = OpenAI(
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("LLM_API_BASE"),
)

JUDGE_SYSTEM_PROMPT = (
    "You are a strict evaluator. Your ONLY task is to output a JSON object. "
    "1. Analyze the Response against the Grading Notes. "
    "2. If the notes are satisfied, result is 'pass', otherwise 'fail'. "
    "3. NEVER write introductory text or reasoning. "
    "4. Output ONLY the JSON object. "
    'Example: {"result": "pass"}'
)

JUDGE_USER_TEMPLATE = (
    "Response: {response}\n"
    "Grading Notes: {grading_notes}\n"
    "Expected Answer: {ground_truth}\n\n"
    "Pass if the response is semantically equivalent to the Expected Answer, "
    "even if phrased differently. Fail only if key facts are wrong.\n"
    'Return JSON: {{"result": "pass"}} or {{"result": "fail"}}'
)


def judge_score(response: str, grading_notes: str, ground_truth: str) -> str:
    """Call the local LLM judge. Returns 'pass', 'fail', or 'error'."""
    prompt = JUDGE_USER_TEMPLATE.format(
        response=response,
        grading_notes=grading_notes,
        ground_truth=ground_truth,
    )
    try:
        completion = _judge_client.chat.completions.create(
            model=os.getenv("MODEL"),
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            **({"response_format": {"type": "json_object"}}
               if os.getenv("USE_JSON_FORMAT", "false").lower() == "true" else {}),
            max_tokens=2048,
            temperature=0.2,
        )
        raw = completion.choices[0].message.content or ""

        # Fallback for reasoning models that put output in reasoning_content
        if not raw.strip():
            msg = completion.choices[0].message
            raw = getattr(msg, "reasoning_content", "") or ""
        match = re.search(r'\{\s*"result"\s*:\s*"(pass|fail)"\s*\}', raw, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        print(f"  [judge] No valid verdict — raw: {repr(raw[:120])}")
        return "error"
    except Exception as e:
        print(f"  [judge] Error: {type(e).__name__}: {e}")
        return "error"


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    total = len(samples)
    missing = [i + 1 for i, s in enumerate(samples) if not s.get("perplexity_answer", "").strip()]
    if missing:
        print(f"[WARNING] {len(missing)} questions still have no perplexity_answer (rows: {missing})\n")

    results = []
    passed = failed = errors = 0

    for i, sample in enumerate(samples, start=1):
        question      = sample["question"]
        grading_notes = sample.get("grading_notes", "")
        ground_truth  = sample.get("ground_truth", "")
        answer        = sample.get("perplexity_answer", "").strip()

        print(f"[{i}/{total}] '{question[:65]}'")

        verdict = judge_score(answer, grading_notes, ground_truth)
        print(f"         -> {verdict.upper()}")
        time.sleep(3)

        if verdict == "pass":   passed += 1
        elif verdict == "fail": failed += 1
        else:                   errors += 1

        results.append({
            "question":          question,
            "ground_truth":      ground_truth,
            "perplexity_answer": answer,
            "judge_result":      verdict,
            "source":            sample.get("source", ""),
        })

    # Save CSV
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["question", "ground_truth", "perplexity_answer", "judge_result", "source"],
        )
        writer.writeheader()
        writer.writerows(results)

    print("\n" + "=" * 50)
    print(f"Results saved to: {OUTPUT_CSV}")
    print(f"  Total : {total}")
    print(f"  Pass  : {passed}  ({passed/total*100:.1f}%)")
    print(f"  Fail  : {failed}  ({failed/total*100:.1f}%)")
    print(f"  Error : {errors}  ({errors/total*100:.1f}%)")
    print("=" * 50)


if __name__ == "__main__":
    main()