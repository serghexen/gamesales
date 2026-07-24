import unittest

from scripts.run_migrations import is_no_transaction_migration, split_sql_statements


class MigrationRunnerTests(unittest.TestCase):
    # Проверяет, что DO-блок остается единым запросом и concurrent-индекс не попадает в общую транзакцию.
    def test_split_sql_statements_preserves_dollar_quoted_block(self):
        statements = split_sql_statements(
            """
            DO $$
            BEGIN
              PERFORM 1;
            END $$;
            CREATE INDEX CONCURRENTLY example_idx ON example_table(id);
            """
        )

        self.assertEqual(len(statements), 2)
        self.assertIn("PERFORM 1;", statements[0])
        self.assertTrue(statements[1].startswith("CREATE INDEX CONCURRENTLY"))

    # Проверяет директиву, которая разрешает DDL без оборачивания миграции в BEGIN.
    def test_no_transaction_directive_is_detected(self):
        self.assertTrue(is_no_transaction_migration("-- migrate:no-transaction\nCREATE INDEX CONCURRENTLY test_idx ON test(id);"))
        self.assertFalse(is_no_transaction_migration("CREATE TABLE test(id bigint);"))
