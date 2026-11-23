"""Weblate translation client, based on wlc (the Weblate API client).

Mapping with the TranslationConfig:

- project_slug: the Weblate project slug
- resource_slug: the Weblate component slug
- api_url: the Weblate API URL, e.g. https://hosted.weblate.org/api/
"""

import logging
from collections.abc import Callable
from pathlib import Path

from wlc import Weblate, WeblateException
from wlc.config import WeblateConfig

from qgispluginci.translation_clients.baseclient import BaseClient, TranslationConfig


# GLOBALS
logger = logging.getLogger(__name__)

DEFAULT_API_URL = "https://hosted.weblate.org/api/"


class WeblateClient(BaseClient):
    def __init__(
        self,
        config: TranslationConfig,
        update_string_fcn: Callable,
        create_project: bool = True,
    ):
        super().__init__(config, update_string_fcn, create_project)

    def login(self):
        """Weblate client: explicit token first, then the wlc configuration.

        Without any token the access is anonymous (enough to pull a public project).
        """
        url = self.config.api_url or DEFAULT_API_URL
        if self.config.api_token:
            self.client = Weblate(url=url, key=self.config.api_token)
            return
        config = WeblateConfig()
        config.load()
        _, key = config.get_url_key()
        if key:
            self.client = Weblate(config=config)
            return
        logger.warning("No Weblate API token found, anonymous access.")
        self.client = Weblate(url=url)

    def get_project(self):
        return self.client.get_project(self.config.project_slug)

    def get_resource(self):
        return self.client.get_component(
            f"{self.config.project_slug}/{self.config.resource_slug}"
        )

    def list_languages(self):
        """Language codes of the component, the source language included."""
        return [t.language_code for t in self.get_resource().list()]

    def update_source_translation(self):
        """Push the source TS file. Only the source strings are updated."""
        source = next((t for t in self.get_resource().list() if t.is_source), None)
        if source is None:
            raise WeblateException(
                f"No source language found in "
                f"{self.config.project_slug}/{self.config.resource_slug}"
            )

        with open(self.config.resource_file_path, "rb") as fh:
            result = source.upload(fh, method="source")

        logger.info(
            "Source updated: accepted {accepted}, skipped {skipped}, "
            "not found {not_found}, total {total}".format(
                **{
                    k: result.get(k, "?")
                    for k in ("accepted", "skipped", "not_found", "total")
                }
            )
        )

    def get_translation(
        self,
        language_code: str,
        path_to_output_file: str,
    ) -> str:
        """Pull the TS file matching the given language"""
        path = Path(path_to_output_file)
        path.parent.mkdir(parents=True, exist_ok=True)

        translation = next(
            t for t in self.get_resource().list() if t.language_code == language_code
        )
        content = translation.download()

        if path.exists() and path.read_bytes() == content:
            logger.info(f"Translations '{language_code}' unchanged")
        else:
            path.write_bytes(content)
            logger.info(f"Translations '{language_code}' downloaded")
        return str(path)
