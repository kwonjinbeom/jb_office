import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from apps.routines import overlap

DRAFT = """# [원고] {code} · {title}
사이트: black_lukey
<!-- 본문 시작 -->
# {title}
본문
<!-- 본문 끝 -->
"""

PLAN = """# 주제 기획 · 2026-10-31

## 쓸 글 (2편)
### T210 · black_lukey > 축제·행사 · 계산
- 대상: 지스타 · 벡스코
- 반복 점검: {note}

### T211 · black_lukey > 지역 놀거리 · 코스
- 대상: 파주
- 반복 점검: 없음

### T212 · 밤밤 > 나스닥 시황 노트 · 시황 노트
- 대상: 없음 (시황 노트)

## 오늘 배운 것
- 대상: 지스타
"""


class OverlapTests(SimpleTestCase):
    """2026-10-31 사용자: T210 지스타가 T114(8일 전)와 겹쳤는데 기획·작가 모두 '없음'이라 적었다 → 기계로 막는다."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "원고"
        self._draft("T114_지스타2026", "T114", "지스타 2026 언제 가야 덜 붐빌까", days=8)
        self._draft("T50_지스타2025", "T50", "지스타 2025 정리", days=40)
        self._draft("T209_파주당일치기", "T209", "파주 당일치기", days=0)
        self._draft("T210_지스타2026", "T210", "지스타 2026 입장권", days=0)  # 기획표 자신은 뺀다
        self.plans = Path(tmp.name) / "주제기획"
        self.plans.mkdir()

    def _draft(self, key, code, title, days):
        folder = self.root / key
        folder.mkdir(parents=True)
        f = folder / "원고.md"
        f.write_text(DRAFT.format(code=code, title=title), encoding="utf-8")
        stamp = (datetime(2026, 10, 31, 12) - timedelta(days=days)).timestamp()
        os.utime(f, (stamp, stamp))

    def _plan(self, note="없음"):
        path = self.plans / "2026-10-31.md"
        path.write_text(PLAN.format(note=note), encoding="utf-8")
        return path

    def test_recent_same_target_is_blocked(self):
        slots = overlap.check_plan(self._plan(), self.root)
        gstar, paju, nasdaq = slots
        self.assertFalse(nasdaq.blocked)  # 날마다 쓰는 소재는 건너뛴다
        self.assertEqual(gstar.words, ["지스타", "벡스코"])
        self.assertEqual([(h.code, h.days) for h in gstar.hits], [("T114", 8), ("T50", 40)])
        self.assertTrue(gstar.blocked)
        self.assertEqual([h.code for h in paju.hits], ["T209"])  # 같은 날이라도 이 기획표 밖의 원고면 겹침
        text = "\n".join(overlap.report(slots))
        self.assertIn("겹침 — 21일 안", text)
        self.assertIn("T114 (2026-10-23, 8일 전)", text)
        self.assertIn("참고 (40일 전) T50", text)

    def test_noted_change_is_exception(self):
        gstar = overlap.check_plan(self._plan(note="T114 와 달리 입장권 요금 변경"), self.root)[0]
        self.assertFalse(gstar.blocked)
        self.assertIn("예외", overlap.report([gstar])[0])

    def test_missing_target_line_blocks(self):
        path = self._plan()
        path.write_text(path.read_text(encoding="utf-8").replace("- 대상: 파주\n", ""), encoding="utf-8")
        paju = overlap.check_plan(path, self.root)[1]
        self.assertTrue(paju.blocked)
        self.assertIn("대상 줄 없음", overlap.report([paju])[0])

    def test_command_fails_on_overlap(self):
        self._plan()
        with override_settings(WRITING_DRAFTS_DIR=self.root):
            with self.assertRaisesMessage(CommandError, "T210"):
                call_command("check_overlap", "2026-10-31", stdout=open(os.devnull, "w", encoding="utf-8"))
