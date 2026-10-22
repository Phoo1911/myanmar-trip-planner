# 무료 Render 체험 배포

기본 `render.yaml`은 무료 Web 서비스 1개와 무료 PostgreSQL 1개만 생성합니다. `Dockerfile.free`에 Next.js와 FastAPI를 함께 구성해 유료 private service가 필요하지 않습니다. API는 컨테이너 loopback에만 노출되고 웹 `/api` 프록시가 내부 토큰을 전달합니다. 시작 시 DB 마이그레이션을 실행합니다.

Render → New Blueprint → Phoo1911/myanmar-journey → main → render.yaml. 생성 전 두 리소스의 plan이 **Free**인지 확인하세요. 유료 인스턴스나 카드 등록을 요구하면 생성하지 말고 설정을 다시 확인합니다. 계정의 별도 검증 요구가 있을 경우 우회하지 않습니다.

- 무료 웹은 15분 미사용 후 대기하며 재접속 시 시작에 약 1분 걸릴 수 있습니다.
- 무료 PostgreSQL은 생성 후 30일에 만료되므로 영구 운영용으로 사용하지 않습니다. 만료 전 필요한 합성 테스트 데이터를 내보내세요.
- 무료 인스턴스 시간은 워크스페이스 전체에서 월 750시간을 공유합니다. 기존 다른 무료 서비스가 있으면 사용량이 합산됩니다. 이 프로젝트는 다른 서비스를 중지하거나 변경하지 않습니다.
- 카드 없는 워크스페이스는 무료 대역폭/빌드 한도 초과 시 서비스나 빌드가 중지될 수 있습니다. 카드를 추가한 계정은 초과 사용 과금 가능성이 있으므로 무료 사용을 원하면 지출 제한도 확인해야 합니다.
- OpenAI/YouTube API 키는 빈 값으로 배포합니다. AI는 명시적 기본 일정이며 SNS는 링크 검토 흐름을 사용합니다. 무료 배포에서 유료 AI 서비스를 자동 활성화하지 않습니다.
- 실제 고객정보·실제 예약·결제를 처리하지 않는 체험판입니다. 검증 재고를 사용하는 실제 운영 전에는 안정적인 DB·공급사 계약·개인정보 고지·운영 절차가 필요합니다.

기존 유료 production 구성은 `render.production.yaml`에 따로 보관합니다. 사용자의 명시적 유료 전환 요청 없이 적용하지 않습니다. Docker Compose 로컬 구성도 유지됩니다.

공식 제한: https://render.com/docs/free


## SNS automatic integrations
Facebook/TikTok sources are managed through the admin review workflow, then published as recommended places on the map and in trips. Public search buttons, platform labels and submission forms have been removed. Original and location references remain stored and are available as generic reference links. Automatic collection is not implemented; adding a key alone will not activate a connector.

- Facebook: provide managed/partner Page URLs and access, then a Meta developer app. Required Pages API permissions, tokens and public-content review depend on the app use case; confirm in the dashboard. Do not assume an unrestricted all-post keyword search API. Official references: https://developers.facebook.com/docs/pages-api/ and https://developers.facebook.com/docs/features-reference/page-public-content-access/ (official docs returned 429 during this verification; exact permissions not verified).
- TikTok: approved Login Kit and Display API, user.info.basic/video.list consent, OAuth callback and refresh implementation. This retrieves consenting accounts, not global destination trends: https://developers.tiktok.com/docs/en/display-api-get-started
- Research API excludes commercial users; do not use it for this travel business: https://developers.tiktok.com/docs/en/research-api-faq
- Broad automatic discovery requires an approved commercial search/data provider with confirmed reuse terms and a spending limit. None has been selected or purchased.
- Enter secrets directly in Render environment settings; never in chat or source control. No Facebook/TikTok connector environment variables are implemented yet.

## Keyless initial places
backend/app/data/places.json contains six real named Myanmar landmarks, source URLs, coordinates, translated names and collection timestamps. Served locally through /catalog and merged into /hotspots and /routes; no provider credentials or external calls on visitor requests. This is a dated map snapshot, not automatic SNS discovery or a live business-status feed. Catalog source_kind/openstreetmap and location_verified=false must remain visible in status/references. Dataset is redistributed under ODbL and downloadable through /catalog with attribution. Future updates require fresh source review and a release; do not silently claim live refresh.

## Travel desk launch requirements
Migration 004 adds private journey_requests and local_facts; normal startup applies it. Back up the DB before production migration. Keep the new tables on rollback (do not downgrade/drop customer records); roll back app code only if needed.

SUPPLIER_OPERATIONS_ENABLED defaults false. With NEXT_PUBLIC_DEMO_MODE=true, customer forms continue to identify the preview and must use synthetic contact data even if the server flag changes. Do not enable actual customer operations until all of these exist: stable non-expiring DB/backup, operator privacy/contact/retention process, actual hotel/driver/guide relationships, written quote and confirmation authority, customer support/cancellation handling, reviewed ko/en/my wording. No supplier currently partnered (user confirmed none).

The travel desk stores requests and messages internally. It sends no external emails, social messages, supplier requests or payments. Operators must independently contact suppliers through authorized channels, then enter actual evidence, final party totals, inclusions/exclusions, cancellation terms and expiry. A customer choosing a quote is quote_accepted, not supplier_confirmed; the latter requires explicit written-confirmation/authority attestations and booking reference. Payment stays unpaid. Quote totals use integer hundredths of USD/MMK, with at most two decimals in admin entry.

Local facts require a public HTTPS evidence URL, actual checked time and recheck date within seven days. Expired facts become unknown. Opening/foreign-access negative facts exclude a place from drafts; negative step-free entry excludes it when a mobility need was entered. Missing transport times, walking conditions, check-in and safety remain checks, never certified. Public map locations still use the dated six-landmark snapshot.

Translation is operator-reviewed original/translated text, not live automatic translation. Fixed interface supports ko/en/my; native Burmese editorial review remains required. The public /concierge/status reports enabled/manual-delivery/operator-reviewed mode only; it reveals no credentials. Google Maps, broad SNS discovery, supplier integrations and automatic translation require separate provider setup and are not enabled by this release.

## 2026-10-22 지도/기기 저장 릴리스
- 서버 DB 스키마 변경 없음(004 유지). 프론트 `journey:places:v1`, `journey:draft:v1`에는 공개 장소/방문 초안만 저장. 관리자·접수증·연락처는 저장 금지. 기기 변경/브라우저 데이터 삭제 시 복원되지 않음.
- `NEXT_PUBLIC_API_URL=/api`가 기본. 브라우저는 동일 출처 Next 프록시를 사용, API_INTERNAL_ORIGIN은 서버 전용. 기존 직접 API URL 설정은 그대로 지원.
- 보안 헤더: frame-ancestors/object-src/base-uri 제한, frame 차단, nosniff, referrer/permissions 정책, production HSTS. 전체 script CSP는 Next 부트스트랩을 검증하지 않고 강제하지 않음.
- 릴리스 검증: pnpm test / typecheck / build, pytest, Alembic head, API→DB 및 API 오류/복구, 저장 후 새로고침, 모바일 지도/목록. 전체 PG/Docker 검증은 원격 CI에서 수행. 실패 시 이전 Render 배포로 rollback. 신규 DB migration 없음; 로컬 초안은 지워질 수 있으나 서버 고객 데이터는 변경하지 않음.
- 무료 배포 제한과 실제 공급사 연결 제한은 COMMERCIAL_REVIEW.md의 P0를 따른다. 무료 체험판을 상용 운영으로 전환하지 않는다.
