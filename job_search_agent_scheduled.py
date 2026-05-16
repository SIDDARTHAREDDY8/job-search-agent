#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║        JOB SEARCH AGENT v5.0 — GITHUB ACTIONS OPTIMIZED      ║
║        Single-run mode for GitHub Actions CI/CD              ║
║        Runs once per schedule (9 AM UTC daily)               ║
╠══════════════════════════════════════════════════════════════╣
║  Features:                                                   ║
║  ✓ Multi-board job search (JSearch API)                     ║
║  ✓ FILTERS: Entry Level / New Grad / 2+ Years              ║
║  ✓ ROLES: Full Stack Dev / Software Engineer / Data roles  ║
║  ✓ LOCATIONS: USA (Ohio, Cincinnati priority)              ║
║  ✓ DEDUPLICATION: Never processes same job twice           ║
║  ✓ CSV OUTPUT: All jobs saved to spreadsheet               ║
║  ✓ FAST EXECUTION: 10-minute timeout with proper exit      ║
╚══════════════════════════════════════════════════════════════╝

SETUP:
  1. JSEARCH_API_KEY   → https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
  2. HUNTER_API_KEY    → https://hunter.io (free: 25 searches/mo)
  3. Set environment variables
  4. Run: python3 job_search_agent_scheduled.py
"""

import os, re, json, hashlib, requests, csv, sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import signal

# ─────────────────────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────────────────────
CONFIG = {
    # ── Job Search Parameters ───────────────────────────────
    "locations": ["Ohio, US", "Cincinnati, Ohio", "USA"],
    "search_remote": True,
    "date_posted": "today",
    "max_jobs_per_search": 15,
    "employment_types": "FULLTIME,CONTRACTOR,PARTTIME",

    # ── API Keys ────────────────────────────────────────────
    "jsearch_api_key":  os.environ.get("JSEARCH_API_KEY", ""),
    "hunter_api_key":   os.environ.get("HUNTER_API_KEY", ""),

    # ── Output files ────────────────────────────────────────
    "seen_jobs_db":     "seen_jobs_scheduled.json",
    "output_csv":       "jobs_scheduled.csv",
    "run_log":          "run_log_scheduled.txt",
    
    # ── API Timeout (seconds) ──────────────────────────────
    "api_timeout": 15,
    "max_retries": 2,
}

# ─────────────────────────────────────────────────────────────
#  JOB ROLES & CATEGORIES
# ─────────────────────────────────────────────────────────────
JOB_ROLES = {
    "Full Stack Developer": {
        "queries": ["Full Stack Developer", "Full Stack Engineer", "Fullstack Developer"],
        "keywords": ["full stack", "fullstack", "full-stack"],
    },
    "Software Engineer": {
        "queries": ["Software Engineer", "Software Developer", "Backend Engineer"],
        "keywords": ["software engineer", "software developer", "backend"],
    },
    "Data Engineer": {
        "queries": ["Data Engineer", "ETL Developer", "Data Pipeline Engineer"],
        "keywords": ["data engineer", "etl", "data pipeline"],
    },
    "Data Analyst": {
        "queries": ["Data Analyst", "Business Analyst", "Analytics Engineer"],
        "keywords": ["data analyst", "business analyst", "analytics"],
    }
}

# ─────────────────────────────────────────────────────────────
#  VISA SPONSORSHIP & C2C PATTERNS
# ─────────────────────────────────────────────────────────────
VISA_SPONSORSHIP_KEYWORDS = [
    r"\bh-?1b\b", r"\bh1b\b", r"\bvisa\s*sponsor", r"\bsponsors?\s*visa",
    r"\bwork\s*visa\b", r"\bimmigration\s*sponsor", r"\bvisa\s*support",
    r"\bvisa\s*eligible\b", r"\bvisa\s*required\b", r"\bvisa\s*available\b",
    r"\bh-?1b\s*sponsor", r"\bh-?1b\s*eligible", r"\bh-?1b\s*available",
    r"\bwork\s*authorization\b", r"\bvisa\s*transfer\b", r"\bvisa\s*extension\b",
]

C2C_KEYWORDS = [
    r"\bc2c\b", r"\bcontract\s*to\s*hire\b", r"\bcontract-to-hire\b",
    r"\bcontractor\b", r"\bindependent\s*contractor\b", r"\b1099\b",
    r"\bcontract\s*position\b", r"\bcontract\s*role\b", r"\bw2\b",
    r"\bcontract\s*work\b", r"\btemporary\s*to\s*permanent\b",
]

# ─────────────────────────────────────────────────────────────
#  EXPERIENCE LEVEL PATTERNS
# ─────────────────────────────────────────────────────────────
EXPERIENCE_LEVELS = {
    "New Grad": [
        r"\bnew\s*grad(?:uate)?\b", r"\brecent\s*grad(?:uate)?\b",
        r"\b0[\s-]*(?:to|-)[\s-]*1\s*year\b", r"\bno\s*experience\s*required\b",
        r"\bfresh(?:er|man)?\b", r"\bgraduate\s*(?:hire|program)\b", r"\bcampus\s*hire\b",
    ],
    "Entry Level (0-2 yrs)": [
        r"\bentry[- ]level\b", r"\bjunior\b",
        r"\b0[\s-]*(?:to|-)[\s-]*2\s*year\b", r"\b1[\s-]*(?:to|-)[\s-]*2\s*year\b",
        r"\bup\s*to\s*2\s*year\b", r"\bless\s*than\s*2\s*year\b",
    ],
    "2+ Years": [
        r"\b2\+\s*year\b", r"\b3\+\s*year\b", r"\b4\+\s*year\b", r"\b5\+\s*year\b",
        r"\b2[\s-]*(?:to|-)[\s-]*(?:4|5|6|7|8)\s*year\b",
        r"\bmid[- ]level\b", r"\bintermediate\b",
    ]
}

TARGET_EXPERIENCE_LEVELS = ["New Grad", "Entry Level (0-2 yrs)", "2+ Years"]

# ─────────────────────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────────────────────
def log(msg):
    """Log to console and file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        with open(CONFIG["run_log"], "a") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"[WARNING] Could not write to log file: {e}")

# ─────────────────────────────────────────────────────────────
#  DEDUPLICATION DATABASE
# ─────────────────────────────────────────────────────────────
class SeenJobsDB:
    def __init__(self, filepath):
        self.filepath = filepath
        self.db = self._load()

    def _load(self):
        if Path(self.filepath).exists():
            try:
                with open(self.filepath) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"jobs": {}, "total_processed": 0}

    def _save(self):
        try:
            with open(self.filepath, "w") as f:
                json.dump(self.db, f, indent=2)
        except Exception as e:
            log(f"[WARNING] Could not save dedup DB: {e}")

    def _key(self, job):
        raw = f"{job.get('title','').lower().strip()}|{job.get('company','').lower().strip()}|{job.get('location','').lower().strip()}"
        return hashlib.md5(raw.encode()).hexdigest()

    def is_seen(self, job):
        return self._key(job) in self.db["jobs"]

    def mark_seen(self, job):
        k = self._key(job)
        self.db["jobs"][k] = {
            "title": job.get("title"), "company": job.get("company"),
            "location": job.get("location"),
            "first_seen": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "apply_link": job.get("apply_link", "")
        }
        self.db["total_processed"] = len(self.db["jobs"])
        self._save()

    def total_seen(self):
        return len(self.db["jobs"])

# ─────────────────────────────────────────────────────────────
#  FETCH JOBS FROM JSEARCH API (WITH TIMEOUT & RETRY)
# ─────────────────────────────────────────────────────────────
def fetch_jobs(query: str, location: str, api_key: str) -> List[Dict]:
    """Fetch jobs from JSearch API with timeout and retry logic."""
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
    
    for attempt in range(CONFIG["max_retries"]):
        try:
            response = requests.get(
                url, 
                headers=headers, 
                params=params,
                timeout=CONFIG["api_timeout"]  # 15-second timeout
            )
            
            if response.status_code == 200:
                return response.json().get("data", [])
            elif response.status_code == 429:  # Rate limited
                log(f"[RATE LIMIT] API rate limited. Skipping this search.")
                return []
            else:
                log(f"[ERROR] API returned {response.status_code}")
                return []
                
        except requests.Timeout:
            log(f"[TIMEOUT] API request timed out (attempt {attempt + 1}/{CONFIG['max_retries']})")
            if attempt < CONFIG["max_retries"] - 1:
                continue
            return []
        except Exception as e:
            log(f"[ERROR] Failed to fetch jobs: {str(e)[:100]}")
            return []
    
    return []

# ─────────────────────────────────────────────────────────────
#  PARSE JOB
# ─────────────────────────────────────────────────────────────
def parse_job(raw: Dict, role: str) -> Dict:
    """Parse raw job data from API."""
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
        "job_id": raw.get("job_id", ""),
        "title": raw.get("job_title", ""),
        "company": raw.get("employer_name", ""),
        "company_domain": raw.get("employer_website", "") or "",
        "location": loc,
        "remote": raw.get("job_is_remote", False),
        "employment_type": raw.get("job_employment_type", ""),
        "description": desc[:2000],
        "apply_link": raw.get("job_apply_link", ""),
        "posted_date": (raw.get("job_posted_at_datetime_utc") or "")[:10],
        "source": raw.get("job_publisher", ""),
        "salary": salary,
        "required_skills": ", ".join(raw.get("job_required_skills", []) or []),
        "role": role,
        "experience_level": "",
        "visa_sponsorship": "",
        "job_type": "",
        "status": "Found",
        "date_added": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

# ─────────────────────────────────────────────────────────────
#  CLASSIFY EXPERIENCE LEVEL
# ─────────────────────────────────────────────────────────────
def classify_experience(job: Dict) -> str:
    """Classify job experience level."""
    text = (job.get("title", "") + " " + job.get("description", "") + " " + job.get("required_skills", "")).lower()
    
    for level, patterns in EXPERIENCE_LEVELS.items():
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                return level
    return "Not Specified"

# ─────────────────────────────────────────────────────────────
#  CHECK VISA SPONSORSHIP
# ─────────────────────────────────────────────────────────────
def check_visa_sponsorship(job: Dict) -> str:
    """Check if job sponsors H-1B visa."""
    text = (job.get("title", "") + " " + job.get("description", "")).lower()
    
    for pattern in VISA_SPONSORSHIP_KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE):
            return "H-1B Sponsor"
    return ""

# ─────────────────────────────────────────────────────────────
#  CHECK JOB TYPE (C2C or Regular)
# ─────────────────────────────────────────────────────────────
def check_job_type(job: Dict) -> str:
    """Check if job is C2C (Contract-to-Hire) or W2."""
    text = (job.get("title", "") + " " + job.get("description", "") + " " + job.get("employment_type", "")).lower()
    
    for pattern in C2C_KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE):
            return "C2C/Contract"
    return "W2/Full-Time"

# ─────────────────────────────────────────────────────────────
#  SAVE TO CSV
# ─────────────────────────────────────────────────────────────
def save_to_csv(jobs: List[Dict], filepath: str):
    """Save jobs to CSV file."""
    if not jobs:
        return
    
    fieldnames = [
        "date_added", "role", "experience_level", "visa_sponsorship", "job_type",
        "title", "company", "location", "remote", "salary", "apply_link", "source", "status"
    ]
    
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

# ─────────────────────────────────────────────────────────────
#  MAIN JOB SCRAPING FUNCTION (ONE-TIME RUN)
# ─────────────────────────────────────────────────────────────
def scrape_jobs():
    """Main job scraping function - runs once per execution."""
    log("=" * 60)
    log("JOB SEARCH AGENT v5.0 — Single Run")
    log("=" * 60)
    
    # Validate API keys
    if not CONFIG["jsearch_api_key"]:
        log("✗ ERROR: JSEARCH_API_KEY not set. Exiting.")
        sys.exit(1)
    
    # Initialize dedup database
    seen_db = SeenJobsDB(CONFIG["seen_jobs_db"])
    log(f"Dedup DB: {seen_db.total_seen()} jobs already seen")
    
    all_new_jobs = []
    queries_attempted = 0
    
    # Search all role + location combinations
    for role, role_info in JOB_ROLES.items():
        log(f"\n▶ Role: {role}")
        
        for location in CONFIG["locations"]:
            for query in role_info["queries"]:
                queries_attempted += 1
                log(f"  [{queries_attempted}] Searching: '{query}' in {location}...")
                
                try:
                    raw_jobs = fetch_jobs(query, location, CONFIG["jsearch_api_key"])
                    
                    for raw in raw_jobs:
                        job = parse_job(raw, role)
                        
                        # Skip if already seen
                        if seen_db.is_seen(job):
                            continue
                        
                        # Classify experience level
                        exp_level = classify_experience(job)
                        job["experience_level"] = exp_level
                        
                        # Filter by target experience levels
                        if exp_level not in TARGET_EXPERIENCE_LEVELS:
                            continue
                        
                        # Check visa sponsorship and job type
                        visa_info = check_visa_sponsorship(job)
                        job_type = check_job_type(job)
                        job["visa_sponsorship"] = visa_info
                        job["job_type"] = job_type
                        
                        # FILTER: Only include jobs that sponsor H-1B OR are C2C
                        if not visa_info and job_type != "C2C/Contract":
                            continue
                        
                        # Mark as seen and add to results
                        seen_db.mark_seen(job)
                        all_new_jobs.append(job)
                        
                        log(f"    ✓ {job['title']} @ {job['company']} ({exp_level})")
                
                except Exception as e:
                    log(f"    ✗ Error processing this search: {str(e)[:80]}")
                    continue
    
    # Save results
    log(f"\n{'=' * 60}")
    if all_new_jobs:
        log(f"✓ Found {len(all_new_jobs)} new jobs")
        save_to_csv(all_new_jobs, CONFIG["output_csv"])
        log(f"✓ Saved to {CONFIG['output_csv']}")
        log(f"Total jobs in database: {seen_db.total_seen()}")
    else:
        log(f"✗ No new jobs found (Total in database: {seen_db.total_seen()})")
    
    log("=" * 60)
    log("✓ Run Complete - Script will exit")
    log("=" * 60)

# ─────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        scrape_jobs()
        log("✓ Job search agent finished successfully")
        sys.exit(0)  # Explicit exit
    except KeyboardInterrupt:
        log("⏹ Script interrupted by user")
        sys.exit(0)
    except Exception as e:
        log(f"✗ Critical error: {e}")
        sys.exit(1)
