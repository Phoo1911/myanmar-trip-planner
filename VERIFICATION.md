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

## 외부 배포 상태
Render가 저장소의 Blueprint를 읽었으나 유료 production 리소스 생성에 결제수단 등록을 요구함. 계정 소유자가 직접 카드 등록을 완료해야 한다. 서비스 생성·외부 HTTPS 배포는 아직 미완료이며 live URL은 없다. 실제 요금과 생성될 리소스를 최종 화면에서 확인한 후 진행한다.

## 검증 한계
- 실제 OpenAI/YouTube 호출은 계정 키 미제공으로 미실행. AI는 mock 경계와 명시적 템플릿으로 검증. Facebook/TikTok은 링크 검토 흐름이며 자동 크롤링/영상 이해 API는 미구현.
- 실제 공급사 API·온라인 결제·실상품은 미연동. 운영자 배정 재고의 현장 결제 예약만 지원하며 합성 데이터로 검증. 운영 DB에 가짜 상품·인기 수치를 seed하지 않음.
- 마지막 재고 동시성 테스트는 SQLite에서 수행. PostgreSQL에서는 마이그레이션 및 컨테이너 연결을 확인했으며 전체 예약 동시성 시나리오를 별도로 수행하지 않음.
- 한국어/영어/미얀마어 UI 제공. 미얀마어 원어민 검수, 개인정보 고지와 운영 연락처, 실공급사 계약·이행 절차는 실제 고객 공개 전 필요.
- Starlette TestClient의 향후 httpx 변경 경고 및 GitHub Actions 런타임 전환 안내가 있음. 테스트 실패는 아님.
