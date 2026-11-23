import glob
import logging
import re
import subprocess
import sys
from pathlib import Path

from qgispluginci.exceptions import (
    TranslationFailed,
)
from qgispluginci.parameters import Parameters
from qgispluginci.translation_clients.baseclient import (
    DEFAULT_PLATFORM,
    BaseClient,
    I18nPlatform,
    TranslationConfig,
)


# GLOBALS
logger = logging.getLogger(__name__)


class Translation:
    def __init__(
        self,
        parameters: Parameters,
        api_token: str | None = None,
        create_project: bool = True,
        platform: I18nPlatform = DEFAULT_PLATFORM,
    ):
        """
        Parameters
        ----------
        parameters:

        api_token:
            API token of the translation platform.
            If given, the platform is used to push and pull the TS files.
            Without any token, only local TS and QM files can be handled.

        create_project:
            if True, it will create the project, resource and language on Transifex.
            Not used with Weblate.

        platform:
            The translation platform of the token.

        """
        self.parameters = parameters

        plugin_path = self.parameters.plugin_path
        resource_name = self.parameters.i18n_resource_name
        lang = self.parameters.translation_source_language
        self.ts_file = f"{plugin_path}/i18n/{resource_name}_{lang}.ts"

        self.i18n_client = None

        if not api_token:
            # Only local TS and QM files are handled
            return

        # ValueError for an unknown platform
        platform = I18nPlatform(platform)
        if platform == I18nPlatform.Transifex:
            self.i18n_client = self._create_transifex_client(
                api_token, create_project
            )
        elif platform == I18nPlatform.Weblate:
            self.i18n_client = self._create_weblate_client(api_token)

    def _create_transifex_client(
        self, api_token: str, create_project: bool
    ) -> BaseClient:
        try:
            from qgispluginci.translation_clients.transifex import TransifexClient
        except ImportError as exc:
            raise ImportError(
                "The Transifex support is optional and its dependencies are not installed. "
                "Install them with: pip install 'qgis-plugin-ci[transifex]'"
            ) from exc

        config = TranslationConfig(
            api_token=api_token,
            organization_name=self.parameters.transifex_organization,
            project_slug=self.parameters.i18n_project,
            repository_url=self.parameters.repository_url,
            source_language_code=self.parameters.translation_source_language,
            resource_file_path=self.ts_file,
            resource_slug=self.parameters.i18n_resource_name,
        )
        return TransifexClient(config, self.update_strings, create_project)

    def _create_weblate_client(self, api_token: str) -> BaseClient:
        try:
            from qgispluginci.translation_clients.weblate import WeblateClient
        except ImportError as exc:
            raise ImportError(
                "The Weblate support is optional and its dependencies are not installed. "
                "Install them with: pip install 'qgis-plugin-ci[weblate]'"
            ) from exc

        config = TranslationConfig(
            api_token=api_token,
            api_url=self.parameters.weblate_url,
            organization_name="",
            project_slug=self.parameters.i18n_project,
            repository_url=self.parameters.repository_url,
            source_language_code=self.parameters.translation_source_language,
            resource_file_path=self.ts_file,
            resource_slug=self.parameters.i18n_resource_name,
        )
        # Weblate projects and components are not created by qgis-plugin-ci
        return WeblateClient(config, self.update_strings, create_project=False)

    def language_ts_files(self) -> list[str]:
        """TS files of the translation languages, the source language excluded."""
        plugin_path = self.parameters.plugin_path
        return [
            f"{plugin_path}/i18n/{self.parameters.i18n_resource_name}_{lang}.ts"
            for lang in self.parameters.translation_languages
            if lang != self.parameters.translation_source_language
        ]

    def update_strings(self, all_languages: bool = False):
        """
        Update TS files from plugin source strings.

        The plugin folder is given to pylupdate, which reads all .py and .ui files in it.

        Parameters
        ----------
        all_languages:
            If True, the TS file of each language in `translation_languages` is
            updated too, otherwise only the TS file of the source language.
        """
        ts_files = [self.ts_file]
        if all_languages:
            ts_files += self.language_ts_files()

        cmd = [self.parameters.pylupdate_path, "--no-obsolete"]
        for ts_file in map(Path, ts_files):
            # pylupdate6 creates the TS file, but refuses an existing empty one
            ts_file.parent.mkdir(parents=True, exist_ok=True)
            if ts_file.is_file() and ts_file.stat().st_size == 0:
                ts_file.unlink()
            cmd += ["--ts", str(ts_file)]
        cmd.append(self.parameters.plugin_path)

        try:
            output = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError:
            logger.error(
                f"'{self.parameters.pylupdate_path}' executable not found. "
                "It is provided by PyQt, install it with: "
                "pip install 'qgis-plugin-ci[pyqt]' "
                "or set 'pylupdate_path' in the configuration.",
                exc_info=TranslationFailed(),
            )
            sys.exit(1)

        output_ts_file = Path(self.ts_file)
        ts_file_contents = output_ts_file.read_text()
        # Since the source language sent to Transifex is English and it has two plural forms, the produced output must have the `<numerusform />` tag twice.
        ts_file_contents = ts_file_contents.replace(
            "<numerusform></numerusform>",
            "<numerusform></numerusform><numerusform></numerusform>",
        )
        output_ts_file.write_text(ts_file_contents)

        if output.returncode != 0:
            logger.error(
                f"Translation failed: {output.stderr}", exc_info=TranslationFailed()
            )
            sys.exit(1)
        else:
            logger.info(f"Successfully run pylupdate: {output.stdout}")

        # pylupdate does not set the language, it is needed by Qt Linguist
        if all_languages:
            for ts_file in self.language_ts_files():
                self.set_ts_language(Path(ts_file))

    def set_ts_language(self, ts_file: Path):
        """Set the language attributes of a TS file, from its name: <resource>_<lang>.ts"""
        prefix = f"{self.parameters.i18n_resource_name}_"
        if not ts_file.stem.startswith(prefix):
            return

        attributes = {
            "language": ts_file.stem[len(prefix) :],
            "sourcelanguage": self.parameters.translation_source_language,
        }

        content = ts_file.read_text(encoding="utf-8")
        match = re.search(r"<TS\b([^>]*)>", content)
        if not match:
            return
        tag_attributes = match.group(1)
        for name, value in attributes.items():
            if not re.search(rf"\b{name}=\"[^\"]+\"", tag_attributes):
                # remove an empty attribute, if any, before adding it
                tag_attributes = re.sub(rf"\s*\b{name}=\"\"", "", tag_attributes)
                tag_attributes += f' {name}="{value}"'
        content = content[: match.start(1)] + tag_attributes + content[match.end(1) :]
        ts_file.write_text(content, encoding="utf-8")

    def compile_strings(self):
        """
        Compile TS file into QM files
        """
        cmd = [self.parameters.lrelease_path]
        for file in glob.glob(f"{self.parameters.plugin_path}/i18n/*.ts"):
            cmd.append(file)
        output = subprocess.run(cmd, capture_output=True, text=True)
        if output.returncode != 0:
            logger.error(
                f"Translation failed: {output.stderr}", exc_info=TranslationFailed()
            )
            sys.exit(1)
        else:
            logger.info(f"Successfully run lrelease: {output.stdout}")

    def pull(self):
        """
        Pull TS files from Transifex
        """
        resource = self.i18n_client.get_resource()
        existing_langs = self.i18n_client.list_languages()
        logger.info(
            f"{len(existing_langs)} languages found for resource {resource}:"
            f" ({existing_langs})"
        )
        for lang in self.parameters.translation_languages:
            if lang not in existing_langs:
                logger.debug(f"Creating missing language: {lang}")
                try:
                    self.i18n_client.create_language(
                        language_code=lang,
                    )
                except NotImplementedError:
                    # Weblate: languages are added on the platform
                    logger.warning(
                        f"Language '{lang}' not found on the translation platform, "
                        "add it there to pull it."
                    )
                    continue
                existing_langs.append(lang)
        for lang in existing_langs:
            ts_file = f"{self.parameters.plugin_path}/i18n/{self.parameters.i18n_resource_name}_{lang}.ts"
            logger.debug(f"Downloading translation file: {ts_file}")
            self.i18n_client.get_translation(
                language_code=lang,
                path_to_output_file=ts_file,
            )

    def push(self):
        self.i18n_client.get_resource()
        logger.debug(
            f"Pushing resource: {self.parameters.i18n_resource_name} "
            f"with file {self.ts_file}"
        )
        self.i18n_client.update_source_translation()
