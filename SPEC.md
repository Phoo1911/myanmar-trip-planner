# Myanmar Journey MVP

## Scope and acceptance
Korean, English and Burmese single-page UI: destination search, map, itinerary generation, accommodation/transport/tour inquiries, private receipt lookup, admin queue and approval/rejection.

- GET /places?q= searches translated catalog names and regions. Seed catalog is a small editorial destination list with approximate map coordinates and source links; not a live operating-status inventory.
- GET /products exposes only generic inquiry services. No actual hotel/provider listings are seeded. All prices and availability are null; mode=request_only.
- GET /safety exposes a dated advisory snapshot and official source, live=false. It never classifies a destination as safe. Planning does not certify routes, operating access or transport.
- POST /itineraries accepts 1–14 days and allowlisted place IDs. OpenAI structured output chooses only catalog IDs and day numbers. Exact day sequence and allowed IDs validated on server. No key => explicitly labeled template. Failure => 502. UI offers one destination per generated draft; API supports up to three. Drafts are not bookings and are not persisted.
- POST /bookings validates dates, email, guests, offering IDs and explicit safety acknowledgment. Idempotency-Key prevents duplicate submissions. Receipt secret is returned only to submitter, stored hashed in DB; status lookup requires it.
- Admin bearer token guards all customer data and decisions. Optimistic version check prevents conflicting decisions. States: requested → approved | rejected. Decision audit persisted in same transaction. Inquiry endpoints have no payment or confirmed state. Separate /reservations endpoints support operator-allocated, pay-on-site confirmations as specified below.
- Three-language navigation, forms, status/error messages and safety text. Place names are translated. Source content remains in original language. Burmese needs native editorial review before public launch.

## Data and security
PostgreSQL production; SQLAlchemy models; versioned Alembic migration. SQLite used only for local tests. Admin shared token MVP, held in memory by browser. Use TLS and restrict admin access at reverse proxy. Public endpoints require gateway request limits before public launch. No session cookies or payment data. Contact email retained for manual follow-up; no automated email delivery. Provide a privacy notice and operator deletion process before collecting real customer data.

## Deliberate boundaries
No external supplier API integration, online payment, live safety feed, safe-route engine, user accounts or multi-user admin roles. Direct confirmations apply only to verified operator-allocated inventory, never unintegrated inquiry offerings. No false placeholders for these capabilities. Map tiles require internet and OpenStreetMap attribution; review tile policy or use a contracted tile provider for commercial scale.

## Completion evidence
Backend contract tests, negative authorization/validation tests, AI mocked boundary checks, migration upgrade, frontend typecheck and production build. Live AI/provider/PostgreSQL/Docker/deployment checks must be identified separately from mock and SQLite evidence.

## SNS 핫플 탐색 확장
- YouTube Data API의 최근 90일 검색 표본(최대 10개)에서 실제 조회수/좋아요/게시일을 수집. regionCode는 업로드 위치가 아닌 시청 가능 국가이므로 위치 증거로 사용하지 않음.
- 점수 = 누적 조회수 / max(1, 게시 후 경과일). 표본 내 비교일 뿐 유동인구·실시간 트렌드·전국 순위가 아님. Instagram/TikTok 미연동 상태 명시.
- 관리자만 수집 가능. 영상 제목을 좌표로 자동 변환하지 않음. 영상 검토 + 별도 HTTPS 위치 출처 + 다국어 명칭 + 좌표 검증 확인 후 공개.
- 공개 장소는 가격/재고 미확인. 30일 지난 수집 데이터는 공개 목록에서 제외. 장소 카테고리 검색 및 목록↔지도 선택 연동.
- 공개 초기 핫플 목록은 비어 있음. 테스트 데이터는 운영 DB에 넣지 않음.
- production Render 경로는 Next 서버 프록시→비공개 API→비공개 DB. 내부 토큰 검증과 DB 공유 분당 요청 제한(쓰기/AI 15회/IP)을 적용. rate bucket은 개인정보 대신 IP 해시와 만료 시각만 보유.

## 직접 예약 확장 수용 기준
계약상 예약 확정 권한이 있는 운영자 배정 재고만 직접 예약. 공급사 계약 근거, 검증 시각, 만료 시각, 날짜별 인원 재고와 세금 포함 1인 최종 가격(최소 화폐 단위) 필수. 실데이터 seed 금지. 지급 방식은 현장 결제만 지원하며 온라인 결제 완료 표시 금지. 재고·가격 버전 재확인, 원자적 차감, 중복 요청 및 잔여 재고 초과 방지. 취소는 무료 취소 정책으로만 재고를 한 번 복원. 예약 영수증에는 현장 결제 및 확정 범위를 명시.
Facebook/TikTok 링크 등록은 메타데이터 자동 수집과 구별. 사용자 입력 후보 제목과 URL만 저장하고 조회수·좋아요는 미검증 null. 관리자 위치 검증 후 지도 공개. 선택한 검증 장소를 일수와 지역에 맞춰 그룹화하되 직선거리 순서이며 실제 길찾기/소요시간/안전 보장 아님.

## 무료 체험 배포
기본 render.yaml은 무료 Web 서비스 1개와 무료 PostgreSQL만 생성. Next.js와 FastAPI를 한 컨테이너에 넣고 API는 loopback에만 바인딩. 내부 토큰·관리자 인증·DB 검증은 유지. 무료에서 지원하지 않는 private service/pre-deploy job 사용 안 함. 시작 시 마이그레이션 후 두 프로세스 실행, 하나가 종료되면 모두 정리하고 컨테이너 재시작 유도.
무료 UI는 자동 대기 및 DB 30일 만료와 실제 고객 데이터 입력 금지를 명시. OpenAI/YouTube 키는 기본 빈 값이며 유료 호출 없음. 이 배포는 production SLA나 영구 데이터 보관을 제공하지 않음. 이전 유료 구성은 render.production.yaml로 분리하고 자동 적용하지 않음.
수용: 루트 무료 이미지 빌드→PostgreSQL 연결→웹/API health→인증 거부 확인. Render 생성 화면에서 free 리소스만 확인한 후 무료 배포.

## 추천 장소 화면 (2026-10-21 변경)
- 이전 공개 SNS 검색/제출 UI를 대체: 방문자는 추천 장소 검색·지도·일정 추가만 사용. 플랫폼명/외부 검색/제출 폼/수집 점수 설명은 공개 화면에서 제거.
- 원본 링크와 위치 출처는 백엔드 데이터와 관리자 검토 화면에 보존. 공개 카드에는 접힌 참고자료 안에 일반적인 원본·위치 출처 링크만 제공.
- 관리자 기존 수집/링크 등록/위치 검증 유지. 자동 Facebook/TikTok 수집 미연동 사실을 숨겨 완료로 주장하지 않으며 운영 안내는 관리자에게 제공.
- 빈 목록/검색 결과 없음/연결 실패를 구별. 지도와 일정 추가 흐름 유지. 검증: 기존 API 테스트와 빌드, 운영 화면 확인.

## Cold-start connection recovery
- Start public Next.js only after authenticated internal API /health (including DB) succeeds; fail startup after 60s or early API exit.
- Recommended places show loading, retry failed GET at most three times, support manual retry, cancel stale requests on unmount. Empty data only appears after successful JSON array response; no auto-retry of writes.

## Usable keyless mapped-place catalog
- Six individually named OSM landmark lookups in Yangon, Bagan and Inle Lake, stored as an attributed ODbL snapshot. Visitors never depend on public Overpass/Nominatim calls. Public /catalog returns the reusable source snapshot; /hotspots merges catalog and reviewed social records.
- Catalog records have source_kind=openstreetmap and location_verified=false. They represent map entries, not reviewed SNS popularity, live opening status, verified prices or available inventory. Source links and collection date shown in references, with mapped/unverified status.
- Search/filter mapped places, select marker/list, add deduplicated places to trip, generate regional geographic visit order through existing /routes. Published SNS expiry checks remain unchanged. Map catalog source is not subject to SNS evidence expiry; dated snapshots must not be presented as live.
- Acceptance: nonempty actual catalog, valid Myanmar coordinates, source/ODbL access, search/category/region filtering, catalog route success, invalid route rejection, null price/availability; live browser search→map→add→route.

## Local travel concierge (five differentiators)
- Add a persisted request workflow: preferences and dated real catalog places → draft → operator quotes → private customer acceptance → supplier confirmation recorded only with written confirmation evidence and explicit authority attestation. No automatic supplier delivery or online payment claims. All customer/admin updates use version checks and audit; request creation and acceptance handle retries. Prices are integer minor units from operator quotes, never AI guesses; quotes expire within seven days.
- Facts (opening, foreign visitor access, cash-only, accessibility) require source, checked-at, expiry <= seven days and operator attestation. Unknown/expired facts never appear verified. Public facts stay separate from safety advisories and map entries. No fake operational facts/suppliers/quotes seeded.
- Preferences: actual date, party size, region, days, pace, interests, mobility needs, services and notes. Draft selects only real catalog IDs; unknown transport duration, walking access and check-in are explicit checks, never inferred as verified.
- Private request thread supports original messages and explicitly operator-reviewed translations in three languages. Fixed request brief labels in ko/en/my; no automatic free-text translation claimed without a provider. No outbound messages sent by this implementation.
- Admin can review requests, add sourced quotes and record supplier confirmation; customers can retrieve private receipt, ask questions and accept an unexpired quote. Receipt secrets never appear in admin/public lists. Authentication/privacy/expiry/stale-version/duplicate tests required.
- Free Render remains a preview with expiring DB and no real customer data; live end-to-end operational completion requires actual supplier relationships, evidence, stable hosting and translation/editorial review. This build alone cannot certify all five real-world services as complete.

## Map workspace and saved draft — 2026-10-22
- Default screen is mapped places. Desktop split list/map; mobile map-first with list/map switches. Search includes translated names and region, clear filters, result count, selected marker/list alignment, saved-state buttons and itinerary navigation. Keep OSM attribution and explicit source/operating-status limits. No Google/SNS integration implied.
- Persist only public place selections and an explicitly saved geographic draft in this browser's localStorage. Never store receipt/admin tokens, contact data or messages. Clearly label device-only storage, missing cross-device sync, last saved date and a user deletion control. Handle unavailable storage and corrupt/oversized/wrong-version data without crashing.
- Route generation has a timeout, distinguishes unavailable source/insufficient days, invalidates stale results after input changes, and cancels on unmount. Save only a successfully generated route matching current inputs; restore after reload; regenerate to revalidate source availability.
- Acceptance: real browser search → marker/list selection → add (deduplicated) → generate → save → reload → restore → remove invalidates route → delete. Test desktop and 320/768/1024/1440 widths, empty filters and API failure recovery. Security: private endpoint denial, proxy errors/no-store, no secrets persisted; existing backend/migration/build checks. Commercial gaps prioritized separately without claiming suppliers/real road routes or production readiness.

## Content to trip, nationwide scope — 2026-10-22
- Core job: discover sourced content → identify mentioned places → inspect candidates on map → add all → generate/save a visit draft. Users should not retype every place into a map. Existing manual map search alone does not satisfy automated discovery.
- Nationwide selector uses all 15 GeoNames ADM1 entries, including Nay Pyi Taw; add their 15 actual capital-city centre records, clearly distinct from attractions. Never describe gazetteer entries as trending, open, safe, reviewed or bookable. Preserve per-source license and dates. Legacy OSM six landmarks remain separate.
- POST /discovery/resolve accepts bounded supplied text and optional public source reference. Unique name/alias matches only, no invented coordinates; ambiguous names are not auto-selected. TikTok canonical video URL may obtain title via official fixed oEmbed endpoint; Facebook full-post access and image/OCR are unavailable. No arbitrary URL fetches, credentials, HTML execution or customer text persistence.
- Optional TAVILY_API_KEY enables bounded indexed web/social content search through fixed official Tavily API; basic search, six-hour bounded cache and DB-shared monthly cap (default100, hard max500). Not equivalent to all-platform live posts, review extraction or popularity ranking. No key = explicit503; do not invent recommendation data. No subscriptions or paid calls configured by this release.
- Public content UI supports source-linked candidates → bulk add with deduplication → existing draft and device save; distinguish city-centre candidate and mapped attraction. Reference remains attached to selected public place data only, no private caption stored. Test source URL validation, unconfigured provider, ambiguous/no match, adversarial text, upstream failure, route with new city IDs, all15 region coverage.

## Multilingual semantic recommendations
- POST /discovery/recommend accepts public preference text <=500 chars, ko/en/my output language and optional region. Gemini multilingual embeddings rank sourced catalog records and Tavily excerpts by exact cosine similarity (not keyword matching). Small bounded in-process document-vector cache, no vector DB migration. Region filters restrict eligible catalog records before ranking; city centres are not attraction recommendations.
- Gemini structured output selects only retrieved attraction IDs and evidence IDs; server validates IDs, duplicate selections, and evidence association. Explain suggested suitability in requested language, with source excerpts/links and explicit unverified operational/safety status. No invented coordinates, prices, stock or ratings. Unknown cafes remain source discoveries until mapped; do not attach them to unrelated catalog coordinates.
- Missing Gemini key returns503 and explicit UI configuration state, quota429, invalid/upstream502. No silent keyword fallback branded semantic/AI. DB-shared monthly recommendation cap default50 hardmax100; fixed provider models/endpoints, no automatic paid provider fallback. Public preferences are sent to Google; no contact/private content, no query persistence. Gemini free-project billing must remain disabled; app cap alone cannot enforce provider billing tier.
- Three-language prompts, UI/loading/errors and model-output language requested. Test cross-language synthetic vectors, ranking vs literal overlap, region scope, missing credential, budget, forged IDs/evidence, bad vectors/provider failures. Live model and native Burmese quality require separate verification.

- Live multilingual refinement: normalize travel intent into a bounded English discovery query before social search; retain original-language query for embeddings. AI selects relevant source IDs only, and server rejects fabricated discovery IDs. Similarity is not a popularity score. Gemini generation uses currently available gemini-3.1-flash-lite; model availability must be smoke-tested, not inferred from old pricing entries.

## Automatic venue discovery, road times and share links — 2026-10-23
- Recommendation output may name up to three new venues, each tied to one search_index_excerpt. The server keeps a venue only when its normalized name appears in that excerpt and is not an existing catalog name, then geocodes it with Geoapify restricted to Myanmar. Only amenity/building results with confidence >= 0.8 whose name matches are accepted; streets, cities and region centroids are rejected. Accepted venues are returned as auto_places with source_kind geoapify_auto, location_verified false, auto_located true, null price/availability and OSM/Geoapify attribution; the UI labels them "auto-located · unverified". Unmatched names are listed without coordinates. No coordinate is ever invented or attached to an unrelated catalog place.
- /routes accepts auto-located points (id geo:<24 hex>, names in ko/en/my, Myanmar bounds) and groups each with the nearest known place's region. /routes/road returns driving distance/time per day from Geoapify (max 4 stops/day, 14 days), labelled as estimates without traffic, closures or safety. Missing key 503, budget/provider quota 429, invalid provider output 502.
- Share links replace accounts for now: POST /trips stores public place data (allowlisted HTTPS references only, no contact or account data) and an optional order covering every place once, under a random unlisted id for 30 days. GET /trips/{id} returns 404 when missing or expired. Loading a shared trip replaces the device trip after the user confirms.
- AI pipeline 502 responses include the fixed reason code (no model text, preferences or secrets) for diagnosis.
