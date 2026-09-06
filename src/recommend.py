import pandas as pd
from pathlib import Path
from datetime import datetime
import re, argparse
import warnings
from utils import clear_file_os
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

def added_process(added_data_path_list:list, last_apply_path: Path, threshold: int, 
                  needed_keywords_in_title:str,
                  delete_words_in_title:str,
                  job_alert_company:str,
                  job_alert_path:Path):
      added = pd.DataFrame()
      for address in added_data_path_list:
            print(added.shape)
            tmp = pd.read_csv(address)
            for col in tmp.columns.tolist():
                  tmp[col] = tmp[col].apply(lambda x:str(x).lower())
            added = pd.concat([added,tmp], axis=0)
      print(' - Merge increasal data from different platforms with ：', added.shape)

      added = added.drop_duplicates(subset = ['company','title'],keep='first').reset_index(drop=True)
      print(" - Delete duplicate jobs with：", added.shape)

      key_words = [x.lower() for x in needed_keywords_in_title.split(',')]
      escaped_words1 = [re.escape(word) for word in key_words]
      pattern1 = '|'.join(escaped_words1)
      added = added[added['title'].str.contains(pattern1, na=False)]

      # delete_words = ['trainee', 'affairs', 'grain', 'part-time', 'part time', 'intern']
      escaped_words2 = [re.escape(word) for word in delete_words_in_title.split(',')]
      pattern2 = '|'.join(escaped_words2)
      added = added[~added['title'].str.contains(pattern2, na=False)]

      added['salary'] = added['salary'].apply(lambda x:str(x))
      added['start_salary'] = added['salary'].apply(lambda x:re.findall(r'[\d,]+',x)[0] if re.findall(r'[\d,]+',x) else '9999999')
      added['start_salary'] = added['start_salary'].apply(lambda x:int(str(x).replace(',', '')))
      if threshold is not None:
          added = added[added['start_salary']>=int(threshold)]      
      print(' - after data cleaning with ：', added.shape)

      if 'apply_date' in added.columns.tolist():
           del added['apply_date']

      # Add company-level job alerts:
      # Users define a list of target companies, and any newly posted job
      # from those companies will be recommended regardless of previous
      # applications or application timing.
      # Only enable this feature for users with clearly defined target companies.
      job_alert_company = [x.lower() for x in job_alert_company.split(',')]
      new_alert_df = added[added['company'].str.contains('|'.join(job_alert_company))]
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

      last_df = pd.read_csv(last_apply_path)
      for col in last_df.columns.tolist():
            last_df[col] = last_df[col].apply(lambda x:str(x).lower())

      data = added.merge(last_df[['company','apply_date']], on='company', how='left')
      print(' - Final data with：')
      print(pd.isnull(data).sum())
      print('='*20)

      return data

def main(main_table_path:Path, added_data_path_list: list, 
         last_apply_path: Path, recommendation_path: Path, threshold,                  
         needed_keywords_in_title:str,delete_words_in_title:str,
         delete_words_in_company:str, job_alert_company:str,
         job_alert_path:Path):

      new_df = added_process(added_data_path_list, last_apply_path, threshold, 
                             needed_keywords_in_title, delete_words_in_title,
                             job_alert_company,job_alert_path)

      recommendation_tmp = pd.read_csv(recommendation_path)
      recommendation_tmp = recommendation_tmp[recommendation_tmp['recommend'].isin(['1',1])]
      if len(recommendation_tmp)>0:
            recommendation_tmp.to_csv(main_table_path, mode='a', header=False, 
                                      index=False, encoding = 'utf-8-sig')
 
      df = pd.read_csv(main_table_path, encoding='utf-8-sig')
      for col in df.columns.tolist():
            df[col] = df[col].apply(lambda x:str(x).lower())

      company_lower_set = set(new_df['company'].unique().tolist())
      df_filtered = df[df['company'].isin(company_lower_set)]
      df_filtered = df_filtered.sort_values(by=['company','apply_date'], ascending=False).drop_duplicates(subset='company',keep='first').reset_index(drop=True)
      df_filtered.rename(columns={'apply_date':'apply_date_fill'},inplace=True)

      df_job_set = set(df_filtered['job_id'].unique().tolist())
      new_df = new_df[~new_df['job_id'].isin(df_job_set)]
      print(' - Delete duplicates job_id from main table，the increasal data with：', new_df.shape)

      new_df = new_df.merge(df_filtered[['company','apply_date_fill']], on = 'company', how='left')
      new_df.loc[new_df['apply_date_fill'].notnull(), 'apply_date'] = new_df['apply_date_fill']
      del new_df['apply_date_fill']

      new_df['last_apply_to_today'] = (pd.Timestamp.now()-pd.to_datetime(new_df['apply_date'])).dt.days
      new_df['posted_date'] = new_df['posted_date'].apply(lambda x:str(x).replace('posted','').strip())

      new_df['unit'] = new_df['posted_date'].apply(lambda x:x.split()[0])
      new_df['period'] = new_df['posted_date'].apply(lambda x:x.split()[1])
      new_df['new_period'] = new_df['period']
      new_df.loc[new_df['period'].isin(['hours','hour', 'minutes', 'minute']), 'new_period'] = 'day'
      new_df['new_unit'] = new_df['unit']
      new_df.loc[new_df['period'].isin(['hours','hour', 'minutes', 'minute']), 'new_unit'] = '1'
      
      new_df = new_df[~new_df['title'].str.contains('data engineer')]
      new_df = new_df[~new_df['company'].str.contains('|'.join(delete_words_in_company.split(',')))]

      group1 = new_df[(new_df['apply_date'].isnull())&(new_df['new_period'].isin(['day','days']))&(new_df['new_unit'].isin([str(x) for x in range(1,8)]))]

      group2 = new_df[(new_df['new_unit'].isin([str(x) for x in range(1,4)]))&(new_df['new_period'].isin(['days','day']))&(new_df['last_apply_to_today']>30)]

      recommendation = pd.concat([group1, group2], axis=0).drop_duplicates().reset_index(drop=True)
      recommendation = recommendation.sort_values(by=['new_period','new_unit','period','unit'],ascending=True).reset_index(drop=True)
      piority = {'minute':0, 'minutes':1, 'hour':2, 'hours':3, 'day':4 , 'days':5, 'week':6, 'weeks':7}
      recommendation['priority'] = recommendation['period'].map(piority)

      recommendation['priority'] = pd.to_numeric(recommendation['priority'])
      recommendation['unit'] = pd.to_numeric(recommendation['unit'])

      recommendation = recommendation.sort_values(by=['priority','unit'],ascending=True).reset_index(drop=True)
      print(f" - There are total {len(recommendation)} jobs to recommend to you！")
      recommendation['recommend'] = 1
      recommendation['apply_date'] = pd.Timestamp.now().strftime('%Y%m%d')

      need_cols = df.columns.tolist()
      recommendation = recommendation[need_cols]
      recommendation.to_csv(recommendation_path, index=False, encoding = 'utf-8-sig')
      print(' - Today_recommendation.csv has been saved locally, you could apply right now！')
      
if __name__=='__main__':
      arg_parser = argparse.ArgumentParser(description='recommend jobs for today application')
      arg_parser.add_argument('--main_table_path', default='../all_jobs.csv', help='total table path')
      arg_parser.add_argument('--added_data_path_list', 
                              default=[Path('../linkedin_data_added.csv'),
                                       Path('../irishjobs_data_added.csv')],
                                       help='increasal data path')
      arg_parser.add_argument('--last_apply_path', default='../applied_data/last_apply_data.csv', help='your own historical apply data')
      arg_parser.add_argument('--recommendation_path', default='../today_recommendation.csv', help="the path to save recommendation for today!")
      arg_parser.add_argument('--threshold', type=int, default=None, help='salary threshold (optional; if not set, no filtering is applied)')
      arg_parser.add_argument('--needed_keywords_in_title', type=str, default='', help='keywords in title to help filtering')
      arg_parser.add_argument('--delete_words_in_title', type=str, default='', help='delete keywords in title')
      arg_parser.add_argument('--delete_words_in_company', type=str, default='', help='delete keywords in company')
      arg_parser.add_argument('--job_alert_company', type=str, default='', help='your target company list, apply once new jobs open')
      arg_parser.add_argument('--job_alert_path', default='../job_alert_recommendation.csv', help="the path to save recommendation for your target companies!")
      args = arg_parser.parse_args()
      main(Path(args.main_table_path), 
           args.added_data_path_list, 
           Path(args.last_apply_path), 
           Path(args.recommendation_path), 
           args.threshold,
           args.needed_keywords_in_title,
           args.delete_words_in_title,
           args.delete_words_in_company,
           args.job_alert_company,
           Path(args.job_alert_path)
           )
      

