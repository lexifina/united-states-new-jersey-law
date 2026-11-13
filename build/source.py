"""Read the checksum-pinned New Jersey source responses without network access.

Place response bodies in a directory named by NJ_SOURCE_CACHE (default: cache/
beside this module). Names may be the SHA-256 of the URL, that name plus .gz
for a gzip-compressed response, or the response SHA-256 in DATA-SHA256SUMS.
Every body is checked against the recorded checksum before the builder uses it.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
READ: dict[str, str] = {}


def manifest() -> dict[str, str]:
    result = {}
    for number, line in enumerate((HERE / 'DATA-SHA256SUMS').read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        digest, url = line.split(None, 1)
        if not re.fullmatch(r'[0-9a-f]{64}', digest) or url in result:
            raise ValueError(f'invalid or repeated manifest entry at line {number}')
        result[url] = digest
    return result


CHECKS = tuple(url for url in manifest() if '/web/' not in url or not url.lower().endswith('.zip'))


def cached(url: str) -> bytes | None:
    expected = manifest().get(url)
    if expected is None:
        raise ValueError('source URL is not in DATA-SHA256SUMS')
    cache = Path(os.environ.get('NJ_SOURCE_CACHE', str(HERE / 'cache')))
    key = hashlib.sha256(url.encode('utf-8')).hexdigest()
    for name in (key, key + '.gz', expected):
        path = cache / name
        if not path.is_file():
            continue
        body = path.read_bytes()
        if name.endswith('.gz'):
            body = gzip.decompress(body)
        actual = hashlib.sha256(body).hexdigest()
        if actual != expected:
            raise ValueError(f'source checksum mismatch for {url}: expected {expected}, got {actual}')
        READ[url] = actual
        return body
    return None


def captures() -> list[dict[str, str]]:
    records = []
    for url, digest in manifest().items():
        match = re.fullmatch(r'https?://web\.archive\.org/web/(\d{14})id_/(https?://.+/STATUTES-TEXT\.zip)', url, re.I)
        if match:
            records.append({'timestamp': match[1], 'original': match[2], 'digest': digest, 'url': url})
    if not records:
        raise ValueError('manifest contains no statute captures')
    return sorted(records, key=lambda row: (row['timestamp'], row['url']))


def capture_url(record: dict[str, str]) -> str:
    return record['url']


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['verify'])
    parser.add_argument('--cache-dir', type=Path)
    args = parser.parse_args()
    if args.cache_dir:
        os.environ['NJ_SOURCE_CACHE'] = str(args.cache_dir.resolve())
    missing = []
    for url in manifest():
        body = cached(url)
        if body is None:
            missing.append(url)
        else:
            print(f'OK {READ[url]} {len(body)} bytes {url}')
    for url in missing:
        print(f'MISSING {url}')
    print(f'{len(READ)} verified responses, {len(missing)} missing responses')
    raise SystemExit(1 if missing else 0)


if __name__ == '__main__':
    main()
