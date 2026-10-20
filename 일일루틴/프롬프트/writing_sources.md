# 조사 출처 (글쓰기 고정 출처)

글쓰기 조사는 여기 출처를 먼저 본다. 트렌드·순위(무엇이 뜨나)는 '공통'에서, 사실·숫자·일정(주요 최신 정보)은 분류별 공식 출처에서 받는다.
고정 출처에 없는 새 소식이나 빈 곳은 WebSearch 로 채운다. 메인은 보조에게 '공통'과 그 분류의 줄만 넘긴다.

읽기: **바로** = WebFetch 로 본문이 읽힘 · **브라우저** = 화면에서 그려지는 곳이라 playwright 로 연다 (안 되면 WebSearch 로 그 사이트 글을 찾는다) · **막힘** = 넘어간다.
주소 확인: 2026-10-20 (프롬프트 최신화가 다시 확인하고 고친다).

## 공통 — 트렌드·핫·순위
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 구글 트렌드 (한국 실시간) | https://trends.google.co.kr/trending?geo=KR | 급상승 검색어 | 바로 (목록이 잘리면 WebSearch 보조) |
| 네이버 뉴스 많이 본 | https://news.naver.com/main/ranking/popularDay.naver | 언론사별 많이 본 기사 | 바로 |
| 네이버 데이터랩 | https://datalab.naver.com/ | 분야별 인기 검색어·검색량 추이 | 브라우저 |
| 시그널 | https://www.signal.bz/ | 실시간 검색어 모음 | 바로 |
| 정책브리핑 보도자료 | https://www.korea.kr/briefing/pressReleaseList.do | 모든 부처의 오늘 발표 (정책·요금·일정의 원 출처) | 바로 |

## 광고 수익
### 정책·내 돈 — 공통
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 정부24 혜택 알리미 | https://www.gov.kr/portal/rcvfvrSvc/main | 중앙·지자체 지원금 대상·신청 | 바로 |
| 복지로 | https://www.bokjiro.go.kr/ | 복지 서비스 대상·금액·신청 방법 | 브라우저 |
| 국세청 | https://www.nts.go.kr/ | 근로·자녀장려금, 연말정산 일정 | 바로 |
| 서민금융진흥원 | https://www.kinfa.or.kr/ | 청년도약계좌·서민 대출 상품 | 바로 |

### 정책·내 돈 — 주거 (행복주택·청년주택·청약)
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 마이홈 입주자 모집공고 | https://www.myhome.go.kr/hws/portal/sch/selectRsdtRcritNtcView.do | 행복주택·국민임대·매입임대 공고 모음 (전국), 자격 자가진단 | 바로 |
| LH 청약플러스 공고 | https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do | LH 행복주택·청년 매입임대·전세임대 공고와 접수일 | 브라우저 |
| SH 인터넷청약 | https://www.i-sh.co.kr/main/index.do | 서울 행복주택·청년안심주택·장기전세 공고 | 바로 |
| GH 경기주택도시공사 | https://www.gh.or.kr/ | 경기 행복주택·기존주택 매입임대 공고 | 바로 |
| 청약홈 | https://www.applyhome.co.kr/ai/aia/selectAPTLttotPblancListView.do | 분양 청약 일정, 신혼부부·생애최초 특별공급 | 바로 |
| 주택도시기금 | https://nhuf.molit.go.kr/ | 버팀목 전세·디딤돌 구입 대출 (청년·신혼·신생아 조건, 금리) | 바로 |
| 한국주택금융공사 | https://www.hf.go.kr/ | 보금자리론·전세보증 | 바로 |

### 정책·내 돈 — 청년·신혼부부
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 온통청년 | https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch | 중앙·지자체 청년정책 통합 검색 (일자리·주거·금융·생활) | 바로 |
| 서울 청년몽땅정보통 | https://youth.seoul.go.kr/ | 서울 청년 월세·수당·통장 모집 | 브라우저 |
| 서울주거포털 | https://housing.seoul.go.kr/ | 서울 신혼부부·청년 임차보증금 이자 지원, 청년 월세 | 바로 |
| 저출산고령사회위원회 | https://www.betterfuture.go.kr/ | 결혼·출산 지원 정책 모음 (신혼부부) | 브라우저 |

정책 글로 이어지는 신호:
- 모집공고가 새로 뜨면: 접수 기간·자격(나이·소득·자산·무주택)·지역·임대료를 한 표로 → "이번 달 공고 달력", "내가 되나 자가 체크" 글.
- 기준이 바뀌면 (소득 기준·금리·나이): 작년 → 올해 before/after 표.
- 같은 이름이라도 지자체마다 다르다 (청년 월세·신혼 이자 지원): 서울·경기·내 지역을 나눠 쓴다.
- 금액·기준·접수일은 공고문 원문에서만 가져오고 공고 번호·날짜를 적는다. 블로그 글의 숫자는 쓰지 않는다.

### 금융·시장
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 한국은행 | https://www.bok.or.kr/portal/main/main.do | 기준금리·통화정책 일정 | 바로 |
| 금융위원회 보도자료 | https://www.fsc.go.kr/no010101 | 대출·예금 규제, 금융 정책 | 바로 |
| 네이버 증권 | https://finance.naver.com/ | 지수·환율·종목 시황 | 바로 |
| KIND 공시 | https://kind.krx.co.kr/ | 상장사 공시·IPO 일정 | 바로 |

### 생활 일정·요금
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 한전 사이버지점 | https://online.kepco.co.kr/ | 전기요금표·할인 | 바로 |
| 한국가스공사 | https://www.kogas.or.kr/ | 도시가스 원료비·요금 조정 | 바로 |
| 국가법령정보센터 | https://www.law.go.kr/ | 시행일·바뀌는 법 | 바로 |

### 콘텐츠·엔터
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 넷플릭스 TOP 10 | https://www.netflix.com/tudum/top10 | 국가별 이번 주 순위 | 바로 |
| KOBIS 영화관입장권 | https://www.kobis.or.kr/ | 박스오피스·개봉 예정 | 바로 |
| 멜론 차트 | https://www.melon.com/chart/index.htm | 음원 순위 | 바로 |

### 스포츠 일정
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| KBO | https://www.koreabaseball.com/ | 경기 일정·결과·포스트시즌 | 바로 |
| K리그 | https://www.kleague.com/ | 경기 일정 | 바로 |

### IT·앱 / IT 소식·제품
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 애플 뉴스룸 | https://www.apple.com/kr/newsroom/ | 출시·업데이트 발표 | 바로 |
| 삼성 뉴스룸 | https://news.samsung.com/kr/ | 갤럭시 출시·One UI | 바로 |
| GSMArena 뉴스 | https://www.gsmarena.com/news.php3 | 신제품 스펙·출시 소식 | 바로 |

### 시험·교육
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 큐넷 | https://www.q-net.or.kr/ | 국가자격 시험 일정·발표일 | 바로 |
| 한국교육과정평가원 (수능) | https://www.suneung.re.kr/ | 수능·모의평가 일정 | 바로 |

### 여행·계절
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 대한민국 구석구석 | https://korean.visitkorea.or.kr/ | 축제·여행 코스 | 바로 |
| 산림청 | https://www.forest.go.kr/ | 단풍·산 정보 | 바로 |
| 기상청 | https://www.weather.go.kr/ | 계절 예보·첫눈·한파 | 바로 |

## 판매 수익 (고르기·문제 해결·타이밍·선물·비용 계산·생활 장면·여행·체험)
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| 다나와 | https://danawa.com/ | 가격 비교·인기 순위·최저가 추이 | 바로 |
| 클리앙 모두의공원 | https://www.clien.net/service/board/park | 생활 고민·제품 후기 반응 | 바로 |
| 대한민국 구석구석 | https://korean.visitkorea.or.kr/ | 여행·체험 코스 (예약 연결 전 확인) | 바로 |

막힘: 뽐뿌(403) → WebSearch "뽐뿌 <품목>". 다음 뉴스 랭킹(주소 없어짐) → 네이버 뉴스 많이 본.

## IT/AI
### AI 도구·활용
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| Anthropic 뉴스 | https://www.anthropic.com/news | Claude 출시·기능 | 바로 |
| OpenAI 뉴스 | https://openai.com/news/ | ChatGPT 출시·기능 | 바로 |
| GeekNews | https://news.hada.io/ | 국내 개발자가 모은 AI·도구 소식 | 바로 |

### 개발·코딩
| 사이트 | 주소 | 무엇을 보나 | 읽기 |
|---|---|---|---|
| GitHub Trending | https://github.com/trending | 뜨는 저장소 | 바로 |
| GeekNews | https://news.hada.io/ | 개발 소식 | 바로 |
| 공식 문서 출시 노트 | 예: https://nodejs.org/en/blog | 버전·에러 기준 (글에 쓰는 도구의 공식 블로그·릴리스 노트) | 바로 |
