# BÁO CÁO PHÂN TÍCH KỸ THUẬT & CHIẾN LƯỢC TỐI ƯU HÓA GPU FINOPS
## Khách hàng: NimbusAI (AI Startup) | Tác giả: FinOps Lead Engineer

---

## 1. TỔNG QUAN HIỆU QUẢ TÀI CHÍNH (BASELINE VS. OPTIMIZED)

Trong bối cảnh chi phí cơ sở hạ tầng AI tại NimbusAI tăng phi mã, việc kiểm toán toàn diện từ tầng phần cứng (Hardware telemetry) đến tầng ứng dụng (Token unit economics) đã giúp xây dựng lộ trình cắt giảm chi phí bền vững.

### Bảng đối chiếu các chỉ số kinh tế then chốt:

| Chỉ số | Baseline (Chưa tối ưu) | Optimized (Đã tối ưu) | Mức cắt giảm / Cải thiện |
|---|:---:|:---:|:---:|
| **Tổng chi phí GPU hàng tháng** | **$27,133** / tháng | **$14,626** / tháng | **-$12,507 (-46.1%)** |
| **Đơn giá suy luận (`$/1M-token`)** | **$6.488** / 1M token | **$1.126** / 1M token | **-$5.362 (-82.6%)** |
| **Chi phí Inference trung bình** | $48.87 / ngày | $8.48 / ngày | -$40.39 / ngày |
| **Chi phí Purchasing (Workloads)** | $25,667 / tháng | $15,627 / tháng | -$10,040 / tháng |
| **Lãng phí do GPU Idle** | $600 / tháng | $0 / tháng | -$600 / tháng (100%) |
| **Lãng phí do Over-provisioning (Util-Lie)** | $655 / tháng | $0 / tháng | -$655 / tháng (100%) |

> **Nhận định cốt lõi:** Việc chuyển đổi góc nhìn từ `$/GPU-giờ` sang `$/1M-token` là bước ngoặt quyết định. Chi phí suy luận trên mỗi triệu token giảm hơn **5.7 lần**, cho phép NimbusAI mở rộng quy mô lượng người dùng phục vụ mà không làm phình to hóa đơn điện toán.

---

## 2. PHÂN TÍCH CHI TIẾT 4 ĐÒN BẨY TIẾT KIỆM (SAVINGS LEVERS)

Tổng số tiền tiết kiệm **$12,507/tháng** được cấu thành từ 4 đòn bẩy chính:

```
                          CƠ CẤU TIẾT KIỆM CHI PHÍ
+----------------------------------------------------+----------+
| Đòn bẩy (Lever)                                    | Tiết kiệm|
+----------------------------------------------------+----------+
| 1. Purchasing Strategy (Spot / Reserved 3-yr)      | $10,040  | (80.3%)
| 2. Inference Optimization (Cascade/Cache/Batch)    | $1,212   | (9.7%)
| 3. Right-sizing Over-provisioned GPUs (Util-Lies)  | $655     | (5.2%)
| 4. Terminate & Scale-to-Zero Idle GPUs             | $600     | (4.8%)
+----------------------------------------------------+----------+
| TỔNG CỘNG                                          | $12,507  | (100.0%)
+----------------------------------------------------+----------+
```

### Đánh giá chuyên sâu từng đòn bẩy:
1. **Purchasing Strategy (Đóng góp lớn nhất — 80.3%):**
   - **Tại sao lớn nhất?** Các tác vụ huấn luyện (`job-train-llm`, `job-train-embed`) và dịch vụ suy luận 24/7 (`job-infer-chat`, `job-infer-rag`) tiêu thụ lượng GPU-giờ khổng lồ.
   - **Cơ chế:** Chuyển các dịch vụ 24/7 sang **Reserved 3-Year** (chiết khấu ~45%, vượt xa điểm hòa vốn 55% duty cycle = 13.2h/ngày). Định tuyến các tác vụ huấn luyện và batch có khả năng chịu lỗi sang **Spot Instances** kết hợp cơ chế lưu checkpoint định kỳ.
2. **Inference Levers (Đóng góp 9.7% tổng chi phí, nhưng giảm 82.6% chi phí suy luận):**
   - **Cơ chế:** Tận dụng hiệu ứng chồng chiết khấu nhân tử (Multiplicative discount stack):
     $$\text{Effective Cost} = \text{Batch Discount (50%)} \times \text{Cache Discount (10%)} = 0.05 \text{ (Giảm tới 95%)}$$
   - Định tuyến các câu hỏi thông thường sang Model nhỏ ($0.20/$0.40/1M tok) thay vì ép toàn bộ qua Model lớn ($3.00/$15.00/1M tok).
3. **Right-sizing Util-Lies (Đóng góp 5.2%):**
   - Hạ cấp các GPU đắt tiền (H100 $2.50/hr) đang bị nghẽn băng thông xuống GPU phù hợp hơn (A100 $1.79/hr).
4. **Kill Idle GPUs (Đóng góp 4.8%):**
   - Tự động tắt hoặc thu hồi các GPU có mức sử dụng xung nhịp `< 10%` trong suốt ca làm việc.

---

## 3. BẢN CHẤT CỦA "GPU-UTIL LIE" VÀ TÁC ĐỘNG TÀI CHÍNH

### Hiện tượng phát hiện trong đợt kiểm toán (M1):
- `gpu-h100-4` ghi nhận chỉ số **GPU-Util = 98.2%**, tạo cảm giác phần cứng đang vận hành hết công suất.
- Tuy nhiên, chỉ số **MFU (Model FLOPs Utilization)** thực tế chỉ đạt **0.194 (19.4%)**, và **MBU (Model Bandwidth Utilization) chỉ đạt 0.207**.

### Giải thích cơ chế kỹ thuật:
- `nvidia-smi` chỉ đo tỷ lệ thời gian mà nhân GPU có xung nhịp hoạt động (time-active clock), **hoàn toàn không đo lường mật độ tính toán hữu ích**.
- Hiện tượng này xảy ra do GPU bị nghẽn cổ chai nghiêm trọng tại bus bộ nhớ (Memory bandwidth stall), truyền dữ liệu I/O từ CPU sang GPU (Host-to-Device transfer bottleneck), hoặc do kích thước batch quá nhỏ dẫn đến overhead khởi tạo kernel (kernel launch latency).
- **Tác động tài chính:** NimbusAI đang chi trả trọn vẹn **$2.50/GPU-giờ** cho phần cứng H100 nhưng chỉ thu về giá trị tương đương **$0.485/giờ** hiệu năng tính toán thực. Đây là hình thức rò rỉ ngân sách âm thầm và nguy hiểm nhất.

---

## 4. CHI TIẾT KẾT QUẢ ĐO LƯỜNG 5 PHẦN MỞ RỘNG ("YOUR TURN")

Cả 5 phần mở rộng đã được triển khai hoàn chỉnh vào engine `finops/` và các kịch bản kiểm toán:

### 🔹 Extension 1: Nâng cấp chính sách chọn Tier (`recommend_tier`)
- **Giải pháp:** Tích hợp tỷ lệ ngắt quãng theo từng dòng GPU (H100 Spot ~3% rủi ro ngắt vs A10G Spot ~10%) và phân tích vòng đời dự án (Job duration). Đối với các dự án ngắn hạn (< 1 năm), áp dụng mức cam kết 1-Year Reserved (chiết khấu 28%, điểm hòa vốn 72% duty cycle) để tránh rủi ro "chôn vốn" 3 năm.
- **Đo lường:** Chi phí mua sắm theo chính sách nâng cao tối ưu thêm từ **$10,040 (39.1%)** lên **$10,096 (39.3%)**, bảo vệ dòng tiền linh hoạt cho startup.

### 🔹 Extension 2: Tối ưu kích thước GPU theo MBU (MBU Right-Sizing)
- **Giải pháp:** Tính toán ma trận hiệu quả `$/GB-VRAM` và `$/TB/s Bandwidth` cho toàn bộ catalog. Với các GPU H100/A100 chạy tác vụ giải mã (LLM Decode) bị nghẽn bộ nhớ nhưng chỉ đạt thông lượng 0.49–0.91 TB/s, tự động gợi ý hạ cấp sang A100 hoặc A10G.
- **Đo lường:** Đề xuất right-size cho `gpu-h100-4`, `gpu-h100-5`, `gpu-a100-1` mang lại thêm **$1,420.80/tháng** tiền tiết kiệm.

### 🔹 Extension 3: Đánh giá kinh tế học của Prompt Caching (`cache_is_worth_it`)
- **Giải pháp:** Xây dựng mô hình điểm hòa vốn số lần đọc:
  $$\text{Break-even Reads} = \frac{\text{Write Cost per 1M}}{\text{Read Price per 1M} \times (1 - \text{Discount})}$$
- **Đo lường:** Với Model Large ($3.75 write vs $3.00 read), ngưỡng hòa vốn là **1.39 lần đọc**. Trên thực tế, dữ liệu NimbusAI đạt tỷ lệ trúng cache **31.9%** (hơn 1.7 triệu tokens), khẳng định tính năng Prompt Caching đem lại lợi nhuận biên ròng vượt trội.

### 🔹 Extension 4: Quản lý ngân sách Reasoning Tokens (Reasoning Budget)
- **Giải pháp:** Bóc tách và đo lường độc lập lưu lượng `is_reasoning = 1`.
- **Đo lường:** 
  - Lưu lượng Reasoning chỉ chiếm **8.4% tổng số request** (201/2,400) và 16.5% chi phí suy luận.
  - Tuy nhiên, do tiêu tốn gấp ~80 lần năng lượng tính toán, traffic reasoning chiếm tới **29,787.7 Wh (94.0% tổng điện năng suy luận)**!
  - **Khuyến nghị chính sách:** Áp dụng bộ lọc Gateway chỉ chuyển sang reasoning model khi độ tin cậy của mô hình nhỏ `< 0.85`, giúp tiết kiệm tới **70% điện năng reasoning**.

### 🔹 Extension 5: Lập lịch tác vụ theo dấu chân Carbon (Carbon-Aware Scheduling)
- **Giải pháp:** Phân tích 4,227 kWh/tháng điện năng tiêu thụ của các tác vụ huấn luyện gián đoạn (`interruptible=1`) trên 5 khu vực điện toán đám mây.
- **Đo lường:** 
  - Vùng `us-east-1` (Mặc định): Phát thải **1,606.3 kg CO2e** (Chi phí điện $507.24).
  - Vùng `europe-north1` (Na Uy Thủy điện - 30 gCO2/kWh): Phát thải **126.8 kg CO2e** (Chi phí điện $380.43).
  - **Kết quả:** Chuyển dịch vùng huấn luyện giúp **giảm 1,479.5 kg CO2e (giảm 92.1% phát thải)** và tiết kiệm thêm **$126.81/tháng** tiền điện.

---

## 5. TOP 3 KHUYẾN NGHỊ HÀNH ĐỘNG CHO BAN LÃNH ĐẠO NIMBUSAI

1. **Hành động 1 (Triển khai ngay — Ngày 1): Dọn sạch lãng phí hạ tầng cứng**
   - Kích hoạt Cron job tự động phát hiện và tắt các GPU Idle (< 10% clock) sau 30 phút rảnh rỗi.
   - Hạ cấp ngay lập tức instance `gpu-h100-4` từ H100 về A100.
   - *Thu hồi tức thì: $1,255 / tháng.*

2. **Hành động 2 (Triển khai trong Tuần 1): Tối ưu hóa cổng API Gateway**
   - Thiết lập Gateway đa tầng: Ưu tiên Model nhỏ làm mặc định (Cascade), bật tính năng Prompt Caching cho các System Prompt dài (>1,024 tokens), và định tuyến các tác vụ chấm điểm (Eval/RAG indexing) qua Batch API qua đêm.
   - *Thu hồi: $1,212 / tháng chi phí API suy luận (giảm 82.6% $/1M-token).*

3. **Hành động 3 (Triển khai trong Tháng 1): Cam kết Reserved & Quy hoạch Vùng xanh**
   - Ký kết cam kết 3-Year Reserved cho 3 cụm GPU phục vụ sản phẩm 24/7 (`job-infer-chat`, `job-infer-rag`, `job-infer-search`).
   - Di dời toàn bộ job Training/Fine-tuning sang trung tâm dữ liệu `europe-north1`.
   - Thiết lập cơ chế Chargeback nội bộ dựa trên xuất dữ liệu chuẩn **FOCUS 1.0** (với Tag coverage hiện tại đạt 92%).
   - *Thu hồi: $10,040 / tháng chi phí GPU và giảm 92.1% dấu chân Carbon.*

---
*Tài liệu đính kèm:*
- Báo cáo dữ liệu: `outputs/report.md`
- Biểu đồ phân tích: `outputs/savings.png`
- Dữ liệu chuẩn hóa quốc tế: `outputs/focus_export.csv`
