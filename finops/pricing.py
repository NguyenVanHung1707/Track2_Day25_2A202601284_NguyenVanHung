"""Pricing & purchasing economics — measure in $/1M-token, not $/GPU-hr.

Figures are June-2026 as-of snapshots from the deck's RESEARCH dossier; treat
live prices as fast-moving (re-baseline before each cohort).
"""
from __future__ import annotations


def request_cost(
    input_tok: int,
    output_tok: int,
    price_in_per_m: float,
    price_out_per_m: float,
    cached_in: int = 0,
    cache_discount: float = 0.10,   # Anthropic cached-read ~0.1x (=-90%)
    batch: bool = False,
    batch_discount: float = 0.50,   # Batch API ~ -50%
) -> float:
    """USD cost of a single request. Cached input billed at cache_discount x price."""
    cached_in = min(max(0, cached_in), input_tok)
    uncached_in = input_tok - cached_in
    cost = (
        (uncached_in / 1e6) * price_in_per_m
        + (cached_in / 1e6) * price_in_per_m * cache_discount
        + (output_tok / 1e6) * price_out_per_m
    )
    if batch:
        cost *= batch_discount
    return cost


def dollars_per_million(total_cost_usd: float, total_tokens: int) -> float:
    """Aggregate unit economics: $ per 1,000,000 tokens served."""
    if total_tokens <= 0:
        return 0.0
    return total_cost_usd / (total_tokens / 1e6)


def discount_stack(
    batch: bool = False,
    cache_hit_frac: float = 0.0,
    batch_discount: float = 0.50,
    cache_discount: float = 0.10,
) -> float:
    """Effective fraction of the naive bill after stacking discounts (input-heavy view).

    Discounts MULTIPLY: cache applies to the cached share of input, batch to the
    whole bill. batch + 100% cache-hit -> 0.5 * 0.1 = 0.05 (~95% off).
    """
    cache_mult = cache_hit_frac * cache_discount + (1.0 - cache_hit_frac)
    batch_mult = batch_discount if batch else 1.0
    return cache_mult * batch_mult


def cache_is_worth_it(
    avg_cache_reads: float,
    write_cost_per_m: float,
    read_price_per_m: float,
    read_discount: float = 0.10,
) -> bool:
    """Prompt caching only pays off when total savings from reads exceed cache write/storage cost.
    
    Savings per 1M read tokens = read_price_per_m * (1 - read_discount).
    Break-even reads threshold = write_cost_per_m / (read_price_per_m * (1 - read_discount)).
    """
    savings_per_read = read_price_per_m * (1.0 - read_discount)
    if savings_per_read <= 0:
        return False
    return (avg_cache_reads * savings_per_read) >= write_cost_per_m


def cache_break_even_reads(
    write_cost_per_m: float,
    read_price_per_m: float,
    read_discount: float = 0.10,
) -> float:
    """Calculate minimum average read count per cached prefix to break even."""
    savings_per_read = read_price_per_m * (1.0 - read_discount)
    if savings_per_read <= 0:
        return float("inf")
    return write_cost_per_m / savings_per_read


def break_even_utilization(discount_frac: float) -> float:
    """Utilization at which a commitment pays off ~= 1 - discount.

    A 45% reserved discount needs ~55% utilization (~13.2h/day) to beat on-demand.
    """
    return max(0.0, min(1.0, 1.0 - discount_frac))


def recommend_tier(
    hours_per_day: float,
    interruptible: bool,
    reserved_discount: float = 0.45,
    gpu_type: str | None = None,
    job_days: int | None = None,
    interruption_rate: float | None = None,
) -> str:
    """Pick a purchasing tier from a workload's duty cycle, interruptibility, GPU type, and duration.

    Extensions:
      - Interruption risk varies by GPU: H100/H200 (~3-5%) vs A10G/L4 (~10-15%).
      - Duration & commitment horizon: 3-year commitment (45% discount) requires job_days >= 365.
        For shorter projects (e.g. job_days < 180), 1-year reserved (~28% discount, break-even 72%)
        or on-demand/spot is preferred.
    """
    duty = max(0.0, hours_per_day) / 24.0

    # If advanced parameters are specified
    if interruption_rate is not None or gpu_type is not None or job_days is not None:
        # GPU-specific interruption rate estimation if not explicitly given
        ir = interruption_rate
        if ir is None:
            ir = 0.03 if gpu_type in ("H100", "H200") else (0.05 if gpu_type == "A100" else 0.10)

        # Interruptible workloads: evaluate spot feasibility
        if interruptible:
            # If interrupt rate is very high (>20%) and duty cycle is 24/7, spot risk might be too high
            if ir < 0.20 and hours_per_day <= 24:
                return "spot"

        # Duration-aware reserved commitment
        effective_reserved_discount = reserved_discount
        if job_days is not None and job_days < 365:
            # For short-term workloads (< 1 year), cannot lock 3-year reserved (45% off).
            # 1-year reserved discount is ~28% -> break-even duty cycle = 72% (17.3h/day)
            effective_reserved_discount = 0.28

        be = break_even_utilization(effective_reserved_discount)
        if duty >= be:
            return "reserved"
        return "on_demand"

    # Default documented simple policy (fully backward compatible)
    be = break_even_utilization(reserved_discount)
    if interruptible and hours_per_day < 24:
        return "spot"
    if duty >= be:
        return "reserved"
    return "on_demand"


def spot_checkpoint_cost(
    job_hours: float,
    spot_hr: float,
    on_demand_hr: float,
    interrupt_rate: float = 0.05,      # per-hour chance (H100 spot ~<5%)
    ckpt_overhead_frac: float = 0.03,  # steady cost of writing checkpoints
    rework_hours_per_interrupt: float = 0.5,
) -> dict:
    """Effective cost of running a checkpointable job on spot vs on-demand.

    Interruptions waste the compute since the last checkpoint (rework); checkpointing
    adds a small steady overhead. Spot still wins for interruptible jobs.
    """
    expected_interrupts = job_hours * interrupt_rate
    rework_hours = expected_interrupts * rework_hours_per_interrupt
    effective_hours = job_hours * (1.0 + ckpt_overhead_frac) + rework_hours
    spot_cost = effective_hours * spot_hr
    on_demand_cost = job_hours * on_demand_hr
    savings_pct = (1.0 - spot_cost / on_demand_cost) * 100.0 if on_demand_cost > 0 else 0.0
    return {
        "spot_effective_hours": round(effective_hours, 2),
        "spot_cost": round(spot_cost, 2),
        "on_demand_cost": round(on_demand_cost, 2),
        "savings_pct": round(savings_pct, 1),
    }
