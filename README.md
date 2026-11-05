> 기본 Render 배포는 **무료 체험판**입니다. 무료 DB는 생성 30일 후 만료되고 웹은 미사용 시 대기합니다. 실제 고객정보나 실제 예약을 입력하지 마세요. 유료 구성은 자동 적용하지 않습니다.

# Myanmar Trip Planner

미얀마 여행 탐색·SNS 장소 검토·일정·예약 MVP. 운영자가 계약으로 배정받은 검증 재고는 현장 결제 방식으로 즉시 예약하며, 미연동 서비스는 상담 요청으로 처리합니다. Next.js + TypeScript + Tailwind / FastAPI / PostgreSQL.

## Docker 실행
```sh
cp .env.example .env
# .env의 비밀번호와 두 secret을 각각 충분히 긴 난수로 교체
# DB 비밀번호는 URL에 안전한 영문/숫자/하이픈을 사용
# 예: python3 -c "import secrets; print(secrets.token_hex(32))"
docker compose up --build -d
```
웹 http://localhost:3000 · API 문서 http://localhost:8000/docs. DB 테이블은 API 시작 시 Alembic으로 생성됩니다. 여러 API 인스턴스를 운영할 때 마이그레이션은 단일 release job에서 실행하세요.

## 로컬 개발
```sh
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
export DATABASE_URL=sqlite:///./travel.db
export ADMIN_TOKEN=your-random-token-at-least-32-characters
export RECEIPT_SECRET=another-random-secret-at-least-32-characters
cd backend
alembic upgrade head
uvicorn app.main:app --reload
# 별도 터미널
cd frontend
corepack enable
pnpm install --frozen-lockfile
pnpm dev
```
관리자 탭에 ADMIN_TOKEN을 입력하면 상담 요청을 조회·처리합니다. 승인해도 예약은 확정되지 않습니다. 접수증 ID와 Token은 고객이 안전하게 보관해야 합니다. 서버는 접수증을 이메일로 보내지 않습니다.

## 검증
```sh
cd backend
pytest -q
cd ../frontend
pnpm typecheck
pnpm build
```
실행 결과와 미검증 범위는 VERIFICATION.md, 배포 절차는 DEPLOY.md 참조.

## 추가된 사용 흐름
- 여행지 탐색: 왼쪽 목록/검색/지역 선택 ↔ 오른쪽 지도. 작은 화면에서는 지도 우선.
- SNS 핫플: 공식 API로 수집하거나 Facebook/TikTok 게시물 링크를 등록한 후보를 관리자가 검증한 후 공개. 링크 등록은 자동 영상 분석이 아닙니다.
- 내 일정: 공개된 SNS 장소를 담고 방문 순서 생성. 직선거리 기준 초안이며 도로 경로·소요시간·지역별 이동 안전은 미검증.
- 바로 예약: 관리자가 공급사 계약·확정 권한·배정 재고·세금 포함 가격을 확인해 등록한 상품만 노출. 예약 시 원자적 재고 차감, 접수증 발급, 이용일 전 무료 취소와 재고 복원. 판매 중지 가능.
- 온라인 결제와 공급사 API 예약은 아직 미연동. 현장 결제 예약은 미결제 상태를 명시합니다. 실상품 seed는 없습니다.
- Render는 `render.yaml`을 저장소 루트에서 배포합니다. 웹→내부 API→관리형 DB 구성.

## 콘텐츠 → 장소 → 일정 (2026-10-22)
- 전국15개 주·지역 필터와15개 도시 중심점 + 기존 OSM 명소6개. 도시 중심점은 구체 관광 명소/핫플/실시간 영업 정보가 아니다.
- 공개 본문 붙여넣기 → 이름·별칭이 맞는 장소 후보 → 선택한 장소 일괄 담기 → 방문 순서 → 기기 저장. 원문 링크 보존. 도시 중심점은 자동 선택하지 않는다. 알려지지 않은 장소의 좌표를 추측하지 않는다.
- `TAVILY_API_KEY`를 서버에 연결하면 SNS 도메인의 공개 검색 색인 결과를 찾아 후보를 연결한다. 무료 설정·월 사용 제한은 DEPLOY.md 참조. 키가 없는 현재 배포에서는 자동 검색을 작동 중이라고 표시하지 않는다.
- 전체 Facebook/TikTok 피드, 신규 카페 자동 지오코딩, 사진OCR/영상 이해, 전체 리뷰/평점 수집은 미구현. 계정 없이 모든 SNS 콘텐츠를 자동 추천할 수 있는 서비스로 소개하지 않는다.
- 테스트: backend `python -m pytest -q`; frontend `pnpm test && pnpm typecheck && pnpm build`. GeoNames 원본 재생성: backend 의존성을 설치한 Python으로 `scripts/import_national_cities.py` 실행(공식 공개 덤프에 네트워크 요청).
