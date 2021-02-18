import odoolib

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

upgrade_tasks = task_model.search([('project_id', '=', 70), ('create_date', '>', '2021-01-31')])
count = 0

for task in upgrade_tasks:
    vals = task_model.read(task, ["name", "mnt_subscription_id", "enterprise_subscription_ids", "description", "create_date"], load='_classic_write')

    task_id = vals.get('id')
    name = vals.get('name')
    create_date = vals.get('create_date')


    #1 : mnt_subscription_id
    subscription_ids = [vals.get('mnt_subscription_id')] if vals.get('mnt_subscription_id') else []

    #2 : code on enterprise_subscription_ids
    enterprise_subscriptions = vals.get('enterprise_subscription_ids')
    for ent_subscription in enterprise_subscriptions:
        ent_vals =  sub_model.read(ent_subscription, ["code"], load='_classic_write')
        subscription_ids.append(ent_vals.get('id'))

    #3 : contract number on description
    #TODO

    #print("SUB", subscription_ids)

    for sub in subscription_ids:
        maintenance = False
        sub_line_vals = sub_model.read(sub, ["recurring_invoice_line_ids", "team_id", "partner_id"], load='_classic_write')
        if sub_line_vals.get('team_id') in [8, 63, 106, 35, 125]: #BE except partnership team
            invoice_lines = sub_line_vals.get('recurring_invoice_line_ids')
            partner = sub_line_vals.get('partner_id')
            partner_name = partner_model.read(partner, ["name"]).get('name')
            for invoice_line in invoice_lines:
                product_vals = sub_line_model.read(invoice_line, ["product_id"])
                maintenance = "Maintenance of Custo" in product_vals.get('product_id')[1]
                if maintenance:
                    count+=1
                    print("Upgrade Issue #%s (%s) for ==%s== Maintenance fee on Subscription %s" % (task, create_date, partner_name, sub))
                    break



print("Custom Upgrade Tasks --------", count)



# for event in events:
#     lead_opp = calendar_model.read(event, ["opportunity_id"]).get('opportunity_id')
#     if lead_opp:
#       lead_user = lead_model.read(lead_opp[0], ["user_id"]).get('user_id')
#       cal_user = calendar_model.read(event, ["user_id"]).get('user_id')
#       if lead_user and lead_user != cal_user:
#         try:
#           calendar_model.write(event, {'user_id': lead_user[0]}, context={'tracking_disable': True})
#           print("OK %s" % event)
#         except:
#           print("NOT OK %s" % event)
#           continue




# 1. trouver la sub sur la tâche
#   1.1 susbscription_id
#   1.2 code dans enterprise_subscription_ids (au - 1)
#   1.3 notes Contract number: M21010722378222  TODO

# 2. y a t-il de la maintenance?
#   2.1 une ligne contient maintenance
#   2.2 running maintenance True

# 3. Team Sales BE uniquement

# 4. Penser à filtrer sur une create date apd janvier
