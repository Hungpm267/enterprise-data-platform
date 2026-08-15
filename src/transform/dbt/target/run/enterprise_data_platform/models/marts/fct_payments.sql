
  
    

    create or replace table `data-engineering-504901`.`marts`.`fct_payments`
      
    
    

    
    OPTIONS()
    as (
      

SELECT
    payment_id,
    order_id,
    payment_type,
    payment_installments,
    payment_value
FROM `data-engineering-504901`.`staging`.`stg_payments`
    );
  