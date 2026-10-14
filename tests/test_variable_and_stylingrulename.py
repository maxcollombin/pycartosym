from pycartosym.models.styles import Style
from pycartosym.parser import CartoSymParser


def test_variable_parsing():
    """Test that @variable definitions are extracted from cscss."""
    cscss = """
    @roadColor = gray;

    Roads[type = 'highway']
    {
       stroke: { color: @roadColor, width: 2px };
    }
    """
    parser = CartoSymParser()
    style: Style = parser.parse_string_to_pydantic(cscss)

    # Variable must be extracted
    assert style.variables is not None, "variables should not be None"
    assert len(style.variables) == 1
    assert style.variables[0].name == "roadColor"
    assert style.variables[0].value == "gray"


def test_styling_rule_name_parsing():
    """Test that .name 'value' (rule ``name``) is extracted from cscss."""
    cscss = """
    Roads[type = 'highway']
    {
       .name 'Highways'
       fill: { color: red };
    }
    """
    parser = CartoSymParser()
    style: Style = parser.parse_string_to_pydantic(cscss)

    assert len(style.styling_rules) >= 1
    rule = style.styling_rules[0]
    # the explicit .name is extracted
    assert rule.name == "Highways", f"Expected name='Highways', got {rule.name!r}"
    # Selector and symbolizer should still be present
    assert rule.selector is not None
    assert rule.symbolizer is not None


def test_variable_and_stylingrulename_combined():
    """Test variables and stylingRuleName together in a realistic cscss."""
    cscss = """
    @roadColor = gray;

    Roads[type = 'highway']
    {
       .name 'Highways'
       stroke: { color: @roadColor, width: 2px };
    }
    """
    parser = CartoSymParser()
    style: Style = parser.parse_string_to_pydantic(cscss)

    # Variables
    assert style.variables is not None
    assert len(style.variables) == 1
    assert style.variables[0].name == "roadColor"
    assert style.variables[0].value == "gray"

    # Rule name
    rule = style.styling_rules[0]
    assert rule.name == "Highways"

    # Symbolizer with stroke
    assert rule.symbolizer is not None


def test_name_absent_when_not_in_source():
    """With no ``.name`` in the cscss, CS-JSON must not contain ``name``."""
    cscss = """
    Roads[type = 'highway']
    {
       fill: { color: red };
    }
    """
    parser = CartoSymParser()
    style: Style = parser.parse_string_to_pydantic(cscss)
    rule = style.styling_rules[0]

    # model attribute should be None
    assert rule.name is None

    # serialized dict must not contain the key
    d = rule.to_dict()
    assert (
        "name" not in d
    ), f"'name' should not appear in JSON when absent from source, got: {d}"


def test_name_present_when_in_source():
    """With ``.name 'X'`` in the cscss, CS-JSON must contain that name."""
    cscss = """
    Roads[type = 'highway']
    {
       .name 'MyRoads'
       fill: { color: red };
    }
    """
    parser = CartoSymParser()
    style: Style = parser.parse_string_to_pydantic(cscss)
    rule = style.styling_rules[0]

    d = rule.to_dict()
    assert (
        d.get("name") == "MyRoads"
    ), f"Expected name='MyRoads' in serialized dict, got: {d}"


def test_field_order_in_serialized_json():
    """JSON key order: name → selector → symbolizer → nestedRules."""
    cscss = """
    Landuse[type = 'forest']
    {
       .name 'Forests'
       fill: { color: green };

       Deep[level > 5]
       {
          fill: { color: darkgreen };
       }
    }
    """
    parser = CartoSymParser()
    style: Style = parser.parse_string_to_pydantic(cscss)
    rule = style.styling_rules[0]

    d = rule.to_dict()
    keys = list(d.keys())

    # nestedRules must come after selector and symbolizer
    if "nestedRules" in keys and "selector" in keys:
        assert keys.index("selector") < keys.index(
            "nestedRules"
        ), f"'selector' should appear before 'nestedRules', got order: {keys}"
    if "nestedRules" in keys and "symbolizer" in keys:
        assert keys.index("symbolizer") < keys.index(
            "nestedRules"
        ), f"'symbolizer' should appear before 'nestedRules', got order: {keys}"


def test_stylingrulename_roundtrip():
    """A ``name`` must survive a .cscss → CS-JSON → .cscss round-trip."""
    from pycartosym.converter import Converter

    cscss_src = """
    [TestLayer]
    {
       .name 'My Layer Name'
       visibility: true;
    }
    """
    converter = Converter()
    # Forward: CSCSS → CS-JSON
    cs_json = converter.cscss_to_csjson(cscss_src)
    assert cs_json["stylingRules"][0].get("name") == "My Layer Name"

    # Reverse: CS-JSON → CSCSS
    style = Style.from_dict(cs_json)
    cscss_out = converter.style_to_cscss(style)

    assert (
        ".name 'My Layer Name'" in cscss_out
    ), f"Expected .name directive in round-trip CSCSS output, got:\n{cscss_out}"


def test_legacy_styling_rule_name_key_is_rejected():
    """The pre-1.0 ``stylingRuleName`` key is gone: ``name`` is the only key."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Style.from_dict({"stylingRules": [{"stylingRuleName": "R"}]})
