"""Tests for CartoSym nested-rule cascade flattening (``codecs/_cascade.py``).

Shared by any codec whose target format has no cascade concept of its own
(SLD/SE, MapLibre). A selector-bearing ``nestedRules`` entry is a
cascading refinement: its selector is AND-ed with the parent's and its
symbolizer is merged onto the parent's.
"""

from pycartosym.codecs._cascade import flatten_cascade_rules


class TestFlattenCascadeRules:
    def test_selector_is_and_merged_down_the_tree(self):
        flat = flatten_cascade_rules(
            [
                {
                    "selector": {"op": "=", "args": [{"property": "A"}, 1]},
                    "symbolizer": {"fill": {"color": "gray"}},
                    "nestedRules": [
                        {
                            "selector": {"op": "=", "args": [{"property": "B"}, 2]},
                            "symbolizer": {"fill": {"color": "red"}},
                        }
                    ],
                }
            ]
        )
        assert len(flat) == 2
        assert flat[0]["selector"] == {"op": "=", "args": [{"property": "A"}, 1]}
        assert flat[1]["selector"] == {
            "op": "and",
            "args": [
                {"op": "=", "args": [{"property": "A"}, 1]},
                {"op": "=", "args": [{"property": "B"}, 2]},
            ],
        }

    def test_symbolizer_partial_override_is_deep_merged(self):
        flat = flatten_cascade_rules(
            [
                {
                    "selector": {"op": "=", "args": [{"property": "A"}, 1]},
                    "symbolizer": {
                        "fill": {"color": "gray", "opacity": 0.5},
                        "stroke": {"color": "gray", "width": {"px": 2}},
                    },
                    "nestedRules": [
                        {
                            "selector": {"op": "=", "args": [{"property": "K"}, "x"]},
                            "symbolizer": {"fill": {"color": "darkGreen"}},
                        }
                    ],
                }
            ]
        )
        child = flat[1]["symbolizer"]
        # overridden key wins, siblings inherited
        assert child["fill"] == {"color": "darkGreen", "opacity": 0.5}
        assert child["stroke"] == {"color": "gray", "width": {"px": 2}}

    def test_indexed_element_override_replaces_one_inherited_element(self):
        flat = flatten_cascade_rules(
            [
                {
                    "selector": {"op": "=", "args": [{"property": "A"}, 1]},
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {"type": "Dot", "color": "white"},
                                {"type": "Dot", "color": "orange"},
                            ]
                        }
                    },
                    "nestedRules": [
                        {
                            "selector": {"op": "=", "args": [{"property": "K"}, "x"]},
                            "symbolizer": {
                                "marker": {
                                    "alter": True,
                                    "elements": {
                                        "index": 1,
                                        "value": {"type": "Text", "text": "hi"},
                                    },
                                }
                            },
                        }
                    ],
                }
            ]
        )
        elements = flat[1]["symbolizer"]["marker"]["elements"]
        assert elements == [
            {"type": "Dot", "color": "white"},
            {"type": "Text", "text": "hi"},
        ]
        assert "alter" not in flat[1]["symbolizer"]["marker"]

    def test_selectorless_nested_rule_merges_into_the_parent(self):
        """Same as removing its curly brackets: one rule, no second row."""
        parent_selector = {"op": "=", "args": [{"property": "A"}, 1]}
        flat = flatten_cascade_rules(
            [
                {
                    "selector": parent_selector,
                    "symbolizer": {"stroke": {"color": "red", "width": 3}},
                    "nestedRules": [
                        {"symbolizer": {"stroke": {"color": "gray", "width": 1}}},
                    ],
                }
            ]
        )
        assert len(flat) == 1
        assert flat[0]["selector"] == parent_selector
        assert "nestedRules" not in flat[0]
        assert flat[0]["symbolizer"]["stroke"] == {"color": "gray", "width": 1}

    def test_selectorless_nested_rule_is_inherited_by_later_refinements(self):
        parent = {"op": "=", "args": [{"property": "A"}, 1]}
        child = {"op": "=", "args": [{"property": "B"}, 2]}
        flat = flatten_cascade_rules(
            [
                {
                    "selector": parent,
                    "symbolizer": {"stroke": {"color": "red"}},
                    "nestedRules": [
                        {"selector": child, "symbolizer": {"fill": {"color": "blue"}}},
                        {"symbolizer": {"stroke": {"width": 3}}},
                    ],
                }
            ]
        )
        assert [r.get("selector") for r in flat] == [
            parent,
            {"op": "and", "args": [parent, child]},
        ]
        # the selector-less rule comes last in the document but, being part of
        # the parent, applies to the refinement too
        assert flat[1]["symbolizer"]["stroke"] == {"color": "red", "width": 3}
        assert flat[1]["symbolizer"]["fill"] == {"color": "blue"}

    def test_selectorless_rule_nested_in_a_selectorless_one(self):
        flat = flatten_cascade_rules(
            [
                {
                    "symbolizer": {"stroke": {"color": "red"}},
                    "nestedRules": [
                        {
                            "symbolizer": {"stroke": {"width": 2}},
                            "nestedRules": [{"symbolizer": {"stroke": {"width": 4}}}],
                        }
                    ],
                }
            ]
        )
        assert len(flat) == 1
        assert flat[0]["symbolizer"]["stroke"] == {"color": "red", "width": 4}

    def test_selectorless_nested_rule_inside_a_selector_bearing_one(self):
        outer = {"op": "=", "args": [{"property": "A"}, 1]}
        inner = {"op": "=", "args": [{"property": "B"}, 2]}
        flat = flatten_cascade_rules(
            [
                {
                    "selector": outer,
                    "nestedRules": [
                        {
                            "selector": inner,
                            "nestedRules": [
                                {"symbolizer": {"stroke": {"color": "gray"}}}
                            ],
                        }
                    ],
                }
            ]
        )
        assert flat[-1]["selector"] == {"op": "and", "args": [outer, inner]}
        assert flat[-1]["symbolizer"]["stroke"] == {"color": "gray"}

    def test_symbolizerless_base_node_still_emits_a_row_but_writer_drops_it(self):
        flat = flatten_cascade_rules(
            [
                {
                    "selector": {"op": "=", "args": [{"property": "A"}, 1]},
                    "symbolizer": {"visibility": False},
                    "nestedRules": [
                        {
                            "selector": {
                                "op": "<",
                                "args": [{"sysId": "viz.sd"}, 5000],
                            },
                            "symbolizer": {
                                "visibility": True,
                                "fill": {"color": "gray"},
                            },
                        }
                    ],
                }
            ]
        )
        assert flat[0]["symbolizer"] == {"visibility": False}
        assert flat[1]["symbolizer"]["visibility"] is True
