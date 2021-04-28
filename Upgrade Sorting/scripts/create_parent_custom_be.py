import odoolib
import re


connection = odoolib.get_connection(
    hostname="www.odoo.com",
    database="openerp",
    login="pda",
    port=443,
    password="I8Phleyn",
    protocol='jsonrpcs',
)

task_model = connection.get_model("project.task")
sub_model = connection.get_model("sale.subscription")
sub_line_model = connection.get_model("sale.subscription.line")
product_model = connection.get_model("product.product")
partner_model = connection.get_model("res.partner")
odoo_database_model = connection.get_model("openerp.enterprise.database")
tag_model = connection.get_model("project.tags")

print("===CREATE CUSTOM BE PARENT===")

## PART 1 : CHECK TASKS
upgrade_issues = task_model.search_read([('project_id', '=', 4157),('stage_id', 'not in', (373, 365)), ('create_date', '>', '2021-04-15'),
                                        ('mnt_subscription_id', '!=', False), ('parent_id', '=', False)],
                                        ["partner_id", "id", "name", "mnt_subscription_id", "enterprise_subscription_ids", "description", "create_date",
                                        "project_id", "user_id", "tag_ids", "parent_id", "reviewer_id"])


print(len(upgrade_issues))

for issue in upgrade_issues:
    parent_task = False

    issue_sub_id = issue.get('mnt_subscription_id')[0] if issue.get('mnt_subscription_id') else False
    if not issue_sub_id:
        continue

    upgrade_tasks = task_model.search_read([('project_id', '=', 4429), ('mnt_subscription_id', '!=', False), ('stage_id', 'not in', (3303, 373))],
                                              ["id", "name", "mnt_subscription_id", "user_id", "reviewer_id"])

    for upgrade_task in upgrade_tasks:
        upgrade_sub_id = upgrade_task.get('mnt_subscription_id')[0] if upgrade_task.get('mnt_subscription_id') else False
        if upgrade_sub_id and upgrade_sub_id == issue_sub_id:
            parent_task = upgrade_task
            #kanban_state

    if parent_task and not parent_task.get('id') == issue.get('id'):
        print("WRITE on %s" % issue.get('id'))
        issue_user_id =  issue.get('user_id')[0] if  issue.get('user_id') else False
        issue_reviewer_id =  issue.get('reviewer_id')[0] if issue.get('reviewer_id') else False
        issue_parent_id = issue.get('parent_id')[0] if issue.get('parent_id') else False
        parent_task_user_id = parent_task.get('user_id')[0] if parent_task.get('user_id') else False
        parent_task_reviewer_id = parent_task.get('reviewer_id')[0] if parent_task.get('reviewer_id') else False

        task_model.write(issue.get('id'),
            {'parent_id': issue_parent_id or parent_task.get('id'),
             'user_id': issue_user_id or parent_task_user_id,
             'reviewer_id': issue_reviewer_id or parent_task_reviewer_id,
             })

    else:
        print("CREATE a parent for task %s" % issue.get('id'))
        partner_name = issue.get('partner_id')[1] if issue.get('partner_id') else "NAME"
        db = odoo_database_model.search_read([('subscription_id', '=', issue_sub_id)],
                                              ["id", "version", "hosting"], limit=1)
        db_version = db[0].get('version').replace("+e", "") if db else "X"
        target_version = "X"
        db_hosting = db[0].get('hosting').replace("paas", "sh") if db else "X"

        tag_maintenance = tag_model.search([('name', '=', "Maintenance of Customisations")], limit=1)
        tag_team = tag_model.search([('name', '=', "Team BE")], limit=1)

        parent_task = task_model.create({
            'name': "[UP] %s [%s->%s] (%s)" % (partner_name, db_version, target_version, db_hosting),
            'partner_id': issue.get('partner_id')[0] if issue.get('partner_id') else False,
            'mnt_subscription_id': issue.get('mnt_subscription_id')[0],
            'project_id': 4429,
            'stage_id': 3271,
            'user_id': False,
            'reviewer_id': False,
            'description': "(Upgrade Task automatically created)",
            'tag_ids': [(6, 0, (tag_maintenance[0],tag_team[0]))],
        })
        print(parent_task)
        task_model.write(issue.get('id'), {'parent_id': parent_task})
