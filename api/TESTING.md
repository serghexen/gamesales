# Backend tests

## Что есть сейчас
- Тесты лежат в `api/tests`.
- В текущей среде без доступа к `pypi` можно запускать тесты через `unittest`.

## Быстрый запуск
```bash
cd api
make test-v
```

## Когда появится доступ к интернету
1. Установить зависимости:
```bash
cd api
../.venv/bin/pip install -r requirements.txt
```
2. Запуск через pytest:
```bash
make test-pytest
```
3. Покрытие:
```bash
make test-cov
```
