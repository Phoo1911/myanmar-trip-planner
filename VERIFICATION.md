# 실행 검증 기록 — 2026-10-21

## 통과
- Python API 테스트 10개 통과. 문의→승인→조회, 인증 거부, 잘못된 입력, AI 출력 경계(mock), 가격/재고 미검증 표기, SNS 큐레이션·만료 숨김, 내부 프록시 토큰, 공유 요청 제한 검사.
- 직접 예약: 검증 재고 등록→확정→총액 검산→재시도 중복 방지→마지막 재고 동시 예약 2건 중 1건만 성공→취소 및 중복 취소 시 한 번만 재고 복원. 합성 데이터/SQLite 테스트.
- Facebook/TikTok 링크: 허용 도메인 검사, 사용자정보 포함 URL 거부, 중복 등록, 조회수 null 유지, 관리자 위치 검증 후 공개, 장소 ID 검증 및 방문 순서 생성.
- Alembic upgrade 001→002→003 실제 SQLite DB에서 실행. 테스트 DB는 /private/tmp에 보관하며 운영 데이터와 분리.
- Next.js production build 및 빌드 내 TypeScript 검사 통과. standalone 산출물 생성.
- pnpm production 의존성 감사: 알려진 취약점 없음 (PostCSS 패치 override 적용).
- Python requirements 보안 감사: 알려진 취약점 없음 (FastAPI/Starlette 및 하위 의존성 갱신).
- 브라우저: 실제 API 연결, 여행지·지도 표시, 기본 일정 생성, 문의 접수→관리자 승인→고객 상태 갱신 확인. 개편 UI도 별도 시각 확인.

## 제한 및 미실행
- 실제 OpenAI/YouTube/Meta/TikTok 호출: 계정 키·권한 미제공. AI는 mock 경계 테스트와 명시적 템플릿으로 검증. Facebook/TikTok 자동 수집·영상 이해 API는 구현되지 않았으며 링크 검토 흐름만 제공.
- 실제 공급사 예약 API·온라인 결제·실재고 등록: 미연동. 운영자 배정 재고 흐름은 합성 테스트만 수행.
- PostgreSQL 서버, Docker 이미지 build/Compose, Caddy 인증서: 로컬 Docker 미설치로 실행하지 못함. PostgreSQL 마이그레이션 CI 구성은 제공했으나 원격 실행 전.
- Render 로그인과 GitHub 연결 저장소 목록 확인. 현재 여행 서비스 저장소는 없음. 사용자는 비공개 Phoo1911/myanmar-journey 생성 승인. 브라우저 GitHub는 로그인이 필요하며 connector도 아직 연결되지 않아 생성/업로드/외부 배포 미완료.
- 미얀마어 원어민 검수, 운영 개인정보 고지·담당 연락처·실공급사 계약·판매/취소 절차 점검은 실제 고객 공개 전 필요.
- 테스트에서 Starlette의 httpx TestClient 향후 변경 경고 1건 발생. 현재 모든 테스트 통과.

SQLite 테스트와 mock은 PostgreSQL 운영·실공급사 확정·실결제·실제 AI 품질의 증명이 아닙니다.
