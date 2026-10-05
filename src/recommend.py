import pandas as pd
from pathlib import Path
import re, argparse
import warnings
from utils import clear_file_os, load_config
from logger import setup_logging
import logging
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

setup_logging()
logger = logging.getLogger(__name__)

def added_process(added_data_path_list:list, 
                  needed_keywords_in_title:str,
                  delete_words_in_title:str,
                  delete_words_in_company: str,):
      logger.info("---Integrate increasal data and data processing---")
      added = pd.DataFrame()
      for address in added_data_path_list:
            tmp = pd.read_csv(address)
            # for col in tmp.columns.tolist():
            for col in ['company','title','posted_date']:
                  tmp[col] = tmp[col].apply(lambda x:str(x).lower())
            # add drop-duplicates in single platform
            tmp = tmp.drop_duplicates(subset=['company','title'],keep='first').reset_index(drop=True)
            added = pd.concat([added,tmp], axis=0)

      # drop-duplicates in cross platform
      added = added.drop_duplicates(subset = ['company','title'],keep='first').reset_index(drop=True)

      # start data filtering for keyword name of jobs
      key_words = [x.lower() for x in needed_keywords_in_title.split(',')]
      escaped_words1 = [re.escape(word) for word in key_words]
      pattern1 = '|'.join(escaped_words1)
      added = added[added['title'].str.contains(pattern1, na=False)]

      # delete jobs which including below words that not suitable to apply
      delete_words_in_title = [x.lower() for x in delete_words_in_title.split(',')]
      escaped_words2 = [re.escape(word) for word in delete_words_in_title]
      pattern2 = '|'.join(escaped_words2)
      added = added[~added['title'].str.contains(pattern2, na=False)]

      delete_words_in_company = [x.lower() for x in delete_words_in_company.split(',')]
      escaped_words3 = [re.escape(word) for word in delete_words_in_company]
      pattern3 = '|'.join(escaped_words3)
      added = added[~added['company'].str.contains(pattern3, na=False)]
          
      logger.info("✅Final Data Shape is: %s", added.shape)

      return added


def get_features(new_df:pd.DataFrame)->pd.DataFrame:
      logger.info("---Start basic feature engineering---")
      # update on 2026/10/4, some posted date is empty, then fill with default value
      new_df.loc[(new_df['posted_date'].isnull())|(new_df['posted_date']=='nan'), 'posted_date'] = 'posted 1 day ago'

      new_df['posted_date'] = new_df['posted_date'].apply(lambda x:str(x).replace('posted','').strip())

      new_df['unit'] = new_df['posted_date'].apply(lambda x:x.split()[0])

      # reduce the posted date granularity for recommendation: posted less 24 hours-> 1 day
      new_df['period'] = new_df['posted_date'].apply(lambda x:x.split()[1])
      new_df['new_period'] = new_df['period']
      new_df.loc[new_df['period'].isin(['hours','hour', 'minutes', 'minute']), 'new_period'] = 'day'
      new_df['new_unit'] = new_df['unit']
      new_df.loc[new_df['period'].isin(['hours','hour', 'minutes', 'minute']), 'new_unit'] = '1'

      piority_mapping = {'minute':0, 'minutes':1, 'hour':2, 'hours':3, 'day':4 , 'days':5, 'week':6, 'weeks':7}
      new_df['priority'] = new_df['period'].map(piority_mapping)

      new_df['priority'] = pd.to_numeric(new_df['priority'])
      new_df['unit'] = pd.to_numeric(new_df['unit'])

      return new_df

def add_yesterday_to_main_table(job_alert_path:Path, 
                                recommendation_path: Path, 
                                all_today_new_open_jobs: Path, 
                                main_table_path: Path,
                                recent_week_review_path: Path)->pd.DataFrame:
      logger.info("---Integrate yesterday's application data into main table---")
      
      # append result-0 into primary_table
      job_alert_tmp = pd.read_csv(job_alert_path)
      job_alert_tmp_filter = job_alert_tmp[job_alert_tmp['recommend'].isin(['1',1,1.0,'1.0'])]
      if len(job_alert_tmp_filter)>0:
            job_alert_tmp_filter.to_csv(main_table_path, mode='a', 
                                          header=False, 
                                          index=False, encoding = 'utf-8-sig')

      # append result-1 into primary_table
      recommendation_tmp = pd.read_csv(recommendation_path)
      recommendation_tmp_filter = recommendation_tmp[recommendation_tmp['recommend'].isin(['1',1,1.0,'1.0'])]
      if len(recommendation_tmp_filter)>0:
            recommendation_tmp_filter.to_csv(main_table_path, mode='a', 
                                      header=False, 
                                      index=False, encoding = 'utf-8-sig')

      # append result-2 into primary_table
      all_dt_tmp = pd.read_csv(all_today_new_open_jobs)
      all_dt_tmp_filter = all_dt_tmp[all_dt_tmp['recommend'].isin(['1',1,1.0,'1.0'])]
      if len(all_dt_tmp_filter)>0:
            all_dt_tmp_filter.to_csv(main_table_path, mode='a', 
                                    header=False, 
                                    index=False, encoding = 'utf-8-sig')

      # this table used to store recent two weeks reviewed jobs
      recent_week_review = pd.read_csv(recent_week_review_path)
      recent_week_review['scrape_date'] = pd.to_datetime(recent_week_review['scrape_date'])
      recent_date = pd.Timestamp.today().normalize()-pd.Timedelta(days=14)
      recent_week_review = recent_week_review[recent_week_review['scrape_date']>=recent_date]

      # this is based on review all recommendation tables!
      # based on the job_id never changed based on its setup!
      # develop another filter method based on title+company!
      yesterday_review_tmp = pd.concat([job_alert_tmp,recommendation_tmp,all_dt_tmp],axis=0)
      yesterday_review_tmp = yesterday_review_tmp[~yesterday_review_tmp['recommend'].isin(['1',1,1.0,'1.0'])]
      yesterday_review_tmp = yesterday_review_tmp[~yesterday_review_tmp['job_id'].isin(recent_week_review['job_id'].unique().tolist())]
      if len(yesterday_review_tmp)>0:
            recent_week_review = pd.concat([recent_week_review,yesterday_review_tmp],axis=0)
      recent_week_review.to_csv(recent_week_review_path, index=False, encoding='utf-8-sig')      
      

def get_last_apply_info(main_table_path: Path, 
                        new_df:pd.DataFrame)->pd.DataFrame:
      logger.info("---Add last apply info into increasal data---")
     # read main table to do filtering and get main feature of apply_date
      main_df = pd.read_csv(main_table_path, encoding='utf-8-sig')
      main_df = main_df.drop_duplicates().reset_index(drop=True)

      company_lower_set = set(new_df['company'].unique().tolist())
      last_apply_df = main_df[main_df['company'].isin(company_lower_set)]
  
      last_apply_df = last_apply_df[(last_apply_df['apply_date'].notnull())&(last_apply_df['apply_date']!='')]

      last_apply_df['apply_date'] = pd.to_datetime(last_apply_df['apply_date'], format="%Y%m%d", errors="coerce")
      last_apply_df = last_apply_df.sort_values(by=['company','apply_date'], ascending=False).drop_duplicates(subset='company',keep='first').reset_index(drop=True)
      last_apply_df = last_apply_df[['company','title','apply_date']].drop_duplicates().reset_index(drop=True)
      last_apply_df = last_apply_df.rename(columns={"apply_date": "last_apply_date", 
                                                    "title": "last_apply_title"})
      last_apply_df['last_apply_to_today_days'] = (pd.Timestamp.now() - last_apply_df['last_apply_date']).dt.days
      last_apply_df = last_apply_df[['company','last_apply_date','last_apply_title','last_apply_to_today_days']].drop_duplicates().reset_index(drop=True)
      return last_apply_df


def build_order_group(df:pd.DataFrame)->pd.DataFrame:
     group_df = df.sort_values(by=['priority','unit','company'],ascending=[True,True,True]).drop_duplicates(subset=['company'],keep='first').reset_index(drop=True)
     group_df['group'] = range(len(group_df))
     df = df.merge(group_df[['company','group']],on='company',how='left')
     df = df.sort_values(by=['group','priority','unit'],ascending=[True,True,True]).reset_index(drop=True)
     return df


def main(main_table_path:Path, added_data_path_list: list, 
         recommendation_path: Path,                
         title_filter_keywords:str,delete_words_in_title:str,
         delete_words_in_company:str, job_alert_company:list,
         job_alert_path:Path, all_today_new_open_jobs:Path,
         recent_week_review_path:Path):
      
      new_df = added_process(added_data_path_list, 
                              title_filter_keywords, 
                              delete_words_in_title, 
                              delete_words_in_company)

      # add applied data into main table
      # get table 1 and 2 as yesterday total review data, if today appear again, then delete from increasal data directly
      add_yesterday_to_main_table(job_alert_path, recommendation_path, 
                                  all_today_new_open_jobs, main_table_path,
                                  recent_week_review_path)
      
      recent_week_review_data = pd.read_csv(recent_week_review_path)

      new_df = new_df[~new_df['job_id'].isin(recent_week_review_data['job_id'].unique().tolist())]

      new_df = get_features(new_df)

      last_apply_df = get_last_apply_info(main_table_path, new_df)

      for col in ['last_apply_date','last_apply_title','last_apply_to_']:
           if col in new_df.columns.tolist():
                del new_df[col]

      new_df = new_df.merge(last_apply_df, on='company', how='left')
      new_df['recommend'] = 1
      new_df['apply_date'] = pd.Timestamp.now().strftime('%Y%m%d')

      need_cols = ['job_id', 'title', 'company', 'location', 'salary', 'posted_date', 
                   'job_url', 'scrape_date', 'last_apply_date','last_apply_title',
                   'last_apply_to_today_days', 'recommend', 'apply_date']

      logger.info("---Start to gain job alerts list---")
      job_alert_company = [x.lower() for x in job_alert_company]
      job_alert_df = new_df[new_df['company'].str.contains('|'.join(job_alert_company))]
      if len(job_alert_df)>0:
            job_alert_df = build_order_group(job_alert_df)
            job_alert_df.to_csv('double_check.csv',index=False,encoding='utf-8-sig')
            job_alert_df[need_cols].to_csv(job_alert_path, index=False, encoding='utf-8-sig')
            logger.info("✅ The first recommendation list has %d jobs!", len(job_alert_df))

      logger.info("---Begin to customed recommendation---")
      # never applied before and post in recent 5 days
      group1 = new_df[(new_df['last_apply_date'].isnull())&(new_df['new_period'].isin(['day','days']))&(new_df['new_unit'].isin([str(x) for x in range(1,6)]))]
      # post in recent 5 days and last apply date was 30 days ago
      group2 = new_df[(new_df['new_unit'].isin([str(x) for x in range(1,6)]))&(new_df['new_period'].isin(['days','day']))&(new_df['last_apply_to_today_days']>15)]

      recommendation = pd.concat([group1, group2], axis=0).drop_duplicates().reset_index(drop=True)
      recommendation = recommendation[~recommendation['job_id'].isin(job_alert_df['job_id'].unique().tolist())]
      recommendation = build_order_group(recommendation)
      recommendation[need_cols].to_csv(recommendation_path, index=False, encoding = 'utf-8-sig')
      logger.info("✅ The second recommendation list has %d jobs!", len(recommendation))
      
      logger.info("---Except above, other jobs for today---")
      # add new table for peak application period, it means apply all today's new posted jobs
      all_today_df = new_df[(new_df['new_unit'].isin(['1',1]))&(new_df['new_period']=='day')]

      exclude_ids = set(job_alert_df['job_id'].unique()) | set(recommendation['job_id'].unique())
      all_today_df = all_today_df[~all_today_df['job_id'].isin(exclude_ids)]

      # list according to the posted date
      all_today_df = build_order_group(all_today_df)
      all_today_df['recommend'] = ''
      all_today_df['apply_date'] = ''
      all_today_df[need_cols].to_csv(all_today_new_open_jobs, index=False, encoding='utf-8-sig')
      logger.info("✅ The third recommendation list has %d jobs!", len(all_today_df))

if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    arg_parser = argparse.ArgumentParser(description="Generate today's job recommendation")
    arg_parser.add_argument("--config", type=str,
                            default=str(PROJECT_ROOT / "config.yaml"))
    args = arg_parser.parse_args()

    cfg = load_config(args.config)
    config_dir = Path(args.config).resolve().parent

    title_filter_keywords = cfg["title_filter_keywords"]
    delete_words_in_title = cfg["delete_words_in_title"]
    delete_words_in_company = cfg["delete_words_in_company"]

    def resolve_path(base: Path, p) -> Path:
        p = Path(p)
        return p if p.is_absolute() else (base / p).resolve()

    main_table_path = resolve_path(config_dir, Path(cfg['main_table_path']))
    added_data_path_list = [
    resolve_path(config_dir, Path(cfg['data_dir']) / cfg['linkedin_filename_added']),
    resolve_path(config_dir, Path(cfg['data_dir']) / cfg['irishjobs_filename_added']),
    ]   

    recommendation_path     = resolve_path(config_dir, Path(cfg['recommendation_path']))
    job_alert_path          = resolve_path(config_dir, Path(cfg['job_alert_path']))
    all_today_new_open_jobs = resolve_path(config_dir, Path(cfg['all_today_new_open_jobs']))
    recent_week_review_path = resolve_path(config_dir, Path(cfg['recent_week_review_path']))

    similar_company_save_path = resolve_path(config_dir, Path(cfg['similar_company_save_path']))
    similar_company = pd.read_csv(similar_company_save_path)
    job_alert_company = similar_company['company'].unique().tolist() # str->list

    main(
        main_table_path=main_table_path,
        added_data_path_list=added_data_path_list,
        recommendation_path=recommendation_path,
        title_filter_keywords=title_filter_keywords,
        delete_words_in_title=delete_words_in_title,
        delete_words_in_company=delete_words_in_company,
        job_alert_company=job_alert_company,
        job_alert_path=job_alert_path,
        all_today_new_open_jobs=all_today_new_open_jobs,
        recent_week_review_path=recent_week_review_path
    )
      

