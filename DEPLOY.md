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

## 무료 콘텐츠 검색 연결 (2026-10-22)
1. Tavily 공식 요금 페이지 https://www.tavily.com/pricing 는 카드 없는 월1000 무료 크레딧을 안내한다(확인2026-10-22). 가입 후 무료 플랜만 선택한다. PAYG·자동 충전·카드·유료 플랜을 켜지 않는다. 현재 에이전트 브라우저의 https://app.tavily.com/ 접속은 CloudFront403으로 차단되어 계정/키 발급은 수행하지 못했다.
2. 사용자가 본인 브라우저에서 무료 계정/API 키를 준비하고, Render `myanmar-journey-free`의 Environment에 서버 전용 `TAVILY_API_KEY`를 직접 입력한다. 키를 채팅·소스·NEXT_PUBLIC 환경변수에 넣지 않는다. 키 입력 시 Save/redeploy가 필요하다. 이번 릴리스는 키가 없으며 자동 검색은 비활성으로 표시한다.
3. `DISCOVERY_MONTHLY_SEARCH_LIMIT=100` 기본값. DB 공유 월 검색 예약 카운터, 기본검색1회/요청, 6시간·32쿼리 메모리 캐시. 환경변수는0~500까지만 허용하며 잘못된 값은0(차단)이다. 무료 크레딧을 다른 앱에서도 쓰면 남은 공급자 한도는 다를 수 있다. 공급자 무료 계정과 PAYG 비활성 상태를 직접 확인한다. 실패 요청도 보수적으로 앱 한도에서 차감한다.
4. `/api/discovery/status`가 configured일 때 공개 콘텐츠 기본 검색을 화면 진입 시1회 요청한다. 실제 Facebook/TikTok 전체 피드·사진OCR·동영상 이해·평점/리뷰 전체 수집이 아니다. 검색 색인에 없는 게시물은 나오지 않는다. 게시물 원문을 임의 크롤링하지 않는다. API 결과에서 허용된 SNS 출처만 표시하고 원문 링크·색인 발췌·조회일을 보존한다.
5. 키 없이 본문 가져오기와 전국15개 지역/도시 중심점은 작동한다. 문자 인식/LLM은 없음. 기존 명소와 도시 별칭의 이름 일치 후보만 반환한다. 미확인 신규 카페의 좌표를 만들지 않는다. 도시 중심점은 자동 선택에서 제외한다. 지점 구분·사진 속 장소·새 장소 지오코딩은 추가 데이터 연동이 필요하다.
6. TikTok의 canonical /@user/video/숫자 링크는 고정 공식 oEmbed endpoint에만 요청해 title을 읽는다. HTML/스크립트는 실행하지 않는다. 단축 링크·Facebook URL만으로 본문 읽기는 지원하지 않으며 본문 붙여넣기를 안내한다. 실제 TikTok oEmbed 호출은 운영에서 검증하지 않았고 mock 계약만 통과했다.
7. GeoNames 전국 지명 전체를 핫플로 복제하지 않는다. 15개 ADM1과 해당 행정 중심 도시15개만 별도 CC BY4.0 snapshot에 추가했다. OSM 명소6개와 라이선스/날짜/좌표 범위 구분. scripts/import_national_cities.py로 공식 덤프에서 재생성 가능. 모든 지점의 현장/영업/안전 정보는 미검증.
8. 롤백: DB 변경 없이 이전 Render 배포 사용. 기존 저장 초안의 공개 장소 필드는 호환되며 출처 링크와 city_centre 구분만 추가된다. 고객 정보와 예약 기록은 이번 기능으로 생성하지 않는다.
