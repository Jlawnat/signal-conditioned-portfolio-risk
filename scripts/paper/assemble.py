"""Assemble the eight section drafts into a unified manuscript."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"
FILES = [
    "01_TITLE_ABSTRACT.md", "02_INTRODUCTION.md", "03_LITERATURE_REVIEW.md",
    "04_DATA_METHODOLOGY.md", "05_EMPIRICAL_RESULTS.md", "06_DISCUSSION.md",
    "07_LIMITATIONS.md", "08_CONCLUSION.md",
]

if __name__ == "__main__":
    parts = [(PAPER / name).read_text().strip() for name in FILES]
    (PAPER / "MANUSCRIPT_DRAFT_V1.md").write_text("\n\n---\n\n".join(parts) + "\n")
    print(f"Assembled {len(FILES)} sections")
