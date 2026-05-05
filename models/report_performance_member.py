from odoo import models, fields, api

class ReportPerformanceMember(models.TransientModel):
    _name = 'report.performance.member'
    _description = 'Member performance report'

    project_id = fields.Many2one('project.project', string='Project')
    user_id = fields.Many2one('res.users', string='Member')
    task_id = fields.Many2one('project.task', string='Task')
    phase_id = fields.Many2one('project.phase', string='Phase')
    planned_start = fields.Datetime(string='Planned Start')
    planned_end = fields.Datetime(string='Planned End')
    planned_hours = fields.Float(string='Planned hours')
    actual_hours = fields.Float(string='Actual hours')
    performance_ratio = fields.Float(string='Ratio', compute='_compute_ratio')

    # Compute ratio
    @api.depends('planned_hours', 'actual_hours')
    def _compute_ratio(self):
        for record in self:
            record.performance_ratio = (record.actual_hours / record.planned_hours) if record.planned_hours else 0.0

    # Generate report
    def action_generate_report(self):
        # Delete old data
        self.search([]).unlink()

        # Get all phase
        all_phases = self.env['project.task.phase'].search([])

        for phase in all_phases:
            # Lấy các thành viên được gán (planned)
            users = phase.planned_user_ids
            if not users:
                continue
                
            for user in users:
                # Tính giờ thực tế của riêng user này trong phase này
                user_timesheets = phase.task_id.timesheet_ids.filtered(
                    lambda l: l.phase_id.id == phase.id and l.user_id.id == user.id
                )
                user_actual_hours = sum(user_timesheets.mapped('unit_amount'))

                # Tạo bản ghi riêng cho từng user - task để hiển thị lên calendar
                self.create({
                    'project_id': phase.project_id.id,
                    'user_id': user.id,
                    'task_id': phase.task_id.id,
                    'phase_id': phase.phase_id.id,
                    'planned_start': phase.planned_start,
                    'planned_end': phase.planned_end,
                    'planned_hours': phase.planned_hours / len(users) if len(users) > 0 else 0, # Chia đều giờ kế hoạch
                    'actual_hours': user_actual_hours,
                })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Member Performance',
            'res_model': 'report.performance.member',
            'view_mode': 'list,calendar',
            'target': 'current',
        }
