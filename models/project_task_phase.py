from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ProjectTaskPhase(models.Model):
    _name = 'project.task.phase'
    _description = 'Task Phase (WBS)'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    project_id = fields.Many2one('project.project', related='task_id.project_id', store=True)
    task_id = fields.Many2one('project.task', required=True, ondelete='cascade', tracking=True)
    phase_id = fields.Many2one('project.phases', required=True, tracking=True)

    # ===== Planned =====
    planned_start = fields.Datetime(string='Planned Start', tracking=True)
    planned_end = fields.Datetime(string='Planned End', tracking=True)
    planned_user_ids = fields.Many2many('res.users', relation='task_phase_planned_user_rel', column1='task_phase_id', column2='user_id', string='Planned Members', tracking=True)
    planned_hours = fields.Float(string='Planned Hours', tracking=True)

    # ===== Actual =====
    actual_start = fields.Datetime(string='Actual Start', tracking=True)
    actual_end = fields.Datetime(string='Actual End', tracking=True)
    actual_user_ids = fields.Many2many('res.users', relation='task_phase_actual_user_rel', column1='task_phase_id', column2='user_id', string='Actual Members', tracking=True)
    actual_hours = fields.Float(string='Actual Hours', tracking=True)

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
