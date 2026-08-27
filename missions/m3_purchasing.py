"""M3 — Purchasing Strategy: break-even, tier choice, spot-checkpoint sim (deck §4).

Run: python missions/m3_purchasing.py
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num, catalog_by_type
from finops import pricing, sustainability

DAYS = 30


def run(verbose: bool = True) -> dict:
    jobs = load_csv("workloads.csv")
    cat = catalog_by_type()
    on_demand_monthly = optimized_monthly = 0.0
    recs = []

    # Extension 5: Carbon tracking for interruptible workloads
    interruptible_kwh = 0.0

    # Extension 1: Advanced tier tracking
    adv_optimized_monthly = 0.0
    adv_recs = []

    for j in jobs:
        gtype = j["gpu_type"]
        ngpu = int(num(j["num_gpus"]))
        hpd = num(j["hours_per_day"])
        interruptible = bool(int(num(j["interruptible"])))
        c = cat[gtype]
        gpu_hours = hpd * DAYS * ngpu
        od = num(c["on_demand_hr"])
        on_demand_cost = gpu_hours * od
        watts = num(c["watts"])

        # Base policy (for standard verification)
        tier = pricing.recommend_tier(hpd, interruptible)
        if tier == "spot":
            sim = pricing.spot_checkpoint_cost(gpu_hours, num(c["spot_hr"]), od)
            opt_cost = sim["spot_cost"]
        elif tier == "reserved":
            opt_cost = gpu_hours * num(c["reserved_3yr_hr"])
        else:
            opt_cost = on_demand_cost

        on_demand_monthly += on_demand_cost
        optimized_monthly += opt_cost
        recs.append({"job_id": j["job_id"], "gpu_type": gtype, "tier": tier,
                     "on_demand": round(on_demand_cost), "optimized": round(opt_cost)})

        # Extension 1: Advanced policy
        adv_tier = pricing.recommend_tier(hpd, interruptible, gpu_type=gtype, job_days=DAYS*3)
        if adv_tier == "spot":
            ir = 0.03 if gtype in ("H100", "H200") else 0.08
            sim_adv = pricing.spot_checkpoint_cost(gpu_hours, num(c["spot_hr"]), od, interrupt_rate=ir)
            adv_cost = sim_adv["spot_cost"]
        elif adv_tier == "reserved":
            adv_cost = gpu_hours * num(c["reserved_3yr_hr"])
        else:
            adv_cost = on_demand_cost
        adv_optimized_monthly += adv_cost
        adv_recs.append({"job_id": j["job_id"], "tier": adv_tier, "cost": round(adv_cost)})

        # Extension 5: Track energy for interruptible jobs
        if interruptible:
            job_kwh = (gpu_hours * watts) / 1000.0
            interruptible_kwh += job_kwh

    savings = on_demand_monthly - optimized_monthly
    savings_pct = savings / on_demand_monthly * 100 if on_demand_monthly else 0.0

    adv_savings = on_demand_monthly - adv_optimized_monthly
    adv_savings_pct = (adv_savings / on_demand_monthly * 100) if on_demand_monthly else 0.0

    # Extension 5: Regional carbon analysis
    regional_carbon = {}
    for region, carbon_rate in sustainability.REGION_CARBON.items():
        co2_kg = (interruptible_kwh * carbon_rate) / 1000.0
        elec_cost = interruptible_kwh * sustainability.REGION_PRICE_KWH.get(region, 0.12)
        regional_carbon[region] = {
            "carbon_kg": round(co2_kg, 1),
            "electricity_cost": round(elec_cost, 2),
            "carbon_intensity": carbon_rate,
        }

    us_east_co2 = regional_carbon["us-east-1"]["carbon_kg"]
    norway_co2 = regional_carbon["europe-north1"]["carbon_kg"]
    co2_saved_kg = us_east_co2 - norway_co2
    co2_reduction_pct = (co2_saved_kg / us_east_co2 * 100) if us_east_co2 else 0.0

    carbon_analysis = {
        "interruptible_kwh": round(interruptible_kwh, 1),
        "regional_breakdown": regional_carbon,
        "co2_saved_kg": round(co2_saved_kg, 1),
        "co2_reduction_pct": round(co2_reduction_pct, 1),
    }

    if verbose:
        print("== M3 Purchasing Strategy ==")
        print(f"break-even utilization @ 45% reserved discount = {pricing.break_even_utilization(0.45):.0%}")
        print(f"{'job':18}{'gpu':7}{'tier':11}{'on-demand':>12}{'optimized':>12}")
        for r in recs:
            print(f"{r['job_id']:18}{r['gpu_type']:7}{r['tier']:11}${r['on_demand']:>11,}${r['optimized']:>11,}")
        print(f"\nmonthly: on-demand ${on_demand_monthly:,.0f} -> optimized ${optimized_monthly:,.0f}  ({savings_pct:.1f}% saved)")

        print("\n--- Extension 1: Advanced Tier Policy Comparison ---")
        print(f"Standard Purchasing Savings: ${savings:,.0f} ({savings_pct:.1f}%)")
        print(f"Advanced Purchasing Savings: ${adv_savings:,.0f} ({adv_savings_pct:.1f}%)")

        print("\n--- Extension 5: Carbon-Aware Scheduling for Interruptible Workloads ---")
        print(f"Total Interruptible Workload Energy: {interruptible_kwh:,.1f} kWh / month")
        print(f"{'Region':18}{'Grid Carbon (g/kWh)':>22}{'CO2 Emitted (kg)':>20}{'Elec Cost ($)':>16}")
        for reg, data in regional_carbon.items():
            print(f"{reg:18}{data['carbon_intensity']:>22}{data['carbon_kg']:>19.1f} kg${data['electricity_cost']:>15,.2f}")
        print(f"\nCarbon Reduction by relocating to europe-north1: {co2_saved_kg:,.1f} kg CO2e saved ({co2_reduction_pct:.1f}% reduction!)")

    return {
        "recommendations": recs,
        "on_demand_monthly": round(on_demand_monthly),
        "optimized_monthly": round(optimized_monthly),
        "savings_pct": round(savings_pct, 1),
        "advanced_policy_savings_pct": round(adv_savings_pct, 1),
        "carbon_analysis": carbon_analysis,
    }


if __name__ == "__main__":
    run()
