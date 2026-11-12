from ctypes import CDLL
from pathlib import Path
from sys import platform

_interface = None


def __getattr__(name: str):
    """Load the native interface library only for ctypes-backed modules."""
    if name != "interface":
        raise AttributeError(name)

    global _interface
    if _interface is None:
        extension = "dylib" if platform == "darwin" else "so"
        path = (Path(__file__).parent / f"../build/libobc-gs-interface.{extension}").resolve()
        _interface = CDLL(str(path))
    return _interface
