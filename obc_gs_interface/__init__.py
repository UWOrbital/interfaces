from ctypes import CDLL
from pathlib import Path
from sys import platform

if platform == "darwin":
    prefix = "lib"
    extension = "dylib"
elif platform == "win32":
    prefix = ""
    extension = "dll"
else:
    prefix = "lib"
    extension = "so"

# The build directory varies by CMake generator:
# - Unix Makefiles / Ninja: directly in build/
# - MSVC: in build/Debug/ or build/Release/
lib_name = f"{prefix}obc-gs-interface.{extension}"
build_dir = Path(__file__).parent / ".." / "build"
candidates = [
    build_dir / lib_name,
    build_dir / "Debug" / lib_name,
    build_dir / "Release" / lib_name,
]

path = None
for candidate in candidates:
    if candidate.exists():
        path = candidate
        break

if path is None:
    raise FileNotFoundError(f"Could not find {lib_name} in any of: {[str(c) for c in candidates]}")

interface = CDLL(str(path))
