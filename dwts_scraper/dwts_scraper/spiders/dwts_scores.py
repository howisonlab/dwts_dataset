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
        
        if (default_judge_sentences := weekly_scores.xpath('../following-sibling::p[1]')):
            default_judge_sentence = default_judge_sentences[0] # gets only first judge statement
           
        
        for week_tag in weekly_scores.xpath('../following-sibling::h3/span[@class="mw-headline"]'):
            
            week = week_tag.xpath('./text()').get()
            
            # Guest judges are just under the header, if present.
            if (weekly_judge_candidates := week_tag.xpath("../following-sibling::p[1]/*[contains(text(), 'left to right')]")):
                judge_html = weekly_judge_candidates[0]
            else:
                judge_html = default_judge_sentence
            
            judge_sentence = ''.join(judge_html.xpath('./descendant-or-self::*/text()').getall())
            score_pandas['judge_phrase'] = judge_sentence.split(':')[-1]
            
         
            # Get score table, parse using Pandas.read_html which handles rowspan/colspan
            score_table = week_tag.xpath('../following-sibling::table')[0]

            score_pandas = pd.read_html(score_table.get().replace('<br>','---'))[0].fillna('') # read_html returns list of tables
                        # remove footnote refs from column headers.
            score_pandas = score_pandas.rename(columns=lambda x: re.sub(r'\[.*?\]','',x))
            score_pandas = score_pandas.clean_names()
            
            score_pandas['season'] = season
            score_pandas['week'] = week
            
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
