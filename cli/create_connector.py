#!/usr/bin/env python
import os
import sys
import argparse

def create_connector(name: str):
    slug = name.lower().strip().replace("-", "_").replace(" ", "_")
    camel_name = "".join(word.capitalize() for word in slug.split("_")) + "Connector"
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dir = os.path.join(base_dir, "connectors", slug)
    staging_dbt_dir = os.path.join(base_dir, "dbt", "models", "staging", slug)

    if os.path.exists(target_dir):
        print(f"Error: Connector '{slug}' already exists at {target_dir}")
        sys.exit(1)

    os.makedirs(target_dir, exist_ok=True)
    os.makedirs(staging_dbt_dir, exist_ok=True)

    # 1. extract.py with parameterized queries
    extract_code = f"""from typing import List, Optional, Dict, Any
from sqlalchemy import text
from connectors._base.schemas import RunArgs
from src.utils.logger import logger

def extract_{slug}_data(args: RunArgs) -> List[str]:
    \"\"\"
    Secure extraction logic for {slug} connector using parameterized queries / API params.
    \"\"\"
    logger.info(f"Extracting data for connector '{slug}' with mode: {{args.mode}}")
    params: Dict[str, Any] = {{}}
    if args.start_date:
        params["start_date"] = args.start_date
    if args.end_date:
        params["end_date"] = args.end_date
    
    # TODO: Implement API requests or DB parameterized queries and save Parquet files to landing zone.
    extracted_files = []
    return extracted_files
"""

    # 2. connector.py
    connector_code = f"""from typing import List
from connectors._base.base_connector import BaseConnector
from connectors._base.schemas import RunArgs
from connectors.{slug}.extract import extract_{slug}_data

class {camel_name}(BaseConnector):
    \"\"\"
    Data Connector for {slug}.
    \"\"\"
    def __init__(self):
        super().__init__(name="{slug}")

    def extract(self, args: RunArgs) -> List[str]:
        return extract_{slug}_data(args)
"""

    # 3. __init__.py
    init_code = f"""from connectors.{slug}.connector import {camel_name}

__all__ = ["{camel_name}"]
"""

    # 4. README.md
    readme_code = f"""# {camel_name}

Data connector for `{slug}`.
- Mode: INCREMENTAL / FULL_REFRESH
- Staging models: `dbt/models/staging/{slug}/`
"""

    # 5. dbt staging sources.yml
    sources_dbt_code = f"""version: 2

sources:
  - name: {slug}
    schema: staging
    tables:
      - name: stg_raw_{slug}
        description: "Raw staging table for {slug} data lake ingestion"
"""

    with open(os.path.join(target_dir, "extract.py"), "w", encoding="utf-8") as f:
        f.write(extract_code)
    with open(os.path.join(target_dir, "connector.py"), "w", encoding="utf-8") as f:
        f.write(connector_code)
    with open(os.path.join(target_dir, "__init__.py"), "w", encoding="utf-8") as f:
        f.write(init_code)
    with open(os.path.join(target_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_code)

    with open(os.path.join(staging_dbt_dir, "sources.yml"), "w", encoding="utf-8") as f:
        f.write(sources_dbt_code)

    print(f"\n========================================================")
    print(f" Successfully created connector: '{slug}'")
    print(f" Class Name: {camel_name}")
    print(f" Connector path: connectors/{slug}/")
    print(f" dbt staging path: dbt/models/staging/{slug}/")
    print(f"========================================================")
    print(f"To run this connector:")
    print(f"  python main.py --connector {slug}")
    print(f"========================================================\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scaffold a new data connector for Enterprise Data Platform")
    parser.add_argument("--name", type=str, required=True, help="Name of the new connector (e.g. facebook_ads, shopify)")
    args = parser.parse_args()
    create_connector(args.name)