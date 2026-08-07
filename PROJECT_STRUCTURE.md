# 📂 Cấu Trúc Dự Án ELT (Extract - Load - Transform)

Tài liệu này mô tả chi tiết kiến trúc và thành phần thư mục của dự án **E-Commerce ELT Data Pipeline**.

---

## 🌳 Cây Cấu Trúc Thư Mục (Project Directory Tree)

```text
data-pipeline-airflow-api-postgres-dbt-powerbi-main/
├── README.md                           # Tổng quan dự án, hướng dẫn cài đặt và sử dụng
├── PROJECT_STRUCTURE.md                # Mô tả cấu trúc dự án chi tiết
├── requirements.txt                    # Danh sách thư viện Python (psycopg2, pandas, sqlalchemy,...)
├── .env                                # Khai báo biến môi trường & Credentials (DB Host, User, Pass, Port)
├── .gitignore                          # Cấu hình bỏ qua các file tạm/credentials khi push Git
├── docker-compose.yml                  # Cấu hình khởi chạy Apache Airflow WebUI & Scheduler bằng Docker
├── main.py                             # Script chính khởi chạy trọn vẹn luồng ELT thủ công ở Terminal
├── view_dw_tables.py                   # Script hỗ trợ xem nhanh danh sách bảng và dữ liệu trong Postgres DW
├── dags/                               # Chứa các file định nghĩa Airflow DAGs
│   └── elt_pipeline_dag.py             # Airflow DAG lập lịch điều phối chuỗi công việc Extract -> Load -> Transform
├── src/                                # Mã nguồn chính của Pipeline
│   ├── extract/                        # Trích xuất dữ liệu thô từ Nguồn (Databases, APIs, Files, Streams)
│   │   ├── __init__.py
│   │   ├── extract_api.py
│   │   ├── extract_db.py               # Rút trích 6 bảng thô từ Postgres sang Parquet
│   │   └── extract_stream.py
│   ├── load/                           # Nạp dữ liệu thô thẳng vào Data Lake / DW Staging schema
│   │   ├── __init__.py
│   │   ├── load_to_lake.py
│   │   └── load_to_dw.py               # Nạp file Parquet từ landing vào staging schema trong DW
│   ├── transform/                      # Biến đổi dữ liệu TRONG Data Warehouse (In-Warehouse Transformations)
│   │   ├── __init__.py
│   │   ├── dbt/                        # Dự án dbt (data build tool) cho SQL modeling
│   │   │   ├── dbt_project.yml
│   │   │   └── models/
│   │   │       └── staging/            # Staging SQL models
│   │   ├── sql/                        # Các câu lệnh SQL tạo bảng Fact & Dimension (marts schema)
│   │   │   ├── dim_customers.sql
│   │   │   ├── dim_products.sql
│   │   │   ├── fct_orders.sql
│   │   │   └── fct_payments.sql
│   │   └── run_transform.py            # Runner khởi chạy toàn bộ file SQL/dbt transform
│   ├── utils/                          # Công cụ hỗ trợ dùng chung
│   │   ├── __init__.py
│   │   ├── config.py                   # Đọc biến môi trường từ .env
│   │   ├── db_connector.py             # Quản lý kết nối SQLAlchemy Engine tới Postgres DW
│   │   └── logger.py                   # Custom Logger hiển thị màu sắc ANSI trực quan
│   └── pipelines/                      # Điều phối luồng làm việc
│       ├── __init__.py
│       ├── elt_pipeline.py
│       └── tasks.py
├── tests/                              # Bộ kiểm thử tự động (Unit test, Data Quality test)
│   ├── __init__.py
│   ├── test_extract.py
│   ├── test_load.py
│   └── test_transform.py
├── data/                               # Vùng lưu trữ dữ liệu tạm thời cục bộ
│   └── landing/                        # Chứa các file Parquet thô trích xuất từ nguồn trước khi nạp DW
├── notebooks/                          # Jupyter Notebooks phục vụ EDA và phân tích dữ liệu
│   ├── eda.ipynb
│   └── dw_profiling.ipynb
└── logs/                               # Lưu vết file log quá trình thực thi pipeline
```

---

## 🎯 Chi Tiết Mô Hình ELT (Extract – Load – Transform)

| Bước | Thành phần | Mô tả |
| :--- | :--- | :--- |
| **1. Extract** | `src/extract/` | Thu thập 6 bảng thô từ PostgreSQL mà **KHÔNG** làm sạch/biến đổi logic nghiệp vụ. Dữ liệu được lưu dạng tệp Parquet ở `data/landing/`. |
| **2. Load** | `src/load/` | Nạp nguyên bản các tệp Parquet vào các bảng Staging trong schema `staging` của Data Warehouse (`staging.stg_raw_*`). |
| **3. Transform** | `src/transform/` | Tận dụng sức mạnh tính toán của Data Warehouse để thực thi các tệp SQL biến đổi dữ liệu Staging thành các bảng **Fact & Dimension** trong schema `marts`. |

---

## 📝 Diễn Giải Chi Tiết Các Thành Phần Chính

### 1. File Cấu Hình & Điều Phối Gốc
- **`README.md`**: Hướng dẫn tổng quan về dự án, môi trường và cách vận hành.
- **`requirements.txt`**: Khai báo danh sách các thư viện Python chuẩn (`psycopg2-binary`, `sqlalchemy`, `pandas`, `pyarrow`, `python-dotenv`).
- **`.env`**: Quản lý biến môi trường bảo mật (Database Host, Port, Credentials).
- **`docker-compose.yml`**: Khởi chạy môi trường **Apache Airflow WebUI (port 8080)** độc lập bằng Docker.
- **`main.py`**: Điểm khởi chạy (Entry point) để kích hoạt toàn bộ 3 bước ELT liên tục bằng câu lệnh Python.
- **`view_dw_tables.py`**: Công cụ CLI tra cứu số lượng bản ghi và xem thử nội dung các bảng trong schema `staging` và `marts`.

### 2. Các Module Nguồn (`src/`)
- **`src/extract/extract_db.py`**: Trích xuất dữ liệu từ các bảng `raw_customers`, `raw_orders`, `raw_order_items`, `raw_payments`, `raw_reviews`, `raw_products`. Tự động làm sạch các file cũ để tránh trùng lặp.
- **`src/load/load_to_dw.py`**: Tạo schema `staging` và nạp toàn bộ file parquet thô vào các bảng `stg_raw_*`.
- **`src/transform/sql/`**: Chứa các file SQL biến đổi dữ liệu thành Star Schema:
  - `dim_customers.sql`: Chuẩn hóa thông tin khách hàng, thành phố, tiểu bang.
  - `dim_products.sql`: Xử lý thông tin danh mục sản phẩm.
  - `fct_orders.sql`: JOIN thông tin đơn hàng và tổng giá trị đơn/cước phí vận chuyển.
  - `fct_payments.sql`: Thống kê hình thức và giá trị thanh toán.
- **`src/utils/logger.py`**: Logger phân loại màu sắc ANSI (Cyan cho thời gian, Green cho INFO, Red cho ERROR) giúp theo dõi trong terminal dễ dàng.
- **`dags/elt_pipeline_dag.py`**: Cấu hình Airflow DAG điều phối luồng `extract_task >> load_task >> transform_task` tự động chạy lúc 02:00 AM hàng ngày.
