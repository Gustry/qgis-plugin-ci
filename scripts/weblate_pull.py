#!/usr/bin/env python3
"""Pull the TS files from Weblate into QuickOSM/i18n.

Examples:
    WEBLATE_TOKEN=wlu_xxx python scripts/weblate_pull.py
    python scripts/weblate_pull.py -l fr -l de
"""

import sys

from weblate_common import base_parser, translations
from wlc import WeblateException


def main() -> int:
    parser = base_parser(__doc__.splitlines()[0])
    parser.add_argument(
        '-l',
        '--language',
        action='append',
        dest='languages',
        help='Only process this language code (repeatable), e.g. -l fr -l pt_BR',
    )
    parser.add_argument(
        '--include-source',
        action='store_true',
        help='Also pull the source language (quickosm_en.ts)',
    )
    args = parser.parse_args()

    errors = 0
    for translation, path in translations(args):
        print(f'[pull] {translation.language_code} -> {path}')
        if args.dry_run:
            continue

        try:
            content = translation.download()
        except WeblateException as error:
            errors += 1
            print(f'       error: {error}', file=sys.stderr)
            continue

        if path.exists() and path.read_bytes() == content:
            print('       unchanged')
            continue
        path.write_bytes(content)
        print('       updated')

    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
