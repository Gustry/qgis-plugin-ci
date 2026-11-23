#!/usr/bin/env python3
"""Push the source TS file (quickosm_en.ts) to Weblate.

Only the source strings are updated, translations are left untouched.

Examples:
    WEBLATE_TOKEN=wlu_xxx python scripts/weblate_push.py
    python scripts/weblate_push.py --dry-run
"""

import sys

from weblate_common import base_parser, client, source_path
from wlc import WeblateException


def main() -> int:
    args = base_parser(__doc__.splitlines()[0]).parse_args()

    component = client(args).get_component(args.component)
    source = next((t for t in component.list() if t.is_source), None)
    if source is None:
        print(f'No source language found in {args.component}', file=sys.stderr)
        return 1

    path = source_path(args, source)
    if not path.exists():
        print(f'{path} not found', file=sys.stderr)
        return 1

    print(f'[push] {path.name} -> {source.language_code} (source)')
    if args.dry_run:
        return 0

    try:
        with path.open('rb') as handle:
            result = source.upload(handle, method='source')
    except WeblateException as error:
        print(f'       error: {error}', file=sys.stderr)
        return 1

    print(
        '       accepted {accepted}, skipped {skipped}, not found {not_found}, total {total}'.format(
            **{k: result.get(k, '?') for k in ('accepted', 'skipped', 'not_found', 'total')}
        )
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
