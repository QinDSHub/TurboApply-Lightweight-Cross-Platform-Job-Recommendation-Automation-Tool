import csv,time
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
from utils import clear_folder_os

@dataclass
class JobInfo:
    job_id: str
    title: str
    company: str
    location: str
    salary: str
    posted_date: str
    job_url: str = "" 
    scrape_date: str = "" 
    recommend: str = ""
    apply_date: str = ""

class IrishJobsLocalParser:
    
    def __init__(self, html_data_dir: str, data_dir: str):
        self.html_data_dir = Path(html_data_dir)
        self.html_data_dir.mkdir(exist_ok=True)
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
    
    def parse_html_file(self, html_file_path: str) -> List[JobInfo]:
        """
        parse one HTML file
        
        Args:
            html_file_path: HTML raw data path
            
        Returns:
            jobs info
        """
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        return self.parse_html_content(html_content)
    
    def parse_html_content(self, html_content: str) -> List[JobInfo]:
        soup = BeautifulSoup(html_content, 'html.parser')
        cards = soup.select('[data-at="job-item"]')

        if not cards:
            print("Do not find job cards（[data-at='job-item']）, pls double check the search result of HTML from IrishJobs.ie!")
            return []

        jobs = []
        for card in cards:
            job = self._parse_card(card)
            if job:
                jobs.append(job)
        return jobs

    def _parse_card(self, card) -> Optional[JobInfo]:
        try:
            raw_id = card.get('id', '')
            job_id = raw_id.replace('job-item-', '') if raw_id else ''
            if not job_id:
                return None

            title_el = card.select_one('[data-at="job-item-title"]')
            title = title_el.get_text(strip=True) if title_el else ''
            href = title_el.get('href', '') if title_el else ''
            job_url = href if href.startswith('http') else f"https://www.irishjobs.ie{href}"

            company_el = card.select_one('[data-at="job-item-company-name"]')
            company = company_el.get_text(strip=True) if company_el else ''
            company = company.lower()

            # logo_el = card.select_one('[data-at="company-logo"] img')
            # company_logo = logo_el.get('src', '') if logo_el else ''

            location_el = card.select_one('[data-at="job-item-location"]')
            location = location_el.get_text(strip=True) if location_el else ''

            salary_el = card.select_one('[data-at="job-item-salary-info"]')
            salary = salary_el.get_text(strip=True) if salary_el else 'Not Disclosed'

            timeago_el = card.select_one('[data-at="job-item-timeago"]')
            posted_date = timeago_el.get_text(strip=True) if timeago_el else ''

            scrape_date = datetime.now().strftime('%Y%m%d') 

            return JobInfo(
                job_id=job_id,
                title=title,
                company=company,
                location=location,
                salary=salary,
                posted_date=posted_date,
                job_url=job_url,
                scrape_date = scrape_date
            )
        except Exception as e:
            print(f"Parse job card failed: {e}")
            return None
    
    def parse_multiple_pages(self, file_pattern: str, page_range: range) -> List[JobInfo]:
        """
        parse multiple html pages
        
        Args:
            file_pattern: file name pattern，如 "page_{page}.html"
            page_range: page range，如 range(1, 8)
            
        Returns:
            all increasal jobs
        """
        all_jobs = []
        
        for page in page_range:
            filename = file_pattern.format(page=page)
            file_path = self.html_data_dir / filename
            
            if file_path.exists():
                print(f"is parsing {page} page...")
                jobs = self.parse_html_file(str(file_path))
                all_jobs.extend(jobs)
                print(f"  Find {len(jobs)} jobs")
            else:
                print(f"file path not exists: {file_path}")
        
        return all_jobs


    def print_stats(self, jobs: List[JobInfo]) -> None:
        if not jobs:
            print("No increasal data!")
            return
        
        print(f"\n All increasal jobs number: {len(jobs)}")
        
        company_counts = {}
        for job in jobs:
            company_counts[job.company] = company_counts.get(job.company, 0) + 1
        
        for company, count in sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {company}: {count}")
        
        location_counts = {}
        for job in jobs:
            loc = job.location or "Not assigned"
            location_counts[loc] = location_counts.get(loc, 0) + 1
        
        for loc, count in sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {loc}: {count}")
        
        salary_known = sum(1 for job in jobs if job.salary and job.salary != "Not Disclosed")
        print(f"\nJobs with salary number: {salary_known}/{len(jobs)}")


def main(start_page: int, end_page: int, html_data_dir: str, data_dir: str, filename: str, is_total: bool, filename_added: str):

    parser = IrishJobsLocalParser(html_data_dir, data_dir)
    
    jobs = parser.parse_multiple_pages(
        file_pattern="page_{page}.html",
        page_range=range(start_page, end_page + 1)
    )
    
    if jobs:
        parser.print_stats(jobs)

        columns = ['job_id', 'title', 'company', 'location', 'salary', 'posted_date', 'job_url', 'scrape_date', 'recommend', 'apply_date']
        if is_total: 
            save_path = Path(data_dir) / filename
        else:
            save_path = Path(data_dir) / filename_added
        print(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(jobs, columns = columns)
        df.to_csv(save_path, index=False, encoding='utf-8-sig')
        print('Increasal data is saved locally！')
    else:
        print("No more increasal data!")


if __name__ == "__main__":
    import argparse
    arg_parser = argparse.ArgumentParser(description='get jobs for start and end page')
    arg_parser.add_argument('--start_page', type=int, default=1, help='start page for parser')
    arg_parser.add_argument('--end_page', type=int, default=5, help='end page for parser')
    arg_parser.add_argument('--html_data_dir', default='../irishjobs_raw_data', help='raw data for html')
    arg_parser.add_argument('--data_dir', default="../", help="save extracted data")
    arg_parser.add_argument('--filename', default="irishjobs_data.csv", help='the file name for saved data')
    arg_parser.add_argument('--is_total', action='store_true', default=False, 
                           help='if total, then run with filename, or run with filename_added')
    arg_parser.add_argument('--filename_added', default='irishjobs_data_added.csv', help='the file name for added increasal data')
    args = arg_parser.parse_args()

    # Use method：
    # First run：python parser.py --is_total --start_page 1 --end_page 35
    # Afterwards run with：python parser.py --html_data_dir '../raw_data_20260814' --start_page 1 --end_page 10
    main(args.start_page, args.end_page, args.html_data_dir, args.data_dir, args.filename, args.is_total, args.filename_added)

    # clear raw data files for next using.
    clear_folder_os(args.html_data_dir)