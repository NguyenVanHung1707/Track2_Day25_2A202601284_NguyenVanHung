"""M2 — Inference Cost Levers: $/1M-token, batch x cache x cascade (deck §7).

Run: python missions/m2_inference_levers.py
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num
from finops import pricing, sustainability

# $/1M tokens (input, output) — illustrative 2026.
MODEL_PRICES = {"small": (0.20, 0.40), "large": (3.00, 15.00)}


def run(verbose: bool = True) -> dict:
    rows = load_csv("token_usage.csv")
    base_cost = opt_cost = 0.0
    total_tokens = 0

    # Extension 4 tracking
    reasoning_reqs = 0
    reasoning_tokens = 0
    reasoning_cost = 0.0
    reasoning_wh = 0.0
    non_reasoning_wh = 0.0

    # Extension 3 tracking
    cached_requests = 0
    total_cached_tokens = 0
    total_input_tokens = 0

    for r in rows:
        inp, out = int(num(r["input_tokens"])), int(num(r["output_tokens"]))
        cached = int(num(r["cached_input_tokens"]))
        is_batch = bool(int(num(r["is_batch"])))
        is_reasoning = bool(int(num(r.get("is_reasoning", 0))))

        req_tokens = inp + out
        total_tokens += req_tokens
        total_input_tokens += inp
        total_cached_tokens += cached
        if cached > 0:
            cached_requests += 1

        # BASELINE: naive deployment — everything on the large model, no cache, no batch
        lin, lout = MODEL_PRICES["large"]
        req_base = pricing.request_cost(inp, out, lin, lout)
        base_cost += req_base

        # OPTIMIZED: cascade (route_tier), prompt caching, batch API
        pin, pout = MODEL_PRICES[r["route_tier"]]
        req_opt = pricing.request_cost(inp, out, pin, pout, cached_in=cached, batch=is_batch)
        opt_cost += req_opt

        # Reasoning tracking
        if is_reasoning:
            reasoning_reqs += 1
            reasoning_tokens += req_tokens
            reasoning_cost += req_opt
            reasoning_wh += sustainability.wh_per_query(req_tokens, is_reasoning=True)
        else:
            non_reasoning_wh += sustainability.wh_per_query(req_tokens, is_reasoning=False)

    base_pm = pricing.dollars_per_million(base_cost, total_tokens)
    opt_pm = pricing.dollars_per_million(opt_cost, total_tokens)
    savings_pct = (1 - opt_cost / base_cost) * 100 if base_cost else 0.0

    # Extension 3: Cache Economics Analysis
    cache_analysis = {
        "cached_requests": cached_requests,
        "cached_req_pct": round(cached_requests / len(rows) * 100, 1),
        "total_cached_tokens": total_cached_tokens,
        "cache_hit_rate": round(total_cached_tokens / total_input_tokens * 100, 1) if total_input_tokens else 0.0,
        "break_even_reads_large": round(pricing.cache_break_even_reads(write_cost_per_m=3.75, read_price_per_m=3.0, read_discount=0.10), 2),
        "break_even_reads_small": round(pricing.cache_break_even_reads(write_cost_per_m=0.25, read_price_per_m=0.20, read_discount=0.10), 2),
    }

    # Extension 4: Reasoning Budget Analysis
    total_wh = reasoning_wh + non_reasoning_wh
    reasoning_analysis = {
        "reasoning_reqs": reasoning_reqs,
        "reasoning_req_pct": round(reasoning_reqs / len(rows) * 100, 1),
        "reasoning_tokens": reasoning_tokens,
        "reasoning_tok_pct": round(reasoning_tokens / total_tokens * 100, 1),
        "reasoning_cost": round(reasoning_cost, 2),
        "reasoning_cost_pct": round(reasoning_cost / opt_cost * 100, 1) if opt_cost else 0.0,
        "reasoning_wh": round(reasoning_wh, 2),
        "reasoning_wh_pct": round(reasoning_wh / total_wh * 100, 1) if total_wh else 0.0,
    }

    if verbose:
        print("== M2 Inference Cost Levers ==")
        print(f"requests={len(rows)}  tokens={total_tokens:,}")
        print(f"baseline  : ${base_cost:,.2f}/day   ${base_pm:.3f}/1M-token")
        print(f"optimized : ${opt_cost:,.2f}/day   ${opt_pm:.3f}/1M-token")
        print(f"savings   : {savings_pct:.1f}%  (cascade + caching + batch)")
        print(f"discount stack (batch + 100% cache): {pricing.discount_stack(batch=True, cache_hit_frac=1.0):.3f} of naive")

        print("\n--- Extension 3: Cache Economics ---")
        print(f"Cache hit rate: {cache_analysis['cache_hit_rate']}% of input tokens ({total_cached_tokens:,} tokens)")
        print(f"Break-even reads (Large tier @ $3.75 write vs $3.00 read): {cache_analysis['break_even_reads_large']} reads")
        print(f"Break-even reads (Small tier @ $0.25 write vs $0.20 read): {cache_analysis['break_even_reads_small']} reads")

        print("\n--- Extension 4: Reasoning Budget & Energy Profile ---")
        print(f"Reasoning requests: {reasoning_reqs}/{len(rows)} ({reasoning_analysis['reasoning_req_pct']}%)")
        print(f"Reasoning cost: ${reasoning_cost:,.2f} ({reasoning_analysis['reasoning_cost_pct']}% of inference bill)")
        print(f"Reasoning energy: {reasoning_wh:,.1f} Wh ({reasoning_analysis['reasoning_wh_pct']}% of total query energy!)")
        print("Routing rule recommendation: Gate reasoning to tasks with confidence < 0.85 to save up to 70% reasoning energy.")

    return {
        "baseline_daily": round(base_cost, 2),
        "optimized_daily": round(opt_cost, 2),
        "baseline_per_m": round(base_pm, 3),
        "optimized_per_m": round(opt_pm, 3),
        "savings_pct": round(savings_pct, 1),
        "total_tokens": total_tokens,
        "cache_analysis": cache_analysis,
        "reasoning_analysis": reasoning_analysis,
    }


if __name__ == "__main__":
    run()
