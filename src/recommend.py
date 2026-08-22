import pandas as pd
from pathlib import Path
from datetime import datetime
import re, argparse
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

def added_process(added_data_path_list:list, last_apply_path: Path, threshold: int):
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

      key_words = [x.lower() for x in ['AI', 'ML', 'Data', 'software', 'senior', 'engineer']]
      escaped_words1 = [re.escape(word) for word in key_words]
      pattern1 = '|'.join(escaped_words1)
      added = added[added['title'].str.contains(pattern1, na=False)]

      delete_words = ['trainee', 'affairs', 'grain', 'part-time', 'part time', 'intern']
      escaped_words2 = [re.escape(word) for word in delete_words]
      pattern2 = '|'.join(escaped_words2)
      added = added[~added['title'].str.contains(pattern2, na=False)]

      added['salary'] = added['salary'].apply(lambda x:str(x))
      added['start_salary'] = added['salary'].apply(lambda x:re.findall(r'[\d,]+',x)[0] if re.findall(r'[\d,]+',x) else '9999999')
      added['start_salary'] = added['start_salary'].apply(lambda x:int(str(x).replace(',', '')))
      if threshold is not None:
          added = added[added['start_salary']>=threshold]      
      print(' - after data cleaning with ：', added.shape)

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

def main(main_table_path:Path, added_data_path_list: list, 
         last_apply_path: Path, recommendation_path: Path, agent_key_words, threshold):

      new_df = added_process(added_data_path_list, last_apply_path, threshold)

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
      new_df['apply_date'] = new_df['apply_date'].fillna(new_df['apply_date_fill'])
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
      new_df = new_df[~new_df['company'].str.contains('|'.join(agent_key_words))]

      group1 = new_df[(new_df['apply_date'].isnull())&(new_df['new_period'].isin(['day','days']))&(new_df['new_unit'].isin([str(x) for x in range(1,8)]))]

      group2 = new_df[(new_df['new_unit'].isin([str(x) for x in range(1,4)]))&(new_df['new_period'].isin(['days','day']))&(new_df['last_apply_to_today']>30)]

      recommendation = pd.concat([group1, group2], axis=0).drop_duplicates().reset_index(drop=True)
      recommendation = recommendation.sort_values(by=['new_period','new_unit','period','unit'],ascending=True).reset_index(drop=True)
      piority = {'minute':0, 'minutes':1, 'hour':2, 'hours':3, 'day':4 , 'days':5, 'week':6, 'weeks':7}
      recommendation['priority'] = recommendation['period'].map(piority)
      recommendation = recommendation.sort_values(by=['new_period','new_unit','priority','unit'],ascending=True).reset_index(drop=True)
      print(f" - There are total {len(recommendation)} jobs to recommend to you！")
      recommendation['recommend'] = 1
      recommendation['apply_date'] = pd.Timestamp.now().strftime('%Y%m%d')

      need_cols = df.columns.tolist()
      recommendation = recommendation[need_cols]
      recommendation = recommendation.sort_values(by=['posted_date'], ascending = True).reset_index(drop=True)
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
      args = arg_parser.parse_args()
      
      agent_key_words = ['human', 'recruitment', 'jobgether', 'recruit', 'fruition']
      main(Path(args.main_table_path), 
           args.added_data_path_list, 
           Path(args.last_apply_path), 
           Path(args.recommendation_path), agent_key_words, args.threshold)
      

