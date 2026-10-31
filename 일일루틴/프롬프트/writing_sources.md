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
| 코스피시황.csv · 나스닥시황.csv | 시황 노트 한 편 = 한 줄 (코스피: 코스피·코스닥·환율·수급 / 나스닥: 나스닥·S&P500·다우) | 작가 (그날 줄을 먼저 더한다) |
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

### 생활 (2026-10-27)
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 정책브리핑 보도자료 | https://www.korea.kr/briefing/pressReleaseList.do | 접종·검진·요금·신고 일정 발표의 원 출처 | 바로 |
| 질병관리청 예방접종도우미 | https://nip.kdca.go.kr/ | 무료 예방접종 대상·기간·지정 의료기관 | 브라우저 |
| 국민건강보험공단 | https://www.nhis.or.kr/ | 국가건강검진 대상(출생연도 짝·홀)·보험료 개편 | 브라우저 |
| 국세청 | https://www.nts.go.kr/ | 종합소득세·연말정산·근로장려금 일정 | 바로 |
| 위택스 | https://www.wetax.go.kr/ | 자동차세 연납·재산세·주민세 기한 | 브라우저 |
| 정부24 | https://www.gov.kr/ | 지원금·바우처·민원 일정, 혜택 알리미 | 바로 |
| 한국전력 · 도시가스 요금 공지 | https://home.kepco.co.kr/ | 전기요금 조정·누진 구간 | 바로 |

생활 글로 이어지는 신호: 부처 보도자료의 '○일부터 시행·접수', 출생연도로 대상이 갈리는 제도, 작년과 날짜·금액이 달라진 것.

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

### 세일 이벤트 (2026-10-31 사용자 — 검색량 순 = 우선순위, 위에서부터 연다)
검색량은 2026-10-31 구글 트렌드 12개월 합(올영세일 = 100). 판정·편수 규칙은 `writing_topics.md` 1단계.

**고정 5곳 (무조건 먼저, 이 순서로)**
| 순 | 브랜드 | 검색량 | 주소 | 무엇을 보나 | 지난 시기 | 읽기 |
|---|---|---|---|---|---|---|
| 1 | 올리브영 | 100 | https://www.oliveyoung.co.kr/ | 올영세일·올영데이 기간·혜택 (앱 이벤트 공지) | 올영세일 3·6·9·12월 초 · 올영데이 매달 하순 | 확인 전 |
| 2 | 유니클로 | 53 | https://www.uniqlo.com/kr/ko/ | 감사제 기간·한정 특가 | 감사제 11월 하순~12월 초 · 5월 하순~6월 초 | 확인 전 |
| 3 | 무신사 | 48 | https://www.musinsa.com/ | 무진장(겨울·여름)·블랙프라이데이 | 무진장 블프 11월 중순 · 여름 무진장 6월 | 확인 전 |
| 4 | 자라 | 31 | https://www.zara.com/kr/ | 블프·시즌오프 시작일 | 블프 11월 말 · 겨울 시즌오프 12월 중순 · 여름 6월 하순 | 확인 전 |
| 5 | SSG (쓱데이·신세계) | 28 | https://www.ssg.com/ · https://www.shinsegae.com/ | 쓱데이 행사 페이지(해마다 `ssg.com/hub/ssgday-연도-info`) · 신세계백화점·아울렛 정기 세일 | 쓱데이 10월 말~11월 초 · 백화점 정기 세일 1·4·7·10월 | 확인 전 |

**A 혜택 시즌 (날짜가 정해진 것 — 고정과 함께 '있음'이면 다 쓴다)**
| 순 | 시즌 | 검색량 | 쓸 때 | 무엇을 보나 |
|---|---|---|---|---|
| 1 | 블랙프라이데이 총정리 | 282 | 11월 중순~말 (국내 주요 블프 공지가 2곳 이상 뜬 뒤) | 고정 5곳·나이키·애플·아마존 등 각 공식 공지 |
| 2 | 화이트데이 | 211 | 3월 4~11일 | 편의점(GS25·CU·세븐일레븐)·제과·브랜드 한정 기획 |
| 3 | 발렌타인데이 | 192 | 2월 4~11일 | 같은 곳 |
| 4 | 크리스마스 선물·케이크 사전예약 | 86 · 40 | 11월 말~12월 초 | 호텔·파리바게뜨·뚜레쥬르·스타벅스 케이크 사전예약 공지, 브랜드 홀리데이 기획 |
| 5 | 수험생 할인 | 55 | 수능 3~7일 전 ~ 수능 다음 날 | 브랜드별 수험표 할인 공식 공지 |
| 6 | 빼빼로데이 | 46 | 11월 1~8일 | 편의점 3사·롯데웰푸드 공식 기획 |
| 7 | 어버이날 선물 | 33 | 4월 말~5월 초 | 백화점·브랜드 기획전 |

**B 생활 혜택 (고정·A 가 하나도 없는 날만)**
| 순 | 주제 | 검색량 | 무엇을 보나 |
|---|---|---|---|
| 1 | 다이소 뷰티 신상 | 38 | https://www.daisomall.co.kr/ 신상·품절 공지 |
| 2 | 네이버페이 이번 달 적립 이벤트 | 36 | 네이버페이 이벤트 페이지 |
| 3 | 배달·피자 할인 (도미노·배민) | 31 · 26 | https://web.dominos.co.kr/ 이벤트 · 배민 앱 이벤트 |
| 4 | 스타벅스 프리퀀시·시즌 이벤트 | 23 | https://www.starbucks.co.kr/ 이벤트 |

**쓰지 않는 곳 (검색량이 고정 5위보다 훨씬 낮다):** 29CM 이구위크 3 · 쿠팡 세일 6 · 코리아세일페스타 5 · 11번가 그랜드십일절 0.2 · 나이키·아디다스 세일 2~3 · 르메르·마뗑킴 세일 0. 그 외 브랜드는 그 행사의 검색량이 자라(31)보다 높다고 확인될 때만 고정처럼 본다 (블프 총정리 안 한 줄은 된다).

### 영화·OTT 공개
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 넷플릭스 TOP 10 | https://www.netflix.com/tudum/top10 | 국가별 이번 주 순위 | 바로 |
| KOBIS 영화관입장권 | https://www.kobis.or.kr/ | 박스오피스·개봉 예정 | 바로 |

## 밤밤 (구글 블로거)
### 코스피 시황 노트 · 나스닥 시황 노트 (2026-10-26 두 시리즈)
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

## 워드프레스 jinbaam.com (2026-10-26)
### 산과 캠핑
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 산림청 숲에ON (100대 명산·등산로) | https://www.foresttrip.go.kr/ | 명산 정보·자연휴양림 예약 | 확인 전 |
| 산림청 단풍·꽃 예측 | https://www.forest.go.kr/ | 단풍·봄꽃 절정 예측 | 바로 |
| 국립공원공단 예약 | https://reservation.knps.or.kr/ | 대피소·야영장 예약 오픈일 | 확인 전 |
| 국립공원공단 | https://www.knps.or.kr/ | 탐방로 통제·코스·탐방 예약 | 확인 전 |
| 고캠핑 | https://www.gocamping.or.kr/ | 전국 야영장 시설·예약 (공공데이터 15101933) | 확인 전 |
| 기상청 산악 예보 | https://www.weather.go.kr/ | 산 날씨·상고대·눈 | 바로 |

### 드라이브·자동차
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 오피넷 | https://www.opinet.co.kr/ | 주간·시도별 기름값 (공공데이터 15163154) | 확인 전 |
| 한국도로공사 | https://www.ex.co.kr/ | 통행료·휴게소·교통 예보 | 확인 전 |
| 위택스 | https://www.wetax.go.kr/ | 자동차세·연납 할인 | 확인 전 |
| 한국교통안전공단 | https://www.kotsa.or.kr/ | 자동차 검사·리콜 | 확인 전 |
| 무공해차 통합누리집 | https://ev.or.kr/ | 전기차 보조금·충전 | 확인 전 |
| 제조사 뉴스룸 (현대·기아·KGM·르노·쉐보레·테슬라·BMW·벤츠) | 각 사 뉴스룸 | 신차·연식 변경·가격 | 확인 전 |

### 국내여행 (외국인용, 영어)
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| VisitKorea (영문) | https://english.visitkorea.or.kr/ | 관광지·축제 영문 정보 | 확인 전 |
| Visit Seoul | https://english.visitseoul.net/ | 서울 영문 안내 | 확인 전 |
| 코레일 (영문) | https://www.letskorail.com/ebizbf/EbizBfTicketSearch.do | KTX 외국인 예매 | 확인 전 |
| K-ETA | https://www.k-eta.go.kr/ | 전자여행허가·면제 국가 | 확인 전 |
| 관광지 집중률 예측 | https://www.data.go.kr/data/15128555/openapi.do | 30일 혼잡 예측 | 확인 전 |

### 해외여행 (영어 N박 N일)
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 각국 관광청 공식 사이트 | (그 나라) | 명소·교통·패스 | 확인 전 |
| 미국 국무부 여행 정보 | https://travel.state.gov/ | 영어권 여권 기준 입국·안전 | 확인 전 |
| 영국 외무부 여행 안내 | https://www.gov.uk/foreign-travel-advice | 입국 조건·안전 | 확인 전 |
- 일본·밤밤과 겹치는 도시는 writing_topics.md 반복 규칙대로.

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
