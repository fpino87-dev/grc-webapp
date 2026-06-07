#!/usr/bin/env python
# govrico - Governance, Risk and Compliance Platform
# Copyright (C) 2026 Pino Federico. All rights reserved.
# SPDX-License-Identifier: AGPL-3.0-or-later OR LicenseRef-govrico-commercial
# For commercial licensing: https://www.linkedin.com/in/fpino87/
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.dev")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

