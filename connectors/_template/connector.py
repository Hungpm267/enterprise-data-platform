from typing import List
from connectors._base.base_connector import BaseConnector
from connectors._base.schemas import RunArgs
from connectors._template.extract import extract_template_source

class TemplateConnector(BaseConnector):
    """
    Boilerplate template for creating a new platform connector.
    """
    def __init__(self):
        super().__init__(name="template_connector")

    def extract(self, args: RunArgs) -> List[str]:
        return extract_template_source(args)