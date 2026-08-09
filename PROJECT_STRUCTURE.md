# 📂 Cấu Trúc Dự Án GCP Modern Data Stack ELT Pipeline

Tài liệu này mô tả chi tiết kiến trúc và thành phần thư mục của dự án **E-Commerce GCP ELT Data Pipeline**.

---

## 🌳 Cây Cấu Trúc Thư Mục (Project Directory Tree)

```text
ecommerce-data-pipeline/
├── README.md                           # Tổng quan dự án, hướng dẫn cài đặt và sử dụng
├── PROJECT_STRUCTURE.md                # Mô tả cấu trúc dự án chi tiết
├── requirements.txt                    # Danh sách thư viện Python (Prefect, dbt-bigquery, GCP SDKs,...)
├── .env                                # Biến môi trường & cấu hình GCP / Postgres
├── .gitignore                          # Cấu hình bỏ qua các file tạm / credentials khi push Git
├── main.py                             # Prefect @flow & @task entry point điều phối toàn bộ ELT pipeline
├── prefect.yaml                        # Cấu hình Prefect Cloud deployment
├── .github/                            # GitHub Actions workflows
│   └── workflows/
│       └── elt_pipeline.yml            # Tự động hóa 24/7 (1h15m/lần) & Báo cáo Telegram Bot
├── docs/                               # Tài liệu & Sơ đồ kiến trúc dự án
│   └── architecture_diagram.png        # Sơ đồ kiến trúc 3D Modern Data Stack
├── src/                                # Mã nguồn chính của Pipeline
│   ├── extract/                        # Trích xuất dữ liệu thô từ Postgres
│   │   ├── __init__.py
│   │   └── extract_db.py               # Rút trích 6 bảng thô từ Postgres sang Parquet
│   ├── load/                           # Nạp dữ liệu thô lên GCS Data Lake & BigQuery Staging
│   │   ├── __init__.py
│   │   ├── load_to_gcs.py              # Đẩy file Parquet lên GCS Bucket (gs://ecommerce-data-lake-504901/)
│   │   └── load_to_bigquery.py         # Nạp bulk Parquet từ GCS vào BigQuery dataset `staging`
│   ├── transform/                      # Biến đổi dữ liệu trong BigQuery DW bằng dbt
│   │   ├── __init__.py
│   │   ├── dbt/                        # Dự án dbt-bigquery cho Data Modeling
│   │   │   ├── dbt_project.yml
│   │   │   ├── profiles.yml
│   │   │   ├── macros/
│   │   │   │   └── generate_schema_name.sql
│   │   │   └── models/
│   │   │       ├── staging/            # Staging SQL models (stg_*)
│   │   │       └── marts/              # Star Schema Data Marts (dim_*, fct_*)
│   │   └── run_transform.py            # Runner kích hoạt dbt-bigquery transformations
│   └── utils/                          # Công cụ hỗ trợ dùng chung
│       ├── __init__.py
│       ├── config.py                   # Đọc biến môi trường từ .env
│       ├── gcp_client.py               # Quản lý kết nối GCS Storage & BigQuery Client
│       ├── db_connector.py             # Quản lý kết nối SQLAlchemy Engine tới Postgres
│       └── logger.py                   # Custom Logger hiển thị màu sắc ANSI trực quan
├── tests/                              # Bộ kiểm thử tự động
├── notebooks/                          # Jupyter Notebooks phục vụ EDA và phân tích dữ liệu
└── logs/                               # Lưu vết file log quá trình thực thi pipeline
```

---

## 🎯 Chi Tiết Mô Hình GCP ELT (Extract – Load – Transform)

| Bước | Thành phần | Mô tả |
| :--- | :--- | :--- |
| **1. Extract** | `src/extract/` | Thu thập 6 bảng thô từ PostgreSQL Aiven Cloud ➔ Đóng gói tệp Parquet nén siêu nhẹ ở `data/landing/`. |
| **2A. Load GCS** | `src/load/load_to_gcs.py` | Đẩy 6 tệp Parquet từ Landing Zone lên **Google Cloud Storage (GCS Bucket)**: `gs://ecommerce-data-lake-504901/landing/`. |
| **2B. Load BigQuery** | `src/load/load_to_bigquery.py` | Nạp nguyên bản các tệp Parquet từ GCS vào BigQuery Dataset **`staging`** (`stg_raw_*`). |
| **3. Transform (dbt)** | `src/transform/` | Công cụ **`dbt-bigquery`** làm sạch, join và xây dựng mô hình **Star Schema (Fact & Dim)** trực tiếp trong BigQuery Dataset **`marts`**. |
