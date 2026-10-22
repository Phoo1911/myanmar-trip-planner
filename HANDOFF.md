# Claude Code / Codex 인수인계

기준: 2026-10-22. 이 문서의 최신 상태가 과거 검증 기록의 '키 미연결' 설명보다 우선한다. 아래의 구현, 실제 검증, 미완료를 구별한다.

## 시작할 곳
- 이 폴더가 실제 앱 소스다. 인접 OrderDesk, myanmar-ai-saas-template은 별도 프로젝트이며 수정하지 않는다.
- AGENTS.md → HANDOFF.md → SPEC.md → VERIFICATION.md → COMMERCIAL_REVIEW.md → DEPLOY.md 순서로 읽는다.
- 로컬 폴더에는 .git이 없다(2026-10-22 직접 확인). GitHub와 자동 동기화되는 checkout이 아니다. 기존 폴더를 덮어쓰거나 git reset하지 않는다. 필요하면 별도 폴더에 비공개 저장소를 clone하고, 이 로컬의 최신 문서/수정분과 비교해서 옮긴다.
- GitHub: https://github.com/Phoo1911/myanmar-journey (private)
- 공개 체험: https://myanmar-journey-free.onrender.com/
- Render: myanmar-journey-free / srv-dbc8ahifngtc739ch26g. 무료 리소스만 사용하도록 승인됨. 유료 전환/결제 계정 연결은 승인되지 않음.

## 제품의 핵심
사용자가 SNS 글·사진·영상·후기를 보고 장소를 다시 지도에서 찾고 동선을 만드는 반복을 줄인다. 목표 흐름은 콘텐츠 발견/가져오기 → 장소 후보 및 출처 → 위치 확인 → 취향에 따른 AI 추천 → 지도/코스 → 일정 저장이다. 한국어·영어·미얀마어 모두 지원해야 한다. 단순 콘텐츠 목록이나 장소명 일치를 의미 검색이라고 부르지 않는다.

## 구현된 코드
- Next.js15 / React19 / TypeScript / Tailwind / Leaflet, FastAPI / SQLAlchemy / PostgreSQL, Alembic head004. 무료 Render 단일 Docker 이미지에서 Next와 loopback API 실행.
- 전국15개 GeoNames 지역, 15개 수도/도시 중심점, 6개 OSM 명소: 총21개 지도 레코드. 전국 상세 핫플21곳이라는 뜻이 아니다. 도시 중심점은 명소 추천과 구별한다.
- 장소 검색/필터/지도, 일괄 일정 담기, 직선거리 기반 방문 순서, 기기 내 저장/복원. 실제 도로 길찾기·이동시간이나 계정 동기화는 아니다.
- 공개 글 붙여넣기 → 기존 장소 이름/별칭 후보 추출, 한국어 조사/해시태그 및 미얀마어 붙여쓰기 처리. TikTok 정식 영상 URL의 oEmbed 제목 읽기는 mock 검증만 했다.
- Tavily 공개 검색 색인 연동: 실제 운영에서 Facebook/YouTube 콘텐츠8건 반환 확인. 원문/수집일 보존. 전체 SNS 피드·전체 리뷰·실시간 인기 순위는 아니다.
- Gemini 다국어 임베딩 + 코사인 검색 + 근거 기반 구조화 추천 API와 UI. 소규모 문서 벡터128개 메모리 캐시, 별도 벡터 DB 없음. 원래 언어로 임베딩; SNS 검색어는 AI가 영어 의도로 재작성. 추천 장소/근거 ID를 서버에서 검증한다.
- 예약 요청/관리자 처리/접수증과 검증 재고용 별도 예약 로직은 코드에 있으나 실제 제휴 업체 없음. 운영/결제 비활성. 관리자 요청 승인은 공급사 확정이 아니다.

## 가장 먼저 이어서 고칠 문제 (P0)
**2026-10-22 업데이트 (122e82a, CI 39790238512 성공, Render Live):** 세 언어 실제 API 각각 200, 올바른 언어의 추천/이유와 실제 출처 확인. 한국어는 실제 브라우저에서 추천 → 모두 담기 → 방문 순서 → 기기 저장 → reload 복원까지 확인. 영어·미얀마어의 브라우저 담기/저장 흐름과 원어민 미얀마어 검수는 아직 남았다. 품질 주의: 지도 카탈로그 레코드만 근거로 한 이유에 '고요한 분위기' 같은 근거 밖 묘사가 섞일 수 있다(아래 VERIFICATION 참고). 아래 1–6은 수정 전 기록이다.
**추가 (ede59d9):** 지도 레코드만 인용한 이유는 범주 적합성만 말하도록 프롬프트를 제한했고 en/my 200에서 확인했다. 그러나 같은 날 재검사에서 한국어는 503(혼잡, 재시도 소진) 후 502(파이프라인 거부)로 **간헐적 실패가 남아 있다.** Render 로그의 `AI pipeline rejected response reason=` 고정 코드를 확인해 원인을 좁힐 것.

**(이전 기록) 세 언어 실제 AI 추천 검증이 아직 끝나지 않았다.**
1. Render에 TAVILY_API_KEY, GEMINI_API_KEY가 저장되어 있음을 확인했다. 키를 채팅/로그/저장소로 복사하지 않는다. status configured는 키 존재 확인일 뿐 호출 성공을 보장하지 않는다.
2. gemini-2.5-flash-lite 생성 API404를 실제 재현했다. 현재 코드는 gemini-3.1-flash-lite로 교체했으며 임베딩은 gemini-embedding-001이다. 모델 사용 가능 여부/무료 티어를 공식 문서와 실제 호출로 확인한다.
3. 모델 교체 후 한국어 요청200: 쉐다곤·술레·보족 시장 추천을 실제 확인했다. 하지만 원어 그대로 Tavily에 검색하면 무관한 영상이 섞여 영어 검색어 재작성과 관련 출처 선택을 추가했다.
4. 그 후 실제 세 언어 순차 검사: 영어200 및 관련 여행 출처, 한국어502 / 미얀마어502. 로그는 ValueError였다. 안전 검증을 제거해서 통과시키지 않는다.
5. 마지막 수정: 생성 JSON Schema에 조회된 장소 ID/근거 ID enum을 넣고 출력 한도를3000으로 늘림. 비밀/사용자 본문 없이 오류 원인을 정해진 코드로 로그에 남기도록 함. **이 마지막 수정 이후의 실제 모델·브라우저 성공은 아직 확인하지 않았다.** 현재 배포/CI 상태를 새로 확인할 것.
6. 확인할 오류 원인: Invalid search rewrite / Ungrounded recommendation / Invalid discovery evidence / 벡터 차원 등. 모델 본문·키를 로그로 남기지 말고 고정 오류 코드로 좁힌다. 검색어 재작성 실패의 복구와 근거 연관성 검증을 살펴본다.

수용 기준: 장소명을 쓰지 않은 취향 문장으로 ko/en/my 각각 실제200 → 올바른 언어의 추천/이유 → 실제 출처 → 지도에 담기 → 방문 순서 → 기기 저장 → reload 복원. 없는 장소·출처·가격·영업/안전 상태를 만들지 않는다. 원어민 미얀마어 품질 검수는 별도다.

## 다음 기능 (요청됨, 아직 구현 안 됨)
- 하나의 가져오기 화면: 공개 링크 + 본문 + 사진/스크린샷 업로드. 사진 OCR/시각적 장소 후보 추출. 실제 미디어 업로드 엔드포인트/UI는 아직 없다.
- 영상 업로드 → 제한된 주요 프레임/음성/자막 분석. 현재 제목/설명 검색은 영상 내용 분석이 아니다.
- 신규 장소/카페/지점 식별과 지오코딩, 서로 다른 SNS 출처의 동일 장소 병합. 지금 추천 가능한 좌표는 작은 기존 명소 카탈로그에 제한된다.
- 업로드 권한·크기/MIME·해상도/영상 길이 제한, 비용 상한, 비공개 보관·삭제, 개인정보 처리 동의, 출처/권리 확인, 지점 오인 검증을 설계할 것.
- 로그인 제한 콘텐츠를 무단 우회하지 않는다. 업로드/본문 입력을 대안으로 제공한다. 공식 API는 승인·동의 범위만. 모바일 공유해서 담기와 제휴 크리에이터 연결은 다음 단계이며 현재 구현 아님.
- 실제 리뷰/평점·트렌드 근거, 전국 상세 장소 확대, 실제 도로 이동/시간, 계정 저장/공유, 운영 보안/백업, 제휴 공급/확정/이행은 미완료. 구체적 사업화 우선순위는 COMMERCIAL_REVIEW.md.

## 중요한 코드 위치
- backend/app/recommendations.py: /discovery/ai-status, /discovery/recommend, Gemini 호출/임베딩/근거 검증/월 한도
- backend/app/discovery.py: Tavily 검색, 원문 URL 검증, 글의 이름 후보 추출, 지역 목록
- backend/app/catalog.py 및 data/: 출처 있는 실제 작은 장소 데이터
- backend/app/main.py: 내부 프록시 인증/요청 제한, 기존 API, 방문 순서
- frontend/app/AIRecommendations.tsx: 세 언어 취향/추천/출처/일괄 추가
- frontend/app/ContentTrip.tsx, Social.tsx: 콘텐츠 가져오기/발견/지도
- frontend/app/Trip.tsx, trip-storage.ts: 기기 저장 및 출처 검증
- frontend/app/api/[...path]/route.ts: same-origin 프록시, 본문16KB 제한. 향후 미디어를 현재 JSON 경로에 억지로 넣지 말 것.
- backend/tests/test_recommendations.py, test_discovery.py; frontend/tests/trip-storage.test.mjs

## 검증과 배포 상태
- 가장 최근 로컬: backend25 tests, frontend5 tests 통과; frontend build/typecheck 통과. SQLite migration004(head) 확인. 실제 PostgreSQL/Docker는 원격 CI와 구별한다.
- c40e171 CI39765332941 성공(6m21s)을 실제 GitHub에서 확인했다. 이후 모델/검색 개선 CI는 이 문서 작성 시 완료 상태를 재확인하지 않았다.
- 마지막 직접 확인한 운영 소스는31d01020ad5ff10c0b7e9892595280a5ded67d97, Render dep-dbd0dc4s728c73b3auhg Live(1m40s). 이후 enum/진단 수정 커밋은 GitHub 웹 편집기로 저장했으나 배포/CI/실제 호출 결과는 미확인. 이 해시는 최신 HEAD라는 뜻이 아니다.
- 보안 유지: 키 backend only, 실패를 가짜 결과로 바꾸지 않기, SNS 글을 지시로 실행하지 않기, 출처/가격/재고/안전 조작 금지. 새 실제 고객/예약 정보를 체험 환경에 넣지 않는다.
- Free Render 웹은 대기, 무료 PostgreSQL은 생성30일 만료. 현재 구성은 유료 사업 운영/SLA/영구 보관을 충족하지 않는다.

## 재현 명령 (자신의 환경에서 의존성 설치 후)
```sh
# 프로젝트 루트: Python3.12 환경에서
cd backend
python -m pytest -q
# 테스트용 DB만 지정하고 migrations 실행; 실제 운영DB로 테스트하지 말 것
DATABASE_URL=sqlite:////tmp/journey-handoff.sqlite python -m alembic upgrade head
DATABASE_URL=sqlite:////tmp/journey-handoff.sqlite python -m alembic current
cd ../frontend
pnpm test
pnpm build
```
로컬 실행/환경 변수는 README.md, .env.example, DEPLOY.md를 참고한다. Render 비밀값은 로컬 .env에 있다고 가정하지 않는다. 사용자 기존 localhost3000 서버는 확인 없이 종료/대체하지 않는다.
