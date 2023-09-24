# SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

    from .util import SimpleContextTest


@pytest.fixture()
def ensure_no_warnings_logged(caplog: pytest.LogCaptureFixture) -> SimpleContextTest:
    """When exiting the context, assert no warning log records have been created."""

    @contextlib.contextmanager
    def assert_nothing_logged_ctx() -> Generator[None, None, None]:
        yield
        assert not [rec for rec in caplog.records if rec.levelno >= logging.WARNING]

    return assert_nothing_logged_ctx
