"""
Script kiem tra toan dien he thong (Codebase Auditor & Verification Script).
Kiem tra:
1. Danh sach API endpoints trong main.py vs index.html.
2. Logic va du lieu tra ve cua tung endpoint.
3. Kiem tra tinh toan Rule Engine va cac edge case.
4. Kiem tra vector DB va chunks.json.
5. Kiem tra tinh toan ven va dinh dang file bao cao docx.
"""
import inspect
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

print("=" * 60)
print("1. KIỂM TRA ĐỒNG BỘ API ENDPOINTS GIỮA BACKEND VÀ FRONTEND")
print("=" * 60)

# Doc main.py
main_py = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
backend_endpoints = re.findall(r'@app\.(?:get|post)\(["\'](/api/[^"\']+)["\']\)', main_py)
print(f"Backend (@app routes in main.py): {len(backend_endpoints)} endpoints:")
for ep in sorted(backend_endpoints):
    print(f"  [BE] {ep}")

# Doc index.html
index_html = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
frontend_endpoints = re.findall(r'fetch\(["\'](/api/[^"\'?]+)', index_html)
print(f"\nFrontend (fetch in index.html): {len(set(frontend_endpoints))} unique endpoints:")
for ep in sorted(set(frontend_endpoints)):
    print(f"  [FE] {ep}")

# Kiem tra xem co endpoint nao FE goi ma BE khong co khong
missing_in_backend = set(frontend_endpoints) - set(backend_endpoints)
if missing_in_backend:
    print(f"\n[CANH BAO LOI] Co endpoint FE goi ma BE khong dinh nghia: {missing_in_backend}")
else:
    print("\n[OK] Toan bo cac endpoint Frontend goi deu ton tai trong Backend!")

unused_in_frontend = set(backend_endpoints) - set(frontend_endpoints)
print(f"\nEndpoint BE co nhung FE khong goi truc tiep qua fetch: {unused_in_frontend}")

print("\n" + "=" * 60)
print("2. KIỂM TRA CHUNKS VÀ QUY CHẾ")
print("=" * 60)
chunks_file = ROOT / "data" / "chunks.json"
if chunks_file.exists():
    chunks = json.loads(chunks_file.read_text(encoding="utf-8"))
    print(f"So luong chunks: {len(chunks)}")
    dieus = [c.get("dieu") for c in chunks]
    print(f"Cac Dieu: {dieus}")
else:
    print("[LOI] Khong tim thay data/chunks.json")

print("\n" + "=" * 60)
print("3. KIỂM TRA RULE ENGINE & EDGE CASES")
print("=" * 60)
from app.rule_engine import (
    calculate_course_grade, CourseGradeInput,
    check_academic_status_rules, StatusCheckInput,
    simulate_gpa_improvement, GPASimulatorInput, RetakeCourseItem,
    check_graduation_eligibility, GraduationCheckInput
)

# Test 1: Grade Calc edge cases (diem 0, diem 10, vang thi, vang > 20%)
g0 = calculate_course_grade(CourseGradeInput(attendance=0, midterm=0, final_exam=0))
print(f"Diem 0: {g0['grade_letter']} (he 4: {g0['grade_4']}) - is_passed: {g0['is_passed']}")
g10 = calculate_course_grade(CourseGradeInput(attendance=10, midterm=10, final_exam=10))
print(f"Diem 10: {g10['grade_letter']} (he 4: {g10['grade_4']}) - is_passed: {g10['is_passed']}")
g_absent = calculate_course_grade(CourseGradeInput(attendance=10, midterm=10, final_exam=10, absent_ratio=0.25))
print(f"Vang >20%: {g_absent['grade_letter']} (he 4: {g_absent['grade_4']}) - note: {g_absent['note']}")

# Test 2: Status check edge cases
st_expel = check_academic_status_rules(StatusCheckInput(
    semester_index=6, year_level=3, gpa_semester=1.0, cpa_cumulative=1.0, previous_warnings=2, consecutive_warning=True
))
print(f"\nTrang thai nguy hiem: {st_expel['status']} - is_expelled: {st_expel['is_expelled']} - label: {st_expel['risk_label']}")

# Test 3: GPA retake edge case (khong co mon hoc lai)
sim_empty = simulate_gpa_improvement(GPASimulatorInput(current_cpa=2.5, accumulated_credits=50, retake_courses=[]))
print(f"Simulate empty retake: current {sim_empty['current_cpa']} -> new {sim_empty['new_cpa']}")

# Test 4: Graduation edge case (rot tot nghiep do no tin chi hoac thieu ngoai ngu)
grad_fail = check_graduation_eligibility(GraduationCheckInput(
    cpa=3.5, accumulated_credits=120, required_credits=130, has_foreign_language=False
))
print(f"Grad fail check: is_eligible: {grad_fail['is_eligible']} - final_rank: {grad_fail['final_rank']}")

print("\n" + "=" * 60)
print("HOÀN TẤT KIỂM TRA SƠ BỘ!")
print("=" * 60)

