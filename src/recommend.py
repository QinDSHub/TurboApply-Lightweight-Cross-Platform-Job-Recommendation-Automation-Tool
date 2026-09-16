import pandas as pd
from pathlib import Path
import re, argparse
import warnings
from utils import clear_file_os, load_config
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

def added_process(added_data_path_list:list, 
                  min_base_salary: int, 
                  needed_keywords_in_title:str,
                  delete_words_in_title:str,
                  delete_words_in_company: str,):
      print('------Integrate increasal data, data preprocessing and features extraction------')
      added = pd.DataFrame()
      for address in added_data_path_list:
            print(address)
            tmp = pd.read_csv(address)
            for col in ['company','title']:
                  tmp[col] = tmp[col].apply(lambda x:str(x).lower())
            # add drop-duplicates in single platform
            tmp = tmp.drop_duplicates(subset=['company','title'],keep='first').reset_index(drop=True)
            added = pd.concat([added,tmp], axis=0)
      print(' - Merge increasal data from different platforms with ：', added.shape)

      # drop-duplicates in cross platform
      added = added.drop_duplicates(subset = ['company','title'],keep='first').reset_index(drop=True)
      print(" - Delete duplicate jobs in cross platforms：", added.shape)

      # start data filtering
      key_words = [x.lower() for x in needed_keywords_in_title.split(',')]
      escaped_words1 = [re.escape(word) for word in key_words]
      pattern1 = '|'.join(escaped_words1)
      added = added[added['title'].str.contains(pattern1, na=False)]

      # delete_words = ['trainee', 'affairs', 'grain', 'part-time', 'part time', 'intern']
      escaped_words2 = [re.escape(word) for word in delete_words_in_title.split(',')]
      pattern2 = '|'.join(escaped_words2)
      added = added[~added['title'].str.contains(pattern2, na=False)]

      added = added[~added['company'].str.contains('|'.join(delete_words_in_company.split(',')))]

      added['start_salary'] = (added['salary'].astype(str).str.extract(r'([\d,]+)', expand=False)
                               .str.replace(',', '', regex=False)
                               .fillna('9999999')
                               .astype(int)
                               )
      
      if min_base_salary is not None:
          added = added[added['start_salary']>=int(min_base_salary)]      
      print(' - after data filtering with ：', added.shape)

      if 'apply_date' in added.columns.tolist():
           del added['apply_date']

      return added


def get_features(new_df:pd.DataFrame)->pd.DataFrame:
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


def gain_job_alerts(added:pd.DataFrame, job_alert_company:list, job_alert_path:Path,
                    last_apply_df:pd.DataFrame, need_cols:list)->pd.DataFrame:
      # Add company-level job alerts:
      # Users define a list of target companies, and any newly posted job
      # from those companies will be recommended regardless of previous
      # applications or application timing.
      # Only enable this feature for users with clearly defined target companies.
      # start today's job alert filtering
      dt = added.copy()





def get_last_apply_info(job_alert_path:Path, recommendation_path: Path, 
                        all_today_new_open_jobs: Path, main_table_path: Path, 
                        new_df:pd.DataFrame)->pd.DataFrame:
      
      print('---Starting Data Integration---')
      # append result0 into primary_table
      job_alert_tmp = pd.read_csv(job_alert_path)
      job_alert_tmp = job_alert_tmp[job_alert_tmp['recommend'].isin(['1',1])]
      if job_alert_tmp:
            job_alert_tmp.to_csv(main_table_path, mode='a', 
                                          header=False, 
                                          index=False, encoding = 'utf-8-sig')

      # append result1 into primary_table
      recommendation_tmp = pd.read_csv(recommendation_path)
      recommendation_tmp = recommendation_tmp[recommendation_tmp['recommend'].isin(['1',1])]
      if recommendation_tmp:
            recommendation_tmp.to_csv(main_table_path, mode='a', 
                                      header=False, 
                                      index=False, encoding = 'utf-8-sig')

      # append result2 into primary_table
      all_dt_tmp = pd.read_csv(all_today_new_open_jobs)
      all_dt_tmp = all_dt_tmp[all_dt_tmp['recommend'].isin(['1',1])]
      if all_dt_tmp:
            all_dt_tmp.to_csv(main_table_path, mode='a', 
                                    header=False, 
                                    index=False, encoding = 'utf-8-sig')

     # read main table to do filtering and get main feature of apply_date
      print('------Begin to get last apply info------')
      main_df = pd.read_csv(main_table_path, encoding='utf-8-sig')
      main_df = main_df.drop_duplicates().reset_index(drop=True)

      for col in ['company','title']:
            main_df[col] = main_df[col].apply(lambda x:str(x).lower())

      company_lower_set = set(new_df['company'].unique().tolist())
      last_apply_df = main_df[main_df['company'].isin(company_lower_set)]
      last_apply_df['apply_date'] = pd.to_datetime(last_apply_df['apply_date'], format="%Y%m%d", errors="coerce")
      last_apply_df = last_apply_df.sort_values(by=['company','apply_date'], ascending=False).drop_duplicates(subset='company',keep='first').reset_index(drop=True)
      last_apply_df.rename(columns={"apply_date":"last_apply_date","title":"last_apply_title"},inplace=True)
      last_apply_df['last_apply_to_today_days'] = (pd.Timestamp.now() - last_apply_df['last_apply_date']).dt.days
      print('- double check last apply date to be unique for last one: ',last_apply_df.shape[0]==last_apply_df['company'].nunique())
      last_apply_df = last_apply_df[['company','last_apply_date','last_apply_title','last_apply_to_today_days']].drop_duplicates().reset_index(drop=True)
      return last_apply_df


def main(main_table_path:Path, added_data_path_list: list, 
         last_apply_path: Path, recommendation_path: Path, min_base_salary:int,                  
         title_filter_keywords:str,delete_words_in_title:str,
         delete_words_in_company:str, job_alert_company:list,
         job_alert_path:Path, all_today_new_open_jobs:Path):
      
      new_df = added_process(added_data_path_list, last_apply_path, 
                              min_base_salary, title_filter_keywords, 
                              delete_words_in_title, delete_words_in_company, )
      new_df = get_features(new_df)
      
      last_apply_df = get_last_apply_info(job_alert_path, recommendation_path, 
                        all_today_new_open_jobs, main_table_path, new_df)

      new_df = new_df.merge(last_apply_df, on='company', how='left')
      new_df['recommend'] = 1
      new_df['apply_date'] = pd.Timestamp.now().strftime('%Y%m%d')

      need_cols = ['job_id', 'title', 'company', 'location', 'salary', 'posted_date', 
                   'job_url', 'scrape_date', 'last_apply_date','last_apply_title',
                   'last_apply_to_today_days', 'recommend', 'apply_date']

      print('------Starting gain job alerts company list------')
      job_alert_company = [x.lower() for x in job_alert_company]
      job_alert_df = new_df[new_df['company'].str.contains('|'.join(job_alert_company))]
      if job_alert_df:
            job_alert_df = job_alert_df.sort_values(by=['priority','unit','company'],ascending=True).reset_index(drop=True)
            job_alert_df[need_cols].to_csv(job_alert_path, index=False, encoding='utf-8-sig')
            print(f' - Firstly, there are total {len(job_alert_df)} jobs for job alert company list!')

      print('------Starting customed recemmendation------')
      # never applied before and post in recent 5 days
      group1 = new_df[(new_df['apply_date'].isnull())&(new_df['new_period'].isin(['day','days']))&(new_df['new_unit'].isin([str(x) for x in range(1,6)]))]
      # post in recent 5 days and last apply date was 30 days ago
      group2 = new_df[(new_df['new_unit'].isin([str(x) for x in range(1,6)]))&(new_df['new_period'].isin(['days','day']))&(new_df['last_apply_to_today']>30)]

      recommendation = pd.concat([group1, group2], axis=0).drop_duplicates().reset_index(drop=True)
      recommendation = recommendation[~recommendation['job_id'].isin(job_alert_df['job_id'].unique().tolist())]

      recommendation = recommendation.sort_values(by=['priority','unit','company'],ascending=True).reset_index(drop=True)
      recommendation[need_cols].to_csv(recommendation_path, index=False, encoding = 'utf-8-sig')
      print(f" - Secondly, there are total {len(recommendation)} jobs to recommend by your customization！")

      print('---Begin to generate all today new open jobs list---')
      # add new table for peak application period, it means apply all today's new posted jobs
      all_today_df = new_df[(new_df['new_unit'].isin(['1',1]))&(new_df['new_period']=='day')]

      exclude_ids = set(job_alert_df['job_id'].unique()) | set(recommendation['job_id'].unique())
      all_today_df = all_today_df[~all_today_df['job_id'].isin(exclude_ids)]

      # list according to the posted date
      all_today_df = all_today_df.sort_values(by=['priority','unit', 'company'],ascending=True).reset_index(drop=True)
      all_today_df['recommend'] = ''
      all_today_df['apply_date'] = ''
      all_today_df[need_cols].to_csv(all_today_new_open_jobs, index=False, encoding='utf-8-sig')
      print(' - Finally, if you still have time, you could double check all_today_new_open_jobs.csv！')


if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    arg_parser = argparse.ArgumentParser(description="Generate today's job recommendation")
    arg_parser.add_argument("--config", type=str,
                            default=str(PROJECT_ROOT / "config.yaml"))
    arg_parser.add_argument("--min_base_salary", type=int, default=0)
    args = arg_parser.parse_args()

    cfg = load_config(args.config)
    config_dir = Path(args.config).resolve().parent

    def resolve_path(base: Path, p) -> Path:
        p = Path(p)
        return p if p.is_absolute() else (base / p).resolve()

    main_table_path = resolve_path(config_dir, cfg['main_table_path'])
    added_data_path_list = [
    resolve_path(config_dir, Path(cfg['data_dir']) / cfg['linkedin_filename_added']),
    resolve_path(config_dir, Path(cfg['data_dir']) / cfg['irishjobs_filename_added']),
    ]   

    last_apply_path         = resolve_path(config_dir, cfg['save_file'])
    recommendation_path     = resolve_path(config_dir, cfg['recommendation_path'])
    job_alert_path          = resolve_path(config_dir, cfg['job_alert_path'])
    all_today_new_open_jobs = resolve_path(config_dir, cfg['all_today_new_open_jobs'])
    
    title_filter_keywords = cfg["title_filter_keywords"]
    delete_words_in_title = cfg["delete_words_in_title"]
    delete_words_in_company = cfg["delete_words_in_company"]

    similar_company_save_path = resolve_path(config_dir, cfg['similar_company_save_path'])
    similar_company = pd.read_csv(similar_company_save_path)
    job_alert_company = similar_company['company'].unique().tolist() # str->list
    
    main(
        main_table_path=main_table_path,
        added_data_path_list=added_data_path_list,
        last_apply_path=last_apply_path,
        recommendation_path=recommendation_path,
        title_filter_keywords=title_filter_keywords,
        delete_words_in_title=delete_words_in_title,
        delete_words_in_company=delete_words_in_company,
        min_base_salary=args.min_base_salary,
        job_alert_company=job_alert_company,
        job_alert_path=job_alert_path,
        all_today_new_open_jobs=all_today_new_open_jobs,
    )
      

