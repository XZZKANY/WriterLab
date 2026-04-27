from pathlib import Path
import subprocess
import sys


SCHEMA_MODULES = [
    "app.schemas.book",
    "app.schemas.branch",
    "app.schemas.chapter",
    "app.schemas.character",
    "app.schemas.consistency",
    "app.schemas.knowledge",
    "app.schemas.location",
    "app.schemas.lore_entry",
    "app.schemas.project",
    "app.schemas.scene",
    "app.schemas.scene_analysis_store",
    "app.schemas.scene_version",
    "app.schemas.style_memory",
    "app.schemas.timeline_event",
    "app.schemas.workflow",
]


def test_schema_modules_import_without_class_config_deprecation():
    backend_root = Path(__file__).resolve().parents[1]
    import_lines = "\n".join(f"import {module_name}" for module_name in SCHEMA_MODULES)
    script = "\n".join(
        [
            "import warnings",
            "warnings.filterwarnings('error', category=DeprecationWarning)",
            import_lines,
        ]
    )

    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=backend_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
