# 실행 검증 기록 — 2026-10-21

## 저장소 및 재현 가능한 원격 검증
- 비공개 저장소: https://github.com/Phoo1911/myanmar-journey
- 검증한 코드 커밋: 6dbac1e1c575b80f4e836377ab10096ab33c3937
- 성공한 CI: https://github.com/Phoo1911/myanmar-journey/actions/runs/39574367111
- 실행 환경: GitHub Actions Linux, Python 3.12, Node 22, PostgreSQL 16, Docker Compose.

## 통과
1. API 테스트 10개. 상담 요청/승인/조회, 인증·입력 검증, AI 응답 검증(mock), 미검증 가격·재고 표기, SNS 큐레이션과 데이터 만료, 내부 프록시 토큰과 DB 공유 요청 제한.
2. 직접 예약 합성 테스트: 검증 재고 등록→예약 확정→총액 검산→중복 요청 방지→마지막 재고 동시 예약 2건 중 1건 성공→취소 시 재고 한 번만 복원. SQLite를 사용한 계약/동시성 테스트.
3. Facebook/TikTok 링크: 허용 도메인 검사, 사용자정보 포함 URL 거부, 중복 등록, 조회수 미검증 null 유지, 관리자 위치 검증 후 공개, 검증 장소의 방문 순서 생성.
4. 실제 PostgreSQL 16에서 Alembic 001→002→003 마이그레이션 및 head 확인.
5. Next.js 프로덕션 빌드와 TypeScript 검사.
6. 프론트엔드·API Docker 이미지 빌드.
7. Docker Compose로 PostgreSQL·API·웹 컨테이너 실제 기동. API /health, 웹 HTML, 웹 /api/health를 통한 웹→API→PostgreSQL 연결 검사 통과. 검사 후 테스트 컨테이너·볼륨 정리.
8. 이전 로컬 검증: 브라우저 여행지·지도, 기본 일정, 문의 접수→관리자 승인→고객 상태 갱신. 개편 지도 UI 시각 확인. 의존성 보안 감사 당시 알려진 취약점 없음.

## 수정한 원격 실행 문제
- pytest 콘솔 진입점의 프로젝트 import 경로 문제: CI를 `python -m pytest`로 수정.
- 깨끗한 Git 체크아웃에 빈 public 폴더가 없는 문제: Docker 빌드에서 명시적으로 생성.
- Compose의 웹 서버 프록시가 API 컨테이너를 찾도록 API_INTERNAL_ORIGIN 지정.

## 실제 무료 배포 완료
- 공개 주소: https://myanmar-journey-free.onrender.com
- Render 웹: myanmar-journey-free, **Free** 플랜, 서비스 ID srv-dbc8ahifngtc739ch26g.
- Blueprint: exs-dbc7unt9fdbs73c5vno0. 웹 1개와 무료 PostgreSQL 1개만 생성. 기존 타 서비스는 변경하지 않음.
- Render 상태: Deploy succeeded | Live. 실제 Render DB는 PostgreSQL 18이며 배포 시작 시 마이그레이션과 API 시작 완료.
- 공개 사이트 브라우저 검증: 여행지 3개와 지도 로딩, 공식 경보 표시, 일정 생성 POST 성공 및 '기본 일정 · AI 키 미설정' 표시. 유료 AI/YouTube 키를 설정하지 않았고 카드 등록 없이 생성.
- 무료 통합 이미지 검증: https://github.com/Phoo1911/myanmar-journey/actions/runs/39576158990 (dd14dc5e6d51a7bc58a90a255e5c8acc36031ac1). 단일 이미지의 웹→loopback API→PostgreSQL 연결과 관리자 미인증 401 확인.
- 제한: 무료 웹은 미사용 시 대기, 무료 DB는 생성 후 30일 만료. 실제 고객정보·실제 예약을 받지 않는 체험판이며 UI에 명시. 워크스페이스 무료 사용량은 다른 서비스와 공유. 유료 production/SLA/영구 데이터 보관을 제공하지 않음.

## 검증 한계
- 실제 OpenAI/YouTube 호출은 계정 키 미제공으로 미실행. AI는 mock 경계와 명시적 템플릿으로 검증. Facebook/TikTok은 링크 검토 흐름이며 자동 크롤링/영상 이해 API는 미구현.
- 실제 공급사 API·온라인 결제·실상품은 미연동. 운영자 배정 재고의 현장 결제 예약만 지원하며 합성 데이터로 검증. 운영 DB에 가짜 상품·인기 수치를 seed하지 않음.
- 마지막 재고 동시성 테스트는 SQLite에서 수행. PostgreSQL에서는 마이그레이션 및 컨테이너 연결을 확인했으며 전체 예약 동시성 시나리오를 별도로 수행하지 않음.
- 한국어/영어/미얀마어 UI 제공. 미얀마어 원어민 검수, 개인정보 고지와 운영 연락처, 실공급사 계약·이행 절차는 실제 고객 공개 전 필요.
- Starlette TestClient의 향후 httpx 변경 경고 및 GitHub Actions 런타임 전환 안내가 있음. 테스트 실패는 아님.


## Public SNS submission update — 2026-10-21
- Added region/keyword external Facebook and TikTok search entry points and public link submission using the existing validated/rate-limited endpoint. Review-pending, failure and busy states are explicit. No automatic collector claimed.
- Local API suite: 10 passed (SQLite, mocked AI). Production frontend build and TypeScript passed. No schema changes; migration checks remain in CI.
- TikTok Display API requires approved app/account consent; Research API FAQ excludes commercial users. Facebook docs returned 429; exact permissions not verified.
- Automatic all-platform hotspot discovery remains incomplete: no credentials supplied or commercial data provider selected.

- Live Render update c08b623 verified in the public SNS tab: region/keyword encoded in external search URL; real public Rangoon Tea House Facebook page submitted successfully and shown as pending review. No popularity claims or map publication. No customer information submitted. Screenshot saved separately. Remote CI: https://github.com/Phoo1911/myanmar-journey/actions/runs/39583189762 (completed successfully, 4m23s: API tests, PostgreSQL migration, production build, Compose and combined free image smoke checks).

## Recommended places presentation — 2026-10-21
- Replaced public SNS platform controls, external searches and submission form with a recommended-places experience. Removed collection/ranking implementation text and engagement metrics from public cards. Retained generic collapsible references and backend/admin evidence workflows. No source records deleted.
- Local: 10 API tests passed; Next.js production build including type checking passed. No backend/schema changes. Existing PostgreSQL migration and container checks run in CI on the release.
- Backend Facebook/TikTok automatic discovery remains unconnected; this presentation change does not enable it.

- Live release 5ac9d51: public recommended-places heading and filters rendered; Facebook/TikTok labels count 0 and public post-link input count 0. Existing source records preserved. Screenshot: recommended-places-live.png. CI: https://github.com/Phoo1911/myanmar-journey/actions/runs/39584413720.
- Remote CI completed successfully in 3m29s: API tests, PostgreSQL migrations, frontend build and separate/combined image runtime checks.

## Cold-start diagnosis and API evaluation — 2026-10-21
- Browser reproduced Render application-loading interstitial. After wake, /api/hotspots returned JSON [] (no published places), distinguishing server wake failure from missing recommendation data.
- Fixed public-server startup order: wait for authenticated API/DB health before Next starts. Recommended-place GET now retries three times with per-request timeout, cancellation on unmount, loading/empty/error states and manual retry; no writes retried. Local 10 API tests and production build/type checking passed. CI c99e428: https://github.com/Phoo1911/myanmar-journey/actions/runs/39635882195 (completed successfully in 3m43s, including PostgreSQL migrations and combined free image API readiness/runtime check).
- freepublicapis.com lists Nominatim. One real identified HTTP request for Shwedagon Pagoda with countrycodes=mm returned HTTP200, worship POI 16.7990633,96.1494229 and a same-name dry-cleaning result. Category filtering is essential. No generic public Nominatim service integrated: official policy requires informed developer choice, app-wide <=1req/sec, cache, attribution, no autocomplete/systematic POI extraction. https://operations.osmfoundation.org/policies/nominatim/
- Geoapify official pricing separately verified: free commercial production use with attribution, 3000 credits/day, no card, API key required. https://www.geoapify.com/pricing/ Actual Myanmar Geoapify data not queried (no key).
- Open-Meteo free endpoint is noncommercial only; unsuitable for free commercial production weather integration. Overpass public instances explicitly discourage relying on them as an app backend. No third-party subscriptions created.
- Render c99e428 deployed Live. Logs confirm API /health200 before Next startup. Public UI verified loading→successful empty-list message without connection error. Published recommendation records remain zero; no location provider has been connected by this fix.

## Working mapped-place catalog — 2026-10-21
- Six real named landmarks resolved via small one-time Nominatim lookup with identifying header, sequential calls and two-second spacing, persisted to attributed ODbL snapshot. An attempted bounded Overpass import failed with timeout/502 and alternative provider errors; none of those failed responses were used. No public-provider calls on visitor requests.
- /catalog serves reusable source data; /hotspots merges mapped landmarks with reviewed SNS evidence; /routes accepts mapped IDs. Names/region/category search, map selection, references/date, trip add and geographic ordering connected. No operating status, price, availability or SNS engagement fabricated.
- Local API suite 11 passed, including catalog source/coordinate invariants, search/filter, route success and existing expiry/security boundaries. Frontend production build and typecheck passed. No schema changes.
- Render release aef3c89 is Live. Real public-browser path verified: six mapped places rendered → Korean search 술레 narrows to Sule Pagoda → selecting place updates map → references show original OSM URL and collection date → add Sule and Shwedagon (cart=2) → /routes generates DAY1 with Shwedagon then Sule. No customer data or bookings created. Screenshots working-place-search.png and working-place-itinerary.png. CI: https://github.com/Phoo1911/myanmar-journey/actions/runs/39638541248.
- CI aef3c89 completed successfully in 4m26s: 11 API tests, PostgreSQL migration, production frontend build, separate containers and combined free image runtime checks. Real Geoapify/OpenAI/SNS provider calls remain unperformed; only the named OSM source lookups and live first-party place/route APIs were exercised.

## Travel desk differentiators — 2026-10-21
- Implemented preference draft from real catalog, saved private request/receipt, sourced expiring operator quotes, customer acceptance, separately attested written supplier confirmation, internal messages and operator-reviewed translations, sourced local facts and known-closed place exclusion. Default operations disabled: user confirmed no supplier partners. No fake operational facts, supplier quotes or reservations seeded in Render.
- Local API suite: 14 passed, covering ownership/auth, duplicate request/acceptance, stale version, price validation, quote expiry, authority attestation, private evidence omission, reviewed-translation boundary, fact expiry and draft exclusion. Frontend production build/typecheck passed. SQLite migration 001→004 and head confirmed. Wrong-directory test invocation initially failed import; rerun in backend passed.
- Real local browser with temporary SQLite DB and synthetic-only data: preview with mobility/vehicle preferences; request submission; operator quote entry at 125.50 (12550 integer minor units); private retrieval; customer acceptance; operator written-confirmation fixture; customer thread; operator reviewed Korean reply; sourced synthetic local fact displayed in place card. These are mock operational records, not actual supplier delivery. No external messages or payments sent.
- Production verification will exercise only public preview with actual mapped landmarks; no synthetic supplier evidence will be published there.
- Live release 04b4f20: public travel-desk form rendered, sample walking/vehicle preferences produced real Yangon landmark draft, no request/contact data submitted to production. /concierge/status confirms operations_enabled=false, manual delivery, operator-reviewed translation, online_payment=false. Unauthenticated admin request list denied. CI https://github.com/Phoo1911/myanmar-journey/actions/runs/39643027465 completed successfully in 3m50s: 14 API tests, PostgreSQL migration through 004, frontend build/typecheck, separate and free combined image runtime checks. Subsequent Burmese fact-label-only change passed local production build/typecheck; no backend changes. Temporary local test servers stopped.
- Burmese fact-label follow-up 77d285f is also Live on Render. Core live preview uses actual six-landmark catalog; full commercial operations remain disabled. Supplier partnering, field checks, broad place coverage, live road/transit data, automatic SNS discovery and automated free-text translation are outstanding external/data work, not completed by this release.

## Map workspace and device trip storage — 2026-10-22
- Commercial readiness review: COMMERCIAL_REVIEW.md ranks actual suppliers/fulfillment, permanent DB/backups/support/privacy, sourced coverage and admin operations as P0. No external integrations, subscriptions or supplier partners created.
- UI: mapped-place discovery is default; compact primary navigation, desktop split list/map, mobile map-first and map/list switches; region/name/category filtering, empty result and reset, deduplicated saved buttons and itinerary count. Map instance persists during selection; ResizeObserver refreshes hidden/resized map. Tile failures retain usable list. Legacy regional template is collapsed and explicitly not saved.
- Persistence: selected public places plus explicitly saved geographic draft in this browser only, allowlisted/validated and bounded. No credentials, receipts or customer messages stored. Version/signature/day/stop checks reject corrupt or mismatched drafts. Changed inputs invalidate visible route, requests abort/time out, stale responses ignored. Device deletion provided.
- Security: same-origin /api default, proxy stream capped at 16384 bytes before buffering entire body, Retry-After forwarded, no-store on error paths, frame/object/base restrictions, DENY/nosniff/referrer/permissions and production HSTS headers. No auth/CORS or real supplier confirmation logic changed. Full script CSP remains a separate hardening task.
- Local final production build/typecheck passed (Next 15.5.28); frontend node:test 3 passed (malformed/oversize/duplicate storage, credential field stripping, saved-route roundtrip and tampered/stale/incomplete route rejection). Existing backend pytest 14 passed with one existing Starlette/httpx deprecation warning. Native pnpm audit --prod: No known vulnerabilities found.
- Temporary SQLite migration 001→004 and alembic current 004(head) passed. First migration invocation from repository root failed because relative migrations path requires backend working directory; corrected invocation passed. A first frontend invocation lacked Node on PATH and wrote no Map/config files due wrong directory; corrected commands/build passed. Docker and PostgreSQL checks require remote CI; local tests do not claim those ran.
- Actual local browser, actual six-source catalog, no customer records: search 술레→add, search 쉐다곤→add (2), arrange route via real local /api/routes→save→reload→two places and saved DAY1 restored; removing Sule invalidated route and disabled save. Empty query result and reset, mobile map/list switch and 320px no horizontal overflow confirmed; default desktop 1280px rendered split view. Viewport tool did not reliably apply 768/1024/1440 overrides, so those widths are NOT verified.
- Actual local HTTP: /api/health200 with SQLite, /api/admin/bookings401, /api/concierge/admin/requests401, proxy allowlist404, oversized POST413/no-store, security headers on HTML. API stopped intentionally: browser showed connection failure and retry (not successful empty data); API restarted: retry returned six places and cleared initial-data error. This exposed and fixed a stale global error after recovery. No production customer data submitted.
- Release production/CI evidence appended after deployment. Source coverage is still six mapped landmarks, no live opening/road times/safety certification, no automated SNS/Google provider or account sync. Free DB expiry and real operational launch requirements remain unchanged.
