PY ?= ../.venv/bin/python

.PHONY: test test-v test-pytest test-cov

# Базовый запуск тестов, работает даже без pytest.
test:
	PYTHONPATH=.. $(PY) -m unittest discover -s tests

# Подробный режим для локальной отладки.
test-v:
	PYTHONPATH=.. $(PY) -m unittest discover -s tests -v

# Запуск через pytest (если установлен в окружении).
test-pytest:
	PYTHONPATH=.. $(PY) -m pytest

# Отчет покрытия через pytest-cov (если установлен в окружении).
test-cov:
	PYTHONPATH=.. $(PY) -m pytest --cov=. --cov-report=term-missing
