"""메뉴 레지스트리.

새 메뉴(앱)를 추가할 때는 여기에 항목 하나만 넣으면 홈 카드와 좌측 내비게이션에 함께 나타난다.
- key: 앱 이름(urls.py 의 app_name)과 같게 둔다. 현재 메뉴 강조에 쓴다.
- url_name: reverse() 가능한 이름.
- icon: templates/includes/icons.html 의 symbol 이름 (i-<icon>). 없는 아이콘은 그 파일에 추가한다.
- color: 홈 카드의 아이콘 색. 사무적인 톤의 색만 쓴다.
"""
from dataclasses import dataclass

from django.urls import reverse


@dataclass(frozen=True)
class Menu:
    key: str
    title: str
    description: str
    url_name: str
    icon: str
    color: str = "#2f6bd8"

    @property
    def url(self) -> str:
        return reverse(self.url_name)


MENUS: list[Menu] = [
    Menu("daily_ideas", "일일 아이디어", "날짜별로 조사한 후보를 비교하고 필요한 것만 담는 곳", "daily_ideas:list", "sparkles", "#334155"),
    Menu("ideas", "내 아이디어", "내가 고른 후보를 단계별로 실제 작업으로 바꾸는 곳", "ideas:list", "bulb", "#2f6bd8"),
    Menu("memos", "메모", "떠오른 생각, 참고 사항을 빠르게 기록", "memos:list", "memo", "#64748b"),
    Menu("docs", "문서", "시장조사 폴더의 문서를 화면에서 읽기 (읽기 전용)", "docs:list", "book", "#475569"),
]


def get_menus() -> list[Menu]:
    return MENUS
