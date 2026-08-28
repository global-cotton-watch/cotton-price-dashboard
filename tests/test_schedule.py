from pathlib import Path


def test_workflow_sends_weekday_daily_and_saturday_weekly_reports():
    workflow = Path(".github/workflows/pages.yml").read_text(encoding="utf-8")
    assert 'cron: "0 13 * * 1-5"' in workflow  # 周一至周五，北京时间21:00
    assert 'cron: "0 1 * * 6"' in workflow  # 周六，北京时间09:00
    assert 'cron: "30 1 * * *"' not in workflow
    assert '"0 1 * * 6"' in workflow
    assert '--report-type "${{ steps.report.outputs.type }}"' in workflow
