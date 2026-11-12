"""GeodeSync launcher for running from source on Windows without a console window.

v3 keeps a single implementation: this file only runs main.py as __main__,
so it can never drift from it (v2 kept a byte-identical copy by hand).
"""
import os
import runpy
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
runpy.run_path(os.path.join(_HERE, "main.py"), run_name="__main__")
