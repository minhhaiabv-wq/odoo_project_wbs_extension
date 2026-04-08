from odoo import api, fields, models

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    phase_id = fields.Many2one(
        'project.task.phase',
        string='Phase',
        required=True,
        domain="[('project_id', '=', project_id), ('task_id', '=', task_id)]",
    )
    progress = fields.Char(string='Progress', store=True)
    end_flag = fields.Boolean(string='End Flag', default=False)

    @api.onchange('project_id', 'task_id')
    def _onchange_task_id_phase_id(self):
        for record in self:
            if record.phase_id and (
                record.phase_id.project_id != record.project_id
                or record.phase_id.task_id != record.task_id
            ):
                record.phase_id = False
