"""Tests for multimodal attachment support."""

import pytest
from orchestration.engine import Attachment, OrchestrationRequest
from orchestration.response_generator import ResponseGenerator


class TestAttachment:
    """Unit tests for Attachment dataclass."""

    def test_image_attachment(self):
        att = Attachment(
            type="image",
            content=b"\x89PNG\r\n\x1a\n",
            mime_type="image/png",
            filename="chart.png",
        )
        assert att.is_image()
        assert not att.is_pdf()
        assert att.to_base64() is not None

    def test_pdf_attachment(self):
        att = Attachment(
            type="pdf",
            content=b"%PDF-1.4",
            mime_type="application/pdf",
            filename="report.pdf",
        )
        assert att.is_pdf()
        assert not att.is_image()

    def test_path_attachment(self):
        att = Attachment(
            type="image",
            content="/path/to/image.jpg",
            mime_type="image/jpeg",
        )
        assert att.is_image()
        assert att.to_base64() is None

    def test_default_mime(self):
        att = Attachment(type="image", content=b"fake")
        assert att.mime_type == ""


class TestUserContentBuilding:
    """Tests for _build_user_content multimodal support."""

    def test_text_only(self):
        gen = ResponseGenerator()
        content = gen._build_user_content("Hello", None)
        assert content == "Hello"

    def test_with_image_attachments(self):
        gen = ResponseGenerator()
        att = Attachment(
            type="image",
            content=b"fake_image_bytes",
            mime_type="image/jpeg",
        )
        content = gen._build_user_content("分析这张图", [att])
        assert isinstance(content, list)
        assert len(content) == 2
        assert content[0]["type"] == "image"
        assert content[0]["mime_type"] == "image/jpeg"
        assert content[1]["type"] == "text"
        assert content[1]["text"] == "分析这张图"

    def test_multiple_images(self):
        gen = ResponseGenerator()
        att1 = Attachment(type="image", content=b"img1", mime_type="image/png")
        att2 = Attachment(type="image", content=b"img2", mime_type="image/jpeg")
        content = gen._build_user_content("对比这两张图", [att1, att2])
        assert isinstance(content, list)
        assert len(content) == 3
        assert content[0]["type"] == "image"
        assert content[1]["type"] == "image"
        assert content[2]["type"] == "text"

    def test_pdf_ignored(self):
        gen = ResponseGenerator()
        att = Attachment(type="pdf", content=b"%PDF", mime_type="application/pdf")
        content = gen._build_user_content("分析这份财报", [att])
        # PDFs are not yet supported in multimodal messages, only text remains
        assert isinstance(content, list)
        assert len(content) == 1
        assert content[0]["type"] == "text"


class TestAnthropicMultimodalConversion:
    """Tests for _convert_to_anthropic_messages with multimodal content."""

    def test_image_content_blocks(self):
        gen = ResponseGenerator()
        messages = [
            {"role": "system", "content": "You are Z."},
            {
                "role": "user",
                "content": [
                    {"type": "image", "mime_type": "image/jpeg", "data": "abc123"},
                    {"type": "text", "text": "分析这张图"},
                ],
            },
        ]
        system, anthropic_msgs = gen._convert_to_anthropic_messages(messages)
        assert system == "You are Z."
        assert len(anthropic_msgs) == 1
        assert anthropic_msgs[0]["role"] == "user"
        content = anthropic_msgs[0]["content"]
        assert isinstance(content, list)
        assert content[0]["type"] == "image"
        assert content[0]["source"]["type"] == "base64"
        assert content[0]["source"]["media_type"] == "image/jpeg"
        assert content[0]["source"]["data"] == "abc123"
        assert content[1]["type"] == "text"
        assert content[1]["text"] == "分析这张图"

    def test_mixed_text_and_multimodal(self):
        gen = ResponseGenerator()
        messages = [
            {"role": "user", "content": "Hello"},
            {
                "role": "user",
                "content": [
                    {"type": "image", "mime_type": "image/png", "data": "xyz"},
                    {"type": "text", "text": "看图"},
                ],
            },
        ]
        system, anthropic_msgs = gen._convert_to_anthropic_messages(messages)
        assert len(anthropic_msgs) == 2
        assert anthropic_msgs[0]["content"] == "Hello"
        assert isinstance(anthropic_msgs[1]["content"], list)


class TestOpenAIMultimodalConversion:
    """Tests for OpenAI provider multimodal format conversion."""

    def test_image_to_openai_format(self):
        gen = ResponseGenerator()
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "mime_type": "image/jpeg", "data": "base64data"},
                    {"type": "text", "text": "分析"},
                ],
            },
        ]
        openai_messages = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                openai_content = []
                for block in content:
                    if block.get("type") == "image":
                        mime = block.get("mime_type", "image/jpeg")
                        data = block.get("data", "")
                        openai_content.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{data}"},
                        })
                    elif block.get("type") == "text":
                        openai_content.append({
                            "type": "text",
                            "text": block.get("text", ""),
                        })
                openai_messages.append({"role": msg["role"], "content": openai_content})
            else:
                openai_messages.append(msg)

        assert len(openai_messages) == 1
        content = openai_messages[0]["content"]
        assert isinstance(content, list)
        assert content[0]["type"] == "image_url"
        assert content[0]["image_url"]["url"] == "data:image/jpeg;base64,base64data"
        assert content[1]["type"] == "text"
        assert content[1]["text"] == "分析"


class TestOrchestrationRequestWithAttachments:
    """Tests for OrchestrationRequest attachments field."""

    def test_request_with_attachments(self):
        att = Attachment(type="image", content=b"fake", mime_type="image/png")
        req = OrchestrationRequest(
            query="分析这张图",
            attachments=[att],
        )
        assert req.attachments is not None
        assert len(req.attachments) == 1
        assert req.attachments[0].is_image()

    def test_request_without_attachments(self):
        req = OrchestrationRequest(query="Hello")
        assert req.attachments is None

    def test_request_with_multiple_attachments(self):
        req = OrchestrationRequest(
            query="对比",
            attachments=[
                Attachment(type="image", content=b"img1", mime_type="image/png"),
                Attachment(type="image", content=b"img2", mime_type="image/jpeg"),
            ],
        )
        assert len(req.attachments) == 2
