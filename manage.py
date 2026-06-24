#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path


def use_local_venv():
    """Restart through the project venv when called with a system Python."""
    base_dir = Path(__file__).resolve().parent
    if os.name == 'nt':
        venv_python = base_dir / '.venv' / 'Scripts' / 'python.exe'
    else:
        venv_python = base_dir / '.venv' / 'bin' / 'python'

    current_python = Path(sys.executable).resolve()
    if venv_python.exists() and current_python != venv_python.resolve():
        os.execv(str(venv_python), [str(venv_python), *sys.argv])


def main():
    """Run administrative tasks."""
    use_local_venv()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
