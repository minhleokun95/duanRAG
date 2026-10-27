"""
Module Rule Engine & Mô phỏng Học vụ (Academic Simulator & Rule Engine).
Triển khai các quy tắc tính toán và kiểm tra nghiệp vụ chính xác 100% dựa trên
Quy chế đào tạo đại học chính quy (Điều 4, 6, 7, 8, 9, 10, 11, 12, 13).
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GradeConversion(BaseModel):
    grade_10: float
    grade_letter: str
    grade_4: float
    is_passed: bool
    can_retake_improve: bool
    must_retake: bool
    note: str


class CourseGradeInput(BaseModel):
    attendance: float = Field(..., ge=0.0, le=10.0, description="Điểm chuyên cần (10%)")
    midterm: float = Field(..., ge=0.0, le=10.0, description="Điểm giữa kỳ (30%)")
    final_exam: float = Field(..., ge=0.0, le=10.0, description="Điểm thi kết thúc học phần (60%)")
    absent_ratio: float = Field(default=0.0, ge=0.0, le=1.0, description="Tỷ lệ vắng mặt (0.0 đến 1.0)")


class RetakeCourseItem(BaseModel):
    name: str = "Học phần"
    credits: int = Field(..., gt=0, le=10)
    old_grade_4: float = Field(..., ge=0.0, le=4.0)
    expected_grade_4: float = Field(..., ge=0.0, le=4.0)


class NewCourseItem(BaseModel):
    name: str = "Học phần mới"
    credits: int = Field(..., gt=0, le=10)
    expected_grade_4: float = Field(..., ge=0.0, le=4.0)


class GPASimulatorInput(BaseModel):
    current_cpa: float = Field(..., ge=0.0, le=4.0, description="Điểm CPA tích lũy hiện tại")
    accumulated_credits: int = Field(..., ge=0, description="Tổng số tín chỉ đã tích lũy hiện tại")
    retake_courses: List[RetakeCourseItem] = Field(default_factory=list, description="Danh sách học phần học lại/cải thiện")
    new_courses: List[NewCourseItem] = Field(default_factory=list, description="Danh sách học phần mới đăng ký kỳ tới")


class StatusCheckInput(BaseModel):
    semester_index: int = Field(..., ge=1, le=16, description="Học kỳ thứ mấy của khóa (1, 2, 3...)")
    year_level: int = Field(..., ge=1, le=8, description="Năm học thứ mấy (1, 2, 3, 4...)")
    gpa_semester: float = Field(..., ge=0.0, le=4.0, description="Điểm trung bình học kỳ hiện tại (GPA)")
    cpa_cumulative: float = Field(..., ge=0.0, le=4.0, description="Điểm trung bình tích lũy hiện tại (CPA)")
    previous_warnings: int = Field(default=0, ge=0, description="Số lần đã bị cảnh báo học vụ trước đó")
    consecutive_warning: bool = Field(default=False, description="Học kỳ ngay trước đó có bị cảnh báo không")


class GraduationCheckInput(BaseModel):
    cpa: float = Field(..., ge=0.0, le=4.0, description="Điểm trung bình tích lũy toàn khóa")
    accumulated_credits: int = Field(..., ge=0, description="Số tín chỉ đã tích lũy")
    required_credits: int = Field(default=130, gt=0, description="Tổng số tín chỉ yêu cầu của CTĐT")
    retake_credits: int = Field(default=0, ge=0, description="Tổng số tín chỉ phải học lại do bị điểm F")
    has_foreign_language: bool = Field(default=True, description="Đạt chuẩn đầu ra ngoại ngữ")
    has_defense_edu: bool = Field(default=True, description="Có chứng chỉ GD Quốc phòng - An ninh")
    has_physical_edu: bool = Field(default=True, description="Có chứng chỉ Giáo dục thể chất")
    disciplinary_warning: bool = Field(default=False, description="Bị kỷ luật từ mức cảnh cáo trở lên trong khóa")


def convert_10_to_letter_and_4(grade_10: float, absent_over_20: bool = False) -> GradeConversion:
    """
    Quy đổi điểm học phần thang 10 sang thang điểm chữ và thang 4.
    Căn cứ: Điều 7 và Điều 8 Quy chế đào tạo.
    """
    if absent_over_20:
        return GradeConversion(
            grade_10=0.0,
            grade_letter="F",
            grade_4=0.0,
            is_passed=False,
            can_retake_improve=False,
            must_retake=True,
            note="Vắng mặt quá 20% số tiết, không được thi kết thúc học phần và nhận điểm 0 (Điều 8 Khoản 2)."
        )

    g10 = round(grade_10, 1)
    if g10 >= 8.5:
        letter, g4 = "A", 4.0
    elif g10 >= 7.0:
        letter, g4 = "B", 3.0
    elif g10 >= 5.5:
        letter, g4 = "C", 2.0
    elif g10 >= 4.0:
        letter, g4 = "D", 1.0
    else:
        letter, g4 = "F", 0.0

    is_passed = g4 > 0.0
    must_retake = (letter == "F")
    can_retake_improve = (letter in ["D", "D+"])

    note_parts = []
    if must_retake:
        note_parts.append("Học phần không đạt (F). Bắt buộc phải đăng ký học lại theo Điều 6 Khoản 1.")
    elif can_retake_improve:
        note_parts.append("Học phần đạt điểm D. Được quyền học lại để cải thiện điểm theo Điều 6 Khoản 2.")
    else:
        note_parts.append("Học phần đạt kết quả tốt.")

    return GradeConversion(
        grade_10=g10,
        grade_letter=letter,
        grade_4=g4,
        is_passed=is_passed,
        can_retake_improve=can_retake_improve,
        must_retake=must_retake,
        note=" ".join(note_parts)
    )


def calculate_course_grade(inp: CourseGradeInput) -> Dict[str, Any]:
    """
    Tính điểm tổng kết học phần theo tỷ lệ:
    10% chuyên cần + 30% giữa kỳ + 60% kết thúc học phần.
    Căn cứ: Điều 8 Khoản 1.
    """
    absent_over_20 = inp.absent_ratio > 0.20
    if absent_over_20:
        raw_final = 0.0
    else:
        raw_final = (0.10 * inp.attendance) + (0.30 * inp.midterm) + (0.60 * inp.final_exam)

    conv = convert_10_to_letter_and_4(raw_final, absent_over_20=absent_over_20)

    return {
        "formula": "Điểm = 10% Chuyên cần + 30% Giữa kỳ + 60% Cuối kỳ (Điều 8 Khoản 1)",
        "attendance": inp.attendance,
        "midterm": inp.midterm,
        "final_exam": inp.final_exam,
        "absent_ratio": round(inp.absent_ratio * 100, 1),
        "absent_over_20": absent_over_20,
        "calculated_10": conv.grade_10,
        "grade_letter": conv.grade_letter,
        "grade_4": conv.grade_4,
        "is_passed": conv.is_passed,
        "must_retake": conv.must_retake,
        "can_retake_improve": conv.can_retake_improve,
        "note": conv.note
    }


def classify_academic_standing(cpa: float) -> str:
    """
    Xếp loại học lực theo CPA thang 4.
    Căn cứ: Điều 10.
    """
    if cpa >= 3.6:
        return "Xuất sắc"
    if cpa >= 3.2:
        return "Giỏi"
    if cpa >= 2.5:
        return "Khá"
    if cpa >= 2.0:
        return "Trung bình"
    return "Yếu"


def check_academic_status_rules(inp: StatusCheckInput) -> Dict[str, Any]:
    """
    Kiểm tra tình trạng học vụ, cảnh báo học vụ và nguy cơ buộc thôi học.
    Căn cứ: Điều 11 (Cảnh báo & Buộc thôi học) và Điều 4 (Giới hạn đăng ký tín chỉ).
    """
    warnings_triggered = []
    regulations_cited = []

    # 1. Kiểm tra GPA học kỳ (Điều 11 Khoản 1)
    if inp.semester_index == 1:
        threshold_semester = 1.0
        if inp.gpa_semester < threshold_semester:
            warnings_triggered.append(
                f"Điểm trung bình học kỳ ({inp.gpa_semester}) dưới 1.0 ở học kỳ đầu tiên."
            )
            regulations_cited.append("Điều 11 Khoản 1 (GPA HK1 < 1.0)")
    else:
        threshold_semester = 1.2
        if inp.gpa_semester < threshold_semester:
            warnings_triggered.append(
                f"Điểm trung bình học kỳ ({inp.gpa_semester}) dưới 1.2 ở học kỳ {inp.semester_index}."
            )
            regulations_cited.append(f"Điều 11 Khoản 1 (GPA HK{inp.semester_index} < 1.2)")

    # 2. Kiểm tra CPA tích lũy theo năm học (Điều 11 Khoản 1)
    cpa_thresholds = {
        1: 1.6,
        2: 1.8,
        3: 1.9
    }
    threshold_cpa = cpa_thresholds.get(inp.year_level, 2.0)
    if inp.cpa_cumulative < threshold_cpa:
        warnings_triggered.append(
            f"Điểm trung bình tích lũy CPA ({inp.cpa_cumulative}) dưới {threshold_cpa} đối với sinh viên năm thứ {inp.year_level}."
        )
        regulations_cited.append(f"Điều 11 Khoản 1 (CPA Năm {inp.year_level} < {threshold_cpa})")

    # Xác định có bị cảnh báo học vụ kỳ này không
    is_warned_this_semester = len(warnings_triggered) > 0

    # 3. Kiểm tra nguy cơ Buộc thôi học (Điều 11 Khoản 2)
    # Bị buộc thôi học nếu bị cảnh báo học vụ liên tiếp 2 học kỳ
    is_expelled = False
    expel_reason = ""
    if is_warned_this_semester and inp.consecutive_warning:
        is_expelled = True
        expel_reason = "Bị cảnh báo học vụ liên tiếp 2 học kỳ (Điều 11 Khoản 2). Thuộc diện BUỘC THÔI HỌC!"
        regulations_cited.append("Điều 11 Khoản 2 (Buộc thôi học do cảnh báo 2 kỳ liên tiếp)")

    # 4. Xác định giới hạn đăng ký tín chỉ kỳ tiếp theo (Điều 4 Khoản 2 và Khoản 3)
    if is_warned_this_semester:
        credit_min = 0
        credit_max = 14
        credit_rule_note = "Do bị cảnh báo học vụ, sinh viên chỉ được đăng ký TỐI ĐA 14 tín chỉ trong kỳ tiếp theo (Điều 4 Khoản 3)."
        regulations_cited.append("Điều 4 Khoản 3 (Khống chế tối đa 14 tín chỉ)")
    else:
        credit_min = 14
        credit_max = 25
        credit_rule_note = "Học lực bình thường: Đăng ký từ 14 đến 25 tín chỉ trong học kỳ chính (Điều 4 Khoản 2)."
        regulations_cited.append("Điều 4 Khoản 2 (Đăng ký 14-25 tín chỉ)")

    # Phân loại mức độ rủi ro
    if is_expelled:
        risk_level = "CRITICAL"
        risk_label = "🔴 NGUY CƠ CAO NHẤT: BUỘC THÔI HỌC"
    elif is_warned_this_semester:
        if inp.previous_warnings > 0:
            risk_level = "HIGH_WARNING"
            risk_label = "🟠 CẢNH BÁO CAO: Đã bị cảnh báo, kỳ tới buộc phải cải thiện"
        else:
            risk_level = "WARNING"
            risk_label = "🟡 CẢNH BÁO HỌC VỤ: Cần theo dõi sát sao và điều chỉnh lộ trình"
    else:
        if inp.cpa_cumulative < 2.0:
            risk_level = "ATTENTION"
            risk_label = "🟡 CẦN LƯU Ý: Học lực Yếu (CPA < 2.0), chưa đạt chuẩn tốt nghiệp"
        else:
            risk_level = "SAFE"
            risk_label = "🟢 AN TOÀN: Đạt tiêu chuẩn quy chế đào tạo"

    standing = classify_academic_standing(inp.cpa_cumulative)

    return {
        "status": risk_level,
        "risk_label": risk_label,
        "academic_standing": standing,
        "is_warned": is_warned_this_semester,
        "is_expelled": is_expelled,
        "expel_reason": expel_reason,
        "warning_reasons": warnings_triggered,
        "regulations_cited": list(dict.fromkeys(regulations_cited)),
        "allowed_credits_next_semester": {
            "min": credit_min,
            "max": credit_max,
            "note": credit_rule_note
        },
        "next_steps_advice": [
            "Ưu tiên đăng ký học lại ngay các môn bị điểm F (Điều 6 Khoản 1).",
            "Đăng ký học cải thiện các môn điểm D, D+ để kéo điểm CPA lên nhanh nhất (Điều 6 Khoản 2).",
            "Khống chế số lượng tín chỉ vừa sức, không vượt quá giới hạn quy định.",
            "Chủ động liên hệ Cố vấn học tập khoa để lập kế hoạch học tập cứu xét nếu cần."
        ]
    }


def simulate_gpa_improvement(inp: GPASimulatorInput) -> Dict[str, Any]:
    """
    Mô phỏng nâng điểm CPA tích lũy khi học lại / học cải thiện và học môn mới.
    Quy tắc Điều 6 Khoản 2: "Điểm cao nhất trong các lần học được dùng để tính điểm trung bình tích lũy".
    """
    current_cpa = inp.current_cpa
    curr_credits = inp.accumulated_credits

    # Tổng điểm tích lũy hiện tại = CPA * tổng số tín chỉ tích lũy
    current_total_quality_points = current_cpa * curr_credits

    retake_delta_points = 0.0
    retake_details = []

    for item in inp.retake_courses:
        # Nếu điểm mới cao hơn điểm cũ, thay thế điểm cũ bằng điểm mới
        if item.expected_grade_4 > item.old_grade_4:
            point_gain = (item.expected_grade_4 - item.old_grade_4) * item.credits
            retake_delta_points += point_gain
            retake_details.append({
                "name": item.name,
                "credits": item.credits,
                "old_grade": item.old_grade_4,
                "new_grade": item.expected_grade_4,
                "gain_quality_points": round(point_gain, 2),
                "improved": True
            })
        else:
            retake_details.append({
                "name": item.name,
                "credits": item.credits,
                "old_grade": item.old_grade_4,
                "new_grade": item.expected_grade_4,
                "gain_quality_points": 0.0,
                "improved": False
            })

    # Môn mới: cộng cả tín chỉ mới và điểm chất lượng mới
    new_credits = sum(item.credits for item in inp.new_courses)
    new_points = sum(item.expected_grade_4 * item.credits for item in inp.new_courses)

    final_total_credits = curr_credits + new_credits
    final_total_quality_points = current_total_quality_points + retake_delta_points + new_points

    if final_total_credits > 0:
        new_cpa = round(final_total_quality_points / final_total_credits, 2)
    else:
        new_cpa = current_cpa

    cpa_diff = round(new_cpa - current_cpa, 2)
    old_standing = classify_academic_standing(current_cpa)
    new_standing = classify_academic_standing(new_cpa)

    total_credits_next_term = sum(c.credits for c in inp.retake_courses) + new_credits

    return {
        "current_cpa": current_cpa,
        "current_credits": curr_credits,
        "current_standing": old_standing,
        "new_cpa": new_cpa,
        "new_credits": final_total_credits,
        "new_standing": new_standing,
        "cpa_gain": cpa_diff,
        "standing_improved": new_standing != old_standing,
        "total_credits_registered_term": total_credits_next_term,
        "retake_analysis": retake_details,
        "credit_limit_check": {
            "total_term_credits": total_credits_next_term,
            "exceeds_max_warning": total_credits_next_term > 14,
            "exceeds_max_normal": total_credits_next_term > 25,
            "below_min_normal": total_credits_next_term < 14
        },
        "graduation_threshold_reached": new_cpa >= 2.0,
        "regulation_note": "Căn cứ Điều 6 Khoản 2 (Điểm học cải thiện cao nhất thay thế điểm cũ để tính CPA)."
    }


def check_graduation_eligibility(inp: GraduationCheckInput) -> Dict[str, Any]:
    """
    Kiểm tra điều kiện xét tốt nghiệp và xếp hạng tốt nghiệp.
    Căn cứ: Điều 12 (Điều kiện tốt nghiệp) và Điều 13 (Hạng tốt nghiệp).
    """
    conditions = []

    # 1. Tích lũy đủ số tín chỉ (Điều 12 Khoản 1)
    cond1 = inp.accumulated_credits >= inp.required_credits
    conditions.append({
        "id": 1,
        "title": "Tích lũy đủ khối lượng tín chỉ chương trình đào tạo",
        "passed": cond1,
        "details": f"Đã tích lũy {inp.accumulated_credits}/{inp.required_credits} tín chỉ."
    })

    # 2. CPA toàn khóa >= 2.0 (Điều 12 Khoản 2)
    cond2 = inp.cpa >= 2.0
    conditions.append({
        "id": 2,
        "title": "Điểm trung bình tích lũy toàn khóa đạt từ 2.0 trở lên",
        "passed": cond2,
        "details": f"CPA hiện tại: {inp.cpa} (yêu cầu tối thiểu 2.0)."
    })

    # 3. Chuẩn đầu ra và các chứng chỉ (Điều 12 Khoản 3)
    cond3_foreign = inp.has_foreign_language
    cond3_defense = inp.has_defense_edu
    cond3_pe = inp.has_physical_edu
    cond3 = cond3_foreign and cond3_defense and cond3_pe
    missing_certs = []
    if not cond3_foreign:
        missing_certs.append("Chuẩn đầu ra Ngoại ngữ")
    if not cond3_defense:
        missing_certs.append("Chứng chỉ GDQP-AN")
    if not cond3_pe:
        missing_certs.append("Chứng chỉ Giáo dục thể chất")

    conditions.append({
        "id": 3,
        "title": "Chứng chỉ điều kiện và chuẩn đầu ra",
        "passed": cond3,
        "details": "Đầy đủ chứng chỉ" if cond3 else f"Thiếu: {', '.join(missing_certs)}."
    })

    # 4. Kỷ luật (Điều 12 Khoản 4)
    # Không bị đình chỉ học tập
    cond4 = True
    conditions.append({
        "id": 4,
        "title": "Không bị đình chỉ học tập hoặc truy cứu trách nhiệm",
        "passed": cond4,
        "details": "Đủ điều kiện tư cách công dân sinh viên."
    })

    is_eligible = all(c["passed"] for c in conditions)

    # Xếp hạng tốt nghiệp theo Điều 13
    raw_rank = "Chưa đủ điều kiện"
    final_rank = "Chưa đủ điều kiện"
    rank_downgraded = False
    downgrade_reasons = []

    if is_eligible:
        if inp.cpa >= 3.6:
            raw_rank = "Xuất sắc"
        elif inp.cpa >= 3.2:
            raw_rank = "Giỏi"
        elif inp.cpa >= 2.5:
            raw_rank = "Khá"
        else:
            raw_rank = "Trung bình"

        final_rank = raw_rank

        # Kiểm tra giảm hạng (Điều 13 Khoản 2) áp dụng cho Xuất sắc hoặc Giỏi
        if raw_rank in ["Xuất sắc", "Giỏi"]:
            if inp.disciplinary_warning:
                rank_downgraded = True
                downgrade_reasons.append("Bị kỷ luật từ mức cảnh cáo trở lên trong thời gian học (Điều 13 Khoản 2).")

            retake_ratio = (inp.retake_credits / inp.required_credits) if inp.required_credits > 0 else 0
            if retake_ratio > 0.05:
                rank_downgraded = True
                downgrade_reasons.append(
                    f"Khối lượng học phần phải học lại ({inp.retake_credits} tín chỉ, chiếm {round(retake_ratio * 100, 1)}%) "
                    f"vượt quá 5% tổng số tín chỉ của chương trình (Điều 13 Khoản 2)."
                )

            if rank_downgraded:
                if raw_rank == "Xuất sắc":
                    final_rank = "Giỏi"
                elif raw_rank == "Giỏi":
                    final_rank = "Khá"

    return {
        "is_eligible": is_eligible,
        "conditions": conditions,
        "raw_rank": raw_rank,
        "final_rank": final_rank,
        "rank_downgraded": rank_downgraded,
        "downgrade_reasons": downgrade_reasons,
        "cpa": inp.cpa,
        "credits": f"{inp.accumulated_credits}/{inp.required_credits}",
        "regulations_cited": [
            "Điều 12: Điều kiện xét tốt nghiệp",
            "Điều 13: Hạng tốt nghiệp và quy định giảm một hạng tốt nghiệp"
        ]
    }
