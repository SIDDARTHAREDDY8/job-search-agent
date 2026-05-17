#!/usr/bin/env python3
"""
JOB SEARCH AGENT - Simplified Working Version
Creates jobs_scheduled.csv with all found jobs
"""

import os, re, json, hashlib, requests, csv, sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict

CONFIG = {
    "locations": ["Ohio, US", "Cincinnati, Ohio", "USA"],
    "date_posted": "today",
    "max_jobs_per_search": 15,
    "employment_types": "FULLTIME,CONTRACTOR,PARTTIME",
    "jsearch_api_key": os.environ.get("JSEARCH_API_KEY", ""),
    "hunter_api_key": os.environ.get("HUNTER_API_KEY", ""),
    "seen_jobs_db": "seen_jobs_scheduled.json",
    "output_csv": "jobs_scheduled.csv",
    "run_log": "run_log_scheduled.txt",
    "api_timeout": 15,
}

JOB_ROLES = {
    "Full Stack Developer": ["Full Stack Developer", "Full Stack Engineer"],
    "Software Engineer": ["Software Engineer", "Software Developer"],
    "Data Engineer": ["Data Engineer", "ETL Developer"],
    "Data Analyst": ["Data Analyst", "Business Analyst"],
}

EXPERIENCE_LEVELS = {
    "New Grad": [r"\bnew\s*grad", r"\b0[\s-]*(?:to|-)[\s-]*1\s*year"],
    "Entry Level": [r"\bentry[- ]level", r"\bjunior", r"\b0[\s-]*(?:to|-)[\s-]*2\s*year"],
    "2+ Years": [r"\b2\+\s*year", r"\b3\+\s*year", r"\bmid[- ]level"],
}

def log(msg):
    """Log to console and file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        with open(CONFIG["run_log"], "a") as f:
            f.write(line + "\n")
    except:
        pass

def log_inline(msg):
    """Log without newline"""
    print(msg, end="")

class SeenJobsDB:
    """Deduplication database"""
    def __init__(self, filepath):
        self.filepath = filepath
        self.db = self._load()

    def _load(self):
        if Path(self.filepath).exists():
            try:
                with open(self.filepath) as f:
                    return json.load(f)
            except:
                pass
        return {"jobs": {}}

    def _save(self):
        try:
            with open(self.filepath, "w") as f:
                json.dump(self.db, f, indent=2)
        except:
            pass

    def _key(self, job):
        raw = f"{job.get('title','').lower()}|{job.get('company','').lower()}|{job.get('location','').lower()}"
        return hashlib.md5(raw.encode()).hexdigest()

    def is_seen(self, job):
        return self._key(job) in self.db["jobs"]

    def mark_seen(self, job):
        k = self._key(job)
        self.db["jobs"][k] = {"title": job.get("title"), "company": job.get("company")}
        self._save()

    def total_seen(self):
        return len(self.db["jobs"])

def fetch_jobs(query: str, location: str) -> List[Dict]:
    """Fetch jobs from JSearch API"""
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "x-rapidapi-key": CONFIG["jsearch_api_key"],
        "x-rapidapi-host": "jsearch.p.rapidapi.com"
    }
    params = {
        "query": f"{query} in {location}",
        "date_posted": CONFIG["date_posted"],
        "employment_types": CONFIG["employment_types"],
        "page": 1,
        "num_pages": 1,
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=CONFIG["api_timeout"])
        if response.status_code == 200:
            return response.json().get("data", [])
    except Exception as e:
        log(f"  [ERROR] API failed: {str(e)[:60]}")
    return []

def parse_job(raw: Dict, role: str) -> Dict:
    """Parse raw job data from API"""
    desc = raw.get("job_description", "") or ""
    city = raw.get("job_city", "") or ""
    state = raw.get("job_state", "") or ""
    loc = f"{city}, {state}".strip(", ")
    
    sal_min = raw.get("job_min_salary")
    sal_max = raw.get("job_max_salary")
    salary = ""
    if sal_min and sal_max:
        salary = f"${int(sal_min):,} – ${int(sal_max):,}"
    elif sal_min:
        salary = f"${int(sal_min):,}+"
    
    return {
        "date_added": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "title": raw.get("job_title", ""),
        "company": raw.get("employer_name", ""),
        "location": loc,
        "remote": raw.get("job_is_remote", False),
        "employment_type": raw.get("job_employment_type", ""),
        "description": desc[:1000],
        "apply_link": raw.get("job_apply_link", ""),
        "source": raw.get("job_publisher", ""),
        "salary": salary,
        "role": role,
        "experience_level": "",
    }

def classify_experience(job: Dict) -> str:
    """Classify job experience level"""
    text = (job.get("title", "") + " " + job.get("description", "")).lower()
    for level, patterns in EXPERIENCE_LEVELS.items():
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                return level
    return "Not Specified"

def save_to_csv(jobs: List[Dict], filepath: str):
    """Save jobs to CSV file"""
    if not jobs:
        return
    
    fieldnames = ["date_added", "role", "experience_level", "title", "company", "location", "remote", "salary", "apply_link", "source"]
    file_exists = Path(filepath).exists()
    
    try:
        with open(filepath, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            for job in jobs:
                writer.writerow({k: job.get(k, "") for k in fieldnames})
    except Exception as e:
        log(f"[ERROR] Failed to save CSV: {e}")

def scrape_jobs():
    """Main job scraping function"""
    log("=" * 70)
    log("JOB SEARCH AGENT - Starting Scrape")
    log("=" * 70)
    
    if not CONFIG["jsearch_api_key"]:
        log("✗ ERROR: JSEARCH_API_KEY not set")
        sys.exit(1)
    
    seen_db = SeenJobsDB(CONFIG["seen_jobs_db"])
    log(f"Previously seen jobs: {seen_db.total_seen()}")
    
    all_new_jobs = []
    total_api_results = 0
    
    for role, queries in JOB_ROLES.items():
        log(f"\n▶ Role: {role}")
        
        for location in CONFIG["locations"]:
            for query in queries:
                log(f"  Searching: '{query}' in {location}...")
                
                raw_jobs = fetch_jobs(query, location)
                total_api_results += len(raw_jobs)
                
                for raw in raw_jobs:
                    job = parse_job(raw, role)
                    
                    if seen_db.is_seen(job):
                        continue
                    
                    exp_level = classify_experience(job)
                    job["experience_level"] = exp_level
                    
                    seen_db.mark_seen(job)
                    all_new_jobs.append(job)
                
                log(f"    Found {len(raw_jobs)} jobs ({len([j for j in all_new_jobs if j['role'] == role])} new)")
    
    log(f"\n{'=' * 70}")
    log(f"Total API results: {total_api_results}")
    log(f"New jobs found: {len(all_new_jobs)}")
    
    if all_new_jobs:
        save_to_csv(all_new_jobs, CONFIG["output_csv"])
        log(f"✓ Saved {len(all_new_jobs)} jobs to {CONFIG['output_csv']}")
    else:
        log("No new jobs to save")
    
    log(f"Total jobs in database: {seen_db.total_seen()}")
    log("=" * 70)
    log("✓ Run Complete")
    log("=" * 70)

if __name__ == "__main__":
    try:
        scrape_jobs()
        sys.exit(0)
    except Exception as e:
        log(f"✗ Error: {e}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)
