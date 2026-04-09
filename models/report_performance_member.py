from odoo import models, fields, api

class ReportPerformanceMember(models.TransientModel):
    _name = 'report.performance.member'
    _description = 'Member performance report'

    project_id = fields.Many2one('project.project', string='Project')
    user_id = fields.Many2one('res.users', string='Member')
    planned_hours = fields.Float(string='Planned hours')
    actual_hours = fields.Float(string='Actual hours')
    performance_ratio = fields.Float(string='Ratio', compute='_compute_ratio')

    @api.depends('planned_hours', 'actual_hours')
    def _compute_ratio(self):
        for record in self:
            record.performance_ratio = (record.actual_hours / record.planned_hours) if record.planned_hours else 0.0

    def action_generate_report(self):
        # Delete old data
        self.search([]).unlink()

        # Get all phase
        all_phases = self.env['project.task.phase'].search([])

        # get data by group (project_id, user_id)
        stats = {}

        for phase in all_phases:
            p_id = phase.project_id.id
            # Get member_ids from timesheets by phase_id
            timesheets = phase.task_id.timesheet_ids.filtered(lambda l: l.phase_id.id == phase.id)
            
            for ts in timesheets:
                u_id = ts.user_id.id
                key = (p_id, u_id)
                
                if key not in stats:
                    stats[key] = {'planned': 0.0, 'actual': 0.0}
                
                # Sum actual_hours
                stats[key]['actual'] += ts.unit_amount
                # Get planned_hours
                stats[key]['planned'] = phase.planned_hours 

        # Create record
        for key, value in stats.items():
            self.create({
                'project_id': key[0],
                'user_id': key[1],
                'planned_hours': value['planned'],
                'actual_hours': value['actual'],
            })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Member Performance',
            'res_model': 'report.performance.member',
            'view_mode': 'list',
            'target': 'current',
        }