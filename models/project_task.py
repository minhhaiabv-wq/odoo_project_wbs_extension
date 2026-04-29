from odoo import models, fields, api

class ProjectTask(models.Model):
    _inherit = 'project.task'
    
    user_ids = fields.Many2many(
        'res.users', 
        domain="[('id', 'in', project_member_ids), ('share', '=', False)]",
        compute='_compute_user_ids_from_phase',
        store=True,
        readonly=False
    )
    date_deadline = fields.Date(
        string='Deadline',
        compute='_compute_deadline_from_phase',
        store=True,
        readonly=False
    )
    project_member_ids = fields.Many2many('res.users', related='project_id.member_ids')

    date_start = fields.Date(string='Start Date')
    date_end = fields.Date(string='End Date')
    effective_hours = fields.Float("Effective Time", tracking=True)
    allocated_hours = fields.Float("Allocated Time", compute='_compute_allocated_hours', store=True)
    is_project_manager = fields.Boolean(compute='_compute_is_project_manager')

    @api.depends_context('uid')
    def _compute_is_project_manager(self):
        for task in self:
            is_manager = task.project_id.user_id == self.env.user or self.env.user.has_group('project.group_project_manager')
            task.is_project_manager = is_manager

    phase_line_ids = fields.One2many(
        'project.task.phase',
        'task_id',
        string='Phase (WBS)',
        tracking=True
    )
    issue_ids = fields.One2many('project.issue', 'task_id', string='Issues')
    review_ids = fields.One2many('project.review', 'task_id', string='Reviews')

    # bug_count is replaced by issue_count
    review_count = fields.Integer(string='Review Count', compute='_compute_review_count', store=True)
    
    issue_count = fields.Integer(string='Issue', compute='_compute_bug_count', store=True)
    resolved_count = fields.Integer(string='Resolved', compute='_compute_bug_count', store=True)

    @api.depends('phase_line_ids.planned_hours')
    def _compute_allocated_hours(self):
        for task in self:
            task.allocated_hours = sum(task.phase_line_ids.mapped('planned_hours'))

    @api.depends('phase_line_ids.planned_user_ids')
    def _compute_user_ids_from_phase(self):
        for task in self:
            users = task.phase_line_ids.mapped('planned_user_ids')
            task.user_ids = users

    @api.depends('phase_line_ids.planned_end')
    def _compute_deadline_from_phase(self):
        for task in self:
            ends = task.phase_line_ids.mapped('planned_end')
            valid_ends = [e for e in ends if e]
            if valid_ends:
                task.date_deadline = max(valid_ends).date()
            else:
                task.date_deadline = False

    @api.depends('issue_ids')
    def _compute_bug_count(self):
        for task in self:
            task.issue_count = len(task.issue_ids)
            task.resolved_count = len(task.issue_ids.filtered(lambda b: b.state in ('resolved', 'closed')))

    @api.depends('review_ids')
    def _compute_review_count(self):
        for task in self:
            task.review_count = len(task.review_ids)

    def action_view_issues(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bugs',
            'res_model': 'project.issue',
            'view_mode': 'list,form',
            'domain': [('task_id', '=', self.id)],
            'context': {
                'default_project_id': self.project_id.id,
                'default_task_id': self.id,
            },
        }

    def action_view_reviews(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reviews',
            'res_model': 'project.review',
            'view_mode': 'list,form',
            'domain': [('task_id', '=', self.id)],
            'context': {
                'default_project_id': self.project_id.id,
                'default_task_id': self.id,
            },
        }
