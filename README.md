# Dancing with the Stars Dataset

A dataset of Dancing with the Stars scraped from wikipedia tables.  Created for a Data Engineering class.

## Understanding the dataset

The database can be understood as:

> A `score` is awarded by single `judge` to a single `performance` and is out of 10. A `performance` is by a single `couple` made up of a `celebrity` and a `professional`, performing in a `primary_dance_style` set to a `primary_song` by a `primary_song_artist`. The performances take place during a `performances.week` of a particular `week_theme` which make up a `performances.season`.

Currently performances by multiple couples at the same time are dropped. This removes the complication of different kinds of judgements, including judgements in which the judges rank the couples (rather than giving scores out of 10).

In some weeks judges give two scores each to a dance (a performance score and a technical score). Those are collapsed to a single score by averaging.

Sometimes performances are medleys with multiple dance styles and multiple songs.  Currently only the first listed dance_style and song are included (hence `primary`).  

I have not tried to standardize the type of `notability` for which a star is known. This would also need to be a hierarchy but is currently just a single column `celebrities.notability`.

Celebrities are teamed with a professional for the season. That enables professionals to claim wins over time. However sometimes the celebrity dances with a different professional for some performances, causes include substitutions for illness/injury, but sometimes there is a "switch up" and all celebrities dance with the professional. Note that the `couples` table is the couple listed in the weekly scores tables on the wikipedia pages, which reflects the actual people performing in that particular dance (as does the `performances.professional` column which is derived from the couple column on the wikipedia page.). The database currently does not have the season long pairings; this could be derived from the `performances` by finding the most frequent professionals with which a `celebrity` performed.

I don't think that the `ids` are stable through runs of the `parse_scores_json_to_tables.ipynb` because they are created with `pd.factorize` which I don't think is stable.  Or perhaps it is the spidering order and thus the order in the scores.json.  Either way the ids of things like judges change when you re-generate the dataset (they are consistent within each dataset, though!).

The scraper uses cached html, which is in the repo and located in `.scrapy/httpcache`. 

The scraper produces `dwts_scrapy/scores.json` the actual scraping code is in `dwts_scraper/spiders/dwts_scores.py` and can be run with:

```sh
cd dwts_scrapy
scrapy crawl dwts_scores -O scores.json
```

There is then a parser in `parse_scores_json_to_tables.ipynb` which produces the output csv files in `dwts_dataset`.

Within the `dwts_dataset` each `csv` is a table. Primary keys are the first column (e.g., `performance_id`). Foreign keys are named with `<table_name>_id` (e.g., primary_dance_style_id).

Note that this is set up as a repo that can work with `repo2docker`.  You can run it direcltly on mybinder via this link [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/howisonlab/dwts_dataset.git/HEAD)

Or you can get it running if you have Docker by installing `repo2docker` and running it.

```sh
brew install repo2docker
git clone https://github.com/howisonlab/dwts_dataset.git
cd dwts_dataset
repo2docker --volume .:on-disk .
```

That gives you a notebook environment in which you can edit the files in the `~/on-disk` folder and those edits will persist.
