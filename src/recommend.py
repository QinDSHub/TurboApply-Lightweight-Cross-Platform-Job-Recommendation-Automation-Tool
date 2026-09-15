import pandas as pd
from pathlib import Path
import re, argparse
import warnings
from utils import clear_file_os, load_config
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

def added_process(added_data_path_list:list, 
                  last_apply_path: Path, 
                  min_base_salary: int, 
                  needed_keywords_in_title:str,
                  delete_words_in_title:str,
                  delete_words_in_company: str,):
      added = pd.DataFrame()
      for address in added_data_path_list:
            print(address)
            tmp = pd.read_csv(address)
            for col in tmp.columns.tolist():
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

      last_df = pd.read_csv(last_apply_path)
      for col in last_df.columns.tolist():
            last_df[col] = last_df[col].apply(lambda x:str(x).lower())

      data = added.merge(last_df[['company','apply_date']], on='company', how='left')
      print(' - Final data with：')
      print(pd.isnull(data).sum())
      print('='*20)

      return data


def gain_job_alerts(added:pd.DataFrame, job_alert_company:str, job_alert_path:Path):
      # Add company-level job alerts:
      # Users define a list of target companies, and any newly posted job
      # from those companies will be recommended regardless of previous
      # applications or application timing.
      # Only enable this feature for users with clearly defined target companies.
      dt = added.copy()

      if 'apply_date' in dt.columns.tolist():
            del dt['apply_date']

      job_alert_company = [x.lower() for x in job_alert_company.split(',')]
      new_alert_df = dt[dt['company'].str.contains('|'.join(job_alert_company))]
      if len(new_alert_df)>0:
            if 'recommend' in new_alert_df.columns.tolist():
                  del new_alert_df['recommend']
            if 'start_salary' in new_alert_df.columns.tolist():
                  del new_alert_df['start_salary']
            new_alert_df = new_alert_df.sort_values(by=['company','title']).reset_index(drop=True)
            new_alert_df.to_csv(job_alert_path, index=False, encoding='utf-8-sig')
            print('If you have job alert company list, you could apply right now!')
      else:
            clear_file_os(job_alert_path)
            print('Today, there are no new jobs opened by your target companies!')

def get_features(new_df:pd.DataFrame)->pd.DataFrame:
      new_df['posted_date'] = new_df['posted_date'].apply(lambda x:str(x).replace('posted','').strip())

      new_df['unit'] = new_df['posted_date'].apply(lambda x:x.split()[0])

      # reduce the posted date granularity for recommendation: posted less 24 hours-> 1 day
      new_df['period'] = new_df['posted_date'].apply(lambda x:x.split()[1])
      new_df['new_period'] = new_df['period']
      new_df.loc[new_df['period'].isin(['hours','hour', 'minutes', 'minute']), 'new_period'] = 'day'
      new_df['new_unit'] = new_df['unit']
      new_df.loc[new_df['period'].isin(['hours','hour', 'minutes', 'minute']), 'new_unit'] = '1'

      piority = {'minute':0, 'minutes':1, 'hour':2, 'hours':3, 'day':4 , 'days':5, 'week':6, 'weeks':7}
      new_df['priority'] = new_df['period'].map(piority)

      new_df['priority'] = pd.to_numeric(new_df['priority'])
      new_df['unit'] = pd.to_numeric(new_df['unit'])

      return new_df

def main(main_table_path:Path, added_data_path_list: list, 
         last_apply_path: Path, recommendation_path: Path, min_base_salary:int,                  
         title_filter_keywords:str,delete_words_in_title:str,
         delete_words_in_company:str, job_alert_company:str,
         job_alert_path:Path, all_today_new_open_jobs:Path):

      new_df = added_process(added_data_path_list, last_apply_path, 
                             min_base_salary, title_filter_keywords, 
                             delete_words_in_title, delete_words_in_company, )
      gain_job_alerts(new_df, job_alert_company, job_alert_path)

      recommendation_tmp = pd.read_csv(recommendation_path)
      recommendation_tmp = recommendation_tmp[recommendation_tmp['recommend'].isin(['1',1])]
      if len(recommendation_tmp)>0:
            recommendation_tmp.to_csv(main_table_path, mode='a', header=False, 
                                      index=False, encoding = 'utf-8-sig')

      # read main table to do filtering and get main feature of apply_date
      df = pd.read_csv(main_table_path, encoding='utf-8-sig')
      need_cols = df.columns.tolist()
      for col in need_cols:
            df[col] = df[col].apply(lambda x:str(x).lower())

      company_lower_set = set(new_df['company'].unique().tolist())
      df_filtered = df[df['company'].isin(company_lower_set)]
      # must transfer apply date into dat format
      df_filtered['apply_date'] = pd.to_datetime(df_filtered[])
      df_filtered = df_filtered.sort_values(by=['company','apply_date'], ascending=False).drop_duplicates(subset='company',keep='first').reset_index(drop=True)
      print('- double check last apply date to be unique for last one: ',df_filtered.shape[0]==df_filtered['company'].nunique())
      df_filtered.rename(columns={'apply_date':'apply_date_fill'},inplace=True)

      # # delete those jobs that have applied before
      # # but if the jobs were applied in last year or last last year
      # # therefore, cancel below filtering function
      # df_job_set = set(df_filtered['job_id'].unique().tolist())
      # new_df = new_df[~new_df['job_id'].isin(df_job_set)]
      # print(' - Delete duplicates job_id from main table，the increasal data with：', new_df.shape)

      new_df = new_df.merge(df_filtered[['company','apply_date_fill']],on = 'company', how='left')
      new_df.loc[new_df['apply_date_fill'].notnull(), 'apply_date'] = new_df['apply_date_fill']
      del new_df['apply_date_fill']

      new_df['apply_date_dt'] = pd.to_datetime(new_df['apply_date'], format='%Y%m%d', errors='coerce')
      new_df['last_apply_to_today'] = (pd.Timestamp.now() - new_df['apply_date_dt']).dt.days

      new_df = get_features(new_df)

      # add new table for peak application period, it means apply all today's new posted jobs
      all_today_df = new_df[(new_df['new_unit'].isin(['1',1]))&(new_df['new_period']=='day')]
      # list according to the posted date
      all_today_df = all_today_df.sort_values(by=['priority','unit'],ascending=True).reset_index(drop=True)
      all_today_df[need_cols].to_csv(all_today_new_open_jobs, index=False, encoding='utf-8-sig')

      # never applied before and post in recent 5 days
      group1 = new_df[(new_df['apply_date'].isnull())&(new_df['new_period'].isin(['day','days']))&(new_df['new_unit'].isin([str(x) for x in range(1,6)]))]
      # post in recent 5 days and last apply date was 30 days ago
      group2 = new_df[(new_df['new_unit'].isin([str(x) for x in range(1,6)]))&(new_df['new_period'].isin(['days','day']))&(new_df['last_apply_to_today']>30)]

      recommendation = pd.concat([group1, group2], axis=0).drop_duplicates().reset_index(drop=True)

      recommendation = recommendation.sort_values(by=['priority','unit'],ascending=True).reset_index(drop=True)
      print(f" - Finally, there are total {len(recommendation)} jobs to recommend to you！")
      recommendation['recommend'] = 1
      recommendation['apply_date'] = pd.Timestamp.now().strftime('%Y%m%d')

      recommendation = recommendation[need_cols]
      recommendation.to_csv(recommendation_path, index=False, encoding = 'utf-8-sig')
      print(' - Today_recommendation.csv has been saved locally, you could apply right now！')
      
if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    arg_parser = argparse.ArgumentParser(description="Generate today's job recommendation")
    arg_parser.add_argument("--config", type=str,
                            default=str(PROJECT_ROOT / "config.yaml"))
    arg_parser.add_argument('--title_filter_keywords', default="AI,ML,Data,software,senior,engineer")
    arg_parser.add_argument('--delete_words_in_title', default="trainee,affairs,grain,part-time,part time,intern,contract,product")
    arg_parser.add_argument('--delete_words_in_company', default="human,recruitment,jobgether,recruit,fruition,talent")
    arg_parser.add_argument('--min_base_salary', type=int, default=0)
    arg_parser.add_argument('--job_alert_company', default="")
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

    main(
        main_table_path=main_table_path,
        added_data_path_list=added_data_path_list,
        last_apply_path=last_apply_path,
        recommendation_path=recommendation_path,
        title_filter_keywords=args.title_filter_keywords,
        delete_words_in_title=args.delete_words_in_title,
        delete_words_in_company=args.delete_words_in_company,
        min_base_salary=args.min_base_salary,
        job_alert_company=args.job_alert_company,
        job_alert_path=job_alert_path,
        all_today_new_open_jobs=all_today_new_open_jobs,
    )
      

