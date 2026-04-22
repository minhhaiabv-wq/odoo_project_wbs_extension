from odoo import models, fields
from datetime import datetime
import logging
import io
import base64
_logger = logging.getLogger(__name__)

class WbsReport(models.AbstractModel):
    _name = 'report.wbs.report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, wbs):

        if not wbs:
            return

        max_date = datetime(9999, 12, 31)
        wbs = wbs.sorted(
            key=lambda r: (
                r.project_id.id or 0,
                r.task_id.parent_id.parent_id.id or 0,
                r.task_id.parent_id.id or 0,
                r.task_id.id or 0,
                r.planned_start or max_date
            )
        )

        # 1. format
        sheet = workbook.add_worksheet('WBS')
        bold_center_bg = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#B7DEE8'})
        bold_left_bg = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter', 'border': 1, 'bg_color': '#B7DEE8'})
        border_center = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        border_center_wrap = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
        border_left_wrap = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'top', 'text_wrap': True})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd', 'align': 'left'})
        border_date_format = workbook.add_format({'num_format': 'yyyy-mm-dd', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        border_number_format = workbook.add_format({'num_format': '#,##0.00', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        
        # Formats for conditional highlighting
        yellow_date = workbook.add_format({'num_format': 'yyyy-mm-dd', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#FFFF00'})
        yellow_left_wrap = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'top', 'text_wrap': True, 'bg_color': '#FFFF00'})
        yellow_number = workbook.add_format({'num_format': '#,##0.00', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#FFFF00'})
        
        red_number = workbook.add_format({'num_format': '#,##0.00', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_color': '#FF0000'})
        yellow_red_number = workbook.add_format({'num_format': '#,##0.00', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#FFFF00', 'font_color': '#FF0000'})

        # set width column
        sheet.set_column(0, 0, 3.5) # col A
        sheet.set_column(1, 1, 15) # col B
        sheet.set_column(2, 2, 15) # col C
        sheet.set_column(3, 3, 43) # col D

        # Create time
        sheet.write('B1', '作成日：', workbook.add_format({'bold': True}))
        sheet.write('C1', datetime.now(), date_format)

        # Project name
        project_name = wbs[0].project_id.name if wbs and wbs[0].project_id else ''
        sheet.write('A4', project_name, workbook.add_format({'bold': True, 'font_size': 22}))

        # Phase
        projects = wbs.mapped('project_id')
        max_phases = []
        for proj in projects:
            proj_phases = proj.phase_ids.sorted('sequence')
            if len(proj_phases) > len(max_phases):
                max_phases = proj_phases

        # Header columns 1 - 4
        sheet.merge_range('A7:A8', 'No.', bold_center_bg)
        sheet.merge_range('B7:B8', '区分', bold_center_bg)
        sheet.merge_range('C7:C8', '作業大項目', bold_center_bg)
        sheet.merge_range('D7:D8', '作業項目', bold_left_bg)

        # Phases headers
        start_col = 4 # Start column header
        for phase in max_phases:
            end_col = start_col + 7
            sheet.merge_range(5, start_col, 5, end_col, phase.name, border_center)

            # Sub header
            sheet.merge_range(6, start_col, 6, start_col + 3, '予定', border_center)
            sheet.merge_range(6, start_col + 4, 6, start_col + 7, '実績', border_center)

            sub_headers = ['開始日', '終了日', '担当者', '工数 (人日)'] * 2
            for i, sub in enumerate(sub_headers):
                sheet.write(7, start_col + i, sub, border_center_wrap)
                if sub == '開始日':
                    sheet.set_column(start_col + i, start_col + i, 10)
                if sub == '終了日':
                    sheet.set_column(start_col + i, start_col + i, 10)
                if sub == '担当者':
                    sheet.set_column(start_col + i, start_col + i, 15)
                if sub == '工数 (人日)':
                    sheet.set_column(start_col + i, start_col + i, 10)

            start_col += 8

        tasks_lvl3_all = wbs.filtered(lambda p: p.task_id.parent_id.parent_id)
        seen_task_ids = []
        unique_tasks = []

        for p in tasks_lvl3_all:
            if p.task_id.id not in seen_task_ids:
                unique_tasks.append(p.task_id)
                seen_task_ids.append(p.task_id.id)
        
        # Tasks
        row = 8
        global_idx = 1
        last_proj_id = None
        last_lv1_id = None
        last_lv2_id = None

        for t in unique_tasks:
            p_id = t.project_id.id
            lv1 = t.parent_id.parent_id
            lv2 = t.parent_id

            # Column A
            sheet.write(row, 0, global_idx, border_center)

            # Column B
            if p_id != last_proj_id or lv1.id != last_lv1_id:
                sheet.write(row, 1, lv1.name or '', border_center)
                last_lv1_id = lv1.id
            else:
                sheet.write(row, 1, '', border_center)

            # Column C
            if p_id != last_proj_id or lv1.id != last_lv1_id or lv2.id != last_lv2_id:
                sheet.write(row, 2, lv2.name or '', border_center)
                last_lv2_id = lv2.id
            else:
                sheet.write(row, 2, '', border_center)

            sheet.write(row, 3, t.name or '', border_left_wrap)

            last_proj_id = p_id

            # Column Phase dynamic
            current_col = 4
            for p_header in max_phases:
                task_phase_rec = wbs.filtered(lambda p: p.task_id == t and p.phase_id == p_header)

                if task_phase_rec:
                    rec = task_phase_rec[0]
                    # Planned (Sắp xếp theo header: Bắt đầu, Kết thúc, Nhân sự, Công số)
                    sheet.write(row, current_col, rec.planned_start or '', border_date_format)
                    sheet.write(row, current_col + 1, rec.planned_end or '', border_date_format)
                    planned_users = ", ".join(rec.planned_user_ids.mapped('name'))
                    sheet.write(row, current_col + 2, planned_users, border_left_wrap)
                    sheet.write(row, current_col + 3, rec.planned_hours or '', border_number_format)
                    
                    # Actual
                    is_late_start = rec.actual_start and rec.planned_start and rec.actual_start > rec.planned_start
                    is_over_hours = rec.actual_hours and rec.planned_hours and rec.actual_hours > rec.planned_hours
                    
                    fmt_date = yellow_date if is_late_start else border_date_format
                    fmt_wrap = yellow_left_wrap if is_late_start else border_left_wrap
                    
                    if is_late_start and is_over_hours:
                        fmt_num = yellow_red_number
                    elif is_late_start:
                        fmt_num = yellow_number
                    elif is_over_hours:
                        fmt_num = red_number
                    else:
                        fmt_num = border_number_format

                    sheet.write(row, current_col + 4, rec.actual_start or '', fmt_date)
                    sheet.write(row, current_col + 5, rec.actual_end or '', fmt_date)
                    actual_users = ", ".join(rec.actual_user_ids.mapped('name'))
                    sheet.write(row, current_col + 6, actual_users, fmt_wrap)
                    sheet.write(row, current_col + 7, rec.actual_hours or '', fmt_num)
                else:
                    # Điền ô trống có border nếu không có dữ liệu cho phase này
                    for i in range(8):
                        sheet.write(row, current_col + i, "-", border_center)

                current_col += 8

            row += 1
            global_idx += 1

        # 3. Dòng tổng cộng
        row += 1 # Dòng trống
        sheet.merge_range(row, 0, row, 3, '', border_center)

        current_col = 4
        for p_header in max_phases:
            # Tính tổng cho phase này dựa trên danh sách task đã in
            phase_tasks = wbs.filtered(lambda p: p.phase_id == p_header and p.task_id.id in seen_task_ids)
            sum_planned = sum(phase_tasks.mapped('planned_hours'))
            sum_actual = sum(phase_tasks.mapped('actual_hours'))
            
            # Ghi dữ liệu dòng tổng cho phase
            for i in range(8):
                if i == 3: # Planned Hours
                    sheet.write(row, current_col + i, sum_planned, border_number_format)
                elif i == 7: # Actual Hours
                    sheet.write(row, current_col + i, sum_actual, border_number_format)
                else:
                    sheet.write(row, current_col + i, '', border_center)
            current_col += 8

        self._create_schedule_overview_sheet(workbook, wbs)

    def _create_schedule_overview_sheet(self, workbook, wbs):
        sheet = workbook.add_worksheet('Overview')

        # 1. Định dạng
        header_fmt = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#B7DEE8', 'text_wrap': True})
        phase_name_fmt = workbook.add_format({'bold': True, 'valign': 'vcenter', 'border': 1})
        type_fmt = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd', 'align': 'left'})

        # Dữ liệu ảnh 1x1 pixel để giả lập đường thẳng
        # Blue #0000FF (Planned)
        planned_img_data = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQwp8GAAAADklEQVR42mNk+M8ABwAFAAIAD198AAAAAElFTkSuQmCC')
        # Red #FF0000 (Actual)
        actual_img_data = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQwp8GAAAADklEQVR42mP8z8AAAgEBAAABO6OaAAAAAElFTkSuQmCC')
        
        empty_border = workbook.add_format({'border': 1})

        sheet.write('I1', '予定')
        # Vẽ line mẫu vào H1 bằng ảnh 1x1 scale
        sheet.insert_image(0, 7, 'p_legend.png', {
            'image_data': io.BytesIO(planned_img_data),
            'x_offset': 0, 'y_offset': 6, 'x_scale': 25, 'y_scale': 5
        })
        sheet.write('I2', '実績')
        # Vẽ line mẫu vào H2 bằng ảnh 1x1 scale
        sheet.insert_image(1, 7, 'a_legend.png', {
            'image_data': io.BytesIO(actual_img_data),
            'x_offset': 0, 'y_offset': 6, 'x_scale': 25, 'y_scale': 5
        })
        sheet.merge_range('Q1:S1', '作成日')
        sheet.merge_range('T1:V1', datetime.now(), date_format)

        # 2. Vẽ Header (12 tháng, mỗi tháng 4 tuần)
        sheet.write('A5', '工程', header_fmt)
        sheet.write('B5', '予定・実績', header_fmt)
        sheet.set_column('A:A', 20)

        months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']

        col_idx = 2
        for month in months:
            sheet.merge_range(4, col_idx, 4, col_idx + 3, month, header_fmt)
            for week in range(1, 5):
                # sheet.write(1, col_idx, f'W{week}', header_fmt)
                sheet.set_column(col_idx, col_idx, 3) # Cột tuần để hẹp
                col_idx += 1

        # 3. Đổ dữ liệu Phase
        # Lấy danh sách Phase duy nhất từ Project
        project = wbs[0].project_id
        phases_list = project.phase_ids.sorted('sequence')

        row = 5
        for phase in phases_list:
            # Merge 2 dòng cho cột Phase Name
            sheet.merge_range(row, 0, row + 1, 0, phase.name, phase_name_fmt)

            # Dòng Planned
            sheet.write(row, 1, '予定', type_fmt)
            # Dòng Actual
            sheet.write(row + 1, 1, '実績', type_fmt)

            # Tính toán ngày bắt đầu và kết thúc của Phase dựa trên các Task
            phase_data = wbs.filtered(lambda p: p.phase_id == phase)
            if phase_data:
                # Lấy Min/Max của Planned
                p_starts = [d for d in phase_data.mapped('planned_start') if d]
                p_ends = [d for d in phase_data.mapped('planned_end') if d]
                p_start = min(p_starts) if p_starts else False
                p_end = max(p_ends) if p_ends else False

                # Lấy Min/Max của Actual
                a_starts = [d for d in phase_data.mapped('actual_start') if d]
                a_ends = [d for d in phase_data.mapped('actual_end') if d]
                
                # Nếu chưa có actual_start thì không vẽ đường actual
                a_start = min(a_starts) if a_starts else False
                
                # Logic cho a_end:
                # 1. Lấy max(a_ends) nếu có
                # 2. Nếu chưa có task nào kết thúc nhưng đã có task bắt đầu, lấy ngày hiện tại
                # 3. Không được vượt quá ngày kết thúc của project (project.date)
                a_end = False
                if a_start:
                    a_end = max(a_ends) if a_ends else datetime.now()
                    
                    # Lấy project từ wbs nếu biến project chưa được truyền vào hoặc bị mất
                    proj_rec = wbs[0].project_id
                    project_end_date = proj_rec.date
                    if project_end_date:
                        # Chuyển Date thành Datetime để so sánh
                        project_end_dt = datetime.combine(project_end_date, datetime.max.time())
                        if a_end > project_end_dt:
                            a_end = project_end_dt

                # Vẽ đường thẳng tiến độ bằng Ảnh 1x1 scale
                self._draw_progress_bar(sheet, row, p_start, p_end, planned_img_data, empty_border, 'p_%s.png' % row)
                self._draw_progress_bar(sheet, row + 1, a_start, a_end, actual_img_data, empty_border, 'a_%s.png' % row)
            else:
                # Kẻ border trống nếu không có dữ liệu
                for c in range(2, 50):
                    sheet.write(row, c, '', empty_border)
                    sheet.write(row + 1, c, '', empty_border)

            row += 2

    def _draw_progress_bar(self, sheet, row, start_date, end_date, img_data, border_fmt, img_name='line.png'):
        """Hàm phụ trợ để vẽ đường thẳng bằng Ảnh 1x1 scale (thay thế cho Shape)"""
        # Kẻ border cho toàn bộ 48 tuần trước (giữ lưới)
        for c in range(2, 50):
            sheet.write(row, c, '', border_fmt)

        if not start_date or not end_date:
            return

        # Đảm bảo start_date và end_date là kiểu datetime/date
        if isinstance(start_date, str):
            start_date = fields.Datetime.to_datetime(start_date)
        if isinstance(end_date, str):
            end_date = fields.Datetime.to_datetime(end_date)

        # Tính toán pixel (Giả định mỗi cột rộng 3 ~ 26 pixels)
        col_width_px = 26
        month_width_px = 4 * col_width_px
        
        def get_x_offset(d):
            month_idx = d.month - 1
            # Tỷ lệ ngày trong tháng (tính tương đối 30 ngày)
            day_ratio = min((d.day - 1) / 30.0, 1.0)
            return int(month_idx * month_width_px + day_ratio * month_width_px)

        start_x = get_x_offset(start_date)
        end_x = get_x_offset(end_date)
        
        width_px = end_x - start_x
        if width_px <= 0:
            width_px = 5 # Độ dài tối thiểu
        # Chèn ảnh 1x1 pixel và scale chiều rộng để tạo thành đường thẳng
        sheet.insert_image(row, 2, img_name, {
            'image_data': io.BytesIO(img_data),
            'x_offset': start_x,
            'y_offset': 10, # Căn giữa dòng
            'x_scale': width_px,
            'y_scale': 6, # Độ dày của đường thẳng
            'object_position': 1 
        })
    # end