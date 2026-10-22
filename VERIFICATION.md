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
- Final release 0b42f113e1ecc576ac0ad82d6e646c47ecefb3dd is Live on Render (free service, 1m46s deploy). CI https://github.com/Phoo1911/myanmar-journey/actions/runs/39752930957 succeeded in 4m51s, including 14 backend + 3 frontend tests, PostgreSQL migration through004, production build, separate Compose containers and combined free image runtime health/auth checks.
- Actual public site: search Sule and Shwedagon → add two real landmarks → /routes → save device draft → reload → saved DAY1 and both places restored. Public HTTP read-only checks passed health/DB, >=six places, private endpoint401, disabled supplier operations/payment, security headers. No booking/contact/customer records created. Local test itinerary deletion and Burmese rendering/no console errors checked; original localhost3000 untouched, temporary test servers stopped. Screenshots live-map-workspace.png and live-saved-trip.png saved outside source tree.

## Content-to-trip and nationwide selectors — 2026-10-22
- Corrected product scope: users want content discovery → location extraction → map/route, not more manual map lookup. Added nationwide15-region selector and15 actual GeoNames capital city centres, preserving source, modification date, retrieval date, SHA256 and CC BY4.0 attribution. Six OSM landmarks remain separately attributed. Raw GeoNames dump contained66930 mostly villages/streams/etc; did not publish those as attractions. Known data-quality issues in raw tourism rows were not imported. No synthetic hotspots/reviews/ratings seeded.
- Backend discovery: supplied public text + optional allowed social source URL → unique name/alias candidates from actual catalog/cities; Burmese contiguous-script matching; no LLM/OCR/inferred coordinates. Canonical TikTok title lookup via fixed official oEmbed endpoint (mock only). Optional Tavily search fixed endpoint with strict domain filtering, no raw HTML/images/AI answer, no redirects, escaped snippets, source references and retrieval date. No-key503, upstream502, global DB monthly budget429, 6h bounded memory cache. Default100 monthly searches, hard maximum500, basic mode; no paid plan configured.
- Source validation rejects arbitrary domains, credentials/ports, AI-generated shop.tiktok.com pages and credential-bearing query strings. Supplied text is not persisted; only public reference links may be saved with selected places. City-centre candidates are unchecked by default, and remain labeled through device storage. No schema migration needed (existing rate_buckets used with distinct monthly hash).
- Local backend suite19 passed (14 existing+5 discovery). Tests cover15-region coverage/source/scope, national city routing, known/no matches, Burmese mentions, malicious instructions treated as text, URL boundary checks, unconfigured search, provider outage, mocked provider snippets and domain rejection, cache/no extra provider call, budget0/no provider call, TikTok title-only/no embedded HTML. Existing Starlette/httpx warning remains.
- Frontend4 tests passed including content-reference allowlist/city scope preservation. Production build/typecheck passed after resolving Map component/global Map naming collision and narrowing city coordinate-scope type. No dependencies added. pnpm audit --prod: no known vulnerabilities. Migration remains004(head).
- Actual local browser: Kachin filter shows Myitkyina city centre (one result); synthetic supplied caption with Shwedagon+Sule+Yangon resolves two checked landmarks and unchecked city centre; bulk-add → real local /routes → device save → reload restores DAY1 and two source references. The source URL was a synthetic local fixture, never published as real SNS evidence or inserted into production DB. Snapshot/source parsing and name matching are real; provider Search/oEmbed payload tests are mocked.
- Tavily official pricing/docs verified: no-card free1000 monthly credits; basic search API contract. Browser account portal returned CloudFront403; no account/API key, no subscription, no billing/card and no actual Tavily search call made. Automatic discovery remains not_configured until user provisions free key directly into Render. Photo OCR, new-venue geocoding and full reviews remain unavailable.
- Deployment/remote CI evidence to be appended after release. Temporary local tests do not prove full nationwide POI coverage, supplier availability, safe routing or actual automatic SNS recommendations.
- Production Korean-caption follow-up: whitespace-only matching would miss Korean postpositions and joined hashtags. Added bounded Korean particle matching, compact/underscore hashtag aliases, and regression assertions alongside Burmese contiguous-script and ambiguous-name checks; final backend19 passed. A failed wrong-directory edit wrote no source; corrected edit and actual rerun passed. No AI semantic/photo understanding is claimed by these name-match rules.
- Final source release 0a0cb1172a5e361be8269e6d8ce28c1f1a1ea17f is Live on Render (1m04s deploy). Final CI https://github.com/Phoo1911/myanmar-journey/actions/runs/39760677142 succeeded (4m29s total / 4m26s test job): backend19, frontend4, production build/typecheck, PostgreSQL migration004 and separate/combined Docker runtime checks. Intermediate31fa1ab full CI also passed before Korean matcher follow-up.
- Actual final public-browser flow: Korean preference text '양곤에서 쉐다곤 파고다와 술레 파고다를 방문하고 싶어요.' (not claimed as an SNS post; no source URL) → two landmark candidates → bulk add → /routes → device save → reload restored DAY1. All15 regional options and21 mapped records (15 centres+6 landmarks) displayed; nationwide map overview shown before selection. No production booking/contact/source-evidence records created. Screenshot live-content-to-trip.png saved outside source. Original user site tab preserved; verification used a separate tab.
- Read-only production HTTP: /api/health200; /api/discovery/regions has15 regions/15 city centres, prices null; /api/discovery/status reports search=not_configured, OCR=false, monthly cap100. API key/actual Tavily provider calls remain unverified and blocked by missing key/portal403. User was given a secure key-setup handoff; no keys requested in chat. Temporary local servers stopped.

## Tavily production connection — 2026-10-22
- User completed API setup. Live status initially not_configured. Render variable name was TAVILY_API_KEYx; renamed only to TAVILY_API_KEY without revealing or changing its value. Free service redeploy dep-dbcu9md9fdbs73fbnr00.
- Actual public /api/discovery/status now configured. Real browser automatic discovery returned eight indexed Facebook/YouTube source excerpts, with source links and retrieval dates; Shwedagon Pagoda and three city-centre name candidates appeared. City centres remained unchecked. No popularity, rating or full-review verification claimed. Screenshot live-tavily-connected.png saved outside source. No customer bookings or contacts submitted.

## Multilingual semantic recommendations — 2026-10-22
- Implemented bounded Gemini embedding cosine retrieval over sourced attraction records and Tavily excerpts, followed by schema-validated grounded AI recommendations in requested ko/en/my language. City-centre records excluded from attraction recommendations; unknown venues remain unmapped content discoveries. No learned ranking or provider access claim from mocks.
- Local backend24 tests passed, frontend4 storage tests passed, production build/typecheck passed, temporary SQLite migration004(head) confirmed. Synthetic vectors verify semantic ranking math independent of literal overlap; three-language mocked pipeline, missing key, quota, forged place/evidence and upstream failure tested. A first new-test write used an incorrect relative path and did not create the test; corrected backend-relative path and ran all24 tests successfully.
- No new dependency/schema. Fixed HTTPS providers, bounded requests/output, secret header only, monthly shared cap, no preference text stored, no paid provider fallback. Live Gemini calls/native Burmese semantic quality not yet verified: API key absent and AI Studio browser request timed out. User asked to create free unbilled key securely and save directly in Render. Deployment/browser outcome appended separately.

## 최신 인수인계 보정 — 2026-10-22
- 사용자 완료 후 Gemini 키 존재를 실제 확인. 구 모델 생성404를 gemini-3.1-flash-lite로 교체한 뒤 한국어 추천200 확인. 의도 영어 재작성/관련 출처 선택을 추가한 버전에서 영어200, 한국어/미얀마어502(ValueError)를 확인했다. 이후 조회 ID enum 제한/3000토큰/고정 오류 코드 진단을 커밋했으나 그 최종 수정의 운영 성공은 아직 미검증이다.
- 최종 로컬 backend25 + frontend5 tests, production build/typecheck 통과. c40e171 원격 CI39765332941 성공을 확인했으며 이후 버전 CI는 완료 확인 전이다. 최신 상태와 재현 절차는 HANDOFF.md. 이 기록은 과거의 Gemini 키 없음 설명을 대체한다.
- HANDOFF.md, CLAUDE.md 및 README 인수인계 링크는 로컬에 작성했다. 이 문서 추가분은 아직 GitHub에 게시하지 않았다.

## AI recommendation resilience — 2026-10-22
- Live production probe before change (commit 2824354, CI 39782340776 success): en 200 with Shwedagon + real excerpt; ko first 502 (ungrounded/validation), ko retry and my x2 Gemini generateContent HTTP503. Five of the 50 monthly calls used. No customer data submitted.
- Change: transient Gemini 500/503/504 retried with bounded backoff inside an 85s request deadline, then 503 + Retry-After (UI shows "busy, retry" instead of "configuring"). Generation schema now has one anyOf variant per mapped candidate so each place can only cite evidence linked to it; server grounding validation unchanged and still rejects forged IDs. Search-rewrite failure skips social evidence (warning) instead of failing the request. Duplicate place selections collapse. MAX_TOKENS/blocked finishReason logged as fixed codes.
- Local Windows: backend 29 passed (PYTHONUTF8=1; default cp949 decoding fails data-file reads, CI is Linux). Node not installed locally, so frontend test/build/typecheck rely on remote CI. Live ko/en/my result after deployment pending.
