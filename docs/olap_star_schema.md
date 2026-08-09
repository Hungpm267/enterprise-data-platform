# 🌟 Mô Hình Dữ Liệu OLAP Star Schema (Data Marts)

Tài liệu này mô tả chi tiết sơ đồ kiến trúc **Mô hình hình Sao (Star Schema)** nằm trọn vẹn trong BigQuery dataset `marts`. 

---

## 📐 Sơ Đồ Quan Hệ Bảng OLAP (Entity-Relationship Diagram)

```mermaid
erDiagram
    dim_customers ||--o{ fct_orders : "places (1:N)"
    fct_orders ||--o{ fct_payments : "has_payments (1:N)"
    fct_orders ||--o{ fct_order_items : "contains (1:N)"
    dim_products ||--o{ fct_order_items : "purchased_in (1:N)"
    dim_customers ||--o{ fct_order_items : "bought_by (1:N)"

    dim_customers {
        string customer_id PK "Mã định danh khách hàng"
        string customer_city "Thành phố cư trú"
        string customer_state "Tỉnh/Bang cư trú"
    }

    dim_products {
        string product_id PK "Mã định danh sản phẩm"
        string product_category_name "Tên danh mục sản phẩm"
    }

    fct_orders {
        string order_id PK "Mã đơn hàng"
        string customer_id FK "Khóa ngoại trỏ về dim_customers"
        string order_status "Trạng thái đơn hàng"
        timestamp order_purchase_timestamp "Thời điểm đặt hàng"
        integer total_items "Tổng số lượng sản phẩm trong đơn"
        numeric total_order_value "Tổng giá trị đơn hàng"
        numeric total_freight_value "Tổng cước phí vận chuyển"
    }

    fct_order_items {
        string order_item_id PK "Mã chi tiết sản phẩm trong đơn"
        string order_id FK "Khóa ngoại trỏ về fct_orders"
        string product_id FK "Khóa ngoại trỏ về dim_products"
        string customer_id FK "Khóa ngoại trỏ về dim_customers"
        numeric price "Giá bán sản phẩm"
        numeric freight_value "Phí vận chuyển sản phẩm"
    }

    fct_payments {
        string payment_id PK "Mã giao dịch thanh toán"
        string order_id FK "Khóa ngoại trỏ về fct_orders"
        string payment_type "Phương thức thanh toán"
        integer payment_installments "Số kỳ trả góp"
        numeric payment_value "Số tiền thanh toán"
    }
```

---

## 🔍 Diễn Giải Các Tầng Bảng Trong Schema `marts`

### 1. Bảng Sự Kiện (Fact Tables)

- **`marts.fct_orders` (Fact Đơn hàng - Cấp Header):**
  - **Mức độ chi tiết:** 1 dòng = 1 đơn hàng (`order_id`).
  - **Dùng cho:** Đếm tổng số đơn (`COUNT`), doanh thu toàn sàn (`SUM(total_order_value)`), AOV.

- **`marts.fct_order_items` (Fact Chi tiết Mặt hàng - Cấp Item):**
  - **Mức độ chi tiết:** 1 dòng = 1 mặt hàng bán out (`order_item_id`).
  - **Dùng cho:** Phân tích doanh số theo sản phẩm (`product_id` ➔ `dim_products`), tính sản lượng bán ra.

- **`marts.fct_payments` (Fact Thanh toán):**
  - **Mức độ chi tiết:** 1 dòng = 1 giao dịch thanh toán (`payment_id`).
  - **Dùng cho:** Phân tích tỷ trọng phương thức thanh toán (`payment_type`).

---

### 2. Bảng Chiều Mô Tả (Dimension Tables)

- **`marts.dim_customers`:** Chứa vị trí địa lý khách hàng (`customer_id`, `customer_city`, `customer_state`).
- **`marts.dim_products`:** Chứa danh mục sản phẩm (`product_id`, `product_category_name`).

---

## 🚀 Ứng Dụng Nối Bảng Trên Looker Studio / Power BI

Tất cả các bảng báo cáo **CHỈ NẰM TRONG SCHEMA `marts`**:
1. **Phân tích Doanh số Sản phẩm:** Connect `wide_orders_analytics` view (hoặc blend `fct_order_items` với `dim_products` qua `product_id`).
2. **Phân tích Địa lý:** Connect `wide_orders_analytics` view (hoặc blend `fct_orders` với `dim_customers` qua `customer_id`).
3. **Phân tích Thanh toán:** Connect `wide_orders_analytics` view (hoặc blend `fct_orders` với `fct_payments` qua `order_id`).
