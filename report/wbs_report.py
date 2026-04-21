from odoo import models
from datetime import datetime, timedelta
import logging
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
    # end