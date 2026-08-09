# 📖 Hướng Dẫn Đọc Source Code Dự Án GCP Modern Data Stack

Tài liệu này giúp bạn làm chủ mã nguồn của dự án một cách nhanh chóng và hiệu quả nhất theo tư duy của một **Data Architect / Senior Data Engineer**. Bạn không cần đọc từng dòng code phụ trợ, mà chỉ cần tập trung vào **5 tệp lõi** dưới đây.

---

## 🎯 Tư Duy Đọc Code (Data Engineering Mindset)

Khi xem mã nguồn của một Data Pipeline, bạn nên đọc theo **luồng di chuyển của dữ liệu** thay vì đọc theo thứ tự bảng chữ cái:
1. **Nguồn dữ liệu (Source)** ➔ 2. **Rút trích (Extract)** ➔ 3. **Lưu trữ Data Lake (GCS)** ➔ 4. **Kho dữ liệu Staging (BigQuery)** ➔ 5. **Biến đổi Data Marts (dbt)** ➔ 6. **Điều phối (Prefect Flow)**.

---

## 🔝 5 Tệp Lõi Cần Tập Trung Đọc

### 1. `main.py` — Xương Sống Điều Phối (Orchestration Spine)
- **Vị trí:** [main.py](file:///c:/Users/hungm/OneDrive/M%C3%A1y%20t%C3%ADnh/data-pipeline-airflow-api-postgres-dbt-powerbi-main/main.py)
- **Điểm cần tập trung:**
  - Cấu trúc trang trí `@task(retries=2, retry_delay_seconds=10)` định nghĩa tính năng tự động thử lại khi mất mạng.
  - Cấu trúc `@flow(name="E-Commerce ELT Pipeline")`: Xem cách tham số `wait_for=[...]` thiết lập thứ tự thực thi nghiêm ngặt:
    ```python
    extracted_files = extract_step_task()
    gcs_uris = load_gcs_step_task(wait_for=[extracted_files])
    loaded_tables = load_bigquery_step_task(wait_for=[gcs_uris])
    transform_step_task(wait_for=[loaded_tables])
    ```
  - Khối `if __name__ == "__main__":`: Xem cơ chế `.serve(name="ecommerce-deployment")` cho phép lắng nghe trực tiếp từ Prefect Cloud.

---

### 2. `src/utils/gcp_client.py` — Động Cơ Xác Thực Đám Mây (GCP Auth Engine)
- **Vị trí:** [src/utils/gcp_client.py](file:///c:/Users/hungm/OneDrive/M%C3%A1y%20t%C3%ADnh/data-pipeline-airflow-api-postgres-dbt-powerbi-main/src/utils/gcp_client.py)
- **Điểm cần tập trung:**
  - Cơ chế **Dual Authentication** (Xác thực kép): Ưu tiên đọc chuỗi Secret `GCP_SA_KEY` từ biến môi trường (khi chạy trên GitHub Cloud), nếu không thấy thì tự chuyển sang đọc tệp cục bộ `gcp_key.json` (khi chạy dưới máy nhà).
  - Hai hàm khởi tạo Client: `get_storage_client()` và `get_bigquery_client()`.

---

### 3. `src/load/load_to_gcs.py` — Nạp Dữ Liệu Vào Data Lake (GCS Loader)
- **Vị trí:** [src/load/load_to_gcs.py](file:///c:/Users/hungm/OneDrive/M%C3%A1y%20t%C3%ADnh/data-pipeline-airflow-api-postgres-dbt-powerbi-main/src/load/load_to_gcs.py)
- **Điểm cần tập trung:**
  - Hàm `client.bucket(bucket_name)` và `blob.upload_from_filename(file_path)`: Cách đẩy các tệp nén cột `.parquet` từ thư mục cục bộ `data/landing/` lên Cloud Storage `gs://ecommerce-data-lake-504901/landing/`.

---

### 4. `src/load/load_to_bigquery.py` — Nạp Nén Bulk Vào Data Warehouse (BigQuery Staging Loader)
- **Vị trí:** [src/load/load_to_bigquery.py](file:///c:/Users/hungm/OneDrive/M%C3%A1y%20t%C3%ADnh/data-pipeline-airflow-api-postgres-dbt-powerbi-main/src/load/load_to_bigquery.py)
- **Điểm cần tập trung:**
  - Cấu hình nạp dữ liệu:
    ```python
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    ```
  - Chế độ `WRITE_TRUNCATE`: Đảm bảo tính nhất quán (Idempotency) bằng cách xóa và nạp lại toàn bộ bảng thô `staging.stg_raw_*` mỗi lần chạy.

---

### 5. `src/transform/dbt/models/marts/fct_orders.sql` — Mô Hình Hóa Bảng Fact (Star Schema Modeling)
- **Vị trí:** [src/transform/dbt/models/marts/fct_orders.sql](file:///c:/Users/hungm/OneDrive/M%C3%A1y%20t%C3%ADnh/data-pipeline-airflow-api-postgres-dbt-powerbi-main/src/transform/dbt/models/marts/fct_orders.sql)
- **Điểm cần tập trung:**
  - Kỹ thuật CTE (`WITH orders AS (...), items AS (...)`): Tách nhỏ truy vấn để tối ưu hóa hiệu năng tính toán của BigQuery.
  - Hàm `ref('stg_orders')`: Cơ chế gọi bảng ảo Staging độc đáo của `dbt` giúp tự động xây dựng cây phụ thuộc dữ liệu (DAG Lineage).
  - Phép tính `COUNT(order_item_id)` and `SUM(price)`: Gom nhóm theo đơn hàng và tính tổng giá trị đơn hàng cũng như cước phí vận chuyển.

---

## 💡 Các Tệp Phụ Trợ (Có Thể Đọc Nhanh Hoặc Bỏ Qua)
- `src/utils/logger.py`: Tạo log hiển thị màu sắc trên Terminal (Không cần đọc chi tiết).
- `src/utils/config.py`: Đọc biến `.env` (Không cần đọc chi tiết).
- `src/transform/run_transform.py`: Gọi lệnh `dbt run` từ Python bằng `subprocess` (Đã xử lý chạy tương thích trên Windows & Linux).
