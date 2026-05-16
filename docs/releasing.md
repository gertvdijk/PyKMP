# Releasing
<!--
SPDX-FileCopyrightText: 2026 Gert van Dijk <github@gertvandijk.nl>

SPDX-License-Identifier: CC0-1.0
-->

## Versioning

Build the release from the commit that should become the release.
If the commit is not tagged yet, `setuptools_scm` will generate a development version
instead of the final release version.

## Release checklist

1. Start from a clean worktree on the branch or commit to release.
1. Sync the tooling and dependencies:

    ```console
    $ uv sync
    ```

1. Run the local quality checks:

    ```console
    $ uv run ./run-all-linters
    $ uv run pytest
    $ uv run zensical build
    ```

1. Create the release tag on the release commit:

    ```console
    $ git tag --sign --annotate --message "Release 0.0.2" 0.0.2
    ```

1. Build the source distribution and wheel locally:

    ```console
    $ uv build --no-sources
    ```

    Note: `--no-sources` skips possibly specified dependencies `tool.uv.sources` as a
    safeguard to not use these alternative dependency sources for development; it still
    ships a source distribution.

1. Verify the generated metadata and distribution files:

    ```console
    $ ls dist/
    ```

    You should see files named like `dist/PyKMP-0.0.2.tar.gz` and
    `dist/pykmp-0.0.2-py3-none-any.whl` on a clean git checkout of the `0.0.2` tag.

1. Verify the built wheel passes the check-wheel-contents linter:

    ```console
    $ uv run check-wheel-contents dist/*.whl
    ```

1. Upload to PyPI:

    ```console
    $ uv publish --index testpypi --dry-run
    ```

    For local publishing to PyPI, use a PyPI token, for example through the
    `UV_PUBLISH_TOKEN` environment variable.

    Repeat without `--dry-run` if you confirmed this is what you intend to publish.

    As an extra safety check, publish to TestPyPI first by specifying `--index testpypi`
    with that being configured as an index in `pyproject.toml`.
    Repeat the upload without this option to publish to the regular PyPI index.

    If `dist/` still contains files from an older build, remove them to avoid uploading
    the wrong artifacts.

    Ensure to **not** publish development versions, e.g.
    `pykmp-0.0.2.dev30+g578be6af2.d20260417-py3-none-any.whl`.

1. Push the commit and tag:

    ```console
    $ git push origin HEAD
    $ git push origin 0.0.2
    ```

## Publish documentation

1. Build the documentation:

    ```console
    $ uv run zensical build --clean
    ```

1. Publish using `ghp-import`:

    ```console
    $ COMMIT_ID="$(git describe --dirty)"
    $ ZENSICAL_VERSION="$(uv run zensical --version)"
    $ uv run ghp-import \
        --no-jekyll \
        --message="Deployed ${COMMIT_ID} with Zensical version ${ZENSICAL_VERSION}" \
        --remote=origin \
        --push \
        site/
    ```
