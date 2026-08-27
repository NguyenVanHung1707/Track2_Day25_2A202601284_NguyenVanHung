"""Efficiency metrics — the numbers that actually drive GPU cost.

Key teaching point (deck §5): nvidia-smi "GPU-Util %" is a *time-active* clock,
not an efficiency metric. A GPU can read 100% util while its MFU is ~20% — you
are paying the full GPU-hour for a fraction of the FLOPs you rented.
"""
from __future__ import annotations


def compute_mfu(achieved_tflops: float, peak_tflops: float) -> float:
    """Model FLOPs Utilization = achieved / peak (clamped to 0..1).

    Good training MFU is ~0.35-0.45; >0.50 is excellent. Returns 0 if peak<=0.
    """
    if peak_tflops <= 0:
        return 0.0
    return max(0.0, min(1.0, achieved_tflops / peak_tflops))


def compute_mbu(achieved_bw_tbs: float, peak_bw_tbs: float) -> float:
    """Model Bandwidth Utilization = achieved HBM BW / peak BW (clamped 0..1).

    The right metric for memory-bound decode; target ~0.60 on H100-80GB batch-1.
    """
    if peak_bw_tbs <= 0:
        return 0.0
    return max(0.0, min(1.0, achieved_bw_tbs / peak_bw_tbs))


def arithmetic_intensity(flops: float, bytes_moved: float) -> float:
    """FLOP / byte for a workload (the x-axis of the roofline model)."""
    if bytes_moved <= 0:
        return 0.0
    return flops / bytes_moved


def roofline_regime(intensity: float, ridge_point: float) -> str:
    """Below the ridge point a workload is memory-bound; at/above it is compute-bound.

    H100 ridge ~295 FLOP/byte (BF16). LLM decode (~1-2) is memory-bound; prefill
    (~455) is compute-bound — which is *why* prefill/decode disaggregation pays off.
    """
    return "compute-bound" if intensity >= ridge_point else "memory-bound"


def flag_util_lies(rows, util_threshold: float = 0.90, mfu_threshold: float = 0.30):
    """Return the rows where GPU-Util is high but MFU is low — money leaking.

    `rows` is an iterable of dicts each having 'gpu_util_pct' (0-100) and 'mfu' (0-1).
    These are GPUs you are billed full-rate for while they do little real compute.
    """
    out = []
    for r in rows:
        util = float(r.get("gpu_util_pct", 0)) / 100.0
        mfu = float(r.get("mfu", 0))
        if util >= util_threshold and mfu < mfu_threshold:
            out.append(r)
    return out


def idle_waste_usd(idle_hours: float, on_demand_hr: float) -> float:
    """Dollars burned by a GPU left running idle (training done, instance up)."""
    return max(0.0, idle_hours) * max(0.0, on_demand_hr)


def mbu_rightsizing_analysis(summary_rows, catalog_by_type) -> dict:
    """Extension 2: Analyze memory-bound workloads and recommend right-sized GPUs.
    
    Computes $/GB-VRAM and $/TB/s BW efficiency for catalog GPUs, and suggests
    downsizing memory-bound GPUs whose achieved bandwidth fits in a cheaper chip.
    """
    catalog_eff = {}
    for gtype, c in catalog_by_type.items():
        od = float(c["on_demand_hr"])
        vram = float(c.get("hbm_gb", 0))
        bw = float(c.get("peak_bw_tbs", 0))
        catalog_eff[gtype] = {
            "on_demand_hr": od,
            "vram_gb": vram,
            "peak_bw_tbs": bw,
            "cost_per_gb_vram": round(od / vram, 4) if vram > 0 else float("inf"),
            "cost_per_tbs_bw": round(od / bw, 4) if bw > 0 else float("inf"),
        }

    recommendations = []
    total_daily_savings = 0.0
    for s in summary_rows:
        cur_type = s["gpu_type"]
        cur_mbu = s.get("mbu", 0.0)
        cur_peak_bw = float(catalog_by_type[cur_type].get("peak_bw_tbs", 1.0))
        achieved_bw = cur_mbu * cur_peak_bw

        # Memory-bound with low MFU (<0.30)
        if s.get("mfu", 0.0) < 0.30 and cur_type in ("H100", "H200", "A100"):
            target_type = None
            target_cost = float("inf")
            for gtype, eff in sorted(catalog_eff.items(), key=lambda x: x[1]["on_demand_hr"]):
                if eff["peak_bw_tbs"] >= achieved_bw * 1.2 and eff["on_demand_hr"] < catalog_eff[cur_type]["on_demand_hr"]:
                    target_type = gtype
                    target_cost = eff["on_demand_hr"]
                    break

            if target_type:
                cur_cost = catalog_eff[cur_type]["on_demand_hr"]
                active_hours = 24 - s.get("idle_hours", 0)
                daily_saving = (cur_cost - target_cost) * active_hours
                total_daily_savings += daily_saving
                recommendations.append({
                    "gpu_id": s["gpu_id"],
                    "current_gpu": cur_type,
                    "achieved_bw_tbs": round(achieved_bw, 3),
                    "recommended_gpu": target_type,
                    "cur_hourly_cost": cur_cost,
                    "new_hourly_cost": target_cost,
                    "daily_savings": round(daily_saving, 2),
                    "monthly_savings": round(daily_saving * 30, 2),
                })

    return {
        "catalog_efficiency": catalog_eff,
        "recommendations": recommendations,
        "total_monthly_savings": round(total_daily_savings * 30, 2),
    }
