import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

from ..items import DwtsScraperItem

from scrapy.shell import inspect_response

import pandas as pd
import re
import janitor
from nameparser import HumanName
import numpy as np


class DwtsScoresSpider(CrawlSpider):
    name = 'dwts_scores'
    allowed_domains = ['en.wikipedia.org']
    start_urls = ['https://en.wikipedia.org/wiki/Dancing_with_the_Stars_(American_season_1)']

    rules = (
        Rule(LinkExtractor(allow=r'wiki/Dancing_with_the_Stars_\(American_season_\d+\)$'), callback='parse_item', follow=True),
#       Rule(LinkExtractor(allow=r'wiki/Dancing_with_the_Stars_\(American_season_11\)$'), callback='parse_item', follow=True),
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
            .assign(professional = lambda df_: df_.professional.str.replace(r'\(Week.*?\)', '', regex = True).str.strip(' '))
            .drop_duplicates()
            .assign(pro_name_part = lambda df_: df_.professional
                                                   .apply(self.name_parse)
                                                   .str.strip()
                                                   .replace(['Maksim'], 'Maks')
                                                   .replace(['Valentin'], 'Val')
                   ) 
        )
        
        # In one season there is both Anna Demidova ('Anna D.' and Anna Trebunskaya 'Anna T.'
        # https://en.wikipedia.org/wiki/Dancing_with_the_Stars_(American_season_9)
        if (all_pros.professional.str.contains("Anna Demidova").any()):
            # df_final['judge'] = np.where(df_final['judge'] == 'Guest judge', df_final['guest_judge'], df_final['judge'])
            all_pros.pro_name_part = np.where(all_pros.professional == "Anna Demidova", "Anna D.", all_pros.pro_name_part)
            all_pros.pro_name_part = np.where(all_pros.professional == "Anna Trebunskaya", "Anna T.", all_pros.pro_name_part)
            
        
        all_celebs = (
            cast_pandas
            .rename(columns={'notability_known_for_': 'notability'})
            .filter(['celebrity','notability'])
            .assign(
                celebrity = lambda df_: df_.celebrity.str.replace(r'---S.*?$', '', regex = True), 
                celeb_name_part = lambda df_: df_.celebrity
                                                     # .replace(['Mike "The Miz" Mizanin'], 'Miz Mizanin')
                                                     # .replace(['Bill Engvall'], 'Bill E. Engvall')
                                                     # .replace(['Bill Nye'], 'Bill N. Nye')
                                                      # removes ---Season 7 all-stars
                                                     # .str.replace(r'---S.*?$', '', regex = True) 
                                                     .apply(self.name_parse)
                                                     .str.strip()
                                                     .replace(['Brian Austin'], 'Brian')
                                                     .replace(['Miz'], 'The Miz')
                                                     .replace(['Jessie James'], 'Jessie')
                                                     .replace(['Metta World'], 'Metta')
                                                     .replace(['Apolo Anton'], 'Apolo')
                                                     .replace(['P'], 'Master P')
                                                     .replace(['Melissa Joan'], 'Melissa')
                                                     .replace(['Lil\''], 'Lil\' Kim')  
                                                     .replace(['David Alan'], 'David')
                                                     .replace(['Marissa Jaret'], 'Marissa')
                                                     .replace(['Vivica A.'], 'Vivica')
                                                     .replace(['Candace Cameron'], 'Candace')
                                                     # .replace(['D.L'], 'D.L.') # fixed on page
                                                     .replace(['The'], 'The Situation') # hope there is only one
                                                     .replace(['Vanilla'], 'Vanilla Ice')
                                                     .replace(['Jake T.'], 'Jake')
                                                     .replace(['Jennie Finch'], 'Jennie')
                                                     .replace(['Elizabeth Berkley'], 'Elizabeth')
                                                     
                   )
        )
        # Note the above can be replaced by putting all the special cases into a dict (much more natural)
        # and using .replace(to_replace = name_special_cases).
        
        if (all_celebs.celebrity.str.contains("Bill Nye").any()):
            all_celebs.celeb_name_part = np.where(all_celebs.celebrity == "Bill Nye", "Bill N.",  all_celebs.celeb_name_part)
            all_celebs.celeb_name_part = np.where(all_celebs.celebrity == "Bill Engvall", "Bill E.",  all_celebs.celeb_name_part)
        
        all_celebs.celeb_name_part = np.where(all_celebs.celebrity == 'Mike "The Miz" Mizanin', 'The Miz',  all_celebs.celeb_name_part)
        all_celebs.celeb_name_part = np.where(all_celebs.celebrity == 'Sailor Brinkley-Cook', 'Sailor',  all_celebs.celeb_name_part)
        all_celebs.celeb_name_part = np.where(all_celebs.celebrity == 'Mr. T', 'Mr. T',  all_celebs.celeb_name_part)
        
        # Note that these can likely be done with Series.where
        
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
                            judge_phrase = judge_sentence.split(': ')[-1],
                            couple = lambda df_: df_.couple.str.replace(r'\[\w\]','',regex = True),
                           )
                    .assign(couple = lambda df_: df_.couple.replace(['D.L & Cheryl'],'D.L. & Cheryl'))
                    .query('~couple.str.contains("---")') # removes multiple couple dances.  revisit this.
                    .query('~couple.isnull()')
                )
                
                # Note that the split might be better with:
                # (age ... .str.split('-', expand=True) ... .iloc[:,0] ... .astype(int)
                
                if(score_pandas.shape[0] < 1):
                    continue
                
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
                
     
                problems = with_names.query('celebrity.isnull() | professional.isnull()')
                if(problems.shape[0] > 0):
                    print(problems)
                    print(all_pros)
                    print(all_celebs)

                for row in with_names.to_dict('records'):
                      yield row 
            
            
        
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
