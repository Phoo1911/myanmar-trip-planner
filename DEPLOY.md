# 배포 가이드

## 필요한 권한과 값
1. Docker 실행 가능한 Linux VPS 또는 컨테이너 호스팅 계정과 배포 권한, SSH/서비스 생성 권한.
2. 도메인을 쓸 경우 DNS 관리 권한과 web/api 호스트 이름. 도메인 없이 제공업체 HTTPS 주소로도 가능.
3. PostgreSQL 연결/백업 권한. Compose DB 대신 관리형 DB를 쓰려면 DATABASE_URL과 SSL 요구사항을 적용.
4. 실제 AI를 켜려면 본인 OpenAI 프로젝트의 결제 활성화된 API 키. 키는 서버 환경변수로만 전달.
5. 현재 결제 기능이 없으므로 결제 계정은 필요하지 않습니다. 공급사 계약·예약 API와 결제 사업자 연동은 별도 작업.

## 단일 서버 배포
- Docker Engine + Compose를 설치한 서버에 이 프로젝트를 복사. .env 생성 후 비밀값 교체. 저장소에 .env를 올리지 말 것.
- CORS_ORIGINS=https://여행도메인, NEXT_PUBLIC_API_URL=https://api.여행도메인 설정. 후자는 빌드 시점 값이므로 변경 후 web 재빌드.
- `docker compose up --build -d` 실행. `docker compose logs api`와 `curl http://127.0.0.1:8000/health`로 확인.
- Caddy/Nginx에서 HTTPS 웹 호스트→127.0.0.1:3000, API 호스트→127.0.0.1:8000 프록시. 외부에는 80/443만 노출.
- API gateway에서 요청 본문 제한(예: 16KB), IP별 속도 제한(예: 예약/AI 5회/분), 관리자 경로 IP 제한 또는 추가 인증 적용. AI 사용량/비용 한도 설정.
- 실제 고객 접수 전에 개인정보 처리 고지·보유기간·삭제/문의 절차·운영 연락처를 게시. 네이티브 미얀마어 검수, 공식 안전경보 수동 갱신 담당자 지정.
- DB 정기 백업 및 복구 연습. 감사 로그와 고객 데이터 접근 제한. 관리자 토큰 변경 시 전체 관리자 재로그인.

## 운영 확인
HTTPS, 올바른 CORS, 검색·지도 표시, 실제 날짜의 테스트 접수→관리자 승인→접수증 조회를 확인하고 테스트 고객 정보를 삭제하세요. PostgreSQL 마이그레이션은 `docker compose exec api alembic current`로 확인. `pg_dump`로 변경 전 백업하고 이전 이미지 태그를 보관하세요. 본 마이그레이션 downgrade는 데이터를 삭제하므로 운영 롤백은 이미지 복귀 및 백업 복원을 우선합니다.

## 외부 의존성과 출처
- 안전경보: https://www.gov.uk/foreign-travel-advice/myanmar (2026-10-21 확인 스냅샷; 자동 갱신 아님)
- AI 계약: https://developers.openai.com/api/docs/guides/structured-outputs
- 지도: https://operations.osmfoundation.org/policies/tiles/ (기본 OSM 타일, 서비스 보장 없음)

현재 이 작업에는 호스팅 계정/도메인/서버 자격증명이 제공되지 않았습니다. 로컬 산출물만 생성하며 외부 배포 완료로 간주하지 않습니다.

## 포함된 production HTTPS 구성
`WEB_DOMAIN`과 `API_DOMAIN`의 DNS A 레코드를 서버 IP로 연결하고 80/443 포트를 허용하세요. `.env`의 두 도메인, HTTPS CORS/API URL, 비밀값을 채운 후:
```sh
python3 scripts/preflight.py
docker compose -f compose.yaml -f compose.production.yaml config --quiet
docker compose -f compose.yaml -f compose.production.yaml up --build -d
```
Caddy가 인증서를 자동 발급하며 API 앞 Nginx가 본문 크기와 IP별 속도를 제한합니다. 외부 요청은 HTTPS gateway로만 받고 원본 API 포트는 loopback 유지. 다중 gateway/프록시 운영 시 실제 클라이언트 IP 전달/신뢰 정책을 재설정하세요. 두 이미지 모두 버전 태그를 사용하며 production 공급망 운영에는 검증된 digest 고정을 권장합니다.

GitHub Actions 구성은 제공되지만 아직 원격에서 실행되지 않았습니다. GitHub 저장소에 이 프로젝트를 루트로 올리면 Python 테스트, PostgreSQL 마이그레이션, 프론트 빌드 및 Docker 빌드가 실행됩니다. 자동 외부 배포는 계정 권한이 없어 설정하지 않았습니다.

## Render 배포 (권장 경로)
이 프로젝트 폴더 내용이 저장소 루트가 되도록 GitHub/GitLab에 올립니다. Render → New → Blueprint → 해당 저장소 → `render.yaml`을 선택합니다. Blueprint는 Singapore의 유료 Web Service + Private Service + 관리형 PostgreSQL을 생성합니다. 실제 금액은 생성 화면에서 확인하세요. 무료 체험 구성으로 운영 DB를 대체하지 않습니다.

웹만 공개되고 API와 DB는 비공개 네트워크로 연결됩니다. `/api` 프록시를 사용하므로 도메인/CORS 주소를 수동으로 맞출 필요가 없습니다. Render가 제공하는 HTTPS 주소로 시작할 수 있습니다. DB URL은 psycopg 드라이버 형식으로 자동 정규화합니다. 마이그레이션은 API pre-deploy 단계에서 실행됩니다. 웹 health check도 API와 DB까지 확인합니다.

생성 후 API 서비스의 Environment에서 자동 생성된 ADMIN_TOKEN을 확인하고 관리자 탭에 입력하세요. OPENAI_API_KEY 및 YOUTUBE_API_KEY는 API 서비스 환경변수에만 추가합니다. 키가 없으면 AI는 명시적인 템플릿, SNS는 연동 대기로 표시됩니다. Render 계정 로그인/저장소 접근 승인 및 유료 리소스 생성은 계정 소유자가 수행해야 합니다.

배포 실패 시: API 로그의 migration 오류 → DB 내부 URL/지역 확인; 웹 502 → API 서비스 상태/hostport 연결 확인; health 401 → 두 서비스 INTERNAL_PROXY_TOKEN 참조 확인. 프록시 목적지는 서버 환경변수로만 결정되며 사용자 입력 URL을 받지 않습니다.

공식 절차: https://render.com/docs/deploy-fastapi , https://render.com/docs/deploy-nextjs-app , https://render.com/docs/private-services , https://render.com/docs/blueprint-spec

## SNS 연동
Google Cloud 프로젝트에서 YouTube Data API v3 활성화 → API key 생성 → API 서비스의 YOUTUBE_API_KEY로 설정. 브라우저 공개 변수로 넣지 않습니다. 해당 API만 허용하도록 키를 제한하고 일일 할당량을 설정하세요. 관리자 토큰 입력 → SNS 수집 → 영상 원본 검토 → 다국어 장소명/좌표/독립 위치 출처 입력 → 검증 후 공개. 실제 핫플은 이 과정을 거쳐야 지도에 나타납니다.

정기 수집은 현재 수동입니다. YouTube 저장 데이터는 30일 이내 재수집하거나 삭제해야 하므로 장기 운영 시 일일 갱신·정리 작업을 예약하세요. 인기 점수는 게시 후 평균 조회수이며 실제 방문객·안전·영업 중 여부를 증명하지 않습니다. Instagram/TikTok 권한과 공식 API 계약을 확보하기 전 스크래핑으로 대체하지 않습니다.

## 직접 예약 운영
관리자 → 즉시 예약 재고 등록에서 실제 계약상 확정 권한이 있는 재고만 입력합니다. 검증 유효기간은 7일 이내이며, 만료·매진·판매 중지 상품은 공개 목록에서 제외됩니다. 가격은 세금 포함 1인 최종액을 통화의 1/100 단위 정수로 입력합니다. USD 10.00은 1000입니다. 현재 상품은 날짜별 1회 이용/1인 단위이며 다박 객실·좌석 배정은 지원하지 않습니다.

직접 예약은 운영자가 배정받은 재고에 대한 확정이며 공급사 API 접수증이나 온라인 결제 완료가 아닙니다. 지급은 현장에서 하며 이용일 전 무료 취소 정책만 지원합니다. 기존 예약을 이행할 공급사 연락·예약자 전달·확인 절차를 운영자가 마련해야 합니다.

매일 backend에서 `python cleanup.py`를 실행해 30일 지난 SNS 자료와 만료 요청 제한 데이터를 정리하세요. Render Scheduled Job을 별도 추가할 경우 비용과 동일 DB 연결 권한을 확인해야 합니다. 고객 이메일/예약 감사 이력의 보유기간은 운영자의 고지에 따라 별도 관리하세요.
