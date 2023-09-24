# SPDX-FileCopyrightText: 2023 Gert van Dijk <github@gertvandijk.nl>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import contextlib
import re
from collections.abc import Callable
from typing import TypeAlias


def full_match_re(string: str) -> re.Pattern[str]:
    """
    Return a compiled regular expression for an exact string match.

    This is used as a helper function in the work-around for Pytest that only accepts
    regular expressions for comparing exception messages.
    """
    return re.compile(f"^{re.escape(string)}$")


SimpleContextTest: TypeAlias = Callable[[], contextlib.AbstractContextManager[None]]
