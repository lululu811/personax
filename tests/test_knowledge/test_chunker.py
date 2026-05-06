from knowledge.chunker import MarkdownChunker


def test_split_by_headings():
    text = """# Title

Intro paragraph.

## Section 1

Content of section 1.

## Section 2

Content of section 2.
"""
    chunker = MarkdownChunker()
    chunks = chunker.split_text(text, "test.md")

    assert len(chunks) >= 2
    assert chunks[0].heading_path == "Title"
    assert "Intro paragraph" in chunks[0].content
    assert chunks[1].heading_path == "Title > Section 1"
    assert "Content of section 1" in chunks[1].content


def test_preserve_hierarchy():
    text = """# A
## B
### C
Content.
"""
    chunker = MarkdownChunker()
    chunks = chunker.split_text(text)

    paths = [c.heading_path for c in chunks]
    assert any("A > B > C" in p for p in paths)


def test_split_oversized():
    text = "# Title\n\n" + "word " * 600
    chunker = MarkdownChunker(max_size=500)
    chunks = chunker.split_text(text)

    for chunk in chunks:
        assert len(chunk.content) <= 500
