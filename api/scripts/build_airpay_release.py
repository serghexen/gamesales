"""Снимок исходников CRM/Airpay Hub с проверкой комплектности, без запуска сервисов."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile


def digest(data):
    # Хеш проверяет целостность точного файла, вошедшего в поставку.
    return hashlib.sha256(data).hexdigest()


def listed(root):
    # Учитываем новые файлы, чтобы не потерять Airpay из-за отсутствия git add; секреты не включаем.
    raw = subprocess.check_output(['git', '-C', str(root), 'ls-files', '--cached', '--others', '--exclude-standard', '-z'])
    return sorted(set(name.decode() for name in raw.split(b'\0') if name))


def selected(name, project):
    # Поставка имеет явный список типов исходников и не захватывает env, ключи, дампы или пользовательские файлы.
    path = Path(name)
    if any(part in {'__pycache__', 'node_modules', '.venv', 'dist'} or part.startswith('.env') for part in path.parts):
        return False
    if project == 'crm':
        return ((name.startswith('api/') and (path.suffix == '.py' or name in {'api/requirements.txt', 'api/Dockerfile', 'api/.dockerignore'}))
                or (name.startswith('gamesales-web/src/') and path.suffix in {'.js', '.vue', '.css', '.svg', '.png', '.jpg', '.webp'})
                or (name.startswith('gamesales-web/public/') and path.suffix in {'.svg', '.png', '.jpg', '.ico', '.webp'})
                or name in {'gamesales-web/package.json', 'gamesales-web/package-lock.json', 'gamesales-web/index.html',
                            'gamesales-web/vite.config.js', 'gamesales-web/eslint.config.js', 'gamesales-web/Dockerfile', 'gamesales-web/.dockerignore'}
                or (name.startswith('db/migrations/') and path.suffix == '.sql')
                or (name.startswith('docs/airpay') and path.suffix == '.md'))
    return ((name.startswith('api/') and path.suffix == '.py') or name == 'api/airpay_runtime/manifest.json'
            or (name.startswith('migrations/airpay/') and path.suffix == '.sql')
            or name in {'Dockerfile.airpay', 'Dockerfile.airpay.dockerignore', 'docker-compose.airpay.yml',
                        'requirements.txt', 'requirements-airpay.txt', 'docs/AIRPAY.md'})


def verify(crm, hub):
    # Защищённые рабочие модули сравниваются с HEAD; намеренные изменения оболочки CRM проверяются тестами.
    for root, names in [(crm, ['api/domains/interhub*.py']), (hub, ['api/hub/*.py', 'docker-compose.yml', 'requirements.txt'])]:
        for pattern in names:
            for file in root.glob(pattern):
                if file.name == 'airpay_app.py': continue
                original = subprocess.check_output(['git', '-C', str(root), 'show', 'HEAD:' + str(file.relative_to(root))])
                if file.read_bytes() != original:
                    raise ValueError('Protected Interhub source differs from HEAD: ' + str(file.relative_to(root)))
    runtime = hub / 'api/airpay_runtime'
    manifest = json.loads((runtime / 'manifest.json').read_text())
    required = {p.name for p in (crm / 'api/domains').glob('airpay_*.py')} - {'airpay_bootstrap.py', 'airpay_hub_client.py'}
    if not required.issubset(manifest): raise ValueError('Airpay runtime is incomplete')
    for name, hashes in manifest.items():
        source = crm / 'api/domains' / ('interhub_ssh_transport.py' if name == 'transport.py' else name)
        if digest(source.read_bytes()) != hashes['source_sha256'] or digest((runtime / name).read_bytes()) != hashes['package_sha256']:
            raise ValueError('Runtime checksum mismatch: ' + name)
    for file in (crm / 'db/migrations/runtime').glob('*airpay*.sql'):
        expected = file.read_text().replace('app.airpay_', 'supplier_hub_airpay.airpay_')
        if (hub / 'migrations/airpay/runtime' / file.name).read_text() != expected:
            raise ValueError('Migration mismatch: ' + file.name)
    for file in (crm / 'api/domains').glob('airpay_*.py'):
        compile(file.read_text(), str(file), 'exec')


def build(crm, hub, destination):
    # Архивы включают рабочие изменения, но не меняют git index, окружение, БД или контейнеры.
    verify(crm, hub)
    destination.mkdir(parents=True, exist_ok=False)
    report = {'type': 'source-overlay', 'payments_executed': False, 'files': {}, 'repositories': {},
              'remaining_gates': ['Review exact deployed revisions', 'Backup and encryption key recovery',
                  'Validate dedicated env and existing Docker network', 'Docker build and compose config on deployment host',
                  'Review pending migrations', 'Read-only deployed smoke and manual WorkView smoke']}
    for project, root in [('crm', crm), ('hub', hub)]:
        report['repositories'][project] = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
        files = [name for name in listed(root) if selected(name, project)]
        must_have = (['api/app.py', 'api/domains/airpay_bootstrap.py', 'gamesales-web/src/views/work/sections/WorkPaymentsSection.vue'] if project == 'crm'
                     else ['api/hub/airpay_app.py', 'api/airpay_runtime/manifest.json', 'docker-compose.airpay.yml', 'Dockerfile.airpay.dockerignore'])
        if not set(must_have).issubset(files): raise ValueError('Required release files missing: ' + project)
        with tarfile.open(destination / (project + '-airpay-source.tar.gz'), 'w:gz') as archive:
            for name in files:
                data = (root / name).read_bytes()
                info = tarfile.TarInfo(name)
                info.size, info.mode = len(data), 0o644
                archive.addfile(info, io.BytesIO(data))
                report['files'][project + '/' + name] = digest(data)
    report['archives'] = {p.name: digest(p.read_bytes()) for p in destination.glob('*.tar.gz')}
    (destination / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('Source release prepared:', destination, 'files:', len(report['files']))


if __name__ == '__main__':
    # Явные пути предотвращают случайную запись в соседний проект или боевое окружение.
    parser = argparse.ArgumentParser()
    parser.add_argument('--crm', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--hub', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.crm.resolve(), args.hub.resolve(), args.output.resolve())
