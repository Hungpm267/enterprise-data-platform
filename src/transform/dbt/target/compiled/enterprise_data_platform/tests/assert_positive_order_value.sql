-- Singular Test: An order should never have negative revenue or negative freight costs.
SELECT
    order_id,
    total_order_value,
    total_freight_value
FROM `data-engineering-504901`.`marts`.`fct_orders`
WHERE total_order_value < 0
   OR total_freight_value < 0