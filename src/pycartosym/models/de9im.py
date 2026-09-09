"""DE-9IM (Dimensionally Extended 9-Intersection Model) — predicate lookup table.

This module provides a reference table mapping OGC named spatial predicates
to their DE-9IM intersection matrix patterns, plus utility functions for
pattern matching. It does NOT compute geometric intersections; it only lets
the transcoder validate and look up predicate ↔ pattern relationships.

Reference implementations:
  - ecere/libCartoSym DE9IM/DE9IM.ec  — full computational DE-9IM by
    Jérôme St-Louis (OGC CartoSym spec editor). The ``match()`` method,
    ``geometryContains()``, ``geometryIntersects()`` etc. are the source of
    the patterns used here.
  - pygeofilter (geopython) — ``Relate(lhs, rhs, pattern)`` AST node.

See README section "DE-9IM (Dimensionally Extended 9-Intersection Model)"
for a description of the matrix model.

OGC standards:
  - OGC 06-103r4 (Simple Feature Access) §6.1.15 — DE-9IM definitions
  - OGC 21-065 (CQL2) — spatial predicates ``s_intersects``, ``s_relate`` etc.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# DE-9IM predicate → pattern(s) lookup table
# ---------------------------------------------------------------------------
# Each named predicate maps to one or more 9-character patterns.
# A predicate is satisfied if the computed DE-9IM matrix matches ANY of the
# listed patterns.
#
# Characters:
#   T  — intersection exists (dimension ≥ 0, i.e. not empty)
#   F  — intersection is empty
#   *  — don't care
#   0  — dimension 0 (point)
#   1  — dimension 1 (line)
#   2  — dimension 2 (surface)
#
# Source: ecere/libCartoSym DE9IM.ec — match() patterns used in
# geometryEquals, geometryContains, geometryWithin, geometryTouches,
# geometryCovers, geometryCrosses, geometryOverlaps, geometryDisjoint.

DE9IM_PREDICATES: dict[str, list[str]] = {
    # Simple predicates — one pattern each
    "equals": ["T*F**FFF*"],
    "disjoint": ["FF*FF****"],
    "contains": ["T*****FF*"],
    "within": ["T*F**F***"],
    # Touches — satisfied by any of three patterns
    "touches": ["FT*******", "F**T*****", "F***T****"],
    # Covers — satisfied by any of four patterns
    "covers": ["T*****FF*", "*T****FF*", "***T**FF*", "****T*FF*"],
    # Intersects — negation of disjoint (convenience, not pattern-matched)
    # Handled specially: intersects ⟺ ¬ disjoint
    "intersects": [],
    # Dimension-dependent predicates
    # crosses(dimA < dimB): T*T******   crosses(dimA > dimB): T*****T**
    # crosses(dimA == dimB == 1): 0********
    "crosses": ["T*T******", "T*****T**", "0********"],
    # overlaps(dim == 2 or dim == 0): T*T***T**   overlaps(dim == 1): 1*T***T**
    "overlaps": ["T*T***T**", "1*T***T**"],
    # coveredBy is the transpose of covers
    "coveredby": ["T*F**F***", "*TF**F***", "**FT*F***", "**F*TF***"],
}

# CQL2 operator name → predicate name mapping
# CQL2 uses s_ prefix for spatial predicates
CQL2_SPATIAL_PREDICATES: dict[str, str] = {
    f"s_{name}": name for name in DE9IM_PREDICATES
}


# ---------------------------------------------------------------------------
# Pattern matching
# ---------------------------------------------------------------------------


def match_pattern(matrix: str, pattern: str) -> bool:
    """Check whether a 9-character DE-9IM *matrix* matches a *pattern*.

    Both strings must be exactly 9 characters.  The pattern may contain
    the wildcard characters ``T`` (any non-F value) and ``*`` (anything).

    This is a Python translation of ``DE9IM::match()`` from
    ecere/libCartoSym ``DE9IM.ec``.

    >>> match_pattern("212101212", "T*T***T**")
    True
    >>> match_pattern("FF2FF1212", "FF*FF****")
    True
    >>> match_pattern("212101212", "FF*FF****")
    False
    """
    if len(matrix) != 9 or len(pattern) != 9:
        raise ValueError(
            f"Both matrix and pattern must be exactly 9 characters "
            f"(got {len(matrix)} and {len(pattern)})"
        )
    for m_char, p_char in zip(matrix.upper(), pattern.upper()):
        if p_char == "*":
            continue
        if p_char == "T":
            if m_char == "F":
                return False
        elif m_char != p_char:
            return False
    return True


def is_valid_de9im(matrix: str) -> bool:
    """Validate that *matrix* is a well-formed DE-9IM string.

    A valid matrix has exactly 9 characters, each one of: F, 0, 1, 2.
    (Upper or lower case F is accepted; wildcards T and * are NOT valid
    in a computed matrix, only in patterns.)

    >>> is_valid_de9im("212101212")
    True
    >>> is_valid_de9im("FF2FF1212")
    True
    >>> is_valid_de9im("T*F**FFF*")
    False
    >>> is_valid_de9im("short")
    False
    """
    if len(matrix) != 9:
        return False
    return all(ch in "F012f" for ch in matrix)


# The character set of a DE-9IM *pattern* (as opposed to a computed matrix):
# the matrix characters plus the wildcards ``T`` (any non-empty
# intersection) and ``*`` (don't care). This is the single source of truth
# for the pattern alphabet — the ``SpatialRelatePredicate.pattern`` field
# validator delegates here rather than repeating a regex.
_DE9IM_PATTERN_CHARS = frozenset("012TtFf*")


def is_valid_de9im_pattern(pattern: str) -> bool:
    """Validate that *pattern* is a well-formed DE-9IM intersection pattern.

    A valid pattern has exactly 9 characters, each one of ``0 1 2 T F *``
    (case-insensitive for ``T``/``F``). Unlike :func:`is_valid_de9im`, the
    wildcard characters ``T`` and ``*`` are allowed — a pattern is what the
    caller supplies to ``S_RELATE`` / matches a computed matrix against.

    >>> is_valid_de9im_pattern("T*F**FFF*")
    True
    >>> is_valid_de9im_pattern("tf*ffff**")
    True
    >>> is_valid_de9im_pattern("212101212")
    True
    >>> is_valid_de9im_pattern("XYZXYZXYZ")
    False
    >>> is_valid_de9im_pattern("T*F")
    False
    """
    if len(pattern) != 9:
        return False
    return all(ch in _DE9IM_PATTERN_CHARS for ch in pattern)


def predicate_matches(matrix: str, predicate_name: str) -> bool:
    """Check whether *matrix* satisfies the named spatial *predicate_name*.

    For ``intersects`` the check is the negation of ``disjoint``.
    For dimension-dependent predicates (``crosses``, ``overlaps``) this
    returns ``True`` if *any* variant pattern matches — callers needing
    strict dimension-aware checking should use ``match_pattern`` directly.

    >>> predicate_matches("212101212", "overlaps")
    True
    >>> predicate_matches("FF2FF1212", "disjoint")
    True
    >>> predicate_matches("FF2FF1212", "intersects")
    False
    >>> predicate_matches("0FFFFFFF2", "equals")
    True
    """
    name = predicate_name.lower()

    # Strip CQL2 s_ prefix if present
    if name.startswith("s_"):
        name = name[2:]

    if name == "intersects":
        return not predicate_matches(matrix, "disjoint")

    patterns = DE9IM_PREDICATES.get(name)
    if patterns is None:
        raise ValueError(f"Unknown spatial predicate: {predicate_name!r}")
    return any(match_pattern(matrix, p) for p in patterns)


def get_patterns(predicate_name: str) -> list[str]:
    """Return the DE-9IM pattern(s) for a named spatial predicate.

    >>> get_patterns("contains")
    ['T*****FF*']
    >>> get_patterns("s_touches")
    ['FT*******', 'F**T*****', 'F***T****']
    """
    name = predicate_name.lower()
    if name.startswith("s_"):
        name = name[2:]
    patterns = DE9IM_PREDICATES.get(name)
    if patterns is None:
        raise ValueError(f"Unknown spatial predicate: {predicate_name!r}")
    return list(patterns)
