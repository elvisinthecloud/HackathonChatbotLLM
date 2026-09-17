#!/usr/bin/env python3
"""Build the sanitized live-conversation validation PDF."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Frame,
    HRFlowable,
    PageBreakIfNotEmpty,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "docs" / "live-conversation-validation.json"
DEFAULT_OUTPUT = ROOT / "output" / "pdf" / "mcele-live-conversations.pdf"

NAVY = colors.HexColor("#142B4A")
BLUE = colors.HexColor("#1F5C8F")
TEAL = colors.HexColor("#168582")
INK = colors.HexColor("#1D2733")
MUTED = colors.HexColor("#5D6B78")
LINE = colors.HexColor("#D7E0E8")
PALE_BLUE = colors.HexColor("#EEF5FA")
PALE_TEAL = colors.HexColor("#EAF6F5")
AMBER = colors.HexColor("#9B5C00")
PALE_AMBER = colors.HexColor("#FFF5DC")

REQUIRED_TOP = {"tested_at_utc", "release_id", "public_url", "conversations", "summary"}
REQUIRED_CONVERSATION = {"title", "profile", "turns"}
REQUIRED_TURN = {
    "message",
    "answer",
    "response_kind",
    "retrieved_count",
    "sources",
    "trace_id",
    "observations",
    "passed",
    "checks",
}
SECRET_KEY = re.compile(r"(?:password|passwd|secret|api[_-]?key|access[_-]?token|session[_-]?token|cookie)", re.I)


def _register_fonts() -> tuple[str, str, str]:
    candidates = [
        (
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial Italic.ttf"),
        ),
        (
            Path("/System/Library/Fonts/Supplemental/Verdana.ttf"),
            Path("/System/Library/Fonts/Supplemental/Verdana Bold.ttf"),
            Path("/System/Library/Fonts/Supplemental/Verdana Italic.ttf"),
        ),
    ]
    for regular, bold, italic in candidates:
        if all(path.exists() for path in (regular, bold, italic)):
            pdfmetrics.registerFont(TTFont("ReportSans", str(regular)))
            pdfmetrics.registerFont(TTFont("ReportSans-Bold", str(bold)))
            pdfmetrics.registerFont(TTFont("ReportSans-Italic", str(italic)))
            pdfmetrics.registerFontFamily(
                "ReportSans",
                normal="ReportSans",
                bold="ReportSans-Bold",
                italic="ReportSans-Italic",
                boldItalic="ReportSans-Bold",
            )
            return "ReportSans", "ReportSans-Bold", "ReportSans-Italic"
    return "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"


FONT, FONT_BOLD, FONT_ITALIC = _register_fonts()


def _validate_no_secret_keys(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if SECRET_KEY.search(str(key)):
                raise ValueError(f"credential-like field is not allowed: {path}.{key}")
            _validate_no_secret_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_no_secret_keys(child, f"{path}[{index}]")


def _require_keys(record: dict[str, Any], required: set[str], label: str) -> None:
    missing = required - record.keys()
    if missing:
        raise ValueError(f"{label} is missing fields: {', '.join(sorted(missing))}")


def load_and_validate(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("top-level JSON must be an object")
    _require_keys(data, REQUIRED_TOP, "report")
    _validate_no_secret_keys(data)

    conversations = data["conversations"]
    if not isinstance(conversations, list) or len(conversations) != 2:
        raise ValueError("report requires exactly two conversations")
    for c_index, conversation in enumerate(conversations, 1):
        if not isinstance(conversation, dict):
            raise ValueError(f"conversation {c_index} must be an object")
        _require_keys(conversation, REQUIRED_CONVERSATION, f"conversation {c_index}")
        turns = conversation["turns"]
        if not isinstance(turns, list) or len(turns) < 2:
            raise ValueError(f"conversation {c_index} must contain at least two turns")
        for t_index, turn in enumerate(turns, 1):
            if not isinstance(turn, dict):
                raise ValueError(f"conversation {c_index}, turn {t_index} must be an object")
            _require_keys(turn, REQUIRED_TURN, f"conversation {c_index}, turn {t_index}")
            for name in ("message", "answer", "response_kind", "trace_id"):
                if not isinstance(turn[name], str):
                    raise ValueError(f"conversation {c_index}, turn {t_index}: {name} must be text")
            for name in ("sources", "observations", "checks"):
                if not isinstance(turn[name], list) or not all(isinstance(item, str) for item in turn[name]):
                    raise ValueError(f"conversation {c_index}, turn {t_index}: {name} must be a text list")
            if not isinstance(turn["retrieved_count"], int) or isinstance(turn["retrieved_count"], bool):
                raise ValueError(f"conversation {c_index}, turn {t_index}: retrieved_count must be an integer")
            if not isinstance(turn["passed"], bool):
                raise ValueError(f"conversation {c_index}, turn {t_index}: passed must be boolean")
            if "content_review" in turn and not isinstance(turn["content_review"], str):
                raise ValueError(f"conversation {c_index}, turn {t_index}: content_review must be text")
    return data


def exact_markup(value: Any) -> str:
    """Escape user-provided text while preserving explicit line breaks and tabs."""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")
    return "<br/>".join(escape(line) if line else "&#160;" for line in text.split("\n"))


def label_markup(label: str, value: Any) -> str:
    return f'<font name="{FONT_BOLD}" color="#5D6B78">{escape(label)}:</font> {exact_markup(value)}'


def _format_timestamp(value: Any) -> str:
    raw = str(value)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except ValueError:
        return raw


def _friendly_key(key: str) -> str:
    return key.replace("_", " ").strip().capitalize()


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle", parent=base["Title"], fontName=FONT_BOLD, fontSize=25,
            leading=29, textColor=NAVY, alignment=TA_LEFT, spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle", parent=base["Normal"], fontName=FONT, fontSize=10.2,
            leading=15, textColor=MUTED, spaceAfter=16,
        ),
        "section": ParagraphStyle(
            "Section", parent=base["Heading1"], fontName=FONT_BOLD, fontSize=15,
            leading=19, textColor=NAVY, spaceBefore=8, spaceAfter=8,
        ),
        "conversation": ParagraphStyle(
            "Conversation", parent=base["Heading1"], fontName=FONT_BOLD, fontSize=17,
            leading=21, textColor=NAVY, spaceAfter=4,
        ),
        "turn": ParagraphStyle(
            "Turn", parent=base["Heading2"], fontName=FONT_BOLD, fontSize=11.5,
            leading=15, textColor=BLUE, spaceBefore=2, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontName=FONT, fontSize=9.2,
            leading=13.4, textColor=INK, spaceAfter=6, wordWrap="CJK",
        ),
        "small": ParagraphStyle(
            "Small", parent=base["BodyText"], fontName=FONT, fontSize=7.8,
            leading=11, textColor=MUTED, spaceAfter=3, wordWrap="CJK",
        ),
        "meta": ParagraphStyle(
            "Meta", parent=base["BodyText"], fontName=FONT, fontSize=8.2,
            leading=11.4, textColor=INK, wordWrap="CJK",
        ),
        "user_label": ParagraphStyle(
            "UserLabel", parent=base["BodyText"], fontName=FONT_BOLD, fontSize=7.6,
            leading=10, textColor=BLUE, spaceAfter=3,
        ),
        "answer_label": ParagraphStyle(
            "AnswerLabel", parent=base["BodyText"], fontName=FONT_BOLD, fontSize=7.6,
            leading=10, textColor=TEAL, spaceBefore=7, spaceAfter=3,
        ),
        "transcript": ParagraphStyle(
            "Transcript", parent=base["BodyText"], fontName=FONT, fontSize=9.1,
            leading=13.3, textColor=INK, wordWrap="CJK", splitLongWords=True,
            borderWidth=0.45, borderColor=LINE, borderPadding=9,
            spaceBefore=2, spaceAfter=4,
        ),
        "callout": ParagraphStyle(
            "Callout", parent=base["BodyText"], fontName=FONT, fontSize=8.8,
            leading=13, textColor=NAVY, wordWrap="CJK",
        ),
        "warning": ParagraphStyle(
            "Warning", parent=base["BodyText"], fontName=FONT, fontSize=8.8,
            leading=13, textColor=INK, wordWrap="CJK", backColor=PALE_AMBER,
            borderColor=AMBER, borderWidth=0.7, borderPadding=9,
            spaceBefore=4, spaceAfter=8,
        ),
        "footer": ParagraphStyle(
            "Footer", parent=base["BodyText"], fontName=FONT, fontSize=7.5,
            leading=9, textColor=MUTED,
        ),
    }


def _page(canvas: Any, doc: Any) -> None:
    canvas.saveState()
    width, height = letter
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, 0.52 * inch, width - doc.rightMargin, 0.52 * inch)
    canvas.setFont(FONT, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, 0.31 * inch, "MCeLE live conversation validation")
    canvas.drawRightString(width - doc.rightMargin, 0.31 * inch, f"Page {doc.page}")
    if doc.page > 1:
        canvas.setFillColor(NAVY)
        canvas.setFont(FONT_BOLD, 7.5)
        canvas.drawString(doc.leftMargin, height - 0.4 * inch, "LIVE API VALIDATION REPORT")
    canvas.restoreState()


def _info_table(rows: list[tuple[str, Any]], styles: dict[str, ParagraphStyle]) -> Table:
    data = [
        [Paragraph(escape(label), styles["small"]), Paragraph(exact_markup(value), styles["meta"])]
        for label, value in rows
    ]
    table = Table(data, colWidths=[1.25 * inch, 5.35 * inch], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), PALE_BLUE),
        ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _transcript_box(label: str, text: str, styles: dict[str, ParagraphStyle], answer: bool = False) -> Paragraph:
    # A Paragraph can split across page boundaries, unlike a single-cell Table.
    # This is essential for long model answers: nothing is clipped or omitted.
    style = ParagraphStyle(
        "AnswerTranscript" if answer else "UserTranscript",
        parent=styles["transcript"],
        backColor=PALE_TEAL if answer else PALE_BLUE,
    )
    label_color = "#168582" if answer else "#1F5C8F"
    markup = (
        f'<font name="{FONT_BOLD}" size="7.6" color="{label_color}">{escape(label)}</font><br/>'
        f'{exact_markup(text)}'
    )
    return Paragraph(markup, style)


def _join_or_none(items: list[str]) -> str:
    return ", ".join(items) if items else "None"


def _summary_rows(summary: Any) -> list[tuple[str, Any]]:
    if not isinstance(summary, dict):
        return [("Summary", summary)]
    rows: list[tuple[str, Any]] = []
    for key, value in summary.items():
        if key in {"limitations", "manual_review"}:
            continue
        if isinstance(value, bool):
            shown = "Pass" if value else "Fail"
        elif isinstance(value, list):
            shown = ", ".join(str(item) for item in value) if value else "None"
        elif isinstance(value, dict):
            parts = []
            for child_key, child_value in value.items():
                if isinstance(child_value, bool):
                    child_value = "Pass" if child_value else "Fail"
                parts.append(f"{_friendly_key(str(child_key))}: {child_value}")
            shown = "; ".join(parts)
        else:
            shown = value
        rows.append((_friendly_key(str(key)), shown))
    return rows or [("Summary", "No aggregate fields supplied")]


def build_report(data: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = build_styles()
    doc = BaseDocTemplate(
        str(output), pagesize=letter,
        leftMargin=0.7 * inch, rightMargin=0.7 * inch,
        topMargin=0.65 * inch, bottomMargin=0.68 * inch,
        title="MCeLE Live Conversation Validation",
        author="MCeLE Demo Team",
        subject="Sanitized evidence from two live API conversations",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="report")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_page)])

    story: list[Any] = []
    story.extend([
        Paragraph("MCeLE Live Conversation Validation", styles["title"]),
        Paragraph(
            "Two actual, multi-turn conversations executed against the isolated demo API. "
            "This report presents the sanitized transcript and the recorded retrieval and model evidence for each turn.",
            styles["subtitle"],
        ),
        _info_table([
            ("Tested", _format_timestamp(data["tested_at_utc"])),
            ("Release", data["release_id"]),
            ("Public endpoint", data["public_url"]),
            ("Execution channel", data.get("test_method", "Live HTTP API validation")),
            ("Conversation count", len(data["conversations"])),
        ], styles),
        Spacer(1, 13),
        Paragraph("Result summary", styles["section"]),
        _info_table(_summary_rows(data["summary"]), styles),
        Paragraph(
            f'<font name="{FONT_BOLD}" color="#9B5C00">CONTENT-GROUNDING REVIEW: CONCERN FOUND</font><br/>'
            f'{exact_markup(data["summary"].get("manual_review", "Content review did not pass."))}',
            styles["warning"],
        ),
        Paragraph(
            f'<font name="{FONT_BOLD}">Recorded limitations.</font> '
            f'{exact_markup(data["summary"].get("limitations", "None recorded."))}',
            styles["callout"],
        ),
        Spacer(1, 13),
        Table(
            [[Paragraph(
                '<font name="%s"><b>Evidence interpretation.</b> A turn demonstrates retrieval when its observation list records '
                '<b>embed_text</b>, <b>vector_search</b>, and/or <b>article_candidate_search</b>. It demonstrates model '
                'generation when the list records <b>ollama_chat</b>. Source IDs are the permitted article records returned '
                'for that turn; the retrieval count is reported independently.</font>' % FONT,
                styles["callout"],
            )]],
            colWidths=[6.6 * inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
                ("BOX", (0, 0), (-1, -1), 0.6, BLUE),
                ("LEFTPADDING", (0, 0), (-1, -1), 11),
                ("RIGHTPADDING", (0, 0), (-1, -1), 11),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]),
        ),
    ])

    for c_index, conversation in enumerate(data["conversations"], 1):
        story.append(PageBreakIfNotEmpty())
        story.append(Paragraph(f"Conversation {c_index}: {exact_markup(conversation['title'])}", styles["conversation"]))
        story.append(Paragraph(label_markup("Profile", conversation["profile"]), styles["body"]))
        story.append(HRFlowable(width="100%", thickness=1.0, color=TEAL, spaceBefore=3, spaceAfter=10))

        for t_index, turn in enumerate(conversation["turns"], 1):
            status = "ROUTING/CHECKS PASS" if turn["passed"] else "ROUTING/CHECKS FAIL"
            status_color = "#168582" if turn["passed"] else "#B33A3A"
            story.extend([
                CondPageBreak(1.45 * inch),
                Paragraph(
                    f'Turn {t_index} &nbsp; <font color="{status_color}">{status}</font>',
                    styles["turn"],
                ),
                _transcript_box("USER MESSAGE - VERBATIM", turn["message"], styles),
                Spacer(1, 4),
                _transcript_box("ASSISTANT ANSWER - VERBATIM", turn["answer"], styles, answer=True),
                Spacer(1, 7),
            ])
            if turn.get("content_review"):
                story.append(Paragraph(
                    f'<font name="{FONT_BOLD}" color="#9B5C00">CONTENT REVIEW WARNING</font><br/>'
                    f'{exact_markup(turn["content_review"])}',
                    styles["warning"],
                ))
            evidence_rows = [
                ("Response kind", turn["response_kind"]),
                ("Retrieved", turn["retrieved_count"]),
                ("Source IDs", _join_or_none(turn["sources"])),
                ("Trace ID", turn["trace_id"]),
                ("Observed spans", _join_or_none(turn["observations"])),
                ("Checks", " | ".join(turn["checks"]) if turn["checks"] else "None recorded"),
            ]
            if turn.get("failures"):
                evidence_rows.append(("Check failures", " | ".join(turn["failures"])))
            story.extend([
                _info_table([
                    *evidence_rows,
                ], styles),
            ])
            if t_index != len(conversation["turns"]):
                story.append(Spacer(1, 11))
                story.append(HRFlowable(width="100%", thickness=0.45, color=LINE, spaceAfter=10))

    story.extend([
        PageBreakIfNotEmpty(),
        Paragraph("Scope and limitations", styles["section"]),
        Paragraph(
            "These are actual live API exchanges captured during validation of the identified release. "
            "They are not browser-driven sessions, so this report does not validate visual presentation, browser state, "
            "or front-end interaction behavior. The evidence is limited to the two profiles, prompts, follow-up turns, "
            "source IDs, checks, and trace observations recorded in the sanitized input.",
            styles["body"],
        ),
        Paragraph(
            "The report includes trace identifiers for correlation but contains no credentials or session tokens. "
            "Observation names show that instrumented operations were recorded; detailed Langfuse payloads and model internals "
            "are outside this artifact. Pass/fail labels reproduce the validation record and should be interpreted with the "
            "per-turn routing/check labels shown alongside each transcript. Those labels do not certify that every generated "
            "statement is grounded in a retrieved article.",
            styles["body"],
        ),
        Paragraph(
            f'<font name="{FONT_BOLD}" color="#9B5C00">Known content and resolver limitations</font><br/>'
            f'{exact_markup(data["summary"].get("manual_review", "None recorded."))}<br/><br/>'
            f'{exact_markup(data["summary"].get("limitations", "None recorded."))}',
            styles["warning"],
        ),
        Spacer(1, 8),
        HRFlowable(width="100%", thickness=1.0, color=TEAL, spaceAfter=10),
        Paragraph(
            f'<font name="{FONT_BOLD}">Artifact basis</font><br/>'
            f'Sanitized validation record: docs/live-conversation-validation.json<br/>'
            f'Release: {exact_markup(data["release_id"])}<br/>'
            f'Test time: {exact_markup(_format_timestamp(data["tested_at_utc"]))}',
            styles["small"],
        ),
    ])
    doc.build(story)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    data = load_and_validate(args.input)
    build_report(data, args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
