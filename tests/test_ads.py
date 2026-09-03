"""Tests for the Ads & Tracking pillar (ADR-0007)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ads.insights import AdsInsights
from ads.parse import flag_counts_for, parse_advertisers, build_engagement
from ads.report import format_ads_report
from export_inventory import FileStatus

FIXTURE_EXPORT = (
    Path(__file__).parent
    / "fixtures/minimal_export/instagram-demo-2026-01-01-TEST01"
)


def test_ads_insights_fixture_flag_histogram():
    ins = AdsInsights.build(FIXTURE_EXPORT)
    assert ins.flag_counts.total == 5
    assert ins.flag_counts.data_file == 4
    assert ins.flag_counts.remarketing == 2
    assert ins.flag_counts.in_person_store == 2


def test_ads_insights_inventory_all_present():
    ins = AdsInsights.build(FIXTURE_EXPORT)
    by_key = {i.key: i for i in ins.inventory}
    assert by_key["advertisers"].status == FileStatus.PRESENT
    assert by_key["ads_interests"].status == FileStatus.PRESENT
    assert by_key["ads_viewed"].status == FileStatus.PRESENT
    assert by_key["ads_clicked"].status == FileStatus.PRESENT
    assert by_key["off_instagram"].status == FileStatus.PRESENT


def test_ads_engagement_summary():
    ins = AdsInsights.build(FIXTURE_EXPORT)
    assert ins.engagement.viewed_count == 4
    assert ins.engagement.clicked_count == 2
    assert ins.engagement.viewed_span == ("2024-01", "2024-04")
    assert ins.engagement.top_viewed[0] == ("Demo Retail Co", 2)


def test_ads_interests_and_off_ig():
    ins = AdsInsights.build(FIXTURE_EXPORT)
    assert "Demo Photography" in ins.interests
    assert len(ins.categories) == 2
    assert len(ins.off_ig_apps) == 2
    assert ins.off_ig_apps[0].name == "demo-shop.example"
    assert ins.off_ig_apps[0].event_count == 2


def test_ads_report_no_absolute_path_spam():
    ins = AdsInsights.build(FIXTURE_EXPORT)
    text = format_ads_report(ins, limit=30)
    assert "Export inventory" in text
    assert "Audience types:" in text
    assert "data-file custom audience" in text
    assert "File not found" not in text
    assert str(FIXTURE_EXPORT) not in text


def test_ads_report_sparse_export_inventory(tmp_path):
    export = tmp_path / "instagram-sparse-2026-01-01-TEST01"
    (export / "connections").mkdir(parents=True)
    (export / "personal_information").mkdir(parents=True)
    ads_dir = export / "ads_information/instagram_ads_and_businesses"
    ads_dir.mkdir(parents=True)
    payload = {
        "ig_custom_audiences_all_types": [
            {
                "advertiser_name": "Only Datafile",
                "has_data_file_custom_audience": True,
                "has_remarketing_custom_audience": False,
                "has_in_person_store_visit": False,
            }
        ]
        * 3
    }
    (ads_dir / "advertisers_using_your_activity_or_information.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    ins = AdsInsights.build(export)
    assert ins.flag_counts.total == 3
    assert ins.flag_counts.data_file == 3
    assert ins.flag_counts.remarketing == 0
    text = format_ads_report(ins)
    assert "not in this ZIP" in text
    assert "File not found" not in text
    assert "Only Datafile" in text


def test_parse_advertisers_flag_helpers():
    data = {
        "ig_custom_audiences_all_types": [
            {
                "advertiser_name": "A",
                "has_data_file_custom_audience": True,
                "has_remarketing_custom_audience": False,
                "has_in_person_store_visit": False,
            }
        ]
    }
    advertisers = parse_advertisers(data)
    counts = flag_counts_for(advertisers)
    assert counts.total == 1
    assert counts.data_file == 1


def test_build_engagement_empty():
    eng = build_engagement(None, None)
    assert eng.viewed_count == 0
    assert eng.clicked_count == 0


def test_main_section_ads(capsys):
    import instagram_analysis as ia

    ia.main(["--export-dir", str(FIXTURE_EXPORT), "--section", "ads"])
    out = capsys.readouterr().out
    assert "ADS & TRACKING" in out
    assert "Audience types:" in out
    assert "Ads engagement" in out
    assert "File not found" not in out
    assert "Connection summary" not in out


def test_ads_limit_zero_prints_all(capsys):
    import instagram_analysis as ia

    ia.main(
        [
            "--export-dir",
            str(FIXTURE_EXPORT),
            "--section",
            "ads",
            "--ads-limit",
            "0",
        ]
    )
    out = capsys.readouterr().out
    for name in (
        "Demo Retail Co",
        "Remarket Labs",
        "Footfall Brand",
        "Datafile Only Inc",
        "Omni Target LLC",
    ):
        assert name in out
    assert "and 0 more" not in out
    assert "use --ads-limit 0 to print all" not in out
