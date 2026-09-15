import csv,time
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
from utils import clear_folder_os
from utils import load_config
import argparse, dataclasses
from utils import JobInfo

class IrishJobsLocalParser:    
    def __init__(self, html_data_dir: str, data_dir: str):
        self.html_data_dir = Path(html_data_dir)
        self.html_data_dir.mkdir(exist_ok=True)
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
    
    def parse_html_file(self, html_file_path: str) -> List[JobInfo]:
        """
        parse one html file to extract job's info
        
        Args:
            html_file_path: HTML path
            
        Returns:
            html content
        """
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        return self.parse_html_content(html_content)
    
    def parse_html_content(self, html_content: str) -> List[JobInfo]:
        """
        extract every job content from the html content
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        cards = soup.select('[data-at="job-item"]')

        if not cards:
            print("Not find job card（[data-at='job-item']), pls confirm whether HTML from IrishJobs.ie")
            return []

        jobs = []
        for card in cards:
            job = self._parse_card(card)
            if job:
                jobs.append(job)
        return jobs

    def _parse_card(self, card) -> Optional[JobInfo]:
        """parse every job card from job content"""
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
            print(f"Parsing failed: {e}")
            return None
    
    def parse_multiple_pages(self, file_pattern: str, page_range: range) -> List[JobInfo]:
        """
        Batch-process multiple pages.

        Args:
            file_pattern: File path pattern, e.g. "page_{page}.html"
            page_range: Range of page numbers, e.g. range(1, 8)

        Returns:
            A list containing all job records.
        """
        all_jobs = []
        
        for page in page_range:
            filename = file_pattern.format(page=page)
            file_path = self.html_data_dir / filename
            
            if file_path.exists():
                print(f"Start parsing {page} page...")
                jobs = self.parse_html_file(str(file_path))
                all_jobs.extend(jobs)
                print(f"Find {len(jobs)} jobs")
            else:
                print(f"File not exists: {file_path}")
        
        return all_jobs


    def print_stats(self, jobs: List[JobInfo]) -> None:
        if not jobs:
            print("No data")
            return
        
        print(f"\nTotal jobs number: {len(jobs)}")
        
        # 按公司统计
        company_counts = {}
        for job in jobs:
            company_counts[job.company] = company_counts.get(job.company, 0) + 1
        
        print("\nTOP 10 companies with most opening jobs:")
        for company, count in sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {company}: {count}")
        
        location_counts = {}
        for job in jobs:
            loc = job.location or "undefined"
            location_counts[loc] = location_counts.get(loc, 0) + 1
        
        print("\nTOP 10 location with most opening jobs:")
        for loc, count in sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {loc}: {count}")
        
        salary_known = sum(1 for job in jobs if job.salary and job.salary != "Not Disclosed")
        print(f"\nJobs with salary: {salary_known}/{len(jobs)}")


def main(start_page: int, end_page: int, html_data_dir: Path, data_dir: Path,
         filename: str, filename_added: str, is_total: bool) -> None:
    parser = IrishJobsLocalParser(html_data_dir, data_dir)

    jobs = parser.parse_multiple_pages(
        file_pattern="page_{page}.html",
        page_range=range(start_page, end_page + 1),
    )

    if not jobs:
        print("Could not extract any data!")
        return

    # parser.print_stats(jobs)

    columns = [f.name for f in dataclasses.fields(JobInfo)]
    save_path = data_dir / (filename if is_total else filename_added)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame([asdict(j) for j in jobs], columns=columns)
    df.to_csv(save_path, index=False, encoding="utf-8-sig")
    print(f"[INFO] Saved to: {save_path}")


if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    arg_parser = argparse.ArgumentParser(description="get jobs for start and end page in irishjobs platform")
    arg_parser.add_argument("--config", type=str,
                            default=str(PROJECT_ROOT / "config.yaml"))
    arg_parser.add_argument("--start_page", type=int, default=1)
    arg_parser.add_argument("--end_page", type=int, default=5)
    arg_parser.add_argument("--is_total", action="store_true", default=False)
    args = arg_parser.parse_args()

    cfg = load_config(args.config)
    config_dir = Path(args.config).resolve().parent

    def resolve_path(base: Path, p: str) -> Path:
        p = Path(p)
        return p if p.is_absolute() else (base / p).resolve()

    html_data_dir = resolve_path(config_dir, cfg["irishjobs_html_data_dir"])
    data_dir = resolve_path(config_dir, cfg["data_dir"])

    try:
        main(
            start_page=args.start_page,
            end_page=args.end_page,
            html_data_dir=html_data_dir,
            data_dir=data_dir,
            filename=cfg["irishjobs_filename"],
            filename_added=cfg["irishjobs_filename_added"],
            is_total=args.is_total,
        )
    finally:
        clear_folder_os(html_data_dir)