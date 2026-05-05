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
        compute='_compute_dates_from_phase',
        store=True,
        readonly=False
    )
    planned_start = fields.Date(
        string='Planned Start',
        compute='_compute_dates_from_phase',
        store=True
    )
    project_member_ids = fields.Many2many('res.users', related='project_id.member_ids')

    effective_hours = fields.Float("Effective Time", tracking=True)
    allocated_hours = fields.Float("Allocated Time", compute='_compute_allocated_hours', store=True)
    is_project_manager = fields.Boolean(compute='_compute_is_project_manager')

    # Compute is project manager
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
    phase_ids = fields.Many2many(
        'project.phase',
        compute='_compute_phase_ids',
        string='Phases',
        store=True
    )

    # Compute phase ids
    @api.depends('phase_line_ids.phase_id')
    def _compute_phase_ids(self):
        for task in self:
            task.phase_ids = task.phase_line_ids.mapped('phase_id')

    issue_ids = fields.One2many('project.issue', 'task_id', string='Issues')
    
    issue_count = fields.Integer(string='Issue', compute='_compute_bug_count', store=True)
    resolved_count = fields.Integer(string='Resolved', compute='_compute_bug_count', store=True)

    # Compute allocated hours
    @api.depends('phase_line_ids.planned_hours')
    def _compute_allocated_hours(self):
        for task in self:
            task.allocated_hours = sum(task.phase_line_ids.mapped('planned_hours'))

    # Compute user ids from phase
    @api.depends('phase_line_ids.planned_user_ids')
    def _compute_user_ids_from_phase(self):
        for task in self:
            users = task.phase_line_ids.mapped('planned_user_ids')
            task.user_ids = users

    # Compute dates from phase
    @api.depends('phase_line_ids.planned_start', 'phase_line_ids.planned_end')
    def _compute_dates_from_phase(self):
        for task in self:
            starts = task.phase_line_ids.mapped('planned_start')
            ends = task.phase_line_ids.mapped('planned_end')
            
            valid_starts = [s for s in starts if s]
            valid_ends = [e for e in ends if e]
            
            if valid_starts:
                task.planned_start = min(valid_starts).date()
            else:
                task.planned_start = False
                
            if valid_ends:
                task.date_deadline = max(valid_ends).date()
            else:
                task.date_deadline = False

    # Compute bug count
    @api.depends('issue_ids')
    def _compute_bug_count(self):
        for task in self:
            task.issue_count = len(task.issue_ids)
            task.resolved_count = len(task.issue_ids.filtered(lambda b: b.state in ('resolved', 'closed')))

    # Create task
    @api.model_create_multi
    def create(self, vals_list):
        tasks = super(ProjectTask, self).create(vals_list)
        for task in tasks:
            if task.user_ids and task.project_id:
                task._send_task_teams_notification(task.user_ids.ids, "Task Assigned")
        return tasks

    # Write task
    def write(self, vals):
        # Fields to track for notifications
        track_fields = {'user_ids', 'phase_line_ids', 'name', 'stage_id', 'state', 'priority'}
        
        old_data = {}
        if any(f in vals for f in track_fields):
            for task in self:
                old_data[task.id] = {
                    'user_ids': task.user_ids.ids,
                    'name': task.name,
                    'stage_id': task.stage_id.id,
                    'state': task.state,
                    'priority': task.priority
                }
                
        res = super(ProjectTask, self).write(vals)
        
        for task in self:
            if task.id in old_data:
                # Notify new users
                current_users = task.user_ids.ids
                new_users = list(set(current_users) - set(old_data[task.id]['user_ids']))
                if new_users:
                    task._send_task_teams_notification(new_users, "Task Assigned")
                
                # Notify existing users of other changes
                elif current_users:
                    changed = [f for f in (track_fields - {'user_ids'}) if f in vals]
                    if changed:
                        task._send_task_teams_notification(current_users, "Task Updated", changed_fields=changed)
                    
        return res

    def _send_task_teams_notification(self, user_ids, title_prefix, changed_fields=None):
        """ Helper to send detailed task notification """
        self.ensure_one()
        if not self.project_id or not self.project_id.teams_webhook_url:
            return

        changed_fields = changed_fields or []
        priority_map = dict(self._fields['priority'].selection)
        state_map = dict(self._fields['state'].selection)

        # Get WBS lines (phases) where these users are assigned
        relevant_phases = self.phase_line_ids.filtered(lambda p: any(u in user_ids for u in p.planned_user_ids.ids))

        lines = [
            f"Project: **{self.project_id.name}**",
            ""
        ]

        is_wbs_changed = 'phase_line_ids' in changed_fields

        lines.append("Task details:")
        lines.append(f"- Stage: {self.stage_id.name or '-'}" if 'stage_id' in changed_fields else f"- Stage: {self.stage_id.name or '-'}")
        lines.append(f"- Status: {state_map.get(self.state, self.state)}" if 'state' in changed_fields else f"- Status: {state_map.get(self.state, self.state)}")
        lines.append(f"- Priority: {priority_map.get(self.priority, self.priority)}" if 'priority' in changed_fields else f"- Priority: {priority_map.get(self.priority, self.priority)}")
        lines.append("")

        for p_line in relevant_phases:
            p_start = p_line.planned_start.strftime('%d/%m/%Y') if p_line.planned_start else '-'
            p_end = p_line.planned_end.strftime('%d/%m/%Y') if p_line.planned_end else '-'

            phase_label = f"Phase: {p_line.phase_id.name}"
            lines.append(f"{phase_label}" if is_wbs_changed else phase_label)

            p_dates = f"{p_start} - {p_end}"
            lines.append(f"- Plan start - end: {p_dates}" if is_wbs_changed else f"- Plan start - end: {p_dates}")

            p_hours = f"{p_line.planned_hours}h"
            lines.append(f"- Plan hours: {p_hours}" if is_wbs_changed else f"- Plan hours: {p_hours}")
            lines.append("")

        self.project_id._send_teams_notification(
            user_ids,
            f"{title_prefix}: {self.name}",
            "\n".join(lines)
        )

    # Action view issues
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

    # Check access rights
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
