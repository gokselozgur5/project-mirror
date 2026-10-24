import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_soak_module() -> ModuleType:
    path = Path(__file__).parents[1] / "scripts" / "phase1-soak.py"
    spec = importlib.util.spec_from_file_location("project_mirror_phase1_soak", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load phase1 soak module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


soak = load_soak_module()


def test_empty_latency_samples_produce_diagnostic_zeroes() -> None:
    assert soak.median([]) == 0.0
    assert soak.percentile([], 0.95) == 0.0


def test_nearest_rank_percentile_is_deterministic() -> None:
    values = [40.0, 10.0, 30.0, 20.0]

    assert soak.median(values) == 25.0
    assert soak.percentile(values, 0.50) == 20.0
    assert soak.percentile(values, 0.95) == 40.0


def test_rss_growth_requires_both_samples() -> None:
    assert soak.rss_growth_bytes(100, 125) == 25
    assert soak.rss_growth_bytes(None, 125) is None
