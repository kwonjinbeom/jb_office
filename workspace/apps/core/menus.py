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
    Menu("ideas", "아이디어", "후보 하나를 골라 단계별로 실현해 가는 곳. 단계·할 일·증거·로그가 한 화면에", "ideas:list", "💡", "#2563eb"),
    Menu("memos", "메모", "떠오른 생각, 참고 사항을 빠르게 기록", "memos:list", "📝", "#64748b"),
    Menu("docs", "문서", "시장조사 폴더의 문서를 화면에서 읽기 (읽기 전용)", "docs:list", "📄", "#475569"),
]


def get_menus() -> list[Menu]:
    return MENUS
