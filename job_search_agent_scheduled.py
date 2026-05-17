#!/usr/bin/env python3
"""
JOB SEARCH AGENT v5.1 — Debug Version
Relaxed filters to see actual job results
"""

import os, re, json, hashlib, requests, csv, sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict

CONFIG = {
    "locations": ["Ohio, US", "Cincinnati, Ohio", "USA"],
    "search_remote": True,
    "date_posted": "today",
    "max_jobs_per_search": 15,
    "employment_types": "FULLTIME,CONTRACTOR,PARTTIME",
    "jsearch_api_key": os.environ.get("JSEARCH_API_KEY", ""),
    "hunter_api_key": os.environ.get("HUNTER_API_KEY", ""),
    "seen_jobs_db": "seen_jobs_scheduled.json",
    "output_csv": "jobs_scheduled.csv",
    "run_log": "run_log_scheduled.txt",
    "api_timeout": 15,
    "max_retries": 2,
}

JOB_ROLES = {
    "Full Stack Developer": {
        "queries": ["Full Stack Developer", "Full Stack Engineer"],
    },
    "Software Engineer": {
        "queries": ["Software Engineer", "Software Developer"],
    },
    "Data Engineer": {
        "queries": ["Data Engineer", "ETL Developer"],
    },
    "Data Analyst": {
        "queries": ["Data Analyst", "Business Analyst"],
    }
}

EXPERIENCE_LEVELS = {
    "New Grad": [
        r"\bnew\s*grad(?:uate)?\b", r"\brecent\s*grad(?:uate)?\b",
        r"\b0[\s-]*(?:to|-)[\s-]*1\s*year\b",
    ],
    "Entry Level (0-2 yrs)": [
        r"\bentry[- ]level\b", r"\bjunior\b",
        r"\b0[\s-]*(?:to|-)[\s-]*2\s*year\b", r"\b1[\s-]*(?:to|-)[\s-]*2\s*year\b",
    ],
    "2+ Years": [
        r"\b2\+\s*year\b", r"\b3\+\s*year\b", r"\b4\+\s*year\b",
    ]
}

TARGET_EXPERIENCE_LEVELS = ["New Grad", "Entry Level (0-2 yrs)", "2+ Years"]

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        with open(CONFIG["run_log"], "a") as f:
            f.write(line + "\n")
    except:
        pass

class SeenJobsDB:
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
        return {"jobs": {}, "total_processed": 0}

    def _save(self):
        try:
            with open(self.filepath, "w") as f:
                json.dump(self.db, f, indent=2)
        except:
            pass

    def _key(self, job):
        raw = f"{job.get('title','').lower().strip()}|{job.get('company','').lower().strip()}|{job.get('location','').lower().strip()}"
        return hashlib.md5(raw.encode()).hexdigest()

    def is_seen(self, job):
        return self._key(job) in self.db["jobs"]

    def mark_seen(self, job):
        k = self._key(job)
        self.db["jobs"][k] = {"title": job.get("title"), "company": job.get("company"), "location": job.get("location")}
        self.db["total_processed"] = len(self.db["jobs"])
        self._save()

    def total_seen(self):
        return len(self.db["jobs"])

def fetch_jobs(query: str, location: str, api_key: str) -> List[Dict]:
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "x-rapidapi-key": api_key,
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
        return []
    except Exception as e:
        log(f"[ERROR] API call failed: {str(e)[:80]}")
        return []

def parse_job(raw: Dict, role: str) -> Dict:
    desc = raw.get("job_description", "") or ""
    city = raw.get("job_city", "") or ""
    state = raw.get("job_state", "") or ""
    loc = f"{city}, {state}".strip(", ")
    
    return {
        "title": raw.get("job_title", ""),
        "company": raw.get("employer_name", ""),
        "location": loc,
        "remote": raw.get("job_is_remote", False),
        "employment_type": raw.get("job_employment_type", ""),
        "description": desc[:1000],
        "apply_link": raw.get("job_apply_link", ""),
        "source": raw.get("job_publisher", ""),
        "role": role,
        "experience_level": "",
        "date_added": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

def classify_experience(job: Dict) -> str:
    text = (job.get("title", "") + " " + job.get("description", "")).lower()
    for level, patterns in EXPERIENCE_LEVELS.items():
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                return level
    return "Not Specified"

def save_to_csv(jobs: List[Dict], filepath: str):
    if not jobs:
        return
    
    fieldnames = ["date_added", "role", "experience_level", "title", "company", "location", "remote", "apply_link", "source"]
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
    log("=" * 60)
    log("JOB SEARCH AGENT v5.1 — DEBUG MODE (RELAXED FILTERS)")
    log("=" * 60)
    
    if not CONFIG["jsearch_api_key"]:
        log("✗ ERROR: JSEARCH_API_KEY not set")
        sys.exit(1)
    
    seen_db = SeenJobsDB(CONFIG["seen_jobs_db"])
    log(f"Dedup DB: {seen_db.total_seen()} jobs already seen")
    
    all_new_jobs = []
    total_fetched = 0
    
    for role, role_info in JOB_ROLES.items():
        log(f"\n▶ Role: {role}")
        
        for location in CONFIG["locations"]:
            for query in role_info["queries"]:
                log(f"  Searching: '{query}' in {location}...")
                
                raw_jobs = fetch_jobs(query, location, CONFIG["jsearch_api_key"])
                total_fetched += len(raw_jobs)
                
                for raw in raw_jobs:
                    job = parse_job(raw, role)
                    
                    # Skip if already seen
                    if seen_db.is_seen(job):
                        continue
                    
                    # Classify experience level (NO FILTERING)
                    exp_level = classify_experience(job)
                    job["experience_level"] = exp_level
                    
                    # Mark as seen and add to results (RELAXED - NO VISA FILTER)
                    seen_db.mark_seen(job)
                    all_new_jobs.append(job)
                    
                    log(f"    ✓ {job['title'][:50]} @ {job['company']} ({exp_level})")
    
    log(f"\n{'=' * 60}")
    log(f"Total jobs fetched from API: {total_fetched}")
    log(f"Found {len(all_new_jobs)} new jobs (no experience filter)")
    
    if all_new_jobs:
        save_to_csv(all_new_jobs, CONFIG["output_csv"])
        log(f"✓ Saved to {CONFIG['output_csv']}")
    else:
        log("No new jobs found after deduplication")
    
    log("=" * 60)
    log("✓ Run Complete")
    log("=" * 60)

if __name__ == "__main__":
    try:
        scrape_jobs()
        sys.exit(0)
    except Exception as e:
        log(f"✗ Critical error: {e}")
        sys.exit(1)
