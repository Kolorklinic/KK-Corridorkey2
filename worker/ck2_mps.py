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


def is_intel() -> bool:
    import platform
    return platform.machine() == "x86_64"


def _vram_bytes() -> int:
    """Intel Macs: the largest discrete GPU's memory, from system_profiler."""
    import json
    import subprocess
    env = os.environ.get("CK2_GPU_GB")
    if env:
        return int(float(env) * 2**30)
    try:
        out = subprocess.run(["system_profiler", "-json", "SPDisplaysDataType"],
                             capture_output=True, text=True, timeout=30).stdout
        best = 0
        for gpu in json.loads(out).get("SPDisplaysDataType", []):
            v = gpu.get("spdisplays_vram") or gpu.get("spdisplays_vram_shared") or ""
            parts = v.split()
            if parts and parts[0].isdigit():
                n = int(parts[0]) * (2**30 if "GB" in v else 2**20)
                best = max(best, n)
        if best:
            return best
    except Exception:
        pass
    return 8 * 2**30


def recommended_max_memory() -> int:
    """Bytes the GPU can hold. PyTorch 2.2 (the last for Intel Macs) has no
    torch.mps.recommended_max_memory, so Intel Macs use the GPU's VRAM."""
    import torch
    f = getattr(torch.mps, "recommended_max_memory", None)
    return f() if f is not None else _vram_bytes()


def usable_memory() -> int:
    """Bytes PyTorch will let MPS allocate before it fails. On Apple Silicon
    the recommended working set; on Intel Macs PyTorch allows 1.7x the VRAM
    (PYTORCH_MPS_HIGH_WATERMARK_RATIO), spilling the rest to system RAM."""
    total = recommended_max_memory()
    if is_intel():
        total = int(total * float(os.environ.get("PYTORCH_MPS_HIGH_WATERMARK_RATIO", "1.7")))
    return total


def gpu_name() -> str:
    """'AMD Radeon RX 6700 XT' on Intel Macs; '' when unknown."""
    import json
    import subprocess
    try:
        out = subprocess.run(["system_profiler", "-json", "SPDisplaysDataType"],
                             capture_output=True, text=True, timeout=30).stdout
        gpus = json.loads(out).get("SPDisplaysDataType", [])
        return max(gpus, key=lambda g: g.get("spdisplays_vram", "")).get("sppci_model", "")
    except Exception:
        return ""


def _add_rms_norm(torch, nn, F) -> None:
    """F.rms_norm and nn.RMSNorm arrived in PyTorch 2.4; CorridorKey uses both."""
    if not hasattr(F, "rms_norm"):
        def rms_norm(x, normalized_shape, weight=None, eps=None):
            dims = tuple(range(-len(normalized_shape), 0))
            if eps is None:
                eps = torch.finfo(x.dtype).eps
            y = x * torch.rsqrt(x.pow(2).mean(dim=dims, keepdim=True) + eps)
            return y * weight if weight is not None else y
        F.rms_norm = rms_norm
    if not hasattr(nn, "RMSNorm"):
        class RMSNorm(nn.Module):
            def __init__(self, normalized_shape, eps=None, elementwise_affine=True,
                         device=None, dtype=None):
                super().__init__()
                if isinstance(normalized_shape, int):
                    normalized_shape = (normalized_shape,)
                self.normalized_shape = tuple(normalized_shape)
                self.eps = eps
                self.elementwise_affine = elementwise_affine
                if elementwise_affine:
                    self.weight = nn.Parameter(torch.ones(self.normalized_shape,
                                                          device=device, dtype=dtype))
                else:
                    self.register_parameter("weight", None)

            def forward(self, x):
                return F.rms_norm(x, self.normalized_shape, self.weight, self.eps)

            def extra_repr(self):
                return f"{self.normalized_shape}, eps={self.eps}"
        nn.RMSNorm = RMSNorm


def _bf16_through_cpu(torch) -> None:
    """Intel Macs (PyTorch 2.2): MPS has no bfloat16. CorridorKey stages
    frames on the CPU as bf16; moving them to the GPU turns them into fp32
    (CorridorKey calls .float() right after anyway), and GPU tensors asked
    for as bf16 on the CPU are converted on the CPU."""
    orig_to = torch.Tensor.to
    bf16 = torch.bfloat16

    def to(self, *args, **kwargs):
        try:
            return orig_to(self, *args, **kwargs)
        except TypeError as exc:
            if "BFloat16" not in str(exc):
                raise
        device, dtype, non_blocking, memory_format = torch._C._nn._parse_to(*args, **kwargs)
        extra = {"memory_format": memory_format} if memory_format is not None else {}
        x = orig_to(self, "cpu")
        if device is not None and device.type == "mps":
            if dtype in (None, bf16) and x.dtype == bf16:
                dtype = torch.float32
            elif dtype == bf16:
                dtype = torch.float32
        return orig_to(x, device=device, dtype=dtype or x.dtype,
                       non_blocking=non_blocking, **extra)

    torch.Tensor.to = to


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
        raise RuntimeError("The GPU (MPS) is not available to PyTorch.")

    _add_rms_norm(torch, nn, F)
    mps = torch.device("mps")
    # PyTorch 2.2 can't autocast on MPS: Intel Macs run everything in fp32.
    try:
        torch.autocast("mps", dtype=torch.float16, enabled=False)
        mps_autocast = True
    except RuntimeError:
        mps_autocast = False
    if not mps_autocast:
        autocast_dtype = "fp32"
    dtype = {"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": None}[autocast_dtype]

    def mem_get_info():
        total = recommended_max_memory()
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
            if not mps_autocast and device_type in ("cuda", "mps"):
                # No MPS autocast here: a disabled CPU autocast is a no-op.
                device_type, dt, enabled = "cpu", torch.bfloat16, False
            elif device_type == "cuda":
                device_type = "mps"
                if dtype is None:
                    enabled = False
                else:
                    dt = dtype
            super().__init__(device_type, dtype=dt, enabled=enabled,
                             cache_enabled=cache_enabled)

    torch.autocast = MpsAutocast

    if not mps_autocast:
        _bf16_through_cpu(torch)

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

    if not mps_autocast:
        # PyTorch 2.2 on MPS has no bicubic (or antialiased) resize: use the CPU.
        base_interp = F.interpolate
        CPU_FALLBACKS["interpolate_bicubic"] = 0

        def interpolate(inp, *a, **k):
            mode = k.get("mode", a[2] if len(a) > 2 else "nearest")
            if inp.device.type == "mps" and (mode == "bicubic" or k.get("antialias")):
                CPU_FALLBACKS["interpolate_bicubic"] += 1
                return base_interp(inp.cpu(), *a, **k).to(inp.device)
            return base_interp(inp, *a, **k)

        F.interpolate = interpolate
        _chunked_attention(torch, F)
    _applied = True


ATTN_CHUNK_BYTES = 512 * 2**20     # largest attention matrix computed at once


def _chunked_attention(torch, F) -> None:
    """PyTorch 2.2 on MPS computes attention as one full (queries x keys)
    matrix; at HD that is several GB in one buffer, more than an AMD GPU
    allows. Split the queries into slices so each slice's matrix stays small.
    Each query's result only depends on its own row, so the output is the same."""
    base = F.scaled_dot_product_attention

    def sdpa(query, key, value, attn_mask=None, dropout_p=0.0, is_causal=False, scale=None):
        lq, lk = query.shape[-2], key.shape[-2]
        rows = 1
        for d in query.shape[:-2]:
            rows *= d
        need = rows * lq * lk * query.element_size()
        if query.device.type != "mps" or need <= ATTN_CHUNK_BYTES or is_causal or dropout_p:
            return base(query, key, value, attn_mask=attn_mask, dropout_p=dropout_p,
                        is_causal=is_causal, scale=scale)
        step = max(1, int(lq * ATTN_CHUNK_BYTES // need))
        outs = []
        for s in range(0, lq, step):
            m = attn_mask
            if m is not None and m.dim() >= 2 and m.shape[-2] == lq:
                m = m[..., s:s + step, :]
            outs.append(base(query[..., s:s + step, :], key, value, attn_mask=m, scale=scale))
        return torch.cat(outs, dim=-2)

    F.scaled_dot_product_attention = sdpa
