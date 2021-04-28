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

print("===ADD TAGS===")



## PART 1 : CHECK TASKS
upgrade_tasks = task_model.search_read([('project_id', '=', 70),('stage_id', 'not in', (1241, 898)), ('create_date', '>', '2021-04-15'),
                                        ('id', 'not in', (2486339, 2513205))],
                                        ["partner_id", "id", "name", "mnt_subscription_id", "enterprise_subscription_ids", "description", "create_date",
                                        "project_id", "user_id", "tag_ids"])

task_ids = task_model.search([('project_id', '=', 70),('stage_id', 'not in', (1241, 898)), ('create_date', '>', '2021-04-15'), ('id', 'not in', (2486339, 2513205))])
data = task_model.export_data(task_ids, ["partner_id/.id", "id", "name", "mnt_subscription_id/.id", "enterprise_subscription_ids", "description", "create_date",
                                        "project_id", "user_id", "mnt_subscription_id/tag_ids/name", "mnt_subscription_id/partner_id", "mnt_subscription_id/code", "mnt_subscription_id/maintenance_is_paying", "mnt_subscription_id/team_id"])
data['datas']
print(len(upgrade_tasks))
count = 0
task_ids = []

for task in upgrade_tasks:

    sub_id = task.get('mnt_subscription_id')[0] if task.get('mnt_subscription_id') else False
    if not sub_id:
        continue
    sub = sub_model.search_read([('id', '=', sub_id)], ["recurring_invoice_line_ids", "partner_id", "code", "maintenance_is_paying", "team_id"])[0]

    #ADD TAGS
    maintenance_is_paying = sub.get('maintenance_is_paying')
    partner_name = partner_model.read([sub.get('partner_id')[0]], ["name"])[0].get('name')
    sub_lines = sub_line_model.search_read([('id', 'in', sub.get('recurring_invoice_line_ids'))], ["product_id"])
    product_ids = [x['product_id'][0] for x in sub_lines]
    product_names = [x['product_id'][1] for x in sub_lines]
    salesteam = sub.get('team_id')
    tag_team = tag_maintenance = False

    customized_apps = "Customized" in product_names
    # customized_apps = False
    # for name in product_names:
    #     if "Customized" in name:
    #         customized_apps = True
    #         break

    if customized_apps:
        print(customized_apps)
        print(product_names)

    if any(product in (2579, 18305, 11429) for product in product_ids) or maintenance_is_paying or customized_apps:
        tag_maintenance = tag_model.search([('name', '=', "Maintenance of Customisations")], limit=1)
        if salesteam:
            for prefix in ['BE', 'DU', 'HK', 'IN', 'LU', 'US', 'MX']:
                if salesteam[1].startswith(prefix):
                    break
            tag_team = tag_model.search([('name', '=', 'Team %s' % prefix)], limit=1)

    if tag_maintenance and not tag_maintenance[0] in task.get('tag_ids'):
        print("Write maintenance %s on task %s" % (tag_maintenance, task.get('id')))
        task_model.write(task.get('id'), {'tag_ids': [(4, tag_maintenance[0], 0)]})

    if tag_team and not tag_team[0] in task.get('tag_ids'):
        print("Write team %s on task %s" % (tag_team, task.get('id')))
        task_model.write(task.get('id'), {'tag_ids': [(4, tag_team[0], 0)]})
