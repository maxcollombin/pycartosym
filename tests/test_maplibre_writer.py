"""MapLibre writer — Style → style JSON, and the read↔write round-trip.

Scope mirrors the reader: ``fill`` / ``line`` / ``marker`` (single
``Circle`` or ``Image``) / ``label`` (single ``Text``) symbolizers with
literal values. The round-trip checked here is a **model fixed point**
(``read → write → read`` yields the same Style); the emitted MapLibre is
not byte-identical to the input (a CartoSym Style has no sources / zoom /
metadata to round-trip).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pycartosym.codecs.maplibre import MaplibreReader, MaplibreWriter
from pycartosym.codecs.maplibre._zoom import (
    scale_denominator_from_zoom,
    zoom_from_scale_denominator,
)
from pycartosym.models.styles import Style

from ._maplibre_spec import assert_maplibre_valid
from .test_maplibre_reader import IN_SCOPE

_ATOMIC = Path(__file__).parent / "fixtures" / "maplibre" / "atomic"


@pytest.mark.parametrize("stem", list(IN_SCOPE))
def test_write_output_is_spec_valid(stem: str):
    style = MaplibreReader().read(_ATOMIC / f"{stem}.json")
    assert_maplibre_valid(MaplibreWriter().write(style))


@pytest.mark.parametrize("stem", list(IN_SCOPE))
def test_round_trip_is_a_model_fixed_point(stem: str):
    read = MaplibreReader()
    style = read.read(_ATOMIC / f"{stem}.json")
    again = read.read(MaplibreWriter().write(style))
    assert again.to_dict() == style.to_dict()


def test_zoom_range_round_trip_recovers_integer_zoom():
    layer = {
        "id": "fill",
        "type": "fill",
        "source": "cartosym",
        "minzoom": 10,
        "maxzoom": 14,
        "paint": {"fill-color": "red"},
    }
    read = MaplibreReader()
    style = read.read({"version": 8, "sources": {}, "layers": [layer]})
    out_layer = MaplibreWriter().write(style)["layers"][0]
    assert out_layer["minzoom"] == 10
    assert out_layer["maxzoom"] == 14
    assert isinstance(out_layer["minzoom"], int)
    assert isinstance(out_layer["maxzoom"], int)


def test_empty_style_has_no_sources():
    out = MaplibreWriter().write(Style(styling_rules=[]))
    assert out == {"version": 8, "sources": {}, "layers": []}


def test_stroke_width_unwraps_a_px_unit_value():
    """``stroke.width`` from CSCSS (``2.0 px``) validates into a
    ``UnitValue`` — MapLibre ``line-width`` needs a bare pixel number.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "roads",
                    "symbolizer": {"stroke": {"width": {"px": 2.0}}},
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert out["layers"][0]["paint"]["line-width"] == 2.0
    assert_maplibre_valid(out)


def test_stroke_width_in_a_non_px_unit_is_rejected():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "roads",
                    "symbolizer": {"stroke": {"width": {"mm": 2.0}}},
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError):
        MaplibreWriter().write(style)


def test_viz_sd_arithmetic_stroke_width_samples_a_step_lut():
    """OGC issue #115's ``stroke.width: viz.sd / 1000`` — a ``viz.sd``-only
    arithmetic expression as a whole top-level property value samples into
    a MapLibre ``step`` lookup table (13 integer zoom levels, 6-18) instead
    of raising, per the technique documented in
    ``codecs/maplibre/_expressions.py``'s module docstring. Reading the
    result back is intentionally lossy — it lands on the existing
    ``step(["zoom"])`` -> N ``viz.sd``-bounded-rules machinery (PR #70),
    giving each segment's *literal* sampled value, not the original
    symbolic formula.
    """
    from pycartosym.codecs.maplibre._zoom import scale_denominator_from_zoom
    from pycartosym.codecs.maplibre.reader import MaplibreReader

    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "roads",
                    "symbolizer": {
                        "stroke": {
                            "color": "#333333",
                            "width": {
                                "op": "/",
                                "args": [{"sysId": "viz.sd"}, 1000],
                            },
                        }
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    width = out["layers"][0]["paint"]["line-width"]
    assert width[:3] == ["step", ["zoom"], scale_denominator_from_zoom(6) / 1000]
    assert width[3::2] == list(range(7, 19))
    assert_maplibre_valid(out)

    style_back = MaplibreReader().read(out)
    assert len(style_back.styling_rules) == 13
    for zoom, rule in zip(range(6, 19), style_back.styling_rules):
        assert rule.symbolizer.stroke.width == scale_denominator_from_zoom(zoom) / 1000


def test_stroke_dash_pattern_maps_to_line_dasharray_scaled_by_width():
    """``dashPattern`` lengths are absolute px, ``line-dasharray`` is in
    multiples of the line width — each length is divided by ``width``.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "roads",
                    "symbolizer": {
                        "stroke": {
                            "width": {"px": 4.0},
                            "dashPattern": [4, 2],
                        }
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert out["layers"][0]["paint"]["line-dasharray"] == [1.0, 0.5]
    assert_maplibre_valid(out)


def test_stroke_dash_pattern_without_width_is_rejected():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "roads",
                    "symbolizer": {
                        "stroke": {
                            "color": "#ff0000",
                            "dashPattern": [4, 2],
                        }
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError):
        MaplibreWriter().write(style)


def test_stroke_dash_pattern_indexed_override_fragment_is_rejected():
    """An unflattened ``{index, value}`` cascade fragment (no ``pattern``
    array — ``_cascade.py`` does not resolve indexed overrides for
    ``dashPattern``) has no MapLibre mapping.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "roads",
                    "symbolizer": {
                        "stroke": {
                            "width": {"px": 4.0},
                            "dashPattern": {"index": 0, "value": 6},
                        }
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError):
        MaplibreWriter().write(style)


def test_stroke_cap_join_map_to_line_layout():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "roads",
                    "symbolizer": {
                        "stroke": {
                            "width": {"px": 2.0},
                            "cap": "round",
                            "join": "bevel",
                        }
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert out["layers"][0]["layout"]["line-cap"] == "round"
    assert out["layers"][0]["layout"]["line-join"] == "bevel"
    assert_maplibre_valid(out)


def test_stroke_cap_join_inlined_as_fill_outline_is_rejected():
    """A plain-colour stroke (no width/opacity) with ``cap``/``join`` stays
    inlined as ``fill-outline-color``, which has no line-cap/line-join
    layout property — the combination has no MapLibre mapping.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "parcels",
                    "symbolizer": {
                        "fill": {"color": "#00ff00"},
                        "stroke": {"color": "#000000", "cap": "round"},
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError):
        MaplibreWriter().write(style)


def test_stroke_dash_pattern_inlined_as_fill_outline_is_rejected():
    """A plain-colour stroke (no width/opacity) with a ``dashPattern``
    stays inlined as ``fill-outline-color``, which has no dasharray and
    no width to scale by — the combination has no MapLibre mapping.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "parcels",
                    "symbolizer": {
                        "fill": {"color": "#00ff00"},
                        "stroke": {
                            "color": "#000000",
                            "dashPattern": [4, 2],
                        },
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError):
        MaplibreWriter().write(style)


def test_circle_element_px_dict_fields_are_unwrapped():
    """A graphic element inside ``Marker.elements`` stays an untyped
    ``dict`` (see ``models/symbolizers.py``), so ``radius``/``thickness``
    arrive as a bare ``{"px": …}`` dict rather than a validated
    ``UnitValue`` — both shapes must unwrap the same way.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "pts",
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Circle",
                                    "outline": {"thickness": {"px": 1.5}},
                                    "radius": {"px": 6},
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    paint = out["layers"][0]["paint"]
    assert paint["circle-stroke-width"] == 1.5
    assert paint["circle-radius"] == 6
    assert_maplibre_valid(out)


def test_circle_outline_thickness_accepts_numeric_expression():
    """``circle-stroke-width`` as a numeric expression over a feature
    property (OGC issue #115's "Symbolizer Parameter Value Expressions").

    Same untyped-dict situation as ``test_circle_element_px_dict_fields_are_
    unwrapped`` — an ``ArithmeticExpression`` nested inside
    ``Marker.elements`` also stays a raw dict, which
    ``value_to_maplibre_expr`` must coerce before its ``isinstance`` checks.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "pts",
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Circle",
                                    "outline": {
                                        "thickness": {
                                            "op": "/",
                                            "args": [{"property": "sd"}, 1000],
                                        },
                                    },
                                    "radius": {"px": 6},
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    paint = out["layers"][0]["paint"]
    assert paint["circle-stroke-width"] == ["/", ["get", "sd"], 1000]
    assert_maplibre_valid(out)

    from pycartosym.codecs.maplibre.reader import MaplibreReader

    style_back = MaplibreReader().read(out)
    el = style_back.styling_rules[0].symbolizer.marker.elements[0]
    assert el["outline"]["thickness"] == {
        "op": "/",
        "args": [{"property": "sd"}, 1000],
    }


def test_circle_outline_thickness_system_identifier_raises():
    """``viz.sd`` inside ``circle-stroke-width`` still raises here: it is
    nested under ``Marker.elements`` (typed ``Any``, out of scope for the
    ``viz.sd``-arithmetic step-LUT special case — see
    ``test_viz_sd_arithmetic_stroke_width_samples_a_step_lut`` for the
    in-scope, directly-typed-field case), so it never reaches
    ``writer.py``'s ``_literal`` as a real ``SystemIdentifier`` instance
    for :func:`is_viz_sd_arithmetic` to recognise.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "pts",
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Circle",
                                    "outline": {"thickness": {"sysId": "viz.sd"}},
                                    "radius": {"px": 6},
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError):
        MaplibreWriter().write(style)


def test_text_position_property_reference_raises():
    """``Text.position`` as a property-driven ``UnitPoint`` axis (OGC issue
    #115's "Symbolizer Parameter Value Expressions", scoped to a bare
    property reference for ``UnitPoint`` — see ``models/symbolizers.py``)
    has no MapLibre mapping: ``text-offset`` only accepts a unit-less
    literal number per axis in this codec (``_position_axis_number``).
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "labels",
                    "symbolizer": {
                        "label": {
                            "elements": [
                                {
                                    "type": "Text",
                                    "text": "'x'",
                                    "position": {
                                        "x": {"property": "dx"},
                                        "y": 0,
                                    },
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError):
        MaplibreWriter().write(style)


def test_rgb_literal_color_becomes_hex():
    """CartoSym's ``Color`` accepts a ``[r, g, b]`` 0-255 literal (what a
    CSCSS ``#rrggbb`` hex literal actually parses into) — MapLibre needs
    a colour string.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {"name": "areas", "symbolizer": {"fill": {"color": [32, 32, 32]}}}
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert out["layers"][0]["paint"]["fill-color"] == "#202020"
    assert_maplibre_valid(out)


def test_rgba_literal_color_becomes_hex():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "areas",
                    "symbolizer": {"fill": {"color": [255, 0, 0, 128]}},
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert out["layers"][0]["paint"]["fill-color"] == "#ff000080"
    assert_maplibre_valid(out)


def test_fill_and_line_layers_from_a_hand_built_style():
    style = Style.from_dict(
        {
            "stylingRules": [
                {"name": "areas", "symbolizer": {"fill": {"color": "#eee"}}},
                {
                    "name": "roads",
                    "symbolizer": {"stroke": {"color": "#333", "width": 2}},
                },
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert [(lyr["id"], lyr["type"]) for lyr in out["layers"]] == [
        ("areas", "fill"),
        ("roads", "line"),
    ]
    assert out["layers"][0]["paint"] == {"fill-color": "#eee"}
    assert out["layers"][1]["paint"] == {"line-color": "#333", "line-width": 2}
    assert_maplibre_valid(out)


def test_symbolizerless_rule_is_dropped_not_an_error():
    """A rule that draws nothing (visibility only) is safe to omit — the
    common case of a cascade's base/gate rule, but also holds standalone
    (no nesting involved). Mirrors the SLD/SE writer's identical policy.
    """
    style = Style.from_dict(
        {"stylingRules": [{"name": "gate", "symbolizer": {"visibility": False}}]}
    )
    out = MaplibreWriter().write(style)
    assert out["layers"] == []
    assert_maplibre_valid(out)


def test_raster_only_rule_still_raises_not_dropped():
    """Unlike a genuinely empty rule, one carrying unsupported coverage/
    raster content must still raise — dropping it would silently lose
    data. ``colorChannels`` (band selection) is a genuine, permanent gap —
    see ``MaplibreWriter._raster``.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {"name": "dem", "symbolizer": {"colorChannels": ["B04", "B03", "B02"]}}
            ]
        }
    )
    with pytest.raises(NotImplementedError, match="colorChannels"):
        MaplibreWriter().write(style)


def test_single_channel_colormap_becomes_color_relief_layer():
    """``singleChannel`` (a plain field reference) + ``colorMap`` maps to a
    ``color-relief`` layer on a synthetic ``raster-dem`` source — the only
    coverage/raster shape this codec has a faithful MapLibre target for
    (see ``MaplibreWriter._raster``).
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "Elevation",
                    "symbolizer": {
                        "singleChannel": {"property": "elevation"},
                        "colorMap": [[0, [96, 136, 73]], [900, [226, 219, 167]]],
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert out["sources"]["cartosym-dem"]["type"] == "raster-dem"
    layer = out["layers"][0]
    assert layer["type"] == "color-relief"
    assert layer["source"] == "cartosym-dem"
    assert layer["paint"]["color-relief-color"] == [
        "interpolate",
        ["linear"],
        ["elevation"],
        0,
        "#608849",
        900,
        "#e2dba7",
    ]
    assert_maplibre_valid(out)


def test_single_channel_expression_is_rejected():
    """A computed band expression (band arithmetic, e.g. NDVI) has no
    MapLibre equivalent — only a plain field reference maps.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "ndvi",
                    "symbolizer": {
                        "singleChannel": {
                            "op": "/",
                            "args": [
                                {"property": "B08"},
                                {"property": "B04"},
                            ],
                        },
                        "colorMap": [[0, "red"], [1, "green"]],
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError, match="field reference"):
        MaplibreWriter().write(style)


def test_hillshading_sun_becomes_hillshade_layer():
    """``hillShading.sun.azimuth``/``.elevation`` maps to a ``hillshade``
    layer's illumination direction/altitude — the sun-elevation convention
    (0 at the horizon, 90 at zenith) matches ``hillshade-illumination-
    altitude`` directly.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "Elevation",
                    "symbolizer": {
                        "hillShading": {"sun": {"azimuth": 45.0, "elevation": 60.0}}
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    layer = out["layers"][0]
    assert layer["type"] == "hillshade"
    assert layer["source"] == "cartosym-dem"
    assert layer["paint"] == {
        "hillshade-illumination-direction": 45.0,
        "hillshade-illumination-altitude": 60.0,
    }
    assert_maplibre_valid(out)


def test_hillshading_alter_is_dropped_not_rejected():
    """Same cascade-flag reasoning as ``test_fill_alter_is_dropped_not_rejected``
    — ``hillShading.alter`` is not a rendering property either.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "Elevation",
                    "symbolizer": {
                        "hillShading": {
                            "sun": {"azimuth": 45.0, "elevation": 60.0},
                            "alter": True,
                        }
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert out["layers"][0]["paint"] == {
        "hillshade-illumination-direction": 45.0,
        "hillshade-illumination-altitude": 60.0,
    }
    assert_maplibre_valid(out)


def test_color_relief_and_hillshade_together_become_two_layers():
    """A symbolizer combining ``singleChannel``+``colorMap`` and
    ``hillShading`` (sun only) maps to two layers on the same synthetic
    ``raster-dem`` source, disambiguated with a ``-color-relief``/
    ``-hillshade`` suffix — same idiom as the vector multi-layer case.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "Elevation",
                    "symbolizer": {
                        "singleChannel": {"property": "elevation"},
                        "colorMap": [[0, "black"], [1, "white"]],
                        "hillShading": {"sun": {"azimuth": 0.0, "elevation": 45.0}},
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    ids = {layer["id"]: layer["type"] for layer in out["layers"]}
    assert ids == {
        "Elevation-color-relief": "color-relief",
        "Elevation-hillshade": "hillshade",
    }
    assert all(layer["source"] == "cartosym-dem" for layer in out["layers"])
    assert_maplibre_valid(out)


def test_hillshading_factor_is_rejected():
    """MapLibre's ``hillshade-exaggeration`` is a fixed 0-1 shading
    intensity, not the unbounded vertical-exaggeration z-factor
    CartoSym's ``factor`` is — no faithful unit conversion exists.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "Elevation",
                    "symbolizer": {
                        "hillShading": {
                            "factor": 56,
                            "sun": {"azimuth": 45.0, "elevation": 60.0},
                        }
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError, match="factor"):
        MaplibreWriter().write(style)


def test_hillshading_intensity_colormap_is_rejected():
    """A ``colorMap``/``opacityMap`` nested in ``hillShading`` ramps the
    shading *intensity* (0..1), not elevation — ``hillshade`` paint only
    exposes 3 fixed colours (shadow/highlight/accent), not a ramp.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "Elevation",
                    "symbolizer": {
                        "hillShading": {
                            "sun": {"azimuth": 45.0, "elevation": 60.0},
                            "colorMap": [[0, "black"], [0.5, "white"]],
                        }
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError, match="colorMap"):
        MaplibreWriter().write(style)


def test_coverage_symbolizer_cannot_combine_with_fill():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "x",
                    "symbolizer": {
                        "fill": {"color": "red"},
                        "singleChannel": {"property": "elevation"},
                        "colorMap": [[0, "black"], [1, "white"]],
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError, match="combine"):
        MaplibreWriter().write(style)


def test_datalayer_type_coverage_selector_is_dropped_on_a_raster_rule():
    """A ``sysId dataLayer.type = coverage`` conjunct is provably redundant
    once a rule is already routed to a raster/hillshade/color-relief layer
    — nothing else could have produced those. The mirror case,
    ``dataLayer.type = vector`` on a rule routed to a vector layer, is
    ``test_datalayer_type_vector_selector_is_dropped_on_a_vector_rule``;
    an unrelated ``sysId`` still rejects
    (``test_other_sysid_selector_is_still_rejected``).
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "Elevation",
                    "selector": {
                        "op": "=",
                        "args": [{"sysId": "dataLayer.type"}, "coverage"],
                    },
                    "symbolizer": {
                        "singleChannel": {"property": "elevation"},
                        "colorMap": [[0, "black"], [1, "white"]],
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert "filter" not in out["layers"][0]
    assert_maplibre_valid(out)


def test_nested_cascade_produces_independent_layers():
    """A cascading refinement (a selector-bearing nestedRules entry) has no
    MapLibre nesting equivalent — it must flatten into its own layer, AND-
    merged selector and merged symbolizer, same as the SLD/SE writer.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "Landuse",
                    "selector": {"op": "=", "args": [{"property": "type"}, "vector"]},
                    "symbolizer": {"visibility": False},
                    "nestedRules": [
                        {
                            "selector": {
                                "op": "=",
                                "args": [{"property": "FunctionCode"}, "park"],
                            },
                            "symbolizer": {"fill": {"color": "darkGreen"}},
                        }
                    ],
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    # the empty base/gate rule is dropped; one layer remains
    assert len(out["layers"]) == 1
    layer = out["layers"][0]
    assert layer["paint"] == {"fill-color": "darkGreen"}
    assert layer["filter"] == [
        "all",
        ["==", ["get", "type"], "vector"],
        ["==", ["get", "FunctionCode"], "park"],
    ]
    assert_maplibre_valid(out)


def test_unnamed_cascade_children_get_synthesized_ids():
    """A refinement usually only narrows the selector and carries no name
    of its own — it inherits its nearest named ancestor's, disambiguated
    with a positional suffix (a MapLibre layer id must be unique).
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "Landuse",
                    "symbolizer": {"visibility": False},
                    "nestedRules": [
                        {
                            "selector": {
                                "op": "=",
                                "args": [{"property": "K"}, "a"],
                            },
                            "symbolizer": {"fill": {"color": "red"}},
                        },
                        {
                            "selector": {
                                "op": "=",
                                "args": [{"property": "K"}, "b"],
                            },
                            "symbolizer": {"fill": {"color": "blue"}},
                        },
                    ],
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert [lyr["id"] for lyr in out["layers"]] == ["Landuse-1", "Landuse-2"]
    assert_maplibre_valid(out)


def test_explicitly_named_cascade_child_keeps_its_own_name():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "Landuse",
                    "symbolizer": {"visibility": False},
                    "nestedRules": [
                        {
                            "name": "Parks",
                            "selector": {
                                "op": "=",
                                "args": [{"property": "K"}, "park"],
                            },
                            "symbolizer": {"fill": {"color": "green"}},
                        }
                    ],
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert [lyr["id"] for lyr in out["layers"]] == ["Parks"]


def test_selectorless_nested_rule_is_rejected():
    """A selector-less nestedRules entry is an OGC 'else' rule — MapLibre
    has no equivalent concept, so this must raise rather than be dropped.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "Roads",
                    "symbolizer": {"stroke": {"color": "red"}},
                    "nestedRules": [{"symbolizer": {"stroke": {"color": "gray"}}}],
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError, match="'else' rule"):
        MaplibreWriter().write(style)


def test_visibility_false_becomes_layout_none():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "hidden",
                    "symbolizer": {"visibility": False, "fill": {"color": "red"}},
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert out["layers"][0]["layout"] == {"visibility": "none"}


def test_circle_marker_becomes_a_circle_layer():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "pts",
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Circle",
                                    "fill": {"color": "#f00"},
                                    "outline": {"color": "#000", "thickness": 1},
                                    "radius": 6,
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    layer = out["layers"][0]
    assert layer["type"] == "circle"
    assert layer["paint"] == {
        "circle-color": "#f00",
        "circle-stroke-color": "#000",
        "circle-stroke-width": 1,
        "circle-radius": 6,
    }
    assert_maplibre_valid(out)


def test_dot_marker_becomes_a_circle_layer():
    """A ``1-core`` ``Dot`` (stroke-only: color + size) maps to a ``circle``
    layer — ``color`` as the fill, ``size / 2`` as the radius (``size`` is
    a diameter, matching the SLD/SE codec's own ``Dot`` mapping).
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "pts",
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {"type": "Dot", "color": "white", "size": {"px": 10}}
                            ]
                        }
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    layer = out["layers"][0]
    assert layer["type"] == "circle"
    assert layer["paint"] == {"circle-color": "white", "circle-radius": 5}
    assert_maplibre_valid(out)


def test_dot_size_property_ref_divides_symbolically():
    """``Dot.size`` as a ``PropertyRef`` — unlike a literal, ``size / 2``
    can't divide in Python, so it's wrapped in an ``ArithmeticExpression``
    and written through ``_literal`` instead (matching ``Circle.radius``,
    which already supported an expression here, since it has no such
    halving and maps straight through ``_literal``).
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "pts",
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Dot",
                                    "color": "white",
                                    "size": {"property": "sizeAttr"},
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    layer = out["layers"][0]
    assert layer["paint"]["circle-radius"] == ["/", ["get", "sizeAttr"], 2]
    assert_maplibre_valid(out)

    from pycartosym.codecs.maplibre.reader import MaplibreReader

    back = MaplibreReader().read(out)
    el = back.styling_rules[0].symbolizer.marker.elements[0]
    assert el["type"] == "Circle"
    assert el["radius"] == {"op": "/", "args": [{"property": "sizeAttr"}, 2]}


def test_dot_size_viz_sd_samples_a_step_lut():
    """``Dot.size`` as a ``viz.sd``-only expression still qualifies for the
    step-LUT sampling (:func:`._expressions.step_lut_for_viz_sd`) even
    wrapped in the ``/ 2`` this codec adds — the whole
    ``ArithmeticExpression`` is still built only from ``viz.sd`` and
    numeric literals.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "pts",
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Dot",
                                    "color": "white",
                                    "size": {"sysId": "viz.sd"},
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    radius = out["layers"][0]["paint"]["circle-radius"]
    assert radius[:2] == ["step", ["zoom"]]
    assert_maplibre_valid(out)


def test_dot_size_non_expression_string_still_raises():
    """A ``Dot.size`` that is neither a literal px value nor a recognised
    expression shape (a plain garbage string, say) must still raise —
    regression guard for the new expression-coercion path above
    accidentally treating an unrelated string as a divisible value.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "pts",
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Dot",
                                    "color": "white",
                                    "size": "not-a-number",
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError):
        MaplibreWriter().write(style)


def test_dot_offset_position_is_rejected():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "pts",
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Dot",
                                    "color": "white",
                                    "size": {"px": 10},
                                    "position": {"x": 5, "y": 0},
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError):
        MaplibreWriter().write(style)


def test_mixed_dot_and_text_marker_becomes_circle_and_symbol_layers():
    """``marker.elements`` mixing a ``Dot`` with a ``Text`` (e.g. from a
    cascaded ``marker.elements[1]: Text {...}`` override) — one layer per
    element, in list order.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "pts",
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {"type": "Dot", "color": "white", "size": {"px": 10}},
                                {"type": "Text", "text": "Name"},
                            ]
                        }
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert [(lyr["id"], lyr["type"]) for lyr in out["layers"]] == [
        ("pts-circle", "circle"),
        ("pts-symbol", "symbol"),
    ]
    assert out["layers"][0]["paint"] == {"circle-color": "white", "circle-radius": 5}
    assert out["layers"][1]["layout"] == {"text-field": "Name"}
    assert_maplibre_valid(out)


def test_multi_element_marker_becomes_several_circle_layers():
    """Several marker elements have no single-``circle``-layer equivalent
    (one MapLibre layer draws one primitive per feature) — each element
    becomes its own ``circle`` layer, id-suffixed with a running index
    since the ``-circle`` kind suffix alone is no longer unique.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "pts",
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {"type": "Dot", "color": "white", "size": {"px": 10}},
                                {"type": "Dot", "color": "orange", "size": {"px": 8}},
                            ]
                        }
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert [(lyr["id"], lyr["type"]) for lyr in out["layers"]] == [
        ("pts-circle-1", "circle"),
        ("pts-circle-2", "circle"),
    ]
    assert out["layers"][0]["paint"]["circle-color"] == "white"
    assert out["layers"][1]["paint"]["circle-color"] == "orange"
    assert_maplibre_valid(out)


def test_text_marker_element_becomes_a_symbol_layer():
    """A ``Text`` element inside ``marker.elements`` (not ``label.elements``)
    maps the same as a label ``Text`` — element type, not container,
    decides the layer (a cascaded indexed override, e.g.
    ``marker.elements[1]: Text {...}``, produces exactly this shape).
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "t",
                    "symbolizer": {
                        "marker": {"elements": [{"type": "Text", "text": "x"}]}
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    layer = out["layers"][0]
    assert layer["type"] == "symbol"
    assert layer["layout"] == {"text-field": "x"}
    assert_maplibre_valid(out)


def test_label_text_becomes_a_symbol_layer():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "labels",
                    "symbolizer": {
                        "label": {
                            "elements": [
                                {
                                    "type": "Text",
                                    "text": {"property": "name"},
                                    "position": {"x": 0, "y": 1.5},
                                    "alignment": ["center", "top"],
                                    "font": {
                                        "face": "Open Sans Semibold",
                                        "size": 12,
                                        "color": "#1077b0",
                                        "outline": {"color": "#fff", "size": 1},
                                    },
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    layer = out["layers"][0]
    assert layer["type"] == "symbol"
    assert layer["layout"] == {
        "text-field": "{name}",
        "text-offset": [0, 1.5],
        "text-anchor": "top",
        "text-font": ["Open Sans Semibold"],
        "text-size": 12,
    }
    assert layer["paint"] == {
        "text-color": "#1077b0",
        "text-halo-color": "#fff",
        "text-halo-width": 1,
    }
    assert_maplibre_valid(out)


def test_font_size_unwraps_px_unit_dict():
    """``Font.size`` as ``{"px": N}`` unwraps to a bare number, same as

    ``stroke.width``/``Circle.radius``/``Dot.size`` — regression test for a
    bug found retesting the SLD→MapLibre corpus. The SLD reader itself no
    longer produces this shape (fixed at the source — it now emits the
    schema-correct bare number, matching ``font.size``'s ``numericExpression``
    type), but this input shape remains valid at the Pydantic model level
    (``FlexibleSize`` accepts a ``UnitValue``/dict), so the defensive unwrap
    stays worth covering directly.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "Labels",
                    "symbolizer": {
                        "label": {
                            "elements": [
                                {
                                    "type": "Text",
                                    "text": {"property": "name"},
                                    "font": {"size": {"px": 12}},
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert out["layers"][0]["layout"]["text-size"] == 12
    assert_maplibre_valid(out)


def test_icon_marker_becomes_a_symbol_layer():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "poi",
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Image",
                                    "image": {"id": "dot.sdf"},
                                    "opacity": 0.8,
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    layer = out["layers"][0]
    assert layer["type"] == "symbol"
    assert layer["layout"] == {"icon-image": "dot.sdf"}
    assert layer["paint"] == {"icon-opacity": 0.8}
    assert_maplibre_valid(out)


@pytest.mark.parametrize(
    "fx, fy, anchor",
    [
        (0, 0, "bottom-left"),
        (50, 0, "bottom"),
        (100, 0, "bottom-right"),
        (0, 50, "left"),
        (50, 50, "center"),
        (100, 50, "right"),
        (0, 100, "top-left"),
        (50, 100, "top"),
        (100, 100, "top-right"),
    ],
)
def test_icon_marker_hot_spot_maps_to_icon_anchor(fx, fy, anchor):
    """``hotSpot`` is a fraction within the image, (0,0) lower-left/(1,1)
    upper-right (the ``se:AnchorPoint`` convention) — that lines up
    unflipped with which of the 9 MapLibre ``icon-anchor`` keywords
    describes the same corner/edge/center of the icon.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "poi",
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Image",
                                    "image": {"id": "dot.sdf"},
                                    "hotSpot": [{"pc": fx}, {"pc": fy}],
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert out["layers"][0]["layout"]["icon-anchor"] == anchor
    assert_maplibre_valid(out)


def test_icon_marker_transform_orientation_maps_to_icon_rotate():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "poi",
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Image",
                                    "image": {"id": "dot.sdf"},
                                    "transform": {"orientation": 15},
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert out["layers"][0]["layout"]["icon-rotate"] == 15
    assert_maplibre_valid(out)


def test_icon_marker_transform_scaling_raises():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "poi",
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Image",
                                    "image": {"id": "dot.sdf"},
                                    "transform": {"scaling": {"x": 2, "y": 2}},
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError):
        MaplibreWriter().write(style)


def test_circle_transform_raises():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "poi",
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Circle",
                                    "position": {"x": 0, "y": 0},
                                    "fill": {"color": "red"},
                                    "radius": {"px": 5},
                                    "transform": {"orientation": 45},
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError):
        MaplibreWriter().write(style)


def test_icon_marker_hot_spot_off_grid_is_rejected():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "poi",
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Image",
                                    "image": {"id": "dot.sdf"},
                                    "hotSpot": [{"pc": 30}, {"pc": 50}],
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError):
        MaplibreWriter().write(style)


def test_icon_marker_hot_spot_non_percent_unit_is_rejected():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "poi",
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Image",
                                    "image": {"id": "dot.sdf"},
                                    "hotSpot": [{"px": 5}, {"px": 5}],
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError):
        MaplibreWriter().write(style)


def test_icon_marker_tint_maps_to_icon_color():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "poi",
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Image",
                                    "image": {"id": "dot.sdf"},
                                    "tint": "#000000",
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    layer = out["layers"][0]
    assert layer["paint"] == {"icon-color": "#000000"}
    assert_maplibre_valid(out)


def test_icon_marker_black_tint_is_still_rejected():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "poi",
                    "symbolizer": {
                        "marker": {
                            "elements": [
                                {
                                    "type": "Image",
                                    "image": {"id": "dot.sdf"},
                                    "blackTint": "#000000",
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError):
        MaplibreWriter().write(style)


def test_fill_pattern_image_maps_to_fill_pattern_paint():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "landcover",
                    "symbolizer": {
                        "fill": {"pattern": {"type": "Image", "image": {"id": "grass"}}}
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    layer = out["layers"][0]
    assert layer["type"] == "fill"
    assert layer["paint"] == {"fill-pattern": "grass"}
    assert_maplibre_valid(out)


def test_fill_pattern_non_image_graphic_is_rejected():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "landcover",
                    "symbolizer": {
                        "fill": {
                            "pattern": {
                                "type": "Shape",
                                "outline": {"color": "black"},
                            }
                        }
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError):
        MaplibreWriter().write(style)


def test_label_and_icon_marker_share_one_symbol_layer():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "poi",
                    "symbolizer": {
                        "label": {"elements": [{"type": "Text", "text": "Foo"}]},
                        "marker": {
                            "elements": [{"type": "Image", "image": {"id": "dot.sdf"}}]
                        },
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert len(out["layers"]) == 1
    layer = out["layers"][0]
    assert layer["type"] == "symbol"
    assert layer["layout"]["text-field"] == "Foo"
    assert layer["layout"]["icon-image"] == "dot.sdf"
    assert_maplibre_valid(out)


def test_multi_element_label_becomes_several_symbol_layers():
    """Several label elements have no single-layer equivalent either — one
    ``symbol`` layer per element, same id-suffix scheme as a multi-element
    marker.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "labels",
                    "symbolizer": {
                        "label": {
                            "elements": [
                                {"type": "Text", "text": "a"},
                                {"type": "Text", "text": "b"},
                            ]
                        }
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert [(lyr["id"], lyr["type"]) for lyr in out["layers"]] == [
        ("labels-symbol-1", "symbol"),
        ("labels-symbol-2", "symbol"),
    ]
    assert out["layers"][0]["layout"]["text-field"] == "a"
    assert out["layers"][1]["layout"]["text-field"] == "b"
    assert_maplibre_valid(out)


def test_image_label_element_becomes_a_symbol_layer():
    """An ``Image`` element inside ``label.elements`` maps the same as a
    marker ``Image`` — element type, not container, decides the layer.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "labels",
                    "symbolizer": {
                        "label": {"elements": [{"type": "Image", "image": {"id": "x"}}]}
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    layer = out["layers"][0]
    assert layer["type"] == "symbol"
    assert layer["layout"] == {"icon-image": "x"}
    assert_maplibre_valid(out)


def test_label_with_circle_marker_becomes_two_layers():
    """A label ``Text`` plus a marker ``Circle`` (not the merge-eligible
    single-``Image``-marker case) becomes two point layers: the marker's
    circle layer, then the label's symbol layer.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "labels",
                    "symbolizer": {
                        "label": {"elements": [{"type": "Text", "text": "a"}]},
                        "marker": {"elements": [{"type": "Circle", "radius": 5}]},
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert [(lyr["id"], lyr["type"]) for lyr in out["layers"]] == [
        ("labels-circle", "circle"),
        ("labels-symbol", "symbol"),
    ]
    assert out["layers"][0]["paint"] == {"circle-radius": 5}
    assert out["layers"][1]["layout"] == {"text-field": "a"}
    assert_maplibre_valid(out)


def test_label_with_fill_becomes_two_layers():
    """A symbolizer with both a label and a fill has no single-layer
    MapLibre equivalent — it expands to a ``fill`` layer and a ``symbol``
    layer, id-suffixed since the rule name alone is no longer unique.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "labels",
                    "symbolizer": {
                        "label": {"elements": [{"type": "Text", "text": "a"}]},
                        "fill": {"color": "red"},
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert [(lyr["id"], lyr["type"]) for lyr in out["layers"]] == [
        ("labels-fill", "fill"),
        ("labels-symbol", "symbol"),
    ]
    assert out["layers"][0]["paint"] == {"fill-color": "red"}
    assert out["layers"][1]["layout"] == {"text-field": "a"}
    assert_maplibre_valid(out)


def test_label_text_transform_orientation_maps_to_text_rotate():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "labels",
                    "symbolizer": {
                        "label": {
                            "elements": [
                                {
                                    "type": "Text",
                                    "text": "a",
                                    "transform": {"orientation": -45},
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert out["layers"][0]["layout"]["text-rotate"] == -45
    assert_maplibre_valid(out)


def test_label_text_transform_translation_raises():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "labels",
                    "symbolizer": {
                        "label": {
                            "elements": [
                                {
                                    "type": "Text",
                                    "text": "a",
                                    "transform": {"translation": {"x": 1, "y": 1}},
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError):
        MaplibreWriter().write(style)


def test_font_bold_is_rejected():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "labels",
                    "symbolizer": {
                        "label": {
                            "elements": [
                                {
                                    "type": "Text",
                                    "text": "a",
                                    "font": {"bold": True},
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError):
        MaplibreWriter().write(style)


def test_font_bold_italic_underline_false_is_dropped_not_rejected():
    """A literal ``false`` means no more than MapLibre's own default
    (roman, non-underlined text) — nothing to map, unlike a literal
    ``true`` (``test_font_bold_is_rejected``), which stays a real gap.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "labels",
                    "symbolizer": {
                        "label": {
                            "elements": [
                                {
                                    "type": "Text",
                                    "text": "a",
                                    "font": {
                                        "face": "Open Sans",
                                        "bold": False,
                                        "italic": False,
                                        "underline": False,
                                    },
                                }
                            ]
                        }
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert out["layers"][0]["layout"]["text-font"] == ["Open Sans"]
    assert_maplibre_valid(out)


def test_fill_alter_is_dropped_not_rejected():
    """``fill.alter`` is the CartoSym cascade's own "does this override an
    inherited definition" flag (see ``models/base.py::AlterMixin``), not a
    rendering property — the cascade is already flattened by the time the
    writer sees the symbolizer, so it carries no further meaning here.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "x",
                    "symbolizer": {"fill": {"color": "red", "alter": True}},
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert out["layers"][0]["paint"] == {"fill-color": "red"}
    assert_maplibre_valid(out)


def test_stroke_alter_is_dropped_not_rejected():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "x",
                    "symbolizer": {
                        "stroke": {"color": "black", "width": 2, "alter": True}
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert out["layers"][0]["paint"] == {"line-color": "black", "line-width": 2}
    assert_maplibre_valid(out)


def test_rule_selector_becomes_layer_filter():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "x",
                    "selector": {"op": "=", "args": [{"property": "k"}, "v"]},
                    "symbolizer": {"fill": {"color": "red"}},
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert out["layers"][0]["filter"] == ["==", ["get", "k"], "v"]
    assert list(out["layers"][0]) == ["id", "type", "source", "filter", "paint"]
    assert_maplibre_valid(out)


def test_multi_layer_rule_shares_filter_and_visibility():
    """``filter``/``visibility`` apply identically to every layer a single
    rule expands into, not just the first.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "x",
                    "selector": {"op": "=", "args": [{"property": "k"}, "v"]},
                    "symbolizer": {
                        "visibility": False,
                        "fill": {"color": "red"},
                        "stroke": {"color": "black", "width": 3},
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert len(out["layers"]) == 2
    for layer in out["layers"]:
        assert layer["filter"] == ["==", ["get", "k"], "v"]
        assert layer["layout"] == {"visibility": "none"}
    assert_maplibre_valid(out)


def test_datalayer_id_selector_is_dropped_not_an_error():
    """A ``sysId dataLayer.id = <name>`` conjunct is the implicit
    self-reference a CartoSym-CSS ``RuleName[...]`` rule always carries —
    redundant with the MapLibre layer's own ``id`` and with no
    data-source concept to bind to in this codec — dropped rather than
    raised on, unlike any other ``sysId``.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "x",
                    "selector": {"op": "=", "args": [{"sysId": "dataLayer.id"}, "L"]},
                    "symbolizer": {"fill": {"color": "red"}},
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert "filter" not in out["layers"][0]
    assert_maplibre_valid(out)


def test_datalayer_id_conjunct_dropped_among_siblings():
    """The same conjunct, AND-combined with a real property predicate,
    is stripped out while the rest of the filter survives.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "x",
                    "selector": {
                        "op": "and",
                        "args": [
                            {"op": "=", "args": [{"sysId": "dataLayer.id"}, "L"]},
                            {"op": "=", "args": [{"property": "k"}, "v"]},
                        ],
                    },
                    "symbolizer": {"fill": {"color": "red"}},
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert out["layers"][0]["filter"] == ["==", ["get", "k"], "v"]
    assert_maplibre_valid(out)


def test_datalayer_type_vector_selector_is_dropped_on_a_vector_rule():
    """Mirror of ``test_datalayer_type_coverage_selector_is_dropped_on_a_raster_rule``:
    ``sysId dataLayer.type = vector`` is provably redundant once a rule is
    routed to a fill/line/circle/symbol/background layer — nothing else
    could have produced those.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "x",
                    "selector": {
                        "op": "=",
                        "args": [{"sysId": "dataLayer.type"}, "vector"],
                    },
                    "symbolizer": {"fill": {"color": "red"}},
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert "filter" not in out["layers"][0]
    assert_maplibre_valid(out)


def test_other_sysid_selector_is_still_rejected():
    """A ``sysId`` other than ``dataLayer.id``/``dataLayer.type``/``viz.sd``
    carries real information this codec has no filter for — still raises.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "x",
                    "selector": {
                        "op": "=",
                        "args": [{"sysId": "dataLayer.owner"}, "someone"],
                    },
                    "symbolizer": {"fill": {"color": "red"}},
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError):
        MaplibreWriter().write(style)


def test_fill_with_full_stroke_becomes_fill_and_line_layers():
    """A stroke with a ``width``/``opacity`` (not just a plain outline
    colour) has no ``fill-outline-color`` equivalent — it gets its own
    ``line`` layer alongside the ``fill`` one, id-suffixed.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "x",
                    "symbolizer": {
                        "fill": {"color": "red"},
                        "stroke": {"color": "black", "width": 3},
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert [(lyr["id"], lyr["type"]) for lyr in out["layers"]] == [
        ("x-fill", "fill"),
        ("x-line", "line"),
    ]
    assert out["layers"][0]["paint"] == {"fill-color": "red"}
    assert out["layers"][1]["paint"] == {"line-color": "black", "line-width": 3}
    assert_maplibre_valid(out)


def test_fill_with_plain_outline_stroke_stays_one_layer():
    """A stroke with only a ``color`` (no ``width``/``opacity``) still
    inlines into ``fill-outline-color`` — no split, unchanged behaviour.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "x",
                    "symbolizer": {
                        "fill": {"color": "red"},
                        "stroke": {"color": "black"},
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert [(lyr["id"], lyr["type"]) for lyr in out["layers"]] == [("x", "fill")]
    assert out["layers"][0]["paint"] == {
        "fill-color": "red",
        "fill-outline-color": "black",
    }
    assert_maplibre_valid(out)


def test_circle_marker_with_fill_becomes_two_layers():
    """A symbolizer with both a marker and a fill/stroke needs several
    MapLibre layers too — same split, ``circle`` instead of ``symbol``.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "pts",
                    "symbolizer": {
                        "fill": {"color": "red"},
                        "marker": {"elements": [{"type": "Circle", "radius": 5}]},
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert [(lyr["id"], lyr["type"]) for lyr in out["layers"]] == [
        ("pts-fill", "fill"),
        ("pts-circle", "circle"),
    ]
    assert_maplibre_valid(out)


def test_background_vendor_tag_becomes_background_layer():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "bg",
                    "symbolizer": {
                        "fill": {"color": "red"},
                        "vendor.maplibre.layer-type": "background",
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    assert out["sources"] == {}
    assert out["layers"] == [
        {"id": "bg", "type": "background", "paint": {"background-color": "red"}}
    ]
    assert_maplibre_valid(out)


def test_viz_sd_selector_becomes_zoom_range():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "fill",
                    "selector": {
                        "op": "and",
                        "args": [
                            {
                                "op": "<=",
                                "args": [
                                    {"sysId": "viz.sd"},
                                    scale_denominator_from_zoom(10),
                                ],
                            },
                            {
                                "op": ">",
                                "args": [
                                    {"sysId": "viz.sd"},
                                    scale_denominator_from_zoom(12),
                                ],
                            },
                        ],
                    },
                    "symbolizer": {"fill": {"color": "red"}},
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    layer = out["layers"][0]
    assert layer["minzoom"] == 10
    assert layer["maxzoom"] == 12
    assert "filter" not in layer
    assert_maplibre_valid(out)


def test_viz_sd_selector_merges_with_residual_filter():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "fill",
                    "selector": {
                        "op": "and",
                        "args": [
                            {
                                "op": "<=",
                                "args": [
                                    {"sysId": "viz.sd"},
                                    scale_denominator_from_zoom(10),
                                ],
                            },
                            {"op": "=", "args": [{"property": "class"}, "water"]},
                        ],
                    },
                    "symbolizer": {"fill": {"color": "red"}},
                }
            ]
        }
    )
    layer = MaplibreWriter().write(style)["layers"][0]
    assert layer["minzoom"] == 10
    assert layer["filter"] == ["==", ["get", "class"], "water"]


def test_viz_sd_strict_lower_bound_becomes_a_zoom_filter():
    """``viz.sd < N`` has no minzoom/maxzoom shape (only ``<=``/``>`` do) —
    it becomes a ``["zoom"]`` filter conjunct instead (see
    ``_zoom.zoom_filter_conjunct``), not a minzoom/maxzoom layer property.
    """
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "fill",
                    "selector": {"op": "<", "args": [{"sysId": "viz.sd"}, 100000]},
                    "symbolizer": {"fill": {"color": "red"}},
                }
            ]
        }
    )
    layer = MaplibreWriter().write(style)["layers"][0]
    assert "minzoom" not in layer
    assert "maxzoom" not in layer
    assert layer["filter"] == [">", ["zoom"], zoom_from_scale_denominator(100000)]
    assert_maplibre_valid(MaplibreWriter().write(style))


def test_background_with_zoom_range_selector_is_kept():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "bg",
                    "selector": {
                        "op": "<=",
                        "args": [{"sysId": "viz.sd"}, scale_denominator_from_zoom(5)],
                    },
                    "symbolizer": {
                        "fill": {"color": "red"},
                        "vendor.maplibre.layer-type": "background",
                    },
                }
            ]
        }
    )
    out = MaplibreWriter().write(style)
    layer = out["layers"][0]
    assert layer["minzoom"] == 5
    assert "filter" not in layer
    assert_maplibre_valid(out)


def test_background_with_stroke_is_rejected():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "bg",
                    "symbolizer": {
                        "fill": {"color": "red"},
                        "stroke": {"color": "black"},
                        "vendor.maplibre.layer-type": "background",
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError):
        MaplibreWriter().write(style)


def test_background_with_selector_is_rejected():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "bg",
                    "selector": {"op": "=", "args": [{"property": "k"}, "v"]},
                    "symbolizer": {
                        "fill": {"color": "red"},
                        "vendor.maplibre.layer-type": "background",
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError):
        MaplibreWriter().write(style)


def test_unrecognised_vendor_extension_is_rejected():
    style = Style.from_dict(
        {
            "stylingRules": [
                {
                    "name": "x",
                    "symbolizer": {
                        "fill": {"color": "red"},
                        "vendor.geoserver.group": "layers",
                    },
                }
            ]
        }
    )
    with pytest.raises(NotImplementedError):
        MaplibreWriter().write(style)


def test_json_serialisable():
    style = MaplibreReader().read(_ATOMIC / "fill-color-literal.json")
    json.dumps(MaplibreWriter().write(style))


@pytest.mark.parametrize(
    "expr",
    [
        ["get", "cls"],
        ["case", ["get", "big"], "#f00", "#00f"],
        ["match", ["get", "cls"], "park", "#0f0", "water", "#00f", "#888"],
        ["step", ["get", "rank"], "#eee", 3, "#aaa", 6, "#444"],
        ["interpolate", ["linear"], ["get", "zoom"], 0, "#fff", 10, "#000"],
        ["coalesce", ["get", "override"], ["get", "cls"], "#888"],
    ],
)
def test_fill_layer_value_expression_round_trip(expr):
    """A value expression on fill-color read → write → read is a model
    fixed point, and the written-back style is spec-valid MapLibre.
    """
    read = MaplibreReader()
    style = read.read(
        {
            "version": 8,
            "sources": {},
            "layers": [
                {
                    "id": "areas",
                    "type": "fill",
                    "source": "s",
                    "paint": {"fill-color": expr},
                }
            ],
        }
    )
    out = MaplibreWriter().write(style)
    assert_maplibre_valid(out)
    again = read.read(out)
    assert again.to_dict() == style.to_dict()


class TestStepZoomRecombination:
    """N ``base-1``/``base-2``/… rules → one ``step(["zoom"])`` layer.

    Inverse of ``TestStepZoomExplosion`` in ``test_maplibre_reader.py``.
    """

    def test_single_property_recombines_into_one_step_layer(self):
        style = {
            "version": 8,
            "sources": {},
            "layers": [
                {
                    "id": "line",
                    "type": "line",
                    "source": "s",
                    "paint": {
                        "line-color": ["step", ["zoom"], "red", 12, "blue", 15, "green"]
                    },
                }
            ],
        }
        read = MaplibreReader()
        parsed = read.read(style)
        assert len(parsed.styling_rules) == 3
        out = MaplibreWriter().write(parsed)
        assert_maplibre_valid(out)
        assert len(out["layers"]) == 1
        layer = out["layers"][0]
        assert layer["id"] == "line"
        assert layer["paint"]["line-color"] == [
            "step",
            ["zoom"],
            "red",
            12,
            "blue",
            15,
            "green",
        ]
        assert "minzoom" not in layer
        assert "maxzoom" not in layer
        # Reading the recombined output back gives an equivalent Style
        # (the same 3-way split the original input would have produced).
        again = read.read(out)
        assert [
            r["symbolizer"]["stroke"]["color"] for r in again.to_dict()["stylingRules"]
        ] == ["red", "blue", "green"]

    def test_two_properties_with_different_breakpoints_recombine(self):
        style = {
            "version": 8,
            "sources": {},
            "layers": [
                {
                    "id": "l",
                    "type": "symbol",
                    "source": "s",
                    "minzoom": 10,
                    "layout": {
                        "text-field": "x",
                        "icon-image": ["step", ["zoom"], "a", 15, "b", 16, "c"],
                    },
                    "paint": {
                        "icon-opacity": ["step", ["zoom"], 0.2, 13, 0.5, 14, 1.0]
                    },
                }
            ],
        }
        read = MaplibreReader()
        parsed = read.read(style)
        assert len(parsed.styling_rules) == 5
        out = MaplibreWriter().write(parsed)
        assert_maplibre_valid(out)
        assert len(out["layers"]) == 1
        layer = out["layers"][0]
        assert layer["id"] == "l"
        assert layer["minzoom"] == 10
        assert "maxzoom" not in layer
        # Model fixed point over the full recombination round-trip.
        again = read.read(out)
        assert again.to_dict() == parsed.to_dict()

    def test_gap_in_index_sequence_is_not_combined(self):
        style = Style.from_dict(
            {
                "stylingRules": [
                    {
                        "name": "l-1",
                        "selector": {
                            "op": "<=",
                            "args": [{"sysId": "viz.sd"}, 100000],
                        },
                        "symbolizer": {"fill": {"color": "red"}},
                    },
                    {
                        "name": "l-3",
                        "selector": {"op": ">", "args": [{"sysId": "viz.sd"}, 100000]},
                        "symbolizer": {"fill": {"color": "blue"}},
                    },
                ]
            }
        )
        out = MaplibreWriter().write(style)
        assert [layer["id"] for layer in out["layers"]] == ["l-1", "l-3"]

    def test_differing_extra_key_prevents_combination(self):
        # l-2 has fill-opacity, l-1 doesn't -> not a pure step-of-one-value
        # difference, so this codec doesn't guess a step reconstruction.
        style = Style.from_dict(
            {
                "stylingRules": [
                    {
                        "name": "l-1",
                        "selector": {
                            "op": "<=",
                            "args": [{"sysId": "viz.sd"}, 100000],
                        },
                        "symbolizer": {"fill": {"color": "red"}},
                    },
                    {
                        "name": "l-2",
                        "selector": {"op": ">", "args": [{"sysId": "viz.sd"}, 100000]},
                        "symbolizer": {"fill": {"color": "red", "opacity": 0.5}},
                    },
                ]
            }
        )
        out = MaplibreWriter().write(style)
        assert [layer["id"] for layer in out["layers"]] == ["l-1", "l-2"]

    def test_non_contiguous_zoom_ranges_are_not_combined(self):
        # A gap between segment 1's maxzoom and segment 2's minzoom - not
        # a shape the reader's own explosion would ever produce.
        style = Style.from_dict(
            {
                "stylingRules": [
                    {
                        "name": "l-1",
                        "selector": {
                            "op": ">",
                            "args": [{"sysId": "viz.sd"}, 200000],
                        },
                        "symbolizer": {"fill": {"color": "red"}},
                    },
                    {
                        "name": "l-2",
                        "selector": {
                            "op": "<=",
                            "args": [{"sysId": "viz.sd"}, 100000],
                        },
                        "symbolizer": {"fill": {"color": "blue"}},
                    },
                ]
            }
        )
        out = MaplibreWriter().write(style)
        assert [layer["id"] for layer in out["layers"]] == ["l-1", "l-2"]
