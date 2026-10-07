from engine.stages.business_rules import matches_pattern


pattern = r"\bpod\b"

test_cases = {
    "Empoderamiento y Desarrollo 2026 - G60": False,
    "POD Coaching": True,
    "Group/POD Coaching": True,
    "Leadership POD": True,
    "POD - Team Session": True,
    "Empoderar líderes": False,
    "Empoderamiento": False,
}


all_ok = True

for value, expected in test_cases.items():
    result = matches_pattern(
        field_value=value,
        pattern=pattern,
        match_type="regex_any",
    )

    status = "OK" if result == expected else "ERROR"

    print(
        f"{status} | {value!r} | "
        f"resultado={result} | esperado={expected}"
    )

    if result != expected:
        all_ok = False


if all_ok:
    print("\nTODAS LAS PRUEBAS PASARON")
else:
    print("\nHAY PRUEBAS CON ERROR")