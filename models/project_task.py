from odoo import models, fields, api
class ProjectTask(models.Model):
    _inherit = 'project.task'
    
    user_ids = fields.Many2many(
        'res.users', 
        domain="[('id', 'in', project_member_ids), ('share', '=', False)]",
        compute='_compute_user_ids_from_phase',
        store=True,
        readonly=True
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

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super(ProjectTask, self).create(vals_list)
        for task in tasks:
            if task.user_ids:
                task.project_id._send_teams_notification(
                    task.user_ids.ids,
                    f"Task Assignment: {task.name}",
                    f"You have been assigned to this task in project **{task.project_id.name}**:"
                )
        return tasks

    def write(self, vals):
        # Store old users to detect changes
        old_users = {}
        if 'user_ids' in vals or 'phase_line_ids' in vals:
            for task in self:
                old_users[task.id] = task.user_ids.ids
                
        res = super(ProjectTask, self).write(vals)
        
        for task in self:
            if task.id in old_users:
                current_users = task.user_ids.ids
                new_users = list(set(current_users) - set(old_users[task.id]))
                if new_users:
                    task.project_id._send_teams_notification(
                        new_users,
                        f"Task Assignment: {task.name}",
                        f"You have been assigned to this task in project **{task.project_id.name}**:"
                    )
        return res

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

    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        res = super().check_access_rights(operation, raise_exception=raise_exception)
        
        if operation == 'create' and res and not self.env.user.has_group('project.group_project_manager'):
            context = self.env.context
            project_id = context.get('active_id') or context.get('default_project_id')
            
            # 1. Final Resort: Parse project_id from URL path or referrer
            if not project_id:
                from odoo.http import request
                try:
                    if request and request.httprequest:
                        # Check full path and referrer
                        url = request.httprequest.full_path or request.httprequest.referrer or ""
                        import re
                        # Pattern for /projects/ID/tasks or ?active_id=ID or &id=ID
                        match = re.search(r'/projects/(\d+)', url) or \
                                re.search(r'active_id=(\d+)', url) or \
                                re.search(r'[?&]id=(\d+)', url)
                        if match:
                            project_id = match.group(1)
                except Exception:
                    pass

            # 2. Backup: HTTP Request params
            if not project_id:
                from odoo.http import request
                try:
                    if request and hasattr(request, 'params'):
                        project_id = request.params.get('id') or request.params.get('active_id')
                except Exception:
                    pass

            if project_id:
                try:
                    if isinstance(project_id, list):
                        project_id = project_id[0]
                    
                    project = self.env['project.project'].browse(int(project_id))
                    if project.exists() and project._name == 'project.project':
                        if project.user_id != self.env.user:
                            if raise_exception:
                                from odoo.exceptions import AccessError
                                raise AccessError("You are not the Project Manager of this project.")
                            return False
                except Exception:
                    pass
        return res


