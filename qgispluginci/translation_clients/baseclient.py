from collections.abc import Callable
from enum import StrEnum
from typing import NamedTuple


class I18nPlatform(StrEnum):
    """The translation platforms, the value is the name used in the code and CLI."""

    Transifex = "transifex"
    Weblate = "weblate"


DEFAULT_PLATFORM = I18nPlatform.Weblate


class TranslationConfig(NamedTuple):
    api_token: str
    project_slug: str
    resource_file_path: str
    resource_slug: str
    source_language_code: str = "en"
    # Transifex only
    organization_name: str = ""
    project_name: str | None = None
    i18n_type: str = "QT"
    repository_url: str | None = None
    private: bool = False
    # Weblate only
    api_url: str | None = None


class BaseClient:
    def __init__(
        self,
        config: TranslationConfig,
        update_string_fcn: Callable,
        create_project: bool = True,
    ):
        """
        Parameters
        ----------
        config:
            The config for the Translation platform

        create_project:
            if True, it will create the project, resource and language on Transifex

        """
        self.config = config
        self.login()
        self.project = self.get_project()
        if not self.project and create_project:
            self.project = self.create_project()
            update_string_fcn()
            self.create_resource()

    def login(self):
        raise NotImplementedError

    def get_project(self):
        raise NotImplementedError

    def project_exists(self):
        raise NotImplementedError

    def create_project(self):
        raise NotImplementedError

    def delete_project(self):
        raise NotImplementedError

    def create_resource(self):
        raise NotImplementedError

    def list_resources(self):
        raise NotImplementedError

    def get_resource(self):
        raise NotImplementedError

    def list_languages(self):
        raise NotImplementedError

    def create_language(self, language_code: str):
        raise NotImplementedError

    def update_source_translation(self):
        raise NotImplementedError

    def get_translation(
        self,
        language_code: str,
        path_to_output_file: str,
    ) -> str:
        raise NotImplementedError
