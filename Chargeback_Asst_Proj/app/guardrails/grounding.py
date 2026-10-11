from __future__ import annotations


def validate_citations(citations: list[str], known_ids: set[str]) -> tuple[bool, list[str]]:
    invalid = []
    for citation in citations:
        if citation not in known_ids:
            invalid.append(citation)
    return (not invalid, invalid)
