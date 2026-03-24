# User Manual — GRC Platform

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

The selected language applies to the entire interface. PDF reports generated use the language active at the time of generation.

### Side menu: main sections and what they contain

[Screenshot: sidebar with expanded menu]

The left sidebar shows only the sections accessible based on your role. The main entries are:

| Entry | Contents |
|-------|----------|
| **Dashboard** | Compliance KPIs, risk heat map, upcoming deadlines, alerts |
| **Compliance** | Controls library (M03), documents (M07), evidence |
| **Risk** | IT/OT Assets (M04), BIA (M05), Risk Assessment (M06) |
| **Operations** | Incidents (M09), Tasks/Schedule (M08), PDCA (M11) |
| **Governance** | Org chart/Roles (M00), Lesson Learned (M12), Management Review (M13), Suppliers (M14), Training (M15), BCP (M16) |
| **Audit** | Audit Preparation (M17), Reporting (M18) |
| **Notifications** | Email notifications, preferences |
| **Settings** | Administrative roles only — SMTP, policies, notification profiles |

To expand or collapse a section click on the section title. The menu state is remembered between sessions.

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
| **N/A** | The control does not apply to your plant's context. Requires a mandatory note. For TISAX L3 it requires the signature of two roles and expires after 12 months |

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

### How to download SOA ISO 27001, VDA ISA TISAX, NIS2 Matrix

[Screenshot: compliance export page]

1. Go to **Compliance → Controls library**
2. Click the **Export** button (download icon) in the top right of the page
3. Select the type of export:
   - **SOA ISO 27001** — Statement of Applicability with all Annex A controls and their status
   - **VDA ISA TISAX** — VDA Information Security Assessment table
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

The CISO has 30 minutes from incident creation to confirm or exclude the notification obligation via the **Exclude NIS2 obligation** button. If there is no response within 30 minutes, the system assumes the notification is required and the timers remain active.

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
| **DO → CHECK** | Attached evidence documenting the action performed (mandatory file) |
| **CHECK → ACT** | Result of the verification (descriptive text) + Chosen outcome: **ok** / **partial** / **ko** |
| **ACT → CLOSED** | Standardisation: documentation of the adopted solution so that it is replicable (minimum 20 characters) |

### What happens if CHECK outcome = ko

If in the CHECK phase the outcome is **ko** (the solution did not work):

1. The cycle does not advance to ACT but automatically returns to the **DO** phase
2. A note is added to the cycle log with the date of the failure
3. A new action plan must be filled in for the DO phase
4. The DO cycle counter is incremented to track how many iterations were needed

There is no limit to the number of DO-CHECK iterations, but the system signals cycles with more than 3 iterations to the Compliance Officer.

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

### How to create a review

1. Go to **Governance → Management Review → New**
2. Fill in:
   - **Year and number**: e.g. "2026 — Rev. 1/2026"
   - **Planned date**
   - **Participants**: select the roles involved (Plant Manager, CISO, Risk Manager, CO)
3. The system automatically adds the mandatory agenda items (see below)
4. You can add extra items via **Add agenda item**
5. Click **Save draft**

### Mandatory agenda items (ISO 27001 cl.9.3)

ISO 27001 clause 9.3 requires that the management review mandatorily includes a number of items. The system inserts them automatically into the draft:

- Status of actions from previous reviews
- Changes in the internal and external context relevant to the ISMS
- Feedback on ISMS performance (NCs, audits, monitoring, measurements)
- Feedback from interested parties
- Results of risk assessment and status of the treatment plan
- Opportunities for continual improvement

It is not possible to close a review if any of these items does not have at least one comment or recorded decision.

### How to record decisions

For each agenda item:

1. Click on the item to expand it
2. Enter the **discussion summary**
3. Click **Add decision** to record the actions approved by management
4. For each decision specify: responsible, action to be taken, deadline

Decisions with a responsible and deadline are automatically converted into tasks in M08 and, if structural, into PDCA cycles in M11.

### Closure and approval

1. After completing all mandatory items click **Submit for approval**
2. The Plant Manager receives an approval task
3. Once approved, the review becomes immutable
4. The meeting minutes are automatically generated as a hash- and timestamp-signed PDF, available in the **Generated documents** section of the review

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

Response deadlines are automatically calculated from the finding opening date based on these policies. For Major NC a PDCA cycle is also automatically created.

#### How to close a finding

1. From the finding record, after adopting the corrective actions, click **Propose closure**
2. Upload the **closing evidence** (mandatory for Major NC and Minor NC)
3. Enter the **closing comment**: describe the actions taken
4. The finding moves to "Under verification" status
5. The responsible auditor verifies the evidence and clicks **Confirm closure** or **Reopen finding** with a comment

#### How to download the audit report

From the in-progress or closed audit:
1. Click the **Report** button (PDF icon) in the top right of the audit page
2. Choose the report language
3. The system generates a PDF with: coverage summary, list of findings by type, closure status, trend compared to the previous audit
4. The PDF is available immediately for download

---

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

### How to register a supplier

1. Go to **Governance → Suppliers → New supplier**
2. Fill in:
   - **Company name** and **VAT number**
   - **Category**: IT, OT, Professional Services, Logistics, other
   - **Criticality**: how critical it is to operational continuity (1–5)
   - **Internal contact**: select the role responsible for managing the supplier
   - **Supplier contact**: name and email of the contact at the supplier
   - **Data processing**: flag if the supplier processes personal data (entails additional GDPR obligations)
3. Click **Save**

### Assessment: planned → in progress → completed → approved/rejected

Each critical supplier must be periodically evaluated through an assessment. The flow is:

1. **Planned**: the assessment is created with a target date. The internal contact receives a task
2. **In progress**: the assessment is started. The supplier receives (via email or temporary access) the questionnaire to fill in
3. **Completed**: the supplier has answered all questions. The internal contact receives the questionnaire for review
4. **Approved** or **Rejected**: the Compliance Officer or Risk Manager expresses the final judgement (see below)

### Governance, security, BCP score

The assessment questionnaire evaluates the supplier on 3 dimensions:

| Dimension | What it evaluates |
|-----------|------------------|
| **Governance** | Organisational structure for security, internal policies, defined responsibilities, internal audits |
| **Security** | Implemented technical controls, vulnerability management, incident response, certifications (ISO 27001, TISAX) |
| **BCP** | Operational continuity plans, declared RTO/RPO, continuity tests performed, infrastructure redundancies |

Each dimension produces a score of 0–100. The overall score is the weighted average of the three dimensions.

### Approval and rejection with mandatory notes

**Approval:**
1. From the completed assessment record click **Approve supplier**
2. Enter the **approval notes** (mandatory — e.g. "Supplier certified ISO 27001, adequate score. Next review in 12 months")
3. Set the **approval expiry date** (typically 12 months)
4. Click **Confirm approval**

**Rejection:**
1. From the completed assessment record click **Reject supplier**
2. Enter the **rejection notes** (mandatory — must be a detailed justification for the decision)
3. Click **Confirm rejection**

The rejection generates a task for the internal contact to manage the transition (supplier replacement or remediation plan).

---

## 14. Training (M15)

[Screenshot: personal training plan]

### How to see your mandatory courses

1. Go to **Governance → Training → My plan**
2. You will find the list of mandatory courses for your role and plant, with:
   - Course name
   - Status: To be completed / In progress / Completed / Expired
   - Expiry date (or completion date if already done)
   - Type: online (KnowBe4), in-person, documentary

### Completion and deadlines

- Click **Start course** on online courses to open the module directly on KnowBe4
- Completions are synchronised automatically every night — if you have completed a course on KnowBe4 and it does not yet appear as completed in the GRC Platform, wait until the next day or contact the Compliance Officer
- An expired course (completed but requiring periodic renewal) appears with a red badge and generates a renewal task

### Skills gap analysis

Go to **Governance → Training → Gap analysis**. The page shows:

- The competency requirements for each role and plant
- The competencies actually certified (completed courses, uploaded certificates)
- Highlighted gaps: required competencies not yet covered by any completed course

The Compliance Officer can use this view to plan training sessions and address priority gaps.

### KnowBe4 synchronisation (admin only)

Go to **Settings → Integrations → KnowBe4**:

1. Configure the KnowBe4 API key
2. Click **Sync now** to force immediate synchronisation of completions
3. Check the last synchronisation log to identify any errors

Automatic synchronisation occurs every night at 02:00.

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

### Generating a PDF report

1. Select the report type (TISAX gap, NIS2 compliance, SOA ISO 27001, BIA executive)
2. Choose the plant and period
3. Select the report language
4. Click **Generate** — the PDF is signed with a timestamp and hash
5. The report is available for download in the **Generated reports** section

All generated reports are recorded in the audit trail.

---

## Appendix: Frequently Asked Questions

**I cannot find a control that should be in my framework.**
Check that you have selected the correct plant in the selector at the top. If the framework is active for that plant but the control does not appear, contact the Compliance Officer — it may not have been generated during framework activation.

**I uploaded evidence but the control still shows "gap".**
Check that the evidence is linked to the correct control (evidence record → "Controls covered" section) and that the expiry date has not already passed.

**The NIS2 timer has started but the incident is not really a NIS2 incident.**
The CISO has 30 minutes to exclude the notification obligation. If you are the CISO, open the incident record and click **Exclude NIS2 obligation** entering the reason. The timers stop and the decision is recorded in the audit trail.

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
