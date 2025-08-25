# filesystem_manager.py — minimal local file helper
from __future__ import annotations
import os
from typing import Tuple, List

class FileSystemManager:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _abs(self, rel: str) -> str:
        return os.path.join(self.base_dir, rel.replace("..","_"))

    def write_file(self, rel_path: str, content: str) -> Tuple[bool, str | None]:
        try:
            abs_path = self._abs(rel_path)
            d = os.path.dirname(abs_path)
            os.makedirs(d, exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content or "")
            return True, None
        except Exception as e:
            return False, str(e)

    def list_files(self, rel_dir: str = "", include_dirs: bool = False) -> List[str]:
        root = self._abs(rel_dir)
        out = []
        for dirpath, dirnames, filenames in os.walk(root):
            if include_dirs:
                for d in dirnames: out.append(os.path.relpath(os.path.join(dirpath, d), root))
            for fn in filenames:
                out.append(os.path.relpath(os.path.join(dirpath, fn), root))
        return out
