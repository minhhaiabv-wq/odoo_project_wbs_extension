from odoo import models, fields, api

class Project(models.Model):
    _inherit = 'project.project'

    # This is just a scratch script to check if is_template exists
    def check_template_field(self):
        return 'is_template' in self._fields
