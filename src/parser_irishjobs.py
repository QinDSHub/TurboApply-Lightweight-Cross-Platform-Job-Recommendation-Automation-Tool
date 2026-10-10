from pathlib import Path
from typing import List, Optional
from dataclasses import asdict
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
from utils import clear_folder_os
from utils import load_config
import argparse, dataclasses
from utils import JobInfo
import logging

logger = logging.getLogger(__name__)

class IrishJobsLocalParser:    
    """Parse locally saved IrishJobs.ie HTML pages into structured job records.

    This parser reads HTML files from a local directory, extracts each job
    card's fields (title, origin_company, location, salary, posted date, URL, etc.),
    and returns them as ``JobInfo`` objects. It supports both single-file
    parsing and batch parsing across multiple pages.

    Attributes:
        html_data_dir (Path): Directory containing the local HTML files.
        data_dir (Path): Directory used for output data.
    """

    def __init__(self, html_data_dir: str, data_dir: str):
        """Initialize the parser with input and output directories.

        Args:
            html_data_dir (str): Directory containing the local HTML files.
                Created if it does not exist.
            data_dir (str): Directory for output data. Created if it does not exist.
        """

        self.html_data_dir = Path(html_data_dir)
        self.html_data_dir.mkdir(exist_ok=True)
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
    
    def parse_html_file(self, html_file_path: str) -> List[JobInfo]:
        """Parse one HTML file to extract job information.

        Args:
            html_file_path (str): Path to the HTML file to parse.

        Returns:
            List[JobInfo]: A list of parsed job records. Empty if no job cards are found.
        """

        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        return self.parse_html_content(html_content)
    
    def parse_html_content(self, html_content: str) -> List[JobInfo]:
        """Extract every job record from the given HTML content.

        Args:
            html_content (str): Raw HTML content of an IrishJobs.ie page.

        Returns:
            List[JobInfo]: A list of parsed job records. Empty if no job cards are found.
        """

        soup = BeautifulSoup(html_content, 'html.parser')
        cards = soup.select('[data-at="job-item"]')

        if not cards:
            logger.warning("Not find job card, pls confirm whether HTML from IrishJobs.ie")
            return []

        jobs = []
        for card in cards:
            job = self._parse_card(card)
            if job:
                jobs.append(job)
        return jobs

    def _parse_card(self, card) -> Optional[JobInfo]:
        """Parse a single job card into a ``JobInfo`` object.

        Args:
            card: A BeautifulSoup element representing one job card.

        Returns:
            Optional[JobInfo]: The parsed job record, or ``None`` if the card
            is missing a job ID or parsing fails.
        """

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
                origin_company=company,
                location=location,
                salary=salary,
                posted_date=posted_date,
                job_url=job_url,
                scrape_date = scrape_date
            )
        except Exception as e:
            logger.exception("Parsing failed!")
            return None
    
    def parse_multiple_pages(self, file_pattern: str, page_range: range) -> List[JobInfo]:
        """Batch-process multiple HTML pages.

        Args:
            file_pattern (str): File path pattern, e.g. ``"page_{page}.html"``.
            page_range (range): Range of page numbers, e.g. ``range(1, 8)``.

        Returns:
            List[JobInfo]: A list containing all job records from the parsed pages.
            Missing files are skipped with a warning.
        """

        all_jobs = []
        
        for page in page_range:
            filename = file_pattern.format(page=page)
            file_path = self.html_data_dir / filename
            
            if file_path.exists():
                logger.info("Parsing %d page...", page)
                jobs = self.parse_html_file(str(file_path))
                all_jobs.extend(jobs)
            else:
                logger.warning("File %s not exists!", file_path)
        
        return all_jobs

def main(start_page: int, end_page: int, html_data_dir: Path, data_dir: Path,
         filename: str, filename_added: str, is_total: bool) -> None:
    """Run the local IrishJobs parser and save the results as a CSV file.

    Parses HTML pages in the given range, converts the extracted ``JobInfo``
    records into a ``pandas.DataFrame``, and writes them to a CSV file under
    ``data_dir``.

    Args:
        start_page (int): First page number to parse (inclusive).
        end_page (int): Last page number to parse (inclusive).
        html_data_dir (Path): Directory containing the local HTML files.
        data_dir (Path): Directory where the output CSV will be saved.
        filename (str): Output CSV filename used when ``is_total`` is True.
        filename_added (str): Output CSV filename used when ``is_total`` is False.
        is_total (bool): If True, save as ``filename``; otherwise save as
            ``filename_added``.

    Returns:
        None: This function writes the CSV to disk and does not return a value.
    """
    
    parser = IrishJobsLocalParser(html_data_dir, data_dir)

    jobs = parser.parse_multiple_pages(
        file_pattern="page_{page}.html",
        page_range=range(start_page, end_page + 1),
    )

    if not jobs:
        logger.warning("NO DATA!")
        return

    columns = [f.name for f in dataclasses.fields(JobInfo)]
    save_path = data_dir / (filename if is_total else filename_added)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame([asdict(j) for j in jobs], columns=columns)
    df.to_csv(save_path, index=False, encoding="utf-8-sig")
    logger.info("Jobs saved at %s locally!", save_path)


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