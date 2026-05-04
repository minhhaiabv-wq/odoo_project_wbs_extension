from odoo import models, fields, api

class ProjectReview(models.Model):
    _name = 'project.review'
    _description = 'Project Review'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Review Title', required=True, tracking=True)
    content = fields.Html(string='Review Content')
    project_id = fields.Many2one('project.project', string='Project', required=True, tracking=True)
    task_id = fields.Many2one('project.task', string='Task', tracking=True)
    phase_id = fields.Many2one('project.phase', string='Phase', tracking=True)
    project_phase_ids = fields.Many2many('project.phase', related='project_id.phase_ids')
    project_member_ids = fields.Many2many('res.users', related='project_id.member_ids')
    
    reviewer_id = fields.Many2one('res.users', string='Reviewer', default=lambda self: self.env.user, tracking=True, domain="[('id', 'in', project_member_ids), ('share', '=', False)]")
    assigned_to = fields.Many2one('res.users', string='Assigned To', tracking=True, domain="[('id', 'in', project_member_ids), ('share', '=', False)]")
    date = fields.Date(string='Review Date', default=fields.Date.today)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], string='Status', default='draft', tracking=True)

    task_phase_id = fields.Many2one('project.task.phase', string='Task Phase', compute='_compute_task_phase_id', store=True)

    @api.depends('task_id', 'phase_id')
    def _compute_task_phase_id(self):
        for record in self:
            if record.task_id and record.phase_id:
                record.task_phase_id = self.env['project.task.phase'].sudo().search([
                    ('task_id', '=', record.task_id.id),
                    ('phase_id', '=', record.phase_id.id)
                ], limit=1)
            else:
                record.task_phase_id = False

    can_change_state = fields.Boolean(compute='_compute_can_change_state')
    is_leader_or_manager = fields.Boolean(compute='_compute_is_leader_or_manager')

    def _compute_is_leader_or_manager(self):
        is_manager = self.env.user.has_group('project.group_project_manager') or \
                     self.env.user.has_group('project_wbs_extension.group_project_leader')
        for record in self:
            record.is_leader_or_manager = is_manager

    def _compute_can_change_state(self):
        is_manager = self.env.user.has_group('project.group_project_manager') or \
                     self.env.user.has_group('project_wbs_extension.group_project_leader')
        for record in self:
            record.can_change_state = is_manager or (record.assigned_to == self.env.user)

    def action_done(self):
        self.write({'state': 'done'})

    @api.onchange('project_id')

    def _onchange_project_id(self):
        self.task_id = False
        self.phase_id = False
