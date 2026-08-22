from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import csv, argparse
import re,os,shutil
from bs4 import BeautifulSoup
from datetime import datetime
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


def clean_text(text: str) -> str:

    if not text:
        return ""

    return re.sub(r"\s+", " ", text).strip()


def _get_p_texts(card) -> list[str]:
    return [
        clean_text(p.get_text(" ", strip=True))
        for p in card.find_all("p")
        if p.get_text(strip=True)
    ]


def extract_job_id(card) -> str:
    """
    Extract job_id from componentkey.

    For example：
        componentkey="job-card-component-ref-4368310806"
    -> "4368310806"
    """
    ck = card.get("componentkey", "")
    match = re.search(r"job-card-component-ref-(\d+)", ck)
    return match.group(1) if match else ""


def extract_job_url(job_id: str) -> str:
    """
    Get LinkedIn job URL from job_id。
    """
    if not job_id:
        return ""
    return f"https://www.linkedin.com/jobs/view/{job_id}/"


def extract_title(card) -> str:
    """
    Extract title name.

    LinkedIn card structure：
        <p>
          <span>Title (Verified job)</span>   ← seen text
          <span aria-hidden="true">Title</span>  ← pure text
        </p>

    Using aria-hidden span to get title name end with "(Verified job)"；
    If failed, then fallback to the first <p> and manually solve。
    """
    p_tags = [p for p in card.find_all("p") if p.get_text(strip=True)]
    if not p_tags:
        return ""

    p0 = p_tags[0]

    hidden_span = p0.find("span", attrs={"aria-hidden": "true"})
    if hidden_span:
        text = clean_text(hidden_span.get_text(" ", strip=True))
        if text:
            return text

    first_span = p0.find("span")
    if first_span:
        text = clean_text(first_span.get_text(" ", strip=True))
        text = re.sub(r"\s*\(Verified job\)", "", text, flags=re.IGNORECASE)
        return text.strip()

    return clean_text(p0.get_text(" ", strip=True))


def extract_company(card) -> str:
    texts = _get_p_texts(card)
    return texts[1] if len(texts) >= 2 else ""


def extract_location(card) -> str:
    texts = _get_p_texts(card)
    return texts[2] if len(texts) >= 3 else ""


def extract_salary(card) -> str:
    # Range patterns must come before single-value patterns
    salary_patterns = [
        # e.g. "200K CAD/yr - 330K CAD/yr"  or  "200K CAD - 330K CAD"
        r"[\d,.]+\s?(?:K|k)?\s?(?:CAD|USD|EUR|GBP)(?:/yr|/year)?\s*(?:-|–|to)\s*[\d,.]+\s?(?:K|k)?\s?(?:CAD|USD|EUR|GBP)?(?:/yr|/year)?",
        # e.g. "$80K - $120K/yr"
        r"[$€£]\s?[\d,.]+(?:K|k)?\s?(?:-|–|to)\s?[$€£]?\s?[\d,.]+(?:K|k)?(?:/yr|/year)?",
        # e.g. "200K CAD/yr"
        r"[\d,.]+\s?(?:K|k)?\s?(?:CAD|USD|EUR|GBP)(?:/yr|/year)?",
        # e.g. "$80K/yr"
        r"[$€£]\s?[\d,.]+(?:K|k)?(?:/yr|/year)?",
    ]

    # Only scan the <p> tags (not the full card text) to avoid false positives
    for p in card.find_all("p"):
        text = clean_text(p.get_text(" ", strip=True))
        for pattern in salary_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0).strip()

    return ""


def extract_posted_date(card) -> str:
    """
    Extract the posted date (only take visible spans to avoid duplicates caused by aria-hidden).

    For example：
        Posted 10 hours ago
        Reposted 4 days ago
        1 week ago
    """
    patterns = [
        r"(?:Reposted|Posted)\s+\d+\s+(?:minute|minutes|hour|hours|day|days|week|weeks|month|months)\s+ago",
        r"\d+\s+(?:minute|minutes|hour|hours|day|days|week|weeks|month|months)\s+ago",
    ]

    for p in card.find_all("p"):
        first_span = p.find("span", attrs={"aria-hidden": lambda v: v is None})
        text = clean_text(
            first_span.get_text(" ", strip=True) if first_span
            else p.get_text(" ", strip=True)
        )
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(0)

    return ""


def find_job_cards(soup):
    """
    Find the job card based on the component key in the LinkedIn DOM.

    Current HTML includes：
        componentkey="job-card-component-ref-XXXXXXXXXX"

    So it does not rely on random CSS class。
    """

    cards = soup.find_all(
        attrs={
            "componentkey": re.compile(
                r"^job-card-component-ref-\d+$"
            )
        }
    )

    return cards


def parse_jobs(html_path: str) -> list[JobInfo]:

    html_path = Path(html_path)

    with html_path.open(
        "r",
        encoding="utf-8"
    ) as f:
        html = f.read()

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    cards = find_job_cards(soup)

    print(f"Find {len(cards)} job cards")

    jobs = []

    for card in cards:

        job_id = extract_job_id(card)

        job_url = extract_job_url(job_id)

        title = extract_title(card)

        company = extract_company(card).strip().lower()

        location = extract_location(card)

        salary = extract_salary(card)

        posted_date = extract_posted_date(card)

        scrape_date = datetime.now().strftime('%Y%m%d') 

        job = JobInfo(
            job_id=job_id,
            title=title,
            company=company,
            location=location,
            salary=salary,
            posted_date=posted_date,
            job_url=job_url,
            scrape_date=scrape_date
        )

        jobs.append(job)

    return jobs


def save_jobs_to_csv(
    jobs: list[JobInfo],
    output_path: str
):

    output_path = Path(output_path)

    fieldnames = [
        "job_id",
        "title",
        "company",
        "location",
        "salary",
        "posted_date",
        "job_url",
        "scrape_date",
        "recommend",
        "apply_date"
    ]

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for job in jobs:
            writer.writerow(asdict(job))

    print(
        f"Save {len(jobs)} jobs successfully to ："
        f"{output_path.resolve()}"
    )


if __name__ == "__main__":
      
      arg_parser = argparse.ArgumentParser(description='parse LinkedIn HTML data')
      arg_parser.add_argument('--start_page', type=int, default=1, help='start page with pattern page_{page}.html')
      arg_parser.add_argument('--end_page', type=int, default=2, help='end page(included)')
      arg_parser.add_argument('--html_data_dir', default='../linkedin_raw_data', help='HTML raw data path')
      arg_parser.add_argument('--data_dir', default='../', help='save path for results')
      arg_parser.add_argument('--filename', default='linkedin_data.csv', help='file name for first run with all data')
      arg_parser.add_argument('--filename_added', default='linkedin_data_added.csv', help='file name for increasal data')
      arg_parser.add_argument('--is_total', action='store_true', default=False, help='if all data (is_total=True), then use filename，otherwise use filename_added')
      args = arg_parser.parse_args()

      file_pattern="page_{page}.html"

      data_dir = Path(args.data_dir)
      html_data_dir = Path(args.html_data_dir)

      all_jobs = []
      for page in range(args.start_page, args.end_page+1):
            file_path = html_data_dir/file_pattern.format(page=page)
            if file_path.exists():
                  print(f"Is parsing {page} page...")
                  jobs = parse_jobs(str(file_path))
                  all_jobs.extend(jobs)
                  print(f"  Find {len(jobs)} jobs")
            else:
                  print(f"File path not exists: {file_path}")
      
      if args.is_total:
          save_jobs_to_csv(all_jobs, str(data_dir / args.filename))
      else:
          save_jobs_to_csv(all_jobs, str(data_dir / args.filename_added))
      print('All data saved locally！')

      # clean raw data file for next using
      clear_folder_os(args.html_data_dir)

