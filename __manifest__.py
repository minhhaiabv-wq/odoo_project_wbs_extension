{
    'name': 'Project WBS Extension',
    'version': '1.0',
    'depends': ['project', 'hr_timesheet'],
    'author': 'Custom',
    'category': 'Project',
    'description': 'Add Planned vs Actual fields on Project level',
    'data': [
        'security/project_security.xml',
        'security/ir.model.access.csv',
        'views/project_phase_views.xml',
        'views/project_project_views.xml',
        'views/project_task_views.xml',
        'views/project_wbs_views.xml',
        'views/hr_timesheet_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'project_wbs_extension/static/src/css/style.css',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
