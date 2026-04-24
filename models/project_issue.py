from odoo import models, fields, api

class ProjectIssue(models.Model):
    _name = 'project.issue'
    _description = 'Project Issue'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Issue Title', required=True, tracking=True)
    content = fields.Html(string='Issue Content')
    project_id = fields.Many2one('project.project', string='Project', required=True, tracking=True)
    task_id = fields.Many2one('project.task', string='Task', tracking=True)
    phase_id = fields.Many2one('project.phase', string='Phase', tracking=True)
    project_phase_ids = fields.Many2many('project.phase', related='project_id.phase_ids')
    project_member_ids = fields.Many2many('res.users', related='project_id.member_ids')
    
    reported_by = fields.Many2one('res.users', string='Reported By', default=lambda self: self.env.user, tracking=True, domain="[('id', 'in', project_member_ids), ('share', '=', False)]")
    assigned_to = fields.Many2one('res.users', string='Assigned To', tracking=True, domain="[('id', 'in', project_member_ids), ('share', '=', False)]")
    
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='1', tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True)

    date_reported = fields.Date(string='Date Reported', default=fields.Date.today)
    date_resolved = fields.Date(string='Date Resolved')
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

    def action_confirm(self):
        self.write({'state': 'open'})

    def action_resolve(self):
        self.write({
            'state': 'resolved',
            'date_resolved': fields.Date.today()
        })

    def action_close(self):
        self.write({'state': 'closed'})

    @api.onchange('project_id')
    def _onchange_project_id(self):
        self.task_id = False
        self.phase_id = False
