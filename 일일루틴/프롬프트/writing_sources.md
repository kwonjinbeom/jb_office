# 조사 출처 (글쓰기 고정 출처)

글쓰기 조사는 여기 출처를 먼저 본다. 트렌드·순위(무엇이 뜨나)는 '공통'에서, 사실·숫자·일정(주요 최신 정보)과 소재 판정(있음/없음)은 사이트 > 소재별 출처에서 받는다 (2026-10-22: 글 분류 = 사이트 > 고정 소재).
고정 출처에 없는 새 소식이나 빈 곳은 WebSearch 로 채운다. 메인은 보조에게 '공통'과 그 소재의 표만 넘긴다.

읽기: **바로** = WebFetch 로 본문이 읽힘 · **브라우저** = 화면에서 그려지는 곳이라 playwright 로 연다 (안 되면 WebSearch 로 그 사이트 글을 찾는다) · **막힘** = 넘어간다.
주소 확인: 2026-10-20. 읽기가 **확인 전**인 줄은 2026-10-22 새로 더한 곳이다 (프롬프트 최신화가 열어 보고 고친다).

## 데이터 폴더 — 웹 검색보다 먼저 (2026-10-26)
`콘텐츠/블로그_카페/데이터/` 의 표. 메인이 기획 전에 `manage.py collect_data` 로 공공 API 값을 받아 둔다 (키가 없는 곳은 건너뛰고 그렇게 적힌다). 형식은 그 폴더의 README.md.
| 파일 | 무엇 | 채우는 쪽 |
|---|---|---|
| 축제.csv | 관광공사 TourAPI 축제 (앞으로 45일) | collect_data |
| 분양.csv | 청약홈 APT 분양 공고 (최근·다가오는 접수) | collect_data |
| 박스오피스.csv | KOBIS 주간 박스오피스 | collect_data |
| 증권신고서.csv | OpenDART 지분증권 증권신고서 (공모주 새 종목 신호) | collect_data |
| 미국지수.csv | FRED 나스닥·S&P500 종가 | collect_data |
| 시황노트.csv | 시황 노트 한 편 = 한 줄 (코스피·코스닥·나스닥·S&P500·환율) | 작가 (그날 줄을 먼저 더한다) |
| 공모주.csv | 종목마다 수요예측·청약·상장 결과 누적 | 작가 (새로 확인한 값을 더하거나 고친다) |

## 공통 — 트렌드·핫·순위
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 구글 트렌드 (한국 실시간) | https://trends.google.co.kr/trending?geo=KR | 급상승 검색어 | 바로 (목록이 잘리면 WebSearch 보조) |
| 네이버 뉴스 많이 본 | https://news.naver.com/main/ranking/popularDay.naver | 언론사별 많이 본 기사 | 바로 |
| 네이버 데이터랩 | https://datalab.naver.com/ | 분야별 인기 검색어·검색량 추이 | 브라우저 |
| 시그널 | https://www.signal.bz/ | 실시간 검색어 모음 | 바로 |
| 정책브리핑 보도자료 | https://www.korea.kr/briefing/pressReleaseList.do | 모든 부처의 오늘 발표 (정책·요금·일정의 원 출처) | 바로 |

## 눈잎 (티스토리)
### 주택 공고
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 마이홈 입주자 모집공고 | https://www.myhome.go.kr/hws/portal/sch/selectRsdtRcritNtcView.do | 행복주택·국민임대·매입임대 공고 모음 (전국), 자격 자가진단 | 바로 |
| LH 청약플러스 공고 | https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do | LH 행복주택·청년 매입임대·전세임대 공고와 접수일 | 브라우저 |
| SH 인터넷청약 | https://www.i-sh.co.kr/main/index.do | 서울 행복주택·청년안심주택·장기전세 공고 | 바로 |
| GH 경기주택도시공사 | https://www.gh.or.kr/ | 경기 행복주택·기존주택 매입임대 공고 | 바로 |
| 청약홈 | https://www.applyhome.co.kr/ai/aia/selectAPTLttotPblancListView.do | 분양 청약 일정, 신혼부부·생애최초 특별공급 | 바로 |
| 주택도시기금 | https://nhuf.molit.go.kr/ | 버팀목 전세·디딤돌 구입 대출 (청년·신혼·신생아 조건, 금리) | 바로 |
| 한국주택금융공사 | https://www.hf.go.kr/ | 보금자리론·전세보증 | 바로 |

### 청년·신혼 정책
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 온통청년 | https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch | 중앙·지자체 청년정책 통합 검색 (일자리·주거·금융·생활) | 바로 |
| 서울 청년몽땅정보통 | https://youth.seoul.go.kr/ | 서울 청년 월세·수당·통장 모집 | 브라우저 |
| 서울주거포털 | https://housing.seoul.go.kr/ | 서울 신혼부부·청년 임차보증금 이자 지원, 청년 월세 | 바로 |
| 저출산고령사회위원회 | https://www.betterfuture.go.kr/ | 결혼·출산 지원 정책 모음 (신혼부부) | 브라우저 |
| 정부24 혜택 알리미 | https://www.gov.kr/portal/rcvfvrSvc/main | 중앙·지자체 지원금 대상·신청 | 바로 |
| 복지로 | https://www.bokjiro.go.kr/ | 복지 서비스 대상·금액·신청 방법 | 브라우저 |
| 국세청 | https://www.nts.go.kr/ | 근로·자녀장려금, 연말정산 일정 | 바로 |
| 서민금융진흥원 | https://www.kinfa.or.kr/ | 청년도약계좌·서민 대출 상품 | 바로 |

정책 글로 이어지는 신호:
- 모집공고가 새로 뜨면: 접수 기간·자격(나이·소득·자산·무주택)·지역·임대료를 한 표로 → "이번 달 공고 달력", "내가 되나 자가 체크" 글.
- 기준이 바뀌면 (소득 기준·금리·나이): 작년 → 올해 before/after 표.
- 같은 이름이라도 지자체마다 다르다 (청년 월세·신혼 이자 지원): 서울·경기·내 지역을 나눠 쓴다.
- 금액·기준·접수일은 공고문 원문에서만 가져오고 공고 번호·날짜를 적는다. 블로그 글의 숫자는 쓰지 않는다.

### 공모주
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| KIND 공시 | https://kind.krx.co.kr/ | 상장사 공시·IPO 일정 | 바로 |
| 38커뮤니케이션 공모주 일정 | https://www.38.co.kr/html/fund/index.htm?o=k | 청약·환불·상장일 달력, 수요예측 결과 | 확인 전 |
| DART 증권신고서 | https://dart.fss.or.kr/ | 공모가 밴드·청약 일정 원문 | 확인 전 |

### 일본 (엔화·환율)
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 네이버 증권 환율 | https://finance.naver.com/marketindex/ | 엔화·달러 환율과 추이 | 바로 |
| 한국은행 ECOS | https://ecos.bok.or.kr/ | 기준 환율 통계 (오래된 추이) | 확인 전 |
| 하나은행 환율 | https://www.kebhana.com/ | 고시 환율·환전 수수료 우대 | 확인 전 |

### 일본 (여행) · 밤밤 해외여행
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 일본정부관광국 (JNTO) | https://www.japan.travel/ko/ | 일본 여행 제도·축제·시즌 | 확인 전 |
| 외교부 해외안전여행 | https://www.0404.go.kr/ | 나라별 입국 규정·안전 공지 | 확인 전 |
| 인천공항 | https://www.airport.kr/ | 노선·출국 혼잡·새 취항 | 확인 전 |

### 동물 (2026-10-26)
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 국립생물자원관 | https://www.nibr.go.kr/ | 국내 생물 정보·보도자료 | 확인 전 |
| 국립생태원 | https://www.nie.re.kr/ | 국내 생태·멸종위기종 | 확인 전 |
| 내셔널지오그래픽 동물 | https://www.nationalgeographic.com/animals | 종별 기본 사실 | 확인 전 |
| 사이언스데일리 동물 | https://www.sciencedaily.com/news/plants_animals/ | 새 연구 결과 (원 논문 링크) | 확인 전 |
| 구글 스칼라 | https://scholar.google.com/ | 원 논문 확인 (초록·연도·저널) | 확인 전 |
- 인터넷 '상식' 글·블로그는 근거로 쓰지 않는다. 숫자·연구 결과는 원 논문이나 기관 글에서, 연도·기관을 본문에 적는다.

## black_lukey (네이버)
### 지역 놀거리 · 축제·행사
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 대한민국 구석구석 | https://korean.visitkorea.or.kr/ | 축제·여행 코스 | 바로 |
| 산림청 | https://www.forest.go.kr/ | 단풍·산 정보 | 바로 |
| 기상청 | https://www.weather.go.kr/ | 계절 예보·첫눈·한파 | 바로 |

### 신제품 출시
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 애플 뉴스룸 | https://www.apple.com/kr/newsroom/ | 출시·업데이트 발표 | 바로 |
| 삼성 뉴스룸 | https://news.samsung.com/kr/ | 갤럭시 출시·One UI | 바로 |
| GSMArena 뉴스 | https://www.gsmarena.com/news.php3 | 신제품 스펙·출시 소식 | 바로 |

### 영화·OTT 공개
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 넷플릭스 TOP 10 | https://www.netflix.com/tudum/top10 | 국가별 이번 주 순위 | 바로 |
| KOBIS 영화관입장권 | https://www.kobis.or.kr/ | 박스오피스·개봉 예정 | 바로 |

### 세일 이벤트
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 코리아세일페스타 | https://www.koreasalefesta.kr/ | 국가 세일 기간·참여사 | 확인 전 |
| 올리브영 | https://www.oliveyoung.co.kr/ | 올영세일 기간·혜택 (이벤트 공지) | 확인 전 |
| 무신사 | https://www.musinsa.com/ | 무신사 블랙프라이데이 등 기획전 | 확인 전 |
| 유니클로 | https://www.uniqlo.com/kr/ko/ | 감사제·한정 특가 기간 | 확인 전 |
| 다나와 | https://danawa.com/ | 가격 추이 (세일이 진짜 싼지) | 바로 |

## 밤밤 (구글 블로거)
### 시황 노트 (코스피 + 나스닥 한 편, 2026-10-26)
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 한국은행 | https://www.bok.or.kr/portal/main/main.do | 기준금리·통화정책 일정 | 바로 |
| 금융위원회 보도자료 | https://www.fsc.go.kr/no010101 | 대출·예금 규제, 금융 정책 | 바로 |
| 네이버 증권 | https://finance.naver.com/ | 지수·환율·종목 시황 | 바로 |
| KIND 공시 | https://kind.krx.co.kr/ | 상장사 공시·IPO 일정 | 바로 |
| KRX 휴장일 | https://open.krx.co.kr/contents/MKD/01/0110/01100305/MKD01100305.jsp | 한국 휴장일 (소재 판정) | 확인 전 |
| Nasdaq 지수 | https://www.nasdaq.com/market-activity/index/comp | 나스닥 종가·등락 | 확인 전 |
| NYSE 휴장일 | https://www.nyse.com/markets/hours-calendars | 미국 휴장일 (소재 판정) | 확인 전 |
| CNBC 마켓 | https://www.cnbc.com/markets/ | 간밤 미국 증시 원인 기사 | 확인 전 |
| 네이버 증권 (playwright) | https://stock.naver.com/ | 일별 시세·투자자별 매매·등락 종목 (2026-10-23 기획표: WebFetch 막힘, 브라우저로 읽힘) | 브라우저 |

막힘: 뽐뿌(403) → WebSearch "뽐뿌 <검색어>". 다음 뉴스 랭킹(주소 없어짐) → 네이버 뉴스 많이 본.

## memorily (커스텀 글쓰기 · AI 소식)
### AI 소식
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| Anthropic 뉴스 | https://www.anthropic.com/news | Claude 출시·기능 | 바로 |
| OpenAI 뉴스 | https://openai.com/news/ | ChatGPT·Codex 출시·기능 | 바로 |
| Google AI 블로그 | https://blog.google/technology/ai/ | Gemini 등 구글 AI | 확인 전 |
| Hugging Face 인기 모델 | https://huggingface.co/models?sort=trending | 뜨는 오픈소스 모델 | 확인 전 |
| Product Hunt AI | https://www.producthunt.com/topics/artificial-intelligence | 새로 뜨는 AI 서비스 | 확인 전 |
| GeekNews | https://news.hada.io/ | 국내 개발자가 모은 AI·도구 소식 | 바로 |
| AI타임스 | https://www.aitimes.com/ | 국내 AI 소식 (네이버·카카오·LG·업스테이지 등) | 확인 전 |
| Hacker News | https://news.ycombinator.com/ | 해외에서 화제인 AI 출시 | 확인 전 |
