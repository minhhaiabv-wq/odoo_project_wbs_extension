from odoo import api, fields, models

class TimesheetsAnalysisReport(models.Model):
    _inherit = "timesheets.analysis.report"

    phase_id = fields.Many2one("project.task.phase", string="Phase", readonly=True)

    @api.model
    def _select(self):
        select_ = super()._select().rstrip()
        return (
            f"{select_},\n"
            "                A.phase_id AS phase_id\n"
        )

    def init(self):
        super().init()
