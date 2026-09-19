# Third-Party Notices

FinPilot is built on top of permissively-licensed open-source projects.
This file records the dependencies installed during this build for transparency.

## Python (apps/api — installed 2026-09-19)

| Package           | Version  | License    |
|-------------------|----------|------------|
| fastapi           | 0.141.1  | MIT        |
| starlette         | 1.6.0    | BSD-3-Clause |
| uvicorn           | 0.53.0   | BSD-3-Clause |
| pydantic          | 2.13.5   | MIT        |
| pydantic-settings | 2.15.0   | MIT        |
| python-dotenv     | 1.2.3    | BSD-3-Clause |
| supabase          | 2.31.0   | MIT        |
| postgrest         | 2.31.0   | MIT        |
| storage3          | 2.31.0   | MIT        |
| httpx             | 0.28.1   | BSD-3-Clause |
| pytest            | 9.1.1    | MIT        |
| anyio             | 4.15.1   | MIT        |
| watchfiles        | 1.2.0    | MIT        |
| click             | 8.5.0    | BSD-3-Clause |
| cryptography      | 50.0.1   | Apache-2.0 OR BSD-3-Clause |
| cffi              | 2.1.1    | MIT        |

Full transitive list is in `apps/api/requirements.txt` (as installed into `.venv`).

## Node.js (apps/web — installed 2026-09-19)

| Package                | Version | License   |
|------------------------|---------|-----------|
| next                   | 15.5.25 | MIT       |
| react                  | 19.1.0  | MIT       |
| react-dom              | 19.1.0  | MIT       |
| typescript             | ^5      | Apache-2.0 |
| tailwindcss            | ^4      | MIT       |
| @tailwindcss/postcss   | ^4      | MIT       |
| eslint                 | ^9      | MIT       |
| eslint-config-next     | 15.5.25 | MIT       |
| shadcn/ui (components) | latest  | MIT       |
| Radix UI (radix)       | via shadcn | MIT    |

## Notes

- The Supabase CLI project is community/open source; the hosted Supabase service
  is SaaS (see supabase.com).
- No proprietary code is vendored into this repository.