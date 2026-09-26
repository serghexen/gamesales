"""Собирает воспроизводимый исходный пакет Airpay для отдельного процесса Supplier Hub."""
from pathlib import Path
import argparse
import hashlib
import json


def export(destination):
    # Один исходник логики используется CRM и Hub; копию нельзя править независимо от manifest.
    root = Path(__file__).resolve().parents[2]
    package = destination / 'api' / 'airpay_runtime'
    package.mkdir(parents=True, exist_ok=True)
    files = ['airpay_api', 'airpay_service', 'airpay_preparation', 'airpay_purchase', 'airpay_batch', 'airpay_repository', 'airpay_jobs', 'airpay_contract', 'airpay_resolution', 'airpay_history', 'airpay_queue', 'airpay_diagnostics']
    manifest = {}
    for name in files:
        source = root / 'api' / 'domains' / (name + '.py')
        data = source.read_text().replace('from domains.airpay_', 'from airpay_runtime.airpay_').replace('from domains.interhub_ssh_transport', 'from airpay_runtime.transport').replace('app.airpay_', 'supplier_hub_airpay.airpay_')
        (package / source.name).write_text(data)
        manifest[source.name] = {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'package_sha256': hashlib.sha256(data.encode()).hexdigest()}
    transport = (root / 'api/domains/interhub_ssh_transport.py').read_bytes()
    (package / 'transport.py').write_bytes(transport)
    manifest['transport.py'] = {'source_sha256': hashlib.sha256(transport).hexdigest(), 'package_sha256': hashlib.sha256(transport).hexdigest()}
    (package / '__init__.py').write_text('"""Изолированный пакет Airpay, сгенерирован export_airpay_runtime.py."""\n')
    (package / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    migrations = destination / 'migrations/airpay/runtime'
    migrations.mkdir(parents=True, exist_ok=True)
    for source in sorted((root / 'db/migrations/runtime').glob('*airpay*.sql')):
        data = source.read_text().replace('app.airpay_', 'supplier_hub_airpay.airpay_')
        (migrations / source.name).write_text(data)
    # Мигратор имеет отдельный журнал и каталог, не затрагивает таблицы Interhub.
    script = (root / 'api/scripts/run_migrations.py').read_text().replace('app.schema_migrations', 'supplier_hub_airpay.schema_migrations')
    script = script.replace('gamesales_schema_migrations', 'airpay_schema_migrations')
    script = script.replace('with psycopg.connect(dsn, autocommit=True) as conn:', "with psycopg.connect(dsn, autocommit=True) as conn:\n        conn.execute('CREATE SCHEMA IF NOT EXISTS supplier_hub_airpay')")
    scripts = destination / 'api/scripts'
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / 'run_airpay_migrations.py').write_text(script)
    (scripts / 'airpay_deploy_preflight.py').write_bytes((root / 'api/scripts/airpay_deploy_preflight.py').read_bytes())
    print('Airpay runtime exported; provider credentials were not read')


if __name__ == '__main__':
    # Путь указывается явно: по умолчанию никакой соседний репозиторий не изменяется.
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    export(parser.parse_args().destination)
