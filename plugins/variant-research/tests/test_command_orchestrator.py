"""Tests for the command orchestrator (variant-research.md) path assumptions.

These tests verify that the paths and assumptions in the command markdown
actually work in different execution contexts.
"""

import os
from pathlib import Path
import pytest


PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "skills" / "variant-research" / "scripts"
TEMPLATE_DIR = PROJECT_ROOT / "skills" / "variant-research" / "templates"
COMMAND_FILE = PROJECT_ROOT / "commands" / "variant-research.md"


class TestProjectStructure:
    """Verify the expected file structure exists."""

    def test_venv_exists(self):
        venv = PROJECT_ROOT / ".venv"
        assert venv.exists(), f"Virtual environment not found at {venv}"
        assert (venv / "bin" / "python").exists(), "venv/bin/python missing"

    def test_all_scripts_exist(self):
        expected = [
            "resolve_variant.py",
            "fetch_literature.py",
            "fetch_patents.py",
            "fetch_clinical.py",
            "fetch_protein.py",
            "fetch_string_hpa.py",
            "fetch_intact.py",
            "fetch_bioplex.py",
            "fetch_biogrid.py",
            "fetch_drug_targets.py",
            "generate_report.py",
            "setup.sh",
        ]
        for script in expected:
            assert (SCRIPTS_DIR / script).exists(), f"Missing script: {script}"

    def test_template_exists(self):
        assert (TEMPLATE_DIR / "report_template.html").exists()

    def test_reports_dir_exists(self):
        reports = PROJECT_ROOT / "reports"
        assert reports.exists(), f"reports/ directory missing at {reports}"

    def test_scripts_are_executable_python(self):
        """All .py scripts should have valid syntax."""
        import py_compile
        for script in SCRIPTS_DIR.glob("*.py"):
            try:
                py_compile.compile(str(script), doraise=True)
            except py_compile.PyCompileError as e:
                pytest.fail(f"Syntax error in {script.name}: {e}")


class TestCommandPathAssumptions:
    """Test the path assumptions in variant-research.md."""

    def test_command_file_exists(self):
        assert COMMAND_FILE.exists(), f"Command file not found at {COMMAND_FILE}"

    def test_command_has_phase_0_plugin_discovery(self):
        """The command must include Phase 0 that discovers the plugin directory."""
        content = COMMAND_FILE.read_text()
        assert "Phase 0" in content, "Command is missing Phase 0 (plugin discovery)"
        assert "PLUGIN_DIR" in content, "Command is missing PLUGIN_DIR variable"

    def test_command_uses_plugin_dir_not_relative_paths(self):
        """The command must NOT use bare relative paths for scripts or venv.
        All script and venv references should use $PLUGIN_DIR."""
        content = COMMAND_FILE.read_text()
        # These bare relative patterns should NOT appear in command lines
        # (they may appear in the Phase 0 discovery block as the fallback check,
        # which is fine -- we only check they don't appear in the actual script invocations)
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Skip non-command lines, comments, and the Phase 0 discovery block
            if not stripped.startswith("- Prompt:") and not stripped.startswith("source "):
                continue
            # These lines should use $PLUGIN_DIR, not bare relative paths
            if "source .venv/bin/activate" in stripped:
                pytest.fail(
                    f"Line {i}: Uses bare relative venv path 'source .venv/bin/activate'. "
                    f"Should use '$PLUGIN_DIR/.venv/bin/activate'"
                )
            if "python skills/" in stripped:
                pytest.fail(
                    f"Line {i}: Uses bare relative script path 'python skills/...'. "
                    f"Should use '$PLUGIN_DIR/skills/...'"
                )

    def test_command_checks_installed_plugin_path(self):
        """The command should check ~/.claude/plugins/variant-research/ first."""
        content = COMMAND_FILE.read_text()
        assert ".claude/plugins/variant-research" in content, (
            "Command should check the standard plugin install path "
            "~/.claude/plugins/variant-research/"
        )

    def test_command_has_development_fallback(self):
        """The command should fall back to CWD for development mode."""
        content = COMMAND_FILE.read_text()
        assert "Development mode" in content or "development" in content.lower(), (
            "Command should have a fallback for development mode (CWD-relative)"
        )

    def test_all_scripts_referenced_in_command_exist(self):
        """Every script referenced in the command file must exist on disk."""
        content = COMMAND_FILE.read_text()
        # Extract script filenames from the command
        import re
        script_refs = re.findall(r'scripts/(\w+\.py)', content)
        for script_name in script_refs:
            assert (SCRIPTS_DIR / script_name).exists(), (
                f"Command references script '{script_name}' but it doesn't exist in {SCRIPTS_DIR}"
            )

    def test_venv_activate_exists(self):
        """The venv activate script referenced in the command must exist."""
        activate = PROJECT_ROOT / ".venv" / "bin" / "activate"
        assert activate.exists(), "venv activate script not found"

    def test_reports_dir_relative(self):
        """The command expects reports/ relative to CWD."""
        assert (PROJECT_ROOT / "reports").exists()

    def test_script_project_dir_resolution(self):
        """Scripts compute project_dir as script_dir.parent.parent.parent.
        Verify this resolves correctly."""
        script_dir = SCRIPTS_DIR
        # script_dir = skills/variant-research/scripts
        # .parent = skills/variant-research
        # .parent.parent = skills (WRONG - should be project root)
        # .parent.parent.parent = project root
        computed = script_dir.parent.parent.parent
        assert computed == PROJECT_ROOT, (
            f"Script path resolution is WRONG: "
            f"scripts/../../.. = {computed}, expected {PROJECT_ROOT}"
        )

    def test_setup_sh_and_code_use_same_env_var(self):
        """setup.sh and fetch_patents.py should both reference PATENTSVIEW_API_KEY."""
        setup_sh = SCRIPTS_DIR / "setup.sh"
        setup_content = setup_sh.read_text()
        patents_code = (SCRIPTS_DIR / "fetch_patents.py").read_text()
        # Both should use the same env var name
        assert "PATENTSVIEW_API_KEY" in setup_content, (
            "setup.sh should reference PATENTSVIEW_API_KEY"
        )
        assert "PATENTSVIEW_API_KEY" in patents_code, (
            "fetch_patents.py should reference PATENTSVIEW_API_KEY"
        )

    def test_installed_plugin_path_resolved_by_phase_0(self):
        """When installed to ~/.claude/plugins/variant-research/, Phase 0
        should discover the plugin directory automatically. The command
        no longer relies on CWD being the plugin root.

        This test verifies the command structure supports the installed case."""
        content = COMMAND_FILE.read_text()
        # Phase 0 should set PLUGIN_DIR to the installed location first
        assert '$HOME/.claude/plugins/variant-research' in content, (
            "Phase 0 should try the installed plugin path first"
        )
        # Then all script invocations should use PLUGIN_DIR
        assert '$PLUGIN_DIR/.venv/bin/activate' in content, (
            "Venv activation should use $PLUGIN_DIR"
        )
        assert '$PLUGIN_DIR/skills/variant-research/scripts/' in content, (
            "Script paths should use $PLUGIN_DIR"
        )
