# 🚀 Automated E-Commerce ELT Data Pipeline (Prefect & Cloud Native)

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://www.postgresql.org/)
[![Prefect](https://img.shields.io/badge/Prefect-3.x%20%2F%202.x-blueviolet.svg)](https://www.prefect.io/)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-24%2F7%20Cloud-blue.svg)](https://github.com/features/actions)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An end-to-end, modern **ELT (Extract – Load – Transform)** Data Pipeline built for E-Commerce analytics orchestrated by **Prefect**. Dữ liệu được rút trích tự động từ PostgreSQL Server nguồn, lưu trữ dạng Parquet tại Landing Zone, nạp vào Data Warehouse Staging schema, và chuyển đổi thành mô hình **Star Schema (Fact & Dimension Tables)** phục vụ báo cáo Business Intelligence (Power BI, Metabase, Tableau).

---

## 📌 Table of Contents
- [Architecture Diagram](#-architecture-diagram)
- [Tech Stack](#-tech-stack)
- [Project Directory Structure](#-project-directory-structure)
- [Key Features](#-key-features)
- [Data Warehouse Schema (Star Schema)](#-data-warehouse-schema-star-schema)
- [Quick Start & Setup Guide](#-quick-start--setup-guide)
  - [1. Prerequisites](#1-prerequisites)
  - [2. Environment Configuration](#2-environment-configuration)
  - [3. Running Pipeline via Terminal](#3-running-pipeline-via-terminal)
  - [4. Running Pipeline via Prefect & Cloud Actions](#4-running-pipeline-via-prefect--cloud-actions)
  - [5. Inspecting Data Warehouse Tables](#5-inspecting-data-warehouse-tables)
- [Author & License](#-author--license)

---

![GCP Modern Data Stack Architecture Diagram](docs/architecture_diagram.png)

---

## 🛠 Tech Stack

- **Orchestration:** Prefect 3.x / Cloud, GitHub Actions (24/7 Cloud Automation)
- **Data Lake (Landing):** Google Cloud Storage (GCS Bucket `gs://ecommerce-data-lake-504901/`)
- **Data Warehouse:** Google BigQuery (`staging` and `marts` datasets)
- **Transform Engine:** `dbt-bigquery` (Star Schema Data Marts)
- **Language & Core SDKs:** Python 3.11, Pandas, PyArrow, SQLAlchemy 2.0+, google-cloud-storage, google-cloud-bigquery
- **BI & Analytics:** Google Looker Studio
- **Notifications & Alerts:** Telegram Bot Instant Notifications


---

## 🌳 Project Directory Structure

```text
.
├── README.md                           # Documentation & Setup Guide
├── PROJECT_STRUCTURE.md                # Detailed project architecture description
├── requirements.txt                    # Python dependencies (Prefect, SQLAlchemy 2.0, Pandas,...)
├── .env                                # Database credentials & environment variables
├── .gitignore                          # Git ignore configuration
├── main.py                             # Prefect @flow & @task entry point for full ELT pipeline
├── view_dw_tables.py                   # Data Warehouse CLI inspector script
├── .github/                            # GitHub Actions workflows
│   └── workflows/
│       └── elt_pipeline.yml            # 24/7 Cloud Automated Execution & Telegram Notifications
├── src/                                # Source code for ELT pipeline
│   ├── extract/                        # Data extraction modules
│   │   ├── extract_api.py
│   │   ├── extract_db.py               # Batch Postgres table extraction to Parquet
│   │   └── extract_stream.py
│   ├── load/                           # Raw data loading modules
│   │   ├── load_to_lake.py
│   │   └── load_to_dw.py               # Bulk loading Parquet files into DW staging schema
│   ├── transform/                      # In-Warehouse SQL transformation models
│   │   ├── dbt/                        # dbt project structure
│   │   ├── sql/                        # SQL Transformation scripts
│   │   │   ├── dim_customers.sql       # Customer Dimension table
│   │   │   ├── dim_products.sql        # Product Dimension table
│   │   │   ├── fct_orders.sql          # Order Fact table (aggregations & joins)
│   │   │   └── fct_payments.sql        # Payment Fact table
│   │   └── run_transform.py            # Transformation runner
│   └── utils/                          # Shared utilities
│       ├── config.py                   # Environment configuration loader
│       ├── db_connector.py             # SQLAlchemy Engine manager
│       └── logger.py                   # Custom ANSI colored logger
├── tests/                              # Automated tests (Unit & Data Quality)
├── data/                               # Local landing storage
│   └── landing/                        # Raw Parquet landing directory
├── notebooks/                          # Jupyter Notebooks for EDA & Data Profiling
└── logs/                               # Pipeline execution logs
```

---

## ✨ Key Features

- **Prefect Modern Orchestration:** Tự động theo dõi các task `@task` với cơ chế `retries` và `retry_delay_seconds` khi xảy ra sự cố mạng.
- **24/7 Cloud Execution:** Chạy tự động 45 phút / lần trên GitHub Actions hoàn toàn miễn phí.
- **Telegram Bot Notifications:** Gửi thông báo chi tiết tức thì (thẻ Xanh 🟢 / Đỏ 🔴) về điện thoại của bạn.
- **Self-Healing Data Warehouse:** Tự động tái tạo Schema `staging` và `marts` nếu dữ liệu bị xóa.

---

## 📊 Data Warehouse Schema (Star Schema)

### Schema: `staging` (Raw Loaded Data)
- `staging.stg_raw_customers`
- `staging.stg_raw_orders`
- `staging.stg_raw_order_items`
- `staging.stg_raw_payments`
- `staging.stg_raw_products`
- `staging.stg_raw_reviews`

### Schema: `marts` (Business Analytics & BI Ready)
- **`marts.dim_customers`**: Chuẩn hóa thông tin địa lý khách hàng (`customer_id`, `customer_city`, `customer_state`).
- **`marts.dim_products`**: Quản lý thông tin danh mục sản phẩm (`product_id`, `product_category_name`).
- **`marts.fct_orders`**: Tổng hợp thông tin đơn hàng, tổng doanh thu và cước vận chuyển (`order_id`, `customer_id`, `total_items`, `total_order_value`, `total_freight_value`,...).
- **`marts.fct_payments`**: Phân tích phương thức và giá trị thanh toán (`payment_id`, `order_id`, `payment_type`, `payment_value`,...).

---

## 🚀 Quick Start & Setup Guide

### 1. Prerequisites
- Python 3.10 or higher
- Access to a PostgreSQL instance

### 2. Environment Configuration
Tạo hoặc cập nhật tệp `.env` tại thư mục gốc của dự án:

```env
DB_HOST=your_postgres_host
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password
DB_SCHEMA=public

LANDING_DIR=data/landing
```

Cài đặt các thư viện Python:
```bash
pip install -r requirements.txt
```

### 3. Running Pipeline via Terminal
Kích hoạt Prefect Flow trực tiếp từ Terminal:

```bash
python main.py
```

### 4. Running Pipeline via Prefect & Cloud Actions
- Pipeline tự động được đẩy lên Cloud và thực thi định kỳ 45 phút / lần.
- Kết quả được tự động báo cáo về **Telegram Bot**.

### 5. Inspecting Data Warehouse Tables
Chạy script tra cứu số lượng bản ghi và xem thử nội dung dữ liệu trong các bảng Data Marts:

```bash
python view_dw_tables.py
```

---

## 📜 Author & License

Developed with ❤️ as a modern Data Engineering Portfolio Project.
Distributed under the **MIT License**.
