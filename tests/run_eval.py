#!/usr/bin/env python3
"""
RAG Evaluation Script
Usage:
  python tests/run_eval.py                          # run all questions
  python tests/run_eval.py --save-baseline          # save this run as baseline
  python tests/run_eval.py --compare                # run and diff against baseline
  python tests/run_eval.py --topic efficiency       # filter by topic
  python tests/run_eval.py --api-url http://localhost:8000
  python tests/run_eval.py --question Q01           # run a single question
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# Force UTF-8 stdout on Windows (cp1252 can't encode the box-drawing chars
# used in the report) — same approach as Pipeline/ingest.py.
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).parent
QUESTIONS_FILE = SCRIPT_DIR / "eval_questions.json"
RESULTS_DIR = SCRIPT_DIR / "results"
BASELINE_FILE = RESULTS_DIR / "baseline.json"
DEFAULT_API_URL = "https://chat.vaughneugenio.com"
TIMEOUT_SECONDS = 30
SLOW_THRESHOLD_MS = 15000  # warn but don't fail
PASS_THRESHOLD = 0.80  # used by CI


def load_questions(topic_filter=None, question_filter=None):
    with open(QUESTIONS_FILE) as f:
        questions = json.load(f)
    if topic_filter:
        questions = [q for q in questions if q["topic"] == topic_filter]
    if question_filter:
        questions = [q for q in questions if q["id"] == question_filter]
    return questions


def call_api(api_url, question):
    url = f"{api_url.rstrip('/')}/api/chat"
    payload = {"question": question, "conversation_history": []}
    start = time.monotonic()
    resp = requests.post(url, json=payload, timeout=TIMEOUT_SECONDS)
    elapsed_ms = int((time.monotonic() - start) * 1000)
    resp.raise_for_status()
    return resp.json(), elapsed_ms


def check_keywords(answer, expected_keywords, min_required):
    answer_lower = answer.lower()
    found = [kw for kw in expected_keywords if kw.lower() in answer_lower]
    missing = [kw for kw in expected_keywords if kw.lower() not in answer_lower]
    passed = len(found) >= min_required
    return passed, found, missing


def check_sources(sources, expected_sources, min_required):
    returned_filenames = {s["filename"] for s in sources}
    found = [s for s in expected_sources if s in returned_filenames]
    missing = [s for s in expected_sources if s not in returned_filenames]
    passed = len(found) >= min_required
    return passed, found, missing


def evaluate_question(q, api_url):
    result = {
        "id": q["id"],
        "question": q["question"],
        "topic": q["topic"],
        "passed": False,
        "error": None,
        "response_ms": None,
        "timeout": False,
        "keyword_check": None,
        "source_check": None,
        "answer_preview": None,
    }

    try:
        data, elapsed_ms = call_api(api_url, q["question"])
    except requests.exceptions.Timeout:
        result["error"] = f"Timeout after {TIMEOUT_SECONDS}s"
        result["timeout"] = True
        return result
    except requests.exceptions.RequestException as e:
        result["error"] = str(e)
        return result

    result["response_ms"] = elapsed_ms
    answer = data.get("answer", "")
    sources = data.get("sources", [])
    result["answer_preview"] = answer[:200]

    kw_passed, kw_found, kw_missing = check_keywords(
        answer, q["expected_keywords"], q["min_keywords_required"]
    )
    src_passed, src_found, src_missing = check_sources(
        sources, q["expected_sources"], q["min_sources_required"]
    )

    result["keyword_check"] = {
        "passed": kw_passed,
        "found": kw_found,
        "missing": kw_missing,
        "required": q["min_keywords_required"],
        "total": len(q["expected_keywords"]),
    }
    result["source_check"] = {
        "passed": src_passed,
        "found": src_found,
        "missing": src_missing,
        "required": q["min_sources_required"],
        "total": len(q["expected_sources"]),
    }

    result["passed"] = kw_passed and src_passed
    return result


def run_eval(questions, api_url):
    results = []
    for i, q in enumerate(questions):
        if i > 0:
            time.sleep(1)  # brief pause to avoid overwhelming the backend
        print(f"  Running {q['id']}...", end="", flush=True)
        r = evaluate_question(q, api_url)
        status = "PASS" if r["passed"] else ("ERROR" if r["error"] else "FAIL")
        print(f" {status}")
        results.append(r)
    return results


def build_summary(results):
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    errors = sum(1 for r in results if r["error"])
    times = [r["response_ms"] for r in results if r["response_ms"] is not None]
    avg_ms = int(sum(times) / len(times)) if times else 0

    by_topic = {}
    for r in results:
        t = r["topic"]
        if t not in by_topic:
            by_topic[t] = {"passed": 0, "total": 0}
        by_topic[t]["total"] += 1
        if r["passed"]:
            by_topic[t]["passed"] += 1

    return {
        "passed": passed,
        "total": total,
        "errors": errors,
        "accuracy": round(passed / total, 4) if total else 0,
        "avg_response_ms": avg_ms,
        "by_topic": by_topic,
    }


def print_report(results, summary, run_at, api_url):
    width = 75
    print()
    print(f"RAG Evaluation Report — {run_at}")
    print(f"API: {api_url}")
    print("─" * width)

    for r in results:
        if r["passed"]:
            status = "\033[32mPASS\033[0m"
        elif r["error"]:
            status = "\033[31mERR \033[0m"
        else:
            status = "\033[31mFAIL\033[0m"

        kw = r["keyword_check"]
        src = r["source_check"]
        slow = r["response_ms"] and r["response_ms"] > SLOW_THRESHOLD_MS
        time_str = f"{r['response_ms']/1000:.1f}s" if r["response_ms"] else "  -  "
        if slow:
            time_str = f"\033[33m{time_str}\033[0m"

        if kw and src:
            detail = (
                f"[{len(kw['found'])}/{kw['total']} keywords"
                f"{'' if kw['passed'] else ' ✗'}"
                f", {len(src['found'])}/{src['total']} sources"
                f"{'' if src['passed'] else ' ✗'}]"
            )
        else:
            detail = ""

        print(f" {r['id']:<4}  {status}  {r['topic']:<14}  {time_str}  {detail}")

        if r["error"]:
            print(f"        Error: {r['error']}")
        elif not r["passed"]:
            if kw and kw["missing"] and not kw["passed"]:
                print(f"        Missing keywords: {', '.join(kw['missing'])}")
            if src and src["missing"] and not src["passed"]:
                print(f"        Missing sources:  {', '.join(src['missing'])}")

    print("─" * width)
    pct = summary["accuracy"] * 100
    print(
        f"Results: {summary['passed']}/{summary['total']} passed ({pct:.1f}%)"
        f"  |  Avg response: {summary['avg_response_ms']}ms"
        + (f"  |  Errors: {summary['errors']}" if summary["errors"] else "")
    )
    print()
    print("By topic:")
    for topic, counts in sorted(summary["by_topic"].items()):
        t_pct = counts["passed"] / counts["total"] * 100
        flag = "  \033[33m← needs attention\033[0m" if t_pct < 75 else ""
        print(f"  {topic:<16}  {counts['passed']}/{counts['total']}  ({t_pct:.0f}%){flag}")
    print()


def save_result(results, summary, run_at, api_url, path):
    RESULTS_DIR.mkdir(exist_ok=True)
    payload = {
        "run_at": run_at,
        "api_url": api_url,
        "summary": summary,
        "questions": results,
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Results saved to {path}")


def print_comparison(current_results, baseline_path):
    if not baseline_path.exists():
        print("No baseline found. Run with --save-baseline first.")
        return

    with open(baseline_path) as f:
        baseline = json.load(f)

    baseline_map = {r["id"]: r for r in baseline["questions"]}
    current_map = {r["id"]: r for r in current_results}

    baseline_acc = baseline["summary"]["accuracy"] * 100
    current_passed = sum(1 for r in current_results if r["passed"])
    current_total = len(current_results)
    current_acc = (current_passed / current_total * 100) if current_total else 0
    delta = current_acc - baseline_acc

    print(f"\nComparing against baseline (saved {baseline['run_at'][:10]})")
    print("─" * 60)

    changed = False
    all_ids = sorted(set(baseline_map) | set(current_map))
    for qid in all_ids:
        b = baseline_map.get(qid)
        c = current_map.get(qid)
        if b is None or c is None:
            continue
        if b["passed"] == c["passed"]:
            continue
        changed = True
        topic = c.get("topic", "")
        if c["passed"] and not b["passed"]:
            arrow = "\033[32mFAIL → PASS\033[0m  ✓ improved"
        else:
            arrow = "\033[31mPASS → FAIL\033[0m  ✗ regressed"
            if c.get("keyword_check") and c["keyword_check"]["missing"]:
                arrow += f"  (missing: {', '.join(c['keyword_check']['missing'])})"
        print(f"  {qid}  {topic:<14}  {arrow}")

    if not changed:
        print("  No changes from baseline.")

    direction = f"\033[32m+{delta:.1f}%\033[0m" if delta >= 0 else f"\033[31m{delta:.1f}%\033[0m"
    print(f"\nOverall: {baseline_acc:.1f}% → {current_acc:.1f}% ({direction})")
    print()


def main():
    parser = argparse.ArgumentParser(description="RAG chatbot evaluation suite")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="Base API URL")
    parser.add_argument("--topic", help="Filter by topic (e.g. efficiency, technical, projects)")
    parser.add_argument("--question", help="Run a single question by ID (e.g. Q01)")
    parser.add_argument("--save-baseline", action="store_true", help="Save this run as baseline")
    parser.add_argument("--compare", action="store_true", help="Compare against saved baseline")
    parser.add_argument("--output", help="Path to save results JSON (optional)")
    args = parser.parse_args()

    questions = load_questions(topic_filter=args.topic, question_filter=args.question)
    if not questions:
        print("No questions matched the given filters.")
        sys.exit(1)

    print(f"\nRunning {len(questions)} question(s) against {args.api_url} ...")
    results = run_eval(questions, args.api_url)

    summary = build_summary(results)
    run_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    print_report(results, summary, run_at, args.api_url)

    if args.compare:
        print_comparison(results, BASELINE_FILE)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    auto_path = RESULTS_DIR / f"run_{timestamp}.json"
    save_result(results, summary, run_at, args.api_url, auto_path)

    if args.save_baseline:
        save_result(results, summary, run_at, args.api_url, BASELINE_FILE)

    if args.output:
        save_result(results, summary, run_at, args.api_url, Path(args.output))

    accuracy = summary["accuracy"]
    if accuracy < PASS_THRESHOLD:
        print(
            f"\033[31mAccuracy {accuracy*100:.1f}% is below threshold {PASS_THRESHOLD*100:.0f}% — CI FAIL\033[0m"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
