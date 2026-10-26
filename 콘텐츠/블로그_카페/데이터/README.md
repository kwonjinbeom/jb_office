# 데이터 폴더 — 글쓰기가 먼저 보는 표 (2026-10-26)

블로그마다 남이 못 베끼는 숫자를 쌓는다 (하루치는 베낄 수 있어도 1년치 누적은 못 베낀다). 근거: `콘텐츠/블로그_카페/포스팅자동화/15_자동화블로그_차별화_2026-10-26.md`.
모두 UTF-8 CSV, 첫 줄이 머리, 첫 칸이 열쇠. 글쓰기 루틴이 원고와 함께 main 에 올린다.

## 공공 API 로 받는 표 — `manage.py collect_data`
글쓰기 루틴 메인이 기획 전에 돌린다 (`workspace/.venv/Scripts/python workspace/manage.py collect_data`). 코드: `workspace/apps/routines/datafeeds.py`.

| 파일 | 출처 | 남기는 기간 | 쓰는 곳 |
|---|---|---|---|
| 축제.csv | 관광공사 국문 관광정보(KorService2) `searchFestival2` | 끝난 지 7일까지, 앞으로 45일 | black_lukey 축제·주말 축제 카드 |
| 분양.csv | 청약홈 APT 분양정보 `getAPTLttotPblancDetail` | 접수 끝난 지 30일까지 | 눈잎 주택 공고·청약·공모주 달력 |
| 박스오피스.csv | KOBIS 주간 박스오피스 | 12주 | black_lukey 영화·OTT 달력 |
| 증권신고서.csv | OpenDART 공시검색 (지분증권 증권신고서 C001) | 180일 | 눈잎 공모주 (새 종목 신호) |
| 미국지수.csv | FRED `NASDAQCOM` · `SP500` | 400일 | 밤밤 나스닥 시황 노트 (대조용) |

**키 (사용자가 한 번 받아 `workspace/.env` 에 넣는다 — git 에 올라가지 않는다).** 키가 없는 출처는 건너뛰고 "키 없음"으로 나온다.
```
DATA_GO_KR_KEY=공공데이터포털 일반 인증키 (Decoding)
KOBIS_KEY=영화진흥위원회 오픈API 키
DART_KEY=OpenDART 인증키
FRED_KEY=FRED API 키
```
- 공공데이터포털(data.go.kr): 회원가입 → '한국관광공사_국문 관광정보 서비스_GW' 와 '한국부동산원_청약홈 분양정보 조회 서비스' 각각 **활용신청** (보통 바로 승인) → 마이페이지의 일반 인증키(Decoding). 하나의 키로 둘 다 쓴다.
- KOBIS: kobis.or.kr/kobisopenapi → 회원가입 → 키 발급.
- OpenDART: opendart.fss.or.kr → 인증키 신청 (이메일 인증).
- FRED: fred.stlouisfed.org → 계정 → API Keys.
- 처음 키를 넣은 날은 `collect_data` 결과에 '실패'가 없는지 본다. 응답 모양이 바뀌었으면 datafeeds.py 를 고친다 (2026-10-26 키 없이 만들어서 실제 응답으로는 아직 확인 전).

## 작가가 쌓는 표 — 원고를 쓸 때 그날 줄을 더한다
**코스피시황.csv · 나스닥시황.csv** (밤밤 시황 노트 두 시리즈, 한 편 = 한 줄, `writing_site_밤밤.md`. 2026-10-26 사용자: 한 편이던 시황 노트를 다시 나눔)
- `날짜`: 그 장의 날짜 (나스닥은 미국 날짜) · `no`: 그 파일에서 번호가 있는 마지막 줄 +1, 처음이면 1 (제목의 No.). 번호가 빈 줄은 예전 시황 글에서 옮긴 지난 날짜다 (5거래일 표에는 쓴다)
- 코스피: `코스피`·`코스닥` 종가 · `…등락률` 전일 대비 % (예: -1.23) · `원달러` 그날 종가 환율 · `외국인`·`기관`·`개인 순매수(억)` 코스피 기준 (+ 순매수, - 순매도)
- 나스닥: `나스닥`·`S&P500`·`다우` 종가와 등락률. 미국지수.csv(FRED)가 있으면 대조한다
- `메모`: 그날 한 줄 (휴장·특이사항) · `글`: 원고 폴더 이름 (예: T150_코스피오늘)

**공모주.csv** (눈잎 공모주, `writing_site_눈잎.md`) — 종목마다 한 줄. 새로 확인한 값을 더하거나 고치고 `고친 날`·`출처`를 바꾼다.
- 숫자는 원 단위, 비율은 % (예: 확약 32.5). `확정가 대비(%)` = (첫날 종가 / 확정 공모가 - 1) × 100, 소수 한 자리.

## 검색 성과 (구글 서치 콘솔) — `manage.py search_perf`
이 폴더가 아니라 `workspace/.routine/perf/` 에 쓴다 (git 에 올리지 않는다 — 저장소가 공개라 검색어 실적은 올리지 않는다). 프롬프트 최신화가 읽는다 (`일일루틴/프롬프트/prompt_update.md` '우리 글 성과로 배우기').
처음 한 번 (사용자):
1. Google Cloud 콘솔(console.cloud.google.com) → 새 프로젝트 → 'Google Search Console API' 사용 설정.
2. 'OAuth 동의 화면' → 외부 · 앱 이름만 → **게시 상태를 '프로덕션'으로** (테스트 상태면 7일마다 다시 로그인해야 한다).
3. '사용자 인증 정보' → OAuth 클라이언트 ID → 애플리케이션 유형 **데스크톱 앱** → 만든 클라이언트 ID·보안 비밀을 `workspace/.env` 에:
   ```
   GSC_CLIENT_ID=…apps.googleusercontent.com
   GSC_CLIENT_SECRET=…
   ```
4. PC 에서 `workspace/.venv/Scripts/python workspace/manage.py search_perf --auth` → 열리는 브라우저에서 서치 콘솔을 쓰는 구글 계정(wlsqja0124)으로 허용. 토큰이 `workspace/.routine/gsc_token.json` 에 남는다.
그 뒤로는 `manage.py search_perf` 가 서치 콘솔에 있는 모든 사이트(memorily·눈잎·밤밤)의 최근 28일 글×검색어를 받는다.
