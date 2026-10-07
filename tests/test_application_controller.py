from __future__ import annotations

from engine.application_controller import (
    NPSApplicationController,
)


def main() -> None:
    controller = NPSApplicationController()

    result = controller.run_preflight(
        reference_date="8/3/2026",
        test_mode=True,
    )

    print("=" * 80)
    print("APPLICATION CONTROLLER TEST")
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

    if not result.success:
        raise SystemExit(1)


if __name__ == "__main__":
    main()