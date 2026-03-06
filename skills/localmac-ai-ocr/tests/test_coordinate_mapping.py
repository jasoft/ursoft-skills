from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import gui_toolkit
import ocr_tool


class CoordinateMappingTests(unittest.TestCase):
    def test_image_point_maps_to_main_display_points(self) -> None:
        with mock.patch.object(
            gui_toolkit,
            "main_display_geometry",
            return_value={
                "x": 0.0,
                "y": 0.0,
                "width_points": 2272.0,
                "height_points": 1278.0,
                "width_pixels": 4544.0,
                "height_pixels": 2556.0,
            },
        ):
            x, y = gui_toolkit.image_point_to_screen_point(996, 444, (4544, 2556))

        self.assertEqual((x, y), (498.0, 222.0))

    def test_click_match_uses_screen_points(self) -> None:
        clicked: list[tuple[float, float, int]] = []

        def fake_click(x: float, y: float, count: int = 1) -> None:
            clicked.append((x, y, count))

        with mock.patch.object(
            gui_toolkit,
            "image_point_to_screen_point",
            return_value=(498.0, 222.0),
        ):
            center = ocr_tool.click_match(
                {"bbox": [950, 420, 1042, 468]},
                (4544, 2556),
                clicker=fake_click,
                count=2,
            )

        self.assertEqual(center, (498, 222))
        self.assertEqual(clicked, [(498.0, 222.0, 2)])

    def test_image_point_maps_with_screen_rect(self) -> None:
        x, y = gui_toolkit.image_point_to_screen_point(
            250,
            125,
            (1000, 500),
            screen_rect="100,200,400,200",
        )

        self.assertEqual((x, y), (200.0, 250.0))

    def test_annotation_lines_include_center_and_score(self) -> None:
        lines = ocr_tool.annotation_lines(
            {
                "text": "自动化",
                "score": 0.9465218782,
                "bbox": [950, 420, 1042, 468],
            }
        )

        self.assertEqual(
            lines,
            [
                "自动化",
                "center=(996,444)",
                "score=0.947",
            ],
        )

    def test_annotation_lines_can_hide_fields(self) -> None:
        lines = ocr_tool.annotation_lines(
            {
                "text": "自动化",
                "score": 0.9465218782,
                "bbox": [950, 420, 1042, 468],
            },
            include_text=False,
            include_score=False,
        )

        self.assertEqual(lines, ["center=(996,444)"])

    def test_select_match_index_uses_one_based_order(self) -> None:
        matches = [{"text": "第一"}, {"text": "第二"}, {"text": "第三"}]
        picked = ocr_tool.select_match_index(matches, 2)
        self.assertEqual(picked, [{"text": "第二"}])

    def test_select_match_index_rejects_out_of_range(self) -> None:
        with self.assertRaises(SystemExit):
            ocr_tool.select_match_index([{"text": "第一"}], 2)


if __name__ == "__main__":
    unittest.main()
