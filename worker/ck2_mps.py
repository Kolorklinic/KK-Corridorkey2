# ---------------------------------------------------------------------------
# CorridorKey 2 for Resolve - Apple GPU (MPS) adapter
#
# From Creative Video Tips (CVT)
# Created by Chadwick  |  https://creativevideotips.com
# An unofficial plugin around CorridorKey 2.0 by Corridor Digital.
# Licence: CC BY-NC-SA 4.0 with the CorridorKey additional terms (see LICENSE).
#
# CorridorKey's runtime is written for NVIDIA GPUs (torch.cuda calls,
# Module.cuda(), autocast("cuda")). Its model code is device-neutral. This
# module redirects those calls to the Apple GPU at runtime so CorridorKey's
# own files stay unedited. Call apply() before importing corridorkey.
# ---------------------------------------------------------------------------
from __future__ import annotations

import os

_applied = False
CPU_FALLBACKS = {"adaptive_avg_pool2d": 0}


def apply(autocast_dtype: str = "bf16") -> None:
    """Patch torch so CUDA-only calls run on MPS. autocast_dtype: bf16|fp16|fp32."""
    global _applied
    if _applied:
        return
    os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    if not torch.backends.mps.is_available():
        raise RuntimeError("The Apple GPU (MPS) is not available to PyTorch.")

    mps = torch.device("mps")
    dtype = {"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": None}[autocast_dtype]

    def mem_get_info():
        total = torch.mps.recommended_max_memory()
        return max(0, total - torch.mps.driver_allocated_memory()), total

    torch.cuda.is_available = lambda: True
    torch.cuda.mem_get_info = mem_get_info
    torch.cuda.memory_reserved = lambda *a, **k: torch.mps.driver_allocated_memory()
    torch.cuda.empty_cache = torch.mps.empty_cache
    torch.cuda.synchronize = lambda *a, **k: torch.mps.synchronize()
    torch.cuda.manual_seed_all = lambda seed: torch.mps.manual_seed(seed)
    nn.Module.cuda = lambda self, *a, **k: self.to(mps)

    base_autocast = torch.autocast

    class MpsAutocast(base_autocast):
        def __init__(self, device_type, dtype_=None, enabled=True, cache_enabled=None, **kw):
            dt = kw.pop("dtype", dtype_)
            if device_type == "cuda":
                device_type = "mps"
                if dtype is None:
                    enabled = False
                else:
                    dt = dtype
            super().__init__(device_type, dtype=dt, enabled=enabled,
                             cache_enabled=cache_enabled)

    torch.autocast = MpsAutocast

    # MPS can't area-resize to sizes that don't divide evenly: use the CPU.
    base_pool = F.adaptive_avg_pool2d

    def adaptive_avg_pool2d(inp, output_size):
        if inp.device.type == "mps":
            osz = output_size if isinstance(output_size, (tuple, list)) else (output_size,) * 2
            if any(o is not None and s % o for s, o in zip(inp.shape[-2:], osz)):
                CPU_FALLBACKS["adaptive_avg_pool2d"] += 1
                return base_pool(inp.cpu(), output_size).to(inp.device)
        return base_pool(inp, output_size)

    F.adaptive_avg_pool2d = adaptive_avg_pool2d
    _applied = True
