# NimbusAI — GPU Cost Optimization Report

> **Executive Summary:** Comprehensive FinOps assessment of NimbusAI infrastructure. By optimizing GPU purchasing tiers, right-sizing underutilized/memory-bound hardware, eliminating idle waste, and deploying multi-layer inference optimizations (Cascade, Prompt Caching, Batch API), projected monthly GPU expenditure drops from **$27,133** to **$14,626**, achieving a **$12,507 (46%) cost reduction**.

- **Billing Period:** Monthly  
- **Baseline spend:** $27,133  
- **Optimized spend:** $14,626  
- **Projected savings:** $12,507  (**46%**)

---

## 1. Savings Breakdown by FinOps Lever

| FinOps Lever | Monthly Savings (USD) | Share of Total Savings | Primary Mechanism |
|---|:---:|:---:|---|
| **Inference (cascade/cache/batch)** | $1,212 | 9.7% | Model cascade (small vs large) + Prompt caching (90% off) + Batch API (50% off) |
| **Purchasing (spot/reserved)** | $10,040 | 80.3% | 3-Year Reserved commitments for steady 24/7 jobs + Spot with checkpointing for fault-tolerant batch |
| **Right-size util-lies** | $655 | 5.2% | Downgrading over-provisioned GPUs (GPU-Util Lie) to right-sized compute/memory chips |
| **Kill idle GPUs** | $600 | 4.8% | Automated instance termination & scaled-to-zero for unutilized GPUs (<10% active clock) |
| **TOTAL PROJECTED SAVINGS** | **$12,507** | **100.0%** | **Comprehensive FinOps Transformation** |

---

## 2. Technical Analysis & Root Cause Insights

### 2.1 The 'GPU-Util Lie' & FLOPs Efficiency (M1 Audit)
- Standard telemetry tools like `nvidia-smi` report time-active clock duty cycle (`GPU-Util %`), NOT true compute throughput.
- In our audit, **`gpu-h100-4` registered 98.2% GPU-Util** but achieved only **19.4% MFU (Model FLOPs Utilization)**. The GPU was heavily stalled on memory bus bandwidth and kernel launch overhead while billing at full H100 hourly rates ($2.50/hr).
- **Financial Impact:** Paying $2.50/hr for 0.20 MFU is equivalent to paying an effective $12.50/hr for peak FLOP delivery. Right-sizing this instance immediately halts capital leakage.

### 2.2 Inference Unit Economics ($/1M-Token vs $/GPU-hr) (M2 Levers)
- Measuring purely in `$/GPU-hr` hides operational efficiency. Unit economics must be tracked in **`$/1M-token`**.
- By implementing a 3-tier discount stack:
  1. **Cascade:** Routing standard requests to small models ($0.20/$0.40 per 1M tok) vs large models ($3.00/$15.00).
  2. **Prompt Caching:** 90% discount on recurrent system prompts & conversation context.
  3. **Batch API:** 50% discount on non-real-time asynchronous evaluations.
- Multiplicative discount stack effect: `0.50 (batch) x 0.10 (cache read) = 0.05` (up to **95% discount** per token).

### 2.3 Purchasing Strategy & Break-Even Dynamics (M3)
- A 45% 3-year Reserved discount has a break-even duty cycle of **55% (13.2 hours/day)**. Workloads running 24/7 (e.g. inference services) yield maximum ROI on Reserved instances.
- Interruptible workloads (training, evaluations) are routed to Spot instances with automated checkpointing, achieving 40%+ savings despite modest checkpoint storage & rework overhead.

### 2.4 Cost Allocation & FOCUS 1.0 Export (M4)
- Achieved **92% tag coverage** across `team` and `project` dimensions, surpassing the 80% threshold required to open the Chargeback gate.
- Billed costs exported in normalized **FOCUS 1.0 (FinOps Open Cost and Usage Specification)** format to ensure cross-cloud multi-vendor transparency.

---

## 3. Advanced Engineering Extensions ('Your Turn')

### Extension 1 — Duration & Interruption-Aware Tier Policy
- Upgraded `recommend_tier()` with GPU-specific interruption risk profiles (H100 spot ~3% vs A10G ~10%) and commitment duration analysis.
- Short-term workloads (<1 year) evaluate 1-Year commitments (28% off, 72% break-even) to prevent locked-in capital waste.

### Extension 2 — MBU-Aware Rightsizing for Memory-Bound Workloads
- Analyzed `$/GB-VRAM` and `$/TB/s Memory Bandwidth` across the entire hardware catalog.
- Workloads with low MFU but memory-bound decode profiles on H100 are downsized to A100/A10G, capturing an additional **$1,420.80/month** in direct savings.

### Extension 3 — Prompt Caching Economics (`cache_is_worth_it`)
- Modeled write/storage fee amortizations. For large model prefixes ($3.75 write vs $3.00 read), break-even read frequency is **1.39 reads**.
- Our production traffic shows a **31.9% cache hit rate**, comfortably exceeding the break-even threshold.

### Extension 4 — Reasoning Tokens Budget & Energy Profile
- Reasoning traffic (`is_reasoning=1`) represents only **8.4% of total requests**, but consumes **16.5% of inference costs** and **94.0% of total electrical energy** (due to the 80x compute/energy multiplier).
- **Policy Recommendation:** Enforce confidence-gated routing (invoke reasoning models only when confidence < 0.85), projected to cut reasoning energy consumption by up to 70%.

### Extension 5 — Carbon-Aware Scheduling for Fault-Tolerant Training
- Relocating 4,227 kWh/month of interruptible training jobs from `us-east-1` (380 gCO2/kWh) to `europe-north1` (Norway hydro: 30 gCO2/kWh) slashes carbon emissions from **1,606.3 kg CO2e** down to **126.8 kg CO2e** — a massive **92.1% carbon reduction**.

---

## 4. Sustainability & Green Computing Snapshot

- **Electrical Energy per Standard Query:** 0.24 Wh
- **Carbon Emissions per Query (US East Grid):** 0.091 gCO2e
- **Cheapest + Cleanest Cloud Region:** `europe-north1` (Norway Hydro / Nordic Grid)

---

## 5. Strategic Recommendations for NimbusAI Leadership

1. **Priority 1 (Day 1): Terminate Idle GPUs & Right-Size 'Util-Lie' Instances.**
   Deploy automated healthcheck scripts to terminate instances with <10% utilization and downsize `gpu-h100-4` to A100/A10G.
2. **Priority 2 (Week 1): Enforce Cascade Routing, Prompt Caching, and Batch API.**
   Mandate small-model first routing in application gateways and schedule overnight batch evaluations via the Batch API to immediately drop inference costs by 80%+.
3. **Priority 3 (Month 1): Transition Chargeback to Engineering Teams & Implement Carbon-Aware Scheduling.**
   Leverage FOCUS 1.0 exports to charge GPU costs directly to department budgets (Assistant, Search, Eval, RAG) and schedule batch training jobs in `europe-north1`.

_Figures are June-2026 as-of snapshots; re-baseline before acting._