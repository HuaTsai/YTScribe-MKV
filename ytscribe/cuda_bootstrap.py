"""Inject bundled NVIDIA CUDA libs into LD_LIBRARY_PATH and re-exec."""
import os
import sys
from importlib.util import find_spec
from pathlib import Path

_GUARD = "_YTSCRIBE_CUDA_BOOTSTRAPPED"


def ensure_cuda_libs() -> None:
    """If nvidia wheels are installed, prepend their lib dirs to
    LD_LIBRARY_PATH and re-exec so dlopen sees them. No-op on subsequent
    calls or when the wheels aren't installed."""
    if os.environ.get(_GUARD):
        return

    paths: list[str] = []
    for pkg in ("nvidia.cublas", "nvidia.cudnn", "nvidia.cuda_nvrtc"):
        spec = find_spec(pkg)
        if spec is None:
            continue
        # nvidia.* are PEP 420 namespace packages: no __init__.py, so
        # spec.origin is None. The package directory lives in
        # submodule_search_locations instead.
        locations = list(spec.submodule_search_locations or [])
        if spec.origin is not None:
            locations.append(str(Path(spec.origin).parent))
        for loc in locations:
            lib_dir = Path(loc) / "lib"
            if lib_dir.is_dir():
                paths.append(str(lib_dir))
                break

    if not paths:
        return

    existing = os.environ.get("LD_LIBRARY_PATH", "")
    new = ":".join(paths + ([existing] if existing else []))
    os.environ["LD_LIBRARY_PATH"] = new
    os.environ[_GUARD] = "1"
    os.execv(sys.executable, [sys.executable] + sys.argv)
