## Deuxieme avec creation de ticket parent

for rec in records: #TODO check id from prod.

    sub = rec.mnt_subscription_id # TODO issue when removing. Should be set on mnt_subscription_id on one shot separate SA : or rec.enterprise_subscription_ids.filtered_domain([('state', '=', 'open')])
    products = sub.recurring_invoice_line_ids.mapped('product_id')

    # ADD tag "Maintenance"
    maintenance_list = [20875, 20876, 11690, 2599, 15505, 2579]

    if any(product_id in maintenance_list for product_id in products.ids) or \
        any("Customized" in product.name for product in products):
        rec['tag_ids'] |= env['project.tags'].search([('name', '=', 'Maintenance')], limit=1)

        # ADD salesteam tag (Team BE, Team DU, Team HK, Team IN, Team LU, Team US, Team MX)
        if sub.team_id:
            for prefix in ['BE', 'DU', 'HK', 'IN', 'LU', 'US', 'MX']:
                if sub.team_id.name.startswith(prefix):
                    break
            rec['tag_ids'] |= env['project.tags'].search([('name', '=', 'Team %s' % prefix)], limit=1) #TODO Do not forget to create tags...

        # MOVE to the right project
        #TODO

        # ADD parent task or CREATE it
        upgrade_tasks = env['project.task'].search([('project_id', '=', 4157), ('stage_id', '=', 1879), ('mnt_subscription_id', '!=', False)]) #TODO change for upgrade project, remove stage
        parent_task = [task for task in upgrade_tasks if task.mnt_subscription_id == rec.mnt_subscription_id]
        if parent_task!= [] and not parent_task[0] == rec:
            rec['parent_id'] = rec.parent_id or parent_task[0]
            rec['user_id'] = rec.user_id or rec.parent_id.user_id
            rec['reviewer_id'] = rec.reviewer_id or rec.parent_id.reviewer_id

        else:
            db_version = sub.database_ids.version if sub.database_count == 1 else "X"
            target_version = "X" #TODO get it from upgrade platform

            env['project.task'].create({
                'name': "[MIG] %s (%s): to %s" % (rec.partner_id.commercial_company_name, db_version, target_version),
                'partner_id': rec.partner_id.id,
                'mnt_subscription_id': rec.mnt_subscription_id.id,
                'project_id': 4157, #TODO change for upgrade project
                'stage_id': 1879, #TODO change depending on teams
                'user_id': False,
                'reviewer_id': False,
                'tag_ids': rec.tag_ids,
                'description': "(Main Upgrade Task automatically created)",
                })
