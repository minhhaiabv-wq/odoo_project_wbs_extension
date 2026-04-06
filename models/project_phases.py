from odoo import models, fields

class ProjectPhases(models.Model):
    _name = 'project.phases'
    _description = 'Phases'
    _order = 'sequence, id'

    name = fields.Char(string='Phase Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)