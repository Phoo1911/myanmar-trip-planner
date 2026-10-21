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
Facebook/TikTok currently support link submission, admin location review, then map/route publication. Search buttons open the external platform; they are not automatic collectors. Adding a key alone will not activate an unimplemented connector.

- Facebook: provide managed/partner Page URLs and access, then a Meta developer app. Required Pages API permissions, tokens and public-content review depend on the app use case; confirm in the dashboard. Do not assume an unrestricted all-post keyword search API. Official references: https://developers.facebook.com/docs/pages-api/ and https://developers.facebook.com/docs/features-reference/page-public-content-access/ (official docs returned 429 during this verification; exact permissions not verified).
- TikTok: approved Login Kit and Display API, user.info.basic/video.list consent, OAuth callback and refresh implementation. This retrieves consenting accounts, not global destination trends: https://developers.tiktok.com/docs/en/display-api-get-started
- Research API excludes commercial users; do not use it for this travel business: https://developers.tiktok.com/docs/en/research-api-faq
- Broad automatic discovery requires an approved commercial search/data provider with confirmed reuse terms and a spending limit. None has been selected or purchased.
- Enter secrets directly in Render environment settings; never in chat or source control. No Facebook/TikTok connector environment variables are implemented yet.
