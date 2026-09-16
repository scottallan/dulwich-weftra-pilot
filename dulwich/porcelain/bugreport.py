# bugreport.py -- Porcelain-like interface for git bugreport
# Copyright (C) 2026 Jelmer Vernooij <jelmer@jelmer.uk>
#
# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-or-later
# Dulwich is dual-licensed under the Apache License, Version 2.0 and the GNU
# General Public License as published by the Free Software Foundation; version 2.0
# or (at your option) any later version. You can redistribute it and/or
# modify it under the terms of either of these two licenses.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# You should have received a copy of the licenses; if not, see
# <http://www.gnu.org/licenses/> for a copy of the GNU General Public License
# and <http://www.apache.org/licenses/LICENSE-2.0> for a copy of the Apache
# License, Version 2.0.
#

"""Porcelain-like interface for ``git bugreport``."""

import datetime
import os
import platform
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..repo import Repo
    from . import RepoPath

#: Default ``strftime``-style format used for the report filename suffix,
#: matching C git's documented default for ``git bugreport --suffix``.
DEFAULT_SUFFIX_FORMAT = "%Y-%m-%d-%H%M"


class BugreportError(Exception):
    """Base class for errors raised by :func:`bugreport`."""


class BugreportOutputDirectoryNotFound(BugreportError):
    """Raised when ``output_directory`` does not exist."""

    def __init__(self, path: str) -> None:
        """Initialize with the missing directory path."""
        self.path = path
        super().__init__(f"Output directory does not exist: {path}")


class BugreportFileExists(BugreportError):
    """Raised when the target bug report file already exists."""

    def __init__(self, path: str) -> None:
        """Initialize with the path that already exists."""
        self.path = path
        super().__init__(
            f"Bug report file already exists: {path} "
            "(refusing to overwrite an existing report)"
        )


def _system_information() -> str:
    """Collect information about the dulwich/Python environment.

    Returns:
      A human-readable text block describing the running dulwich version,
      the Python interpreter and the platform dulwich is running on.
    """
    from .. import __version__

    dulwich_version = ".".join(str(part) for part in __version__)
    return "\n".join(
        [
            "[System Info]",
            f"dulwich version: {dulwich_version}",
            f"Python version: {platform.python_version()}",
            f"Python implementation: {platform.python_implementation()}",
            f"Python executable: {sys.executable}",
            f"Platform: {platform.platform()}",
        ]
    )


def _enabled_hooks(repo: "Repo") -> list[str]:
    """Return the names of hooks that are present and executable in repo."""
    enabled = []
    for name, hook in repo.hooks.items():
        filepath = getattr(hook, "filepath", None)
        if filepath and os.path.exists(filepath) and os.access(filepath, os.X_OK):
            enabled.append(name)
    return sorted(enabled)


def _repository_information(repo: "Repo") -> str:
    """Collect diagnostic information about a discovered repository."""
    enabled_hooks = _enabled_hooks(repo)
    return "\n".join(
        [
            "[Repository Info]",
            f"Repository path: {repo.path}",
            f"Bare repository: {repo.bare}",
            "Enabled hooks: "
            + (", ".join(enabled_hooks) if enabled_hooks else "(none)"),
        ]
    )


def _no_repository_information() -> str:
    """Report text used when no repository could be discovered."""
    return "\n".join(
        [
            "[Repository Info]",
            "No Git repository was found in the current directory or any "
            "parent directory.",
        ]
    )


def _template_section() -> str:
    """User-fillable template, matching the spirit of C git's report template."""
    return "\n".join(
        [
            "Thank you for filling out a Dulwich bug report!",
            "Please answer the following questions to help us understand your issue.",
            "",
            "What did you do before the bug happened? (Steps to reproduce your issue)",
            "",
            "What did you expect to happen? (Expected behavior)",
            "",
            "What happened instead? (Actual behavior)",
            "",
            "Please review the rest of the bug report below.",
            "You can delete any lines you don't wish to share.",
        ]
    )


def bugreport(
    repo: "RepoPath | None" = None,
    output_directory: str | os.PathLike[str] | None = None,
    suffix: str = DEFAULT_SUFFIX_FORMAT,
) -> str:
    """Generate a bug report describing the dulwich environment and repository.

    Writes a plain-text bug report, following C git's documented
    ``git-bugreport(1)`` file-naming contract: the file is named
    ``git-bugreport-<suffix>.txt``, written into ``output_directory`` (or the
    current directory if not given), and ``suffix`` is interpreted as a
    ``strftime``-style format string against the current local time.

    Args:
      repo: Optional path to (or already-open) repository to describe. If
        not given, the repository is discovered from the current directory
        the same way other dulwich commands discover it; if no repository
        is found, the report still succeeds and notes that no repository
        was found.
      output_directory: Directory the report should be written into.
        Defaults to the current working directory. Must already exist.
      suffix: ``strftime``-style format string used to generate the
        filename suffix. Defaults to :data:`DEFAULT_SUFFIX_FORMAT`.

    Returns:
      The path of the bug report file that was written.

    Raises:
      BugreportOutputDirectoryNotFound: if ``output_directory`` is given but
        does not exist.
      BugreportFileExists: if the target report file already exists.
    """
    from ..errors import NotGitRepository
    from . import open_repo_closing

    if output_directory is None:
        directory = os.getcwd()
    else:
        directory = os.fspath(output_directory)
        if not os.path.isdir(directory):
            raise BugreportOutputDirectoryNotFound(directory)

    timestamp = datetime.datetime.now().strftime(suffix)
    target = os.path.join(directory, f"git-bugreport-{timestamp}.txt")
    if os.path.exists(target):
        raise BugreportFileExists(target)

    if repo is None:
        try:
            repo_ctx = open_repo_closing(None)
        except NotGitRepository:
            repo_ctx = None
    else:
        repo_ctx = open_repo_closing(repo)

    if repo_ctx is None:
        repository_section = _no_repository_information()
    else:
        with repo_ctx as r:
            repository_section = _repository_information(r)

    report = (
        "\n\n".join([_template_section(), _system_information(), repository_section])
        + "\n"
    )

    try:
        with open(target, "x", encoding="utf-8") as f:
            f.write(report)
    except FileExistsError:
        raise BugreportFileExists(target) from None

    return target
