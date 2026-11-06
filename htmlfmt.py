"""Indent generated HTML so the page source reads cleanly (stdlib only).

Block-level elements go on their own lines, indented two spaces per level.
Any run of inline content (text, <a>, <span>, <b>, ...) is kept exactly as
written on one line, so whitespace that affects rendering never changes.
<script>, <style>, <pre> and <textarea> contents are left untouched.
"""
import re
from html.parser import HTMLParser

_NL = re.compile(r"[ \t]*\n\s*")

BLOCK = {
    "html", "head", "body", "header", "footer", "main", "nav", "section", "article", "aside",
    "div", "ul", "ol", "li", "dl", "dt", "dd", "figure", "figcaption", "blockquote",
    "table", "thead", "tbody", "tfoot", "tr", "th", "td", "form", "fieldset",
    "h1", "h2", "h3", "h4", "h5", "h6", "p", "hr",
    "title", "meta", "link", "script", "style", "noscript", "base",
}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
RAW = {"script", "style", "pre", "textarea"}


class _Node:
    __slots__ = ("tag", "start", "end", "kids")

    def __init__(self, tag, start="", end=""):
        self.tag, self.start, self.end, self.kids = tag, start, end, []


class _Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.root = _Node(None)
        self.stack = [self.root]
        self.doctype = ""

    def _add(self, item):
        self.stack[-1].kids.append(item)

    def handle_decl(self, decl):
        self.doctype = f"<!{decl}>"

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, self.get_starttag_text())
        self._add(node)
        if tag not in VOID:
            node.end = f"</{tag}>"
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self._add(_Node(tag, self.get_starttag_text()))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self._add(data)

    def handle_entityref(self, name):
        self._add(f"&{name};")

    def handle_charref(self, name):
        self._add(f"&#{name};")

    def handle_comment(self, data):
        self._add(f"<!--{data}-->")


def _raw(item):
    if isinstance(item, str):
        return item
    return item.start + "".join(_raw(k) for k in item.kids) + item.end


def _is_block(item):
    return not isinstance(item, str) and item.tag in BLOCK


def _has_block(node):
    return node.tag not in RAW and any(_is_block(k) or (not isinstance(k, str) and _has_block(k)) for k in node.kids)


def _emit(node, depth, out):
    pad = "  " * depth
    if node.tag in RAW:
        out.append(pad + _raw(node).strip())
        return
    if not _has_block(node):
        out.append(pad + _NL.sub("\n" + pad + "  ", _raw(node).strip()))
        return
    out.append(pad + node.start)
    _children(node.kids, depth + 1, out)
    if node.end:
        out.append(pad + node.end)


def _children(kids, depth, out):
    run = []

    def flush():
        text = "".join(_raw(k) for k in run).strip()
        if text:
            pad = "  " * depth
            out.append(pad + _NL.sub("\n" + pad, text))
        run.clear()

    for k in kids:
        if _is_block(k) or (not isinstance(k, str) and _has_block(k)):
            flush()
            _emit(k, depth, out)
        else:
            run.append(k)
    flush()


def pretty(src):
    tree = _Tree()
    tree.feed(src)
    tree.close()
    out = [tree.doctype] if tree.doctype else []
    _children(tree.root.kids, 0, out)
    return "\n".join(out) + "\n"
