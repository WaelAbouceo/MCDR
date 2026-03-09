# MCDR Enhancements Checklist

Use this list to verify each enhancement one by one. Check off items as you test them.

---

## How to check if an enhancement is applied

You can verify in **two ways**:

1. **In the app (manual test)** — Follow the steps under each enhancement below; if the UI/behavior matches, it’s applied.
2. **In the code** — For each enhancement, the **“Code reference”** box lists files and what to look for. Open those files and confirm the mentioned strings or logic exist.

---

## Part 1: Non-AI Enhancements

### 1. Knowledge Base in Case Detail

- Open a case (e.g. from **Cases** → click a case).
- In the **right sidebar**, find the **Knowledge Base** panel (collapsible).
- Confirm **suggested articles** appear based on the case subject/category.
- Use the **search box** in the panel and click **Search** — results update without leaving the case.
- Expand an article to see full content; collapse with the header again.

**Location:** Case detail page → sidebar → "Knowledge Base" section.

<details>
<summary><strong>Code reference (click to see where to look)</strong></summary>

- **Frontend:** `frontend/src/pages/CaseDetail.jsx`  
  - Search for: `Knowledge Base`, `kbArticles`, `kbPanelOpen`, `loadKbSuggestions`, `searchKb`
- **API:** Existing `GET /api/cx/kb` and `GET /api/cx/kb/categories` (used by the panel)

If these exist, enhancement #1 is present.
</details>

---

### 2. Suggested Articles in Screen-Pop (Incoming Call)

- As **Supervisor** or **Admin**, go to **Simulate Call** and trigger an incoming call to an agent.
- As the **Agent**, accept the call so the screen-pop is visible.
- Scroll in the screen-pop and find **Suggested Articles** (if KB has articles for that call reason/category).
- Confirm **Open Knowledge Base →** link is present.

**Location:** Incoming call modal (after accept) → "Suggested Articles" block.

<details>
<summary><strong>Code reference</strong></summary>

- **Frontend:** `frontend/src/components/IncomingCall.jsx`  
  - Search for: `suggestedArticles`, `cx.kbArticles`, `Suggested Articles`, `BookOpen`

If these exist, enhancement #2 is present.
</details>

---

### 3. Case Duplicate Detection

- Go to **Create Case**.
- Enter an **Investor ID** that has recent cases (e.g. from an existing case).
- Enter a **Subject** that shares words with an existing case for that investor (e.g. "login issue").
- After a short delay, an **amber warning** appears: "Similar recent cases for this investor".
- Confirm similar case numbers are listed and **clicking one** opens that case.

**Location:** Create Case page → form with Investor ID + Subject filled.

<details>
<summary><strong>Code reference</strong></summary>

- **Backend:** `src/services/cx_data_service.py` — search for `check_duplicate_cases`
- **Backend:** `src/api/cases.py` — search for `check-duplicates`
- **Frontend:** `frontend/src/lib/api.js` — search for `checkDuplicates`
- **Frontend:** `frontend/src/pages/CreateCase.jsx` — search for `duplicateCases`, `checkDuplicates`, `Similar recent cases`

If these exist, enhancement #3 is present.
</details>

---

### 4. Auto-Escalation on SLA Breach

- **On case update:** Create or update a case so it **breaches** SLA (e.g. leave it open past first-response or resolution time), then update the case (e.g. add a note or change status). Check that the case is **auto-escalated** (status becomes "escalated" and an escalation record exists).
- **Periodic task:** Ensure **Celery** is running (worker + beat). After the beat interval (~2 min), open/in-progress cases that breach SLA should get escalation records. Check **Escalations** page or case detail.

**Location:** Backend: `_check_sla_and_auto_escalate()` after case update; Celery task `check_sla_breaches` in `src/tasks/sla_tasks.py`.

<details>
<summary><strong>Code reference</strong></summary>

- **Backend:** `src/services/cx_data_service.py` — search for `_check_sla_and_auto_escalate`, `check_sla_and_auto_escalate`, `list_case_ids_for_sla_check`
- **Backend:** `src/tasks/sla_tasks.py` — file exists with task `check_sla_breaches`
- **Backend:** `src/celery_app.py` — search for `sla_tasks`, `check_sla_breaches`, `beat_schedule`

If these exist, enhancement #4 is present.
</details>

---

### 5. Reports: Charts and PDF Export

- Go to **Reports** (Team Lead / Supervisor / Admin).
- Confirm **Case Volume Over Time** line chart is visible (Total, Resolved, Escalated).
- Confirm **SLA Compliance (Bar)** bar chart is visible.
- Click **Export CSV** — CSV downloads as before.
- Click **Export PDF** — a PDF downloads with KPIs, volume table, and SLA section.

**Location:** Reports page → charts at top; **Export CSV** and **Export PDF** buttons.

<details>
<summary><strong>Code reference</strong></summary>

- **Frontend:** `frontend/src/pages/Reports.jsx`  
  - Search for: `LineChart`, `BarChart`, `ResponsiveContainer`, `recharts`, `handleExportPdf`, `jsPDF`, `Export PDF`
- **Frontend:** `frontend/package.json` — should list `recharts` and `jspdf` in dependencies

If these exist, enhancement #5 is present.
</details>

---

### 6. Bulk Case Actions

- Log in as **Team Lead**, **Supervisor**, or **Admin**.
- Go to **Cases** (All Cases list).
- Confirm **checkboxes** on each row and a **header checkbox** for select-all.
- Select one or more cases.
- Confirm the **bulk action bar** appears (e.g. "X selected").
- **Change status:** Pick a status, click **Apply status** — selected cases update.
- **Change priority:** Pick a priority, click **Apply priority** — selected cases update.
- **Reassign:** Pick an agent from **Reassign to**, click **Reassign** — selected cases reassign.
- Use **Clear** to deselect all.

**Location:** Cases list (when not Agent view) → checkboxes + bulk bar when selection is not empty.

<details>
<summary><strong>Code reference</strong></summary>

- **Frontend:** `frontend/src/components/CaseTable.jsx` — search for `selectable`, `selectedIds`, `onToggleSelect`, `checkbox`
- **Frontend:** `frontend/src/pages/CaseList.jsx` — search for `selectedIds`, `applyBulkStatus`, `applyBulkPriority`, `applyBulkReassign`, `canBulk`
- **Frontend:** `frontend/src/lib/api.js` — search for `reassign` in cases object

If these exist, enhancement #6 is present.
</details>

---

## Part 2: AI Features

*Requires `OPENAI_API_KEY` in `.env` for LLM-based features. Rule-based and fallbacks work without it.*

### 7. Semantic Knowledge Base Search

- Set **OPENAI_API_KEY** in `.env`.
- As **Admin**, call **POST /api/ai/kb/embed-all** once (e.g. via Swagger at `/docs`) to build article embeddings.
- Go to **Knowledge Base**.
- Enter a search that uses **synonyms** (e.g. "forgot password" when articles say "password reset") — results should still be relevant (semantic search).
- If embeddings are missing or key is unset, search falls back to keyword search.

**Location:** Knowledge Base page → search box; backend `POST /api/ai/kb/semantic-search`.

<details>
<summary><strong>Code reference</strong></summary>

- **Backend:** `src/services/ai_service.py` — search for `semantic_kb_search`, `_get_embedding`, `store_article_embedding`
- **Backend:** `src/api/ai.py` — search for `kb/semantic-search`, `kb/embed-all`
- **Backend:** `db/init_cx.sql` — search for `kb_article_embeddings`
- **Frontend:** `frontend/src/pages/KnowledgeBase.jsx` — search for `aiApi.kbSemanticSearch`
- **Frontend:** `frontend/src/lib/api.js` — search for `aiApi`, `kbSemanticSearch`

If these exist, enhancement #7 is present.
</details>

---

### 8. Case Auto-Categorization (Suggested Category)

- Call **POST /api/ai/case/suggest-category** with body `{"subject": "...", "description": "..."}` (e.g. via Swagger).
- Response should suggest `taxonomy_id`, `category`, `subcategory` from case taxonomy.
- *(Optional)* Wire this in **Create Case** UI to pre-fill category/subcategory from subject/description.

**Location:** API only: `POST /api/ai/case/suggest-category`.

<details>
<summary><strong>Code reference</strong></summary>

- **Backend:** `src/services/ai_service.py` — search for `suggest_case_category`
- **Backend:** `src/api/ai.py` — search for `suggest-category`, `SuggestCategoryBody`

If these exist, enhancement #8 is present.
</details>

---

### 9. Suggested Resolution Code

- Call **POST /api/ai/case/suggest-resolution** with `subject`, `notes_text`, and optional `description`.
- Response should be one of the 8 resolution codes (e.g. `fixed`, `information_provided`).
- *(Optional)* Use in Case Detail when resolving to pre-select resolution code.

**Location:** API only: `POST /api/ai/case/suggest-resolution`.

<details>
<summary><strong>Code reference</strong></summary>

- **Backend:** `src/services/ai_service.py` — search for `suggest_resolution_code`
- **Backend:** `src/api/ai.py` — search for `suggest-resolution`, `SuggestResolutionBody`

If these exist, enhancement #9 is present.
</details>

---

### 10. AI-Assisted QA Scoring (Draft)

- Call **POST /api/ai/qa/suggest-draft** with `case_subject`, `case_description`, `notes_text`, `resolution_code`.
- Response should include `total_score` (0–100) and `feedback` text.
- *(Optional)* Use on QA Evaluations page to pre-fill score and feedback for the analyst to review.

**Location:** API only: `POST /api/ai/qa/suggest-draft`.

<details>
<summary><strong>Code reference</strong></summary>

- **Backend:** `src/services/ai_service.py` — search for `suggest_qa_draft`
- **Backend:** `src/api/ai.py` — search for `qa/suggest-draft`, `SuggestQABody`

If these exist, enhancement #10 is present.
</details>

---

### 11. Case Summarization

- Call **POST /api/ai/case/summarize** with `subject`, `description`, `notes_text`, `resolution_code`.
- Response should be a 2–3 sentence summary string.
- *(Optional)* Add a "Summarize" button on Case Detail that calls this and displays the result.

**Location:** API only: `POST /api/ai/case/summarize`.

<details>
<summary><strong>Code reference</strong></summary>

- **Backend:** `src/services/ai_service.py` — search for `summarize_case`
- **Backend:** `src/api/ai.py` — search for `case/summarize`, `SummarizeBody`

If these exist, enhancement #11 is present.
</details>

---

### 12. Next-Best-Action Suggestions (Agent Copilot)

- Call **GET /api/ai/case/{case_id}/next-actions** for an open case with an investor but no verification.
- Response should include a suggestion like "Verify caller identity — investor not verified yet."
- Try with a critical-priority case; suggestion may mention escalation.
- *(Optional)* Show these suggestions in Case Detail sidebar or a small "Suggestions" block.

**Location:** API only: `GET /api/ai/case/{case_id}/next-actions`. Rule-based; no API key needed.

<details>
<summary><strong>Code reference</strong></summary>

- **Backend:** `src/services/ai_service.py` — search for `next_best_actions`
- **Backend:** `src/api/ai.py` — search for `next-actions`

If these exist, enhancement #12 is present.
</details>

---

### 13. Sentiment Detection on Notes

- Call **POST /api/ai/note/sentiment** with body `{"content": "Customer was very frustrated with the delay."}`.
- Response should include `label` (e.g. `negative`) and `score`.
- *(Optional)* Call this when saving a note and store or display sentiment.

**Location:** API only: `POST /api/ai/note/sentiment`.

<details>
<summary><strong>Code reference</strong></summary>

- **Backend:** `src/services/ai_service.py` — search for `sentiment_note`
- **Backend:** `src/api/ai.py` — search for `note/sentiment`, `SentimentBody`

If these exist, enhancement #13 is present.
</details>

---

### 14. Predictive SLA Alerts (At-Risk Cases)

- Call **GET /api/ai/sla/at-risk** (e.g. as Team Lead / Supervisor / Admin).
- Response should list cases at risk of FRT or RT breach with `frt_breach_in_minutes` and/or `rt_breach_in_minutes`.
- *(Optional)* Add an "SLA at risk" widget on Dashboard or SLA page that calls this endpoint.

**Location:** API only: `GET /api/ai/sla/at-risk`. Heuristic-based; no API key needed.

<details>
<summary><strong>Code reference</strong></summary>

- **Backend:** `src/services/ai_service.py` — search for `predict_sla_at_risk`
- **Backend:** `src/api/ai.py` — search for `sla/at-risk`

If these exist, enhancement #14 is present.
</details>

---

## Quick verification (terminal)

From the project root you can quickly search for key implementation details. On Windows use Git Bash, or use your IDE’s global search (e.g. Ctrl+Shift+F) with the terms from the **Code reference** boxes above.

```bash
# Part 1 - Non-AI
grep -l "kbPanelOpen\|loadKbSuggestions" frontend/src/pages/CaseDetail.jsx
grep -l "suggestedArticles\|Suggested Articles" frontend/src/components/IncomingCall.jsx
grep -l "check_duplicate_cases\|check-duplicates" src/services/cx_data_service.py src/api/cases.py
grep -l "_check_sla_and_auto_escalate\|check_sla_breaches" src/services/cx_data_service.py src/tasks/sla_tasks.py
grep -l "LineChart\|handleExportPdf\|jsPDF" frontend/src/pages/Reports.jsx
grep -l "selectedIds\|applyBulkStatus\|canBulk" frontend/src/pages/CaseList.jsx

# Part 2 - AI
grep -l "semantic_kb_search\|suggest_case_category\|suggest_resolution_code\|suggest_qa_draft\|summarize_case\|next_best_actions\|sentiment_note\|predict_sla_at_risk" src/services/ai_service.py
grep -l "ai.router\|/ai/" src/api/router.py src/api/ai.py
```

If each command returns the expected file path(s), the corresponding enhancement is in the codebase.

---

## Quick Reference: API Endpoints


| Feature            | Method | Endpoint                              |
| ------------------ | ------ | ------------------------------------- |
| Semantic KB search | POST   | `/api/ai/kb/semantic-search`          |
| Embed all KB       | POST   | `/api/ai/kb/embed-all` (admin)        |
| Suggest category   | POST   | `/api/ai/case/suggest-category`       |
| Suggest resolution | POST   | `/api/ai/case/suggest-resolution`     |
| Summarize case     | POST   | `/api/ai/case/summarize`              |
| Next-best-actions  | GET    | `/api/ai/case/{case_id}/next-actions` |
| QA suggest draft   | POST   | `/api/ai/qa/suggest-draft`            |
| Note sentiment     | POST   | `/api/ai/note/sentiment`              |
| SLA at risk        | GET    | `/api/ai/sla/at-risk`                 |
| Check duplicates   | GET    | `/api/cases/check-duplicates`         |


---

## Notes

- **AI default:** AI is enabled by default (`AI_ENABLED=true` in `.env.example`). Set `OPENAI_API_KEY` to use LLM features; set `AI_ENABLED=false` to disable.
- **Roles:** Bulk actions and some report/charts are for Team Lead, Supervisor, Admin. Semantic search and most AI endpoints use Case Read or higher.
- **Celery:** For periodic SLA breach checks, run Celery worker and beat (see README or `src/celery_app.py`).

