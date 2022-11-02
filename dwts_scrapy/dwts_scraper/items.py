# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class DwtsScraperItem(scrapy.Item):
    # define the fields for your item here like:
    week = scrapy.Field()
    season = scrapy.Field()
    judge_sentence = scrapy.Field()
    judges = scrapy.Field()
    score_table = scrapy.Field()
    
    