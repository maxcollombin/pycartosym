"""Layer names are ORed, ``?:`` is right-associative, channels take any expression."""

from pycartosym.converter import Converter

_LAYERS = "Roads Railways[viz.sd < 10000][level < 4] { visibility: false; }\n"


def _first_rule(cscss: str) -> dict:
    return Converter().cscss_to_csjson(cscss)["stylingRules"][0]


def test_layer_names_are_ored_and_anded_with_filters():
    selector = _first_rule(_LAYERS)["selector"]
    assert selector["op"] == "and"
    assert selector["args"][0] == {
        "op": "or",
        "args": [
            {"op": "=", "args": [{"sysId": "dataLayer.id"}, "Roads"]},
            {"op": "=", "args": [{"sysId": "dataLayer.id"}, "Railways"]},
        ],
    }
    assert len(selector["args"]) == 3


def test_layer_names_only_are_a_plain_or():
    selector = _first_rule("Roads Railways { visibility: false; }\n")["selector"]
    assert selector["op"] == "or"
    assert len(selector["args"]) == 2


def test_layer_names_roundtrip_to_cscss():
    converter = Converter()
    csjson = converter.cscss_to_csjson(_LAYERS)
    cscss = converter.csjson_to_cscss(csjson)
    assert cscss.startswith("Roads Railways[")
    again = converter.cscss_to_csjson(cscss)["stylingRules"][0]["selector"]
    assert again["args"][0] == csjson["stylingRules"][0]["selector"]["args"][0]


def test_conditional_is_right_associative():
    opacity = _first_rule("L { opacity: x > 10 ? 1 : x > 5 ? 2 : 3; }\n")["symbolizer"][
        "opacity"
    ]
    assert opacity["op"] == "?:"
    assert opacity["args"][1] == 1
    assert opacity["args"][2]["op"] == "?:"
    assert opacity["args"][2]["args"][1:] == [2, 3]


def test_channels_accept_calls_and_power():
    symbolizer = _first_rule(
        "L { colorChannels.r: pow(B04 / 2500, 0.5);"
        " colorChannels.g: (B04 / 2500) ^ 0.5; colorChannels.b: abs(B04); }\n"
    )["symbolizer"]
    channels = symbolizer["colorChannels"]
    assert channels["r"]["op"] == "pow"
    assert channels["g"]["op"] == "^"
    assert channels["b"] == {"op": "abs", "args": [{"property": "B04"}]}


def test_single_channel_accepts_calls():
    single = _first_rule("L { singleChannel: pow(B04 / 2500, 0.5); }\n")["symbolizer"][
        "singleChannel"
    ]
    assert single["op"] == "pow"
