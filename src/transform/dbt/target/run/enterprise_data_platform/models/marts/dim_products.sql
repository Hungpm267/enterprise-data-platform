
  
    

    create or replace table `data-engineering-504901`.`marts`.`dim_products`
      
    
    

    
    OPTIONS()
    as (
      

SELECT
    product_id,
    product_category_name
FROM `data-engineering-504901`.`staging`.`stg_products`
    );
  