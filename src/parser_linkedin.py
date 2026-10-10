from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import csv, argparse, re
from bs4 import BeautifulSoup
from utils import JobInfo
from utils import clear_folder_os, load_config
import dataclasses
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Normalize whitespace in a string.

    Collapses consecutive whitespace characters into a single space and
    strips leading/trailing whitespace.

    Args:
        text (str): The input string to clean.

    Returns:
        str: The cleaned string. Returns an empty string if ``text`` is falsy.
    """

    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def _get_p_texts(card) -> list[str]:
    """Collect cleaned text from all non-empty ``<p>`` tags in a job card.

    Args:
        card: A BeautifulSoup element representing one job card.

    Returns:
        list[str]: Cleaned text of each non-empty ``<p>`` tag, in document order.
    """

    return [
        clean_text(p.get_text(" ", strip=True))
        for p in card.find_all("p")
        if p.get_text(strip=True)
    ]


def extract_job_id(card) -> str:
    """Extract the job ID from the card's ``componentkey`` attribute.

    For example::

        componentkey="job-card-component-ref-4368310806"
        -> "4368310806"

    Args:
        card: A BeautifulSoup element representing one job card.

    Returns:
        str: The extracted numeric job ID, or an empty string if not found.
    """

    ck = card.get("componentkey", "")
    match = re.search(r"job-card-component-ref-(\d+)", ck)
    return match.group(1) if match else ""


def extract_job_url(job_id: str) -> str:
    """Build the LinkedIn job URL from a job ID.

    Args:
        job_id (str): The numeric job ID.

    Returns:
        str: The full LinkedIn job URL, or an empty string if ``job_id`` is empty.
    """

    if not job_id:
        return ""
    return f"https://www.linkedin.com/jobs/view/{job_id}/"


def extract_title(card) -> str:
    """Extract the job title from a LinkedIn job card.

    LinkedIn card structure::

        <p>
          <span>Title (Verified job)</span>     ← seen text
          <span aria-hidden="true">Title</span>  ← pure text
        </p>

    Uses the ``aria-hidden`` span to get the title without the "(Verified job)"
    suffix. If that fails, falls back to the first ``<p>`` and removes the
    suffix manually.

    Args:
        card: A BeautifulSoup element representing one job card.

    Returns:
        str: The cleaned job title, or an empty string if not found.
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
    """Extract the origin company name from a job card.

    The origin company name is taken from the second non-empty ``<p>`` tag.

    Args:
        card: A BeautifulSoup element representing one job card.

    Returns:
        str: The origin company name, or an empty string if not available.
    """

    texts = _get_p_texts(card)
    return texts[1] if len(texts) >= 2 else ""


def extract_location(card) -> str:
    """Extract the job location from a job card.

    The location is taken from the third non-empty ``<p>`` tag.

    Args:
        card: A BeautifulSoup element representing one job card.

    Returns:
        str: The job location, or an empty string if not available.
    """

    texts = _get_p_texts(card)
    return texts[2] if len(texts) >= 3 else ""


def extract_salary(card) -> str:
    """Extract the salary text from a job card.

    Scans only ``<p>`` tags (not the full card text) to avoid false positives.
    Range patterns are matched before single-value patterns so that full ranges
    like ``"$80K - $120K/yr"`` are returned intact.

    Args:
        card: A BeautifulSoup element representing one job card.

    Returns:
        str: The matched salary string, or an empty string if no pattern matches.
    """

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
    """Extract the posted date text from a job card.

    Only visible spans are scanned to avoid duplicates caused by ``aria-hidden``
    elements. Example outputs::

        Posted 10 hours ago
        Reposted 4 days ago
        1 week ago

    Args:
        card: A BeautifulSoup element representing one job card.

    Returns:
        str: The matched posted-date string, or an empty string if not found.
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
    """Find all job cards in the LinkedIn DOM.

    Cards are located by the ``componentkey`` attribute, which currently looks
    like ``componentkey="job-card-component-ref-XXXXXXXXXX"``. This avoids
    relying on random CSS class names.

    Args:
        soup: A BeautifulSoup document object.

    Returns:
        list: A list of BeautifulSoup elements matching the job-card pattern.
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
    """Parse a LinkedIn HTML file and extract all job records.

    Reads the HTML file, locates all job cards, extracts each field (job ID,
    URL, title, origin_company, location, salary, posted date), and returns a list of
    ``JobInfo`` objects.

    Args:
        html_path (str): Path to the LinkedIn HTML file to parse.

    Returns:
        list[JobInfo]: A list of parsed job records, one per job card.
    """

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
    logger.info("Find %d job cards!",len(cards))

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
            origin_company=company,
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
    output_path: str):
    """Save a list of job records to a CSV file.

    Writes a header row followed by one row per ``JobInfo`` object, using the
    dataclass field names as column names. The file is written with
    ``utf-8-sig`` encoding so it opens correctly in Excel.

    Args:
        jobs (list[JobInfo]): The job records to save.
        output_path (str): Path where the CSV file will be written.

    Returns:
        None: This function writes the file to disk and does not return a value.
    """

    output_path = Path(output_path)

    fieldnames = [f.name for f in dataclasses.fields(JobInfo)]
        
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

    logger.info("save %d jobs successfully to %s", len(jobs), output_path.resolve())


if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    arg_parser = argparse.ArgumentParser(description="parse LinkedIn HTML data")
    arg_parser.add_argument("--config", type=str,
                            default=str(PROJECT_ROOT / "config.yaml"),
                            help="Path to the YAML config file")
    arg_parser.add_argument("--start_page", type=int, default=1,
                            help="start page with pattern page_{page}.html")
    arg_parser.add_argument("--end_page", type=int, default=2,
                            help="end page (included)")
    arg_parser.add_argument("--is_total", action="store_true", default=False,
                            help="if all data (is_total=True), use filename; otherwise use filename_added")
    args = arg_parser.parse_args()

    cfg = load_config(args.config)
    config_dir = Path(args.config).resolve().parent

    def resolve_path(base: Path, p) -> Path:
        p = Path(p)
        return p if p.is_absolute() else (base / p).resolve()

    html_data_dir = resolve_path(config_dir, cfg["linkedin_html_data_dir"])
    data_dir      = resolve_path(config_dir, cfg["data_dir"])

    file_pattern = "page_{page}.html"

    all_jobs = []
    for page in range(args.start_page, args.end_page + 1):
        file_path = html_data_dir / file_pattern.format(page=page)
        if file_path.exists():
            logger.info("Parsing page %d ...", page)
            jobs = parse_jobs(str(file_path))
            all_jobs.extend(jobs)
        else:
            logger.warning("File not found %s", file_path)

    if args.is_total:
        output_name = cfg["linkedin_filename"]
    else:
        output_name = cfg["linkedin_filename_added"]

    save_jobs_to_csv(all_jobs, data_dir / output_name)
    logger.info("All jobs %d saved locally!",len(all_jobs))

    clear_folder_os(html_data_dir)