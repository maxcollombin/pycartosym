"""MapLibre reader — fill / line / circle / symbol / background layers.

In scope this pass: ``fill`` / ``line`` / ``circle`` / ``symbol`` /
``background`` layers whose paint / layout values are constants, or one
of the six MapLibre value-expression operators covered by
``codecs.maplibre._expressions`` (``circle`` → a ``marker`` with one
``Circle``; ``symbol`` → a ``label`` with one ``Text`` and/or a
``marker`` with one ``Image``; ``background`` → a ``Fill`` symbolizer
tagged ``vendor.maplibre.layer-type: "background"``). A layer's
``minzoom``/``maxzoom`` merge into ``rule.selector`` as ``viz.sd``
conjuncts (see ``codecs.maplibre._zoom``). ``raster`` layers, legacy
zoom/property functions, any other expression operator, and symbol
constructs this pass does not cover (a multi-family ``text-font`` stack,
``symbol-placement: line``, …) must raise ``NotImplementedError`` (a
clean rejection — never another exception type).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pycartosym.codecs.maplibre import MaplibreReader
from pycartosym.codecs.maplibre._zoom import scale_denominator_from_zoom
from pycartosym.models.styles import Style

_ATOMIC = Path(__file__).parent / "fixtures" / "maplibre" / "atomic"

# fixture stem -> the styling rules its layers should produce
IN_SCOPE: dict[str, list[dict]] = {
    "fill-opacity-default": [{"name": "fill", "symbolizer": {"fill": {}}}],
    "fill-color-literal": [{"name": "fill", "symbolizer": {"fill": {"color": "blue"}}}],
    "fill-outline-color-default": [
        {
            "name": "fill",
            "symbolizer": {"fill": {"color": "rgba(0,0,0,0)"}},
        }
    ],
    "fill-outline-color-literal": [
        {
            "name": "fill",
            "symbolizer": {
                "fill": {"color": "rgba(0,0,0,0)"},
                "stroke": {"color": "blue"},
            },
        }
    ],
    "line-simple": [{"name": "line", "symbolizer": {"stroke": {"width": 8.0}}}],
    "line-opacity-literal": [
        {
            "name": "line",
            "symbolizer": {"stroke": {"opacity": 0.3, "width": 8.0}},
        }
    ],
    "circle-radius-literal": [
        {
            "name": "circle",
            "symbolizer": {"marker": {"elements": [{"type": "Circle", "radius": 8}]}},
        }
    ],
    "circle-color-literal": [
        {
            "name": "circle",
            "symbolizer": {
                "marker": {
                    "elements": [
                        {"type": "Circle", "fill": {"color": "blue"}, "radius": 10}
                    ]
                }
            },
        }
    ],
    "circle-stroke-width-default": [
        {
            "name": "circle",
            "symbolizer": {
                "marker": {"elements": [{"type": "Circle", "fill": {"color": "#fff"}}]}
            },
        }
    ],
    "circle-stroke-literal": [
        {
            "name": "circle",
            "symbolizer": {
                "marker": {
                    "elements": [
                        {
                            "type": "Circle",
                            "fill": {"color": "#fff"},
                            "outline": {"color": "blue", "thickness": 2},
                        }
                    ]
                }
            },
        }
    ],
    "icon-image-literal": [
        {
            "name": "text",
            "symbolizer": {
                "marker": {
                    "elements": [
                        {
                            "type": "Image",
                            "image": {"id": "dot.sdf"},
                            "position": {"x": 0, "y": 0},
                        }
                    ]
                }
            },
        }
    ],
    "background-color-literal": [
        {
            "name": "background",
            "symbolizer": {
                "fill": {"color": "red"},
                "vendor.maplibre.layer-type": "background",
            },
        }
    ],
    "line-color-literal": [
        {
            "name": "background",
            "symbolizer": {
                "fill": {"color": "white"},
                "vendor.maplibre.layer-type": "background",
            },
        },
        {
            "name": "road",
            "symbolizer": {"stroke": {"color": "blue", "width": 10.0}},
        },
    ],
    "fill-pattern-literal": [
        {
            "name": "fill",
            "symbolizer": {
                "fill": {"pattern": {"type": "Image", "image": {"id": "generic_icon"}}}
            },
        }
    ],
}

OUT_OF_SCOPE = {
    "text-field-literal": "multi-family text-font stack",
    "line-width-function": "legacy zoom function on line-width",
}


@pytest.mark.parametrize("stem, expected", list(IN_SCOPE.items()))
def test_in_scope_fixture_reads(stem: str, expected: list[dict]):
    style = MaplibreReader().read(_ATOMIC / f"{stem}.json")
    assert isinstance(style, Style)
    assert style.to_dict()["stylingRules"] == expected


@pytest.mark.parametrize("stem", list(OUT_OF_SCOPE))
def test_out_of_scope_fixture_raises_not_implemented(stem: str):
    with pytest.raises(NotImplementedError):
        MaplibreReader().read(_ATOMIC / f"{stem}.json")


def test_every_atomic_fixture_is_classified():
    stems = {p.stem for p in _ATOMIC.glob("*.json")}
    assert stems == set(IN_SCOPE) | set(OUT_OF_SCOPE)


def test_reads_from_dict_and_string():
    style_dict = {
        "version": 8,
        "sources": {},
        "layers": [
            {"id": "l", "type": "line", "source": "s", "paint": {"line-color": "red"}}
        ],
    }
    from_dict = MaplibreReader().read(style_dict)
    import json

    from_str = MaplibreReader().read(json.dumps(style_dict))
    assert from_dict.to_dict() == from_str.to_dict()
    assert from_dict.to_dict()["stylingRules"][0]["symbolizer"]["stroke"] == {
        "color": "red"
    }


def test_style_with_no_layers_is_empty():
    style = MaplibreReader().read({"version": 8, "sources": {}, "layers": []})
    assert style.to_dict()["stylingRules"] == []


def test_non_v8_version_raises():
    with pytest.raises(NotImplementedError):
        MaplibreReader().read({"version": 7, "layers": []})


def test_layer_filter_maps_to_selector():
    style = MaplibreReader().read(
        {
            "version": 8,
            "sources": {},
            "layers": [
                {
                    "id": "l",
                    "type": "fill",
                    "source": "s",
                    "filter": ["==", "class", "water"],
                    "paint": {"fill-color": "blue"},
                }
            ],
        }
    )
    rule = style.to_dict()["stylingRules"][0]
    assert rule["selector"] == {
        "op": "=",
        "args": [{"property": "class"}, "water"],
    }


def test_icon_color_maps_to_image_tint():
    style = MaplibreReader().read(
        {
            "version": 8,
            "sources": {},
            "layers": [
                {
                    "id": "l",
                    "type": "symbol",
                    "source": "s",
                    "layout": {"icon-image": "dot.sdf"},
                    "paint": {"icon-color": "#000000"},
                }
            ],
        }
    )
    elements = style.to_dict()["stylingRules"][0]["symbolizer"]["marker"]["elements"]
    assert elements[0]["tint"] == "#000000"


def test_fill_pattern_literal_maps_to_image_graphic():
    style = MaplibreReader().read(
        {
            "version": 8,
            "sources": {},
            "layers": [
                {
                    "id": "l",
                    "type": "fill",
                    "source": "s",
                    "paint": {"fill-pattern": "grass"},
                }
            ],
        }
    )
    fill = style.to_dict()["stylingRules"][0]["symbolizer"]["fill"]
    assert fill["pattern"] == {"type": "Image", "image": {"id": "grass"}}


def test_fill_pattern_expression_is_rejected():
    with pytest.raises(NotImplementedError):
        MaplibreReader().read(
            {
                "version": 8,
                "sources": {},
                "layers": [
                    {
                        "id": "l",
                        "type": "fill",
                        "source": "s",
                        "paint": {"fill-pattern": ["match", ["get", "w"], 1, "a", "b"]},
                    }
                ],
            }
        )


@pytest.mark.parametrize(
    "layer_type, prop",
    [("line", "line-blur"), ("symbol", "text-halo-blur")],
)
def test_blur_paint_is_dropped_silently(layer_type, prop):
    extra_layout = {"layout": {"text-field": "hi"}} if layer_type == "symbol" else {}
    style = MaplibreReader().read(
        {
            "version": 8,
            "sources": {},
            "layers": [
                {
                    "id": "l",
                    "type": layer_type,
                    "source": "s",
                    "paint": {prop: 1.5},
                    **extra_layout,
                }
            ],
        }
    )
    assert isinstance(style, Style)


@pytest.mark.parametrize(
    "layer_type, extra_layout, prop, value",
    [
        ("symbol", {"icon-image": "dot"}, "icon-halo-blur", 1.5),
        ("symbol", {"text-field": "hi"}, "symbol-spacing", 550),
        ("symbol", {"text-field": "hi"}, "text-padding", 12),
        ("symbol", {"text-field": "hi"}, "symbol-z-order", "y-position"),
        ("symbol", {"icon-image": "dot"}, "icon-optional", True),
        ("symbol", {"icon-image": "dot"}, "text-optional", True),
        ("symbol", {"text-field": "hi"}, "text-max-angle", 30),
        ("symbol", {"text-field": "hi"}, "text-keep-upright", False),
        ("symbol", {"text-field": "hi"}, "symbol-sort-key", 5),
        ("symbol", {"icon-image": "dot"}, "icon-padding", 4),
        ("symbol", {"icon-image": "dot"}, "icon-allow-overlap", True),
        ("symbol", {"text-field": "hi"}, "text-allow-overlap", True),
        ("symbol", {"text-field": "hi"}, "symbol-avoid-edges", True),
        ("symbol", {"icon-image": "dot"}, "icon-ignore-placement", True),
        ("symbol", {"text-field": "hi"}, "text-ignore-placement", True),
        ("symbol", {"text-field": "hi"}, "text-pitch-alignment", "viewport"),
        ("symbol", {"icon-image": "dot"}, "icon-pitch-alignment", "viewport"),
        ("symbol", {"text-field": "hi"}, "text-rotation-alignment", "map"),
        ("symbol", {"icon-image": "dot"}, "icon-rotation-alignment", "map"),
        ("symbol", {"icon-image": "dot"}, "icon-keep-upright", True),
    ],
)
def test_symbol_hint_paint_is_dropped_silently(layer_type, extra_layout, prop, value):
    is_paint = prop == "icon-halo-blur"
    style = MaplibreReader().read(
        {
            "version": 8,
            "sources": {},
            "layers": [
                {
                    "id": "l",
                    "type": layer_type,
                    "source": "s",
                    "paint": {prop: value} if is_paint else {},
                    "layout": {**extra_layout, **({} if is_paint else {prop: value})},
                }
            ],
        }
    )
    assert isinstance(style, Style)


@pytest.mark.parametrize(
    "prop, default",
    [
        ("icon-size", 1),
        ("text-justify", "center"),
        ("text-max-width", 10),
        ("text-letter-spacing", 0),
        ("icon-text-fit", "none"),
        ("icon-text-fit-padding", [0, 0, 0, 0]),
    ],
)
def test_symbol_layout_default_value_passes(prop, default):
    style = MaplibreReader().read(
        _symbol_layer({"text-field": "x", "icon-image": "dot", prop: default})
    )
    assert isinstance(style, Style)


@pytest.mark.parametrize(
    "prop, default, other",
    [
        ("icon-size", 1, 2),
        ("text-justify", "center", "left"),
        ("text-max-width", 10, 20),
        ("text-letter-spacing", 0, 0.1),
        ("icon-text-fit", "none", "both"),
        ("icon-text-fit-padding", [0, 0, 0, 0], [2, 2, 2, 2]),
    ],
)
def test_symbol_layout_non_default_value_raises(prop, default, other):
    with pytest.raises(NotImplementedError):
        MaplibreReader().read(
            _symbol_layer({"text-field": "x", "icon-image": "dot", prop: other})
        )


def test_icon_halo_color_default_transparent_passes():
    style = MaplibreReader().read(
        _symbol_layer(
            {"icon-image": "dot"}, paint={"icon-halo-color": "rgba(0, 0, 0, 0)"}
        )
    )
    assert isinstance(style, Style)


def test_icon_halo_color_non_default_passes_when_width_zero():
    # icon-halo-width absent (spec default 0) means the halo is invisible
    # regardless of icon-halo-color's own value — a proven no-op, dropped
    # rather than raised.
    style = MaplibreReader().read(
        _symbol_layer(
            {"icon-image": "dot"}, paint={"icon-halo-color": "rgba(255, 0, 0, 1)"}
        )
    )
    assert isinstance(style, Style)


def test_icon_halo_width_non_default_raises():
    with pytest.raises(NotImplementedError):
        MaplibreReader().read(
            _symbol_layer({"icon-image": "dot"}, paint={"icon-halo-width": 2})
        )


def test_icon_offset_maps_to_image_position():
    style = MaplibreReader().read(
        _symbol_layer({"icon-image": "dot", "icon-offset": [0, -1.3]})
    )
    element = style.to_dict()["stylingRules"][0]["symbolizer"]["marker"]["elements"][0]
    assert element["position"] == {"x": 0, "y": -1.3}


@pytest.mark.parametrize(
    "anchor, fx, fy",
    [
        ("bottom-left", 0, 0),
        ("bottom", 50, 0),
        ("center", 50, 50),
        ("top-right", 100, 100),
    ],
)
def test_icon_anchor_maps_to_hot_spot(anchor, fx, fy):
    style = MaplibreReader().read(
        _symbol_layer({"icon-image": "dot", "icon-anchor": anchor})
    )
    element = style.to_dict()["stylingRules"][0]["symbolizer"]["marker"]["elements"][0]
    assert element["hotSpot"] == [{"pc": fx}, {"pc": fy}]


def test_icon_rotate_maps_to_transform_orientation():
    style = MaplibreReader().read(
        _symbol_layer({"icon-image": "dot", "icon-rotate": 15})
    )
    element = style.to_dict()["stylingRules"][0]["symbolizer"]["marker"]["elements"][0]
    assert element["transform"] == {"orientation": 15}


def test_line_offset_default_zero_passes():
    style = MaplibreReader().read(
        {
            "version": 8,
            "sources": {},
            "layers": [
                {
                    "id": "l",
                    "type": "line",
                    "source": "s",
                    "paint": {"line-color": "red", "line-offset": 0},
                }
            ],
        }
    )
    assert isinstance(style, Style)


def test_line_offset_non_zero_raises():
    with pytest.raises(NotImplementedError):
        MaplibreReader().read(
            {
                "version": 8,
                "sources": {},
                "layers": [
                    {
                        "id": "l",
                        "type": "line",
                        "source": "s",
                        "paint": {"line-color": "red", "line-offset": 5},
                    }
                ],
            }
        )


def test_line_dasharray_literal_maps_to_dash_pattern():
    style = MaplibreReader().read(
        {
            "version": 8,
            "sources": {},
            "layers": [
                {
                    "id": "l",
                    "type": "line",
                    "source": "s",
                    "paint": {"line-width": 2, "line-dasharray": [2.0, 1.0]},
                }
            ],
        }
    )
    stroke = style.to_dict()["stylingRules"][0]["symbolizer"]["stroke"]
    assert stroke["dashPattern"] == [4, 2]


def test_line_dasharray_without_line_width_raises():
    with pytest.raises(NotImplementedError):
        MaplibreReader().read(
            {
                "version": 8,
                "sources": {},
                "layers": [
                    {
                        "id": "l",
                        "type": "line",
                        "source": "s",
                        "paint": {"line-dasharray": [2.0, 1.0]},
                    }
                ],
            }
        )


def test_line_dasharray_legacy_stops_raises():
    with pytest.raises(NotImplementedError):
        MaplibreReader().read(
            {
                "version": 8,
                "sources": {},
                "layers": [
                    {
                        "id": "l",
                        "type": "line",
                        "source": "s",
                        "paint": {
                            "line-width": 2,
                            "line-dasharray": {"stops": [[13, [1, 1]]]},
                        },
                    }
                ],
            }
        )


@pytest.mark.parametrize(
    "mb_prop, cs_prop, value",
    [
        ("line-cap", "cap", "round"),
        ("line-cap", "cap", "square"),
        ("line-join", "join", "bevel"),
        ("line-join", "join", "miter"),
    ],
)
def test_line_cap_join_maps_to_stroke(mb_prop, cs_prop, value):
    style = MaplibreReader().read(
        {
            "version": 8,
            "sources": {},
            "layers": [
                {
                    "id": "l",
                    "type": "line",
                    "source": "s",
                    "layout": {mb_prop: value},
                }
            ],
        }
    )
    stroke = style.to_dict()["stylingRules"][0]["symbolizer"]["stroke"]
    assert stroke[cs_prop] == value


def test_line_round_limit_raises():
    # miter-limit ratio — no CartoSym Stroke field, unlike cap/join.
    with pytest.raises(NotImplementedError):
        MaplibreReader().read(
            {
                "version": 8,
                "sources": {},
                "layers": [
                    {
                        "id": "l",
                        "type": "line",
                        "source": "s",
                        "layout": {"line-round-limit": 2},
                    }
                ],
            }
        )


@pytest.mark.parametrize("prop, value", [("line-cap", "flat"), ("line-join", "mitre")])
def test_line_cap_join_unrecognised_value_raises(prop, value):
    # "mitre" (British) is not this codec's spelling ("miter") — same
    # rigour as the SLD/SE codec, no guessing at a normalisation.
    with pytest.raises(NotImplementedError):
        MaplibreReader().read(
            {
                "version": 8,
                "sources": {},
                "layers": [
                    {"id": "l", "type": "line", "source": "s", "layout": {prop: value}}
                ],
            }
        )


def test_unsupported_filter_key_raises():
    with pytest.raises(NotImplementedError):
        MaplibreReader().read(
            {
                "version": 8,
                "sources": {},
                "layers": [
                    {
                        "id": "l",
                        "type": "fill",
                        "source": "s",
                        "filter": ["==", "$type", "Polygon"],
                        "paint": {"fill-color": "blue"},
                    }
                ],
            }
        )


def test_get_expression_maps_to_property_ref():
    """['get', 'colour'] is one of the six in-scope value expressions."""
    style = MaplibreReader().read(
        {
            "version": 8,
            "sources": {},
            "layers": [
                {
                    "id": "l",
                    "type": "fill",
                    "source": "s",
                    "paint": {"fill-color": ["get", "colour"]},
                }
            ],
        }
    )
    fill = style.styling_rules[0].symbolizer.fill
    assert fill.color.property == "colour"


def test_legacy_zoom_function_raises():
    with pytest.raises(NotImplementedError):
        MaplibreReader().read(
            {
                "version": 8,
                "sources": {},
                "layers": [
                    {
                        "id": "l",
                        "type": "fill",
                        "source": "s",
                        "paint": {"fill-color": {"stops": [[0, "blue"], [10, "red"]]}},
                    }
                ],
            }
        )


def test_out_of_scope_expression_operator_raises():
    """A comparison expression is real MapLibre syntax, but not one of the
    six operators this codec's value-expression pass covers (nor the
    arithmetic/``viz.sd`` extension added on top of them).
    """
    with pytest.raises(NotImplementedError):
        MaplibreReader().read(
            {
                "version": 8,
                "sources": {},
                "layers": [
                    {
                        "id": "l",
                        "type": "fill",
                        "source": "s",
                        "paint": {"fill-opacity": ["==", ["get", "a"], 1]},
                    }
                ],
            }
        )


def test_visibility_none_maps_to_false():
    style = MaplibreReader().read(
        {
            "version": 8,
            "sources": {},
            "layers": [
                {
                    "id": "l",
                    "type": "fill",
                    "source": "s",
                    "layout": {"visibility": "none"},
                    "paint": {"fill-color": "blue"},
                }
            ],
        }
    )
    sym = style.to_dict()["stylingRules"][0]["symbolizer"]
    assert sym["visibility"] is False


# ---------------------------------------------------------------------------
# symbol layer (label / marker)
# ---------------------------------------------------------------------------


def _symbol_layer(layout: dict, paint: dict | None = None) -> dict:
    return {
        "version": 8,
        "sources": {},
        "layers": [
            {
                "id": "l",
                "type": "symbol",
                "source": "s",
                "layout": layout,
                "paint": paint or {},
            }
        ],
    }


def test_text_field_property_token():
    style = MaplibreReader().read(_symbol_layer({"text-field": "{name}"}))
    el = style.styling_rules[0].symbolizer.label.elements[0]
    assert el.text == {"property": "name"}


def test_text_field_literal_string():
    style = MaplibreReader().read(_symbol_layer({"text-field": "Fixed label"}))
    el = style.styling_rules[0].symbolizer.label.elements[0]
    assert el.text == "Fixed label"


def test_text_field_mixed_template_raises():
    with pytest.raises(NotImplementedError):
        MaplibreReader().read(_symbol_layer({"text-field": "{name} ({code})"}))


def test_text_anchor_maps_to_alignment():
    style = MaplibreReader().read(
        _symbol_layer({"text-field": "x", "text-anchor": "bottom-left"})
    )
    el = style.styling_rules[0].symbolizer.label.elements[0]
    assert el.alignment == ["left", "bottom"]


def test_text_offset_maps_to_position():
    style = MaplibreReader().read(
        _symbol_layer({"text-field": "x", "text-offset": [1, -2]})
    )
    el = style.styling_rules[0].symbolizer.label.elements[0]
    assert (el.position.x, el.position.y) == (1, -2)


def test_text_rotate_maps_to_transform_orientation():
    style = MaplibreReader().read(_symbol_layer({"text-field": "x", "text-rotate": 45}))
    el = style.styling_rules[0].symbolizer.label.elements[0]
    assert el.transform.orientation == 45


def test_text_transform_none_is_ignored():
    style = MaplibreReader().read(
        _symbol_layer({"text-field": "x", "text-transform": "none"})
    )
    el = style.styling_rules[0].symbolizer.label.elements[0]
    assert getattr(el, "font", None) is None


def test_text_transform_uppercase_raises():
    with pytest.raises(NotImplementedError):
        MaplibreReader().read(
            _symbol_layer({"text-field": "x", "text-transform": "uppercase"})
        )


def test_multi_family_text_font_raises():
    with pytest.raises(NotImplementedError):
        MaplibreReader().read(
            _symbol_layer({"text-field": "x", "text-font": ["A", "B"]})
        )


def test_symbol_placement_line_raises():
    with pytest.raises(NotImplementedError):
        MaplibreReader().read(
            _symbol_layer({"text-field": "x", "symbol-placement": "line"})
        )


def test_symbol_without_text_or_icon_raises():
    with pytest.raises(NotImplementedError):
        MaplibreReader().read(_symbol_layer({}))


def test_icon_opacity_without_icon_image_raises():
    with pytest.raises(NotImplementedError):
        MaplibreReader().read(_symbol_layer({}, {"icon-opacity": 0.5}))


def test_icon_image_maps_to_marker():
    style = MaplibreReader().read(_symbol_layer({"icon-image": "poi.png"}))
    sym = style.styling_rules[0].symbolizer
    assert sym.label is None
    assert sym.marker.elements[0]["image"] == {"id": "poi.png"}


def test_text_and_icon_together_produce_label_and_marker():
    style = MaplibreReader().read(
        _symbol_layer({"text-field": "x", "icon-image": "poi.png"})
    )
    sym = style.styling_rules[0].symbolizer
    assert sym.label is not None
    assert sym.marker is not None


def test_text_halo_maps_to_font_outline():
    style = MaplibreReader().read(
        _symbol_layer(
            {"text-field": "x"},
            {"text-halo-color": "#fff", "text-halo-width": 1.5},
        )
    )
    el = style.styling_rules[0].symbolizer.label.elements[0]
    assert el.font["outline"] == {"color": "#fff", "size": 1.5}


def test_unsupported_symbol_layout_key_raises():
    # text-line-height: no CartoSym field (Font has no leading/lineHeight),
    # a confirmed permanent gap, not just an uncabled key.
    with pytest.raises(NotImplementedError):
        MaplibreReader().read(
            _symbol_layer({"text-field": "x", "text-line-height": 1.5})
        )


def _fill_style(layer: dict) -> dict:
    return {"version": 8, "sources": {}, "layers": [layer]}


def test_background_pattern_raises():
    layer = {"id": "bg", "type": "background", "paint": {"background-pattern": "p"}}
    with pytest.raises(NotImplementedError):
        MaplibreReader().read(_fill_style(layer))


def test_minzoom_maps_to_viz_sd_selector():
    layer = {
        "id": "fill",
        "type": "fill",
        "source": "s",
        "paint": {"fill-color": "red"},
        "minzoom": 10,
    }
    rule = MaplibreReader().read(_fill_style(layer)).to_dict()["stylingRules"][0]
    assert rule["selector"] == {
        "op": "<=",
        "args": [{"sysId": "viz.sd"}, scale_denominator_from_zoom(10)],
    }


def test_maxzoom_maps_to_viz_sd_selector():
    layer = {
        "id": "fill",
        "type": "fill",
        "source": "s",
        "paint": {"fill-color": "red"},
        "maxzoom": 12,
    }
    rule = MaplibreReader().read(_fill_style(layer)).to_dict()["stylingRules"][0]
    assert rule["selector"] == {
        "op": ">",
        "args": [{"sysId": "viz.sd"}, scale_denominator_from_zoom(12)],
    }


def test_minzoom_and_filter_merge_into_one_selector():
    layer = {
        "id": "fill",
        "type": "fill",
        "source": "s",
        "filter": ["==", "class", "water"],
        "paint": {"fill-color": "red"},
        "minzoom": 10,
    }
    rule = MaplibreReader().read(_fill_style(layer)).to_dict()["stylingRules"][0]
    assert rule["selector"] == {
        "op": "and",
        "args": [
            {
                "op": "<=",
                "args": [{"sysId": "viz.sd"}, scale_denominator_from_zoom(10)],
            },
            {"op": "=", "args": [{"property": "class"}, "water"]},
        ],
    }


def test_minzoom_zero_is_a_no_op():
    layer = {
        "id": "fill",
        "type": "fill",
        "source": "s",
        "paint": {"fill-color": "red"},
        "minzoom": 0,
    }
    rule = MaplibreReader().read(_fill_style(layer)).to_dict()["stylingRules"][0]
    assert "selector" not in rule


class TestStepZoomExplosion:
    """``["step", ["zoom"], …]`` → one rule per zoom segment, ``viz.sd``-scoped."""

    def test_single_stepped_property_becomes_n_rules(self):
        layer = {
            "id": "line",
            "type": "line",
            "source": "s",
            "paint": {"line-color": ["step", ["zoom"], "red", 12, "blue", 15, "green"]},
        }
        rules = MaplibreReader().read(_fill_style(layer)).to_dict()["stylingRules"]
        assert [r["name"] for r in rules] == ["line-1", "line-2", "line-3"]
        assert [r["symbolizer"]["stroke"]["color"] for r in rules] == [
            "red",
            "blue",
            "green",
        ]
        # Segment boundaries: (-inf, 12), [12, 15), [15, +inf).
        assert rules[0]["selector"] == {
            "op": ">",
            "args": [{"sysId": "viz.sd"}, scale_denominator_from_zoom(12)],
        }
        assert rules[1]["selector"] == {
            "op": "and",
            "args": [
                {
                    "op": "<=",
                    "args": [{"sysId": "viz.sd"}, scale_denominator_from_zoom(12)],
                },
                {
                    "op": ">",
                    "args": [{"sysId": "viz.sd"}, scale_denominator_from_zoom(15)],
                },
            ],
        }
        assert rules[2]["selector"] == {
            "op": "<=",
            "args": [{"sysId": "viz.sd"}, scale_denominator_from_zoom(15)],
        }

    def test_two_stepped_properties_with_different_breakpoints_merge(self):
        layer = {
            "id": "l",
            "type": "symbol",
            "source": "s",
            "minzoom": 10,
            "layout": {
                "text-field": "x",
                "icon-image": ["step", ["zoom"], "a", 15, "b", 16, "c"],
            },
            "paint": {"icon-opacity": ["step", ["zoom"], 0.2, 13, 0.5, 14, 1.0]},
        }
        rules = MaplibreReader().read(_fill_style(layer)).to_dict()["stylingRules"]
        images = [
            r["symbolizer"]["marker"]["elements"][0]["image"]["id"] for r in rules
        ]
        opacities = [r["symbolizer"]["marker"]["elements"][0]["opacity"] for r in rules]
        # Merged breakpoints 13/14/15/16 -> 5 segments, values resolved
        # independently per property at each segment.
        assert images == ["a", "a", "a", "b", "c"]
        assert opacities == [0.2, 0.5, 1.0, 1.0, 1.0]

    def test_breakpoint_outside_layer_zoom_range_is_ignored(self):
        layer = {
            "id": "line",
            "type": "line",
            "source": "s",
            "minzoom": 14,
            "paint": {"line-color": ["step", ["zoom"], "red", 10, "blue", 20, "green"]},
        }
        rules = MaplibreReader().read(_fill_style(layer)).to_dict()["stylingRules"]
        # Only the 20 breakpoint is inside (14, +inf) - the 10 breakpoint
        # is below the layer's own minzoom and produces no extra segment,
        # but the value it selects ("blue", active at zoom 10-20) is still
        # the correct one for the first segment (starting at zoom 14).
        assert len(rules) == 2
        assert [r["symbolizer"]["stroke"]["color"] for r in rules] == [
            "blue",
            "green",
        ]

    def test_ignored_paint_property_stepped_by_zoom_does_not_explode(self):
        layer = {
            "id": "l",
            "type": "symbol",
            "source": "s",
            "layout": {
                "text-field": "x",
                "symbol-spacing": ["step", ["zoom"], 250, 14, 450],
            },
        }
        rules = MaplibreReader().read(_fill_style(layer)).to_dict()["stylingRules"]
        assert len(rules) == 1
        assert rules[0]["name"] == "l"

    def test_step_output_that_is_itself_unsupported_still_raises(self):
        # A step segment's own value goes through the normal per-property
        # path unchanged — an unsupported expression there still raises,
        # not a new failure mode introduced by the explosion itself.
        layer = {
            "id": "line",
            "type": "line",
            "source": "s",
            "paint": {"line-color": ["step", ["zoom"], "red", 12, ["silly-op"]]},
        }
        with pytest.raises(NotImplementedError):
            MaplibreReader().read(_fill_style(layer))
