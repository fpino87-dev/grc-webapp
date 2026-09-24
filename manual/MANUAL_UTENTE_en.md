# User Manual — govrico

> Guide for end users: Compliance Officer, Risk Manager, Plant Manager, Plant Security Officer, External Auditor.

---

## Table of Contents

- [1. Access and Navigation](#1-access-and-navigation)
- [2. Dashboard](#2-dashboard)
- [3. Controls Management (M03)](#3-controls-management-m03)
- [4. IT and OT Assets (M04)](#4-it-and-ot-assets-m04)
- [5. Business Impact Analysis (M05)](#5-business-impact-analysis-m05)
- [6. Risk Assessment (M06)](#6-risk-assessment-m06)
- [7. Documents and Evidence (M07)](#7-documents-and-evidence-m07)
- [8. Incident Management (M09)](#8-incident-management-m09)
- [9. PDCA (M11)](#9-pdca-m11)
- [10. Lesson Learned (M12)](#10-lesson-learned-m12)
- [11. Management Review (M13)](#11-management-review-m13)
- [12. Audit Preparation (M17)](#12-audit-preparation-m17)
- [13. Suppliers (M14)](#13-suppliers-m14)
- [14. Training (M15)](#14-training-m15)
- [15. Business Continuity (M16)](#15-business-continuity-m16)
- [16. Activity Schedule](#16-activity-schedule)
- [17. Mandatory Documents](#17-mandatory-documents)
- [18. Email Notifications](#18-email-notifications)
- [19. Governance (M00)](#19-governance-m00)
- [20. Settings (Admin only)](#20-settings-admin-only)
- [Roles and what you can do](#roles-and-what-you-can-do)
- [AI Engine — AI suggestions (M20)](#ai-engine--ai-suggestions-m20)
- [Reporting and export (M18)](#reporting-and-export-m18)
- [Operations Cockpit (M21)](#operations-cockpit-m21)
- [OSINT Monitor](#osint-monitor)
- [Appendix: Frequently Asked Questions](#appendix-frequently-asked-questions)

---

## 1. Access and Navigation

### Login with email and password

[Screenshot: login page]

1. Open your browser and go to `https://grc.azienda.com`
2. Enter your **corporate email** in the first field
3. Enter your **password** in the second field (minimum 12 characters)
4. Click **Sign in**
5. On first login you will be prompted to change the temporary password received by email

If you use corporate SSO, click **Sign in with corporate account** instead and enter your domain account credentials.

> The session remains active for 30 minutes of inactivity. After expiry you are asked to re-enter your password. The session token renews automatically during active use.

To reset your password: from the login page click **Forgot password** and enter your email. You will receive a link valid for 15 minutes.

### Site (plant) selection in the top left

[Screenshot: plant selector in topbar]

Immediately after login, in the top left next to the logo, you will find the **plant selector**. If you have access to multiple sites or business units:

1. Click on the current plant name (or on "Select plant" on first login)
2. A dropdown menu appears with all plants in your scope
3. Click on the plant you want to view — the page updates immediately

The **All plants** option shows an aggregated view of all sites. This option is available only to Compliance Officers and roles with multi-plant access.

All operations (asset creation, incident opening, control assessments) are associated with the plant selected at that moment.

### Language switch (IT/EN) in the top right

[Screenshot: language menu in topbar]

1. Click on the language icon (or on the current language code) in the top right
2. Select the desired language: **Italiano**, **English**, **Français**, **Polski**, **Türkçe**
3. The interface updates immediately without reloading the page

The selected language applies to the entire interface. The reports and exports generated use the language active at the time of generation.

### Side menu: main sections and what they contain

[Screenshot: sidebar with expanded menu]

The left sidebar shows only the sections accessible based on your role. The main entries are:

| Group | Entries |
|--------|------|
| **Main** | Dashboard · Operations Center (M21)¹ · Reporting (M18) · Operational KPIs · Tasks (M08) · Checklists |
| **Compliance** | Controls (M03) · Gap Analysis · Documents (M07) · Audit Prep (M17) |
| **Risk & continuity** | BIA (M05) · Risk (M06) · IT/OT Assets (M04) · BCP (M16) |
| **Operations** | Incidents (M09) · Lessons (M12) · Suppliers (M14) · Training (M15) · PDCA (M11) |
| **Planning** | Activity Schedule · Required Docs · Due date policy² · Checklist Templates³ |
| **Organization & review** | Governance (M00) · Security objectives · Management Review (M13)⁴ · Sites (M01)² · Users (M02)⁵ · Competency⁶ · Audit Trail (M10)⁷ · MFA Authentication |
| **Security**⁸ | OSINT Monitor |
| **Settings**⁵ | Email settings · Notification rules · Govrico AI · Backup & Restore |

Entries restricted to some roles:

1. Super Admin, Compliance Officer, Risk Manager, Internal Auditor, Plant Manager
2. Super Admin, Compliance Officer
3. Super Admin, Compliance Officer, CISO, Risk Manager
4. Super Admin, Compliance Officer, Risk Manager
5. Super Admin
6. Super Admin, Compliance Officer, CISO
7. Super Admin, Internal Auditor, External Auditor
8. Super Admin, CISO, Compliance Officer

The **«** button at the top shrinks the menu to icons only (hover over an icon to see the entry name) and **»** expands it again. Your choice is remembered between sessions.

### ? icon on every page for contextual help

[Screenshot: ? button next to the page title]

On almost every operational page you will find a small **`?`** button near the module title. Clicking it opens a side panel with:

- A brief explanation of what the module does
- The typical steps to follow
- Connections with other modules (e.g. which tasks or PDCAs are created automatically)
- A list of recommended prerequisites ("Before you start")

Use the help panel to orient yourself on modules you use less frequently or when introducing the system to new colleagues.

### User Manual and Technical Manual buttons in the bottom bar

[Screenshot: bottom bar with manual buttons]

At the bottom of every page, in the bottom bar, you will find two fixed buttons:

- **User Manual** (book icon): opens this manual in a new tab
- **Technical Manual** (wrench icon): opens the technical manual with architectural details, visible only to profiles with administrative access

Both buttons are always visible regardless of which module you are in.

---

## 2. Dashboard

[Screenshot: main dashboard]

The dashboard is the first page you see after login. The content is customised for your role and the selected plant.

### What the main KPIs show

At the top of the dashboard you will find 4 panels with the main KPIs:

| KPI | What it measures |
|-----|-----------------|
| **Compliance %** | Percentage of controls in "compliant" or "partial with valid evidence" status relative to the total active controls for the selected framework |
| **Open risks** | Number of risk assessments with "open" status (not accepted and not closed). The number is accompanied by the count of critical risks (score > 14) in red |
| **Incidents** | Open incidents in the selected plant. Numbers in red indicate incidents with active NIS2 timers |
| **Overdue tasks** | Tasks assigned to your role (or to your entire organisation if you are CO) with a due date already past |

### How to interpret the colours

The platform uses a consistent colour convention throughout the interface:

- **Green**: everything in order — compliant, completed, valid, on time
- **Yellow**: attention required — partial, expiring within 30 days, in progress
- **Red**: critical — gap, overdue, high risk (score > 14), NIS2 timer expiring
- **Grey**: not assessed, N/A, archived
- **Orange**: alert or warning — requires attention but is not yet critical

These colours apply to status badges, progress bars, heat map indicators and sidebar icons.

### Upcoming deadlines widget

[Screenshot: deadlines widget on dashboard]

The "Upcoming deadlines" widget shows the first 10 deadlines in the next 30 days. For each deadline you see:

- The type (document, evidence, task, supplier assessment, etc.)
- The name of the item
- The due date with yellow colour (< 30 days) or red (< 7 days)

Clicking on a deadline takes you directly to the page of the relevant item.

### Vacant role alerts

If there are mandatory regulatory roles without an assigned holder (e.g. CISO not appointed, DPO vacant), an orange "Vacant roles" banner appears on the dashboard with the count and a link to the governance page (M00). These alerts negatively impact the compliance KPI.

### How to navigate directly to an item from the dashboard

Every interactive element on the dashboard is clickable:

- Click on an overdue task to open the task record
- Click on a heat map quadrant to see the risks in that zone
- Click on a compliance bar to go to the controls library filtered by that framework
- Click on an incident to open the incident record

---

## 3. Controls Management (M03)

[Screenshot: controls library]

### How to assess a control

1. Go to **Compliance → Controls library**
2. Use the filters (framework, domain, status, plant) to find the control you are looking for
3. Click on the control name to open the record
4. In the **Status** field click to open the selector and choose the appropriate status
5. Add a context note in the **Assessment notes** field (mandatory for Gap and N/A)
6. Link the evidence via the **Attach evidence** button
7. Click **Save**

### Difference between Compliant, Partial, Gap, N/A

| Status | When to use it |
|--------|---------------|
| **Compliant** | The control is fully satisfied. You have valid, non-expired evidence demonstrating this |
| **Partial** | The control is only partially implemented. There is a plan to complete it but not all requirements are yet met |
| **Gap** | The control is not implemented. A corrective action is required. Automatically generates a task |
| **N/A** | The control does not apply to your plant's context. Requires a written justification of at least 20 characters. The justification is saved and visible whenever you reopen the control. In the VDA ISA TISAX it appears in the "Note / Justification" column and the maturity level is set to 0. For TISAX L3 it requires the signature of two roles and expires after 12 months |

> A control with expired evidence automatically reverts to "Partial" even if you set it as Compliant. Keep your evidence up to date.

### How to upload evidence

1. From the control record click **Attach evidence**
2. Click **Choose file** and select the file from your computer (accepted formats: PDF, DOCX, XLSX, PNG, JPG, ZIP — maximum size 50 MB)
3. Fill in:
   - **Short description** (e.g. "Firewall configuration screenshot dated 15/03/2026")
   - **Expiry date** — mandatory for system logs, scan reports, certificates. Leave blank for documents without an expiry date
   - **Framework / controls covered** — select all controls this evidence documents
4. Click **Upload**

The evidence is available immediately. The system will automatically verify that the MIME type of the file matches the declared extension.

### How to fill in the TISAX Implementation description (guided interview)

The VDA ISA is filled in in English: for each TISAX control the auditor reads, next to the declared maturity, **how** the requirement is implemented. The control's **Evaluation** tab has the «Implementation description (VDA ISA)» box: you can write the English text directly or use the guided interview, which simulates a conversation with a TISAX auditor.

1. Click **Fill in with the guided interview (AI)**
2. The auditor asks you **2–4 questions by topic** in your language (e.g. for the security policy: the documents, their approval and review, communication to staff and partners). For each question you see **what the auditor wants to understand**, **what to mention** and, on request, **an example** with placeholders in square brackets: adapt it to your reality, do not copy it. «VDA requirements of this question» shows the original English requirements (for L3 controls also those of the extended L2 control)
3. Answer concretely: which documents, who is responsible, how it works, how often. Write "no" if something is not in place yet. Names of people and personal data are not needed
4. **Review with the auditor** (at most **2 rounds**): for each requirement the auditor says whether it is covered, partial or not covered, the **maturity** the answers support (with a warning if lower than the declared one), the **evidence** it will ask for on site (flagging what is already linked to the control) and up to 3 **follow-up questions** on what is missing. Answer the follow-ups and, if needed, run the second round. After the rounds you can restart the review: the answers to the questions are kept
5. **Generate English draft**: the AI writes the description from the whole conversation, by topic and without repeating facts, using only what you wrote. Mandatory requirements still uncovered at the last review are marked `[TO BE COMPLETED]`. A translation in your language is shown for review
6. **Use this draft** copies the text into the description field: read it, correct it if needed and press **Save description**

Answers are saved with **Save answers** (review and draft save them too) and stay on the control for next year's re-evaluation. The interview stays in the language it was started in. The draft is never saved on its own: the audit trail records who saved the description and whether it came from the AI. If the AI is not configured the interview is not available and the box shows the original requirements to write the description manually. The Operations Center flags TISAX controls with maturity ≥ 3 and no description.

### How to download SOA ISO 27001, VDA ISA TISAX, NIS2 Matrix

[Screenshot: compliance export page]

1. Go to **Compliance → Controls library**
2. Click the **Export** button (download icon) in the top right of the page
3. Select the type of export:
   - **SOA ISO 27001** — Statement of Applicability with all Annex A controls and their status
   - **VDA ISA TISAX** — VDA Information Security Assessment table, in landscape format (A4 landscape): for each control maturity, status, owner, **Implementation description**, **Reference documentation** (linked documents and evidence) and Note / Justification. Controls with maturity ≥ 3 and no description are marked "Missing" and counted in the header. The description is filled in on the control's **Evaluation** tab, «Implementation description (VDA ISA)» box
   - **NIS2 Matrix** — NIS2 compliance matrix

> **Important note**: always use the "Export" button within the page. Do not open the file URL directly from the browser by copying the link — the download requires the JWT token of the active session and would fail with a 401 error if attempted outside the platform.

### Gap Analysis between frameworks

1. Go to **Compliance → Gap Analysis**
2. Select the two frameworks to compare (e.g. ISO 27001 vs TISAX L2)
3. The system shows a table with controls mapped between the two frameworks, highlighting:
   - Controls satisfied in both frameworks (green)
   - Controls satisfied in only one of the two (yellow)
   - Controls in gap in both (red)
4. You can export the gap analysis in Excel format

### Status propagation across frameworks (and plants)

The **Propagate** button is available in the controls list, next to the status badge, for controls in **Compliant** or **N/A** status that have mappings to other frameworks.

**How it works:**

| Mapping type | Direction | Example |
|--------------|-----------|---------|
| `Equivalent` | Bidirectional | ISO A.8.1 ≡ TISAX ISA-1.1 → propagates in both directions |
| `Covers` | Source → target only | ISO A covers NIS2 art.21 → ISO propagates to NIS2, not vice versa |
| `Partial`, `Related`, `Extends` | Not propagated | Require separate assessment |

**What is copied:**
- The status (`compliant` or `na`) to the mapped control in the same plant
- For N/A: the justification is also copied (with a reference to the source control)
- An audit trail record is generated for each updated control

**Multi-plant propagation:**
Ticking the **"all plants"** checkbox next to the button extends propagation to all plants with an active instance of the target control. Use this when an organisational policy is shared across multiple sites (e.g. password policy, access management).

> `gap`, `partial` and `not assessed` statuses cannot be propagated: each plant must assess them independently.

---

## 4. IT and OT Assets (M04)

[Screenshot: asset inventory]

### How to add an asset

**IT Asset:**

1. Go to **Risk → Asset inventory → New IT asset**
2. Fill in the mandatory fields:
   - **Name / FQDN**: hostname or IP address
   - **Operating system** and **version**
   - **EOL date**: if the system is out of support, criticality is automatically increased
   - **Internet-facing**: critical flag — increases the risk profile
   - **Criticality level**: from 1 to 5 (see table below)
3. In the **Linked critical processes** section select the processes from BIA (M05) that depend on this asset
4. Click **Save**

**OT Asset:**

1. Go to **Risk → Asset inventory → New OT asset**
2. In addition to the common IT asset fields, fill in:
   - **Purdue level** (0–5): position in the OT network hierarchy
   - **Category**: PLC, SCADA, HMI, RTU, sensor, other
   - **Patchable**: if the system cannot be patched, indicate the reason and the scheduled maintenance window
3. Click **Save**

### Difference between IT and OT assets

| Characteristic | IT Asset | OT Asset |
|----------------|---------|---------|
| Examples | Server, workstation, firewall, switch, applications | PLC, SCADA, HMI, RTU, industrial sensors |
| Typical network | Corporate network, Internet | Production network, fieldbus |
| Patching | Frequent, automatable | Limited, requires maintenance windows |
| Disruption impact | Data loss, service unavailability | Production shutdown, physical damage, safety risk |
| Risk assessment | Exposure/CVE dimensions | Purdue/patchability/safety dimensions |

### Criticality table 1–5

In the asset creation and editing form you will find a criticality badge with explanatory tooltips for each level. For reference:

| Level | Label | Description |
|-------|-------|-------------|
| **1** | Low | Shutdown or compromise does not impact production. Acceptable loss without a dedicated continuity plan |
| **2** | Medium-low | Limited impact on administrative or support functions. Recovery within 24 hours |
| **3** | Medium | Impact on operational processes. Requires a continuity plan. Measurable data or production loss |
| **4** | High | Shutdown causes significant financial loss, impact on customers or regulatory compliance. RTO < 4 hours |
| **5** | Critical | Safety impact, risk to life or physical damage, or total production shutdown. RTO < 1 hour. Requires immediate risk analysis |

Always use this table to ensure consistency across different plants.

### How to register an external change

When an asset undergoes a significant modification (firmware update, configuration change, network perimeter expansion):

1. Open the asset record
2. Click **Register change** in the "Change history" section
3. Fill in: change date, description, type (configuration / hardware / software / network), estimated impact
4. Save — the change is recorded in the audit trail and the asset receives the "To be reassessed" badge

### "To be reassessed" badge — when it appears and what to do

The orange **"To be reassessed"** badge appears on the asset record when:

- An external change has been registered
- The scheduled periodic review date set by policy has expired
- A risk linked to the asset has changed significantly in score
- The asset has reached the EOL date of its operating system

What to do: open the asset record, verify that the information is still accurate (in particular criticality, exposure and linked critical processes), then click **Mark as reassessed**. If necessary, update the fields before confirming.

---

## 5. Business Impact Analysis (M05)

[Screenshot: BIA process list]

### How to create a critical process

1. Go to **Risk → BIA → New process**
2. Fill in:
   - **Process name**: e.g. "Production order management"
   - **Description**: what the process does, who uses it
   - **Process owner**: select the responsible role
   - **Department / function**: relevant business area
   - **Plant**: reference site
3. Save — the process enters **Draft** status

### MTPD, RTO, RPO — simple explanation with examples

These three parameters define the process's tolerance to disruption:

| Parameter | Definition | Practical example |
|-----------|------------|-----------------|
| **MTPD** (Maximum Tolerable Period of Disruption) | How long the process can be down before the company suffers irreversible damage | E.g. "The shipping process can be down for at most 48 hours before losing key customers" |
| **RTO** (Recovery Time Objective) | How quickly the process must be restored after a disruption | E.g. "The MES system must be back in operation within 4 hours of the incident" |
| **RPO** (Recovery Point Objective) | How far back in time data can be lost without unacceptable damage | E.g. "We cannot lose more than 1 hour of production data" — so backups must be at least hourly |

The system uses RTO and RPO to verify that the linked BCP plan (M16) is consistent: if the BCP provides an RTO greater than the one declared in the BIA, a warning appears.

### Flow: draft → validation → approval

1. **Draft**: the process has been created but not yet validated. You can edit all fields
2. **Validation**: the Risk Manager verifies the MTPD/RTO/RPO parameters and approves or requests changes
3. **Approval**: the Plant Manager formally approves. The process becomes immutable — to modify it you must open a new revision

To advance a phase: from the process record click **Submit for validation** (from Draft) or **Submit for approval** (from Validation).

### How to link a process to an asset

1. Open the BIA process record
2. In the **Dependent assets** section click **Add asset**
3. Search for and select the asset from the inventory (M04)
4. Indicate the type of dependency: **Critical** (the process stops without this asset) or **Support** (performance degradation)
5. Save

The dependency is bidirectional: the asset will show in its own record the processes that depend on it, and the criticality of the process influences the risk calculation on the asset.

---

## 6. Risk Assessment (M06)

[Screenshot: risk assessment list]

### Difference between inherent and residual risk

- **Inherent risk**: the level of risk in the absence of any controls. It represents the "raw" threat to the asset or domain
- **Residual risk**: the level of risk after applying existing controls. This is the value on which the decision to accept or treat the risk is based

In the assessment form you first fill in the inherent risk, then the system automatically calculates the residual based on the status of the linked controls. If the controls are not yet sufficient, the residual remains high.

### How to fill in the IT and OT dimensions

**IT risk assessment dimensions (4 axes):**

1. **Exposure**: is the asset on the Internet? In DMZ? Isolated? (1 = completely isolated, 5 = exposed on the Internet without protections)
2. **CVE**: what is the maximum CVE score of the assets involved? (1 = no known vulnerabilities, 5 = critical unpatched CVE)
3. **Sector threats**: are there known active threats for the automotive sector? (1 = none, 5 = documented active campaign)
4. **Control gaps**: how many relevant controls are in gap or not assessed status? (1 = all compliant, 5 = majority in gap)

**OT risk assessment dimensions (5 axes):**

1. **Purdue + connectivity**: is the system connected to IT networks or to the Internet? (1 = isolated level 0, 5 = connected to the Internet)
2. **Patchability**: can the system be updated? How frequently? (1 = regular patches, 5 = never updatable)
3. **Physical / safety impact**: can a disruption or alteration cause physical harm or occupational safety issues? (1 = no physical impact, 5 = risk to people's safety)
4. **Segmentation**: is the OT zone adequately separated from IT and the Internet? (1 = completely segregated, 5 = flat network)
5. **Anomaly detectability**: is there a detection system for anomalous behaviour? (1 = active dedicated IDS/ICS, 5 = no visibility)

### Critical threshold (score > 14) and automatically generated tasks

When **residual risk exceeds 14** (red quadrants of the 5x5 heat map):

- The Risk Manager and Plant Manager receive an immediate notification
- A risk treatment planning task is automatically created with a 15-day deadline
- If the task is not completed within 15 days, an escalation to the Compliance Officer is triggered
- The risk is highlighted in red on the dashboard and in the heat map

### Formal risk acceptance

If the residual risk is known but a decision is made to accept it (e.g. the cost of treatment exceeds the expected impact):

1. From the risk record click **Accept risk**
2. Fill in the formal acceptance form:
   - Justification (mandatory, minimum 50 characters)
   - Review date (mandatory — the risk must be periodically reassessed)
   - Digital signature of the authorised responsible
3. Save — the risk moves to "Accepted" status and no longer generates alerts until the review date

### Heat map and interpretation

[Screenshot: 5x5 heat map]

The heat map shows risks on a 5x5 Probability x Impact grid:

- **Green** (score 1–7): acceptable risk — periodic monitoring
- **Yellow** (score 8–14): moderate risk — mitigation plan within 90 days
- **Red** (score 15–25): high risk — automatic escalation, plan within 15 days

Click on a quadrant to see the list of risks that compose it. Use the plant filter to compare the risk distribution across different sites.

---

## 7. Documents and Evidence (M07)

[Screenshot: document management]

### Difference between Document and Evidence

| Characteristic | Document | Evidence |
|----------------|----------|---------|
| What it represents | Policy, procedure, operational instruction | Screenshot, log, scan report, certificates |
| Mandatory workflow | Yes — drafting, review, approval | No — direct upload |
| Versioning | Yes — each version is immutable after approval | No |
| Expiry date | Only if explicitly configured | Mandatory for logs, scans, certificates |
| Main use | Demonstrate that a process exists and is governed | Demonstrate that a control is active and functioning |

### Document approval workflow (3 levels)

The document passes through 3 mandatory phases in sequence:

1. **Drafting** (document owner): upload the PDF file, fill in the metadata (title, code, framework, owner, reviewer, approver), save as draft. The document is only editable in this phase
2. **Review** (nominated reviewer): reads the document, can add structured notes or approve. If rejected, must write a comment that becomes a permanent part of the changelog
3. **Management approval** (Plant Manager or CISO): formally approves. After approval the document is immutable — to modify it you must open a new revision via the **New revision** button

### How to link evidence to a control

Method 1 — from the control record:
1. Go to the control record (Compliance → Controls library → select control)
2. Click **Attach evidence** in the "Linked evidence" section
3. Upload the file or select already-uploaded evidence from your archive
4. Save

Method 2 — from the evidence record:
1. Upload the evidence via **Compliance → Evidence → New evidence**
2. In the **Controls covered** field select one or more controls that this evidence documents
3. Save

Evidence can cover multiple controls simultaneously, even from different frameworks.

### Evidence expiry and coloured badges

Evidence with an expiry date shows a coloured badge on the control record and in the evidence list:

| Badge | Meaning |
|-------|---------|
| **Green** | Valid evidence — expiry more than 30 days away |
| **Yellow** | Expiring soon — less than 30 days remaining |
| **Red** | Expired — the expiry date has already passed. The linked control automatically degrades to "Partial" |
| **Grey** | No expiry date set |

The system sends an email reminder 30 days before expiry and an alert at the actual expiry.

### Document versioning

Each approved document receives a version number (e.g. v1.0, v1.1, v2.0). The complete history of all versions is accessible from the document record in the **Version history** section. Each version records:

- Approval date
- Name of the approver
- Changelog (reviewer's notes)
- File hash to guarantee integrity

---

## 8. Incident Management (M09)

[Screenshot: incident list]

### How to open an incident

1. Go to **Operations → Incidents → New incident**
2. Fill in the mandatory fields:
   - **Affected plant**: automatically determines the NIS2 profile of the subject
   - **Title**: brief description (e.g. "Unauthorised access to MES system — North plant")
   - **Description**: what happened, when it was detected, how it was discovered
   - **Affected assets**: select from the inventory (M04)
   - **Initial severity**: Low / Medium / High / Critical — updatable at any time
3. Click **Create incident**

Immediately after creation the system evaluates whether the plant is a NIS2 subject and, if so, starts the ACN timers visible at the top of the incident record.

### NIS2 flag and 24h timer (ACN notification)

[Screenshot: incident record with NIS2 timer]

If the plant is classified as a NIS2 subject (essential or important), three countdowns appear on the incident record:

- **T+24h — Early warning ACN**: preliminary notification to the reference Authority (legal obligation)
- **T+72h — Full notification**: detailed notification with impact and measures adopted
- **T+30d — Final report**: conclusive report with RCA

If the plant is in NIS2 scope, the incident starts as **to be assessed**: the CISO must either **confirm** the notification obligation — the T+24h and T+72h deadlines are then set — or **exclude** it with a reason. If the incident remains unclassified for more than **30 minutes**, the system sends a **reminder alert** to the CISO asking for classification (it does not decide on their behalf). Every decision is recorded in the audit trail.

The timers are displayed with a red background when the remaining time is less than 2 hours.

### Filling in the RCA (Root Cause Analysis)

1. On the incident record go to the **Root Cause Analysis** section
2. Choose the analysis method:
   - **5 Why**: guided, with 5 levels of "why"
   - **Ishikawa**: cause-effect diagram by category (People, Process, Technology, Environment)
   - **Free text**: unstructured narrative
3. Fill in root cause, failed controls and proposed corrective actions
4. Submit for approval to the Risk Manager via **Submit for approval**

An incident cannot be closed without an approved RCA.

### Closure and automatically generated PDCA

After RCA approval you can close the incident via the **Close incident** button. The closure automatically generates:

- A **Lesson Learned** in M12 with the incident information and corrective actions
- A **PDCA** cycle in M11 if the corrective actions are structural (e.g. procedure changes, implementation of new controls)
- A **review** trigger on linked documents in M07 if the failed controls are covered by existing policies

---

## 9. PDCA (M11)

[Screenshot: PDCA cycle list]

### The 4 phases: PLAN, DO, CHECK, ACT

Each PDCA cycle represents a continuous improvement action. The 4 phases follow a mandatory sequence:

- **PLAN**: define the objective, actions to be taken and resources needed
- **DO**: execute the planned actions
- **CHECK**: verify that the results match the objectives through measurable evidence
- **ACT**: standardise the solution if it worked, or restart from DO with a different approach

### What is needed to advance each phase

| Transition | Mandatory requirement |
|------------|----------------------|
| **PLAN → DO** | Description of the action to be performed (minimum 20 characters). The plan must be understandable even out of context |
| **DO → CHECK** | Evidence documenting the action performed (mandatory): choose an existing one or upload the file from the same window, without leaving the cycle. The uploaded file becomes evidence of the cycle, on the cycle's site and with no expiry |
| **CHECK → ACT** | Result of the verification (descriptive text) + Chosen outcome: **ok** / **partial** / **ko** |
| **ACT → CLOSED** | Standardisation: documentation of the adopted solution so that it is replicable (minimum 20 characters) |

### What happens if CHECK outcome = ko

If in the CHECK phase the outcome is **ko** (the solution did not work):

1. The cycle does not advance to ACT but automatically returns to the **DO** phase
2. A note is added to the cycle log with the date of the failure
3. A new action plan must be filled in for the DO phase
4. The DO cycle counter is incremented to track how many iterations were needed

There is no limit to the number of DO-CHECK iterations, but the system signals cycles with more than 3 iterations to the Compliance Officer.

### Site or organization-wide cycle

When creating a cycle, the **Site** field states what the cycle applies to:

- a **site**: the cycle concerns that plant only and is managed by that site's users;
- **Organization — all sites**: the cycle applies to the whole organization (e.g. a common procedure or an awareness campaign for everyone). The scope automatically becomes **Organization**.

Organization-wide cycles are visible to all sites, but only users with access to the whole organization can open and drive them (phase advancement, editing, archiving, deletion); for the others they appear **read only**, with the dossier available. Filtering the list by a site also shows organization-wide cycles, which apply there too; the **Organization only** option shows just those. The **Status** filter shows cycles in progress (PLAN to ACT), a single phase, closed or archived ones. In the DO phase of an organization-wide cycle you can attach evidence from any site. On closure the generated lesson learned is organization-wide too and, if the CHECK outcome is ko, the new cycle stays organization-wide.

### PDCAs automatically created from incidents, findings, critical risks

PDCA cycles are created manually or automatically from:

- **Closed incidents (M09)**: when the RCA corrective actions are structural — starting phase PLAN
- **Audit findings (M17)**: for Major NC and Minor NC — starting phase PLAN with deadline determined by severity
- **Risks with score > 14 (M06)**: when the treatment plan requires structural actions — urgent PLAN phase
- **Management review decisions (M13)**: for each action approved by the review — PLAN phase

In all cases of automatic creation, the PDCA cycle includes a reference to the originating entity (e.g. "Incident #INC-2026-042") and any deadline derived from policy.

---

## 10. Lesson Learned (M12)

[Screenshot: lesson learned knowledge base]

### How to create a manual lesson learned

1. Go to **Governance → Lesson Learned → New**
2. Fill in:
   - **Title**: brief description of the event or learning
   - **Event description**: what happened, context, relevance
   - **Analysis method used**: 5 Why, Ishikawa, free text
   - **Identified root cause**
   - **Impacted controls**: select the relevant controls from the library
   - **Short-term actions**: actions to be completed within 30 days
   - **Structural actions**: long-term actions (will be managed via PDCA)
3. Click **Submit for approval**

The Risk Manager or Compliance Officer approves the lesson learned before it becomes visible to the whole organisation in the knowledge base.

### Lesson learned automatically created from closed PDCAs

When a PDCA cycle is closed with a positive outcome, the system automatically creates a lesson learned that includes:

- The original context (incident, finding, risk) that initiated the PDCA
- The actions performed in the DO phases
- The result obtained in the CHECK phase
- The standardisation documented in the ACT phase

The automatic lesson learned starts in "Draft" status and is assigned as a task to the PDCA cycle owner for review before approval.

If the PDCA cycle is organization-wide, the lesson learned is organization-wide too: all sites can see it, but only users with access to the whole organization can manage it.

### Searching the knowledge base

Go to **Governance → Lesson Learned → Knowledge base**. You can search by:

- **Keyword**: text search on title and description
- **Framework / control**: filter by impacted controls
- **Event type**: incident, finding, risk, voluntary improvement
- **Plant**: only lesson learned from your plant, or from all plants (if you have multi-plant access)
- **Period**: approval date

Only approved lesson learned are shown. Drafts are visible only to the owner and reviewers.

---

## 11. Management Review (M13)

[Screenshot: management review]

The module guides the management review required by ISO/IEC 27001:2022 §9.3 and produces the minutes to archive and present to the auditor.

### How to create a review

1. Go to **Governance → Management Review → New review**
2. Fill in:
   - **Title**: e.g. "Management review 2026"
   - **Site**: a site, or **org-wide** for a review of the whole organisation (data aggregates all sites and the minutes include an overview by site)
   - **Meeting date**
   - **Body**: the governing body holding the review (see [Governance → Governing bodies](#19-governance-m00)); the board of directors is proposed, if configured. The invitees are the body's members in office on the review date, with the body's chair as meeting chair
   - Without a body, the CISO appointed in M00 Governance is proposed as chair (the site CISO, otherwise the organisation one; failing that the ISMS Manager)
3. Click **Create review**: the system automatically creates the agenda with the mandatory items

From the detail view, until approval, you manage **invitees and attendance**: for each one present, absent or represented by a proxy (with the proxy's name), the role and who chairs, who must be present. You can add body members, platform users and **guests** without an account (e.g. a consultant), with name and position. **Reload from body** reloads the members in office. In the minutes name and position stay as they were on the review date, even if they change later. The body and the next review date can also be changed.

### Mandatory agenda (ISO 27001 §9.3.2)

Every review contains these items, which cannot be deleted:

- a) Status of actions from previous management reviews
- b) Changes in external and internal issues relevant to the ISMS
- c) Changes in needs and expectations of interested parties
- d) Information security performance (nonconformities and corrective actions, monitoring and measurement, audits, objectives)
- e) Feedback from interested parties
- f) Results of risk assessment and status of the risk treatment plan
- g) Opportunities for continual improvement

Extra items can be added with **Add item**. **The meeting cannot be closed** if a mandatory item has neither a discussion nor a decision: missing items are highlighted.

### Data snapshot

Click **Generate data snapshot** to freeze GRC data at the time of the meeting. The data appears inside the agenda items it relates to, with short lists (at most 10 entries, with "… and N more"):

- **a)** actions from previous reviews: all those of the previous review, plus older ones still open or closed in the period, with overdue ones highlighted
- **d)** compliance per framework with controls with gaps; operational KPIs outside thresholds; audits of the last 12 months with readiness and open nonconformities (major first); open and NIS2-notified incidents; stuck PDCA cycles and overdue tasks; expired, expiring and recently approved documents
- **f)** critical risks (inherent → residual, treatment, owner, whether a plan exists), formally accepted risks, critical processes without a BCP plan
- **g)** improvement opportunities from audits

The snapshot can be regenerated until approval; afterwards it is fixed because it is the content of the minutes.

### How to run the meeting and record decisions

1. Click **Start meeting**
2. For each item: open it, review the data, write the **discussion** and save
3. With **Add decision** record the review outputs (§9.3.3): description, **type** (improvement, change to the ISMS, resources, other), owner and due date
4. If the decision needs to be carried out, tick:
   - **Create task**: opens a task in M08 **assigned to the selected role**, with the decision's due date (high priority for changes to the ISMS)
   - **Open PDCA cycle**: opens a PDCA cycle in M11 (for an organisation-wide review choose a site or **Organization (all sites)**, reserved to users with access to the whole organization)
   The status of the linked task and the phase of the linked PDCA are shown on the decision
5. Click **Mark as completed**: the system checks the mandatory items and proposes the **next review date** according to the schedule policy. Planned meetings and the next review appear in the **Schedule**

### Executive summary with AI

The executive summary opens the minutes: overall assessment of the ISMS, critical issues, decisions and priorities.

- **Write manually**, or
- **Generate AI draft** (requires the snapshot; best done after filling in the agenda). The AI engine receives aggregated data and the minutes' texts: people's names are replaced with placeholders and the text goes through the standard anonymisation (emails, phone numbers, site names). The draft is marked as **AI-generated content** and **does not enter the minutes** until you click **Accept into minutes**, possibly after editing it; **Discard draft** deletes it

In the minutes the summary states whether it was drafted with AI support (and with which model), whether it was edited and who accepted it.

### Approval and minutes

1. Approval takes two forms (both require the snapshot and a completed meeting):
   - **Approve in the app**: given by a **member of the body in office with a linked account** (e.g. a director), who sees and approves only their body's reviews without being able to edit them; the minutes show their name and position. Governance (Compliance Officer) can also approve
   - **Record the body's resolution**: if the body resolved outside the platform, governance records the **resolution number and date** (not earlier than the meeting) and, optionally, the **M07 document** as evidence; the minutes show “Approved by <body> — Resolution no. … of …” and who recorded it

   After approval meeting data, invitees, agenda, decisions and summary can no longer be changed; only the progress status of decisions can still be updated
2. Download the minutes as **PDF** or **HTML**: review data, attendees, executive summary, points of attention, agenda with data, discussion and decisions, decisions summary, approval. The download is recorded in the audit trail
   Under **Meeting status** you choose the **minutes logo**, top right in the PDF and HTML, among those uploaded for the sites in Plant Registry (the review site's logo is proposed). It can be changed even after approval
3. The **audit package** (M03) includes the review summary and the PDF minutes of approved reviews

### Targeted review

Between one full review and the next, the body can meet on specific items, for example to approve a policy or decide a small change. For these meetings create a review of type **Targeted** (chosen in the creation form, it cannot be changed later).

1. The targeted review has **no** mandatory §9.3.2 items, data snapshot, executive summary or AI drafts, and it **does not count as the periodic review**: the next review date stays the one decided in the last full review
2. **Documents to decide**: **“Add documents to decide”** opens the list of documents in scope that are in draft, under review or awaiting approval, and of documents in force with a new unapproved version (badges *Mandatory*, *New version*, *Body resolution*). Each chosen document becomes an agenda item, with the **reviewed revision** fixed at the time of selection
3. For each document record the **outcome**: *Approved*, *Postponed* or *Rejected*, with an optional note in the discussion. If a new revision is uploaded after the selection, the item flags it: use **“Realign”** (the outcome must be recorded again, on the new text)
4. Add **free items** for the other decisions, as in the full review (discussion, decisions, tasks, PDCA)
5. **Close the meeting**: at least one item is required and every document must have an outcome
6. **Approve the minutes** (in the app or by recording the resolution): the outcomes are applied to the documents. *Approved* ones take effect by resolution of the body, with the date of the resolution or of the meeting; *rejected* ones go back to draft; *postponed* ones stay pending. If an outcome cannot be applied (for example a new revision was uploaded after the meeting) it is shown with the reason and can be retried
7. The **minutes** of the targeted review list the documents examined with revision and outcome, the items and the decisions; in the **audit pack** targeted meetings are in `09_management_review/sedute_intermedie/`

---

## 12. Audit Preparation (M17)

[Screenshot: audit preparation — programme list]

### Annual Programme

#### How to create the programme with the wizard (4 steps)

1. Go to **Audit → Audit Preparation → New programme**
2. The wizard opens in 4 steps:

**Step 1 — Basic data**
- Programme year (e.g. 2026)
- Reference plant
- Frameworks to audit (ISO 27001, TISAX L2, TISAX L3, NIS2 — select one or more)
- Programme name (e.g. "ISO 27001 Audit Programme — North Plant 2026")

**Step 2 — Coverage parameters**
Choose the audit coverage level:
- **Sample (25%)**: spot audit on a quarter of the controls. Suitable for intermediate checks or when resources are limited
- **Extended (50%)**: coverage of half of the controls. Balance between depth and sustainability
- **Full (100%)**: complete audit of all framework controls. Required for formal certifications

**Step 3 — Review of the suggested plan**
The system analyses the current state of controls and generates a suggested plan that:
- Concentrates Q1 and Q3 on **domains with the most gaps** (the most critical are audited first)
- Distributes the remaining controls across quarters Q2 and Q4
- Suggests auditors based on available roles in the plant

You can manually modify: the dates of each quarter, the auditor assigned to each session, the list of controls included in each quarter.

**Step 4 — Approval**
- Review the programme summary
- Click **Approve programme**
- The programme becomes active and visible to all roles involved

#### How to interpret the suggested plan

The system prioritises domains with the most gaps in the initial quarters (Q1 and Q3) to allow sufficient time for resolution before any certification audits. Domains with good coverage are assigned to quarters Q2 and Q4. Check that the distribution is sustainable in terms of workload for the auditors.

#### How to change dates and auditors per quarter

From the detail of the approved programme:
1. Click the edit icon next to the quarter to update
2. Change the start/end date and the assigned auditor
3. Save — the change is recorded in the programme log

#### How to approve the programme

On completion of Step 4 of the wizard the programme automatically moves to "Approved" status. The Compliance Officer receives a notification. The programme is now visible to the assigned auditors.

---

### Audit Execution

[Screenshot: audit quarter detail]

#### How to start an audit from a quarter

1. From the approved programme, go to the quarter of interest
2. Click **Start audit** — the quarter moves from "Planned" to "In progress"
3. The checklist of controls to verify for that quarter opens

#### Sample vs full coverage — practical differences

- **Sample**: you only see the subset of controls selected by the system (25% or 50% of the total). You cannot add controls not included in the sample
- **Full**: you see all framework controls. You must fill in the evidence for each one before you can close the audit

In both cases the structure of the checklist is identical — the only difference is the number of controls to verify.

#### How to fill in the controls checklist

For each control in the checklist:
1. Click on the control to expand the detail
2. Verify the declared status and the linked evidence
3. Choose the **auditor's judgement**: Confirmed / Non-Conformant / Observation / Opportunity
4. If the judgement is other than "Confirmed" click **Add finding** (see below)
5. Add any auditor notes in the appropriate field
6. Click **Save judgement**

#### How to add a finding

1. From the control record click **Add finding**
2. Fill in:
   - **Finding title**
   - **Detailed description**: what is missing or non-conformant
   - **Finding type** (see table below)
   - **Reference control**
   - **Supporting evidence**: optional at opening, mandatory for Major NC

#### Finding types and response deadlines

| Type | Meaning | Response deadline |
|------|---------|------------------|
| **Major NC** (Major Non-Conformity) | Requirement not met with significant impact on compliance or security | 30 days |
| **Minor NC** (Minor Non-Conformity) | Requirement partially not met, limited impact | 90 days |
| **Observation** | Potential weakness that is not yet a non-conformity. To be monitored | 180 days |
| **Opportunity** | Improvement suggestion with no impact on compliance. No mandatory deadline | — |

Response deadlines are automatically calculated from the finding opening date based on these policies. For Major and Minor NC a PDCA cycle linked to the finding is created automatically; for Major NC also an urgent task.

#### Linking findings and PDCA

Each finding can have **only one PDCA**; a PDCA can cover several findings, but of the same audit and site (e.g. two observations solved by a single action). The link is visible from both sides: on the finding the PDCA phase, with one click to open it; on the PDCA the originating finding and audit, with audit type and requesting party.

From the audit's **Findings** tab, for a finding without a PDCA:

- **Open PDCA** creates the cycle already linked, on the audit's site and with the audit type (useful for observations and opportunities, which do not open one automatically);
- **Link to existing PDCA** links it to an open cycle of the same site.

The same can be done from the **PDCA** menu: in a new cycle with origin **Audit** choose audit and finding (site and audit type are filled in automatically), or from the **🔗 Findings** button of an existing cycle. A wrong link is removed with **Unlink**, giving a reason that is kept in the audit trail.

**Existing PDCAs, including closed ones** — a finding can be linked to any PDCA of the same site, **even one already closed or archived**: this covers a corrective action carried out before the finding was recorded (e.g. a PDCA opened manually from the audit report) or history recovery. If the finding is open and the PDCA is closed, the finding moves to **in response**, ready to be closed with evidence; if the finding is already closed no status changes (retroactive link, recorded as such in the audit trail). From the PDCA menu, **🔗 Findings** shows all the audit's findings, open and closed.

**Replacing a PDCA** — if the finding already has a PDCA (for NCs the one opened automatically), it is replaced with the right one by giving a reason: from the finding with **Replace PDCA**, or from the PDCA menu by choosing the finding (it shows the cycle it is linked to). The replaced PDCA is archived only if it had been opened automatically for that finding and was never worked on; otherwise it stays as it is, only unlinked. No new PDCA is opened for a closed finding: it is linked to an existing one.

#### How to close a finding

1. In the audit's **Findings** tab click **Close finding** on the finding
2. Enter the **closure notes** (at least 20 characters for Major and Minor NC) and choose the **closure evidence** (mandatory for Major and Minor NC)
3. Click **Close**

If the finding has a linked PDCA, it is closed only once the corrective action is complete: with the PDCA **closed** (or archived), or in the **ACT** phase if the PDCA covers only this finding; in that case the PDCA is closed together with the finding and the closure notes become its standardisation. Otherwise the system shows the PDCA phase and saves nothing. When a PDCA is closed, its linked findings still open move to "in response", ready to be closed with evidence.

#### How to download the audit report

From the in-progress or closed audit:
1. Click the **Report** button in the top right of the audit page
2. Choose the report language
3. The system generates an **HTML** report with: coverage summary, list of findings by type, closure status, trend compared to the previous audit
4. The report is available immediately for download (printable/archivable)

---

### External audits: second and third party

Besides internal audits, Audit Prep records audits conducted by others, so their findings follow the same path (deadlines, PDCA, closure with evidence):

- **Second party (customer)**: the audit a customer (e.g. an OEM) performs on you, directly or through an appointed audit body;
- **Third party (certification)**: the audit of a certification body (e.g. TISAX, ISO/IEC 27001).

**How to record it**

1. Click **+ New preparation** and choose the **Audit type**
2. For a second-party audit enter the **Requesting party**, i.e. the customer the audit is performed for, and in **Audit body / auditor** who performs it; the framework is optional
3. Add findings as for an internal audit: if no auditor is given on the finding, the audit body applies, and the PDCA opened for nonconformities shows the audit type (e.g. "Second party")

Type and requesting party can be corrected later from the **Audit info** tab.

**Second party: no checklist.** In a second-party audit the audit criteria are the customer's: the controls checklist is not loaded (not even when choosing TISAX AL3), the detail opens on the **Findings** tab and the card shows the open findings and whether the report is attached, instead of the readiness. The framework, if given, is for reference only. In third-party (certification) audits the checklist stays, because the body checks exactly the framework's requirements.

**Official report** — in the **Audit info** tab, **Official report from the auditor or audit body** section, choose the file (e.g. the PDF received from the customer) and click **Attach report**. The file is stored as evidence of type "report", on the audit's site and with no expiry. From there you can download it, replace it with a revision (the previous one stays among the evidence) or detach it. This is different from **Download report**, which is the summary generated by the platform.

External audits appear with their type and requesting party in the list, in the management review analysis (audit results, §9.3.2 d) and in the minutes; the **audit package** contains the `AUDIT_ESTERNI/` folder with a summary and the attached reports.

### Audits on several sites

An audit may cover some sites but not the whole organization: for example a TISAX AL2 assessment with a single Scope ID on two plants. In this case:

1. Click **+ New preparation** and tick **Audit on several sites**
2. Choose at least two sites: only frameworks assigned to **all** the selected sites are offered
3. Fill in title, type, requesting party, audit body, date and, if any, the **Scope ID**, then create the audit

The system creates **one audit per site** (title "… — site code"), linked to each other:

- **per site**: checklist, readiness, findings with their PDCA, deadlines and tasks, and closure. Users managing a single site see and work only on their own;
- **shared**: type, requesting party, audit body, date, Scope ID and the **official report**, attached only once and downloadable from every site. They are changed from the **Audit info** tab of any site and apply to all, but this requires access to all the audit's sites.

**Common finding** — in the finding form tick **Finding common to all the audit's sites**: one finding is created for each site, each with its own PDCA, marked **Common to sites**. Without the tick the finding stays on the site where you record it.

In the organization-wide management review, the multi-site audit counts **once**, with the list of the sites involved; in a site's review only that site's audit appears.

### Cancelling an audit

[Screenshot: cancel audit button]

#### When to use "Cancel" vs deletion

- Use **Cancel** when a planned audit will not be carried out but you want to keep a record of the original planning (e.g. date change, scope change, business emergency)
- **Deletion** is not available for audits in "In progress" or "Closed" status — always use "Cancel" for started audits

#### How to cancel

1. From the audit list, click the **Cancel** button (X icon) on the audit row
2. A dialogue opens requesting the **cancellation reason** (mandatory, minimum 10 characters)
3. Enter the reason (e.g. "Postponed to Q3 due to auditor availability")
4. Click **Confirm cancellation**

#### What happens to open findings

When you cancel an audit that already has open findings:
- The findings are **automatically closed** with "Cancelled" status and the cancellation reason
- PDCAs linked to the findings remain open and must be managed manually
- The annual programme is not modified — the quarter is marked as "Cancelled" with a record of the reason

The cancelled audit is never physically deleted — it remains in the archive with "Cancelled" status to guarantee traceability.

---

## 13. Suppliers (M14)

[Screenshot: supplier list]

The module is opened from **Operations → Suppliers** and has five tabs: **Suppliers**, **Questionnaires**, **Questionnaire templates**, **NDA status** and **Evaluation settings**. Suppliers are created and edited by Super Admin, Compliance Officer, Risk Manager and Plant Manager; internal and external auditors have read-only access. Each user sees the suppliers of their own sites and those with no site assigned (organisation-wide suppliers).

### How to register a supplier

1. In the **Suppliers** tab click **+ New supplier**
2. Fill in:
   - **Company name**, **Tax / VAT number** and **Registered office country** — mandatory
   - **Supplier email (TO)** — mandatory, it is the recipient of questionnaires; under **Additional CC emails** you can add other contacts in copy
   - **Supply description** — what the supplier provides; also used to suggest CPV codes
   - **Risk level** — your initial estimate; the actual evaluation comes from the sources described below
   - **ACN / NIS2** section: **CPV codes** of the supply (the AI button suggests codes from the description, which is sent without the supplier name; each suggestion must be accepted manually), the **NIS2 relevant supplier** flag and, if set, the **relevance criterion** (structural ICT supply, non-fungibility or both) and the **% supply concentration**
   - **TISAX** section: the **TISAX relevant supplier** flag if the supplier handles information within the TISAX scope (e.g. OEM customer data or prototypes) or accesses in-scope systems (VDA ISA 6.1.1)
3. Click **Create supplier**

**Duplicate check** — while you fill in the form the system looks for suppliers already registered:

- **Same VAT number** (compared ignoring spaces, dots, hyphens and the country prefix, e.g. `IT 0123.4567.890` = `01234567890`): saving is **blocked**. If the existing supplier is within your scope you can open it with **Open**; if it is registered on a site outside your scope you only see that it exists and must ask a Compliance Officer to link it to your site. A deleted supplier does not prevent re-entry.
- **Similar company name** (ignoring case, punctuation and legal forms such as S.r.l., S.p.A., GmbH, Ltd): a **warning** lists the similar suppliers; to create anyway tick **I have checked: this is a different supplier**. The audit trail records how many similar names were present at creation.

The edit icon lets you change the data and the supplier **Status** (active, suspended, terminated). Deletion is logical (the supplier stays in the history) and also removes its questionnaires.

**Concentration** — the percentage sets the TPRM threshold (ACN Resolution 127434): below 20% **low**, 20% to 50% **medium**, above 50% **critical**. When a supplier enters the critical threshold the system sends a notification, only once until the concentration drops back.

### Supplier list

For each supplier the list shows tax/VAT number, country, concentration, **Adj risk**, status, and date and expiry of the latest evaluation. You can search by name, tax/VAT number or email and filter by risk, status, NIS2 relevance and TISAX relevance; the **Risk** filter works on the Adj risk and the **Not evaluated** option lists suppliers with no evaluation at all.

**↓ Export CSV** downloads all suppliers, only NIS2 relevant ones or only TISAX relevant ones, with CPV codes, NIS2 criterion, concentration and evaluation dates.

Clicking the name opens the supplier detail, with three sections: **Internal evaluation**, **Third-party audits** and **NDA / Contracts**.

### How the risk is calculated (Adj risk)

The **Adj risk** is the worst class (low, medium, high, critical) among three sources, each one counted only if present:

1. the current **internal evaluation**;
2. the latest evaluated, non-expired **questionnaire** (sent from the platform or recorded existing evaluation);
3. the latest **third-party audit** approved within the configured validity.

If the supplier is NIS2 relevant and the concentration is critical, the class goes up one level (if the option is enabled in the settings). With no source at all the supplier is **not evaluated**. The calculation runs at every new evaluation and every night, so an expired evaluation stops counting by itself.

### Internal evaluation

In the supplier detail, **Internal evaluation** section, click **Start assessment** (or **New assessment**) and score six parameters from 1 (minimum risk) to 5 (maximum risk): **Business impact**, **System access**, **Data processed**, **Supplier dependency**, **IT integration** and **Cyber certification compliance**. The preview shows the weighted score and the resulting class before saving. Each new evaluation replaces the previous one, which stays in the **Assessment history**.

### Questionnaires

**Templates** — in the **Questionnaire templates** tab you prepare one or more model emails: name, **questionnaire form URL** (for example an online form), subject and body. In subject and body `{supplier_name}` becomes the supplier name; in the body `{questionnaire_link}` becomes the link to the form; if the body does not contain it, the link is added at the end of the email.

**Sending** — in the supplier list click **Quest.**, choose the template and click **Send**. The email goes to the supplier TO address with the CC emails in copy. The supplier fills in the external form: the platform does not receive the answers automatically.

**Reminders** — every Monday whoever sent questionnaires receives a single summary email listing those with no answer for more than 7 days. From the **Questionnaires** tab you can **Resend** the questionnaire; from the 3rd send without an answer the list flags that the supplier should be contacted directly.

**Evaluation** — once you have read the answers, in the **Questionnaires** tab click **Evaluate** and enter the **evaluation date**, the **evaluation** (risk level) and any notes. The expiry is calculated with the questionnaire validity configured in the settings (12 months by default).

At the top of the **Questionnaires** tab you see valid evaluations, those expiring within 90 days, questionnaires awaiting an answer and expired ones: clicking a card filters the list.

**Recording an existing evaluation** — for suppliers already evaluated before using the platform, or with a questionnaire collected on paper:

1. From the **Questionnaires** tab (or from the supplier form) click **Record existing evaluation**
2. Enter the supplier, the evaluation **date** (not in the future) and the **result** (risk level)
3. In the **Reference / notes** field (mandatory) write where the evaluation is stored and who completed it: this is what you will show the auditor
4. Click **Record**. No email is sent to the supplier; in the Questionnaires tab the entry is labelled **Recorded**

### Evaluation date and expiry

The evaluation date is **not entered in the supplier record**: the system derives it from the latest recorded evaluation, which can be:

- the result of a **questionnaire** sent from the platform (**Questionnaires → Evaluate** tab);
- an **existing evaluation**, i.e. carried out outside the platform;
- an approved **third-party audit**.

The **expiry** is calculated with the validity configured in **Evaluation settings** (12 months by default). The supplier list shows date, source and expiry; the compliance schedule shows a **Supplier re-evaluation** item as the expiry approaches and opens a reminder for the Compliance Officer.

### Third-party audits: planned → completed → approved / rejected

For suppliers that undergo an audit (your own or by a third party), in the supplier detail, **Third-party audits** section:

1. **+ New audit**: enter the date and click **Register**. The audit is **Planned**
2. **Complete**: enter the 0–100 scores for **Governance**, **Security** and **BCP** and the **findings**. The **Overall** score is the average of the scores entered. On completion the supplier risk level is updated (Overall ≥ 75 low, ≥ 50 medium, below 50 high) and the audit-completed notification is sent
3. **Approve** or **Reject**: the reviewer records the notes; for a rejection the reason is mandatory (at least 10 characters)

Only an **approved** audit counts in the Adj risk, and only within the configured audit validity (12 months by default): Overall ≥ 75 low, ≥ 50 medium, ≥ 25 high, below 25 critical. A rejected audit stays in the history but does not count.

| Dimension | What it assesses |
|-----------|-------------|
| **Governance** | Security organisation, internal policies, defined responsibilities, internal audits |
| **Security** | Technical controls in place, vulnerability management, incident response, certifications (ISO 27001, TISAX) |
| **BCP** | Business continuity plans, declared RTO/RPO, continuity tests performed, infrastructure redundancy |

### NDAs and contracts

In the supplier detail, **NDA / Contracts** section, click **+ Upload NDA**, choose the file and enter the **title** and, if any, the **expiry**. The document is stored in the Documents module as a contract linked to the supplier; from the same section you can download it or, if it is not approved, approve it.

The **NDA status** tab summarises coverage of active suppliers: with an active NDA, expiring within 90 days, expired, draft or missing. You can search by supplier and filter by NDA status and risk.

### Evaluation settings

The **Evaluation settings** tab holds the calculation parameters: **weights** of the six internal evaluation parameters (they must add up to 1.00), **level labels** for each parameter, weighted-score **thresholds** for the medium, high and critical classes, **validity** of questionnaires and third-party audits (in months) and the **NIS2 bump + critical concentration** option. Users of the module can view them; only the Super Admin can change them.

---

## 14. Training (M15)

The platform **does not deliver** courses and does not connect to e-learning or phishing-simulation platforms: it **governs** training. For each site you plan what to do, record every session with its **proof file** and measure staff coverage **in numbers only**. This is what ISO 27001 A.6.3 and cl. 7.2, NIS2 art. 21.2.g, ACN PR.AT and TISAX ISA 2.1.3 require: a plan, proof that it was carried out and the coverage achieved.

Go to **Operations → Training** and select the site at the top. The page has four tabs: **Plan**, **Sessions**, **Target groups**, **Course catalogue**.

### Who does what

- **Recording** groups, plans and sessions is done by the site's Compliance Officer and Plant Manager, or by whoever holds the **CISO appointment** in Governance for the site or for the organisation. There is no assignment: whoever gets there first records it.
- The Internal Auditor and the External Auditor also **read** the plan, sessions and coverage: they are numbers and proof files, not personal data. For critical roles and the board they also see the participants' names, the same ones already held in Governance: they are the proof NIS2 Art. 20 requires.
- Other roles only see the **Course catalogue**.

### 1. Course catalogue

For each course set:

- **Type**: course, awareness campaign or phishing simulation;
- **Audience**: staff, critical roles or management body;
- **Validity (months)**: after how many months the session must be repeated (e.g. 12 = every year); empty = does not expire;
- **Mandatory**: mandatory staff courses count towards coverage;
- **Scope**: **organisation**, if the course applies to all sites (e.g. standard hygiene: you enter it only once), or **selected sites only** for specific courses. Organisation courses are managed by those with an organisation-wide scope; a plant manager creates and edits the courses of their own sites. A site's plan and sessions offer the organisation courses and that site's courses.
- **Competency granted** and **level** (critical roles and management body only, optional): participants with an account receive this competency on their competency profile (ISO 27001 cl. 7.2). The suggested names are those of the roles' competency requirements.

A course already in a plan or with recorded sessions cannot be deleted: **archive** it instead.

**Controls proven by sessions.** At the top of the catalogue there is a single setting, valid for all courses: for each audience, which controls a session proves (e.g. staff → ACN PR.AT-01, ISO A.6.3, TISAX ISA-2.1.3; critical roles → ACN PR.AT-02). Whoever manages the organisation edits it, searching the control by code; others see it read-only. Controls are not chosen course by course and the frameworks are not modified. The initial values are loaded with the `load_training_evidence_controls` command.

### 2. Target groups

For the site, enter the groups of people to be trained with their **number** (e.g. "Production: 240", "Offices: 45"). No names or employee data are entered. When the number changes, update it: the update date is set automatically. A group not rechecked for over 6 months is flagged **to be rechecked**, because coverage is computed on that number.

### 3. Training plan

1. In the **Plan** tab choose the year and click **Create the site plan** (whoever manages the organisation can also create the **organisation plan**, which applies to every site).
2. Click **Link document** and choose the plan document managed in **Documents**: approval follows the document workflow. The approved plan is the document required by ISO 27001 A.6.3.
3. Click **Add item** for each activity: course, due date and target groups.

Each item shows its status (**Planned**, **Due soon** within 30 days, **Overdue**, **Done**), the number of sessions and the coverage achieved.

**Reminders.** Every morning, for items with no session that are due within 30 days or already overdue, a **task is opened for the site's Compliance Officer** and a notification is sent to those who follow training. The task closes on its own when you record the session. Item due dates also appear in the **Activity Schedule**.

### 4. Recording a session

1. In the **Sessions** tab click **Record session**.
2. Choose the course and the date. The plan item is recognised automatically; if there is more than one you can choose it.
3. Select the groups involved and enter the **people trained**. The people to train are proposed from the total of the groups and can be corrected.
   For a **phishing simulation** enter the e-mails sent, clicks and reports instead.
4. Attach the **proof file** (attendance sheet, e-learning export, campaign report). It is mandatory: participants' names are only in the file, the platform stores the numbers.
5. Click **Record**.

The file becomes **evidence** expiring after the course's validity, **automatically linked to the controls set for the course's audience**, at the session's site and **only for the frameworks applied at the site** (e.g. ACN PR.AT-01 only at NIS2 sites, ISA-2.1.3 only at TISAX sites). The confirmation message shows how many controls were linked and lists those of an applied framework that are not instantiated or are excluded from the SoA.

The proof file cannot be replaced: if it is wrong, delete the session and record it again. A session whose proof supports controls already assessed cannot be deleted (only a superuser can). Rows marked **historical, no proof** come from the migration of the old per-person data: they only carry counts.

### 5. Critical roles and management body

For courses whose audience is **critical roles** or **management body**, the session records **who attended**, not groups:

1. In the recording form, after the course and date, two lists appear: the **role holders** active at the site (with their roles) and the **serving members of governing bodies** of the site or the organisation (board members carry the Board label). The lists depend on the session date: they show who was in office that day.
2. Tick who attended. People trained is the number of participants (someone who is both a member and a role holder counts once); people to train, if you leave it empty, is the same number.
3. Attach the proof file (signature sheet, certificates) and record.

If the course grants a **competency**, those with an account receive it, backed by the session's proof and with the same expiry. A higher level they already hold is not lowered. If you delete the session, the competency goes back to what it was. Participants cannot be changed: if they are wrong, delete the session and record it again.

**Management body training (NIS2 Art. 20).** In the **Sessions** tab a panel lists the serving members of the site's or organisation's board-type bodies: in green those with valid training (with the date it is valid until), in red those still to be trained. What counts is attending a still-valid course whose audience is "management body". Members are managed in **Governance → Governing bodies**.

### Where to see the results

- **Reporting → KPI**, "Training and awareness" section: coverage by course and site, plan progress, overdue items, latest phishing simulations and training to repeat.
- **KPIs** computed automatically, which security objectives can link to: mandatory training coverage, plan progress, overdue items, phishing click and report rates, management body training.
- **Operations Center**: flags overdue plan items.
- **Audit pack** (Audit Preparation): `07_training` folder with the site's plan, sessions with the evidence reference, coverage and groups, participants in critical-role and board sessions, board training status (`board_training.csv`).

---

## 15. Business Continuity (M16)

[Screenshot: BCP plan list]

### How to create a BCP plan

1. Go to **Governance → BCP → New plan**
2. Fill in:
   - **Plan name** (e.g. "BCP Plan — Production line B — South Plant")
   - **Scope**: critical processes covered by the plan (select from BIA)
   - **Plan owner**: person responsible for maintenance
   - **Target RTO** and **Target RPO**: the values the plan must guarantee
3. Click **Save draft**

### Link with BIA RTO/RPO

In the **Covered processes** section of the BCP plan, for each selected process the comparison is shown between:

- **RTO required by BIA**: the maximum tolerable declared in the critical process
- **RTO guaranteed by BCP**: what the plan can actually guarantee

If the BCP guarantees an RTO greater than the one required by the BIA, an orange warning appears requiring review. The system does not block saving but requires an explicit justification.

### Test types

The plan must be tested periodically. The available test types are:

| Type | Description |
|------|-------------|
| **Tabletop** | Paper/discussion simulation. Participants in a meeting room, no real systems involved |
| **Simulation** | Partial simulation with some real systems in test mode, without interrupting production |
| **Full** | Complete test with plan activation on real systems, without impact on normal production |
| **Drill** | Unannounced exercise to test the team's real response times |

To register a test: from the plan record click **New test**, select the type, date, participants and outcome.

### What happens if the test fails (automatic PDCA)

If the test is registered with outcome **Failed** or **Partially passed**:

1. A PDCA cycle is automatically created with starting phase PLAN
2. The PDCA is assigned to the BCP plan owner
3. The owner must fill in the action plan within 30 days
4. The BCP plan remains in "To be updated" status until the PDCA is closed positively

### Plan expiry and alerts

Every BCP plan has a mandatory review date (typically annual). As the date approaches:

- **30 days before**: email notification to the plan owner
- **At expiry**: the plan moves to "Expired" status with a red badge. A review task is automatically created
- If the expired plan covers processes with MTPD < 48 hours, an escalation notification is sent to the Plant Manager

---

## 16. Activity Schedule

[Screenshot: schedule with calendar view]

### How to read the deadline calendar

Go to **Operations → Schedule**. The page shows all deadlines in the selected period (default: next 30 days), ordered by date. For each deadline you see:

- **Type** of deadline (document, evidence, task, assessment, BCP plan, training course, etc.)
- **Name** of the item
- **Date** of the deadline
- **Owner** responsible
- **Status** with coloured badge (see below)

You can switch between list view and calendar view by clicking the icons in the top right.

### Filters by type and period

In the filter bar above the list you can filter by:

- **Type**: select one or more types of deadline (documents, evidence, tasks, assessments, BCP, training)
- **Period**: this week / this month / next 30 days / next 90 days / custom range
- **Owner**: filter by the deadline responsible
- **Plant**: filter by site (if you have multi-plant access)

### Badge colours

| Colour | Meaning |
|--------|---------|
| **Green** | Valid — no action required, deadline far away |
| **Yellow** | Expiring — less than 30 days remaining. Check and plan the action |
| **Red** | Overdue — the date has already passed. Urgent action required |

### How to navigate directly to the item from the deadline

Click on the name of any deadline in the list to open the record of the relevant item directly (e.g. clicking on an expiring piece of evidence opens the evidence record). There is no need to navigate manually through the menus.

---

## 17. Mandatory Documents

[Screenshot: mandatory documents page]

### How to link a document to a regulatory requirement

Mandatory documents are those explicitly required by a regulatory framework (e.g. ISO 27001 requires an "Information security policy"). To link an existing document to a requirement:

1. Go to **Compliance → Mandatory documents**
2. Find the regulatory requirement in the list
3. Click **Link document** next to the requirement
4. Search for and select the appropriate document from the document library (M07)
5. Save

If the document does not yet exist click **Create document** to start the creation workflow in M07.

### Status traffic light

For each regulatory requirement in the list, the traffic light shows the status of the linked document:

| Traffic light colour | Meaning |
|---------------------|---------|
| **Green** | Document present, approved and valid (not expired) |
| **Yellow** | Document present and approved but expiring within 30 days — plan the revision |
| **Red** | Document present but expired — urgent update required |
| **Grey** | Document missing — no document linked to this requirement |

Requirements with a grey traffic light negatively impact the framework compliance KPI.

### How to add a missing document

When the traffic light is grey (missing document):

1. Click on the requirement
2. Click **Create and link document** to start the creation wizard
3. The system automatically pre-fills the suggested title, the reference framework and the regulatory fields of the document
4. Complete the missing fields (owner, reviewer, approver) and upload the file
5. The document starts in Draft status and follows the normal approval workflow (M07)
6. Once approved, the traffic light automatically turns green

---

## 18. Email Notifications

### When notifications arrive

The platform sends automatic email notifications based on events. The main ones:

| Event | Recipients |
|-------|-----------|
| Task assigned | Owner of the recipient role |
| Task expiring (7 days) | Role owner + responsible |
| Task overdue | Owner + responsible + Compliance Officer (after 14 days) |
| Audit finding opened | Responsible of the audited area |
| Finding expiring (30/90/180 days) | Finding owner |
| Imminent audit (7 days) | Auditor + Compliance Officer |
| NIS2 incident — T+24h timer | CISO + Compliance Officer |
| NIS2 incident — T+72h timer | CISO + Compliance Officer + Plant Manager |
| Risk with score > 14 | Risk Manager + Plant Manager |
| Document expiring (30 days) | Document owner |
| Evidence expired | Owner of the linked control |
| Mandatory vacant role | Compliance Officer + Plant Manager |
| Supplier assessment expiring (30 days) | Internal contact |

Some notifications are mandatory and cannot be disabled (e.g. NIS2 timers, critical task escalation, red risks).

### How they change based on the profile assigned to the role

The notifications sent for a role depend on the **notification profile** assigned to that role (configured in Settings). A role with "Essential" profile receives only mandatory notifications and critical deadlines. A role with "Full" profile also receives periodic digests and notifications on reference modules.

### How to configure preferences (admin only)

Go to **Settings → Notification profiles**:

1. Select the profile to modify or click **New profile**
2. Configure for each event type: active / inactive, frequency (immediate / daily digest / weekly digest)
3. Assign the profile to the roles that should use it
4. Save

The configuration applies immediately. Changes are not retroactive on notifications already sent.

---

## 19. Governance (M00)

[Screenshot: regulatory roles org chart]

### How to assign a regulatory role

Regulatory roles are positions required by frameworks (e.g. CISO, DPO, Risk Owner, Asset Owner). To assign a holder:

1. Go to **Governance → Org chart**
2. Find the role to assign (optionally use the filter by framework or plant)
3. Click **Assign holder**
4. Select the user from the list
5. Set:
   - **Start date**: from when the assignment takes effect
   - **Expiry date** (optional): useful for temporary assignments or planned rotations
6. Click **Confirm assignment**

The assignment is recorded in the audit trail. The user receives an email notification with the role's responsibilities.

### How to replace a holder (succession)

If a holder retires, changes function or leaves the company, use the succession mechanism:

1. From the role record click **Manage succession**
2. Select the new holder
3. Set the **transition date**
4. The system automatically handles the overlap: until the transition date the old holder remains active, from the next day the new one takes over
5. Click **Confirm succession**

The old holder receives an end-of-assignment notification. The new holder receives a start-of-assignment notification with the list of responsibilities.

### How to terminate a role

If a position is no longer required (e.g. change in regulatory scope):

1. From the role record click **Terminate role**
2. Enter the **reason** (mandatory — e.g. "Role removed after TISAX 2026 scope review")
3. Set the **end date**
4. If there are open tasks assigned to this role, the system asks how to handle them (reassign to another role or leave open)
5. Click **Confirm**

### Governing bodies (board, committee, top management)

Go to **Governance → Roles & bodies** and scroll to **Governing bodies**. This is the register of who holds and approves the management review (ISO 27001 §5.1, §9.3).

1. **+ New body**: name, **type** (Board of directors, Security committee, Top management), **scope** (whole organisation, or the sites it governs: with several legal entities create one body each) and mandate. The board is flagged as **NIS2 management body** (Art. 20: it approves the risk-management measures, is accountable for them and must undergo training)
2. **+ Member**: full name, position (e.g. Chief Executive Officer), role in the body (chair, member, secretary), start and optional end of term. The **account** is optional: linking it lets the person approve this body's reviews in the app. There is no need to create accounts just to write a name in the minutes
3. Someone leaving the body is closed with **End term** (end date), not deleted: they stay in past minutes and among **former members**. **Delete** only corrects a wrong entry and is not allowed if the member appears in a review

Rules: only one chair in office at a time; the same account cannot be linked to two members of the same body in the same period. Super Admin and Compliance Officer manage the bodies, only those whose scope lies entirely within their own; other roles see them for the sites in their scope. Members and warnings (deactivated account, term expiring, missing chair) also appear in **Reporting → Access & responsibilities** and in the audit pack.


### Alerts for expiring roles and mandatory vacant roles

**Expiring roles**: if an assignment has an expiry date, 30 days beforehand the system sends a notification to the Compliance Officer and Plant Manager to plan renewal or succession.

**Mandatory vacant roles**: some roles are marked as mandatory in the framework (e.g. CISO for ISO 27001). If a mandatory role has no active holder:
- A red banner appears on the dashboard
- The compliance KPI is penalised
- An urgent assignment task is generated

---

## 20. Settings (Admin only)

[Screenshot: admin settings page]

This section is accessible only to users with the System Administrator or Super Admin role.

### SMTP email configuration

1. Go to **Settings → Email → SMTP configuration**
2. Fill in:
   - **SMTP host** (e.g. smtp.azienda.com)
   - **Port** (typically 587 for STARTTLS or 465 for SSL)
   - **Username** and **Password** — the password is encrypted with AES-256 (FERNET) before being saved
   - **Default sender** (e.g. noreply@grc.azienda.com)
   - **TLS/SSL**: select the encryption type
3. Click **Save configuration**

### Email connection test

After configuring SMTP:

1. On the same page click **Send test email**
2. Enter a recipient email address for the test
3. Click **Send**
4. Check for receipt. If the email does not arrive within 2 minutes click **View log** to see any SMTP error

### Notification profiles per role

Go to **Settings → Notifications → Profiles**:

1. The default profiles are: Essential, Standard, Full, Silent
2. To create a custom profile click **New profile**
3. For each notification type set: active/inactive and sending frequency
4. Assign the profile to roles via **Settings → Roles → select role → Notification profile**

### Deadline policies (23 configurable types)

Go to **Settings → Policies → Deadlines**. You can configure advance notice times and default deadlines for 23 types of items, including:

- Evidence by type (logs: 30d, scans: 90d, certificates: 365d)
- Documents by type (policy: 365d, procedure: 730d)
- Findings by severity (Major NC: 30d, Minor NC: 90d, Observation: 180d)
- Supplier assessments (12 months default)
- BCP plans (12 months default)
- Risk review (90d for red risks, 180d for yellow risks)

Modifying these values updates the calculations for all future items. Existing items retain the deadlines calculated at the time of creation.

---

## Roles and what you can do

### Compliance Officer

You have full access to all modules for all plants in your scope. You are responsible for:

- Keeping the controls library up to date (M03)
- Coordinating the document workflow (M07)
- Monitoring tasks and deadlines for the whole team (M08)
- Managing NIS2 incidents and ACN notifications (M09)
- Preparing documentation for audits (M17)
- Generating management reports (M18)

### Risk Manager

You have full access to risk modules. You are responsible for:

- Overseeing IT and OT risk assessment (M06)
- Validating the BIA and MTPD/RTO/RPO values (M05)
- Starting and monitoring PDCA cycles (M11)
- Receiving alerts on risks with score > 14

### Plant Manager

You have access to your plant. You are responsible for:

- Approving management-level documents (M07)
- Receiving escalations on overdue critical tasks
- Validating risk treatment decisions (M06)
- Participating in and approving the management review (M13)

### Plant Security Officer

You have operational access to your plant. You are responsible for:

- Updating control status (M03)
- Uploading evidence (M07)
- Filling in IT and OT risk assessments (M06)
- Opening and managing incidents (M09)
- Completing assigned tasks (M08)

### External Auditor

You have read-only access with a temporary token. You can:

- Consult controls and their status (M03)
- Download documents and evidence (M07)
- Export the evidence pack for your audit (M17)
- Every action you take is recorded in the audit trail

The token has an expiry: you will find the expiry date at the top of the interface. Contact the Compliance Officer if you need an extension.

---

## AI Engine — AI suggestions (M20)

> The AI module is enabled only if your administrator has activated this feature for your plant.

### How it works

When the AI module is active, you will see an **AI Suggestion** panel in some modules — incidents, assets, documents, tasks. The system analyses the context and proposes:

- A **suggested classification** (e.g. incident severity, asset criticality)
- A **draft text** (e.g. ACN notification, policy, RCA)
- A **proactive alert** (e.g. tasks with a high risk of slipping)

### What you need to do

The AI suggestion has no effect until you **explicitly confirm** it. You can:

- **Accept** the suggestion as-is — click **Use this suggestion**
- **Modify** the text and then click **Use modified version** — your version overwrites the AI's
- **Ignore** the suggestion and proceed manually — the panel closes with no effect

> Every interaction (suggestion received, final text adopted) is recorded in the audit trail to guarantee traceability of decisions. The AI never makes decisions autonomously.

---

## Reporting and export (M18)

### Reporting dashboard

Go to **Audit → Reporting**. You will find three levels of dashboard:

- **Operational**: task status, controls by framework and plant, deadlines
- **Risk**: aggregated heat map, top 10 open risks
- **Executive**: compliance %, PDCA maturity trend, audit readiness

### Generating a report

1. Select the report type (TISAX gap, NIS2 compliance, SOA ISO 27001, BIA executive)
2. Choose the plant and period
3. Select the report language
4. Click **Generate** — the report is produced in the appropriate format: **HTML** for summary reports, **CSV/Excel** for tabular exports (SOA, VDA ISA, NIS2 matrix)
5. The report is available for download in the **Generated reports** section

All generated reports are recorded in the audit trail.

---

## Operations Cockpit (M21)

[Screenshot: cockpit with prioritised insights and posture]

The Operations Cockpit is the dashboard that aggregates signals from all modules into prioritised **insights** and shows you the overall **security posture** with its trend. It is designed for daily work: it tells you *what to look at first* without having to open module by module.

### What insights are

Each insight is a signal generated by the **advisors** (rules that watch controls, risks, incidents, deadlines, audits, etc.) with a priority. For each insight you see a summary, the source module and the recommended action.

### Managing an insight (anti alert-fatigue)

From the insight card you can:

- **Accept**: take ownership of the insight until a date — it does not reappear until then
- **Snooze**: pause it until a date, with an optional note
- **Reopen**: bring back an insight previously accepted or snoozed

These actions prevent the same alerts from repeating endlessly and are recorded in the audit trail.

### AI explanation and assistant

If the AI module (M20) is enabled, you can request an **AI explanation** of the insight (data is anonymised before being sent) and use the **operations assistant** for context questions. The AI never applies changes on its own: the human-in-the-loop principle always applies.

### Posture and trend

The page shows an overall posture indicator and its evolution over time (posture trend), useful to understand whether the situation is improving or worsening.

### Who can access

The Operations Cockpit is restricted to governance and supervisory roles: Super Admin, Compliance Officer, Risk Manager, Internal Auditor and Plant Manager. It is not accessible to the External Auditor.

---

## OSINT Monitor

[Screenshot: OSINT exposure dashboard]

OSINT Monitor is the transversal module that monitors your organisation's **external exposure** — your domains and your suppliers' websites — using public sources (Open Source Intelligence). Unlike the other modules it is not tied to a single plant: it works at the **organisation** level.

### What it monitors

- The **primary domain** and any configured **additional domains**
- The **suppliers' websites** (M14), as OSINT entities of type *supplier*
- For each entity: subdomains, SSL certificates, DNS/WHOIS records and — if the keys are configured — reputation, breaches, blacklists and threat intelligence

### Scans and enrichers

The basic scans (SSL, DNS, WHOIS) are **free and always active**. Additional enrichments (HaveIBeenPwned, VirusTotal, AbuseIPDB, Google Safe Browsing, AlienVault OTX, abuse.ch) are enabled by entering the respective **API keys** in **OSINT → Settings** (all optional; use the `?` button on the settings page for the registration links). The keys are encrypted and never shown in clear text.

### Alerts and automatic actions

When a scan detects a relevant issue:

- A **critical alert on one of your domains** can automatically generate an **incident** (M09)
- An **alert on a supplier** can generate a **verification task** (M08) for the internal contact
- Findings can be routed to remediation and, if necessary, **escalated**

External-exposure notifications are intended for **internal staff only** (never the External Auditor).

### AI analysis

If the AI module (M20) is enabled, you can request attack-surface analysis, NIS2 briefings and board reports: the data is **anonymised** before being sent to the AI provider.

### Who can access

OSINT Monitor is restricted to Super Admin, CISO and Compliance Officer.

---

## Appendix: Frequently Asked Questions

**I cannot find a control that should be in my framework.**
Check that you have selected the correct plant in the selector at the top. If the framework is active for that plant but the control does not appear, contact the Compliance Officer — it may not have been generated during framework activation.

**I uploaded evidence but the control still shows "gap".**
Check that the evidence is linked to the correct control (evidence record → "Controls covered" section) and that the expiry date has not already passed.

**The NIS2 timer has started but the incident is not really a NIS2 incident.**
If you are the CISO, open the incident record and **exclude the NIS2 obligation** entering the reason: the deadlines lapse and the decision is recorded in the audit trail. While the incident remains 'to be assessed', after 30 minutes you receive a reminder alert to classify it.

**I completed a task but it keeps appearing as open.**
Some tasks close automatically when the action in the originating module is completed. If the task is manual, you must close it explicitly from the task record → **Mark as completed**.

**A document I had approved now shows as "under review".**
An extraordinary review trigger has been activated — likely linked to an incident, an audit finding or a regulatory change. Check the notes in the document record to understand the reason.

**I cannot set a control as N/A.**
For TISAX L3 controls the N/A status requires the signature of at least two roles (dual lock). If you are the first to approve, the control remains pending the second signature. If you are the sole owner, contact the CISO for co-signature.

**The AI suggestion no longer appears.**
The AI module may have been disabled by the administrator for your plant, or the specific feature may not be active. Contact the Compliance Officer or the System Administrator.

**I cancelled an audit by mistake. Can I restore it?**
No, the cancellation is irreversible. However, you can create a new audit for the same quarter and recreate any findings that were lost. Contact the Compliance Officer who can view the cancelled findings in the archive to retrieve the information.

**The score of my risk changed without me doing anything.**
The residual score is automatically recalculated when the status of linked controls changes. If evidence has expired, the control reverts to "partial" and this can increase the residual risk. Check the controls linked to the risk and update the evidence.

**I am not receiving email notifications.**
First check your spam folder. If emails are not arriving at all, contact the system administrator to verify the SMTP configuration and the notification profile assigned to your role.

**How can I see the change history for an asset or document?**
Every record has an **Audit trail** or **Change history** section at the bottom. Click on it to see all recorded actions with date, user and change detail.

**The audit programme shows the status "To be updated". What should I do?**
The "To be updated" status indicates that the programme has been created but some information (e.g. auditor not assigned to a quarter, missing dates) requires completion before the programme can be approved. Open the programme and look for the fields highlighted in yellow.
