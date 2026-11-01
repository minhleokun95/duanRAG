"""
Bo kiem thu tu dong (Automated Unit & Integration Test Suite) cho He thong RAG Quy dinh hoc vu.
Chay bang lenh: python -m unittest tests/test_system.py
"""
import os
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.rule_engine import (
    CourseGradeInput,
    GPASimulatorInput,
    GraduationCheckInput,
    RetakeCourseItem,
    StatusCheckInput,
    calculate_course_grade,
    check_academic_status_rules,
    check_graduation_eligibility,
    classify_academic_standing,
    simulate_gpa_improvement,
)


class TestAcademicRuleEngine(unittest.TestCase):
    """Kiem thu toan bo cac quy tac toan hoc va nghiep vu trong app/rule_engine.py."""

    def test_calculate_course_grade_pass(self):
        """Kiem tra tinh diem tong ket hoc phan (10/30/60) - Truong hop dat."""
        inp = CourseGradeInput(attendance=8.5, midterm=7.0, final_exam=4.0)
        res = calculate_course_grade(inp)
        self.assertAlmostEqual(res["calculated_10"], 5.3, places=1)
        self.assertIn(res["grade_letter"], ["D", "D+"])
        self.assertGreaterEqual(res["grade_4"], 1.0)
        self.assertTrue(res["is_passed"])

    def test_calculate_course_grade_fail_f(self):
        """Kiem tra tinh diem tong ket - Truong hop bi diem F."""
        inp = CourseGradeInput(attendance=5.0, midterm=4.0, final_exam=2.0)
        res = calculate_course_grade(inp)
        self.assertLess(res["calculated_10"], 4.0)
        self.assertEqual(res["grade_letter"], "F")
        self.assertEqual(res["grade_4"], 0.0)
        self.assertFalse(res["is_passed"])

    def test_check_academic_status_critical_expelled(self):
        """Kiem tra canh bao hoc vu & buoc thoi hoc theo Dieu 11 Khoan 2 (GPA < 1.20 va 2 canh bao)."""
        inp = StatusCheckInput(
            semester_index=4,
            year_level=2,
            gpa_semester=1.15,
            cpa_cumulative=1.15,
            previous_warnings=2,
            consecutive_warning=True,
        )
        res = check_academic_status_rules(inp)
        self.assertEqual(res["status"], "CRITICAL")
        self.assertTrue(res["is_expelled"])
        self.assertTrue(any("Điều 11 Khoản 2" in c for c in res["regulations_cited"]))
        self.assertEqual(res["allowed_credits_next_semester"]["max"], 14)

    def test_check_academic_status_safe(self):
        """Kiem tra trang thai hoc vu an toan (GPA 3.2, 0 canh bao)."""
        inp = StatusCheckInput(
            semester_index=3,
            year_level=2,
            gpa_semester=3.2,
            cpa_cumulative=3.1,
            previous_warnings=0,
            consecutive_warning=False,
        )
        res = check_academic_status_rules(inp)
        self.assertEqual(res["status"], "SAFE")
        self.assertFalse(res["is_expelled"])
        self.assertFalse(res["is_warned"])
        self.assertEqual(res["allowed_credits_next_semester"]["max"], 25)

    def test_simulate_gpa_improvement(self):
        """Kiem tra cong thuc mo phong nang CPA khi hoc lai mon F theo Dieu 6 Khoan 2."""
        inp = GPASimulatorInput(
            current_cpa=2.2,
            accumulated_credits=60,
            retake_courses=[
                RetakeCourseItem(name="Giải tích 1", credits=3, old_grade_4=0.0, expected_grade_4=3.0)
            ],
        )
        res = simulate_gpa_improvement(inp)
        self.assertGreater(res["new_cpa"], res["current_cpa"])
        self.assertEqual(res["cpa_gain"], round(res["new_cpa"] - 2.2, 2))

    def test_graduation_check_eligible(self):
        """Kiem tra 4 dieu kien xet tot nghiep theo Dieu 12 va 13."""
        inp = GraduationCheckInput(
            cpa=3.35,
            accumulated_credits=135,
            required_credits=130,
            retake_credits=3,
            has_foreign_language=True,
            has_defense_edu=True,
            has_physical_edu=True,
            disciplinary_warning=False,
        )
        res = check_graduation_eligibility(inp)
        self.assertTrue(res["is_eligible"])
        self.assertEqual(res["final_rank"], "Giỏi")


class TestSystemCorpusAndConfig(unittest.TestCase):
    """Kiem tra tinh nhat quan cua tap du lieu chunks.json va cau hinh he thong."""

    def test_chunks_json_integrity(self):
        """Kiem tra chunks.json co day du 16 Dieu va metadata dung chuan."""
        chunks_file = ROOT / "data" / "chunks.json"
        self.assertTrue(chunks_file.exists())
        import json
        chunks = json.loads(chunks_file.read_text(encoding="utf-8"))
        self.assertEqual(len(chunks), 16)
        for c in chunks:
            self.assertIn("id", c)
            self.assertIn("chuong", c)
            self.assertIn("dieu", c)
            self.assertIn("text", c)
            self.assertLessEqual(len(c["text"]), 1500)


if __name__ == "__main__":
    unittest.main()
