# URL Shortener Backend

A FastAPI-based URL shortener with:

- custom aliases
- optional link expiry
- redirect click tracking
- Supabase persistence
- Upstash Redis caching
- Redis-backed rate limiting

This backend exposes a small HTTP API for creating short links, redirecting them, and reading click stats.

## Features

- Create a short URL for any destination URL
- Provide a custom alias up to `10` characters long
- Set an optional expiry in minutes
- Redirect with permanent `301` responses
- Track clicks with hashed IP, referrer, and user agent
- Cache redirect lookups in Redis
- Enforce expiry even when cached
- Fail soft if Redis is temporarily unavailable

## Tech Stack

- Python
- FastAPI
- Uvicorn
- Supabase
- Upstash Redis
- python-dotenv

## Project Structure

```text
backend/
├── cache.py
├── database.py
├── main.py
├── rate_limiter.py
├── render.yaml
├── requirements.txt
└── utils.py
```

## Requirements

- Python 3.10+
- A Supabase project
- An Upstash Redis database

## Environment Variables

Create a `.env` file in the project root:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
UPSTASH_REDIS_REST_URL=https://your-upstash-db.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-upstash-token
BASE_URL=http://127.0.0.1:8000
```

### Variable Notes

- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase API key used by the backend
- `UPSTASH_REDIS_REST_URL`: Upstash Redis REST endpoint
- `UPSTASH_REDIS_REST_TOKEN`: Upstash Redis REST token
- `BASE_URL`: public base URL used when returning the generated short URL

## Database Schema

This app expects at least two Supabase tables: `urls` and `clicks`.

### `urls` table

Recommended columns:

| Column | Type | Notes |
| --- | --- | --- |
| `short_code` | `varchar(10)` or `text` | Unique short code |
| `original_url` | `text` | Destination URL |
| `expires_at` | `timestamp` or `timestamptz` | Optional expiry |

Recommended constraints:

- `short_code` should be unique
- If you keep `varchar(10)`, aliases longer than 10 characters will be rejected by the API

### `clicks` table

Recommended columns:

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `uuid` or serial | Optional primary key |
| `short_code` | `text` | The code that was visited |
| `ip_hash` | `text` | SHA-256 hash of the visitor IP |
| `referrer` | `text` | Optional referer header |
| `user_agent` | `text` | Optional user-agent header |
| `created_at` | `timestamp` or `timestamptz` | Optional default timestamp |

## Installation

```bash
pip install -r requirements.txt
```

## Running Locally

```bash
uvicorn main:app --reload
```

Default local server:

```text
http://127.0.0.1:8000
```

## API Endpoints

### `POST /shorten`

Creates a new short URL.

#### Query Parameters

| Parameter | Required | Type | Description |
| --- | --- | --- | --- |
| `original_url` | Yes | `string` | The destination URL |
| `custom_code` | No | `string` | Custom alias, max length `10` |
| `expiry_minutes` | No | `integer` | Number of minutes before the link expires |

#### Example Request

```http
POST /shorten?original_url=https://github.com&custom_code=gh123&expiry_minutes=5
```

#### Example Response

```json
{
  "short_url": "http://127.0.0.1:8000/gh123",
  "expires_at": "2026-03-30T15:30:00.000000"
}
```

#### Validation Rules

- `custom_code` must be `10` characters or fewer
- If a custom alias already exists, the API returns `400`
- If the client exceeds the rate limit, the API returns `429`

### `GET /{code}`

Redirects to the original URL with HTTP `301`.

Behavior:

- checks Redis cache first
- validates cached expiry before redirecting
- falls back to Supabase if cache is missing or stale
- deletes stale cache entries for expired links
- logs the click in the background

If the code does not exist or the link has expired, the API returns `404`.

### `GET /stats/{code}`

Returns click analytics for a short code.

#### Example Response

```json
{
  "total_clicks": 2,
  "data": [
    {
      "short_code": "gh123",
      "ip_hash": "...",
      "referrer": "http://localhost:5173/",
      "user_agent": "Mozilla/5.0 ..."
    }
  ]
}
```

## Rate Limiting

Rate limiting is implemented with Redis sorted sets.

Current default behavior:

- limit: `10` requests
- window: `60` seconds

If Redis is unavailable, the backend keeps serving requests instead of failing with `500`.

## Caching

Redirect responses are cached in Redis.

Cached payload includes:

- `original_url`
- `expires_at`

Important behavior:

- cached links do not bypass expiry checks
- cache TTL is trimmed to the remaining life of the short link
- old stale cache entries are deleted when detected

## Expiry Behavior

When `expiry_minutes` is provided:

- the API stores an expiry timestamp in Supabase
- expired links stop redirecting
- expired cached entries are invalidated before redirecting

When no expiry is provided:

- the short link does not expire automatically

## Deployment

This repository includes a `render.yaml` for deploying on Render.

### Render Service

```yaml
services:
  - type: web
    name: url-shortener-api
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn main:app --host 0.0.0.0 --port $PORT"
```

Before deploying, set the same environment variables in Render:

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `UPSTASH_REDIS_REST_URL`
- `UPSTASH_REDIS_REST_TOKEN`
- `BASE_URL`

## Error Responses

Common cases:

- `400 Bad Request`: alias already taken or alias too long
- `404 Not Found`: short code does not exist or has expired
- `429 Too Many Requests`: rate limit exceeded
- `500 Internal Server Error`: unexpected backend failure

## Notes

- Generated short codes currently use 6 characters
- Custom aliases are limited to 10 characters to match the current database schema
- If you want longer aliases, update both the DB column length and the validation in `main.py`
- `BASE_URL` should match your deployed API domain in production

## Future Improvements

- add URL validation for `original_url`
- add delete and update endpoints
- add better analytics aggregation
- add test coverage
- add admin authentication

## License

Add your preferred license here.
