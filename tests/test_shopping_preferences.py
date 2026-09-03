"""Tests for shopping and preferences sections."""

from __future__ import annotations

from pathlib import Path

from preferences.insights import PreferencesInsights
from shopping.insights import ShoppingInsights

FIXTURE_EXPORT = (
    Path(__file__).parent
    / "fixtures/minimal_export/instagram-demo-2026-01-01-TEST01"
)


def test_shopping_insights_fixture():
    ins = ShoppingInsights.build(FIXTURE_EXPORT)
    assert len(ins.recently_viewed) == 3
    assert "Demo Running Shoes" in ins.recently_viewed
    assert len(ins.wishlist) == 2
    assert "Demo Tripod" in ins.wishlist
    assert len(ins.orders) == 1


def test_preferences_insights_fixture():
    ins = PreferencesInsights.build(FIXTURE_EXPORT)
    assert "Photography" in ins.topics
    assert "Trail Running Reels" in ins.reels_topics
    assert len(ins.notifications) == 3
    assert any("Likes" in label for label, _ in ins.notifications)
    assert any("Everyone" in s for s in ins.comments_settings)


def test_main_shopping_preferences(capsys):
    import instagram_analysis as ia

    ia.main(
        [
            "--export-dir",
            str(FIXTURE_EXPORT),
            "--section",
            "shopping,preferences",
        ]
    )
    out = capsys.readouterr().out
    assert "SHOPPING" in out
    assert "PREFERENCES" in out
    assert "Recently viewed" in out
    assert "Your topics" in out
    assert "Notification preferences" in out
    assert "File not found" not in out
