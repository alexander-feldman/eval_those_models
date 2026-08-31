import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).parents[2] / "scripts/analyze_experiment3_quantity.py"
_SPEC = importlib.util.spec_from_file_location("experiment3_quantity_analysis", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_ANALYSIS = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_ANALYSIS)

_adapt_quantity_rows = _ANALYSIS._adapt_quantity_rows
_contract_compliant = _ANALYSIS._contract_compliant
_strip_first_line_tool_narration = _ANALYSIS._strip_first_line_tool_narration


def test_mixed_number_is_not_mistaken_for_tool_narration() -> None:
    text = "1 1/2 cups | sugar\n1 teaspoon | salt"

    stripped, had_narration = _strip_first_line_tool_narration(text)

    assert stripped == text
    assert not had_narration


def test_concatenated_tool_narration_is_removed_only_for_content() -> None:
    text = "I'll search for this recipe.1/2 cup | cocoa powder\n1 cup | sugar"

    adapted, had_narration = _adapt_quantity_rows(text)

    assert adapted == "- 1/2 cup cocoa powder\n- 1 cup sugar"
    assert had_narration
    assert not _contract_compliant(text)


def test_clear_format_defects_are_mechanically_normalized() -> None:
    text = (
        "1/2 cup cocoa powder | 1 cup sugar | 2 eggs\n"
        "150ml | water\n"
        "1 bay leaf | 1 bay leaf\n"
        "1 tablespoon honey | honey"
    )

    adapted, had_narration = _adapt_quantity_rows(text)

    assert adapted == (
        "- 1/2 cup cocoa powder\n"
        "- 1 cup sugar\n"
        "- 2 eggs\n"
        "- 150 ml water\n"
        "- 1 bay leaf\n"
        "- 1 tablespoon honey"
    )
    assert not had_narration
    assert not _contract_compliant(text)


def test_well_formed_pipe_rows_are_contract_compliant() -> None:
    text = "1/2 cup | cocoa powder\nunknown | Vanilla Cream"

    assert _contract_compliant(text)
