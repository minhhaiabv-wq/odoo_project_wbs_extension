from odoo import models, fields, api, exceptions, _

class ProjectIssue(models.Model):
    _name = 'project.issue'
    _description = 'Project Issue'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'issue_no asc, priority desc'

    name = fields.Char(string='Issue Title', required=True, tracking=True)
    issue_no = fields.Integer(string='No.', readonly=True, copy=False, group_operator=False)
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
    ], string='Priority', default='0', tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ], string='State', default='draft', tracking=True)
    
    state_rank = fields.Integer(compute='_compute_state_rank', store=True)

    @api.depends('state')
    def _compute_state_rank(self):
        rank_map = {'draft': 1, 'open': 2, 'resolved': 3, 'closed': 4}
        for record in self:
            record.state_rank = rank_map.get(record.state, 5)

    date_reported = fields.Date(string='Date Reported', default=fields.Date.today, tracking=True)
    date_resolved = fields.Date(string='Date Resolved', tracking=True)
    
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

    # Compute fields for access control
    can_change_state = fields.Boolean(compute='_compute_access_control')
    is_leader_or_manager = fields.Boolean(compute='_compute_access_control')
    is_creator = fields.Boolean(compute='_compute_access_control')
    is_assigned = fields.Boolean(compute='_compute_access_control')
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('issue_no') and vals.get('project_id'):
                # Find the maximum issue_no for this project
                last_issue = self.search([('project_id', '=', vals['project_id'])], order='issue_no desc', limit=1)
                vals['issue_no'] = (last_issue.issue_no or 0) + 1
        return super(ProjectIssue, self).create(vals_list)

    @api.depends('reported_by', 'assigned_to')
    def _compute_access_control(self):
        is_manager = self.env.user.has_group('project.group_project_manager') or \
                     self.env.user.has_group('project_wbs_extension.group_project_leader')
        for record in self:
            record.is_leader_or_manager = is_manager
            record.is_creator = record.reported_by == self.env.user
            record.is_assigned = record.assigned_to == self.env.user
            record.can_change_state = is_manager or record.is_creator or record.is_assigned

    def write(self, vals):
        # Fields that assigned_to can change
        ALLOWED_FIELDS_ASSIGNED = {'state', 'date_resolved', 'content'}
        
        # Check if user has full rights
        is_manager = self.env.user.has_group('project.group_project_manager') or \
                     self.env.user.has_group('project_wbs_extension.group_project_leader')
        
        if not is_manager:
            for record in self:
                is_creator = record.reported_by == self.env.user
                is_assigned = record.assigned_to == self.env.user
                
                if not is_creator:
                    if is_assigned:
                        # If assigned, can only change allowed fields
                        for key in vals.keys():
                            if key not in ALLOWED_FIELDS_ASSIGNED:
                                raise exceptions.UserError(_("As the assigned user, you can only change: State, Date Resolved, and Content."))
                    else:
                        # If not manager, not creator, and not assigned, they shouldn't edit
                        raise exceptions.AccessError(_("You do not have permission to edit this issue."))
        
        return super(ProjectIssue, self).write(vals)

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
