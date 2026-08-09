
  
    

    create or replace table `data-engineering-504901`.`marts`.`dim_customers`
      
    
    

    
    OPTIONS()
    as (
      

SELECT
    customer_id,
    customer_city,
    customer_state
FROM `data-engineering-504901`.`staging`.`stg_customers`
    );
  