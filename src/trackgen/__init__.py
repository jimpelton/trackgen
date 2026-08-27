#  Copyright (c) 2026 DevZero Labs LLC. All rights reserved.

# Exported as `main` rather than `cli`, so the name does not shadow the
# `trackgen.cli` submodule on the package namespace.
from .cli import cli as main

__all__ = ["main"]
