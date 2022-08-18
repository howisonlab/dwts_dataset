# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem


class DwtsScraperPipeline:
    def process_item(self, item, spider):
        return item

class ValidatePipeline:

    vat_factor = 1.15

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        if adapter.get('judges'):
            return item
        else:
            raise DropItem(f"Missing judges in {item}")
