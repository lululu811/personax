"""Tests for non-vectorized wiki knowledge query."""

import os
import tempfile

import pytest


class TestWikiKnowledgeQuery:
    def test_init_scans_directories(self):
        from knowledge.wiki_query import WikiKnowledgeQuery
        wq = WikiKnowledgeQuery()
        stats = wq.stats()
        assert stats["pages_indexed"] > 0
        assert stats["keywords"] > 0
        assert len(stats["directories"]) > 0

    def test_query_by_keyword(self):
        from knowledge.wiki_query import WikiKnowledgeQuery
        wq = WikiKnowledgeQuery()
        results = wq.query("半导体")
        assert len(results) >= 1
        assert any("半导体" in r.title for r in results)

    def test_query_by_tag(self):
        from knowledge.wiki_query import WikiKnowledgeQuery
        wq = WikiKnowledgeQuery()
        # "固态电池" is in tags of the 固态电池 page
        results = wq.query("固态电池")
        assert len(results) >= 1
        titles = [r.title for r in results]
        assert any("固态电池" in t for t in titles)

    def test_query_no_match(self):
        from knowledge.wiki_query import WikiKnowledgeQuery
        wq = WikiKnowledgeQuery()
        results = wq.query("黹黻黼黽鼯鼱鼷qwerty12345")
        assert len(results) == 0

    def test_query_to_context(self):
        from knowledge.wiki_query import WikiKnowledgeQuery
        wq = WikiKnowledgeQuery()
        context = wq.query_to_context("半导体", max_results=1)
        assert "半导体" in context or "相关知识库" in context
        assert "## 相关知识库片段" in context

    def test_query_to_context_no_match(self):
        from knowledge.wiki_query import WikiKnowledgeQuery
        wq = WikiKnowledgeQuery()
        context = wq.query_to_context("黹黻黼黽qwerty12345")
        assert context == ""

    def test_parse_page_with_frontmatter(self, tmp_path):
        from knowledge.wiki_query import WikiKnowledgeQuery
        md_file = tmp_path / "测试页面.md"
        md_file.write_text(
            "---\ntitle: 测试标题\ntags: [tag1, tag2]\n---\n\n这是内容摘要。\n\n更多内容。",
            encoding="utf-8",
        )
        wq = WikiKnowledgeQuery(wiki_dirs=[str(tmp_path)])
        page = wq._parse_page(str(md_file), "测试页面.md")
        assert page.title == "测试标题"
        assert "tag1" in page.tags
        assert "tag2" in page.tags
        assert "这是内容摘要" in page.summary

    def test_parse_page_without_frontmatter(self, tmp_path):
        from knowledge.wiki_query import WikiKnowledgeQuery
        md_file = tmp_path / "无标题.md"
        md_file.write_text("直接开始的内容。\n\n第二段。", encoding="utf-8")
        wq = WikiKnowledgeQuery(wiki_dirs=[str(tmp_path)])
        page = wq._parse_page(str(md_file), "无标题.md")
        assert page.title == "无标题"  # Derived from filename
        assert "直接开始的内容" in page.summary

    def test_extract_keywords(self):
        from knowledge.wiki_query import WikiKnowledgeQuery
        wq = WikiKnowledgeQuery(wiki_dirs=[])
        kws = wq._extract_keywords("半导体-AI产业链")
        assert "半导体" in kws
        assert "产业链" in kws

    def test_score_ranking(self, tmp_path):
        from knowledge.wiki_query import WikiKnowledgeQuery
        # Create two pages
        (tmp_path / "page1.md").write_text(
            "---\ntitle: 半导体芯片\ntags: [半导体, 芯片]\n---\n\n内容1",
            encoding="utf-8",
        )
        (tmp_path / "page2.md").write_text(
            "---\ntitle: 新能源汽车\ntags: [新能源, 汽车]\n---\n\n内容2",
            encoding="utf-8",
        )
        wq = WikiKnowledgeQuery(wiki_dirs=[str(tmp_path)])
        results = wq.query("半导体", max_results=2)
        assert len(results) >= 1
        # 半导体 page should rank first
        assert "半导体" in results[0].title
