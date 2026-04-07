from odoo import models, fields, api

class Project(models.Model):
    _inherit = 'project.project'

    # Actual
    actual_start = fields.Date(string='Actual Start', compute='_compute_actual_dates', store=True)
    actual_end = fields.Date(string='Actual End', compute='_compute_actual_dates', store=True)

    # Progress
    progress = fields.Float(string='Progress (%)', compute='_compute_progress', store=True)

    # Members
    member_ids = fields.Many2many('res.users', string='Members', tracking=True)

    # Phases
    phase_ids = fields.Many2many('project.phase', string='Phases', tracking=True)

    @api.depends('task_ids.date_start', 'task_ids.date_end')
    def _compute_actual_dates(self):
        for project in self:
            dates_start = project.task_ids.mapped('date_start')
            dates_end = project.task_ids.mapped('date_end')

            project.actual_start = min(dates_start) if dates_start else False
            project.actual_end = max(dates_end) if dates_end else False

    @api.depends('task_ids.allocated_hours', 'task_ids.effective_hours')
    def _compute_progress(self):
        for project in self:
            total_allocated = sum(project.task_ids.mapped('allocated_hours'))
            total_effective = sum(project.task_ids.mapped('effective_hours'))

            if total_allocated > 0:
                project.progress = (total_effective / total_allocated) * 100
            else:
                project.progress = 0.0

    # def action_view_wbs(self):
    #     self.ensure_one()
    #     return {
    #         'name': 'WBS',
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'project.task.phase',
    #         'view_mode': 'list,form',
    #         'domain': [('project_id', '=', self.id)],
    #         'context': {
    #             'default_project_id': self.id,
    #             'search_default_group_by_phase': 1,
    #         },
    #     }
    
    def action_view_wbs(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("project_wbs_extension.action_project_wbs")
        
        action.update({
            'domain': [('project_id', '=', self.id), ('project_id.active', '=', True)],
            'context': {
                'default_project_id': self.id,
                'search_default_group_by_project': 1,
                'search_default_group_by_phase': 1,
                'group_by': ['project_id', 'phase_id'],
            }
        })
        return action
