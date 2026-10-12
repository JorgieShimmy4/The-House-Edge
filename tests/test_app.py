"""Smoke tests for the Streamlit app itself.

These run app.py headless and inspect what it renders. They catch the class
of bug the library tests cannot: a correct number displayed incorrectly.
"""

from pathlib import Path

import pytest

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


@pytest.fixture(scope="module")
def app():
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    return at


def test_app_runs_without_exceptions(app):
    assert not app.exception


def test_all_six_tabs_render(app):
    assert len(app.tabs) == 6


def _unescaped_dollars(text: str) -> int:
    return text.count("$") - text.count(r"\$")


@pytest.mark.parametrize("kind", ["error", "warning", "info", "success"])
def test_callouts_escape_dollar_signs(app, kind):
    """Two bare $ signs in one callout render as a LaTeX equation."""
    for element in getattr(app, kind):
        assert _unescaped_dollars(element.value) == 0, element.value


def test_cost_callout_shows_dollar_amounts(app):
    text = app.error[0].value
    assert r"\$" in text
