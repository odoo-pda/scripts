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


## PART 1 : CHECK TASKS #TODO project 70! remove id = 2478596
upgrade_tasks = task_model.search_read([('project_id', '=', 70), ('stage_id', 'not in', (1241, 898)), ('create_date', '>', '2020-12-31'),
                                        ('id', 'not in', (2476619, 2456147, 2456150, 2456058))],
                                        ["partner_id", "id", "name", "mnt_subscription_id", "enterprise_subscription_ids", "description", "create_date",
                                        "project_id", "user_id"])
print(len(upgrade_tasks))
count = 0
task_ids = []

for task in upgrade_tasks:

    #1 : mnt_subscription_id
    subscription_ids = [task.get('mnt_subscription_id')[0]] if task.get('mnt_subscription_id') else []

    #2: contract number on description
    try:
        contract_number = re.search('<br>Contract number: (.+?)(<br>|</p>)', task.get('description')).group(1) if task.get('description') else False
        contract_id = sub_model.search_read([('code', '=', contract_number)], ["id"])
        subscription_ids.append(contract_id[0]['id']) if contract_id and contract_id[0]['id'] not in subscription_ids else None
    except AttributeError:
        pass

    #3 : code on enterprise_subscription_ids
    active_subs = sub_model.search_read([('id', 'in', task.get('enterprise_subscription_ids')),('state', '=', 'open')], ["id"])
    for active_sub in active_subs:
        subscription_ids.append(active_sub.get('id')) if active_sub.get('id') not in subscription_ids else None


    # 4: database name on description
    try:
        database_name = re.search('(Dbname:|Extra dbname:) (.+?)(<br>|</p>)', task.get('description')).group(2) if task.get('description') else False
        db_contracts = odoo_database_model.search_read([('db_name', '=', database_name.split('.odoo.com')[0])], ["subscription_id"])
        for db_contract in db_contracts:
            if db_contract.get('subscription_id'):
                subscription_ids.append(db_contract.get('subscription_id')[0]) if db_contract.get('subscription_id')[0] not in subscription_ids else None
    except AttributeError:
        pass

    if not subscription_ids:
        continue

    if not task.get('mnt_subscription_id'):
        print(task)
        print(subscription_ids[0])
        #task_model.write({'mnt_subscription_id: subscription_ids[0]})

    ## PART 2 : CHECK SUBSCRIPTIONS FOREACH TASK
    be_team_subs = sub_model.search_read([('id', 'in', subscription_ids), ('team_id', 'in', [8, 35, 63, 106, 125])],  # BE teams (except partnership)
                                         ["recurring_invoice_line_ids", "partner_id", "code", "maintenance_is_paying"])

    for sub in be_team_subs:
        maintenance_is_paying = sub.get('maintenance_is_paying')
        partner_name = partner_model.read([sub.get('partner_id')[0]], ["name"])[0].get('name')
        sub_lines = sub_line_model.search_read([('id', 'in', sub.get('recurring_invoice_line_ids'))], ["product_id"])
        products = [x['product_id'][0] for x in sub_lines]

        if any(product in (2579, 2599, 11690, 20875, 20876) for product in products) or maintenance_is_paying:  # Maintenance of custo products
            count += 1
            to_be_moved = "MV" if not task.get('user_id') else "--"
            print("%s Upgrade Issue %s (%s) for ==%s== Maintenance fee on Subscription %s. Assigned to : %s. New Maintenance LOC : %s" % (to_be_moved, task.get('id'), task.get('create_date'), partner_name, sub.get('code'), task.get('user_id'), maintenance_is_paying))
            if task.get('user_id') == False:
                task_ids.append(task.get('id'))
            break

## MOVE TASKS FROM UPGRADE ISSUES TO PSBE CUSTOM UPGRADES
tasks_to_update = task_model.search([('id', 'in', task_ids)])
print("%s MOVED TASKS : %s" % (len(tasks_to_update), tasks_to_update))
task_model.write(tasks_to_update, {'project_id': 4157})

print("Custom Upgrade Tasks --------", count)
