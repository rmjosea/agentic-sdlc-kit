"""Parse the strict v2 Markdown/frontmatter contract without filesystem I/O.

``parse_markdown`` accepts UTF-8 bytes or Unicode text, an explicit metadata-key
allowlist, and optionally a metadata schema from :mod:`scripts.contracts.schema`.
It returns the exact normalized model consumed by later v2 contracts. Template
mode accepts only caller-declared angle-bracket tokens; rendered mode rejects all
such tokens.

The syntax layer extracts ``**REQ-N**:``, ``**AC-N**:``, and
``### TASK-N: title`` declarations and rejects duplicates. Plain ID-leading prose
is never a declaration. Fenced code and conservative CommonMark HTML blocks are
masked in one bounded pass before all structural extraction. It intentionally
leaves malformed markers,
unqualified references, lifecycle policy, and cross-document resolution to the
later semantic layer; no owner lifecycle is implemented here.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from typing import Any, Collection, Iterable, Mapping, Optional

from scripts.contracts import schema


KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
H1_RE = re.compile(r"^#[ \t]+(.+?)$")
ANY_H1_RE = re.compile(r"^#(?:[ \t]+|$)")
HEADING_RE = re.compile(r"^#{2,6}[ \t]+(.+?)$")
LOCAL_ID_RE = re.compile(
    r"^(?=(?:\*\*|###[ \t]+)((?:REQ|AC|TASK)-[0-9]+))"
    r"(?:\*\*(?:REQ|AC)-[0-9]+\*\*:|###[ \t]+TASK-[0-9]+:[ \t]+\S)"
)
REFERENCE_RE = re.compile(
    r"(?<![A-Z0-9-])"
    r"[A-Z]+-[0-9]+(?:-[A-Z]+-[0-9]+)?#(?:REQ|AC|TASK)-[0-9]+"
    r"(?![A-Z0-9-])|"
    r"(?<![A-Z0-9#-])(?:REQ|AC|TASK)-[0-9]+(?![A-Z0-9-])"
)
DECLARATION_SPAN_RE = re.compile(
    r"^(?:\*\*(?:REQ|AC)-[0-9]+\*\*:|###[ \t]+TASK-[0-9]+:)"
)
PLACEHOLDER_RE = re.compile(r"<[^<>\r\n]+>")
AUTOLINK_RE = re.compile(
    r"(?:[A-Za-z][A-Za-z0-9+.-]{1,31}:[^<>\s]*|"
    r"[^<>\s@]+@[^<>\s@]+\.[^<>\s@]+)"
)
HTML_TAGS = frozenset({
    "a", "abbr", "address", "area", "article", "aside", "audio", "b", "base",
    "basefont", "bdi", "bdo", "big", "blockquote", "body", "br", "button",
    "canvas", "caption", "center", "cite", "code", "col", "colgroup", "data",
    "datalist", "dd", "del", "details", "dfn", "dialog", "div", "dl", "dt",
    "em", "embed", "fieldset", "figcaption", "figure", "font", "footer", "form",
    "h1", "h2", "h3", "h4", "h5", "h6", "head", "header", "hr", "html",
    "i", "iframe", "img", "input", "ins", "kbd", "label", "legend", "li",
    "link", "main", "map", "mark", "menu", "meta", "meter", "nav", "noscript",
    "object", "ol", "optgroup", "option", "output", "p", "picture", "portal",
    "pre", "progress", "q", "rp", "rt", "ruby", "s", "samp", "script",
    "search", "section", "select", "slot", "small", "source", "span", "strike",
    "strong", "style", "sub", "summary", "sup", "table", "tbody", "td",
    "template", "textarea", "tfoot", "th", "thead", "time", "title", "tr",
    "track", "tt", "u", "ul", "var", "video", "wbr",
})
RAW_BLOCK_TAGS = frozenset({"pre", "script", "style", "textarea"})
BLOCK_TAGS = frozenset({
    "address", "article", "aside", "base", "basefont", "blockquote", "body",
    "caption", "center", "col", "colgroup", "dd", "details", "dialog", "dir",
    "div", "dl", "dt", "fieldset", "figcaption", "figure", "footer", "form",
    "frame", "frameset", "h1", "h2", "h3", "h4", "h5", "h6", "head",
    "header", "hr", "html", "iframe", "legend", "li", "link", "main", "math",
    "menu", "menuitem", "nav", "noframes", "ol", "optgroup", "option", "p",
    "param", "search", "section", "summary", "svg", "table", "tbody", "td",
    "tfoot", "th", "thead", "title", "tr", "track", "ul", "video",
})
FOREIGN_TAGS = frozenset({
    "animate", "animatemotion", "animatetransform", "annotation", "circle",
    "clippath", "defs", "desc", "ellipse", "feblend", "fecolormatrix",
    "fecomponenttransfer", "fecomposite", "feconvolvematrix", "fediffuselighting",
    "fedisplacementmap", "fedistantlight", "fedropshadow", "feflood", "fefunca",
    "fefuncb", "fefuncg", "fefuncr", "fegaussianblur", "feimage", "femerge",
    "femergenode", "femorphology", "feoffset", "fepointlight",
    "fespecularlighting", "fespotlight", "fetile", "feturbulence", "filter",
    "foreignobject", "g", "image", "line", "lineargradient", "marker", "mask",
    "math", "metadata", "mfrac", "mi", "mn", "mo", "mover", "mpath", "mroot",
    "mrow", "ms", "msqrt", "msub", "msubsup", "msup", "mtable", "mtd", "mtext",
    "mtr", "munder", "munderover", "path", "pattern", "polygon", "polyline",
    "radialgradient", "rect", "semantics", "set", "stop", "svg", "switch",
    "symbol", "text", "textpath", "tspan", "use", "view",
})
KIND_BY_PREFIX = {
    "REQ": "requirement",
    "AC": "acceptance-criterion",
    "TASK": "task",
}


class MarkdownError(ValueError):
    """Strict Markdown input is malformed or violates caller-supplied policy."""


def _strict_text(source: bytes | str) -> str:
    if isinstance(source, bytes):
        try:
            text = source.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise MarkdownError("input is not strict UTF-8") from exc
    elif isinstance(source, str):
        try:
            source.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise MarkdownError("input is not strict UTF-8") from exc
        text = source
    else:
        raise MarkdownError("input must be UTF-8 bytes or text")
    if any(
        unicodedata.category(character) == "Cc" and character not in "\t\r\n"
        for character in text
    ):
        raise MarkdownError("input contains a control character")
    if "\x7f" in text:
        raise MarkdownError("input contains a control character")
    return unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")


def normalize_text(source: bytes | str) -> str:
    """Return the canonical v2 text projection before structural parsing.

    UTF-8 is strict, Unicode is NFC, CRLF and CR become LF, trailing spaces and
    tabs are removed per line, and only outer blank lines are removed. Internal
    line and blank-line order is preserved. Invalid encoding or control bytes
    raise :class:`MarkdownError`; no input is read or written.
    """
    text = _strict_text(source)
    lines = [line.rstrip(" \t") for line in text.split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _pairs_object(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise MarkdownError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(_: str) -> object:
    raise MarkdownError("frontmatter value is not finite JSON")


def _parse_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise MarkdownError("frontmatter value is not finite JSON")
    return parsed


def _normalize_json(value: object) -> object:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize_json(item) for item in value]
    if isinstance(value, dict):
        normalized: dict[str, object] = {}
        for key, item in value.items():
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in normalized:
                raise MarkdownError(
                    f"duplicate normalized JSON key: {normalized_key}")
            normalized[normalized_key] = _normalize_json(item)
        return normalized
    return value


def _contains_control(value: object) -> bool:
    if isinstance(value, str):
        return any(unicodedata.category(character) == "Cc" for character in value)
    if isinstance(value, list):
        return any(_contains_control(item) for item in value)
    if isinstance(value, dict):
        return any(_contains_control(key) or _contains_control(item)
                   for key, item in value.items())
    return False


def _frontmatter(
    lines: list[str], allowed_metadata_keys: Collection[str]
) -> tuple[dict[str, Any], int]:
    if not lines or lines[0] != "---":
        raise MarkdownError("opening delimiter must be exact and first")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise MarkdownError(
            "closing delimiter must be an exact --- line") from exc
    allowed = set(allowed_metadata_keys)
    if any(not isinstance(key, str) or KEY_RE.fullmatch(key) is None for key in allowed):
        raise MarkdownError(
            "allowed metadata keys must use lowercase JSON names")
    metadata: dict[str, Any] = {}
    for line_number, line in enumerate(lines[1:end], 2):
        if not line or ":" not in line:
            raise MarkdownError(
                f"frontmatter line {line_number} must contain one key and JSON value")
        key, raw_value = line.split(":", 1)
        if KEY_RE.fullmatch(key) is None or not raw_value or raw_value[0] not in " \t":
            raise MarkdownError(
                f"frontmatter line {line_number} must contain one key and JSON value")
        if key in metadata:
            raise MarkdownError(f"duplicate frontmatter key: {key}")
        if key not in allowed:
            raise MarkdownError(f"unknown frontmatter key: {key}")
        try:
            value = json.loads(
                raw_value.lstrip(" \t"), object_pairs_hook=_pairs_object,
                parse_constant=_reject_constant, parse_float=_parse_float,
            )
            value = _normalize_json(value)
        except MarkdownError:
            raise
        except (json.JSONDecodeError, RecursionError) as exc:
            raise MarkdownError(
                f"frontmatter line {line_number} value must be one-line JSON value") from exc
        if _contains_control(value):
            raise MarkdownError(
                f"frontmatter line {line_number} JSON value contains a control character")
        metadata[key] = value
    return metadata, end


def _unique_matches(pattern: re.Pattern[str], text: str) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for match in pattern.finditer(text):
        value = match.group(1) if match.lastindex else match.group(0)
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _mask_declaration_spans(masked_body: str) -> str:
    lines: list[str] = []
    for line in masked_body.split("\n"):
        if LOCAL_ID_RE.match(line) is None:
            lines.append(line)
            continue
        declaration = DECLARATION_SPAN_RE.match(line)
        assert declaration is not None
        lines.append(" " * declaration.end() + line[declaration.end():])
    return "\n".join(lines)


def _fence_opening(line: str) -> Optional[tuple[str, int]]:
    indent = len(line) - len(line.lstrip(" "))
    if indent > 3 or indent == len(line):
        return None
    content = line[indent:]
    character = content[0]
    if character not in "`~":
        return None
    length = len(content) - len(content.lstrip(character))
    if length < 3:
        return None
    if character == "`" and "`" in content[length:]:
        return None
    return character, length


def _fence_closing(line: str, character: str, minimum: int) -> bool:
    indent = len(line) - len(line.lstrip(" "))
    if indent > 3 or indent == len(line):
        return False
    content = line[indent:]
    if not content.startswith(character):
        return False
    length = len(content) - len(content.lstrip(character))
    return length >= minimum and not content[length:].strip(" \t")


def _angle_end(line: str, start: int) -> Optional[int]:
    if line.startswith("<!--", start):
        end = line.find("-->", start + 4)
        return end + 2 if end >= 0 else None
    quote: Optional[str] = None
    for index in range(start + 1, len(line)):
        character = line[index]
        if quote is not None:
            if character == quote:
                quote = None
        elif character in "\"'":
            quote = character
        elif character == ">":
            return index
        elif character == "<":
            return None
    return None


def _tag_is_markup(content: str) -> bool:
    index = int(content.startswith("/"))
    closing = index == 1
    name_start = index
    while index < len(content) and (
        content[index].isascii()
        and (content[index].isalnum() or content[index] == "-")
    ):
        index += 1
    if (index == name_start or not content[name_start].isascii()
            or not content[name_start].isalpha()):
        return False
    name = content[name_start:index].lower()
    custom = re.fullmatch(
        r"[a-z][a-z0-9]*-[a-z0-9][a-z0-9-]*", name) is not None
    if name not in HTML_TAGS and name not in FOREIGN_TAGS and not custom:
        return False
    if closing:
        return not content[index:].strip(" \t")
    while index < len(content):
        if content[index] not in " \t":
            return content[index] == "/" and not content[index + 1:].strip(" \t")
        while index < len(content) and content[index] in " \t":
            index += 1
        if index == len(content):
            return True
        if content[index] == "/":
            return not content[index + 1:].strip(" \t")
        if not (content[index].isascii()
                and (content[index].isalpha() or content[index] in "_:")):
            return False
        index += 1
        while index < len(content) and (
            content[index].isascii()
            and (content[index].isalnum() or content[index] in "_.:-")
        ):
            index += 1
        while index < len(content) and content[index] in " \t":
            index += 1
        if index == len(content) or content[index] != "=":
            continue
        index += 1
        while index < len(content) and content[index] in " \t":
            index += 1
        if index == len(content):
            return False
        if content[index] in "\"'":
            quote = content[index]
            index += 1
            close = content.find(quote, index)
            if close < 0:
                return False
            index = close + 1
        else:
            start = index
            while index < len(content) and content[index] not in " \t":
                if content[index] in "\"'=<>`":
                    return False
                index += 1
            if index == start:
                return False
    return True


def _is_markup_angle(content: str) -> bool:
    if AUTOLINK_RE.fullmatch(content) is not None:
        return True
    if content.startswith("!--") and content.endswith("--"):
        return True
    is_doctype = re.fullmatch(
        r"!doctype[ \t]+html[ \t]*", content, re.IGNORECASE) is not None
    is_cdata = content.startswith("![CDATA[") and content.endswith("]]")
    if is_doctype or is_cdata:
        return True
    if content.startswith("?") and content.endswith("?"):
        return True
    return _tag_is_markup(content)


def _mask_inline(line: str, preserved: Collection[str]) -> str:
    masked = [False] * len(line)
    runs: list[tuple[int, int]] = []
    index = 0
    while index < len(line):
        if line[index] != "`":
            index += 1
            continue
        end = index + 1
        while end < len(line) and line[end] == "`":
            end += 1
        runs.append((index, end - index))
        index = end
    next_same: list[Optional[int]] = [None] * len(runs)
    last_by_length: dict[int, int] = {}
    for run_index in range(len(runs) - 1, -1, -1):
        length = runs[run_index][1]
        next_same[run_index] = last_by_length.get(length)
        last_by_length[length] = run_index
    run_index = 0
    while run_index < len(runs):
        closing_index = next_same[run_index]
        if closing_index is None:
            run_index += 1
            continue
        start = runs[run_index][0]
        close, length = runs[closing_index]
        for position in range(start, close + length):
            masked[position] = True
        run_index = closing_index + 1
    prefix = [0]
    for hidden in masked:
        prefix.append(prefix[-1] + int(hidden))
    index = 0
    while index < len(line):
        if line[index] != "<" or masked[index]:
            index += 1
            continue
        close = _angle_end(line, index)
        if close is None or prefix[close + 1] != prefix[index]:
            index += 1
            continue
        token = line[index:close + 1]
        if token not in preserved and _is_markup_angle(token[1:-1]):
            for position in range(index, close + 1):
                masked[position] = True
        index = close + 1
    return "".join(" " if hidden else character
                   for character, hidden in zip(line, masked))


def _tag_descriptor(
    token: str, preserved: Collection[str]
) -> Optional[tuple[str, bool, bool]]:
    if token in preserved or len(token) < 3:
        return None
    content = token[1:-1]
    if not _tag_is_markup(content):
        return None
    closing = content.startswith("/")
    index = int(closing)
    start = index
    while index < len(content) and (
        content[index].isascii()
        and (content[index].isalnum() or content[index] == "-")
    ):
        index += 1
    name = content[start:index].lower()
    self_closing = not closing and content.rstrip(" \t").endswith("/")
    return name, closing, self_closing


def _outside_terminator(
    line: str, terminator: str, quote: Optional[str]
) -> tuple[bool, Optional[str]]:
    index = 0
    while index < len(line):
        character = line[index]
        if quote is not None:
            if character == quote:
                quote = None
            index += 1
            continue
        if character in "\"'":
            quote = character
            index += 1
            continue
        if line.startswith(terminator, index):
            return True, quote
        index += 1
    return False, quote


def _raw_close_end(line: str, name: str, start: int = 0) -> Optional[int]:
    closing = re.compile(
        rf"</{re.escape(name)}[ \t]*>", re.IGNORECASE).search(line, start)
    return closing.end() if closing is not None else None


def _raw_block_closed(line: str, name: str) -> bool:
    return _raw_close_end(line, name) is not None


def _update_element_state(
    stack: list[str],
    line: str,
    preserved: Collection[str],
    raw_name: Optional[str],
) -> Optional[str]:
    index = 0
    if raw_name is not None:
        closing_end = _raw_close_end(line, raw_name)
        if closing_end is None:
            return raw_name
        index = closing_end
        raw_name = None
    while index < len(line):
        start = line.find("<", index)
        if start < 0:
            break
        end = _angle_end(line, start)
        if end is None:
            index = start + 1
            continue
        descriptor = _tag_descriptor(line[start:end + 1], preserved)
        if descriptor is None:
            index = end + 1
            continue
        name, closing, self_closing = descriptor
        if name in RAW_BLOCK_TAGS and not closing and not self_closing:
            closing_end = _raw_close_end(line, name, end + 1)
            if closing_end is None:
                return name
            index = closing_end
            continue
        if name in BLOCK_TAGS:
            if closing:
                if stack and stack[-1] == name:
                    stack.pop()
            elif not self_closing:
                stack.append(name)
        index = end + 1
    return raw_name


def _html_block_start(
    line: str, preserved: Collection[str]
) -> Optional[tuple[str, Optional[str], list[str], Optional[str]]]:
    indent = len(line) - len(line.lstrip(" "))
    if indent > 3:
        return None
    content = line[indent:]
    if content.startswith("<!--"):
        return "comment", None, [], None
    if content.startswith("<?"):
        return "processing", None, [], None
    if content.startswith("<![CDATA["):
        return "cdata", None, [], None
    if (len(content) > 2 and content.startswith("<!")
            and content[2].isascii() and content[2].isupper()):
        return "declaration", None, [], None
    if not content.startswith("<"):
        return None
    end = _angle_end(content, 0)
    if end is None:
        return None
    descriptor = _tag_descriptor(content[:end + 1], preserved)
    if descriptor is None:
        return None
    name, closing, self_closing = descriptor
    if closing or self_closing:
        return None
    if name in RAW_BLOCK_TAGS:
        return "raw", name, [], None
    if name in BLOCK_TAGS:
        stack: list[str] = []
        nested_raw = _update_element_state(
            stack, content, preserved, raw_name=None)
        return "element", nested_raw, stack, None
    return None


def _mask_markdown(body: str, preserved: Collection[str]) -> str:
    """Mask code and conservative HTML blocks in one bounded line-order pass.

    Comments, processing instructions, declarations, CDATA, and raw-text tags
    run to their explicit terminator; missing terminators mask to EOF. Standard
    block elements run to their matching close, or to a blank-line boundary when
    unclosed. Nested raw-text tags suspend the outer element stack until their
    own close, and an unclosed nested raw tag masks to EOF. Thus malformed
    complete block starts fail closed without hiding Markdown after an explicit
    boundary.
    """
    lines = body.split("\n") if body else []
    result: list[str] = []
    fence_character: Optional[str] = None
    fence_length = 0
    html_kind: Optional[str] = None
    html_raw_name: Optional[str] = None
    html_stack: list[str] = []
    html_quote: Optional[str] = None
    for line in lines:
        if html_kind == "element" and html_raw_name is None and not line:
            html_kind = None
            html_stack = []
        if html_kind is not None:
            result.append(" " * len(line))
            ended = False
            if html_kind == "comment":
                ended = "-->" in line
            elif html_kind == "processing":
                ended, html_quote = _outside_terminator(line, "?>", html_quote)
            elif html_kind == "cdata":
                ended = "]]>" in line
            elif html_kind == "declaration":
                ended, html_quote = _outside_terminator(line, ">", html_quote)
            elif html_kind == "raw" and html_raw_name is not None:
                ended = _raw_block_closed(line, html_raw_name)
            elif html_kind == "element":
                html_raw_name = _update_element_state(
                    html_stack, line, preserved, html_raw_name)
                ended = not html_stack and html_raw_name is None
            if ended:
                html_kind = None
                html_raw_name = None
                html_stack = []
                html_quote = None
            continue
        if fence_character is not None:
            closing = _fence_closing(line, fence_character, fence_length)
            result.append(" " * len(line))
            if closing:
                fence_character = None
                fence_length = 0
            continue
        opening = _fence_opening(line)
        if opening is not None:
            fence_character, fence_length = opening
            result.append(" " * len(line))
            continue
        block = _html_block_start(line, preserved)
        if block is not None:
            html_kind, html_raw_name, html_stack, html_quote = block
            result.append(" " * len(line))
            if html_kind == "comment" and "-->" in line:
                html_kind = None
            elif html_kind == "processing":
                ended, html_quote = _outside_terminator(line, "?>", None)
                if ended:
                    html_kind = None
                    html_quote = None
            elif html_kind == "cdata" and "]]>" in line:
                html_kind = None
            elif html_kind == "declaration":
                ended, html_quote = _outside_terminator(line, ">", None)
                if ended:
                    html_kind = None
                    html_quote = None
            elif (html_kind == "raw" and html_raw_name is not None
                  and _raw_block_closed(line, html_raw_name)):
                html_kind = None
                html_raw_name = None
            elif (html_kind == "element" and not html_stack
                  and html_raw_name is None):
                html_kind = None
            continue
        result.append(_mask_inline(line, preserved))
    return "\n".join(result)


def _body_model(
    body: str, masked_body: str
) -> tuple[str, list[str], list[dict[str, str]]]:
    lines = body.split("\n") if body else []
    masked_lines = masked_body.split("\n") if masked_body else []
    if not masked_lines or not ANY_H1_RE.match(masked_lines[0]):
        raise MarkdownError("Markdown body must begin with exactly one H1")
    masked_h1 = H1_RE.fullmatch(masked_lines[0])
    original_h1 = H1_RE.fullmatch(lines[0])
    if masked_h1 is None or original_h1 is None:
        raise MarkdownError("Markdown body must have a non-empty H1")
    h1 = original_h1.group(1).strip()
    if not h1:
        raise MarkdownError("Markdown body must have a non-empty H1")
    sections: list[str] = []
    local_ids: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for line, masked_line in zip(lines[1:], masked_lines[1:]):
        if ANY_H1_RE.match(masked_line):
            raise MarkdownError("Markdown body must contain exactly one H1")
        heading = HEADING_RE.fullmatch(masked_line)
        original_heading = HEADING_RE.fullmatch(line)
        if heading is not None and original_heading is not None:
            title = re.sub(
                r"[ \t]+#+[ \t]*$", "", original_heading.group(1)).strip()
            if title:
                sections.append(title)
        local = LOCAL_ID_RE.match(masked_line)
        if local is not None:
            identifier = local.group(1)
            if identifier in seen_ids:
                raise MarkdownError(f"duplicate local ID {identifier}")
            seen_ids.add(identifier)
            prefix_name = identifier.split("-", 1)[0]
            local_ids.append(
                {"kind": KIND_BY_PREFIX[prefix_name], "id": identifier})
    return h1, sections, local_ids


def parse_markdown(
    source: bytes | str,
    *,
    allowed_metadata_keys: Collection[str],
    metadata_schema: Optional[Mapping[str, Any]] = None,
    schema_registry: Optional[
        Iterable[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]]
    ] = None,
    schema_limits: Optional[schema.Limits] = None,
    mode: str = "rendered",
    declared_placeholders: Collection[str] = (),
    max_characters: int = 1000000,
) -> dict[str, Any]:
    """Parse one strict v2 Markdown document into its exact normalized model.

    Args:
        source: UTF-8 bytes or Unicode text. Bytes are decoded strictly.
        allowed_metadata_keys: Closed caller-owned frontmatter key set.
        metadata_schema: Optional bounded-profile schema for parsed metadata.
        schema_registry: Optional in-memory URN schemas used only by that schema.
        schema_limits: Optional resource ceilings for metadata evaluation.
        mode: ``"template"`` or ``"rendered"``.
        declared_placeholders: Exact angle-bracket tokens preserved in template
            mode; rendered mode rejects any extracted token.
        max_characters: Positive ceiling checked before structural parsing.

    Returns:
        The exact metadata/H1/sections/local-IDs/references/placeholders model.

    Raises:
        MarkdownError: Encoding, grammar, metadata, H1, local-ID, placeholder, or
            optional schema validation fails.

    Side effects:
        None. Parsing and optional schema evaluation use only supplied memory.
    """
    if mode not in ("template", "rendered"):
        raise MarkdownError("mode must be template or rendered")
    if type(max_characters) is not int or max_characters < 1:
        raise MarkdownError("max_characters must be a positive integer")
    if isinstance(source, bytes) and len(source) > max_characters * 4:
        raise MarkdownError("Markdown input character limit exceeded")
    if isinstance(source, str) and len(source) > max_characters:
        raise MarkdownError("Markdown input character limit exceeded")
    raw = _strict_text(source)
    if len(raw) > max_characters:
        raise MarkdownError("Markdown input character limit exceeded")
    raw_lines = raw.split("\n")
    if not raw_lines or raw_lines[0] != "---":
        raise MarkdownError("opening delimiter must be exact and first")
    try:
        raw_lines.index("---", 1)
    except ValueError as exc:
        raise MarkdownError(
            "closing delimiter must be an exact --- line") from exc
    normalized = normalize_text(raw)
    lines = normalized.split("\n")
    metadata, end = _frontmatter(lines, allowed_metadata_keys)
    if metadata_schema is not None:
        decision = schema.validate(
            metadata, metadata_schema, registry=schema_registry, limits=schema_limits)
        if not decision.valid:
            first = decision.diagnostics[0]
            raise MarkdownError(
                f"metadata does not match schema: {first.code} at {first.instance_path or '/'}")
    declared = set(declared_placeholders)
    if any(not isinstance(item, str) or PLACEHOLDER_RE.fullmatch(item) is None
           for item in declared):
        raise MarkdownError(
            "declared placeholders must be exact angle-bracket tokens")
    body = normalize_text("\n".join(lines[end + 1:]))
    masked_body = _mask_markdown(body, declared)
    h1, sections, local_ids = _body_model(body, masked_body)
    reference_body = _mask_declaration_spans(masked_body)
    searchable = "\n".join(lines[:end + 1]) + "\n" + reference_body
    references = _unique_matches(REFERENCE_RE, searchable)
    placeholders = _unique_matches(PLACEHOLDER_RE, searchable)
    if mode == "rendered" and placeholders:
        raise MarkdownError("rendered document contains a raw placeholder")
    undeclared = [item for item in placeholders if item not in declared]
    if mode == "template" and undeclared:
        raise MarkdownError(f"undeclared placeholder: {undeclared[0]}")
    return {
        "metadata": metadata,
        "h1": h1,
        "sections": sections,
        "local_ids": local_ids,
        "references": references,
        "placeholders": placeholders,
    }
