# Automated E-Commerce ELT Data Pipeline (GCP & Prefect Cloud)

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Google Cloud](https://img.shields.io/badge/GCP-BigQuery%20%26%20GCS-red.svg)](https://cloud.google.com/)
[![dbt](https://img.shields.io/badge/dbt-BigQuery-orange.svg)](https://www.getdbt.com/)
[![Prefect](https://img.shields.io/badge/Prefect-3.x%20Cloud-blueviolet.svg)](https://www.prefect.io/)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-24%2F7%20Automation-blue.svg)](https://github.com/features/actions)
[![Looker Studio](https://img.shields.io/badge/Looker%20Studio-Live%20Dashboard-yellow.svg)](https://datastudio.google.com/reporting/7d592d8e-bc9e-464f-adeb-008de9c7b35f)

An end-to-end, production-ready Cloud-Native **ELT (Extract – Load – Transform)** Data Pipeline built for E-Commerce analytics. Data is extracted from a PostgreSQL database, stored as compressed columnar Parquet files in Google Cloud Storage (GCS), loaded into BigQuery Staging, and modeled into an **OLAP Star Schema and One Big Table (OBT) Analytics View** using `dbt-bigquery` for business intelligence on **Google Looker Studio**. Orchestrated with Prefect Cloud and automated 24/7 on GitHub Actions with real-time Telegram alerts.

---

## Architecture Diagram

![GCP Modern Data Stack Architecture Diagram](docs/architecture_diagram.png)

---

## Tech Stack

- **Orchestration:** Prefect Cloud, GitHub Actions (24/7 Cloud Automation)
- **Data Lake (Landing Zone):** Google Cloud Storage
- **Data Warehouse:** Google BigQuery (staging and marts datasets)
- **Transform Engine:** dbt-bigquery (Star Schema & OBT Analytics View)
- **BI & Analytics:** Google Looker Studio
- **Notifications & Alerts:** Telegram Bot Instant Notifications

---

## Interactive Looker Studio Dashboard

The project includes an executive performance dashboard on Google Looker Studio connected directly to BigQuery View `marts.wide_orders_analytics`:

![Looker Studio E-Commerce Executive Dashboard](docs/looker_dashboard.png)

- **Live Interactive Dashboard:** [View on Looker Studio](https://datastudio.google.com/reporting/7d592d8e-bc9e-464f-adeb-008de9c7b35f)
- **Key Performance Indicators:** Total Revenue, Total Orders, Average Order Value (AOV), Total Freight Value.
- **Analytics Visualizations:** Revenue trend over time, Regional sales distribution by city/state, Top 5 best-selling product categories, Order status and payment breakdown.

---

## Data Warehouse Schema (OLAP Star Schema)

The dimensional data warehouse model is structured into `staging` and `marts` datasets in Google BigQuery, with transformations managed by `dbt-bigquery`:

```mermaid
erDiagram
    dim_customers ||--o{ fct_orders : "places (1:N)"
    fct_orders ||--o{ fct_payments : "has_payments (1:N)"
    fct_orders ||--o{ fct_order_items : "contains (1:N)"
    dim_products ||--o{ fct_order_items : "purchased_in (1:N)"
    dim_customers ||--o{ fct_order_items : "bought_by (1:N)"

    dim_customers {
        string customer_id PK
        string customer_city
        string customer_state
    }

    dim_products {
        string product_id PK
        string product_category_name
    }

    fct_orders {
        string order_id PK
        string customer_id FK
        string order_status
        timestamp order_purchase_timestamp
        integer total_items
        numeric total_order_value
        numeric total_freight_value
    }

    fct_order_items {
        string order_item_id PK
        string order_id FK
        string product_id FK
        string customer_id FK
        numeric price
        numeric freight_value
    }

    fct_payments {
        string payment_id PK
        string order_id FK
        string payment_type
        integer payment_installments
        numeric payment_value
    }
```

### Data Marts Models:
- **`marts.dim_customers`**: Customer geographic profile (`customer_id`, `customer_city`, `customer_state`).
- **`marts.dim_products`**: Product catalog information (`product_id`, `product_category_name`).
- **`marts.fct_orders`**: Order-level aggregations (`order_id`, `customer_id`, `total_items`, `total_order_value`, `total_freight_value`).
- **`marts.fct_order_items`**: Line-item granularity fact table (`order_item_id`, `order_id`, `product_id`, `price`, `freight_value`).
- **`marts.fct_payments`**: Payment transaction methods and values (`payment_id`, `order_id`, `payment_type`, `payment_value`).
- **`marts.wide_orders_analytics`**: Pre-joined One Big Table (OBT) View for direct BI consumption without manual table blending.

---

## Key Features

- **Modern Orchestration:** Prefect 3.x with automated retry policies, task dependency tracking (`wait_for`), and cloud logging.
- **24/7 Cloud Execution:** Automated scheduled pipeline execution on GitHub Actions cloud runners.
- **Real-Time Alerting:** Instant Telegram Bot notifications on pipeline execution status with run metrics.
- **Zero-Blending BI Experience:** BigQuery View `wide_orders_analytics` enables instant drag-and-drop analytics in Looker Studio without complex multi-table joins.