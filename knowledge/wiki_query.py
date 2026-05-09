"""Non-vectorized wiki knowledge query — keyword + tag matching.

Scans wiki directories for markdown files with YAML frontmatter,
builds an in-memory keyword index, and retrieves relevant pages
by matching query keywords against file names and tags.

No embeddings, no vector DB. Pure keyword matching.
"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional

import yaml


@dataclass
class WikiPage:
    """A single wiki page with metadata."""
    title: str = ""
    filepath: str = ""
    tags: list[str] = field(default_factory=list)
    content: str = ""
    summary: str = ""


class WikiKnowledgeQuery:
    """Query wiki knowledge by keyword matching (no vectors)."""

    def __init__(self, wiki_dirs: list[str] | None = None):
        """Initialize with wiki directory paths.

        Args:
            wiki_dirs: List of directories to scan for .md wiki pages.
                       Defaults to paths from registry/wiki.yaml (public + personal).
        """
        if wiki_dirs is None:
            from shared.config import get_wiki_dirs
            wiki_dirs = get_wiki_dirs()
        self.wiki_dirs = [d for d in wiki_dirs if os.path.exists(d)]
        self._pages: list[WikiPage] = []
        self._index: dict[str, list[WikiPage]] = {}  # keyword -> pages
        self._build_index()

    # ------------------------------------------------------------------ #
    #  Index building
    # ------------------------------------------------------------------ #

    def _build_index(self) -> None:
        """Scan all wiki directories and build keyword index."""
        for wiki_dir in self.wiki_dirs:
            for root, _dirs, files in os.walk(wiki_dir):
                for filename in files:
                    if not filename.endswith(".md"):
                        continue
                    filepath = os.path.join(root, filename)
                    page = self._parse_page(filepath, filename)
                    if page.title or page.tags:
                        self._pages.append(page)
                        self._add_to_index(page)

    def _parse_page(self, filepath: str, filename: str) -> WikiPage:
        """Parse a markdown file: extract YAML frontmatter and content summary."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw = f.read()
        except Exception:
            return WikiPage()

        # Extract YAML frontmatter
        title = ""
        tags: list[str] = []
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1])
                    if isinstance(frontmatter, dict):
                        title = frontmatter.get("title", "")
                        tags_raw = frontmatter.get("tags", [])
                        if isinstance(tags_raw, list):
                            tags = [str(t) for t in tags_raw]
                        elif isinstance(tags_raw, str):
                            tags = [tags_raw]
                except Exception:
                    pass
                content = parts[2]
            else:
                content = raw
        else:
            content = raw

        # Derive title from filename if not in frontmatter
        if not title:
            title = os.path.splitext(filename)[0]

        # Extract summary: first paragraph after frontmatter
        summary = self._extract_summary(content)

        return WikiPage(
            title=title,
            filepath=filepath,
            tags=tags,
            content=content,
            summary=summary,
        )

    def _extract_summary(self, content: str) -> str:
        """Extract first meaningful paragraph as summary."""
        # Remove mermaid blocks
        content = re.sub(r"```mermaid.*?```", "", content, flags=re.DOTALL)
        # Remove code blocks
        content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
        # Remove callout blocks
        content = re.sub(r"> \[!.*?\].*?(?=\n\n|\Z)", "", content, flags=re.DOTALL)
        # Find first non-empty line
        for line in content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("-"):
                return line[:300]
        return ""

    def _add_to_index(self, page: WikiPage) -> None:
        """Add page to keyword index."""
        keywords: set[str] = set()

        # From title
        if page.title:
            keywords.update(self._extract_keywords(page.title))

        # From tags
        for tag in page.tags:
            keywords.update(self._extract_keywords(tag))

        # From filename (stem only, no path)
        stem = os.path.splitext(os.path.basename(page.filepath))[0]
        keywords.update(self._extract_keywords(stem))

        for kw in keywords:
            if kw not in self._index:
                self._index[kw] = []
            self._index[kw].append(page)

    def _extract_keywords(self, text: str) -> set[str]:
        """Extract searchable keywords from text."""
        # Split by common separators, keep Chinese and alphanumeric
        tokens = re.findall(r"[一-鿿]+|[a-zA-Z0-9]+", text)
        result: set[str] = set()
        for t in tokens:
            t = t.lower()
            # Alphanumeric: keep as-is if >= 2 chars
            if t.isascii():
                if len(t) >= 2:
                    result.add(t)
                continue
            # Chinese: sliding window 2-4 chars for substring matching
            n = len(t)
            if n == 1:
                result.add(t)
            else:
                for window in range(2, 5):
                    for i in range(n - window + 1):
                        result.add(t[i:i + window])
        return result

    # ------------------------------------------------------------------ #
    #  Query interface
    # ------------------------------------------------------------------ #

    def query(self, query_text: str, max_results: int = 3) -> list[WikiPage]:
        """Query wiki pages by keyword matching.

        Args:
            query_text: User query string
            max_results: Max number of pages to return

        Returns:
            List of matching WikiPage objects, ordered by relevance score
        """
        query_kws = self._extract_keywords(query_text)
        if not query_kws:
            return []

        scores: dict[str, tuple[int, WikiPage]] = {}  # filepath -> (score, page)

        for kw in query_kws:
            for page in self._index.get(kw, []):
                fp = page.filepath
                if fp not in scores:
                    scores[fp] = (0, page)
                # Increase score for each matching keyword
                scores[fp] = (scores[fp][0] + 1, page)

                # Bonus for tag match vs title/filename match
                for tag in page.tags:
                    if kw in self._extract_keywords(tag):
                        scores[fp] = (scores[fp][0] + 2, page)

        # Sort by score descending
        ranked = sorted(scores.values(), key=lambda x: x[0], reverse=True)
        return [page for _score, page in ranked[:max_results]]

    def query_to_context(self, query_text: str, max_results: int = 3) -> str:
        """Query wiki and format results as LLM context string.

        Returns empty string if no matches.
        """
        pages = self.query(query_text, max_results)
        if not pages:
            return ""

        lines: list[str] = ["## 相关知识库片段", ""]
        for i, page in enumerate(pages, 1):
            lines.append(f"### [{i}] {page.title}")
            if page.tags:
                lines.append(f"*标签: {', '.join(page.tags)}*")
            if page.summary:
                lines.append(page.summary)
            # Include more content if available
            content_preview = self._get_content_preview(page.content)
            if content_preview:
                lines.append(content_preview)
            lines.append("")

        return "\n".join(lines)

    def _get_content_preview(self, content: str, max_chars: int = 800) -> str:
        """Get a preview of page content (excluding frontmatter)."""
        # Remove YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2]

        # Remove mermaid
        content = re.sub(r"```mermaid.*?```", "", content, flags=re.DOTALL)

        # Extract bullet points and key paragraphs
        lines: list[str] = []
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                lines.append(line)
            elif line.startswith("-") and "**" in line:
                lines.append(line)
            elif line.startswith(">") and "[!" in line:
                lines.append(line)
            if sum(len(l) for l in lines) > max_chars:
                break

        return "\n".join(lines[:30])

    # ------------------------------------------------------------------ #
    #  Stats / Debug
    # ------------------------------------------------------------------ #

    def stats(self) -> dict:
        """Return index statistics."""
        return {
            "pages_indexed": len(self._pages),
            "keywords": len(self._index),
            "directories": self.wiki_dirs,
        }
