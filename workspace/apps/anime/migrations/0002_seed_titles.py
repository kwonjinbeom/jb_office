"""전체 애니 목록 첫 묶음 (2026-10-23 사용자: 회차정리를 할 만한 장편 명작부터, 유명한 순).
이미 글을 쓴 6작품은 담은 채로 (나루토 발행 완료, 나머지 원고 완료) 작품 md 와 잇는다. 같은 제목이 있으면 넣지 않는다."""
from django.db import migrations

# (제목, 메모, 상태, 작품 md)
TITLES = [
    ("원피스", "1999~", "written", "04_원피스"),
    ("나루토", "2002~", "published", "01_나루토"),
    ("드래곤볼", "1986~", "todo", ""),
    ("명탐정 코난", "1996~", "todo", ""),
    ("블리치", "2004~", "written", "02_블리치"),
    ("헌터×헌터", "1999~", "written", "03_헌터x헌터"),
    ("진격의 거인", "2013~", "todo", ""),
    ("귀멸의 칼날", "2019~", "todo", ""),
    ("강철의 연금술사", "2003~", "written", "05_강철의연금술사"),
    ("나의 히어로 아카데미아", "2016~", "written", "06_히로아카"),
    ("주술회전", "2020~", "todo", ""),
    ("슬램덩크", "1993~", "todo", ""),
    ("은혼", "2006~", "todo", ""),
    ("이누야샤", "2000~", "todo", ""),
    ("페어리 테일", "2009~", "todo", ""),
    ("하이큐!!", "2014~", "todo", ""),
    ("죠죠의 기묘한 모험", "2012~", "todo", ""),
    ("포켓몬스터", "1997~", "todo", ""),
    ("보루토", "2017~", "todo", ""),
    ("블랙 클로버", "2017~", "todo", ""),
    ("일곱 개의 대죄", "2014~", "todo", ""),
    ("소드 아트 온라인", "2012~", "todo", ""),
    ("전생했더니 슬라임이었던 건에 대하여", "2018~", "todo", ""),
    ("Re:제로부터 시작하는 이세계 생활", "2016~", "todo", ""),
    ("원펀맨", "2015~", "todo", ""),
    ("도쿄 리벤저스", "2021~", "todo", ""),
    ("스파이 패밀리", "2022~", "todo", ""),
    ("장송의 프리렌", "2023~", "todo", ""),
    ("약사의 혼잣말", "2023~", "todo", ""),
    ("킹덤", "2012~", "todo", ""),
    ("가정교사 히트맨 리본", "2006~", "todo", ""),
    ("유유백서", "1992~", "todo", ""),
    ("테니스의 왕자", "2001~", "todo", ""),
    ("쿠로코의 농구", "2012~", "todo", ""),
    ("다이아몬드 에이스", "2013~", "todo", ""),
    ("불꽃 소방대", "2019~", "todo", ""),
    ("닥터 스톤", "2019~", "todo", ""),
    ("오버로드", "2015~", "todo", ""),
    ("코드 기어스", "2006~", "todo", ""),
    ("몬스터", "2004~", "todo", ""),
]


def forward(apps, schema_editor):
    AnimeTitle = apps.get_model("anime", "AnimeTitle")
    for i, (title, note, status, doc) in enumerate(TITLES, start=1):
        if AnimeTitle.objects.filter(title=title).exists():
            continue
        AnimeTitle.objects.create(title=title, note=note, status=status, doc_key=doc, picked=bool(doc), order=i * 10)


class Migration(migrations.Migration):

    dependencies = [
        ("anime", "0001_initial"),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
