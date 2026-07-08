"""Evaluate a Boolean search string against a candidate record (local screening).

Used to filter a candidate/applicant pool BEFORE pushing to Loxo: keep the ones that
match the Boolean, drop ("shoot") the rest. Works on any candidate dict (Seamless
sourced candidates today, Handshake applicants later).

Supports: AND / OR / NOT (uppercase operators), "quoted phrases", parentheses,
implicit AND between adjacent terms, and trailing '*' wildcards (reconciliation*).
Term match = case-insensitive substring (wildcard '*' -> \\w*). Invalid/empty
expression => matches everything (fail open, never drops silently on a parse bug).
"""
from __future__ import annotations

import re
from typing import Any, Callable

Predicate = Callable[[str], bool]


def _tokenize(s: str) -> list[Any]:
    tokens: list[Any] = []
    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        if ch.isspace():
            i += 1
        elif ch in "()":
            tokens.append(ch)
            i += 1
        elif ch == '"':
            j = s.find('"', i + 1)
            if j == -1:
                j = n
            tokens.append(("TERM", s[i + 1:j]))
            i = j + 1
        else:  # bareword until space / paren / quote
            j = i
            while j < n and not s[j].isspace() and s[j] not in '()"':
                j += 1
            word = s[i:j]
            i = j
            tokens.append(word if word in ("AND", "OR", "NOT") else ("TERM", word))
    return tokens


def _term(word: str) -> Predicate:
    word = word.strip()
    if not word:
        return lambda t: True
    pat = re.compile(re.escape(word).replace(r"\*", r"\w*"), re.I)
    return lambda t: bool(pat.search(t))


class _Parser:
    def __init__(self, tokens: list[Any]):
        self.toks = tokens
        self.i = 0

    def _peek(self) -> Any:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def _next(self) -> Any:
        t = self._peek()
        self.i += 1
        return t

    def parse(self) -> Predicate:
        return self._or()

    def _or(self) -> Predicate:
        left = self._and()
        while self._peek() == "OR":
            self._next()
            right = self._and()
            left = (lambda a, b: (lambda t: a(t) or b(t)))(left, right)
        return left

    def _and(self) -> Predicate:
        left = self._not()
        while True:
            t = self._peek()
            if t == "AND":
                self._next()
                right = self._not()
            elif t is None or t == "OR" or t == ")":
                break
            else:  # implicit AND between adjacent atoms
                right = self._not()
            left = (lambda a, b: (lambda t: a(t) and b(t)))(left, right)
        return left

    def _not(self) -> Predicate:
        if self._peek() == "NOT":
            self._next()
            operand = self._atom()
            return lambda t: not operand(t)
        return self._atom()

    def _atom(self) -> Predicate:
        t = self._peek()
        if t == "(":
            self._next()
            node = self._or()
            if self._peek() == ")":
                self._next()
            return node
        if isinstance(t, tuple) and t[0] == "TERM":
            self._next()
            return _term(t[1])
        self._next()  # unexpected token — skip
        return lambda _t: True


def compile_boolean(expression: str) -> Predicate:
    """Compile a Boolean string into a predicate over text. Fails open."""
    try:
        toks = _tokenize(expression or "")
        if not toks:
            return lambda _t: True
        return _Parser(toks).parse()
    except Exception:
        return lambda _t: True


def _quote(term: str) -> str:
    """Quote a filter term that contains spaces (so it stays one phrase), unless the
    recruiter already wrote their own Boolean fragment (quotes/operators/parens)."""
    term = term.strip()
    if not term:
        return ""
    if term[0] in '("' or any(op in f" {term} " for op in (" AND ", " OR ", " NOT ")):
        return term  # already a Boolean fragment — leave it alone
    return f'"{term}"' if any(c.isspace() for c in term) else term


def _grouped(fragment: str) -> str:
    """Parenthesize a facet that has a top-level Boolean operator, so AND/OR precedence
    stays correct when it's AND-ed into the composed string (OR binds looser than AND).
    Already-wrapped atoms (`(...)`) are left alone."""
    f = fragment.strip()
    if not f or (f.startswith("(") and f.endswith(")")):
        return f
    if any(op in f" {f} " for op in (" OR ", " AND ", " NOT ")):
        return f"({f})"
    return f


def _split(items: Any) -> list[str]:
    """Accept a list, or a comma/newline-separated string, -> clean list of terms."""
    if items is None:
        return []
    if isinstance(items, str):
        items = re.split(r"[,\n]", items)
    return [t.strip() for t in items if str(t).strip()]


def augment_boolean(
    base: str = "",
    include_all: Any = None,
    include_any: Any = None,
    exclude: Any = None,
    location: Any = None,
) -> str:
    """Compose a new Boolean by layering recruiter filters onto a base expression.

    This is the "swap the Boolean / add search filters" primitive behind the custom
    search UI. Every argument is optional and accepts a list OR a comma/newline string.

      base         existing Boolean to build on (kept verbatim, parenthesized)
      include_all  terms each AND-ed on   (must-have — narrows)
      include_any  terms OR-ed into one AND-ed group  (any-of — widens within a facet)
      exclude      terms each NOT-ed       (knock-outs)
      location     OR-list/phrase AND-ed on (convenience; same effect as include_all)

    Returns a syntactically valid Boolean string that compile_boolean() accepts.
    """
    parts: list[str] = []
    base = (base or "").strip()
    if base:
        parts.append(f"({base})")
    for term in _split(include_all):
        parts.append(_grouped(_quote(term)))
    for term in _split(location):
        parts.append(_grouped(_quote(term)))
    any_terms = [_quote(t) for t in _split(include_any)]
    if any_terms:
        group = any_terms[0] if len(any_terms) == 1 else "(" + " OR ".join(any_terms) + ")"
        parts.append(_grouped(group))
    for term in _split(exclude):
        parts.append(f"NOT {_grouped(_quote(term))}")
    return " AND ".join(p for p in parts if p)


_TEXT_FIELDS = ("name", "title", "company", "location", "headline", "summary",
                "major", "school", "degree", "email")


def candidate_text(candidate: dict[str, Any]) -> str:
    """Flatten the fields we screen against into one searchable string."""
    parts: list[str] = [str(candidate.get(k)) for k in _TEXT_FIELDS if candidate.get(k)]
    skills = candidate.get("skills")
    if isinstance(skills, list):
        parts.append(" ".join(str(s) for s in skills))
    elif skills:
        parts.append(str(skills))
    return " ".join(parts)


def filter_candidates(
    candidates: list[dict[str, Any]], expression: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (kept, dropped) — kept match the Boolean, dropped do not."""
    pred = compile_boolean(expression)
    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for c in candidates:
        (kept if pred(candidate_text(c)) else dropped).append(c)
    return kept, dropped
