#Update mnt_subscription_id
import odoolib
import re


connection = odoolib.get_connection(
    hostname="www.test.odoo.com",
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
upgrade_tasks = task_model.search_read([('project_id', '=', 70), ('stage_id', 'not in', (1241, 898)), ('create_date', '>', '2020-12-31'),
                                        ('mnt_subscription_id', '=', False)],
                                        ["partner_id", "id", "name", "mnt_subscription_id", "enterprise_subscription_ids", "description", "create_date",
                                        "project_id", "user_id"])
print(len(upgrade_tasks))
count = 0
task_ids = []

for task in upgrade_tasks:

    #1 : mnt_subscription_id
    subscription_ids = [task.get('mnt_subscription_id')[0]] if task.get('mnt_subscription_id') else []
    # print("mnt_subscription_id %s" % subscription_ids)

    #2: contract number on description
    try:
        contract_number = re.search('<br>Contract number: (.+?)(<br>|</p>)', task.get('description')).group(1) if task.get('description') else False
        contract_id = sub_model.search_read([('code', '=', contract_number)], ["id"])
        subscription_ids.append(contract_id[0]['id']) if contract_id and contract_id[0]['id'] not in subscription_ids else None
        print("contract_number %s" % subscription_ids)

    except AttributeError:
        pass

    #3 : code on enterprise_subscription_ids
    active_subs = sub_model.search_read([('id', 'in', task.get('enterprise_subscription_ids')),('state', '=', 'open')], ["id"])
    for active_sub in active_subs:
        subscription_ids.append(active_sub.get('id')) if active_sub.get('id') not in subscription_ids else None
        print("enterprise_subscription_ids %s" % subscription_ids)


    # 4: database name on description
    try:
        database_name = re.search('(Dbname:|Extra dbname:) (.+?)(<br>|</p>)', task.get('description')).group(2) if task.get('description') else False
        db_contracts = odoo_database_model.search_read([('db_name', '=', database_name.split('.odoo.com')[0])], ["subscription_id"])
        for db_contract in db_contracts:
            if db_contract.get('subscription_id'):
                subscription_ids.append(db_contract.get('subscription_id')[0]) if db_contract.get('subscription_id')[0] not in subscription_ids else None
        print("database_name %s" % subscription_ids)

    except AttributeError:
        pass

    if not subscription_ids:
        continue

    print("TASK %s now with sub %s from sub list %s" % (task.get('id'), subscription_ids[0], subscription_ids))
    task_model.write(task.get('id'), {'mnt_subscription_id': subscription_ids[0]})
