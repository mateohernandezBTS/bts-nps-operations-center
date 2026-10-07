from engine.source_config import (
    get_enabled_sources,
    get_required_sources,
    load_source_configuration,
)


def main() -> None:
    configuration = load_source_configuration()

    upcoming_sources = get_enabled_sources("weekly_upcoming")
    required_sources = get_required_sources("weekly_upcoming")
    last_results_sources = get_enabled_sources("last_results")

    print("=" * 80)
    print("SOURCE CONFIGURATION TEST")
    print("=" * 80)

    print(f"Configuration version: {configuration.get('version')}")
    print(f"Upcoming enabled: {len(upcoming_sources)}")
    print(f"Upcoming required: {len(required_sources)}")
    print(f"Last Results enabled: {len(last_results_sources)}")

    print("\nREQUIRED UPCOMING SOURCES")
    print("-" * 80)

    for source in required_sources:
        print(
            f"{source['source_id']} | "
            f"{source['country']} | "
            f"{source['report_type']}"
        )


if __name__ == "__main__":
    main()