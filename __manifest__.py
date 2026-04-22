{
    'name': 'Project WBS Extension',
    'version': '1.0',
    'depends': ['project', 'hr_timesheet', 'report_xlsx'],
    'author': 'Custom',
    'category': 'Project',
    'description': 'Add Planned vs Actual fields on Project level',
    'data': [
        'security/project_security.xml',
        'security/ir.model.access.csv',
        'views/project_phase_views.xml',
        'views/project_task_phase_views.xml',
        'views/project_task_views.xml',
        'views/project_views.xml',
        'views/hr_timesheet_views.xml',
        'views/report_performance_member_views.xml',
        'views/report_member_workload_views.xml',
        'views/report_action.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'project_wbs_extension/static/src/css/style.css',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
