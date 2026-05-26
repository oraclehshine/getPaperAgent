from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


def deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        elif isinstance(v, list):
            if k == "weak_points":
                old = out.get(k, []) if isinstance(out.get(k), list) else []
                out[k] = list(dict.fromkeys([*old, *v]))
            else:
                out[k] = v
        elif v not in (None, ""):
            out[k] = v
    return out
