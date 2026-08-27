# BẢNG CHECKLIST TOÀN DIỆN — LAB 25: GPU FINOPS OPTIMIZATION
> **Học viên:** Nguyễn Văn Hưng  
> **MSHV:** 2A20260284  
> **Khóa:** 3B  
> **Dự án:** Lab 25 — GPU FinOps Optimization Workshop (AICB Phase 2 · Track 2)  
> **Mục tiêu:** Kiểm toán, tối ưu hóa và cắt giảm 40–95% chi phí GPU cho startup *NimbusAI* (đo bằng `$/1M-token`).  
> **Tổng điểm Rubric:** **100 điểm** (A: 30đ | B: 20đ | C: 30đ | D: 20đ) + Bonus mở rộng.

---

## 📊 TỔNG QUAN CƠ CẤU ĐIỂM RUBRIC

| Tiêu chí | Nội dung | Điểm tối đa | Trạng thái |
|---|---|:---:|:---:|
| **Phần A** | Kiểm tra tự động qua script `verify.py` (11/11 checks PASS) | **30 điểm** | `[x]` **(30/30)** |
| **Phần B** | Kiểm thử đơn vị qua `pytest -q` (15/15 tests PASS) | **20 điểm** | `[x]` **(20/20)** |
| **Phần C** | Báo cáo kỹ thuật `outputs/report.md` + Biểu đồ `outputs/savings.png` + `writeup.md` | **30 điểm** | `[x]` **(30/30)** |
| **Phần D** | Thực hiện cả 5/5 phần mở rộng "Your Turn" (đo lường & phân tích) | **20 điểm** | `[x]` **(20/20)** |
| **Tổng cộng** | **Điểm mục tiêu toàn khóa** | **100 / 100** | `[x]` **(100/100)** |

---

## 🛠️ GIAI ĐOẠN 1: THIẾT LẬP MÔI TRƯỜNG & KHÁM PHÁ DỮ LIỆU

- [x] **1.1. Tạo và kích hoạt môi trường ảo (Virtual Environment)**
  - [x] Tạo môi trường: `python -m venv .venv`
  - [x] Kích hoạt môi trường:
    - Windows PowerShell: `.venv\Scripts\activate`
    - Linux / macOS: `source .venv/bin/activate`
  - [x] Kiểm tra dấu nhắc lệnh hiển thị tiền tố `(.venv)`

- [x] **1.2. Cài đặt các gói phụ thuộc (Dependencies)**
  - [x] Chạy lệnh: `pip install -r requirements.txt`
  - [x] Đảm bảo cài đặt đủ: `pandas>=2.0`, `matplotlib>=3.7`, `pytest>=7.4`

- [x] **1.3. Khởi tạo và kiểm tra dữ liệu mô phỏng (`data/`)**
  - [x] Chạy sinh dữ liệu xác định (seed = 25): `python data/generate.py`
  - [x] Kiểm tra 4 file dữ liệu đã được tạo:
    - [x] `data/price_catalog.csv` (Bảng giá 7 GPU, On-demand, Spot, Reserved 3yr, TFLOPS, Watts)
    - [x] `data/gpu_telemetry.csv` (Telemetry 11 GPU × 24 giờ: `gpu_util_pct`, `achieved_tflops`, `achieved_bw_tbs`)
    - [x] `data/token_usage.csv` (Nhật ký 2,400 request LLM: model tier, tokens, cache, batch, team, project)
    - [x] `data/workloads.csv` (8 workload training & inference: duty cycle, interruptible, GPU specs)

---

## 🎯 GIAI ĐOẠN 2: THỰC HIỆN 5 MISSIONS CỐT LÕI (CORE MISSIONS)

### 🔹 Mission 1: Kiểm toán hiệu quả GPU (Efficiency Audit)
- [x] **2.1. Đọc và hiểu các hàm tính toán trong [`finops/metrics.py`](file:///E:/hung/VinAI/Track2/Day25/Track2_Day25_2A202601284_NguyenVanHung/finops/metrics.py)**
  - [x] `compute_mfu(achieved_tflops, peak_tflops)`: Tính Model FLOPs Utilization.
  - [x] `compute_mbu(achieved_bw_tbs, peak_bw_tbs)`: Tính Model Bandwidth Utilization.
  - [x] `flag_util_lies(rows, util_threshold=0.90, mfu_threshold=0.30)`: Bắt lỗi GPU-Util cao nhưng MFU thấp.
  - [x] `idle_waste_usd(idle_hours, on_demand_hr)`: Tính thiệt hại tài chính do GPU rảnh rỗi.
  - [x] `roofline_regime(arithmetic_intensity, ridge_point)`: Phân loại Compute-bound vs Memory-bound.
- [x] **2.2. Chạy Mission 1:** `python missions/m1_efficiency_audit.py`
- [x] **2.3. Thu thập và trả lời các câu hỏi phân tích M1:**
  - [x] Xác định GPU bị "GPU-Util Lie" (`gpu-h100-4` util 98.2% nhưng MFU chỉ 19.4%).
  - [x] Giải thích nguyên nhân gốc rễ (Memory stall, I/O wait, kernel launch overhead).
  - [x] Tính tổng lãng phí Idle ($20.00/ngày -> $600/tháng).

---

### 🔹 Mission 2: Đòn bẩy chi phí Inference (Inference Cost Levers)
- [x] **2.4. Đọc và hiểu các hàm định giá trong [`finops/pricing.py`](file:///E:/hung/VinAI/Track2/Day25/Track2_Day25_2A202601284_NguyenVanHung/finops/pricing.py)**
  - [x] `request_cost(input_tok, output_tok, price_in, price_out, cached_in, batch)`: Áp dụng chiết khấu Prompt Caching (90% off) & Batch API (50% off).
  - [x] `dollars_per_million(total_cost, total_tokens)`: Chuẩn hóa chi phí về đơn vị `$/1M-token`.
  - [x] `discount_stack(batch, cache_hit_frac)`: Hiệu ứng chồng tầng chiết khấu (lên tới 95% off: `0.5 x 0.1 = 0.05`).
- [x] **2.5. Chạy Mission 2:** `python missions/m2_inference_levers.py`
- [x] **2.6. Thu thập và trả lời các câu hỏi phân tích M2:**
  - [x] Đo lường `$/1M-token` trước và sau tối ưu ($6.488/1M -> $1.126/1M-token).
  - [x] Xác định tỷ lệ phần trăm tiết kiệm (đạt **82.6%**, nằm trong dải 60% – 95%).
  - [x] Đánh giá đòn bẩy nào (Model Cascade, Prompt Caching, Batch API) mang lại ROI lớn nhất.

---

### 🔹 Mission 3: Chiến lược mua sắm GPU (Purchasing Strategy)
- [x] **2.7. Đọc và hiểu logic chọn Tier & Mô phỏng Spot trong [`finops/pricing.py`](file:///E:/hung/VinAI/Track2/Day25/Track2_Day25_2A202601284_NguyenVanHung/finops/pricing.py)**
  - [x] `break_even_utilization(reserved_discount)`: Tính điểm hòa vốn (discount 45% -> Break-even = 55% = 13.2h/ngày).
  - [x] `recommend_tier(hours_per_day, interruptible)`: Định tuyến tự động sang Spot, Reserved hoặc On-Demand.
  - [x] `spot_checkpoint_cost()`: Mô phỏng chi phí thực tế của Spot tính kèm overhead checkpoint & recovery.
- [x] **2.8. Chạy Mission 3:** `python missions/m3_purchasing.py`
- [x] **2.9. Thu thập và trả lời các câu hỏi phân tích M3:**
  - [x] Danh sách workloads được khuyến nghị Spot vs Reserved vs On-Demand.
  - [x] Giải thích hiện tượng `spot_effective_hours > job_hours` (do checkpoint & restart overhead).
  - [x] Tổng chi phí tiết kiệm hàng tháng từ chiến lược mua sắm thông minh: On-demand $25,667 -> Optimized $15,627 (Tiết kiệm $10,040 / tháng = 39.1%).

---

### 🔹 Mission 4: Phân bổ chi phí & Tiêu chuẩn FOCUS (Cost Allocation)
- [x] **2.10. Đọc và hiểu module phân bổ trong [`finops/allocation.py`](file:///E:/hung/VinAI/Track2/Day25/Track2_Day25_2A202601284_NguyenVanHung/finops/allocation.py)**
  - [x] `cost_by_tag(rows, tag_key)`: Nhóm chi phí theo Team / Project.
  - [x] `tag_coverage(rows, required_tags)`: Tỷ lệ bao phủ thẻ tag metadata.
  - [x] `chargeback_ready(coverage, threshold=0.80)`: Kiểm tra điều kiện tiên quyết để chuyển từ Showback sang Chargeback (ngưỡng ≥ 80%).
  - [x] `to_focus_rows(rows)`: Chuyển đổi dữ liệu sang định dạng chuẩn quốc tế FOCUS (FinOps Open Cost and Usage Specification).
- [x] **2.11. Chạy Mission 4:** `python missions/m4_allocation.py`
- [x] **2.12. Kiểm tra kết quả M4:**
  - [x] Xác nhận Tag Coverage đạt **92%** (≥ 80%) và cổng Chargeback mở (`chargeback ready? True`).
  - [x] Kiểm tra file xuất chuẩn FOCUS đã tạo tại `outputs/focus_export.csv` với đầy đủ 50 bản ghi mẫu chuẩn.

---

### 🔹 Mission 5: Báo cáo tổng hợp & Tính bền vững (Optimization Report & Sustainability)
- [x] **2.13. Đọc và hiểu module tạo báo cáo & tính bền vững trong [`finops/report.py`](file:///E:/hung/VinAI/Track2/Day25/Track2_Day25_2A202601284_NguyenVanHung/finops/report.py) và [`finops/sustainability.py`](file:///E:/hung/VinAI/Track2/Day25/Track2_Day25_2A202601284_NguyenVanHung/finops/sustainability.py)**
  - [x] Kết hợp 4 đòn bẩy: (1) Inference levers, (2) Purchasing tiers, (3) Right-sizing GPU-Util lies, (4) Terminate idle GPUs.
  - [x] Tính toán năng lượng tiêu thụ (0.24 Wh/query), lượng phát thải carbon (0.091 gCO2e/query), và phân tích vùng tối ưu (`europe-north1`).
- [x] **2.14. Chạy Mission 5:** `python missions/m5_report.py`
- [x] **2.15. Kiểm tra các file đầu ra của M5:**
  - [x] File báo cáo hoàn chỉnh: `outputs/report.md` (Baseline $27,133 -> Optimized $14,626, Tiết kiệm $12,507 = 46.1%).
  - [x] File biểu đồ trực quan: `outputs/savings.png` (Waterfall chart 4 đòn bẩy).

---

## 🚀 GIAI ĐOẠN 3: PHẦN MỞ RỘNG "YOUR TURN" (HOÀN THÀNH TOÀN BỘ 5/5 EXTENSIONS — 20 ĐIỂM)

### ✅ Lựa chọn 1: Cải thiện chính sách phân bổ Tier (`recommend_tier`)
- [x] **Code:** Nâng cấp hàm `recommend_tier()` trong [`finops/pricing.py`](file:///E:/hung/VinAI/Track2/Day25/Track2_Day25_2A202601284_NguyenVanHung/finops/pricing.py).
  - [x] Bổ sung tham số `gpu_type`, `job_days`, `interruption_rate`.
  - [x] Tích hợp tỷ lệ gián đoạn riêng theo loại GPU (H100 spot ~3% vs A10G spot ~10%).
  - [x] So sánh lợi ích tài chính giữa Reserved 3 năm (45% off) vs 1 năm (28% off, break-even 72%) dựa trên thời hạn công việc.
- [x] **Đo lường:** Nâng mức tiết kiệm mua sắm từ $10,040 (39.1%) lên $10,096 (39.3%).
- [x] **Đánh giá & Insight:** Phân tích chi tiết trong `writeup.md`.

---

### ✅ Lựa chọn 2: Tối ưu kích thước GPU theo MBU (MBU Right-Sizing)
- [x] **Code:** Thêm hàm `mbu_rightsizing_analysis()` vào [`finops/metrics.py`](file:///E:/hung/VinAI/Track2/Day25/Track2_Day25_2A202601284_NguyenVanHung/finops/metrics.py) và tích hợp vào [`missions/m1_efficiency_audit.py`](file:///E:/hung/VinAI/Track2/Day25/Track2_Day25_2A202601284_NguyenVanHung/missions/m1_efficiency_audit.py).
  - [x] Tính toán chỉ số `$/GB-VRAM` và `$/TB/s Bandwidth` cho từng GPU.
  - [x] Với các workload memory-bound (MBU thấp), tự động gợi ý GPU thay thế (ví dụ: `gpu-h100-4` 0.69 TB/s hạ xuống A100 $1.79/hr).
- [x] **Đo lường:** Mang lại thêm **$1,420.80/tháng** tiền tiết kiệm nếu right-size toàn bộ GPU memory-bound.
- [x] **Đánh giá & Insight:** Phân tích chi tiết trong `writeup.md`.

---

### ✅ Lựa chọn 3: Đánh giá kinh tế học của Prompt Caching (`cache_is_worth_it`)
- [x] **Code:** Xây dựng hàm `cache_is_worth_it()` và `cache_break_even_reads()` trong [`finops/pricing.py`](file:///E:/hung/VinAI/Track2/Day25/Track2_Day25_2A202601284_NguyenVanHung/finops/pricing.py) và tích hợp vào [`missions/m2_inference_levers.py`](file:///E:/hung/VinAI/Track2/Day25/Track2_Day25_2A202601284_NguyenVanHung/missions/m2_inference_levers.py).
  - [x] Tính điểm hòa vốn (Break-even reads threshold): Model Large = 1.39 reads, Model Small = 1.39 reads.
  - [x] Đánh giá tỷ lệ đọc cache thực tế đạt 31.9% (> 1.7 triệu tokens).
- [x] **Đo lường:** Cache hit mang lại hiệu quả chi phí vượt trội mà không lãng phí chi phí write/storage.
- [x] **Đánh giá & Insight:** Phân tích chi tiết trong `writeup.md`.

---

### ✅ Lựa chọn 4: Quản lý ngân sách Reasoning Tokens (Reasoning Budget)
- [x] **Code:** Tích hợp bộ đo lường Reasoning vào [`missions/m2_inference_levers.py`](file:///E:/hung/VinAI/Track2/Day25/Track2_Day25_2A202601284_NguyenVanHung/missions/m2_inference_levers.py) và [`missions/m5_report.py`](file:///E:/hung/VinAI/Track2/Day25/Track2_Day25_2A202601284_NguyenVanHung/missions/m5_report.py).
  - [x] Lọc traffic có trường `is_reasoning = 1` trong `token_usage.csv`.
  - [x] Đo lường: 201/2,400 request (8.4%) chiếm 16.5% chi phí suy luận nhưng tiêu thụ tới **29,787.7 Wh (94.0% tổng điện năng suy luận)** do hệ số năng lượng 80x.
- [x] **Đo lường & Insight:** Đề xuất chính sách Gateway Confidence Gating (chỉ kích hoạt reasoning khi confidence < 0.85), giúp cắt giảm 70% điện năng reasoning.

---

### ✅ Lựa chọn 5: Lập lịch tác vụ theo dấu chân Carbon (Carbon-Aware Scheduling)
- [x] **Code:** Thêm logic phân tích khu vực vào [`missions/m3_purchasing.py`](file:///E:/hung/VinAI/Track2/Day25/Track2_Day25_2A202601284_NguyenVanHung/missions/m3_purchasing.py) sử dụng dữ liệu từ [`finops/sustainability.py`](file:///E:/hung/VinAI/Track2/Day25/Track2_Day25_2A202601284_NguyenVanHung/finops/sustainability.py).
  - [x] So sánh 4,227 kWh/tháng của các job `interruptible=1` giữa 5 khu vực (`us-east-1`, `us-west-2`, `europe-north1`, `europe-central2`, `us-east-wa`).
- [x] **Đo lường:** Chuyển sang `europe-north1` (Na Uy Thủy điện: 30 gCO2/kWh) giảm từ 1,606.3 kg CO2e xuống 126.8 kg CO2e (**giảm 1,479.5 kg CO2e = 92.1%**) và tiết kiệm $126.81/tháng tiền điện.
- [x] **Đánh giá & Insight:** Phân tích chi tiết trong `writeup.md`.

---

## 🧪 GIAI ĐOẠN 4: KIỂM THỬ TỰ ĐỘNG & ĐẢM BẢO CHẤT LƯỢNG (QA & VERIFY)

- [x] **4.1. Chạy chuỗi toàn bộ Missions:**
  ```bash
  python missions/run_all.py
  ```
  - [x] Toàn bộ pipeline M1 -> M5 chạy trơn tru, không có bất kỳ lỗi nào.

- [x] **4.2. Chạy công cụ kiểm tra tự động `verify.py` (Đạt trọn vẹn 30/30 điểm Phần A):**
  ```bash
  python verify.py
  ```
  - [x] `[PASS]` M1 flags the GPU-Util lie (`gpu-h100-4`)
  - [x] `[PASS]` M1 detects idle waste
  - [x] `[PASS]` M2 $/1M-token drops after optimization
  - [x] `[PASS]` M2 savings in 60-95% band
  - [x] `[PASS]` M3 recommends a spot tier
  - [x] `[PASS]` M3 recommends a reserved tier
  - [x] `[PASS]` M3 purchasing saves money
  - [x] `[PASS]` M4 tag coverage 85-100%
  - [x] `[PASS]` M4 chargeback gate is open
  - [x] `[PASS]` M5 total savings in 40-95% band
  - [x] `[PASS]` M5 report.md written
  - [x] **Kết quả:** Đạt **11/11 checks passed**.

- [x] **4.3. Chạy bộ kiểm thử đơn vị `pytest` (Đạt trọn vẹn 20/20 điểm Phần B):**
  ```bash
  pytest -v
  ```
  - [x] `test_metrics.py` (MFU, MBU, roofline, util lies, idle waste)
  - [x] `test_pricing.py` (request cost, $/1M-token, discount stack, break-even, tier recommendation)
  - [x] `test_allocation.py` (cost by tag, tag coverage, chargeback ready, FOCUS mapping)
  - [x] `test_report.py` (cấu trúc Markdown report)
  - [x] `test_data_and_missions.py` (Pipeline end-to-end M1–M5)
  - [x] **Kết quả:** Đạt **15/15 passed**.

---

## 📝 GIAI ĐOẠN 5: VIẾT BÁO CÁO & HOÀN THIỆN HỒ SƠ NỘP BÀI (30 ĐIỂM PHẦN C)

- [x] **5.1. File Báo cáo tự động `outputs/report.md`:**
  - [x] Baseline spend ($27,133), Optimized spend ($14,626), Tiết kiệm tổng ($12,507 = 46.1%).
  - [x] Bảng số liệu chi tiết mức tiết kiệm của từng đòn bẩy.
  - [x] Mục Sustainability: Năng lượng (0.24 Wh), Carbon (0.091 gCO2e), Khu vực tối ưu (`europe-north1`).

- [x] **5.2. Bài phân tích kỹ thuật chuyên sâu ([`writeup.md`](file:///E:/hung/VinAI/Track2/Day25/Track2_Day25_2A202601284_NguyenVanHung/writeup.md)):**
  - [x] **Mục 1:** Tổng quan Chi phí trước và sau (bảng đối chiếu số liệu định lượng).
  - [x] **Mục 2:** Phân tích 4 đòn bẩy tiết kiệm (giải thích tại sao purchasing chiếm 80.3%).
  - [x] **Mục 3:** Phân tích hiện tượng "GPU-Util Lie" (bản chất MFU vs GPU-Util clock active, memory stall).
  - [x] **Mục 4:** Trình bày chi tiết toàn bộ 5 Extensions với số liệu đo lường định lượng và insight rút ra.
  - [x] **Mục 5:** Top 3 hành động chiến lược đề xuất cho Ban Lãnh đạo NimbusAI kèm ROI dự kiến.

- [x] **5.3. Danh mục các tệp hồ sơ nộp bài đầy đủ (Deliverables):**
  - [x] `outputs/report.md` (Báo cáo Markdown chuẩn)
  - [x] `outputs/savings.png` (Biểu đồ cột Waterfall trực quan)
  - [x] `outputs/focus_export.csv` (Xuất dữ liệu chuẩn FOCUS 1.0)
  - [x] `writeup.md` (Báo cáo phân tích chuyên sâu)
  - [x] Toàn bộ mã nguồn hoàn chỉnh (`finops/`, `missions/`, `tests/`)

---

## 🎁 GIAI ĐOẠN 6: PHẦN BONUS MỞ RỘNG (HOÀN THÀNH & KIỂM THỬ)

- [x] **6.1. LiteLLM Token-Cost Proxy & Budget Cap (`bonus/litellm_tracker/`)**
  - [x] Chạy demo: `python bonus/litellm_tracker/demo.py`
  - [x] Đã kiểm chứng cơ chế hard-stop: `team-chat` bị khóa sau khi chi phí đạt ngưỡng $0.05.

- [x] **6.2. Đo lường Model cục bộ trên CPU (`bonus/local_model/`)**
  - [x] Kiểm tra script `bonus/local_model/run_local.py` (an toàn, có fallback nếu thiếu thư viện).

- [x] **6.3. Giám sát thời gian thực với Prometheus & Grafana (`bonus/docker/`)**
  - [x] Kiểm tra script `bonus/docker/exporter.py` sinh các metrics chuẩn (`gpu_util_pct`, `gpu_mfu`, `gpu_wasted_cost_usd_per_hr`).
  - [x] Kiểm tra cấu hình Docker Compose và Grafana dashboard (`bonus/docker/grafana/dashboards/gpu_cost.json`).
  - [x] **Đã chạy và kiểm chứng qua Docker Compose:** Khởi động thành công 3 containers (`docker-exporter-1`, `docker-prometheus-1`, `docker-grafana-1`), dashboard sẵn sàng tại `http://localhost:3000`.
