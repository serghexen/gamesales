import unittest

from domains.rbac_permissions import ACTION_PERMISSIONS, default_action_allowed


REFERENCE_DISABLED_ACTIONS = {
    "deals_active.discount",
    "deals_draft.delete",
    "deals_draft.change_deal_date",
    "deals_draft.change_completed_date",
    "deals_completed.edit",
    "deals_completed.save",
    "deals_completed.change_status",
    "deals_completed.change_deal_date",
    "deals_completed.change_completed_date",
    "deals_completed.process_return",
    "accounts.reflect_date",
    "accounts.reflect_region",
    "accounts.reflect_email_password",
    "accounts.reflect_auth_code",
    "accounts.reflect_reserves",
    "accounts.reflect_slots",
    "accounts.edit",
    "accounts.delete",
    "products.reflect_slots",
    "products.edit",
    "products.delete",
}


class RbacPermissionsTests(unittest.TestCase):
    # Проверяет инверсию бизнес-референса: галочка в таблице означает запрет действия.
    def test_manager_operator_defaults_match_disabled_checkmarks(self):
        action_codes = {action_code for action_code, *_ in ACTION_PERMISSIONS}

        for role in ("manager", "operator"):
            for action_code in action_codes:
                with self.subTest(role=role, action_code=action_code):
                    expected = action_code not in REFERENCE_DISABLED_ACTIONS
                    self.assertEqual(default_action_allowed(role, action_code), expected)

    # Админ и управляющий в референсе пустые, значит все действия по умолчанию включены.
    def test_admin_owner_defaults_allow_all_actions(self):
        for role in ("admin", "owner"):
            for action_code, *_ in ACTION_PERMISSIONS:
                with self.subTest(role=role, action_code=action_code):
                    self.assertTrue(default_action_allowed(role, action_code))

    # Проверяет конкретные спорные действия, которые легко перепутать при чтении таблицы.
    def test_reference_empty_cells_are_enabled(self):
        self.assertTrue(default_action_allowed("manager", "deals_active.approve_return"))
        self.assertTrue(default_action_allowed("operator", "deals_completed.press_return"))
        self.assertTrue(default_action_allowed("manager", "accounts.reflect_deals"))
        self.assertTrue(default_action_allowed("operator", "products.reflect_deals"))


if __name__ == "__main__":
    unittest.main()
