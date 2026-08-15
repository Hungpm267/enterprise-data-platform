
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select total_order_value
from `data-engineering-504901`.`marts`.`fct_orders`
where total_order_value is null



  
  
      
    ) dbt_internal_test