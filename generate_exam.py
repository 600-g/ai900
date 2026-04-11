#!/usr/bin/env python3
"""
AI Exam Question Generator
==========================
Uses Claude Code CLI to generate exam questions in Korean.
Outputs properly formatted JSON matching the existing questions.json structure.

Usage:
    python3 generate_exam.py --exam "AI-900" --domain "Machine Learning" --count 10
    python3 generate_exam.py --exam "AZ-104" --domain "Networking" --count 5 --output data/az104.json
    python3 generate_exam.py --exam "AI-900" --domain "Computer Vision" --count 10 --guidebook
    python3 generate_exam.py --exam "AI-900" --domain "NLP" --count 10 --deploy
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

CLAUDE_CLI = "/opt/homebrew/bin/claude"
PROJECT_ROOT = Path(__file__).parent.resolve()
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"

KNOWN_DOMAINS = {
    "AI-900": [
        "AI Workloads",
        "Machine Learning",
        "Computer Vision",
        "NLP",
        "Conversational AI",
        "Responsible AI",
        "Generative AI",
    ],
    "AZ-104": [
        "Identity and Governance",
        "Storage",
        "Compute",
        "Networking",
        "Monitoring",
    ],
    "AWS SAA-C03": [
        "Design Resilient Architectures",
        "Design High-Performing Architectures",
        "Design Secure Architectures",
        "Design Cost-Optimized Architectures",
    ],
}


def build_prompt(exam: str, domain: str, count: int, existing_ids: list[str]) -> str:
    """Build the prompt for Claude CLI to generate exam questions."""
    return f"""You are an expert exam question writer for the {exam} certification exam.

Generate exactly {count} exam practice questions for the domain: "{domain}"

CRITICAL RULES:
1. All questions and options MUST be in Korean.
2. Questions should be at real exam difficulty level.
3. Each question must have exactly 4 options (A, B, C, D).
4. Include a detailed explanation in Korean for each answer.
5. The answer field must be one of "A", "B", "C", "D".
6. Do NOT reuse these existing IDs: {existing_ids[-20:] if existing_ids else []}

Output ONLY a valid JSON array. No markdown fences, no commentary.
Each element must have this exact structure:

[
  {{
    "id": "gen_TIMESTAMP_001",
    "domain": "{domain}",
    "question": "한국어 문제 텍스트",
    "options": {{
      "A": "보기 A 텍스트",
      "B": "보기 B 텍스트",
      "C": "보기 C 텍스트",
      "D": "보기 D 텍스트"
    }},
    "answer": "B",
    "explanation": "한국어 해설 텍스트",
    "has_image": false,
    "source": "ai_generated"
  }}
]

Use the timestamp prefix "gen_{int(time.time())}_" followed by a 3-digit sequence number for IDs.
Generate exactly {count} questions. Output ONLY the JSON array."""


def call_claude(prompt: str) -> str:
    """Call Claude CLI via subprocess and return the response."""
    cmd = [CLAUDE_CLI, "-p", prompt, "--output-format", "text"]
    print(f"  Calling Claude CLI...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        print("  ERROR: Claude CLI timed out after 300 seconds.")
        sys.exit(1)
    except FileNotFoundError:
        print(f"  ERROR: Claude CLI not found at {CLAUDE_CLI}")
        print("  Install Claude Code CLI or update CLAUDE_CLI path.")
        sys.exit(1)

    if result.returncode != 0:
        print(f"  ERROR: Claude CLI exited with code {result.returncode}")
        print(f"  stderr: {result.stderr[:500]}")
        sys.exit(1)

    return result.stdout.strip()


def extract_json_array(text: str) -> list:
    """Extract a JSON array from Claude's response, handling markdown fences."""
    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n?```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()

    # Try direct parse
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Try to find the JSON array in the text
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    print("  ERROR: Could not parse JSON from Claude's response.")
    print(f"  Response preview: {text[:300]}...")
    sys.exit(1)


def validate_questions(questions: list, domain: str) -> list:
    """Validate and fix question format."""
    valid = []
    required_keys = {"id", "domain", "question", "options", "answer", "explanation"}
    valid_answers = {"A", "B", "C", "D"}

    for i, q in enumerate(questions):
        # Check required keys
        missing = required_keys - set(q.keys())
        if missing:
            print(f"  WARNING: Question {i+1} missing keys {missing}, skipping.")
            continue

        # Validate answer
        if q["answer"] not in valid_answers:
            print(f"  WARNING: Question {i+1} has invalid answer '{q['answer']}', skipping.")
            continue

        # Validate options
        if not isinstance(q["options"], dict) or set(q["options"].keys()) != valid_answers:
            print(f"  WARNING: Question {i+1} has invalid options format, skipping.")
            continue

        # Ensure defaults
        q.setdefault("has_image", False)
        q.setdefault("source", "ai_generated")
        q["domain"] = domain  # Enforce the requested domain

        valid.append(q)

    return valid


def load_existing_questions(filepath: Path) -> list:
    """Load existing questions from JSON file."""
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_questions(filepath: Path, questions: list) -> None:
    """Save questions to JSON file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)


def run_deploy() -> None:
    """Run wrangler pages deploy."""
    print("\n--- Deploying with wrangler ---")
    cmd = ["wrangler", "pages", "deploy", ".", "--project-name", "ai900"]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            print("  Deploy successful!")
            print(result.stdout[-300:] if len(result.stdout) > 300 else result.stdout)
        else:
            print(f"  Deploy failed (exit {result.returncode})")
            print(f"  {result.stderr[:500]}")
    except FileNotFoundError:
        print("  ERROR: wrangler not found. Install with: npm install -g wrangler")
    except subprocess.TimeoutExpired:
        print("  ERROR: Deploy timed out.")


def run_guidebook(exam: str, domain: str) -> None:
    """Generate a study guide using the guidebook_generator."""
    from guidebook_generator import generate_guidebook
    generate_guidebook(exam, domain)


def main():
    parser = argparse.ArgumentParser(
        description="Generate exam questions using Claude Code CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 generate_exam.py --exam "AI-900" --domain "Machine Learning" --count 10
  python3 generate_exam.py --exam "AZ-104" --domain "Networking" --count 5 --output data/az104.json
  python3 generate_exam.py --exam "AI-900" --domain "NLP" --count 10 --guidebook
  python3 generate_exam.py --exam "AI-900" --domain "Computer Vision" --count 10 --deploy
  python3 generate_exam.py --list-domains "AI-900"
        """,
    )
    parser.add_argument("--exam", type=str, help="Exam name (e.g., AI-900, AZ-104, AWS SAA-C03)")
    parser.add_argument("--domain", type=str, help="Domain/topic for question generation")
    parser.add_argument("--count", type=int, default=10, help="Number of questions to generate (default: 10)")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file path (default: data/questions.json)",
    )
    parser.add_argument("--guidebook", action="store_true", help="Also generate a study guide for the domain")
    parser.add_argument("--deploy", action="store_true", help="Run wrangler pages deploy after generation")
    parser.add_argument("--list-domains", type=str, metavar="EXAM", help="List known domains for an exam")
    parser.add_argument("--dry-run", action="store_true", help="Show prompt without calling Claude")

    args = parser.parse_args()

    # Handle --list-domains
    if args.list_domains:
        exam = args.list_domains.upper()
        if exam in KNOWN_DOMAINS:
            print(f"\nKnown domains for {exam}:")
            for d in KNOWN_DOMAINS[exam]:
                print(f"  - {d}")
        else:
            print(f"No known domains for '{exam}'. Known exams: {', '.join(KNOWN_DOMAINS.keys())}")
        return

    # Require --exam and --domain for generation
    if not args.exam or not args.domain:
        parser.print_help()
        return

    exam = args.exam.upper()
    domain = args.domain
    count = args.count
    output_path = Path(args.output) if args.output else DEFAULT_DATA_DIR / "questions.json"

    print(f"\n{'='*50}")
    print(f"  Exam Question Generator")
    print(f"{'='*50}")
    print(f"  Exam:     {exam}")
    print(f"  Domain:   {domain}")
    print(f"  Count:    {count}")
    print(f"  Output:   {output_path}")
    print(f"{'='*50}\n")

    # Load existing questions
    existing = load_existing_questions(output_path)
    existing_ids = [q["id"] for q in existing]
    print(f"  Existing questions: {len(existing)}")

    # Build prompt
    prompt = build_prompt(exam, domain, count, existing_ids)

    if args.dry_run:
        print("\n--- DRY RUN: Prompt ---")
        print(prompt)
        return

    # Generate questions
    print(f"\n  Generating {count} questions for {exam} / {domain}...")
    raw_response = call_claude(prompt)

    # Parse and validate
    print("  Parsing response...")
    new_questions = extract_json_array(raw_response)
    print(f"  Parsed {len(new_questions)} questions from response.")

    valid_questions = validate_questions(new_questions, domain)
    print(f"  Validated {len(valid_questions)} questions.")

    if not valid_questions:
        print("  ERROR: No valid questions generated. Exiting.")
        sys.exit(1)

    # Deduplicate IDs
    existing_id_set = set(existing_ids)
    deduped = []
    for q in valid_questions:
        if q["id"] in existing_id_set:
            # Assign a new unique ID
            q["id"] = f"gen_{int(time.time())}_{len(deduped)+1:03d}"
        existing_id_set.add(q["id"])
        deduped.append(q)

    # Append and save
    combined = existing + deduped
    save_questions(output_path, combined)
    print(f"\n  Saved {len(deduped)} new questions. Total: {len(combined)}")
    print(f"  Output: {output_path}")

    # Guidebook
    if args.guidebook:
        print("\n--- Generating Study Guide ---")
        try:
            run_guidebook(exam, domain)
        except ImportError:
            print("  ERROR: guidebook_generator.py not found in project root.")
        except Exception as e:
            print(f"  ERROR generating guidebook: {e}")

    # Deploy
    if args.deploy:
        run_deploy()

    print(f"\n  Done!")


if __name__ == "__main__":
    main()
