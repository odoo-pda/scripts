#ON CREATE/ON WRITE project.task, fields mnt_subscription_id, project_id
# Domain filtering ["|",["project_id","=",70],["project_id","=",4157]]

# Maintenance products (product.product):
# 18305 : openerp_enterprise.product_maintenance : Extra Modules: Maintenance
# 2579 : openerp_enterprise.product_custo_maintenance : Maintenance of Customizations
# 11429 : __export__.product_product_11429_c00123b6 : Maintenance (Lines of Code)
# 15051 : / : Maintenance of Partner Apps
# 18306 : / : Maintenance Adjustment
# Customized Apps (27 products)

MAINTENANCE_PRODUCTS = [18305, 2579, 11429, 15051]
MAINTENANCE_ADJUSTMENT = 18306
MAINTENANCE_TAG = 23193
PREFIX = ['BE', 'IN', 'US', 'HK', 'DU', 'LU']
PROJECTS = {'BE': 4157}
STAGES = {'BE': 3271, 'IN': 3272, 'US': 3276, 'HK': 3274, 'DU': 3275, 'LU': 3277}
EXCLUDED_STAGES = [3303, 3304] #Done/Cancelled
UPGRADE_PROJECT = 4429


for rec in records:
    sub = rec.mnt_subscription_id
    if sub:
        prefix = has_maintenance = False
        tag_team = tag_maintenance = env['project.tags']

        #1 ADD TAGS
        #Main subscription
        sub_mnt_adjustment_lines = sub.recurring_invoice_line_ids.filtered_domain([('id', '=', MAINTENANCE_ADJUSTMENT)])
        sub_mnt_products_lines = sub.recurring_invoice_line_ids.filtered_domain(['|', ('id', 'in', MAINTENANCE_PRODUCTS),
                                                                                ('name', 'like', 'Customized')])
        #Maintenance subscription
        mnt_sub_mnt_adjustment_lines = sub.maintenance_subscription_id.recurring_invoice_line_ids.filtered_domain([('id', '=', MAINTENANCE_ADJUSTMENT)])
        mnt_sub_mnt_products_lines = sub.maintenance_subscription_id.recurring_invoice_line_ids.filtered_domain([('id', 'in', MAINTENANCE_PRODUCTS)])

        sub_maintenance_price = sum(sub_mnt_products_lines.mapped('price_subtotal')) - sum(sub_mnt_adjustment_lines.mapped('price_subtotal'))
        mnt_sub_maintenance_price = sum(mnt_sub_mnt_products_lines.mapped('price_subtotal')) - sum(mnt_sub_mnt_adjustment_lines.mapped('price_subtotal'))
        has_maintenance = (sub_maintenance_price + mnt_sub_maintenance_price) > 0

        if has_maintenance:
            tag_maintenance = env['project.tags'].search([('id', '=', MAINTENANCE_TAG)])

        if sub.team_id:
            for prefix in PREFIX:
                if sub.team_id.name.startswith(prefix):
                    tag_team = env['project.tags'].search([('name', '=', 'Team %s' % prefix)], limit=1)
                    break

        rec['tag_ids'] = rec['tag_ids'].union(tag_maintenance, tag_team)


        #2 MOVE TO THE RIGHT PROJECT
        rec['project_id'] = PROJECTS.get('prefix') if prefix else rec['project_id']


        #3 SET OR CREATE PARENT TASK
        upgrade_parent = env['project.task'].search([('project_id', '=', UPGRADE_PROJECT),
                                                     ('mnt_subscription_id', '=', rec.mnt_subscription_id.id),
                                                     ('stage_id', 'not in', EXCLUDED_STAGES)], limit=1)

        if upgrade_parent and upgrade_parent != rec:
            rec['parent_id'] = rec.parent_id or upgrade_parent
            rec['user_id'] = rec.user_id or upgrade_parent.user_id
            rec['reviewer_id'] = rec.reviewer_id or upgrade_parent.reviewer_id

        else:
            #CREATE PARENT, SET IN RIGHT STAGE

#                 db_version = sub.database_ids.version.replace("+e", "") if sub.database_count == 1 else "X"
#                 target_version = "X" #TODO get it from upgrade platform
#                 db_hosting = sub.database_ids.hosting if sub.database_count == 1 else "X"
#                 db_hosting = db_hosting.replace("paas", "sh")

#                 partner_name = rec.mnt_subscription_id.partner_id.commercial_company_name or \
#                             rec.mnt_subscription_id.partner_id.name or \
#                             rec.partner_id.commercial_company_name or \
#                             rec.partner_id.name

#                 custom_stages = {'BE': 3252, 'IN': 3253, 'US': 3254, 'HK': 3258, 'DU': 3256, 'LU': 3257} #TODO stages id from production + add other stages!
#                 standard_stage = 3251

#                 parent_task = env['project.task'].create({
#                     'name': "[UP] %s [%s->%s] (%s)" % (partner_name, db_version, target_version, db_hosting),
#                     'partner_id': rec.partner_id.id,
#                     'mnt_subscription_id': rec.mnt_subscription_id.id,
#                     'project_id': 4403, #TODO change for id from prod = 4429
#                     'stage_id': custom_stages.get(prefix) or standard_stage,
#                     'user_id': False,
#                     'reviewer_id': False,
#                     'tag_ids': tag_maintenance.union(tag_team),
#                     'description': "(Upgrade Task automatically created)",
#                     })
#                 rec['parent_id'] = parent_task.id


        #4 ADAPT KANBAN STATE OF PARENT

        #5 CLOSE PARENT TASK WHEN UPGRADED
