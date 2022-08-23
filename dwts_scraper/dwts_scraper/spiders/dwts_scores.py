import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from ..items import DwtsScraperItem

from scrapy.shell import inspect_response

import pandas as pd
import re
import janitor


class DwtsScoresSpider(CrawlSpider):
    name = 'dwts_scores'
    allowed_domains = ['en.wikipedia.org']
    start_urls = ['https://en.wikipedia.org/wiki/Dancing_with_the_Stars_(American_season_1)']

    rules = (
        Rule(LinkExtractor(allow=r'wiki/Dancing_with_the_Stars_\(American_season_\d+\)$'), callback='parse_item', follow=True),
    )

    def parse_item(self, response):
        # inspect_response(response, self)
        
        # item = DwtsScraperItem()
        
        season = response.xpath('string(//*[@id="firstHeading"]/text())').re(r'(\d+)\)$')[0]
        
        weekly_scores = response.xpath('//*[@id="Weekly_scores"]')
        
        # Currently this gets all of the judges on the page.  Season 18 somehow has GMA as a judge?
        # Ah, it's a link somewhere in one of these judge sentences.
        # Probably need to get the first preceeding sibling matching for each table
        # default_judges = weekly_scores.xpath('../following-sibling::p/i/a/text()').getall()
        
        for week_tag in weekly_scores.xpath('../following-sibling::h3/span[@class="mw-headline"]'):
            
            week = week_tag.xpath('./text()').get()
            
            # Get score table, parse using Pandas.read_html which handles rowspan/colspan
            score_table = week_tag.xpath('../following-sibling::table')[0]

            score_pandas = pd.read_html(score_table.get())[0].fillna('') # read_html returns list of tables
                        # remove footnote refs from column headers.
            score_pandas = score_pandas.rename(columns=lambda x: re.sub(r'\[.*?\]','',x))
            score_pandas = score_pandas.clean_names()
            
            score_pandas['season'] = season
            score_pandas['week'] = week
            
#             item['score_table'] = score_pandas.to_dict('records') # records gets col = value for each row
            
            # Judges are in a sentence just above the table (or a few tables up).
            judge_html = score_table.xpath('./preceding-sibling::p//*[contains(text(), "Individual judge")]')[-1]
            # item['judge_sentence'] = ''.join(judge_html.xpath('./descendant-or-self::*/text()').getall())
            
            # 'Individual judges scores in the chart below (given in parentheses) are listed in this order 
            # from left to right: Carrie Ann Inaba, Len Goodman, Robin Roberts, Bruno Tonioli'
            # item['judges'] = [j.strip(' .') for j in item['judge_sentence'].split(":")[-1].split(", ")]
            
            judge_sentence = ''.join(judge_html.xpath('./descendant-or-self::*/text()').getall())
            score_pandas['judge_phrase'] = judge_sentence.split(':')[-1]
            # judges = [j.strip(' .') for j in judge_sentence.split(":")[-1].split(", ")]
            
            for row in score_pandas.to_dict('records'):
                yield row 
            

            
"""
Unresolved issues:
https://en.wikipedia.org/wiki/Dancing_with_the_Stars_(American_season_9)#Weekly_scores has "Dance Off" header row.  How is that handled by pandas.read_html?

Some tables have score instead of scores
e.g., https://en.wikipedia.org/wiki/Dancing_with_the_Stars_(American_season_17)#Weekly_scores week 3
https://en.wikipedia.org/wiki/Dancing_with_the_Stars_(American_season_20)#Weekly_scores Week 5.

Some tables have technical and performance scores.

https://en.wikipedia.org/wiki/Dancing_with_the_Stars_(American_season_11)#Weekly_scores  Week 4.
https://en.wikipedia.org/wiki/Dancing_with_the_Stars_(American_season_10)#Weekly_scores Week 4.

Some scores are X.  Whe
"""
