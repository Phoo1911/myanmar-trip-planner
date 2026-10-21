# Development contract
- Read SPEC.md before changes. Keep Next.js/TypeScript/Tailwind, FastAPI and PostgreSQL.
- Never invent prices, availability, supplier confirmations, safety guarantees or credentials.
- Unintegrated offerings remain request_only; approval never means confirmed reservation.
- Validate model outputs server-side; secrets stay on the backend.
- Run pytest, frontend typecheck/build, and migration checks. Record actual results in VERIFICATION.md.
- Do not commit .env, receipts or customer data. Use synthetic fixtures.

- Verified operator-allocated inventory may confirm pay-on-site reservations through /reservations only. Never route inquiries through confirmation without contract authority, valid price and stock. Concurrency/idempotency/cancellation tests are required.
