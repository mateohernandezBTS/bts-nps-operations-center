from __future__ import annotations

from engine.application_controller import (
    NPSApplicationController,
)


def main() -> None:
    controller = NPSApplicationController()

    result = controller.run_weekly_process(
        reference_date="8/3/2026",
        test_mode=False,
        stop_on_error=False,
    )

    print()
    print("=" * 80)
    print("CONTROLLED PRODUCTION TRIAL")
    print("=" * 80)
    print(f"Operation: {result.operation}")
    print(f"Environment: {result.environment}")
    print(f"Status: {result.status}")
    print(f"Success: {result.success}")
    print(f"Message: {result.message}")

    if result.issues:
        print()
        print("ISSUES")
        print("-" * 80)

        for issue in result.issues:
            print(f"- {issue}")

    processing = result.data.get(
        "processing",
        {},
    )

    if processing:
        print()
        print("OUTPUTS")
        print("-" * 80)

        print(
            "Excel: "
            f"{processing.get('weekly_excel_path', '')}"
        )
        print(
            "Slack Canvas: "
            f"{processing.get('slack_canvas_path', '')}"
        )
        print(
            "CSV: "
            f"{processing.get('csv_path', '')}"
        )
        print(
            "Manual Review: "
            f"{processing.get('manual_review_csv_path', '')}"
        )
        print(
            "Summary: "
            f"{processing.get('summary_path', '')}"
        )

    session = controller.get_current_session("PRODUCTION")

    if session is not None:
        print()
        print("SESSION")
        print("-" * 80)
        print(f"Session ID: {session.session_id}")
        print(f"Status: {session.status}")
        print(f"Weekly Run ID: {session.weekly_run_id}")
        print(f"Ready: {session.metrics.get('ready_records', 0)}")
        print(f"Review: {session.metrics.get('review_records', 0)}")
        print(f"Clients: {session.metrics.get('clients', 0)}")

    if not result.success:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
