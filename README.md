# API-Practice

Practice repository demonstrating a simple Supabase data pipeline: fetch raw session data, compute per-employee metrics, and upsert results back to the database.

## Features

- Fetch session data from Supabase `sessions_raw` table with pagination
- Compute per-employee metrics:
  - `completed_count`: Number of completed sessions
  - `cancelled_count`: Number of cancelled sessions
  - `days_since_last_completed`: Days since most recent completed session
- Upsert computed metrics to `session_metrics` table
- Retry logic with exponential backoff for transient network errors
- Timezone-aware UTC datetime handling throughout

## Project Structure

```
API-Practice/
├── src/
│   └── app/
│       ├── compute_session_metrics.py  # Main pipeline logic
│       ├── config.py                   # Configuration with pydantic-settings
│       ├── datetime_utils.py           # UTC datetime utilities
│       ├── logger.py                   # Logging configuration
│       ├── supabase_client.py          # Supabase client factory
│       └── types.py                    # TypedDict definitions
├── scripts/
│   └── run_session_metrics.py          # CLI runner
├── tests/
│   ├── conftest.py                     # pytest fixtures
│   ├── test_config.py                  # Config module tests
│   ├── test_datetime_utils.py          # Datetime utility tests
│   └── test_integration.py             # Integration tests with real API
├── .env.example                        # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md
```

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd API-Practice
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create `.env` file from template:
   ```bash
   cp .env.example .env
   ```

5. Edit `.env` with your Supabase credentials:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-anon-key
   ```

## Usage

### Run the metrics pipeline

```bash
# Normal mode (INFO level logging)
python -m scripts.run_session_metrics

# Debug mode (DEBUG level logging)
python -m scripts.run_session_metrics --debug
```

### Run tests

```bash
# Run all tests
python -m pytest

# Run with verbose output
python -m pytest -v

# Run specific test file
python -m pytest tests/test_config.py -v
```

## Configuration

Environment variables are managed via `pydantic-settings`:

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Your Supabase project URL |
| `SUPABASE_ANON_KEY` | Yes | Your Supabase anonymous/public key |

Configuration is loaded from:
1. Environment variables
2. `.env` file (if present)

## Database Schema

### sessions_raw (input table)
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| employee_id | text | Employee identifier |
| status | text | Session status: "completed", "cancelled", "scheduled" |
| end_at | timestamptz | Session end time (for completed sessions) |

### session_metrics (output table)
| Column | Type | Description |
|--------|------|-------------|
| employee_id | text | Primary key |
| completed_count | integer | Number of completed sessions |
| cancelled_count | integer | Number of cancelled sessions |
| days_since_last_completed | integer | Days since last completed session (nullable) |
| computed_at | timestamptz | When metrics were computed |

## Error Handling

The pipeline includes retry logic for transient errors:
- Network connection errors (`ConnectError`)
- Request timeouts (`TimeoutException`)

Retry strategy:
- Maximum 3 attempts per operation
- Exponential backoff: 1s, 2s, 4s delays between retries
- Non-retryable errors (auth, schema) fail immediately

## Requirements

- Python 3.11+
- Supabase account with configured tables
- RLS policies allowing `anon` role to SELECT from `sessions_raw` and INSERT/UPDATE on `session_metrics`
