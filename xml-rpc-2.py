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


## PART 1 : CHECK TASKS
upgrade_tasks = task_model.search_read([('project_id', '=', 70), ('stage_id', 'not in', (1241, 898)), ('create_date', '>', '2020-12-31')],
                                        ["partner_id", "id", "name", "mnt_subscription_id", "enterprise_subscription_ids", "description", "create_date"])
print(len(upgrade_tasks))
count = 0

for task in upgrade_tasks:

    #1 : mnt_subscription_id
    subscription_ids = [task.get('mnt_subscription_id')[0]] if task.get('mnt_subscription_id') else []

    #2 : code on enterprise_subscription_ids
    active_subs = sub_model.search_read([('id', 'in', task.get('enterprise_subscription_ids')),('state', '=', 'open')], ["id"])
    for active_sub in active_subs:
        subscription_ids.append(active_sub.get('id'))

    #3: contract number on description
    try:
        contract_number = re.search('<br>Contract number: (.+?)(<br>|</p>)', task.get('description')).group(1) if task.get('description') else False
        contract_id = sub_model.search_read([('code', '=', contract_number)], ["id"])
        subscription_ids.append(contract_id[0]['id']) if contract_id and contract_id[0]['id'] not in subscription_ids else None
    except AttributeError:
        pass

    # 4: database name on description
    try:
        database_name = re.search('(Dbname:|Extra dbname:) (.+?)(<br>|</p>)', task.get('description')).group(2) if task.get('description') else False
        db_contract = odoo_database_model.search_read([('db_name', '=', database_name.split('.odoo.com')[0])], ["subscription_id"])
        subscription_ids.append(db_contract[0]['id']) if db_contract and db_contract[0]['id'] not in subscription_ids else None
    except AttributeError:
        pass

    if not subscription_ids:
        continue


    ## PART 2 : CHECK SUBSCRIPTIONS FOREACH TASK
    be_team_subs = sub_model.search_read([('id', 'in', subscription_ids), ('team_id', 'in', [8, 35, 63, 106, 125])],  # BE teams (except partnership)
                                         ["recurring_invoice_line_ids", "partner_id", "code"])

    for sub in be_team_subs:
        partner_name = partner_model.read([sub.get('partner_id')[0]], ["name"])[0].get('name')
        sub_lines = sub_line_model.search_read([('id', 'in', sub.get('recurring_invoice_line_ids'))], ["product_id"])
        products = [x['product_id'][0] for x in sub_lines]

        if any(product in (2268, 2579, 2599, 11690, 20875, 20876) for product in products):  # Maintenance of custo products
            count += 1
            print("Upgrade Issue #%s (%s) for ==%s== Maintenance fee on Subscription %s" % (task.get('id'), task.get('create_date'), partner_name, sub.get('code')))
            break

print("Custom Upgrade Tasks --------", count)
