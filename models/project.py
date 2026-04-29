from odoo import models, fields, api

class Project(models.Model):
    _inherit = 'project.project'

    # Actual
    actual_start = fields.Date(string='Actual Start', compute='_compute_actual_dates', store=True)
    actual_end = fields.Date(string='Actual End', compute='_compute_actual_dates', store=True)

    # Progress
    progress = fields.Float(string='Progress (%)', compute='_compute_progress', store=True)
    issue_count = fields.Integer(string='Issue', compute='_compute_resolved_issue', store=True)
    resolved_count = fields.Integer(string='Resolved', compute='_compute_resolved_issue', store=True)
    resolved_issue = fields.Char(string='Resolved/Issue', compute='_compute_resolved_issue', store=True)

    # Allowed managers
    allowed_manager_ids = fields.Many2many('res.users', compute='_compute_allowed_manager_ids')
    is_project_manager = fields.Boolean(compute='_compute_is_project_manager')

    @api.depends_context('uid')
    def _compute_is_project_manager(self):
        for project in self:
            is_manager = project.user_id == self.env.user or self.env.user.has_group('project.group_project_manager')
            project.is_project_manager = is_manager

    def _compute_allowed_manager_ids(self):
        leader_group = self.env.ref('project_wbs_extension.group_project_leader', raise_if_not_found=False)
        manager_group = self.env.ref('project.group_project_manager', raise_if_not_found=False)
        group_ids = []
        if leader_group:
            group_ids.append(leader_group.id)
        if manager_group:
            group_ids.append(manager_group.id)
            
        allowed_users = self.env['res.users'].search([
            ('share', '=', False),
            ('group_ids', 'in', group_ids)
        ])
        for project in self:
            project.allowed_manager_ids = allowed_users

    # Members
    member_ids = fields.Many2many('res.users', string='Members', tracking=True)

    # Phase
    phase_ids = fields.Many2many('project.phase', string='Phase', tracking=True)

    issue_ids = fields.One2many('project.issue', 'project_id', string='Issues')
    review_ids = fields.One2many('project.review', 'project_id', string='Reviews')

    # bug_count is removed in favor of issue_count
    review_count = fields.Integer(string='Review Count', compute='_compute_review_count', store=True)
    review_status = fields.Char(string='Reviews', compute='_compute_review_count', store=True)

    # _compute_bug_count is removed, its logic is merged into _compute_resolved_issue

    @api.depends('review_ids', 'review_ids.state')
    def _compute_review_count(self):
        for project in self:
            all_reviews = project.review_ids
            done_count = len(all_reviews.filtered(lambda r: r.state == 'done'))
            total_count = len(all_reviews)
            project.review_count = total_count
            project.review_status = f"{done_count} / {total_count}"

    def action_view_issues(self):
        self.ensure_one()
        is_manager = self.user_id == self.env.user or self.env.user.has_group('project.group_project_manager')
        ctx = {'default_project_id': self.id}
        if not is_manager:
            ctx.update({'create': False, 'delete': False, 'edit': False})
            
        return {
            'type': 'ir.actions.act_window',
            'name': 'Issues',
            'res_model': 'project.issue',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': ctx,
        }

    def action_view_reviews(self):
        self.ensure_one()
        is_manager = self.user_id == self.env.user or self.env.user.has_group('project.group_project_manager')
        ctx = {'default_project_id': self.id}
        if not is_manager:
            ctx.update({'create': False, 'delete': False, 'edit': False})
            
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reviews',
            'res_model': 'project.review',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': ctx,
        }

    def action_view_tasks(self):
        action = super().action_view_tasks()
        is_manager = self.user_id == self.env.user or self.env.user.has_group('project.group_project_manager')
        if not is_manager:
            ctx = dict(action.get('context', {}))
            ctx.update({'create': False, 'delete': False, 'edit': False})
            action['context'] = ctx
        return action

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
    
    def action_view_wbs(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("project_wbs_extension.action_project_wbs")
        
        is_manager = self.user_id == self.env.user or self.env.user.has_group('project.group_project_manager')
        ctx = {
            'default_project_id': self.id,
            'search_default_group_by_project': 1,
            'search_default_group_by_phase': 1,
            'group_by': ['project_id', 'phase_id'],
        }
        if not is_manager:
            ctx.update({'create': False, 'delete': False, 'edit': False})
            
        action.update({
            'domain': [('project_id', '=', self.id), ('project_id.active', '=', True)],
            'context': ctx
        })
        return action
    
    def action_view_wbs_report(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("project_wbs_extension.action_project_wbs_report")
        
        is_manager = self.user_id == self.env.user or self.env.user.has_group('project.group_project_manager')
        ctx = {
            'default_project_id': self.id,
            'search_default_group_by_project': 1,
            'search_default_group_by_phase': 1,
            'group_by': ['project_id', 'phase_id'],
        }
        if not is_manager:
            ctx.update({'create': False, 'delete': False, 'edit': False})
            
        action.update({
            'domain': [('project_id', '=', self.id), ('project_id.active', '=', True)],
            'context': ctx
        })
        return action

    @api.depends('task_ids.resolved_count', 'task_ids.issue_count', 'issue_ids.state')
    def _compute_resolved_issue(self):
        for project in self:
            # Get issues directly linked to project or via tasks
            all_issues = project.issue_ids
            resolved_count = len(all_issues.filtered(lambda i: i.state in ('resolved', 'closed')))
            issue_count = len(all_issues)
            project.resolved_count = resolved_count
            project.issue_count = issue_count
            project.resolved_issue = f"{resolved_count} / {issue_count}"