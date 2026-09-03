"""Tests for activity, security, messages, apps, and contacts pillars."""

from __future__ import annotations

from pathlib import Path

from activity.insights import ActivityInsights
from apps.insights import AppsInsights
from contacts.insights import ContactsInsights
from contacts.report import format_contacts_report
from messages.insights import MessagesInsights
from messages.report import format_messages_report
from security.insights import SecurityInsights
from security.report import format_security_report

FIXTURE_EXPORT = (
    Path(__file__).parent
    / "fixtures/minimal_export/instagram-demo-2026-01-01-TEST01"
)


def test_activity_insights_fixture():
    ins = ActivityInsights.build(FIXTURE_EXPORT)
    assert ins.post_total >= 1
    assert ins.story_total == 2
    assert ins.reel_total == 2
    assert ins.liked_posts_total == 1
    assert ins.liked_comments_total == 2
    assert ins.saved_total == 2
    assert ins.story_likes_total == 3
    assert ins.story_polls_total == 2
    assert ins.search_total == 3
    assert ("alice_demo", 2) in ins.comment_targets or ins.comment_targets[0][0] == "alice_demo"


def test_security_insights_fixture():
    ins = SecurityInsights.build(FIXTURE_EXPORT)
    assert len(ins.logins) == 3
    assert len(ins.sessions) == 1
    assert ins.password_change_count == 1
    assert ins.top_devices[0][0].startswith("DemoPhone")
    text = format_security_report(ins, redact=True)
    assert "203.0.113" not in text or "***" in text
    assert "File not found" not in text


def test_messages_metadata_no_bodies():
    ins = MessagesInsights.build(FIXTURE_EXPORT)
    assert ins.inbox_count == 1
    assert ins.request_count == 1
    assert ins.message_total == 4
    text = format_messages_report(ins)
    assert "SECRET" not in text
    assert "also secret" not in text
    assert "request body hidden" not in text
    assert "metadata only" in text
    assert "alice_demo" in text


def test_apps_and_contacts():
    apps = AppsInsights.build(FIXTURE_EXPORT)
    assert len(apps.linked) == 2
    contacts = ContactsInsights.build(FIXTURE_EXPORT)
    assert len(contacts.names) == 3
    redacted = format_contacts_report(contacts, redact=True)
    assert "Ada Lovelace" not in redacted
    assert "A***" in redacted
    raw = format_contacts_report(contacts, redact=False)
    assert "Ada Lovelace" in raw


def test_main_new_sections(capsys):
    import instagram_analysis as ia

    ia.main(
        [
            "--export-dir",
            str(FIXTURE_EXPORT),
            "--section",
            "activity,security,messages,apps,contacts",
        ]
    )
    out = capsys.readouterr().out
    assert "ACTIVITY" in out
    assert "SECURITY" in out
    assert "MESSAGES" in out
    assert "APPS & WEBSITES" in out
    assert "CONTACTS" in out
    assert "Saved items" in out
    assert "Login history" in out
    assert "SECRET" not in out
    assert "File not found" not in out
