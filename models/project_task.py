from odoo import models, fields, api

class ProjectTask(models.Model):
    _inherit = 'project.task'

    date_start = fields.Date(string='Start Date')
    date_end = fields.Date(string='End Date')
    effective_hours = fields.Float("Effective Time", tracking=True)

    phase_line_ids = fields.One2many(
        'project.task.phase',
        'task_id',
        string='Phase (WBS)',
        tracking=True
    )
    issue_count = fields.Integer(string='Issue', store=True)
    resolved_count = fields.Integer(string='Resolved', store=True)