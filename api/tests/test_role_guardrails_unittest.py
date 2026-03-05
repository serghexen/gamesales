from pathlib import Path


def test_privileged_role_guardrails_admin_owner_only():
    # Защищает от возврата legacy-роли administrator в backend-проверки прав.
    domains_dir = Path(__file__).resolve().parents[1] / "domains"
    py_files = sorted(domains_dir.rglob("*.py"))
    offenders = []

    for path in py_files:
        text = path.read_text(encoding="utf-8")
        if "administrator" in text:
            offenders.append(path.relative_to(domains_dir.parent).as_posix())

    assert not offenders, (
        "В backend-доменах найден legacy role 'administrator'. "
        f"Нужно использовать только актуальные роли: {offenders}"
    )

