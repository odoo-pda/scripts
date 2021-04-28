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

print("===MOVE SPECIFICS===")

## PART 1 : CHECK TASKS
upgrade_tasks = task_model.search_read([('project_id', '=', 70), ('stage_id', 'not in', (1241, 898)),
                                        ('parent_id', '=', 2492031), ('user_id', '=', False)],
                                        ["partner_id", "id", "name", "mnt_subscription_id", "enterprise_subscription_ids", "description", "create_date",
                                        "project_id", "user_id", "tag_ids"])
print(len(upgrade_tasks))

for task in upgrade_tasks:
    task_model.write(task.get('id'), {'company_id': 3, 'project_id': 3137}) #US
    print(task.get('id'))
