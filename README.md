# 🤖 Job Search Agent - Automated Daily Scraper

Automatically scrapes jobs from 1000+ job boards daily. Filters for **H-1B visa sponsorship** and **C2C positions**. Runs on GitHub Actions (completely free, no computer needed).

## ✨ Features

- ✅ **Automatic Daily Runs** - Runs every day at 9 AM UTC
- ✅ **Multi-Board Search** - Searches 1000+ job boards (LinkedIn, Indeed, Glassdoor, etc.)
- ✅ **Smart Filtering** - Entry Level, New Grad, 2+ Years experience
- ✅ **H-1B & C2C Focus** - Only shows jobs that sponsor H-1B visas OR are C2C positions
- ✅ **4 Target Roles** - Full Stack Developer, Software Engineer, Data Engineer, Data Analyst
- ✅ **Geographic Focus** - USA (Ohio, Cincinnati priority)
- ✅ **Deduplication** - Never shows the same job twice
- ✅ **Zero Cost** - Runs on free GitHub Actions
- ✅ **No Computer Needed** - Runs 24/7 in the cloud

## 📊 What You Get

Every day, the agent:
1. Searches 1000+ job boards
2. Finds new jobs matching your criteria
3. Saves results to `jobs_scheduled.csv`
4. Commits results to GitHub
5. You can view/download anytime

## 🚀 Setup Instructions

### Step 1: Create GitHub Account (if you don't have one)
1. Go to https://github.com/signup
2. Create a free account
3. Verify your email

### Step 2: Create a New Repository
1. Go to https://github.com/new
2. Repository name: `job-search-agent`
3. Description: `Automated job scraper for H-1B and C2C positions`
4. Choose **Public** (so GitHub Actions works)
5. Click "Create repository"

### Step 3: Upload Files to GitHub
1. Clone the repository to your computer:
```bash
git clone https://github.com/YOUR_USERNAME/job-search-agent.git
cd job-search-agent
```

2. Copy these files into the folder:
   - `job_search_agent_scheduled.py` (the main agent)
   - `README.md` (this file)

3. Create `.github/workflows/` directory:
```bash
mkdir -p .github/workflows
```

4. Copy the workflow file:
   - Copy `job-search-workflow.yml` to `.github/workflows/job-search-workflow.yml`

5. Push to GitHub:
```bash
git add .
git commit -m "Initial commit: Job search agent setup"
git push origin main
```

### Step 4: Add API Keys (IMPORTANT!)
1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add these secrets:

**Secret 1:**
- Name: `JSEARCH_API_KEY`
- Value: ``

**Secret 2:**
- Name: `HUNTER_API_KEY`
- Value: ``

### Step 5: Enable GitHub Actions
1. Go to **Actions** tab in your repository
2. Click **I understand my workflows, go ahead and enable them**

### Step 6: Test the Agent
1. Go to **Actions** tab
2. Click **Job Search Agent - Daily Run**
3. Click **Run workflow** → **Run workflow**
4. Wait 2-3 minutes for it to complete
5. Check the results in the repository

---

## 📅 Automatic Schedule

The agent runs automatically:
- **Time:** 9 AM UTC every day
- **Frequency:** Once per day
- **No action needed:** Completely automated

To adjust the time, edit `.github/workflows/job-search-workflow.yml` and change the cron schedule.

---

## 📊 View Results

After each run:
1. Go to your repository
2. Look for these files:
   - `jobs_scheduled.csv` - All jobs found (open in Excel)
   - `run_log_scheduled.txt` - Detailed logs
   - `seen_jobs_scheduled.json` - Database of all jobs ever found

---

## 🔍 CSV Output Format

| Column | Description |
|--------|-------------|
| date_added | When the job was found |
| role | Job category (Full Stack Dev, etc.) |
| experience_level | Entry Level, New Grad, or 2+ Years |
| **visa_sponsorship** | "H-1B Sponsor" if detected |
| **job_type** | "C2C/Contract" or "W2/Full-Time" |
| title | Job title |
| company | Company name |
| location | City, State |
| remote | Is it remote? |
| salary | Salary range |
| apply_link | Direct link to apply |
| source | Which job board |
| status | Status (Found, Applied, etc.) |

---

## 🛠️ Troubleshooting

**Agent not running?**
- Check **Actions** tab for errors
- Make sure API keys are set in Secrets
- Check the workflow file is in `.github/workflows/`

**No jobs found?**
- Check it's between 9 AM - 5 PM (agent only runs during business hours)
- Verify API keys are correct
- Check `run_log_scheduled.txt` for error messages

**Want to run manually?**
- Go to **Actions** tab
- Click **Job Search Agent - Daily Run**
- Click **Run workflow**

---

## 📈 What Happens Next

1. **Day 1:** Agent finds initial jobs
2. **Day 2:** Finds new jobs (avoids duplicates)
3. **Day 3+:** Continuous daily updates
4. **Your CSV grows:** More and more jobs added over time

---

## 💡 Tips

- **Download CSV regularly:** Go to repository → click `jobs_scheduled.csv` → click "Download"
- **Share with others:** Your repository is public, anyone can see your job results
- **Customize:** Edit the agent to search different locations or roles
- **Export to Excel:** Download CSV and open in Excel for better viewing

---

## 🆘 Need Help?

If something isn't working:
1. Check the **Actions** tab for error messages
2. Review `run_log_scheduled.txt` for logs
3. Make sure API keys are set correctly in Secrets
4. Verify the workflow file is in `.github/workflows/`

---

## 📝 License

This project is open source. Feel free to modify and use as needed.

---

**Happy job hunting! 🎉**

Your agent is now running 24/7 in the cloud. No computer needed!
