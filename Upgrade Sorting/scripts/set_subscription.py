#Update mnt_subscription_id
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

print("===SET SUBSCRIPTION===")

## PART 1 : CHECK TASKS
upgrade_tasks = task_model.search_read([('project_id', '=', 70),('stage_id', 'not in', (1241, 898)), ('create_date', '>', '2021-03-15'),
                                        ('mnt_subscription_id', '=', False)],
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
        if contract_number:
            contract_id = sub_model.search_read([('code', '=', contract_number)], ["id"])
            subscription_ids.append(contract_id[0]['id']) if contract_id and contract_id[0]['id'] not in subscription_ids else None

    except AttributeError:
        pass



    # 3: database name on description |Dbname:
    try:
        extra_db_name = db_name = False
        try:
            extra_db_name = re.search('(Extra dbname:) (.+?)(<br>|</p>|</span>)', task.get('description')).group(2) if task.get('description') else False
        except:
            pass

        try:
            db_name = re.search('(Dbname:) (.+?)(<br>|</p>|</span>)', task.get('description')).group(2) if task.get('description') else False
        except:
            pass

        database_name = extra_db_name or db_name
        try:
            database_name = re.search('href=[\'"]?([^\'" >]+)', database_name).group(1) or False

        except:
            pass

        if database_name not in ["other", False, "odoo", "odoo.com", "www.odoo.com", "odoo.odoo.com"]:
            db_urls = odoo_database_model.search_read([('url', 'ilike', database_name)], ["subscription_id", "parent_id"])
            for db_url in db_urls:
                parent_id = db_url.get('parent_id')[0] if db_url.get('parent_id') else False
                if parent_id:
                    db_parent = odoo_database_model.search_read([('id', '=', parent_id)], ["subscription_id"])[0]
                    if db_parent.get('subscription_id'):
                        subscription_ids.append(db_parent.get('subscription_id')[0]) if db_parent.get('subscription_id')[0] not in subscription_ids else None
                if db_url.get('subscription_id'):
                    subscription_ids.append(db_url.get('subscription_id')[0]) if db_url.get('subscription_id')[0] not in subscription_ids else None
    except AttributeError:
        pass

    #4 : code on enterprise_subscription_ids
    active_subs = sub_model.search_read([('id', 'in', task.get('enterprise_subscription_ids')),('state', '=', 'open')], ["id"])
    for active_sub in active_subs:
        subscription_ids.append(active_sub.get('id')) if active_sub.get('id') not in subscription_ids else None

    if not subscription_ids:
        continue
    else:
        mtn_sub = subscription_ids[0]
        for sub_id in subscription_ids:
            sub = sub_model.search_read([('id', '=', sub_id)], ["recurring_invoice_line_ids","maintenance_is_paying"])[0]
            maintenance_is_paying = sub.get('maintenance_is_paying')
            sub_lines = sub_line_model.search_read([('id', 'in', sub.get('recurring_invoice_line_ids'))], ["product_id"])
            products = [x['product_id'][0] for x in sub_lines]

            if any(product in (2579, 18305, 11429) for product in products) or maintenance_is_paying:
                mtn_sub = sub_id

    print("SUB %s added on task %s from sub list %s" % (mtn_sub, task.get('id'), subscription_ids))
    task_model.write(task.get('id'), {'mnt_subscription_id': mtn_sub})
