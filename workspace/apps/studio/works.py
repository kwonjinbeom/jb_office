"""창작콘텐츠 시제품 (2026-10-22 사용자: 상상을 여러 방식의 창작물로 바꿀 수 있는지 검증. 게시용 아님).

작품 하나 = 소재 하나. 같은 컷 대본으로 방식마다 결과물을 만든다.
- cuts: 컷마다 자막(cap)과 그림 속 글자(say). 그림은 static/studio/js/works/<key>.js 가 이 글자를 받아 그린다.
  dur·sfx·narr 는 숏폼 영상용 (초, 효과음 이름, 내 목소리로 녹음할 대사).
- 글은 여기 한곳만 고친다. 카툰·숏폼·쓰레드·설정집이 모두 이 값을 읽는다.
DB 없음 — 검증용이라 코드에 둔다. 마음에 드는 방식이 정해지면 그때 소재함·제작 대기열을 DB 로 만든다.
"""

FRIDGE = {
    "key": "fridge",
    "no": 1,
    "series": "생각꼬리 #1",
    "title": "냉장고 앞에서 까먹는 이유",
    "logline": "냉장고 문을 열면 왜 까먹을까 — 불, 콘센트, 냉동, 해동으로 꼬리를 물다 결국 물은 못 마신다.",
    "made": "2026-10-22",
    # 생각이 꼬리를 무는 순서 (한 줄씩)
    "tail": [
        "냉장고를 열자 까먹었다",
        "냉장고 불이 켜질 때 내 불이 꺼진다",
        "같은 콘센트를 쓰나?",
        "생각이 얼어서 떨어진다",
        "냉동실엔 까먹은 게 다 있다",
        "해동하면 돌아온다?",
        "너무 녹아서 영어단어까지 나온다",
        "꽉 찬 머리가 새 생각을 밀어낸다",
        "밀려난 생각은 다시 냉장고로",
        "엄마: 전기세나 기억해",
    ],
    "cuts": [
        {"cap": "냉장고 앞에서\n까먹는 이유", "hook": "냉장고 열면 왜 까먹는지\n드디어 알아냈다",
         "say": {"series": "생각꼬리 #1"},
         "dur": 2.8, "sfx": [[0.15, "pop"], [1.2, "hum_on"]],
         "screen": "닫힌 냉장고 앞에 선 나, 머리 위 물음표",
         "narr": "냉장고 열면 왜 까먹는지 드디어 알아냈다."},
        {"cap": "물 마시러 가서\n냉장고 문을 열었다.",
         "say": {"think": "…뭐 하러 왔더라?"},
         "dur": 3.9, "sfx": [[0.1, "steps"], [1.15, "door"], [2.3, "pop"]],
         "screen": "냉장고 문이 열리고 안쪽 불빛, 멍한 얼굴",
         "narr": "물 마시러 가서 냉장고 문을 열었는데… 뭐 하러 왔더라?"},
        {"cap": "냉장고 불은 켜지고\n나는 깜빡했다.",
         "say": {"left": "딸깍", "right": "깜빡", "note": "냉장고 말고 나"},
         "dur": 4.2, "sfx": [[0.5, "click"], [1.9, "blink"]],
         "screen": "왼쪽 냉장고 전구 켜짐 · 오른쪽 내 머리 전구 꺼짐",
         "narr": "냉장고 불은 켜지고, 나는 깜빡했다."},
        {"cap": "혹시 냉장고랑 나,\n같은 콘센트 쓰나?",
         "say": {"a": "냉장고", "b": "나", "talk": "전기가 모자랐구나…"},
         "dur": 4.3, "sfx": [[0.7, "plug"], [1.1, "plug"], [2.5, "sad"]],
         "screen": "멀티탭 하나에 냉장고 플러그와 내 머리에서 나온 플러그",
         "narr": "혹시 냉장고랑 나랑 같은 콘센트 쓰나?"},
        {"cap": "아니면 생각이\n냉기에 얼어버린 걸지도.",
         "say": {"ice": "물 마셔야지", "drop": "툭"},
         "dur": 4.1, "sfx": [[0.5, "freeze"], [2.0, "ice"]],
         "screen": "생각 말풍선이 얼음이 되어 냉장고 안으로 툭",
         "narr": "아니면 생각이 냉기에 얼어버린 걸지도."},
        {"cap": "그럼 냉동실엔 내가\n까먹은 게 다 얼어 있겠네.",
         "say": {"items": ["우산 둔 데", "그 배우 이름", "와이파이 비번", "하려던 말", "중2 때 다짐", "물 마셔야지"]},
         "dur": 4.8, "sfx": [[0.2, "door"], [0.9, "pop"], [1.3, "pop"], [1.7, "pop"], [2.1, "pop"], [2.5, "pop"], [2.9, "pop"]],
         "screen": "냉동실 칸칸이 얼음 덩어리, 덩어리마다 까먹은 것",
         "narr": "그럼 냉동실엔 내가 까먹은 게 다 얼어 있겠네."},
        {"cap": "해동하면\n돌아오지 않을까?",
         "say": {"btn": "해동", "time": "3:00", "talk": "그 배우 이름부터…"},
         "dur": 4.2, "sfx": [[0.8, "beep"], [1.05, "beep"], [1.3, "beep"], [1.5, "micro"]],
         "screen": "전자레인지 해동 버튼을 누르는 나, 3분",
         "narr": "해동하면 돌아오지 않을까?"},
        {"cap": "너무 오래 돌렸다.\n중학교 영어단어가 같이 녹았다.",
         "say": {"words": ["ambitious", "necessary", "근의 공식", "애국가 4절", "abandon", "출석번호 17번", "photosynthesis", "주기율표"]},
         "dur": 4.9, "sfx": [[0.15, "ding"], [0.8, "flood"]],
         "screen": "전자레인지 문이 열리며 단어가 쏟아짐, 놀란 얼굴",
         "narr": "너무 오래 돌렸다. 중학교 영어단어가 같이 녹았다."},
        {"cap": "머리가 꽉 차니까\n방금 생각이 밀려났다.",
         "say": {"steps": ["머리", "냉장고", "냉동실", "해동"], "talk": "그래서 다들 냉장고 앞에서 까먹는구나"},
         "dur": 5.0, "sfx": [[0.6, "swish"], [1.3, "swish"], [2.0, "swish"], [2.7, "swish"], [3.4, "pop"]],
         "screen": "머리 → 냉장고 → 냉동실 → 해동 → 머리, 도는 화살표",
         "narr": "머리가 꽉 차니까 방금 생각이 밀려났다. 그래서 다들 냉장고 앞에서 까먹는 거였다."},
        {"cap": "엄마한테도\n설명했다.",
         "say": {"mom": "냉장고 문 좀 닫아!!", "me": "기억 해동 중이야…", "mom2": "전기세나 기억해", "end": "(물은 못 마셨다)"},
         "dur": 6.2, "sfx": [[0.25, "shout"], [2.0, "pop"], [3.3, "shout2"], [4.9, "rimshot"], [5.0, "hum_off"]],
         "screen": "화면 밖 엄마 말풍선, 나는 냉장고 문을 잡은 채",
         "narr": "(엄마) 냉장고 문 좀 닫아! (나) 기억 해동 중이야… (엄마) 전기세나 기억해."},
    ],
    "insta": {
        "caption": "냉장고 문 열고 멍 때리는 거 나만 그런 거 아니죠\n전기세는 기억했습니다",
        "tags": ["생각꼬리", "인스타툰", "그림판툰"],
    },
    "thread": [
        "냉장고 문 열자마자 뭐 하러 왔는지 까먹는 거, 이유 알아낸 것 같음",
        "냉장고 불이 딸깍 켜지는 그 순간에 내 머릿속 불이 꺼짐. 둘이 같은 콘센트 쓰는 게 분명함",
        "아니면 생각이 냉기에 얼어서 툭 떨어지는 거지. 그럼 냉동실엔 지금까지 까먹은 게 다 얼어 있다는 소리임. 우산 둔 데, 그 배우 이름, 와이파이 비번, 하려던 말",
        "해동 돌리면 돌아올 줄 알았는데 너무 오래 돌려서 중학교 영어단어가 같이 녹아버림. ambitious 아직도 기억남",
        "머리가 꽉 차니까 방금 들어온 생각이 밀려나고, 밀려난 생각은 다시 냉장고로 감. 다들 냉장고 앞에서 까먹는 이유",
        "엄마한테 설명했더니 전기세나 기억하라심. 물은 못 마심",
    ],
    "thread_single": "냉장고 불이 켜지는 순간 내 머릿속 불이 꺼지는 거 보면 둘이 같은 콘센트 쓰는 게 분명함",
    # AI 이미지 생성용 설정집 — 키가 없어 생성은 못 했다. 글자는 넣지 않게 하고 이 화면에서 얹는다.
    "prompts": {
        "character": (
            "A simple doodle character: a white blob head slightly wider than tall, one curly hair strand on top, "
            "two small black dot eyes, a short straight mouth, a small white rounded-rectangle body, stick arms and legs. "
            "Thick, uneven black outline as if drawn with a computer mouse."
        ),
        "style": (
            "MS Paint doodle, mouse-drawn wobbly black lines about 6px, flat colors from the classic Paint palette, "
            "no gradients, no texture, no shadows, slightly crooked composition, plain white background, 4:5 frame."
        ),
        "negative": "no text, no letters, no speech bubbles, no realistic lighting, no 3D, no anime style, no smooth vector art, no gradient",
        "cuts": [
            "The character standing in front of a closed white refrigerator, a big question mark above the head.",
            "The refrigerator door wide open with warm light spilling out, the character staring blankly into it.",
            "Split panel: left, a refrigerator light bulb switched on with rays; right, a light bulb above the character's head switched off and grey.",
            "One power strip on the floor with two plugs: one from the refrigerator, one from a cord coming out of the back of the character's head.",
            "A thought bubble turning into an ice cube and dropping into the open refrigerator.",
            "An open freezer full of labeled ice blocks stacked on shelves (leave the labels blank).",
            "The character pressing a big button on a microwave holding an ice block inside.",
            "Microwave door bursting open, many floating word-shaped blobs pouring out, the character shocked.",
            "A circular diagram of arrows connecting a head, a refrigerator, a freezer and a microwave.",
            "The character holding the refrigerator door, a speech bubble coming in from outside the frame on the right.",
        ],
        "post": [
            "컷마다 4장씩 뽑고, 캐릭터 머리 모양·선 두께가 1번 컷과 같은 것만 남긴다",
            "글자는 생성기에 맡기지 않는다 — 이 화면의 카툰 틀 위에 손글씨체로 얹는다",
            "색은 그림판 기본 팔레트로 다시 칠하고, 그라데이션이 생기면 버린다",
            "4:5(1080×1350)로 자르고, 10장 모두 여백을 같게 맞춘다",
        ],
    },
}

WORKS = [FRIDGE]


def get(key):
    return next((w for w in WORKS if w["key"] == key), None)


def total_seconds(work):
    return round(sum(c["dur"] for c in work["cuts"]), 1)
