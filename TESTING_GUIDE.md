# MCDR Frontend Testing Guide - New Features

## Overview
This guide will help you test three new features in the MCDR application:
1. **Outbound Queue** - Task management for outbound calls
2. **Reports** - Operations dashboard with KPIs and analytics
3. **Verification Wizard** - Identity verification workflow

---

## Prerequisites

### Backend Must Be Running
Ensure the backend API is running on port 8000:
```bash
# Check if backend is running
curl http://localhost:8000/api/health || echo "Backend not running!"
```

### Frontend Must Be Running
Ensure the frontend dev server is running on port 5173:
```bash
# Check if frontend is running
curl http://localhost:5173 || echo "Frontend not running!"
```

### Database Must Have Seed Data
The features require seed data to display properly. Verify data exists:
```bash
# Check if outbound tasks exist
sqlite3 db/cx.db "SELECT COUNT(*) FROM outbound_tasks;"

# Check if verification sessions exist
sqlite3 db/cx.db "SELECT COUNT(*) FROM verification_sessions;"
```

---

## Test Plan

### Step 1: Login as Admin

**URL:** http://localhost:5173/login

**Actions:**
1. Navigate to login page
2. Click the **"Admin"** demo user button (credentials: `admin1` / `admin123`)
3. Wait for redirect to dashboard

**Expected Results:**
- ✅ Login succeeds without errors
- ✅ Redirected to `/dashboard`
- ✅ Sidebar shows "Administrator" badge
- ✅ Sidebar includes "Outbound Queue" and "Reports" menu items

**Screenshot:** Take a screenshot of the dashboard after login

---

### Step 2: Test Outbound Queue

**URL:** http://localhost:5173/outbound

**Actions:**
1. Click **"Outbound Queue"** in the left sidebar navigation
2. Wait for page to load

**Expected Results:**

#### Stat Cards (Top of Page)
- ✅ **4 stat cards** displayed in a grid:
  - **Pending** - Shows count with blue clock icon
  - **In Progress** - Shows count with amber phone icon
  - **Completed Today** - Shows count with green checkmark icon
  - **Failed** - Shows count with red alert icon
- ✅ All counts should be **numbers** (0 or greater), not "undefined" or "null"

#### Task List
- ✅ **List of outbound tasks** displayed below stats
- ✅ Each task card shows:
  - **Task type badge** (e.g., "Broken Sign-up", "Inactive User", "Transaction Verification", "QA Callback")
  - **Priority badge** (Low/Medium/High/Critical with appropriate colors)
  - **Status badge** (Pending/In Progress/Completed/Failed)
  - **Investor name** (if linked) with user icon
  - **Agent name** (if assigned) showing "Agent: [name]"
  - **Task ID** in top-right corner (e.g., "#42")
- ✅ Task type badges have appropriate colors:
  - Broken Sign-up: amber/yellow
  - Inactive User: blue
  - Transaction Verification: purple
  - QA Callback: teal

#### Filters
- ✅ Filter dropdowns present:
  - "All Statuses" dropdown
  - "All Types" dropdown
- ✅ Task count displayed (e.g., "15 tasks")

#### Create Task Button
- ✅ "New Task" button in top-right corner

**Screenshot:** Take a screenshot showing:
- The 4 stat cards with numbers
- At least 2-3 task cards with visible badges and names

**Common Issues to Check:**
- ❌ Stat cards show "0" for all values → Backend not returning data
- ❌ Task list is empty → No seed data in `outbound_tasks` table
- ❌ Investor names missing → Join with registry database may be failing
- ❌ Agent names missing → Join with users table may be failing
- ❌ Console errors → Check browser console (F12)

---

### Step 3: Test Reports Page

**URL:** http://localhost:5173/reports

**Actions:**
1. Click **"Reports"** in the left sidebar navigation
2. Wait for page to load (may take 1-2 seconds for data aggregation)

**Expected Results:**

#### Page Header
- ✅ Title: "Operations Report" with bar chart icon
- ✅ Time period dropdown (default: "Last 7 days")
- ✅ "Export CSV" button

#### KPI Cards (Top Section)
- ✅ **6 KPI cards** displayed in a grid:
  1. **Total Cases** - Shows total count with indigo icon
  2. **FCR %** - First Contact Resolution percentage with green target icon
  3. **AHT (min)** - Average Handling Time with blue clock icon
  4. **Escalation Rate** - Percentage with yellow trending icon
  5. **Verification %** - Pass rate with purple shield icon
  6. **Verifications** - Total count with teal checkmark icon
- ✅ All values should be **numbers or percentages**, not "—" or "undefined"
- ✅ Percentages should have "%" symbol

#### Case Volume Table
- ✅ Section titled "Case Volume — Last 7 Days"
- ✅ Table with columns:
  - Date (in YYYY-MM-DD format)
  - Total (number)
  - Active (blue number)
  - Resolved (green number)
  - Escalated (amber number)
  - Distribution (progress bar)
- ✅ At least 1-7 rows of data (one per day)
- ✅ Progress bars show relative volume

#### SLA Compliance Section
- ✅ Section titled "SLA Compliance by Policy" with shield icon
- ✅ Shows compliance for different policies (e.g., "Standard", "VIP", "Critical")
- ✅ Each policy shows:
  - Policy name
  - Compliance percentage (color-coded: green ≥90%, amber ≥70%, red <70%)
  - Progress bar matching the color
  - Breach counts (FRT breaches, RT breaches)

#### Category Breakdown Section
- ✅ Section titled "Case Volume by Category"
- ✅ Shows categories like "Account Issue", "Transaction Query", etc.
- ✅ Each category shows:
  - Category name
  - Case count
  - Resolution percentage
  - Progress bar

#### Agent Performance Table
- ✅ Section titled "Agent Performance" with trending icon
- ✅ Table with columns:
  - # (rank)
  - Agent (name)
  - Cases (count)
  - Avg Resolution (min) - color-coded (green <60, red >60)
  - QA Score - color-coded (green ≥80, amber ≥60, red <60)
- ✅ Multiple agent rows with actual data

**Screenshot:** Take a screenshot showing:
- The 6 KPI cards with values
- The Case Volume table with data
- The SLA Compliance section
- The Agent Performance table

**Common Issues to Check:**
- ❌ All KPIs show "0" or "—" → Backend aggregation failing
- ❌ Case Volume table empty → No cases in date range
- ❌ SLA Compliance missing → No SLA policies or breaches tracked
- ❌ Agent Performance empty → No agent activity data
- ❌ Loading spinner never stops → API endpoint timeout or error
- ❌ Console errors → Check browser console (F12)

---

### Step 4: Test Verification Wizard on Case Detail

**URL:** http://localhost:5173/cases

**Actions:**
1. Click **"All Cases"** in the left sidebar
2. Click on the **first case** in the list to open case detail
3. Scroll down to the right sidebar

**Expected Results:**

#### Case Detail Page Loads
- ✅ Case details displayed (case number, subject, description)
- ✅ Tabs visible: Notes, History, Escalations, QA
- ✅ Right sidebar with sections

#### Verification Wizard Section (Right Sidebar)
- ✅ Section titled **"Identity Verification"** with lock or shield icon
- ✅ If verification not started:
  - **"Start Verification"** button visible
  - Button enabled if investor is linked to case
  - Button disabled with message if no investor linked
- ✅ If verification already exists for this case:
  - Shows verification status badge (pending/in_progress/passed/failed)
  - Shows progress bar
  - Shows investor name and code
  - Shows verification steps with icons:
    - Full Name (user icon)
    - National ID (credit card icon)
    - Mobile Number (phone icon)
    - Account Status (activity icon)
  - Each step shows Pass/Fail buttons if in progress
  - Completed steps show checkmark (passed) or X (failed)

**Screenshot:** Take a screenshot of the case detail page showing:
- The verification wizard section in the right sidebar
- Either the "Start Verification" button OR an active verification session with steps

**Common Issues to Check:**
- ❌ Verification section missing → Component not rendered
- ❌ "Start Verification" button always disabled → Investor not linked to case
- ❌ Steps not displaying → Backend not returning `steps_required` array
- ❌ Pass/Fail buttons not working → API endpoint failing
- ❌ Console errors → Check browser console (F12)

---

### Step 5: Test IncomingCall with Verification (Agent Role)

**URL:** http://localhost:5173/simulate

**Actions:**
1. Click **"Sign Out"** at the bottom of the sidebar
2. Return to login page
3. Login as **supervisor1** / **super123** (supervisors can simulate calls)
4. Click **"Simulate Call"** in the sidebar
5. Click the **"Simulate Incoming Call"** button (or similar button to trigger a call)
6. Wait for the incoming call modal/popup to appear

**Expected Results:**

#### Simulate Call Page
- ✅ Page loads with simulation controls
- ✅ Button to trigger incoming call visible
- ✅ Form fields for ANI (phone number), queue, etc.

#### Incoming Call Modal/Popup
- ✅ Modal appears with call details:
  - Caller phone number (ANI)
  - Queue name
  - Call reason
- ✅ **"Accept"** and **"Dismiss"** buttons visible
- ✅ Clicking "Accept" should:
  - Navigate to a case detail page OR
  - Open a case creation form with call details pre-filled
  - Show verification wizard if investor is identified

**Note:** The IncomingCall component is designed for agents, but supervisors can simulate calls. The actual incoming call polling happens for agents only.

**Screenshot:** Take a screenshot of:
- The simulate call page
- The incoming call modal (if it appears)

**Common Issues to Check:**
- ❌ No incoming call appears → Polling not working or no simulated call created
- ❌ Modal doesn't show verification option → Investor not identified from ANI
- ❌ Accept button doesn't work → Navigation or case creation failing
- ❌ Console errors → Check browser console (F12)

---

## Data Verification Queries

If features show empty data, run these SQL queries to verify seed data exists:

### Check Outbound Tasks
```sql
sqlite3 db/cx.db "
SELECT 
  task_id, 
  task_type, 
  status, 
  priority,
  investor_id,
  agent_id
FROM outbound_tasks 
LIMIT 5;
"
```

### Check Verification Sessions
```sql
sqlite3 db/cx.db "
SELECT 
  verification_id,
  investor_id,
  status,
  method,
  steps_required,
  steps_completed
FROM verification_sessions
LIMIT 5;
"
```

### Check Cases with Investors
```sql
sqlite3 db/cx.db "
SELECT 
  case_id,
  case_number,
  subject,
  investor_id,
  status
FROM cases
WHERE investor_id IS NOT NULL
LIMIT 5;
"
```

### Check Report Data (Last 7 Days)
```sql
sqlite3 db/cx.db "
SELECT 
  DATE(created_at) as day,
  COUNT(*) as total,
  SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active,
  SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolved
FROM cases
WHERE created_at >= DATE('now', '-7 days')
GROUP BY DATE(created_at)
ORDER BY day DESC;
"
```

---

## API Endpoint Testing

Test backend endpoints directly if frontend shows errors:

### Test Outbound Stats
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/outbound/stats
```

Expected response:
```json
{
  "by_status": {
    "pending": 10,
    "in_progress": 3,
    "completed": 25,
    "failed": 2
  },
  "by_type": {
    "broken_signup": 15,
    "inactive_user": 12,
    "transaction_verification": 8,
    "qa_callback": 5
  },
  "completed_today": 7
}
```

### Test Outbound Task List
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/outbound
```

Expected: Array of task objects with `task_id`, `task_type`, `status`, `investor_name`, `agent_name`, etc.

### Test Reports Overview
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/cx/reports/overview?days=7"
```

Expected response structure:
```json
{
  "kpis": {
    "fcr_pct": 85.5,
    "avg_handling_time_min": 12.3,
    "escalation_rate_pct": 8.2,
    "verification_pass_rate": 92.0,
    "verification_total": 150
  },
  "case_volume": [
    {"day": "2026-03-04", "total": 45, "active": 12, "resolved": 30, "escalated": 3}
  ],
  "sla_compliance": [
    {"policy_name": "Standard", "compliance_pct": 88, "total_cases": 100, "frt_breached": 8, "rt_breached": 4}
  ],
  "agent_performance": [
    {"agent_id": 1, "agent_name": "John Doe", "cases_handled": 25, "avg_resolution_min": 15, "avg_qa_score": 85}
  ],
  "category_breakdown": [
    {"category": "Account Issue", "cnt": 50, "resolved": 45}
  ]
}
```

### Test Verification for Case
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/verification/case/1
```

Expected: Verification session object or `{"verification_id": null, "status": "none"}`

---

## Troubleshooting

### Issue: Blank/Empty Pages
**Symptoms:** Page loads but shows no data, or shows "No items found" messages

**Solutions:**
1. Check browser console (F12) for JavaScript errors
2. Check Network tab (F12) to see if API calls are failing (look for 4xx/5xx status codes)
3. Verify backend is running: `curl http://localhost:8000/api/health`
4. Check if seed data exists using SQL queries above
5. Verify user has correct permissions (admin/supervisor roles needed for Reports)

### Issue: "Unauthorized" or "Session Expired"
**Symptoms:** Redirected to login, or API calls return 401 errors

**Solutions:**
1. Log out and log back in
2. Check if token is stored: Open DevTools → Application → Session Storage → `mcdr_token`
3. Verify backend authentication is working

### Issue: Stats Show All Zeros
**Symptoms:** Outbound Queue stats show 0/0/0/0, or Reports KPIs show 0%

**Solutions:**
1. Run seed script: `python seed_poc.py`
2. Check if data exists in database (use SQL queries above)
3. Check backend logs for aggregation errors
4. Verify date ranges (reports default to last 7 days)

### Issue: Verification Wizard Not Appearing
**Symptoms:** Case detail page doesn't show verification section

**Solutions:**
1. Verify user role is agent/supervisor/admin (not QA analyst)
2. Check if case has an investor linked (`investor_id` not null)
3. Verify `VerificationWizard` component is imported in `CaseDetail.jsx`
4. Check console for React component errors

### Issue: Task/Agent Names Missing
**Symptoms:** Outbound tasks show IDs but no names, or "—" for agent names

**Solutions:**
1. Check database joins between `cx.db` and `registry.db`
2. Verify `cx_data_service.py` includes proper LEFT JOINs for investor and agent names
3. Check if investor/user records exist in respective databases

---

## Success Criteria

### ✅ Outbound Queue - PASS
- [ ] Stat cards show non-zero counts
- [ ] Task list displays with type badges, priority, status
- [ ] Investor names and agent names visible
- [ ] Filters work (status, type)
- [ ] Can create new task
- [ ] Can pick up and complete tasks

### ✅ Reports - PASS
- [ ] All 6 KPI cards show values (not "—")
- [ ] Case Volume table has data rows
- [ ] SLA Compliance section shows policies with progress bars
- [ ] Agent Performance table lists agents with scores
- [ ] Export CSV button works
- [ ] Time period filter changes data

### ✅ Verification Wizard - PASS
- [ ] Appears on case detail page (right sidebar)
- [ ] "Start Verification" button works
- [ ] Shows investor name when linked
- [ ] Displays verification steps with icons
- [ ] Pass/Fail buttons update step status
- [ ] Progress bar updates as steps complete
- [ ] Final status shows "passed" or "failed"

---

## Test Results Template

Copy this template to record your test results:

```
# MCDR Frontend Testing Results
Date: [DATE]
Tester: [YOUR NAME]
Environment: localhost:5173

## Step 1: Login
- Status: [ ] PASS [ ] FAIL
- Notes: 
- Screenshot: [filename]

## Step 2: Outbound Queue
- Status: [ ] PASS [ ] FAIL
- Stat Cards: [ ] OK [ ] Missing Data
- Task List: [ ] OK [ ] Empty [ ] Missing Names
- Notes:
- Screenshot: [filename]

## Step 3: Reports
- Status: [ ] PASS [ ] FAIL
- KPI Cards: [ ] OK [ ] Zeros/Dashes
- Case Volume: [ ] OK [ ] Empty
- SLA Compliance: [ ] OK [ ] Missing
- Agent Performance: [ ] OK [ ] Empty
- Notes:
- Screenshot: [filename]

## Step 4: Verification Wizard
- Status: [ ] PASS [ ] FAIL
- Wizard Visible: [ ] YES [ ] NO
- Steps Display: [ ] OK [ ] Missing
- Buttons Work: [ ] YES [ ] NO
- Notes:
- Screenshot: [filename]

## Step 5: IncomingCall Simulation
- Status: [ ] PASS [ ] FAIL
- Call Triggered: [ ] YES [ ] NO
- Modal Appears: [ ] YES [ ] NO
- Notes:
- Screenshot: [filename]

## Overall Result
- [ ] ALL TESTS PASSED
- [ ] SOME TESTS FAILED (see notes)
- [ ] MAJOR ISSUES FOUND

## Issues Found
1. 
2. 
3. 

## Recommendations
1. 
2. 
3. 
```

---

## Additional Notes

### Browser Compatibility
Test in Chrome/Edge (Chromium-based browsers recommended). The app uses modern JavaScript features.

### Performance
- Reports page may take 1-2 seconds to load due to data aggregation
- Outbound Queue should load instantly if data is pre-seeded

### Mobile Responsiveness
The app is designed for desktop use. Mobile testing is not required for this POC.

---

## Contact

If you encounter issues not covered in this guide:
1. Check browser console (F12) for errors
2. Check backend logs (`uvicorn` terminal output)
3. Verify database schema matches expected structure
4. Review API endpoint responses using curl/Postman

Good luck with testing! 🚀
