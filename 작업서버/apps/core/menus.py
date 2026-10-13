"""메뉴 레지스트리.

새 메뉴(앱)를 추가할 때는 여기에 항목 하나만 넣으면 홈 카드와 좌측 내비게이션에 함께 나타난다.
- key: 앱 이름(urls.py 의 app_name)과 같게 둔다. 현재 메뉴 강조에 쓴다.
- url_name: reverse() 가능한 이름.
- color: 카드 상단 색 띠. 사무적인 톤의 색만 쓴다.
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
    color: str = "#2563eb"

    @property
    def url(self) -> str:
        return reverse(self.url_name)


MENUS: list[Menu] = [
    Menu(
        key="ideas",
        title="아이디어 리스트",
        description="시장조사에서 나온 후보 C01~C35를 카드로 보고, 눌러서 상세 확인·수정",
        url_name="ideas:list",
        icon="💡",
        color="#2563eb",
    ),
    Menu(
        key="memos",
        title="메모",
        description="작업 중 떠오른 생각, 할 일, 참고 링크를 빠르게 기록",
        url_name="memos:list",
        icon="📝",
        color="#059669",
    ),
]


def get_menus() -> list[Menu]:
    return MENUS
