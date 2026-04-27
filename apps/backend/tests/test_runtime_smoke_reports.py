from pathlib import Path
import runpy

_SUITE_PATH = Path(__file__).with_name("runtime").joinpath("runtime_smoke_reports_suite.py")
_SUITE_EXPORTS = runpy.run_path(_SUITE_PATH)

globals().update(
    {
        name: value
        for name, value in _SUITE_EXPORTS.items()
        if not name.startswith("__")
    }
)
