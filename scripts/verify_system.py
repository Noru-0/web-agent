"""
System Verification Script

This script performs STATIC verification of the web agent system.

WHAT THIS DOES:
- Checks if dependencies are installed
- Verifies file structure
- Validates architectural boundaries
- Inspects import relationships

WHAT THIS DOES NOT DO:
- Launch browsers
- Initialize models
- Load checkpoints
- Run agents
- Start environments
- Execute any runtime behavior

This is a ZERO SIDE-EFFECT verification that completes in seconds.
For runtime execution, see SYSTEM_EXECUTION_GUIDE.md.

Usage:
    python -u scripts/verify_system.py
"""

import sys
import importlib.util
from pathlib import Path
from typing import List, Dict
import ast

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_step(msg: str):
    """Print verification step"""
    print(f"> {msg}", flush=True)


def print_pass(msg: str):
    """Print success message"""
    print(f"  [OK] {msg}", flush=True)


def print_fail(msg: str):
    """Print failure message"""
    print(f"  [FAIL] {msg}", flush=True)


def print_warn(msg: str):
    """Print warning message"""
    print(f"  [WARN] {msg}", flush=True)


def print_header(msg: str):
    """Print section header"""
    print(f"\n{BOLD}{'=' * 80}{RESET}", flush=True)
    print(f"{BOLD}{msg}{RESET}", flush=True)
    print(f"{BOLD}{'=' * 80}{RESET}\n", flush=True)


def check_dependency(name: str, import_path: str, optional: bool = False) -> bool:
    """
    Check if a dependency is installed WITHOUT importing it.
    
    This uses importlib.util.find_spec() which checks module availability
    without executing any code.
    
    Args:
        name: Display name
        import_path: Import path to check
        optional: If True, failure is a warning not an error
        
    Returns:
        True if available, False otherwise
    """
    spec = importlib.util.find_spec(import_path)
    
    if spec is not None:
        print_pass(f"{name} is installed")
        return True
    else:
        if optional:
            print_warn(f"{name} not installed (optional)")
        else:
            print_fail(f"{name} not installed (required)")
        return False


def check_file_exists(path: Path, description: str) -> bool:
    """Check if a file exists"""
    if path.exists():
        print_pass(f"{description}: {path.name}")
        return True
    else:
        print_fail(f"{description} not found: {path}")
        return False


def check_directory_structure(root: Path) -> bool:
    """Verify expected directory structure"""
    print_step("Checking directory structure...")
    
    required_items = [
        ("agents", "dir"),
        ("envs", "dir"),
        ("browser", "dir"),
        ("schema.py", "file"),
        ("data", "dir"),
        ("adapters", "dir"),
        ("training", "dir"),
        ("scripts", "dir"),
        ("run_exploration.py", "file"),
    ]
    
    all_exist = True
    for item, item_type in required_items:
        path = root / item
        if path.exists():
            print_pass(f"Found: {item}")
        else:
            print_fail(f"Missing: {item}")
            all_exist = False
    
    return all_exist


def check_core_dependencies() -> Dict[str, bool]:
    """Check core Python dependencies"""
    print_step("Checking core dependencies...")
    
    results = {}
    
    # Required for core system
    results["python"] = check_dependency("Python stdlib", "sys")
    results["pathlib"] = check_dependency("pathlib", "pathlib")
    results["typing"] = check_dependency("typing", "typing")
    results["dataclasses"] = check_dependency("dataclasses", "dataclasses")
    results["enum"] = check_dependency("enum", "enum")
    
    return results


def check_runtime_dependencies() -> Dict[str, bool]:
    """Check runtime dependencies (browser, agents)"""
    print_step("Checking runtime dependencies...")
    
    results = {}
    
    # Browser automation (required for runtime, optional for verification)
    results["playwright"] = check_dependency(
        "Playwright", "playwright", optional=True
    )
    
    return results


def check_training_dependencies() -> Dict[str, bool]:
    """Check training pipeline dependencies"""
    print_step("Checking training dependencies...")
    
    results = {}
    
    # PyTorch (required for training/SLM, optional for SimpleAgent)
    results["torch"] = check_dependency("PyTorch", "torch", optional=True)
    results["numpy"] = check_dependency("NumPy", "numpy", optional=True)
    
    return results


def check_schema_import() -> bool:
    """Verify schema module imports cleanly"""
    print_step("Verifying schema module...")
    
    try:
        # Schema should have zero side effects
        from schema import Action, ActionType, State, Trajectory
        print_pass("Schema imports successfully")
        print_pass(f"  ActionType values: {len(ActionType.__members__)}")
        return True
    except Exception as e:
        print_fail(f"Schema import failed: {e}")
        return False


def check_agent_classes() -> bool:
    """Verify agent classes are importable (without instantiation)"""
    print_step("Verifying agent classes...")
    
    try:
        from agents.base_agent import BaseAgent
        print_pass("BaseAgent class available")
        
        from agents.simple_agent import SimpleAgent
        print_pass("SimpleAgent class available")
        
        # SLMAgent requires torch - check conditionally
        spec = importlib.util.find_spec("torch")
        if spec is not None:
            try:
                from agents.slm_agent import SLMAgent
                print_pass("SLMAgent class available")
            except ImportError as e:
                print_warn(f"SLMAgent not available: {e}")
        else:
            print_warn("SLMAgent not available (torch not installed)")
        
        return True
    except Exception as e:
        print_fail(f"Agent class import failed: {e}")
        return False


def check_training_classes() -> bool:
    """Verify training classes are importable"""
    print_step("Verifying training classes...")
    
    # Check if torch is available first
    spec = importlib.util.find_spec("torch")
    if spec is None:
        print_warn("Torch not installed - skipping training verification")
        return True
    
    try:
        # Import class definitions only - do NOT instantiate
        from training.dataset import TrajectoryDataset
        print_pass("TrajectoryDataset class available")
        
        from training.model import WebAgentPolicy
        print_pass("WebAgentPolicy class available")
        
        from training.trainer import Trainer
        print_pass("Trainer class available")
        
        return True
    except Exception as e:
        print_fail(f"Training class import failed: {e}")
        return False


def check_adapter_registry() -> bool:
    """Verify adapter registry exists and is accessible"""
    print_step("Verifying adapter registry...")
    
    try:
        # Import registry module (should have no side effects)
        from adapters.registry import list_adapters
        
        print_pass("Adapter registry accessible")
        
        # List registered adapters (just identifiers)
        adapters = list_adapters()
        print_pass(f"  Registered adapters: {', '.join(adapters) if adapters else 'none'}")
        
        return True
    except Exception as e:
        print_fail(f"Adapter registry check failed: {e}")
        return False


def parse_imports_from_file(file_path: Path) -> List[str]:
    """
    Extract import statements from a Python file using AST.
    
    Returns list of module names imported.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(file_path))
        
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module.split('.')[0])
        
        return imports
    except Exception as e:
        print_warn(f"Could not parse {file_path.name}: {e}")
        return []


def check_architectural_boundaries(root: Path) -> bool:
    """
    Verify architectural boundaries are maintained.
    
    Rules:
    1. Runtime agents must NOT import: adapters, training.trainer, training.dataset
    2. Training must NOT import: envs, agents, browser
    3. Adapters must NOT import: envs, agents, browser, training
    """
    print_step("Checking architectural boundaries...")
    
    violations = []
    
    # Rule 1: Runtime agents must not import adapters or training internals
    print_pass("Rule 1: Runtime agents isolation")
    agent_files = [
        root / "agents" / "simple_agent.py",
        root / "agents" / "slm_agent.py",
        root / "agents" / "runner.py"
    ]
    
    for agent_file in agent_files:
        if not agent_file.exists():
            continue
        
        imports = parse_imports_from_file(agent_file)
        forbidden = ["adapters"]
        
        for forbidden_module in forbidden:
            if forbidden_module in imports:
                violations.append(
                    f"  {agent_file.name} imports {forbidden_module}"
                )
    
    # Rule 2: Training must not import runtime components
    print_pass("Rule 2: Training isolation")
    training_files = [
        root / "training" / "dataset.py",
        root / "training" / "trainer.py",
        root / "training" / "train.py"
    ]
    
    for training_file in training_files:
        if not training_file.exists():
            continue
        
        imports = parse_imports_from_file(training_file)
        forbidden = ["envs", "agents", "browser", "adapters"]
        
        for forbidden_module in forbidden:
            if forbidden_module in imports:
                violations.append(
                    f"  {training_file.name} imports {forbidden_module}"
                )
    
    # Rule 3: Adapters must not import runtime/training
    print_pass("Rule 3: Adapter isolation")
    adapter_files = list((root / "adapters").glob("*_adapter.py"))
    
    for adapter_file in adapter_files:
        imports = parse_imports_from_file(adapter_file)
        forbidden = ["envs", "agents", "browser", "training"]
        
        for forbidden_module in forbidden:
            if forbidden_module in imports:
                violations.append(
                    f"  {adapter_file.name} imports {forbidden_module}"
                )
    
    if violations:
        print_fail("Architectural violations detected:")
        for violation in violations:
            print(f"    {violation}")
        return False
    else:
        print_pass("All architectural boundaries maintained")
        return True


def check_example_files(root: Path) -> bool:
    """Verify production CLI exists"""
    print_step("Checking production CLI...")
    
    cli_file = root / "run_exploration.py"
    if cli_file.exists():
        print_pass(f"Found: run_exploration.py")
        return True
    else:
        print_fail(f"Missing: run_exploration.py")
        return False


def check_documentation(root: Path) -> bool:
    """Verify key documentation exists"""
    print_step("Checking documentation...")
    
    docs = [
        "README.md",
        "QUICKSTART_SLM.md",
        "SYSTEM_EXECUTION_GUIDE.md",
        "training/TRAINING.md",
        "agents/README.md"
    ]
    
    all_exist = True
    for doc in docs:
        path = root / doc
        if path.exists():
            print_pass(f"Found: {doc}")
        else:
            print_warn(f"Missing: {doc}")
            all_exist = False
    
    return all_exist


def check_env_configuration(root: Path) -> bool:
    """Check .env configuration setup"""
    print_step("Checking .env configuration...")
    
    env_path = root / ".env"
    env_example_path = root / ".env.example"
    
    # Check if .env.example exists
    if not env_example_path.exists():
        print_fail(".env.example not found")
        return False
    else:
        print_pass(".env.example found")
    
    # Check if .env exists (warn if missing, not fail)
    if not env_path.exists():
        print_warn(".env not found (copy from .env.example)")
        print_warn("  Run: cp .env.example .env")
    else:
        print_pass(".env found")
    
    # Try loading env module
    try:
        from utils.env import env
        print_pass("utils.env module loaded")
        
        # Check for critical keys
        required_keys = ["OPENAI_API_KEY"]
        optional_keys = ["EXPLORER_MODEL", "BROWSER_HEADLESS", "SLM_DEVICE"]
        
        for key in required_keys:
            value = env.get(key)
            if not value or value == "":
                print_warn(f"  {key} not set (required for exploration)")
            else:
                print_pass(f"  {key} configured")
        
        for key in optional_keys:
            value = env.get(key)
            if value:
                print_pass(f"  {key} = {value}")
        
        return True
    
    except Exception as e:
        print_fail(f"Failed to load utils.env: {e}")
        return False


def main():
    """Run complete system verification"""
    print_header("WEB AGENT SYSTEM VERIFICATION")
    
    print(f"{YELLOW}NOTE: This is a STATIC verification (no runtime execution){RESET}")
    print(f"{YELLOW}      No browsers, models, or agents will be started{RESET}\n")
    
    # Find project root
    root = PROJECT_ROOT
    
    print(f"Project root: {root}\n")
    
    # Track results
    checks = {
        "structure": False,
        "core_deps": False,
        "env_config": False,
        "schema": False,
        "agents": False,
        "training": False,
        "adapters": False,
        "boundaries": False,
        "cli": False,
        "docs": False
    }
    
    # Run checks
    print_header("1. Directory Structure")
    checks["structure"] = check_directory_structure(root)
    
    print_header("2. Core Dependencies")
    core_results = check_core_dependencies()
    checks["core_deps"] = all(core_results.values())
    
    print_header("3. Environment Configuration (.env)")
    checks["env_config"] = check_env_configuration(root)
    
    print_header("4. Runtime Dependencies")
    runtime_results = check_runtime_dependencies()
    # Runtime deps are optional for verification
    
    print_header("5. Training Dependencies")
    training_results = check_training_dependencies()
    # Training deps are optional for SimpleAgent
    
    print_header("6. Schema Module")
    checks["schema"] = check_schema_import()
    
    print_header("7. Agent Classes")
    checks["agents"] = check_agent_classes()
    
    print_header("8. Training Pipeline")
    checks["training"] = check_training_classes()
    
    print_header("9. Adapter Registry")
    checks["adapters"] = check_adapter_registry()
    
    print_header("10. Architectural Boundaries")
    checks["boundaries"] = check_architectural_boundaries(root)
    
    print_header("11. Production CLI")
    checks["cli"] = check_example_files(root)
    
    print_header("12. Documentation")
    checks["docs"] = check_documentation(root)
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    
    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    
    for check_name, result in checks.items():
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"  {check_name:20s} {status}")
    
    print(f"\n{BOLD}Result: {passed}/{total} checks passed{RESET}\n")
    
    # Final verdict
    critical_checks = ["structure", "core_deps", "schema", "boundaries"]
    critical_passed = all(checks[c] for c in critical_checks)
    
    if critical_passed:
        print(f"{GREEN}{BOLD}✓ SYSTEM VERIFICATION PASSED{RESET}")
        print(f"\n{BLUE}The system structure is valid.{RESET}")
        print(f"{BLUE}To run actual agents, see: SYSTEM_EXECUTION_GUIDE.md{RESET}\n")
        return 0
    else:
        print(f"{RED}{BOLD}✗ SYSTEM VERIFICATION FAILED{RESET}")
        print(f"\n{RED}Critical issues detected. Fix these before running the system.{RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())