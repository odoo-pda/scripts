# SA on create of upgrade issue

#1 : mnt_subscription_id
subscriptions = self.mnt_subscription_id

#2 : active enterprise_subscription_ids
subscriptions |= self.enterprise_subscription_ids.filtered_domain([('state', '=', 'open')])

# TODO #3: contract number on description
# try:
#     contract_number = re.search('<br>Contract number: (.+?)(<br>|</p>)', task.get('description')).group(1) if task.get('description') else False
#     contract_id = sub_model.search_read([('code', '=', contract_number)], ["id"])
#     subscription_ids.append(contract_id[0]['id']) if contract_id and contract_id[0]['id'] not in subscription_ids else None
# except AttributeError:
#     pass

# TODO # 4: database name on description
# try:
#     database_name = re.search('(Dbname:|Extra dbname:) (.+?)(<br>|</p>)', task.get('description')).group(2) if task.get('description') else False
#     db_contract = odoo_database_model.search_read([('db_name', '=', database_name.split('.odoo.com')[0])], ["subscription_id"])
#     subscription_ids.append(db_contract[0]['id']) if db_contract and db_contract[0]['id'] not in subscription_ids else None
# except AttributeError:
#     pass

if not subscriptions:
    continue

# TODO Products to be checked... ok for new maintenance? All cases covered?
if not any(product_id in (2268, 2579, 2599, 11690, 20875, 20876) for product_id in subscriptions.mapped('recurring_invoice_line_ids')):
    #standard db, task stays in Upgrade Issue pipe
    #check parent task in stage "Standard DB"
else:
    #check salesteam to know where to move the task and in which stage check.
