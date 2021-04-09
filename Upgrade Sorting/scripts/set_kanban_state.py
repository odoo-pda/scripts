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
stage_model = connection.get_model("project.task.type")

print("===SET KANBAN STATE===")

## PART 1 : CHECK TASKS
upgrade_tasks = task_model.search_read([('project_id', '=', 4429),('stage_id', 'not in', (3303, 373))],
                                        ["partner_id", "id", "name", "project_id", "child_ids", "kanban_state"])
print(len(upgrade_tasks))
count = 0
task_ids = []

for task in upgrade_tasks:

    excluded_stage_ids = stage_model.search([('name', 'ilike', 'Cancel')])
    done_stage_ids = stage_model.search([('name', 'ilike', 'Done')])
    excluded_stage_ids.extend(done_stage_ids)

    subtask_ids = task_model.search_read([('parent_id', '=', task.get('id')), ('stage_id', 'not in', excluded_stage_ids)])
    if len(subtask_ids) > 0 and task.get('kanban_state') != 'done':
        print("KANBAN STATE set to GREEN for task %s" % task.get('id'))
        task_model.write(task.get('id'), {'kanban_state': 'done'}) #GREEN : Subtasks to check
    if len(subtask_ids) == 0 and task.get('kanban_state') != 'blocked':
        print("KANBAN STATE set to RED for task %s" % task.get('id'))
        task_model.write(task.get('id'), {'kanban_state': 'blocked'}) #RED : No subtasks to check
