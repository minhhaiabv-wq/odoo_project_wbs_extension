from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ProjectTaskPhase(models.Model):
    _name = 'project.task.phase'
    _description = 'Task Phase (WBS)'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    project_id = fields.Many2one('project.project', related='task_id.project_id', store=True)
    task_id = fields.Many2one('project.task', required=True, ondelete='cascade', tracking=True, store=True)
    phase_id = fields.Many2one('project.phase', required=True, tracking=True, store=True)

    # ===== Planned =====
    planned_start = fields.Datetime(string='Planned Start', tracking=True, store=True)
    planned_end = fields.Datetime(string='Planned End', tracking=True, store=True)
    planned_user_ids = fields.Many2many('res.users', relation='task_phase_planned_user_rel', column1='task_phase_id', column2='user_id', string='Planned Members', tracking=True, store=True)
    planned_hours = fields.Float(string='Planned Hours', tracking=True, store=True)

    # ===== Actual =====
    actual_start = fields.Datetime(string='Actual Start', compute="_compute_actual_data", tracking=True, store=True)
    actual_end = fields.Datetime(string='Actual End', compute="_compute_actual_data", tracking=True, store=True)
    actual_user_ids = fields.Many2many('res.users', relation='task_phase_actual_user_rel', compute="_compute_actual_data", column1='task_phase_id', column2='user_id', string='Actual Members', tracking=True, store=True)
    actual_hours = fields.Float(string='Actual Hours', compute="_compute_actual_data", tracking=True, store=True)

    # ===== Issue =====
    issue_count = fields.Integer(string='Issue', store=True)
    progress = fields.Char(string='Progress', store=True)
    end_flag = fields.Boolean(string='End Flag', default=False)

    @api.depends('task_id', 'phase_id')
    def _compute_display_name(self):
        for record in self:
            if not record._origin.id:
                record.display_name = _("New")
            else:
                task_name = record.task_id.display_name or ""
                phase_name = record.phase_id.display_name or ""
                record.display_name = f"{task_name} / {phase_name}" if phase_name else task_name

    @api.constrains('task_id', 'phase_id')
    def _check_unique_task_phase(self):
        for record in self:
            domain = [
                ('id', '!=', record.id),
                ('task_id', '=', record.task_id.id),
                ('phase_id', '=', record.phase_id.id),
            ]
            exist = self.search_count(domain)
            if exist > 0:
                raise ValidationError(_("Error: Task '%s' already has a phase '%s'!") % (record.task_id.name, record.phase_id.name))

    @api.depends(
        'task_id',
        'task_id.timesheet_ids.date',
        'task_id.timesheet_ids.unit_amount',
        'task_id.timesheet_ids.user_id',
        'task_id.timesheet_ids.end_flag',
        'task_id.timesheet_ids.phase_id',
    )
    def _compute_actual_data(self):
        for record in self:
            # Timesheet lines in this module store `phase_id` as a M2O to `project.task.phase` (this model).
            # Filter from task's timesheets to get only lines for this phase line.
            timesheets = record.task_id.timesheet_ids.filtered(lambda l: l.phase_id.id == record.id)

            if timesheets:
                # 1. actual_start: min date
                start_dates = [fields.Datetime.to_datetime(d) for d in timesheets.mapped('date') if d]
                record.actual_start = min(start_dates) if start_dates else False

                # 2. actual_end: max date with end_flag = 1
                end_lines = timesheets.filtered(lambda t: t.end_flag == True)
                if end_lines:
                    end_dates = [fields.Datetime.to_datetime(d) for d in end_lines.mapped('date') if d]
                    record.actual_end = max(end_dates) if end_dates else False
                else:
                    record.actual_end = False

                # 3. actual_user_ids: Get list user_id unique
                user_ids = timesheets.mapped('user_id').ids
                record.actual_user_ids = [(6, 0, list(set(user_ids)))]

                # 4. actual_hours: Sum unit_amount
                record.actual_hours = sum(timesheets.mapped('unit_amount'))
            else:
                # Reset data without timesheet
                record.actual_start = False
                record.actual_end = False
                record.actual_hours = 0.0
                record.actual_user_ids = [(5, 0, 0)]
