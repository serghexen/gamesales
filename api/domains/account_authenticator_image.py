"""Хранение изображения аутентификатора как отдельного секрета аккаунта."""

import base64
import binascii
import hashlib
import re

from fastapi import HTTPException

IMAGE_SECRET_KEY = 'authenticator_image'
MAX_IMAGE_BYTES = 1024 * 1024


def raster_dimensions(raw, mime):
    # Читаем размеры из заголовков без распаковки пикселей: маленький файл не должен скрывать огромное изображение.
    if mime == 'image/png' and len(raw) >= 33 and raw[:8] == b'\x89PNG\r\n\x1a\n' and raw[12:16] == b'IHDR':
        return int.from_bytes(raw[16:20], 'big'), int.from_bytes(raw[20:24], 'big')
    if mime == 'image/jpeg' and raw.startswith(b'\xff\xd8\xff') and raw.endswith(b'\xff\xd9'):
        offset = 2
        while offset + 4 <= len(raw):
            if raw[offset] != 255:
                break
            while offset < len(raw) and raw[offset] == 255:
                offset += 1
            if offset + 3 > len(raw):
                break
            marker = raw[offset]
            offset += 1
            length = int.from_bytes(raw[offset:offset + 2], 'big')
            if length < 2 or offset + length > len(raw) or marker in (0xDA, 0xD9):
                break
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF) and length >= 7:
                return int.from_bytes(raw[offset + 5:offset + 7], 'big'), int.from_bytes(raw[offset + 3:offset + 5], 'big')
            offset += length
    if mime == 'image/webp' and len(raw) >= 25 and raw[:4] == b'RIFF' and raw[8:12] == b'WEBP' and int.from_bytes(raw[4:8], 'little') == len(raw) - 8:
        kind = raw[12:16]
        if kind == b'VP8X' and len(raw) >= 30:
            return 1 + int.from_bytes(raw[24:27], 'little'), 1 + int.from_bytes(raw[27:30], 'little')
        if kind == b'VP8L' and raw[20] == 0x2F:
            packed = int.from_bytes(raw[21:25], 'little')
            return 1 + (packed & 0x3FFF), 1 + ((packed >> 14) & 0x3FFF)
        if kind == b'VP8 ' and len(raw) >= 30 and raw[23:26] == b'\x9d\x01\x2a':
            return int.from_bytes(raw[26:28], 'little') & 0x3FFF, int.from_bytes(raw[28:30], 'little') & 0x3FFF
    return None


def validate_image(value):
    # Принимаем только небольшие растровые изображения; SVG и произвольные URL не сохраняем.
    if not value:
        return ''
    match = re.fullmatch(r'data:(image/png|image/jpeg|image/webp);base64,([A-Za-z0-9+/=]+)', value)
    if not match or len(value) > MAX_IMAGE_BYTES * 4 // 3 + 128:
        raise HTTPException(400, 'Выберите PNG, JPEG или WebP размером до 1 МБ')
    try:
        raw = base64.b64decode(match[2], validate=True)
    except (ValueError, binascii.Error):
        raise HTTPException(400, 'Некорректное изображение аутентификатора')
    dimensions = raster_dimensions(raw, match[1])
    if not raw or len(raw) > MAX_IMAGE_BYTES or not dimensions:
        raise HTTPException(400, 'Формат изображения не соответствует содержимому файла')
    if not all(0 < side <= 4096 for side in dimensions):
        raise HTTPException(400, 'Размер изображения должен быть не больше 4096 × 4096')
    return f'data:{match[1]};base64,{base64.b64encode(raw).decode()}'


def image_hash(value):
    # Хеш нужен только для проверки версии; значение изображения не попадает в сообщения об ошибке.
    return hashlib.sha256(value.encode()).hexdigest() if value else ''


class AccountAuthenticatorImage:
    def __init__(self, q1, exec1):
        # Работаем в транзакции сохранения секретов без отдельного файлового хранилища.
        self.q1, self.exec1 = q1, exec1

    def read(self, conn, account_id):
        # Изображение читается отдельно, чтобы не раздувать справочники и списки сделок.
        row = self.q1(conn, 'SELECT secret_value FROM app.account_secrets WHERE account_id=%s AND secret_key=%s', (account_id, IMAGE_SECRET_KEY))
        value = base64.b64decode(row[0]).decode() if row else ''
        return {'image': value, 'version': image_hash(value)}

    def replace(self, conn, account_id, value, expected_version):
        # Не затираем параллельную замену и не удаляем картинку из устаревшей карточки.
        value = validate_image(value)
        if expected_version is None:
            raise HTTPException(400, 'Для изменения изображения нужна его исходная версия')
        if not self.q1(conn, 'SELECT account_id FROM app.accounts WHERE account_id=%s FOR UPDATE', (account_id,)):
            raise HTTPException(404, 'Account not found')
        current = self.read(conn, account_id)
        if current['version'] != expected_version:
            raise HTTPException(409, 'Изображение аутентификатора изменилось. Откройте аккаунт заново.')
        if value:
            self.exec1(conn, '''INSERT INTO app.account_secrets(account_id,secret_key,secret_value)
                VALUES (%s,%s,%s) ON CONFLICT(account_id,secret_key)
                DO UPDATE SET secret_value=excluded.secret_value''', (account_id, IMAGE_SECRET_KEY, base64.b64encode(value.encode()).decode()))
        else:
            self.exec1(conn, 'DELETE FROM app.account_secrets WHERE account_id=%s AND secret_key=%s', (account_id, IMAGE_SECRET_KEY))
