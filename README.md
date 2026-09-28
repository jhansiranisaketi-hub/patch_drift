# PatchDrift

**Autonomous API Drift Detection, Self-Healing & Permanent Code Remediation**

> Detect the drift. Heal the request. Remember the fix.

---

## What is PatchDrift?

Modern applications depend on third-party and internal APIs. When those APIs change — renamed fields, removed parameters, restructured responses — applications break silently or loudly.

PatchDrift sits between your application and external APIs. When a breaking change causes a failure, PatchDrift:

1. Detects that the failure is caused by API drift (not a bug in your code)
2. Analyzes what changed between the old and new API contract
3. Generates a compatibility adapter automatically
4. Verifies the adapter in a sandbox before using it
5. Retries the request — keeping your application running
6. Stores the successful migration in **Hindsight memory**
7. Reuses that memory for future identical failures
8. Eventually generates a permanent source-code fix and opens a **GitHub Pull Request**

---

## The Problem

```
Application sends:
{
  "customer_id": 101,
  "billing_address": "Hyderabad"
}

API now expects:
{
  "customer_id": 101,
  "customer": {
    "address": {
      "billing": "Hyderabad"
    }
  }
}

Result: 400 Bad Request — Application breaks
```

Normally a developer has to investigate, understand, fix, test, and redeploy.

PatchDrift automates this as much as safely possible.

---

## How It Works

```
Application
     ↓
PatchDrift Gateway
     ↓
External API
     ↓
400 Error
     ↓
Drift Detection
     ↓
Schema / Change Analysis
     ↓
┌────────────────────────┐
│  Hindsight Recall?     │
│  Yes → Reuse adapter   │
│  No  → AI Investigation│
└────────────────────────┘
     ↓
Adapter Generation
     ↓
Sandbox Verification
     ↓
PASS → Retry Request → 200 OK
FAIL → Human Review
     ↓
Hindsight Retain
     ↓
Permanent Code Fix → GitHub PR
```

---

## Core Features

### 1. API Drift Detection
Monitors API responses. Distinguishes between application bugs and API contract changes using error signals like `Unknown field`, `Missing required parameter`, `Deprecated field`.

### 2. Schema & Change Analysis
Compares old and new API contracts to identify:
- Renamed fields
- Removed fields
- Moved/nested fields
- New required fields
- Data type changes

### 3. AI Investigation
An LLM agent analyzes the error, old request, new schema, and Hindsight memories to understand exactly what changed and how to fix it.

### 4. Adapter Generation
Generates a field-mapping transformation that converts the old request format into the new expected format — without touching application code.

```
billing_address  →  customer.address.billing
```

### 5. Sandbox Verification
The adapter is tested against a mock/sandbox API before being used in production. AI-generated fixes are never applied blindly.

```
Generated Adapter → Sandbox → PASS → Safe to use
                            → FAIL → Human Review
```

### 6. Runtime Self-Healing
Once verified, PatchDrift retries the original failed request using the adapter. The application continues functioning transparently.

### 7. Hindsight Memory
After a successful migration, PatchDrift stores the full context:
- Which API changed
- What the old and new formats were
- Which adapter was used
- Verification result and outcome

On the next failure, Hindsight is checked first — avoiding redundant AI investigation.

### 8. GitHub Pull Request Generation
After runtime healing, PatchDrift generates a permanent source-code fix, runs tests, and opens a GitHub Pull Request for developer review and merge.

---

## Hindsight: Retain, Recall, Reflect

| Phase | What Happens |
|---|---|
| **Retain** | After a successful fix, store the full migration context |
| **Recall** | On a new failure, search memory for a matching past migration |
| **Reflect** | Analyze patterns across migrations to improve future handling |

Hindsight turns PatchDrift from a one-time repair tool into a learning system.

---

## Architecture

```
┌──────────────────────────┐
│       Application        │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│    PatchDrift Gateway    │  ← FastAPI proxy
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│      External API        │
└────────────┬─────────────┘
             ↓
        API Response
        ┌────┴────┐
      200 OK    Error
                  ↓
       ┌────────────────────┐
       │   Drift Detector   │
       └─────────┬──────────┘
                 ↓
       ┌────────────────────┐
       │ Investigation Agent│
       └──────┬──────┬──────┘
              ↓      ↓
       Schema Diff  Hindsight
              ↓      ↓
       ┌────────────────────┐
       │  Adapter Generator │
       └─────────┬──────────┘
                 ↓
       ┌────────────────────┐
       │ Sandbox Verification│
       └──────┬──────┬──────┘
            PASS    FAIL
              ↓      ↓
         Self-Heal  Human Review
              ↓
         Hindsight Retain
              ↓
         Permanent Code Fix
              ↓
           GitHub PR
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend / Gateway | Python, FastAPI |
| AI Investigation | OpenAI GPT-4 / AWS Bedrock |
| Memory (Hindsight) | In-memory dict / SQLite |
| Schema Comparison | JSON diff, OpenAPI |
| Sandbox Testing | FastAPI mock endpoints |
| PR Automation | PyGithub / GitHub API |
| Frontend | HTML, Tailwind CSS, Vanilla JS |

---

## Project Structure

```
patch_drift/
├── main.py              # PatchDrift gateway — entry point
├── mock_api.py          # Mock Payment API V1 and V2
├── drift_detector.py    # Detects API drift from error signals
├── adapter.py           # Generates and applies field adapters
├── hindsight.py         # Retain, Recall, Reflect memory store
├── sandbox.py           # Verifies adapter against mock V2
├── pr_generator.py      # Generates code diff and GitHub PR
├── frontend/
│   └── index.html       # Dashboard UI
└── requirements.txt
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/call` | Proxy a request through PatchDrift |
| `GET` | `/status` | Last drift detection event |
| `GET` | `/hindsight` | All stored migrations |
| `POST` | `/generate-pr` | Trigger PR generation for latest migration |
| `GET` | `/health` | Service health check |

---

## Example Request Flow

**Request sent by application:**
```json
POST /call
{
  "api": "payment",
  "version": "v1_format",
  "payload": {
    "customer_id": 101,
    "billing_address": "Hyderabad"
  }
}
```

**PatchDrift detects drift, generates adapter, verifies, retries:**
```json
Response:
{
  "status": "healed",
  "original_error": "400 Unknown field: billing_address",
  "adapter_applied": {
    "billing_address": "customer.address.billing"
  },
  "verification": "PASS",
  "api_response": { "success": true, "transaction_id": "TXN_9182" },
  "hindsight": "stored"
}
```

---

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload --port 8000

# Open the dashboard
open frontend/index.html
```

---

## Demo Scenario

| Step | What Happens |
|---|---|
| 1 | App sends old-format request → V1 API → 200 OK |
| 2 | API switches to V2 — same request → 400 |
| 3 | PatchDrift detects drift signal in error |
| 4 | Schema diff identifies: `billing_address → customer.address.billing` |
| 5 | Adapter generated and tested in sandbox → PASS |
| 6 | Request retried with adapter → 200 OK |
| 7 | Migration stored in Hindsight |
| 8 | Same request sent again → Hindsight recall → instant fix |
| 9 | PR generated showing before/after code change |

---

## Types of API Drift Handled

| Type | Example |
|---|---|
| Field Rename | `billing_address` → `billingAddress` |
| Field Removal | `customer_id` no longer accepted |
| Field Movement | `billing_address` → `customer.address.billing` |
| New Required Field | Must now include `country: "India"` |
| Data Type Change | `amount: "500"` → `amount: 500` |
| Nested Schema | `user.email` → `user.contact.email` |

---

## Safety & Human-in-the-Loop

PatchDrift does not automatically apply every AI-generated change.

- Low confidence → escalate to human review
- Sandbox verification is mandatory before any retry
- Incorrect adapters could cause data corruption or failed transactions
- All migrations are logged and inspectable

---

## Limitations (MVP)

- Focused on JSON REST APIs
- Handles well-defined schema changes (field renames, moves, type changes)
- Complex business-logic changes require human review
- GitHub PR generation requires a configured GitHub token

---

## Future Enhancements

- Preventive monitoring: detect API changes before they break production
- Support for GraphQL, gRPC APIs
- Multi-API dependency tracking
- Automatic rollback on bad adapter
- CI/CD pipeline integration
- Organization-wide migration knowledge base

---

## One-Line Pitch

> PatchDrift is a memory-powered API reliability agent that detects breaking API changes, verifies compatibility fixes, self-heals requests at runtime, remembers successful migrations using Hindsight, and turns those learned fixes into permanent code changes through GitHub Pull Requests.
