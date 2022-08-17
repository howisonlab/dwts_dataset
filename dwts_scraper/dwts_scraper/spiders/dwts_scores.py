import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from scrapy.shell import inspect_response

import pandas as pd


class DwtsScoresSpider(CrawlSpider):
    name = 'dwts_scores'
    allowed_domains = ['en.wikipedia.org']
    start_urls = ['https://en.wikipedia.org/wiki/Dancing_with_the_Stars_(American_season_1)']

    rules = (
        Rule(LinkExtractor(allow='wiki/Dancing_with_the_Stars_\\(American_season_\\d+\\)$'), callback='parse_item', follow=True),
    )

    def parse_item(self, response):
       # inspect_response(response, self)
        
        season = response.xpath('string(//*[@id="firstHeading"]/text())').re(r'(\d+)\)$')[0]
        
        judge_block = response.xpath('//*[@id="Weekly_scores"]')
        judges = judge_block.xpath('../following-sibling::p/i/a/text()').getall()
        
        for week_tag in judge_block.xpath('../following-sibling::h3/span[@class="mw-headline"]'):
            
            week = week_tag.xpath('./text()').get()
            
            score_table = week_tag.xpath('../following-sibling::table')[0].get()
            score_pandas = pd.read_html(score_table)[0]
            
            yield{
                'season': season,
                'week': week,
                'judges': judges,
                'score_table': score_pandas.to_dict('records')
            }
            
