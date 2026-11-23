# Translating your plugin

The plugin can be translated on [Weblate](https://weblate.org/) or [Transifex](https://www.transifex.com/).
The translation platform depends on the token given to the command: `--weblate-token` or `--transifex-token`.

## Configuration

```toml
translation_languages = [
    "my_MM",
    "zh",
]
```

| Option | Description | Default |
| :----- | :---------- | :------ |
| `translation_source_language` | The language of the strings in the plugin source code. | `en` |
| `translation_languages` | The languages to translate the plugin into. | |
| `i18n_resource_name` | The name of the TS files (`<i18n_resource_name>_<lang>.ts`, in the `i18n` folder of the plugin).<br/>It is also the component on Weblate and the resource on Transifex. | `project_slug` |
| `i18n_project` | The project on the translation platform, Weblate or Transifex. | `project_slug` |
| `weblate_url` | The Weblate API URL, for a self-hosted Weblate. | `https://hosted.weblate.org/api/` |
| `transifex_organization` | The organization on Transifex. | `github_organization_slug` |

## Local TS files



## Weblate

Weblate support is optional. Install it with:

```bash
pip install 'qgis-plugin-ci[weblate]'
```

This also installs PyQt, which provides `pylupdate`, used to extract the strings to translate.
If needed, set its path with `pylupdate_path` in the configuration.

### Setting up Weblate

qgis-plugin-ci does not create anything on Weblate. Before the first push, create on Weblate:

- the project, with the slug `i18n_project`
- a component in this project, with the slug `i18n_resource_name`, using the *Qt Linguist translation file* (TS) format
  and the file mask `<path to the plugin>/i18n/<i18n_resource_name>_*.ts`
- the languages listed in `translation_languages`

A language of `translation_languages` missing on Weblate is skipped with a warning when pulling the translations.

The API token is either a personal token (`wlu_...`, in your Weblate profile) or a project token.
It needs the permission to upload the source strings to push them.

### Push and pull

```bash
# extract the strings from the plugin and push the source TS file to Weblate
qgis-plugin-ci push-translation --weblate-token ${WEBLATE_TOKEN}

# pull the TS files of all the languages from Weblate, and compile them into QM files
qgis-plugin-ci pull-translation --weblate-token ${WEBLATE_TOKEN} --compile
```

Only the source strings are updated by `push-translation`, the translations made on Weblate are left untouched.

When releasing or packaging with `--weblate-token`, the translations are pulled, compiled and added to the plugin archive:

```yaml
jobs:
  include:
    - stage: push-translation
      if: branch = main
      script: qgis-plugin-ci push-translation --weblate-token ${WEBLATE_TOKEN}

    - stage: deploy
      if: tag IS present
      script:
        - >
          qgis-plugin-ci release ${TRAVIS_TAG}
          --weblate-token ${WEBLATE_TOKEN}
          --github-token ${GH_TOKEN}
          --osgeo-username ${OSGEO_USERNAME}
          --osgeo-password ${OSGEO_PASSWORD}
```

## Transifex

Transifex support is optional. Install it with:

```bash
pip install 'qgis-plugin-ci[transifex]'
```

This also installs PyQt, which provides `pylupdate`, used to extract the strings to translate.
If needed, set its path with `pylupdate_path` in the configuration.

The project and the resource are created on Transifex on the first push if they do not exist,
the missing languages of `translation_languages` are added when pulling.

```yaml
jobs:
  include:
    - stage: push-translation
      if: branch = main
      script: qgis-plugin-ci push-translation --transifex-token ${TX_TOKEN}

    - stage: deploy
      if: tag IS present
      script:
        - >
          qgis-plugin-ci release ${TRAVIS_TAG}
          --transifex-token ${TX_TOKEN}
          --github-token ${GH_TOKEN}
          --osgeo-username ${OSGEO_USERNAME}
          --osgeo-password ${OSGEO_PASSWORD}
```
