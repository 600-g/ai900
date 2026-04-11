#!/usr/bin/env python3
"""
Guidebook Generator
===================
Uses Claude Code CLI to generate comprehensive study guides for certification exams.
Outputs both Markdown and HTML files.

Usage:
    python3 guidebook_generator.py --exam "AI-900" --domain "Machine Learning"
    python3 guidebook_generator.py --exam "AI-900" --domain "all"
    python3 guidebook_generator.py --exam "AZ-104" --domain "Networking" --output-dir guides/
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

CLAUDE_CLI = "/opt/homebrew/bin/claude"
PROJECT_ROOT = Path(__file__).parent.resolve()
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "guides"

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


def build_guidebook_prompt(exam: str, domain: str) -> str:
    """Build the prompt for generating a study guide."""
    return f"""You are an expert instructor for the {exam} certification exam.

Generate a comprehensive study guide for the domain: "{domain}"

The guide MUST be written in Korean and include ALL of the following sections:

# {exam} 학습 가이드: {domain}

## 1. 핵심 개념 (Key Concepts)
- Each concept with a clear definition and real-world example
- Use bullet points and sub-sections for clarity
- Cover ALL testable concepts in this domain

## 2. 시험 함정 포인트 (Common Exam Traps)
- List at least 8 common mistakes and misconceptions
- Format: "함정: ... / 정답: ..." for each trap
- Include WHY students get confused

## 3. 실전 시나리오 (Practice Scenarios)
- 5 scenario-based questions with detailed walkthroughs
- Show the thinking process for arriving at the correct answer
- Include "이 시나리오에서 주의할 점" for each

## 4. 빠른 참조 표 (Quick Reference Tables)
- Comparison tables for similar services/concepts
- Feature matrix tables
- Decision flowcharts (described in text)

## 5. 서비스/기능 비교 (Service Comparisons)
- Side-by-side comparison of related Azure services
- When to use each service
- Key differentiators

## 6. 시험 팁 (Exam Tips)
- Time management strategies
- Question-reading strategies
- How to eliminate wrong answers

## 7. 핵심 용어 사전 (Glossary)
- Key terms with Korean definitions
- Include English terms in parentheses

Output the guide in clean Markdown format. Use proper heading levels, tables, and formatting.
Do NOT wrap in code fences. Output the Markdown content directly."""


def call_claude(prompt: str) -> str:
    """Call Claude CLI via subprocess."""
    cmd = [CLAUDE_CLI, "-p", prompt, "--output-format", "text"]
    print(f"  Calling Claude CLI for guidebook generation...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        print("  ERROR: Claude CLI timed out after 600 seconds.")
        sys.exit(1)
    except FileNotFoundError:
        print(f"  ERROR: Claude CLI not found at {CLAUDE_CLI}")
        sys.exit(1)

    if result.returncode != 0:
        print(f"  ERROR: Claude CLI exited with code {result.returncode}")
        print(f"  stderr: {result.stderr[:500]}")
        sys.exit(1)

    return result.stdout.strip()


def clean_markdown(text: str) -> str:
    """Clean up the markdown output from Claude."""
    # Remove leading/trailing code fences if present
    text = re.sub(r"^```(?:markdown)?\s*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n?```\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


def markdown_to_html(markdown_content: str, exam: str, domain: str) -> str:
    """Convert markdown to a styled HTML page."""
    # Escape HTML in content, then apply markdown transformations
    html_body = markdown_content

    # Convert markdown headers
    html_body = re.sub(r"^#### (.+)$", r"<h4>\1</h4>", html_body, flags=re.MULTILINE)
    html_body = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html_body, flags=re.MULTILINE)
    html_body = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html_body, flags=re.MULTILINE)
    html_body = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html_body, flags=re.MULTILINE)

    # Convert bold and italic
    html_body = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html_body)
    html_body = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html_body)

    # Convert inline code
    html_body = re.sub(r"`([^`]+)`", r"<code>\1</code>", html_body)

    # Convert markdown tables to HTML tables
    html_body = convert_tables(html_body)

    # Convert bullet lists (simple conversion)
    lines = html_body.split("\n")
    result_lines = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- "):
            if not in_list:
                result_lines.append("<ul>")
                in_list = True
            result_lines.append(f"  <li>{stripped[2:]}</li>")
        else:
            if in_list:
                result_lines.append("</ul>")
                in_list = False
            if stripped and not stripped.startswith("<"):
                result_lines.append(f"<p>{stripped}</p>")
            else:
                result_lines.append(line)
    if in_list:
        result_lines.append("</ul>")

    html_body = "\n".join(result_lines)

    safe_domain = domain.replace(" ", "-").lower()

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{exam} 학습 가이드: {domain}</title>
    <style>
        :root {{
            --bg: #0f172a;
            --card: #1e293b;
            --text: #e2e8f0;
            --accent: #38bdf8;
            --accent2: #818cf8;
            --border: #334155;
            --success: #34d399;
            --warning: #fbbf24;
            --danger: #f87171;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.7;
            padding: 2rem;
            max-width: 900px;
            margin: 0 auto;
        }}
        h1 {{
            color: var(--accent);
            font-size: 1.8rem;
            margin: 2rem 0 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--accent);
        }}
        h2 {{
            color: var(--accent2);
            font-size: 1.4rem;
            margin: 1.5rem 0 0.8rem;
        }}
        h3 {{
            color: var(--success);
            font-size: 1.15rem;
            margin: 1.2rem 0 0.5rem;
        }}
        h4 {{
            color: var(--warning);
            font-size: 1rem;
            margin: 1rem 0 0.4rem;
        }}
        p {{ margin: 0.5rem 0; }}
        ul {{
            margin: 0.5rem 0 0.5rem 1.5rem;
        }}
        li {{ margin: 0.3rem 0; }}
        code {{
            background: var(--card);
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            font-size: 0.9em;
            color: var(--accent);
        }}
        strong {{ color: var(--warning); }}
        em {{ color: var(--accent); font-style: italic; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            background: var(--card);
            border-radius: 8px;
            overflow: hidden;
        }}
        th {{
            background: var(--border);
            color: var(--accent);
            padding: 0.6rem 1rem;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 0.5rem 1rem;
            border-top: 1px solid var(--border);
        }}
        tr:hover td {{ background: rgba(56, 189, 248, 0.05); }}
        .back-link {{
            display: inline-block;
            margin-bottom: 1rem;
            color: var(--accent);
            text-decoration: none;
        }}
        .back-link:hover {{ text-decoration: underline; }}
        @media (max-width: 640px) {{
            body {{ padding: 1rem; }}
            h1 {{ font-size: 1.4rem; }}
            table {{ font-size: 0.85rem; }}
        }}
    </style>
</head>
<body>
    <a href="../index.html" class="back-link">&larr; Back to Quiz</a>
    {html_body}
</body>
</html>"""


def convert_tables(text: str) -> str:
    """Convert markdown tables to HTML tables."""
    lines = text.split("\n")
    result = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Detect a table: line starts with | and has multiple |
        if line.startswith("|") and line.count("|") >= 3:
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1

            if len(table_lines) >= 2:
                result.append(build_html_table(table_lines))
            else:
                result.extend(table_lines)
        else:
            result.append(lines[i])
            i += 1

    return "\n".join(result)


def build_html_table(table_lines: list[str]) -> str:
    """Build an HTML table from markdown table lines."""

    def parse_row(line: str) -> list[str]:
        cells = line.strip().strip("|").split("|")
        return [c.strip() for c in cells]

    rows = []
    for line in table_lines:
        stripped = line.strip()
        # Skip separator rows like |---|---|
        if re.match(r"^\|[\s\-:|]+\|$", stripped):
            continue
        rows.append(parse_row(stripped))

    if not rows:
        return ""

    html = "<table>\n"
    # First row as header
    html += "  <thead><tr>"
    for cell in rows[0]:
        html += f"<th>{cell}</th>"
    html += "</tr></thead>\n"

    # Remaining rows as body
    if len(rows) > 1:
        html += "  <tbody>\n"
        for row in rows[1:]:
            html += "    <tr>"
            for cell in row:
                html += f"<td>{cell}</td>"
            html += "</tr>\n"
        html += "  </tbody>\n"

    html += "</table>"
    return html


def generate_guidebook(exam: str, domain: str, output_dir: Path = None) -> None:
    """Generate a guidebook for a specific exam domain."""
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    safe_exam = exam.replace(" ", "-").lower()
    safe_domain = domain.replace(" ", "-").lower()
    base_name = f"{safe_exam}_{safe_domain}"

    md_path = output_dir / f"{base_name}.md"
    html_path = output_dir / f"{base_name}.html"

    print(f"\n  Generating guidebook: {exam} / {domain}")

    prompt = build_guidebook_prompt(exam, domain)
    raw = call_claude(prompt)
    content = clean_markdown(raw)

    # Save Markdown
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Saved Markdown: {md_path}")

    # Save HTML
    html_content = markdown_to_html(content, exam, domain)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"  Saved HTML:     {html_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate comprehensive study guides using Claude Code CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 guidebook_generator.py --exam "AI-900" --domain "Machine Learning"
  python3 guidebook_generator.py --exam "AI-900" --domain "all"
  python3 guidebook_generator.py --exam "AZ-104" --domain "Networking" --output-dir guides/
  python3 guidebook_generator.py --list-domains "AI-900"
        """,
    )
    parser.add_argument("--exam", type=str, help="Exam name (e.g., AI-900, AZ-104)")
    parser.add_argument("--domain", type=str, help='Domain/topic (or "all" for all domains)')
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (default: guides/)",
    )
    parser.add_argument("--list-domains", type=str, metavar="EXAM", help="List known domains for an exam")

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

    if not args.exam or not args.domain:
        parser.print_help()
        return

    exam = args.exam.upper()
    domain = args.domain
    output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR

    print(f"\n{'='*50}")
    print(f"  Guidebook Generator")
    print(f"{'='*50}")
    print(f"  Exam:       {exam}")
    print(f"  Domain:     {domain}")
    print(f"  Output dir: {output_dir}")
    print(f"{'='*50}")

    if domain.lower() == "all":
        domains = KNOWN_DOMAINS.get(exam)
        if not domains:
            print(f"  No known domains for '{exam}'. Use --domain with a specific topic.")
            return
        for d in domains:
            generate_guidebook(exam, d, output_dir)
    else:
        generate_guidebook(exam, domain, output_dir)

    print(f"\n  All guidebooks generated!")


if __name__ == "__main__":
    main()
