#ON CREATE/ON WRITE project.task, field mnt_subscription_id and enterprise_subscription_ids (upgrade)
# Domain filtering ["|",["project_id","=",70],["project_id","=",4157]]

# Maintenance products :
# 20875 : Extra Modules: Maintenance
# 20876 : Maintenance Adjustment
# 11690 : Maintenance (Lines of Code)
# 2599 & 2579: Maintenance of Customizations
# 15505 : Maintenance of Partner Apps ???
# Customized Apps


for rec in records:
    sub = rec.mnt_subscription_id
    products = sub.recurring_invoice_line_ids.mapped('product_id')

    # ADD tag "Maintenance"
    maintenance_list = [20875, 20876, 11690, 2599, 15505, 2579]
    prefix = False
    tag_team = tag_maintenance = env['project.tags']


    if any(product_id in maintenance_list for product_id in products.ids) or \
        any("Customized" in product.name for product in products) or \
        sub.maintenance_is_paying:
        #TODO Careful! maintenance_is_paying has False positive with Loc X and Adjustment line of -X.
        # Should be checked to avoid Studio custom db.
        tag_maintenance = env['project.tags'].search([('name', '=', 'Maintenance')], limit=1)

        # ADD salesteam tag (Team BE, Team DU, Team HK, Team IN, Team LU, Team US, Team MX)
        if sub.team_id:
            for prefix in ['BE', 'DU', 'HK', 'IN', 'LU', 'US', 'MX']:
                if sub.team_id.name.startswith(prefix):
                    break
            tag_team = env['project.tags'].search([('name', '=', 'Team %s' % prefix)], limit=1)

        rec['tag_ids'] = rec['tag_ids'].union(tag_maintenance, tag_team)

    # ADD parent task or CREATE it
    upgrade_tasks = env['project.task'].search([('project_id', '=', 4403), ('mnt_subscription_id', '!=', False), ('stage_id', '!=', 3255)]) #TODO change for id upgrade project from prod = 4429 and stage Done = X
    parent_task = [task for task in upgrade_tasks if task.mnt_subscription_id == rec.mnt_subscription_id]

    if parent_task != [] and not parent_task[0] == rec:
        rec['parent_id'] = rec.parent_id or parent_task[0]
        rec['user_id'] = rec.user_id or rec.parent_id.user_id
        rec['reviewer_id'] = rec.reviewer_id or rec.parent_id.reviewer_id

    else:
        if rec.mnt_subscription_id:
            db_version = sub.database_ids.version.replace("+e", "") if sub.database_count == 1 else "X"
            target_version = "X" #TODO get it from upgrade platform
            db_hosting = sub.database_ids.hosting if sub.database_count == 1 else "X"
            db_hosting = db_hosting.replace("paas", "sh")

            partner_name = rec.mnt_subscription_id.partner_id.commercial_company_name or \
                        rec.mnt_subscription_id.partner_id.name or \
                        rec.partner_id.commercial_company_name or \
                        rec.partner_id.name

            custom_stages = {'BE': 3252, 'IN': 3253, 'US': 3254, 'HK': 3254, 'DU': 3254, 'LU': 3254} #TODO stages id from production + add other stages!
            standard_stage = 3251

            parent_task = env['project.task'].create({
                'name': "%s [%s->%s] (%s)" % (partner_name, db_version, target_version, db_hosting),
                'partner_id': rec.partner_id.id,
                'mnt_subscription_id': rec.mnt_subscription_id.id,
                'project_id': 4403, #TODO change for id from prod = 4429
                'stage_id': custom_stages.get(prefix) or standard_stage,
                'user_id': False,
                'reviewer_id': False,
                'tag_ids': tag_maintenance.union(tag_team),
                'description': "(Upgrade Task automatically created)",
                })
            rec['parent_id'] = parent_task.id

    # MOVE to the right project
    custom_projects = {'BE': 4157} #'IN': 3253, 'US': 3254, 'HK': 3254, 'DU': 3254, 'LU': 3254
    if custom_projects.get(prefix):
        rec['project_id'] = custom_projects.get(prefix)
