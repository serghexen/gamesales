import unittest
from pathlib import Path

from domains.rbac_permissions import (
    ACTION_PERMISSIONS,
    ACCOUNT_FIELDS,
    DEAL_ACTIVE_FIELDS,
    DEAL_ACTIVE_FIELD_CONTEXTS,
    DEAL_ACTIVE_LIST_PERMISSIONS,
    DEAL_COMPLETED_LIST_PERMISSIONS,
    PRODUCT_FIELDS,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def read_project_file(relative_path: str) -> str:
    # Читает связанный frontend/backend файл, чтобы тест проверял реальное применение RBAC action-ов.
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def application_source_without_permission_editor() -> str:
    # Собирает код приложения без файлов, которые только рисуют матрицу галочек.
    excluded = {
        "api/domains/rbac_permissions.py",
        "api/domains/rbac_api.py",
        "gamesales-web/src/views/work/dealActivePermissions.js",
        "gamesales-web/src/views/work/accountPermissions.js",
        "gamesales-web/src/views/work/productPermissions.js",
        "gamesales-web/src/views/work/sections/WorkRoleActiveDealsPermissions.vue",
        "gamesales-web/src/views/work/sections/WorkRoleAccountPermissions.vue",
        "gamesales-web/src/views/work/sections/WorkRoleProductPermissions.vue",
    }
    chunks: list[str] = []
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".js", ".vue"}:
            continue
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        if rel in excluded or "/__tests__/" in rel or "/tests/" in rel:
            continue
        if any(part in {".git", "node_modules", "dist", "__pycache__"} for part in path.parts):
            continue
        chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)


class RbacActionCoverageTests(unittest.TestCase):
    # Обычные action-ы должны использоваться вне редактора матрицы, иначе чекбокс ничего не включает.
    def test_non_field_actions_are_used_by_application_code(self):
        source = application_source_without_permission_editor()
        dynamic_backend_guards = {
            "deals_active.new.sale.draft": "`deals_active.new.${newDealType.value}.draft`",
            "deals_active.new.rental.draft": "`deals_active.new.${newDealType.value}.draft`",
            "deals_active.view.sale.edit": "`deals_active.view.${currentDealType.value}.edit`",
            "deals_active.view.rental.edit": "`deals_active.view.${currentDealType.value}.edit`",
            "deals_active.save": 'f"{action_group}.save"',
            "deals_draft.edit": 'f"{action_group}.edit"',
            "deals_draft.save": 'f"{action_group}.save"',
            "deals_draft.change_status": 'f"{action_group}.change_status"',
        }

        missing: list[str] = []
        for action_code, *_ in ACTION_PERMISSIONS:
            if ".field." in action_code or ".list." in action_code:
                continue
            marker = dynamic_backend_guards.get(action_code, action_code)
            if marker not in source:
                missing.append(action_code)

        self.assertEqual(missing, [])

    # Колонки сделок создаются динамически, поэтому сверяем backend-ключи с frontend-генератором списка.
    def test_deal_list_permissions_are_wired_to_table_columns(self):
        permissions_source = read_project_file("gamesales-web/src/views/work/dealActivePermissions.js")
        table_source = read_project_file("gamesales-web/src/views/work/sections/WorkDealsTableSection.vue")
        list_permissions = [*DEAL_ACTIVE_LIST_PERMISSIONS, *DEAL_COMPLETED_LIST_PERMISSIONS]

        for action_code, *_ in list_permissions:
            column_key = action_code.rsplit(".", 1)[-1]
            with self.subTest(action_code=action_code):
                self.assertIn(f"key: '{column_key}'", permissions_source)
        self.assertIn("dealListColumns(dealListActionGroup.value)", table_source)
        self.assertIn("props.canDoAction(actionCode)", table_source)

    # Каждое поле сделки из RBAC должно управлять видимостью формы через canNewDealField/canEditDealField.
    def test_deal_field_permissions_are_wired_to_deal_form(self):
        form_source = read_project_file("gamesales-web/src/views/work/sections/WorkDealEditorForm.vue")
        all_contexts = [context_code for context_code, _ in DEAL_ACTIVE_FIELD_CONTEXTS]

        for field_code, _, allowed_contexts in DEAL_ACTIVE_FIELDS:
            contexts = allowed_contexts or all_contexts
            for context_code in contexts:
                deal_type = "rental" if context_code.endswith(".rental") else "sale"
                marker = (
                    f"canNewDealField('{field_code}', '{deal_type}')"
                    if context_code.startswith("new.")
                    else f"canEditDealField('{field_code}', '{deal_type}')"
                )
                if field_code == "discount":
                    marker = "canViewDiscountField"
                with self.subTest(field_code=field_code, context_code=context_code):
                    self.assertIn(marker, form_source)

    # Поля аккаунта из матрицы должны идти через canAccountField, иначе видимость не зависит от галочки.
    def test_account_field_permissions_are_wired_to_account_form(self):
        form_source = read_project_file("gamesales-web/src/views/work/sections/WorkAccountEditorModal.vue")

        for field_code, *_ in ACCOUNT_FIELDS:
            with self.subTest(field_code=field_code):
                self.assertIn(f"canAccountField('{field_code}')", form_source)

    # Поля товара из матрицы должны идти через canProductField, включая связанные аккаунты/сделки/слоты.
    def test_product_field_permissions_are_wired_to_product_form(self):
        form_source = read_project_file("gamesales-web/src/views/work/sections/WorkProductEditorModal.vue")

        for field_code, *_ in PRODUCT_FIELDS:
            with self.subTest(field_code=field_code):
                self.assertIn(f"canProductField('{field_code}')", form_source)


if __name__ == "__main__":
    unittest.main()
