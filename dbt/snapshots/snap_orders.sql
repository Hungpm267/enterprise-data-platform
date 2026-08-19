{% snapshot snap_orders %}

{{
    config(
      target_schema='snapshots',
      unique_key='order_id',
      strategy='check',
      check_cols=['order_status', 'order_estimated_delivery_date'],
      invalidate_hard_deletes=True,
      tags=['postgres']
    )
}}

select
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp,
    order_estimated_delivery_date
from {{ ref('stg_orders') }}

{% endsnapshot %}
