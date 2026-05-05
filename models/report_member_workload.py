from odoo import models, fields, api
from datetime import datetime, timedelta, date, time

class ReportMemberWorkload(models.TransientModel):
    _name = 'report.member.workload'
    _description = 'Member Workload Report'

    project_id = fields.Many2one('project.project', string='Project')
    user_id = fields.Many2one('res.users', string='Member')
    task_id = fields.Many2one('project.task', string='Task')
    phase_id = fields.Many2one('project.task.phase', string='Phase')
    date_start = fields.Datetime(string='Start Date')
    date_stop = fields.Datetime(string='End Date')
    state = fields.Selection([
        ('free', 'Available'),
        ('busy', 'Assigned'),
    ], string='Status', default='free')
    name = fields.Char(string='Display Name', compute='_compute_name')

    # Compute display name
    @api.depends('user_id', 'task_id', 'phase_id', 'state')
    def _compute_name(self):
        for record in self:
            if record.state == 'free':
                record.name = f"[{record.user_id.name}] FREE"
            else:
                task_name = record.task_id.name or 'Task'
                phase_name = record.phase_id.phase_id.name or 'Phase'
                record.name = f"[{record.user_id.name}] {task_name} - {phase_name}"

    # Generate workload report
    def action_generate_workload(self):
        # Delete old data
        self.search([]).unlink()

        # Determine the time period: 4 months (2 months before and 2 months after)
        today = date.today()
        start_period = today - timedelta(days=today.weekday() + 60) # 2 months ago
        end_period = start_period + timedelta(days=120) # 4 months

        projects = self.env['project.project'].search([('active', '=', True)])
        all_members = projects.mapped('member_ids') # Get all unique members from active projects

        # Get all phases (WBS lines) in this time period
        all_phases = self.env['project.task.phase'].search([
            ('planned_start', '<', fields.Datetime.to_string(datetime.combine(end_period, datetime.max.time()))),
            ('planned_end', '>', fields.Datetime.to_string(datetime.combine(start_period, datetime.min.time())))
        ])

        for member in all_members:
            # 1. Create Busy records from actual task phases (keep entered hours)
            member_phases = all_phases.filtered(lambda p: member.id in p.planned_user_ids.ids)
            for tp in member_phases:
                self.create({
                    'project_id': tp.project_id.id,
                    'user_id': member.id,
                    'task_id': tp.task_id.id,
                    'phase_id': tp.id,
                    'date_start': tp.planned_start,
                    'date_stop': tp.planned_end,
                    'state': 'busy'
                })

            # 2. Create FREE records for empty days
            curr_date = start_period
            while curr_date < end_period:
                # Only create FREE for working days Monday-Friday
                if curr_date.weekday() < 5:
                    d_start_dt = datetime.combine(curr_date, time.min)
                    d_end_dt = datetime.combine(curr_date, time.max)

                    # Check if this day has any tasks
                    has_task = member_phases.filtered(lambda p: 
                        fields.Datetime.to_datetime(p.planned_start) <= d_end_dt and
                        fields.Datetime.to_datetime(p.planned_end) >= d_start_dt
                    )

                    if not has_task:
                        # Set FREE time 8h00 - 17h00 (Vietnam Time = UTC + 7)
                        self.create({
                            'user_id': member.id,
                            'date_start': datetime.combine(curr_date, time(1, 0)),
                            'date_stop': datetime.combine(curr_date, time(10, 0)),
                            'state': 'free'
                        })
                curr_date += timedelta(days=1)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Member Workload',
            'res_model': 'report.member.workload',
            'view_mode': 'calendar,list',
            'target': 'current',
            'context': {'search_default_group_by_user': 1}
        }
