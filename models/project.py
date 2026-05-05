import requests
import json
import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class Project(models.Model):
    _inherit = 'project.project'

    teams_webhook_url = fields.Char(string='Teams Webhook URL', help="Microsoft Teams Incoming Webhook URL for notifications")


    # Progress
    progress = fields.Float(string='Progress (%)', compute='_compute_progress', store=True)
    issue_count = fields.Integer(string='Issue', compute='_compute_resolved_issue', store=True)
    resolved_count = fields.Integer(string='Resolved', compute='_compute_resolved_issue', store=True)
    resolved_issue = fields.Char(string='Resolved/Issue', compute='_compute_resolved_issue', store=True)

    # Allowed managers
    allowed_manager_ids = fields.Many2many('res.users', compute='_compute_allowed_manager_ids')
    is_project_manager = fields.Boolean(compute='_compute_is_project_manager')

    # Compute is project manager
    @api.depends_context('uid')
    def _compute_is_project_manager(self):
        for project in self:
            is_manager = project.user_id == self.env.user or self.env.user.has_group('project.group_project_manager')
            project.is_project_manager = is_manager

    # Compute allowed managers
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

    # Action view issues
    def action_view_issues(self):
        self.ensure_one()
        is_manager = self.user_id == self.env.user or self.env.user.has_group('project.group_project_manager')
        ctx = {'default_project_id': self.id}
        if not is_manager:
            ctx.update({
                'create': False,
                'delete': False,
                'edit': False,
                'quick_create': False,
                'hide_create': True,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Issues',
            'res_model': 'project.issue',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': ctx,
        }

    # Action view tasks
    def action_view_tasks(self):
        is_manager = self.user_id == self.env.user or self.env.user.has_group('project.group_project_manager')
        if not is_manager:
            # Use sudo() to bypass access restrictions on the action record itself
            action = self.env.ref('project_wbs_extension.action_view_task_readonly').sudo().read()[0]
            
            # Explicitly force the ReadOnly views for all modes
            view_kanban = self.env.ref('project_wbs_extension.view_task_kanban_readonly').id
            view_list = self.env.ref('project_wbs_extension.view_task_tree_readonly').id
            view_form = self.env.ref('project_wbs_extension.view_task_form_readonly').id
            
            action['views'] = [
                (view_kanban, 'kanban'),
                (view_list, 'list'),
                (view_form, 'form'),
                (False, 'calendar'),
                (False, 'pivot'),
                (False, 'graph'),
            ]
            
            action.update({
                'domain': [('project_id', '=', self.id)],
                'context': {
                    'default_project_id': self.id,
                    'active_id': self.id,
                    'active_model': 'project.project',
                }
            })
            return action
        return super().action_view_tasks()

    # Compute progress
    @api.depends('task_ids.allocated_hours', 'task_ids.effective_hours')
    def _compute_progress(self):
        for project in self:
            total_allocated = sum(project.task_ids.mapped('allocated_hours'))
            total_effective = sum(project.task_ids.mapped('effective_hours'))

            if total_allocated > 0:
                project.progress = (total_effective / total_allocated) * 100
            else:
                project.progress = 0.0

    # Action view WBS
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
            ctx.update({
                'edit': False,
                'quick_create': False,
                'hide_create': True,
            })

        action.update({
            'domain': [('project_id', '=', self.id), ('project_id.active', '=', True)],
            'context': ctx
        })
        return action

    # Action view WBS report
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
            ctx.update({
                'edit': False,
                'quick_create': False,
                'hide_create': True,
            })

        action.update({
            'domain': [('project_id', '=', self.id), ('project_id.active', '=', True)],
            'context': ctx
        })
        return action

    # Compute resolved issue
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

    # Send teams notification
    def _send_teams_notification(self, user_ids, title, message):
        """ Send a notification to Microsoft Teams channel via webhook with user mentions """
        if not self:
            return
        self.ensure_one()
        if not self.teams_webhook_url:
            return
            
        if isinstance(user_ids, int):
            user_ids = [user_ids]
            
        users = self.env['res.users'].sudo().browse(user_ids)
        
        entities = []
        mention_texts = []
        
        for user in users:
            if user.email:
                # Format for Teams mention
                mention_text = f"<at>{user.name}</at>"
                mention_texts.append(mention_text)
                entities.append({
                    "type": "mention",
                    "text": mention_text,
                    "mentioned": {
                        "id": user.email,
                        "name": user.name
                    }
                })
            else:
                mention_texts.append(user.name)
        
        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "type": "AdaptiveCard",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": title,
                                "weight": "bolder",
                                "size": "large"
                            },
                            {
                                "type": "TextBlock",
                                "text": message,
                                "wrap": True
                            },
                            {
                                "type": "TextBlock",
                                "text": ", ".join(mention_texts),
                                "weight": "bolder",
                                "color": "accent",
                                "wrap": True
                            }
                        ],
                        "msteams": {
                            "entities": entities
                        },
                        "$schema": "http://adaptivecards.io/schemas/adaptivecard.json",
                        "version": "1.2"
                    }
                }
            ]
        }
        
        try:
            response = requests.post(
                self.teams_webhook_url, 
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            if response.status_code != 200:
                _logger.warning("Failed to send Teams notification. Status: %s, Response: %s", response.status_code, response.text)
        except Exception as e:
            _logger.error("Error sending Teams notification: %s", str(e))

    # Store project
    @api.model_create_multi
    def create(self, vals_list):
        projects = super(Project, self).create(vals_list)
        for project in projects:
            if project.user_id:
                project._send_teams_notification(
                    project.user_id.id, 
                    f"Project Assignment: {project.name}", 
                    "You have been assigned as **Project Manager**:"
                )
            if project.member_ids:
                project._send_teams_notification(
                    project.member_ids.ids, 
                    f"Project Assignment: {project.name}", 
                    "You have been assigned as **Member**:"
                )
        return projects

    # Write project
    def write(self, vals):
        # Store old values to detect changes
        old_data = {}
        if 'user_id' in vals or 'member_ids' in vals:
            for project in self:
                old_data[project.id] = {
                    'user_id': project.user_id.id,
                    'member_ids': project.member_ids.ids
                }
                
        res = super(Project, self).write(vals)
        
        for project in self:
            if project.id in old_data:
                # Check for new PM
                if 'user_id' in vals:
                    new_pm_id = vals.get('user_id')
                    if new_pm_id and new_pm_id != old_data[project.id]['user_id']:
                        project._send_teams_notification(
                            new_pm_id, 
                            f"Project Assignment: {project.name}", 
                            "You have been assigned as **Project Manager**:"
                        )
                
                # Check for new members
                if 'member_ids' in vals:
                    current_members = project.member_ids.ids
                    old_members = old_data[project.id]['member_ids']
                    new_members = list(set(current_members) - set(old_members))
                    if new_members:
                        project._send_teams_notification(
                            new_members, 
                            f"Project Assignment: {project.name}", 
                            "You have been assigned as **Member**:"
                        )
        return res
