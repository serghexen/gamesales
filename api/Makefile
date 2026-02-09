PY ?= ../.venv/bin/python

.PHONY: test test-v test-pytest test-cov

# Базовый запуск тестов, работает даже без pytest.
test:
	$(PY) -m unittest discover -s tests

# Подробный режим для локальной отладки.
test-v:
	$(PY) -m unittest discover -s tests -v

# Запуск через pytest (если установлен в окружении).
test-pytest:
	$(PY) -m pytest

# Отчет покрытия через pytest-cov (если установлен в окружении).
test-cov:
	$(PY) -m pytest --cov=. --cov-report=term-missing
