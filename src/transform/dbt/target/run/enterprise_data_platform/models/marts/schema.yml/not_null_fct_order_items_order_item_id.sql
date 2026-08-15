
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select order_item_id
from `data-engineering-504901`.`marts`.`fct_order_items`
where order_item_id is null



  
  
      
    ) dbt_internal_test