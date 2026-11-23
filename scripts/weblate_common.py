"""Shared helpers for the Weblate scripts (wlc client)."""

import argparse
import os
import sys

from pathlib import Path

from wlc import Weblate
from wlc.config import WeblateConfig

DEFAULT_URL = 'https://hosted.weblate.org/api/'
DEFAULT_COMPONENT = 'quickosm/quickosm'
I18N_DIR = Path(__file__).resolve().parent.parent / 'QuickOSM' / 'i18n'


def base_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        '--url',
        default=os.environ.get('WEBLATE_URL', DEFAULT_URL),
        help=f'Weblate API URL (default: {DEFAULT_URL}, env WEBLATE_URL)',
    )
    parser.add_argument(
        '--key',
        default=os.environ.get('WEBLATE_TOKEN'),
        help=(
            'Weblate API key (env WEBLATE_TOKEN). If absent, the wlc config '
            '(~/.config/weblate, WLC_URL/WLC_KEY) is used.'
        ),
    )
    parser.add_argument(
        '--component',
        default=DEFAULT_COMPONENT,
        help=f'Weblate component path project/component (default: {DEFAULT_COMPONENT})',
    )
    parser.add_argument(
        '--i18n-dir',
        type=Path,
        default=I18N_DIR,
        help=f'Folder holding the TS files (default: {I18N_DIR})',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Only print what would be done',
    )
    return parser


def client(args: argparse.Namespace) -> Weblate:
    """Weblate client: explicit key first, then the wlc configuration.

    Without any key the access is anonymous (enough to pull a public project).
    """
    print(args)
    if args.key:
        return Weblate(url=args.url, key=args.key)
    config = WeblateConfig()
    config.load()
    _, key = config.get_url_key()
    if key:
        return Weblate(config=config)
    print('No Weblate API key found, anonymous access.', file=sys.stderr)
    return Weblate(url=args.url)


def translations(args: argparse.Namespace):
    """Yield (translation, local_path) for the component, filtered by args."""
    component = client(args).get_component(args.component)
    wanted = set(args.languages) if args.languages else None
    for translation in component.list():
        if translation.is_source and not args.include_source:
            continue
        if wanted is not None and translation.language_code not in wanted:
            continue
        yield translation, source_path(args, translation)


def source_path(args: argparse.Namespace, translation) -> Path:
    """Local TS file matching a Weblate translation."""
    # Weblate stores the path relative to the repository root, e.g.
    # QuickOSM/i18n/quickosm_fr.ts: only the file name matters here.
    # The source language has no file on Weblate side.
    name = Path(translation.filename or '').name
    return args.i18n_dir / (name or f'quickosm_{translation.language_code}.ts')
