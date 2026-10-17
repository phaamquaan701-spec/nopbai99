# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from datetime import datetime
from app.config import DEFAULT_TIMEZONE
from app.database import init_db, get_db
from app.security import hash_password

STUDENTS_11A1 = [('hs01_an', 'Phạm Quốc An'), ('hs02_anh', 'Hoàng Tuấn Anh'), ('hs03_bach', 'Trần Hải Bách'), ('hs04_chi', 'Dương Yến Chi'), ('hs05_chinh', 'Trương Hồng Chinh'), ('hs06_chinh', 'Trương Thụy Minh Chính'), ('hs07_dang', 'Phạm Hải Đăng'), ('hs08_dung', 'Hoàng Văn Dũng'), ('hs09_dung', 'Phạm Quang Dũng'), ('hs10_duong', 'Vũ Thùy Dương'), ('hs11_duong', 'Bàng Thái Dương'), ('hs12_duong', 'Phạm Thành Dương'), ('hs13_giang', 'Nguyễn Thu Giang'), ('hs14_ha', 'Cao Nguyễn Khánh Hà'), ('hs15_hang', 'Nguyễn Minh Hằng'), ('hs16_hung', 'Bùi Tuấn Hùng'), ('hs17_khai', 'Phạm Quang Khải'), ('hs18_khanh', 'Nguyễn Nam Khánh'), ('hs19_khanh', 'Nguyễn Gia Khánh'), ('hs20_lam', 'Nguyễn Đức Lâm'), ('hs21_linh', 'Ngô Nguyễn Hà Linh'), ('hs22_long', 'Bùi Vũ Hoàng Long'), ('hs23_long', 'Phạm Đào Phúc Long'), ('hs24_man', 'Phạm Gia Mẫn'), ('hs25_minh', 'Bùi Tiến Minh'), ('hs26_minh', 'Nguyễn Ngọc Khánh Minh'), ('hs27_minh', 'Lại Thái Minh'), ('hs28_minh', 'Trịnh Vũ Minh'), ('hs29_ngan', 'Lê Hoàng Bảo Ngân'), ('hs30_ngoc', 'Ngô Trần Bảo Ngọc'), ('hs31_nguyen', 'Trần Xuân Nguyên'), ('hs32_ninh', 'Nguyễn Anh Ninh'), ('hs33_phong', 'Lê Nam Phong'), ('hs34_phong', 'Phạm Hải Phong'), ('hs35_phong', 'Lưu Quang Nam Phong'), ('hs36_phuong', 'Trần Thị Hà Phương'), ('hs37_quan', 'Phạm Anh Quân'), ('hs38_tai', 'Nguyễn Đình Tài'), ('hs39_thanh', 'Bùi Hữu Thành'), ('hs40_thien', 'Nguyễn Ngọc Thiện'), ('hs41_thu', 'Tô Nguyễn Minh Thư'), ('hs42_tung', 'Phạm Việt Tùng'), ('hs43_tung', 'Đặng Hoàng Tùng'), ('hs44_vy', 'Phạm Hà Vy')]
STUDENTS_11A4 = [('anh_dd_11a4', 'Đồng Duy Anh'), ('anh_ltn_11a4', 'Lương Thị Ngọc Ánh'), ('anh_np_11a4', 'Nguyễn Phương Anh'), ('anh_vd_11a4', 'Vũ Duy Anh'), ('bao_ln_11a4', 'Lại Ngọc Bảo'), ('binh_vq_11a4', 'Vũ Quang Bình'), ('chi_ptt_11a4', 'Phạm Thị Thùy Chi'), ('cuc_nt_11a4', 'Nguyễn Thu Cúc'), ('dung_bt_11a4', 'Bùi Trung Dũng'), ('dung_nq_11a4', 'Nguyễn Quang Dũng'), ('dung_nt_11a4', 'Nguyễn Tiến Dũng'), ('duc_la_11a4', 'Lê Anh Đức'), ('ha_nt_11a4', 'Nguyễn Thanh Hà'), ('hai_nh_11a4', 'Nguyễn Hoàng Hải'), ('hai_th_11a4', 'Trần Hoàng Hải'), ('hien_ct_11a4', 'Chu Thúy Hiền'), ('hien_nv_11a4', 'Nguyễn Vinh Hiển'), ('hieu_tm_11a4', 'Trương Minh Hiếu'), ('hieu_vt_11a4', 'Vũ Trung Hiêu'), ('phuong_dm_11a4', 'Đỗ Mai Phương'), ('huyen_nh_11a4', 'Ngô Hương Huyền'), ('hung_nd_11a4', 'Nguyễn Đình Hưng'), ('khanh_nq_11a4', 'Nguyễn Quốc Khánh'), ('lam_ntt_11a4', 'Nguyễn Trần Thảo Lâm'), ('linh_pp_11a4', 'Phạm Phương Linh'), ('loc_pt_11a4', 'Phạm Trần Lộc'), ('luan_nt_11a4', 'Nguyễn Thành Luân'), ('minh_nc_11a4', 'Nguyễn Công Minh'), ('my_ttt_11a4', 'Trần Thị Trà My'), ('anh_nh_11a4', 'Nguyễn Hồng Anh'), ('nam_lpb_11a4', 'Lục Phạm Bảo Nam'), ('phuong_nl_11a4', 'Ngô Lam Phương'), ('quy_vx_11a4', 'Vũ Xuân Quý'), ('son_ch_11a4', 'Chu Hải Sơn'), ('tam_nng_11a4', 'Nguyễn Ngọc Giai Tâm'), ('thanh_bn_11a4', 'Bùi Nam Thanh'), ('thanh_lvd_11a4', 'Lưu Vương Đức Thành'), ('thong_pb_11a4', 'Phạm Bá Thông'), ('thuan_nm_11a4', 'Nguyễn Minh Thuận'), ('trang_tt_11a4', 'Trần Thị Trang'), ('tu_nt_11a4', 'Nguyễn Tuấn Tú'), ('vuong_vh_11a4', 'Vũ Hùng Vương'), ('xuan_dt_11a4', 'Đào Thị Xuân')]
STUDENTS_11A5 = [('tung_pq_11a5', 'Phùng Quang Tùng'), ('trang_pt_11a5', 'Phạm Thùy Trang'), ('vy_th_11a5', 'Tô Hạ Vy'), ('tu_nt_11a5', 'Ngô Tuấn Tú'), ('truc_lh_11a5', 'Lê Hải Trúc'), ('tung_nps_11a5', 'Nguyễn Phạm Sơn Tùng'), ('tung_tm_11a5', 'Trần Mạnh Tùng'), ('thu_va_11a5', 'Vũ Anh Thư'), ('thy_nk_11a5', 'Nguyễn Ka Thy'), ('thu_dh_11a5', 'Đặng Hoài Thu'), ('bao_vg_11a5', 'Vũ Gia Bảo'), ('nam_nb_11a5', 'Nguyễn Bảo Nam'), ('quynh_tt_11a5', 'Trương Tú Quỳnh'), ('linh_nh_11a5', 'Nguyễn Hà Linh'), ('son_lxt_11a5', 'Lê Xuân Thiên Sơn'), ('phong_db_11a5', 'Đặng Bá Phong'), ('ha_nn_11a5', 'Nguyễn Ngọc Hà'), ('linh_nt_11a5', 'Nguyễn Thùy Linh'), ('thai_lq_11a5', 'Lương Quốc Thái'), ('hieu_mt_11a5', 'Mai Trung Hiếu'), ('ly_dc_11a5', 'Đào Cẩm Ly'), ('ngoc_th_11a5', 'Trần Hoài Ngọc'), ('huy_vg_11a5', 'Vũ Gia Huy'), ('nam_nh_11a5', 'Nhữ Hải Nam'), ('bang_nl_11a5', 'Nguyễn Lương Bằng'), ('minh_vd_11a5', 'Vương Đức Minh'), ('minh_nq_11a5', 'Nguyễn Quang Minh'), ('kien_dt_11a5', 'Đặng Trung Kiên'), ('co_pd_11a5', 'Phạm Đức Cơ'), ('minh_bn_11a5', 'Bùi Nhật Minh'), ('linh_nh2_11a5', 'Nguyễn Hà Linh'), ('dai_bs_11a5', 'Bùi Sĩ Đại'), ('hue_pt_11a5', 'Phạm Thu Huệ'), ('thao_lt_11a5', 'Lê Thanh Thảo'), ('anh_pt_11a5', 'Phạm Thế Anh'), ('duc_pa_11a5', 'Phạm Anh Đức'), ('anh_np_11a5', 'Nguyễn Phương Anh'), ('anh_nd_11a5', 'Nguyễn Duy Anh'), ('anh_nm_11a5', 'Nguyễn Minh Anh'), ('huy_ng_11a5', 'Nguyễn Gia Huy'), ('cuong_hm_11a5', 'Hoàng Mạnh Cường'), ('du_vh_11a5', 'Vũ Hữu Du'), ('ha_vt_11a5', 'Vũ Thanh Hà'), ('ha_dtn_11a5', 'Đặng Thị Ngọc Hà'), ('anh_vp_11a5', 'Vũ Phương Anh')]
EXISTING_ASSIGNMENTS = [{'id': 18, 'title': 'Bài tập Vật lí 12 – Khí lí tưởng & Định luật chất khí', 'description': 'Học sinh làm bài ra giấy, chụp ảnh rõ nét và nộp trước deadline.', 'subject': 'Vật lí', 'class_id': 4, 'created_by': 1, 'start_at': '2026-09-19T10:27:28.888377+07:00', 'deadline': '2026-09-25T23:59:00.888377+07:00', 'allow_resubmit': 1, 'allow_late_submission': 1, 'resubmit_after_deadline': 1, 'submission_grace_period': 300, 'max_images': 10, 'max_file_size': 10485760, 'status': 'open', 'created_at': '2026-09-20T10:27:28.888377+07:00', 'updated_at': '2026-09-20T10:27:28.888377+07:00'}, {'id': 19, 'title': 'Bài tập Tiếng Anh – IELTS Reading & Academic Writing', 'description': 'Học sinh làm bài ra giấy, chụp ảnh rõ nét và nộp trước deadline.', 'subject': 'Tiếng Anh', 'class_id': 4, 'created_by': 1, 'start_at': '2026-09-19T10:27:28.888377+07:00', 'deadline': '2026-09-24T23:59:00.888377+07:00', 'allow_resubmit': 1, 'allow_late_submission': 1, 'resubmit_after_deadline': 1, 'submission_grace_period': 300, 'max_images': 10, 'max_file_size': 10485760, 'status': 'open', 'created_at': '2026-09-20T10:27:28.888377+07:00', 'updated_at': '2026-09-20T10:27:28.888377+07:00'}, {'id': 20, 'title': 'Bài tập Vật lí 12 – Cảm ứng điện từ & Suất điện động Faraday', 'description': 'Học sinh làm bài ra giấy, chụp ảnh rõ nét và nộp trước deadline.', 'subject': 'Vật lí', 'class_id': 4, 'created_by': 1, 'start_at': '2026-09-19T10:27:28.888377+07:00', 'deadline': '2026-09-26T23:59:00.888377+07:00', 'allow_resubmit': 1, 'allow_late_submission': 1, 'resubmit_after_deadline': 1, 'submission_grace_period': 300, 'max_images': 10, 'max_file_size': 10485760, 'status': 'open', 'created_at': '2026-09-20T10:27:28.888377+07:00', 'updated_at': '2026-09-20T10:27:28.888377+07:00'}]

def seed():
    init_db()
    now = datetime.now(DEFAULT_TIMEZONE).isoformat()

    with get_db() as conn:
        cursor = conn.cursor()

        # 1. T?i kho?n Qu?n tr? vi?n (Admin)
        admins = [
            ("admin", hash_password("admin123"), "Gi?o vi?n Qu?n tr?"),
            ("Cuong", hash_password("mybeovl"), "L?n My"),
            ("cuong", hash_password("mybeovl"), "L?n My")
        ]
        for u, p_hash, name in admins:
            cursor.execute("SELECT id FROM users WHERE username = ?", (u,))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO users (username, password_hash, full_name, role, class_id, status, created_at)
                    VALUES (?, ?, ?, 'admin', NULL, 'active', ?)
                    """,
                    (u, p_hash, name, now)
                )

        # 2. L?p 11A1
        cursor.execute("SELECT id FROM classes WHERE name = '11A1'")
        row_11a1 = cursor.fetchone()
        if not row_11a1:
            cursor.execute("INSERT INTO classes (name, created_at) VALUES ('11A1', ?)", (now,))
            id_11a1 = cursor.lastrowid
        else:
            id_11a1 = row_11a1["id"]

        pwd_student_hash = hash_password("123456")
        for username, full_name in STUDENTS_11A1:
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO users (username, password_hash, full_name, role, class_id, status, created_at)
                    VALUES (?, ?, ?, 'student', ?, 'active', ?)
                    """,
                    (username, pwd_student_hash, full_name, id_11a1, now)
                )

        # 3. L?p 11A4
        cursor.execute("SELECT id FROM classes WHERE name = '11A4'")
        row_11a4 = cursor.fetchone()
        if not row_11a4:
            cursor.execute("INSERT INTO classes (name, created_at) VALUES ('11A4', ?)", (now,))
            id_11a4 = cursor.lastrowid
        else:
            id_11a4 = row_11a4["id"]

        for username, full_name in STUDENTS_11A4:
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO users (username, password_hash, full_name, role, class_id, status, created_at)
                    VALUES (?, ?, ?, 'student', ?, 'active', ?)
                    """,
                    (username, pwd_student_hash, full_name, id_11a4, now)
                )

        # 4. Lớp 11A5
        cursor.execute("SELECT id FROM classes WHERE name = '11A5'")
        row_11a5 = cursor.fetchone()
        if not row_11a5:
            cursor.execute("INSERT INTO classes (name, created_at) VALUES ('11A5', ?)", (now,))
            id_11a5 = cursor.lastrowid
        else:
            id_11a5 = row_11a5["id"]

        for username, full_name in STUDENTS_11A5:
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO users (username, password_hash, full_name, role, class_id, status, created_at)
                    VALUES (?, ?, ?, 'student', ?, 'active', ?)
                    """,
                    (username, pwd_student_hash, full_name, id_11a5, now)
                )

        # 5. Giữ nguyên toàn bộ bài tập cho các lớp
        admin_row = conn.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1").fetchone()
        admin_id = admin_row["id"] if admin_row else 1
        for cid in [id_11a1, id_11a4, id_11a5]:
            for a in EXISTING_ASSIGNMENTS:
                cursor.execute("SELECT id FROM assignments WHERE title = ? AND class_id = ?", (a["title"], cid))
                if not cursor.fetchone():
                    cursor.execute(
                        """
                        INSERT INTO assignments (
                            title, description, subject, class_id, created_by,
                            start_at, deadline, allow_resubmit, allow_late_submission,
                            resubmit_after_deadline, submission_grace_period, max_images, max_file_size,
                            status, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            a["title"], a["description"], a["subject"], cid, admin_id,
                            a["start_at"], a["deadline"], a["allow_resubmit"], a["allow_late_submission"],
                            a["resubmit_after_deadline"], a["submission_grace_period"], a["max_images"],
                            a["max_file_size"], a["status"], now, now
                        )
                    )

        print("Đồng bộ hoàn hảo: Admin, Lớp 11A1, Lớp 11A4, Lớp 11A5 và toàn bộ bài tập đã được bảo toàn!")

if __name__ == "__main__":
    seed()
