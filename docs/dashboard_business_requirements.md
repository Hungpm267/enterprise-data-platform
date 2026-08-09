# 📊 Business Requirement Document (BRD) — Looker Studio Dashboard

Tài liệu này quy định đầy đủ các **Yêu cầu Nghiệp vụ (Business Requirements)** và **Thiết kế Báo cáo (Dashboard Layout)** để xây dựng trang Dashboard phân tích kinh doanh **E-Commerce Executive Performance** trên **Looker Studio** kết nối trực tiếp với BigQuery Data Marts.

---

## 🎯 1. Mục Tiêu Nghiệp Vụ & Đối Tượng Sử Dụng

- **Mục tiêu:** Cung cấp cho Ban Giám Đốc và Bộ phận Kinh doanh góc nhìn toàn cảnh về Tình hình tăng trưởng doanh số, Xu hướng đơn hàng, Hành vi thanh toán và Phân bố thị trường theo địa lý.
- **Đối tượng sử dụng:** CEO, Head of Sales, E-Commerce Operations Manager, Marketing Leads.

---

## 📌 2. Danh Sách Chỉ Số KPI Trọng Yếu (KPI Cards / Scorecards)
*Vị trí: Đặt ở thanh trên cùng (Header) của Dashboard.*

| Chỉ số KPI | Tên hiển thị | Công thức tính | Bảng nguồn BigQuery |
| :--- | :--- | :--- | :--- |
| **Total Revenue** | Tổng Doanh Thu | `SUM(total_order_value)` | `marts.fct_orders` |
| **Total Orders** | Tổng Số Đơn Hàng | `COUNT(DISTINCT order_id)` | `marts.fct_orders` |
| **Average Order Value (AOV)** | Giá Trị Trung Bình / Đơn | `Total Revenue / Total Orders` | `marts.fct_orders` |
| **Total Freight Value** | Tổng Phí Vận Chuyển | `SUM(total_freight_value)` | `marts.fct_orders` |

---

## 📈 3. Yêu Cầu Các Biểu Đồ Phân Tích (Charts & Visualizations)

### 📈 Biểu đồ 1: Xu Hướng Doanh Thu & Đơn Hàng Theo Thời Gian (Line / Combo Chart)
- **Mục đích:** Theo dõi nhịp độ tăng trưởng doanh số theo ngày/tháng và phát hiện các chu kỳ mua sắm đỉnh điểm.
- **Bảng nguồn:** `marts.fct_orders`
- **Trục X (Dimension):** `order_purchase_timestamp` (Định dạng: `Year Month` hoặc `Date`).
- **Trục Y (Metrics):**
  - Cột chính (Line): `total_order_value` (Doanh thu).
  - Cột phụ (Bar/Line): `order_id` (Số lượng đơn).

### 🗺️ Biểu đồ 2: Phân Bố Doanh Số Theo Tỉnh / Thành Phố (Geo Map / Bar Chart)
- **Mục đích:** Xác định khu vực địa lý mang lại nguồn thu lớn nhất để tối ưu hóa chiến lược Marketing & Kho vận.
- **Bảng nguồn:** Join `marts.fct_orders` ➔ `marts.dim_customers` qua `customer_id`.
- **Dimension:** `customer_state` (hoặc `customer_city`).
- **Metric:** `total_order_value` (Sắp xếp giảm dần).

### 💳 Biểu đồ 3: Cơ Cấu Phương Thức Thanh Toán (Donut Chart)
- **Mục đích:** Đánh giá thị hiếu thanh toán của khách hàng (Thẻ tín dụng, Boleto, Trả góp,...).
- **Bảng nguồn:** `marts.fct_payments`
- **Dimension:** `payment_type`.
- **Metric:** `payment_value` (Phần trăm tổng giá trị).

### 📦 Biểu đồ 4: Top 5 Danh Mục Sản Phẩm Bán Chạy Nhất (Horizontal Bar Chart)
- **Mục đích:** Xác định các dòng sản phẩm đóng góp doanh số chủ lực.
- **Bảng nguồn:** Join `marts.fct_orders` ➔ `marts.dim_products` qua `product_id`.
- **Dimension:** `product_category_name`.
- **Metric:** `total_items` (Số lượng bán out) hoặc `total_order_value`.

---

## 🎛️ 4. Bộ Lọc Tương Tác (Control Filters)
*Vị trí: Đặt ở góc trên bên phải trang báo cáo.*

1. **Date Range Filter:** Lọc khoảng thời gian theo `order_purchase_timestamp` (Mặc định: 30 ngày gần nhất hoặc All Time).
2. **State Dropdown Filter:** Lọc theo khu vực `customer_state` từ `dim_customers`.
3. **Payment Type Filter:** Lọc theo loại hình `payment_type` từ `fct_payments`.

---

## 🛠️ 5. Hướng Dẫn Kết Nối Looker Studio Với BigQuery Data Marts

1. Truy cập **[Looker Studio](https://lookerstudio.google.com/)** ➔ Nhấn **Blank Report**.
2. Chọn **BigQuery** làm Data Source ➔ Chọn GCP Project `data-engineering-504901` ➔ Dataset `marts`.
3. Lần lượt kết nối các bảng:
   - `fct_orders`
   - `dim_customers`
   - `fct_payments`
   - `dim_products`
4. Thực hiện blend data hoặc thiết lập mối quan hệ theo sơ đồ ERD tại [olap_star_schema.md](olap_star_schema.md).
