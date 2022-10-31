import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from ..items import DwtsScraperItem

from scrapy.shell import inspect_response

import pandas as pd
import re
import janitor
from nameparser import HumanName


class DwtsScoresSpider(CrawlSpider):
    name = 'dwts_scores'
    allowed_domains = ['en.wikipedia.org']
    start_urls = ['https://en.wikipedia.org/wiki/Dancing_with_the_Stars_(American_season_1)']

    rules = (
#        Rule(LinkExtractor(allow=r'wiki/Dancing_with_the_Stars_\(American_season_\d+\)$'), callback='parse_item', follow=True),
       Rule(LinkExtractor(allow=r'wiki/Dancing_with_the_Stars_\(American_season_22\)$'), callback='parse_item', follow=True),
    )
    
    def name_parse(self, str_name):
        h_n = HumanName(str_name)
        return (' '.join(getattr(h_n, comp) for comp in ['first', 'middle']))

    def parse_item(self, response):
        # inspect_response(response, self)
        
        # item = DwtsScraperItem()
        
        season = response.xpath('string(//*[@id="firstHeading"]/text())').re(r'(\d+)\)$')[0]
        
        # Create Cast dictionary.
        cast_section = response.xpath('//*[@id="Couples"]') 
        cast_table = cast_section.xpath('../following-sibling::table[1]')
        
        cast_pandas = ( 
            pd.read_html(cast_table.get().replace('<br>','---'))[0].fillna('') # read_html returns list of tables
              .rename(columns=lambda x: re.sub(r'\[.*?\]','',x)) # remove footnote refs from column headers.
              .clean_names()
        )
        
        # get pro lookup table.
 #       cast_pros = cast_pandas.filter(['professional_partner'])
 #       cast_pros['list_of_pros'] = cast_pros['professional_partner'].str.split('---')
        all_pros = (
            cast_pandas
            .filter(['professional_partner'])
            .assign(list_of_pros = lambda df_: df_.professional_partner.str.split('---'))
            .filter(['list_of_pros'])
            .explode(['list_of_pros'])
            .rename(columns={'list_of_pros': 'professional'})
            .assign(professional = lambda df_: df_.professional.str.replace(r'\(Week \d\)', '', regex = True).str.strip())
            .drop_duplicates()
            .assign(pro_name_part = lambda df_: df_.professional
                                                   .apply(self.name_parse)
                                                   .str.strip()
                                                   .replace(['Maksim'], 'Maks')
                                                   .replace(['Valentin'], 'Val')
                   ) 
        )
            
        print(all_pros)
        
        all_celebs = (
            cast_pandas
            .filter(['celebrity'])
            .assign(celeb_name_part = lambda df_: df_.celebrity
                                                     .apply(self.name_parse)
                                                     .str.strip()
                   )
        )
            
        print(all_celebs)
        
        weekly_scores = response.xpath('//*[@id="Weekly_scores"]')
        # print(weekly_scores.get())
        
        # Currently this gets all of the judges on the page.  Season 18 somehow has GMA as a judge?
        # Ah, it's a link somewhere in one of these judge sentences.
        # Probably need to get the first preceeding sibling matching for each table
        
       # if (default_judge_sentences := weekly_scores.xpath('../following-sibling::p[1]')):
       #     default_judge_html = default_judge_sentences[0] # gets only first judge statement
       #     judge_sentence = ''.join(default_judge_html.xpath('./descendant-or-self::*/text()').getall())
        default_judge_sentence = ''.join(weekly_scores.xpath('../following-sibling::p[1]/descendant-or-self::*/text()').getall())
        did_find_guest = False
        # print(judge_sentence)
        
        # tags = weekly_scores.xpath('../following-sibling::*')
        # for tag in tags:
        #     print(tag)
        
        # To parse this we need to iterate through the siblings; the page has a linear and not a nested structure.
        
        tags = weekly_scores.xpath('../following-sibling::*')
        for index, tag in enumerate(tags):
           # print(tag.get())
            tag_name = tag.xpath('name()').get()
            if tag_name == "h2":  # Moves out of Weekly Scores
                break
            
            elif tag_name == "h3": # new week
                week_title = tag.xpath('./span/text()').get()
           #     week = re.search(r'Week (\d+)').group(1)
           #     week_theme = week_title.split(": ")[-1]
                
            elif tag_name == "table": # new table, check for judge statement
                # reset either way so not carried over to next table
                did_find_guest = False
                
                # judge statement usually comes just before the table
                # but sometimes it can be a few p up.
                # https://en.wikipedia.org/w/index.php?title=Dancing_with_the_Stars_(American_season_11)#Week_7:_200th_Episode_Week
                # https://en.wikipedia.org/w/index.php?title=Dancing_with_the_Stars_(American_season_22)#Week_4:_Disney_Night
                # check preceeding-sibling until hit either <table> or <h3>
                
                # trouble in https://en.wikipedia.org/wiki/Dancing_with_the_Stars_(American_season_31)#Week_6:_Michael_Bubl%C3%A9_Night
                # tags[39]
                
              #  print(tag.get()) 
            
                # Look backwards in the tag list using index.  weird results with preceding-sibling
                keep_looking = True
                earlier_index = index
                while (keep_looking):
                    earlier_index -= 1
                    previous_tag = tags[earlier_index]
    
                    if previous_tag.xpath('name()').get() in ["table","h3","h2"]:
                        if not did_find_guest:
                            judge_sentence = default_judge_sentence
                        break # stop searching previous tags above table.
                        
                    elif previous_tag.xpath('name()').get() == "p":
                        p_text = ''.join(previous_tag.xpath('./descendant-or-self::*/text()').getall())
                        if re.search(r'Individual judge', p_text):
                            did_find_guest = True
                            keep_looking = False
                            judge_sentence = p_text
                        
                score_pandas = (
                    pd.read_html(tag.get().replace('<br>','---'))[0].fillna('') # read_html returns list of tables
                        # remove footnote refs from column headers.
                    .rename(columns=lambda x: re.sub(r'\[.*?\]','',x))
                    .clean_names()
                    .assign(season = season,
                            week_title = week_title,
                            judge_phrase = judge_sentence.split(': ')[-1]           
                           )
                    .query('~couple.str.contains("---")')
                )
                # print(score_pandas)
                    
#                 # score_pandas['week'] = week
#                 score_pandas['week_title'] = week_title

#                 score_pandas['judge_phrase'] = judge_sentence.split(': ')[-1]
                
#                 score_pandas[['celeb_name_part', 'pro_name_part']] = score_pandas['couple'].str.split(" & ", expand = True)            
    
    
#                 score_pandas = pd.read_html(tag.get().replace('<br>','---'))[0].fillna('') # read_html returns list of tables
#                         # remove footnote refs from column headers.
#                 score_pandas = score_pandas.rename(columns=lambda x: re.sub(r'\[.*?\]','',x))
#                 score_pandas = score_pandas.clean_names()

#                 score_pandas['season'] = season
#                 # score_pandas['week'] = week
#                 score_pandas['week_title'] = week_title

#                 score_pandas['judge_phrase'] = judge_sentence.split(': ')[-1]
               
    
                score_pandas[['celeb_name_part', 'pro_name_part']] = score_pandas['couple'].str.split(" & ", expand = True)
                # join to cast_pandas.
                
                # To handle substitutions/switch-ups etc, need to separate celebs and pros.
                # then split couple into celeb/pro names
                # then join to celebs on celeb_name_part
                # then join to pros on pro_name_part.
                # But more pros than in the pros column. Need to split that field to get them all.
                
                with_names = (
                    score_pandas
                    .merge(all_pros, how='left', on='pro_name_part')
                    .merge(all_celebs, how='left', on='celeb_name_part')
                )
                    
                print(with_names)

                # for row in with_names.to_dict('records'):
                #      yield row 
            
            
        
#         for week_tag in weekly_scores.xpath('../following-sibling::h3/span[@class="mw-headline"]'):
            
#             week = week_tag.xpath('./text()').get()
            
#             # Guest judges are just under the header, if present.
#             if (weekly_judge_candidates := week_tag.xpath("../following-sibling::p[1]/*[contains(text(), 'left to right')]")):
#                 judge_html = weekly_judge_candidates[0]
#             else:
#                 judge_html = default_judge_sentence
            
#             judge_sentence = ''.join(judge_html.xpath('./descendant-or-self::*/text()').getall())
#             score_pandas['judge_phrase'] = judge_sentence.split(':')[-1]
            
         
#             # Get score table, parse using Pandas.read_html which handles rowspan/colspan
#             score_table = week_tag.xpath('../following-sibling::table')[0]

#             score_pandas = pd.read_html(score_table.get().replace('<br>','---'))[0].fillna('') # read_html returns list of tables
#                         # remove footnote refs from column headers.
#             score_pandas = score_pandas.rename(columns=lambda x: re.sub(r'\[.*?\]','',x))
#             score_pandas = score_pandas.clean_names()
            
#             score_pandas['season'] = season
#             score_pandas['week'] = week
            
#             for row in score_pandas.to_dict('records'):
#                 yield row 
            

            
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
