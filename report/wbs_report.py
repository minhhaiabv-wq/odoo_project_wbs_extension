from odoo import models
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class WbsReport(models.AbstractModel):
    _name = 'report.wbs.report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, wbs):
        _logger.info("BẮT ĐẦU CHẠY HÀM XUẤT EXCEL")
        # 1. format
        sheet = workbook.add_worksheet('WBS')
        bold_center_bg = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#B7DEE8'})
        border_left = workbook.add_format({'border': 1, 'align': 'left'})
        border_center = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd', 'align': 'left'})

        # set width column
        sheet.set_column(0, 0, 3.5) # col A
        sheet.set_column(1, 1, 15) # col B
        sheet.set_column(2, 2, 15) # col C
        sheet.set_column(3, 3, 43) # col D
        sheet.set_column(4, 4, 10) # col E
        sheet.set_column(5, 5, 10) # col F
        sheet.set_column(6, 6, 15) # col G
        sheet.set_column(7, 7, 9) # col H
        sheet.set_column(8, 8, 10) # col I
        sheet.set_column(9, 9, 10) # col J
        sheet.set_column(10, 10, 15) # col K
        sheet.set_column(11, 11, 9) # col L

        # Create time
        sheet.write('B1', '作成日：', workbook.add_format({'bold': True}))
        sheet.write('C1', datetime.now(), date_format)

        # Project name
        project_name = wbs[0].project_id.name if wbs and wbs[0].project_id else ''
        sheet.write('A4', project_name, workbook.add_format({'bold': True, 'font_size': 14}))

        # Task
        projects = wbs.mapped('project_id')
        max_phases = []
        for proj in projects:
            proj_phases = proj.phase_ids.sorted('sequence')
            if len(proj_phases) > len(max_phases):
                max_phases = proj_phases

        start_col = 4 # Cột E là index 4
        for phase in max_phases:
            end_col = start_col + 7
            sheet.merge_range(5, start_col, 5, end_col, phase.name, border_center)
            
            # Ghi tiêu đề con ở dòng 7 và 8 cho mỗi cụm
            sheet.merge_range(6, start_col, 6, start_col + 3, '予定', border_center)
            sheet.merge_range(6, start_col + 4, 6, start_col + 7, '実績', border_center)
            
            sub_headers = ['開始日', '終了日', '担当者', '工数 (人日)'] * 2
            for i, sub in enumerate(sub_headers):
                sheet.write(7, start_col + i, sub, border_center)
            
            start_col += 8

        # Phases
        # sheet.merge_range('E6:L6', 'PS', border_center)
        # sheet.merge_range('M6:T6', 'PG', border_center)

        # No.
        sheet.merge_range('A7:A8', 'No.', bold_center_bg)
        sheet.merge_range('B7:B8', '区分', bold_center_bg)
        sheet.merge_range('C7:C8', '作業大項目', bold_center_bg)
        sheet.merge_range('D7:D8', '作業項目', bold_center_bg)

        # plan, actual
        # sheet.merge_range('E7:H7', '予定', border_center)
        # sheet.merge_range('I7:L7', '実績', border_center)

        # # phase detail plan
        # sheet.write('E8', '開始日', border_center)
        # sheet.write('F8', '終了日', border_center)
        # sheet.write('G8', '担当者', border_center)
        # sheet.write('H8', '工数 (人日)', border_center)
        # # phase detail actual
        # sheet.write('I8', '開始日', border_center)
        # sheet.write('J8', '終了日', border_center)
        # sheet.write('K8', '担当者', border_center)
        # sheet.write('L8', '工数 (人日)', border_center)

        # 2. data
        row = 8
        idx = 1
        #tasks_lvl3 = wbs.filtered(lambda t: t.parent_id and t.parent_id.parent_id and not t.parent_id.parent_id.parent_id)

        # row = 1
        # # 3. get list in selected screen
        # for obj in wbs:
        #     # Boolean (column flag)
        #     status_text = "Active" if obj.active else "Deactive"
            
        #     # write data project
        #     sheet.write(row, 0, obj.name, left)
        #     sheet.write(row, 1, obj.type, left)
        #     sheet.write(row, 2, status_text, center)

        #     # 4. One2Many eg: bom_ids -> bom_line_ids)
        #     # Giả định lấy Bom đầu tiên của sản phẩm
        #     # if obj.bom_ids:
        #     #     bom_lines = obj.bom_ids[0].bom_line_ids
        #     #     for line in bom_lines:
        #     #         sheet.write(row, 3, line.product_id.name, left)
        #     #         sheet.write(row, 4, line.product_qty, center)
        #     #         sheet.write(row, 5, line.product_uom_id.name, center)
        #     #         row += 1
        #     # else:
        #     #     # when empty go to next row.
        #     #     row += 1