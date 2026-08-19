# Mind-Mate: Digital Mental Health Risk Screening System

**Disclaimer:** *Mind-Mate is a non-diagnostic triage and screening tool designed for higher education environments. It does not provide clinical medical diagnoses. Final referral decisions are made by human professionals using the Human-in-the-Loop (HITL) dashboard.*

## 📖 Project Overview
Mind-Mate analyzes anonymized student text entries (journals, chat logs) to detect linguistic patterns associated with psychological distress. High-risk entries are automatically flagged and routed to a secure dashboard where authorized campus counselors can review the context and initiate outreach.

## 🏗️ System Architecture
The pipeline is designed with strict data privacy and decoupled microservices:

1. **PII Anonymization:** Raw text is scrubbed of Personally Identifiable Information (Names, Phone Numbers, Emails, Student IDs) using Microsoft Presidio and spaCy.
2. **NLP Risk Engine:** Scrubbed text is analyzed using Transformer-based NLP models to assign a risk score (0.0 - 1.0) based on sentiment and distress indicators.
3. **HITL Routing:** Cases exceeding the risk threshold are logged in the backend database.
4. **Counselor Dashboard:** A frontend UI where human reviewers evaluate flagged, anonymized text and trigger real-world referrals.

## 💻 Tech Stack
* **Backend Framework:** FastAPI (Python)
* **NLP & Privacy:** HuggingFace Transformers, spaCy, Microsoft Presidio
* **Database:** SQLite / SQLAlchemy (to be implemented)
* **Frontend:** (To be implemented by UI team)

## 🚀 Local Setup & Installation

### Prerequisites
* Python 3.10+
* Git

### 1. Clone the Repository
```bash
git clone [https://github.com/divyanshukumar3740-cmd/Mind-Mate.git](https://github.com/divyanshukumar3740-cmd/Mind-Mate.git)
cd Mind-Mate