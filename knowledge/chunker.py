import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Chunk:
    content: str
    source_file: str
    heading_path: str
    start_line: int
    end_line: int


class MarkdownChunker:
    def __init__(self, max_size: int = 1000, preserve_hierarchy: bool = True):
        self.max_size = max_size
        self.preserve_hierarchy = preserve_hierarchy

    def split_file(self, file_path: Path) -> list[Chunk]:
        content = file_path.read_text(encoding="utf-8")
        return self.split_text(content, str(file_path))

    def split_text(self, text: str, source_file: str = "") -> list[Chunk]:
        lines = text.split("\n")
        chunks = []
        current_heading_path = ""
        current_lines = []
        current_start = 0

        for i, line in enumerate(lines):
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)

            if heading_match:
                # Save previous chunk
                if current_lines:
                    chunk_text = "\n".join(current_lines).strip()
                    if chunk_text:
                        chunks.append(Chunk(
                            content=chunk_text,
                            source_file=source_file,
                            heading_path=current_heading_path,
                            start_line=current_start,
                            end_line=i - 1,
                        ))

                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()

                # Update heading path
                if self.preserve_hierarchy:
                    parts = current_heading_path.split(" > ") if current_heading_path else []
                    parts = parts[:level - 1] + [title]
                    current_heading_path = " > ".join(parts)
                else:
                    current_heading_path = title

                current_lines = [line]
                current_start = i
            else:
                current_lines.append(line)

        # Save final chunk
        if current_lines:
            chunk_text = "\n".join(current_lines).strip()
            if chunk_text:
                chunks.append(Chunk(
                    content=chunk_text,
                    source_file=source_file,
                    heading_path=current_heading_path,
                    start_line=current_start,
                    end_line=len(lines) - 1,
                ))

        # Split oversized chunks
        return self._split_oversized(chunks)

    def _split_oversized(self, chunks: list[Chunk]) -> list[Chunk]:
        result = []
        for chunk in chunks:
            if len(chunk.content) <= self.max_size:
                result.append(chunk)
                continue

            # Split by paragraphs
            paragraphs = chunk.content.split("\n\n")
            current = ""
            current_start = chunk.start_line

            for para in paragraphs:
                # If a single paragraph exceeds max_size, split by words
                if len(para) > self.max_size:
                    if current:
                        result.append(Chunk(
                            content=current.strip(),
                            source_file=chunk.source_file,
                            heading_path=chunk.heading_path,
                            start_line=current_start,
                            end_line=chunk.end_line,
                        ))
                        current = ""

                    words = para.split(" ")
                    sub_current = ""
                    for word in words:
                        if len(sub_current) + len(word) + 1 > self.max_size and sub_current:
                            result.append(Chunk(
                                content=sub_current.strip(),
                                source_file=chunk.source_file,
                                heading_path=chunk.heading_path,
                                start_line=current_start,
                                end_line=chunk.end_line,
                            ))
                            sub_current = word
                        else:
                            sub_current = (sub_current + " " + word).strip() if sub_current else word

                    if sub_current:
                        result.append(Chunk(
                            content=sub_current.strip(),
                            source_file=chunk.source_file,
                            heading_path=chunk.heading_path,
                            start_line=current_start,
                            end_line=chunk.end_line,
                        ))
                    continue

                if len(current) + len(para) + 2 > self.max_size and current:
                    result.append(Chunk(
                        content=current.strip(),
                        source_file=chunk.source_file,
                        heading_path=chunk.heading_path,
                        start_line=current_start,
                        end_line=chunk.end_line,
                    ))
                    current = para
                else:
                    current = (current + "\n\n" + para).strip() if current else para

            if current:
                result.append(Chunk(
                    content=current.strip(),
                    source_file=chunk.source_file,
                    heading_path=chunk.heading_path,
                    start_line=current_start,
                    end_line=chunk.end_line,
                ))
        return result
