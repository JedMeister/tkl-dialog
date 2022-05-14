# Copyright (c) 2022 TurnKey GNU/Linux <admin@turnkeylinux.org>

import re
import sys
import os
import logging
from typing import Optional
try:
    import crack  # type: ignore
except ImportError:
    crack = False

from .exceptions import TklDialogImportError

def fatal(e: str):
    print("error:", e, file=sys.stderr)
    sys.exit(1)


def usage(e: str = None, doc: str = None):
    if e:
        print("Error:", e, file=sys.stderr)

    print(f"Syntax: {sys.argv[0]}", file=sys.stderr)
    if doc:
        print(doc.strip(), file=sys.stderr)
    sys.exit(1)


def password_cracklib(password: str) -> Optional[str]:
    """Parse password with cracklib. Return None if ok, otherwise string."""
    try:
        crack.VeryFascistCheck(password)
        return None
    except NameError:
        raise TklDialogImportError("Cracklib not found. Please install"
                                   " 'python3-cracklib' or avoid this .")
    except ValueError as e:
        return str(e)


def password_complexity(password: str, cracklib: bool = True) -> int:
    """return interger complexity score from 0 (invalid) to 4 (strong)"""

    lowercase = re.search('[a-z]', password) is not None
    uppercase = re.search('[A-Z]', password) is not None
    number = re.search(r'\d', password) is not None
    nonalpha = re.search(r'\W', password) is not None

    return sum([lowercase, uppercase, number, nonalpha])
