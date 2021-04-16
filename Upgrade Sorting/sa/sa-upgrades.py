#ON CREATE/ON WRITE project.task, fields mnt_subscription_id, project_id
# Domain filtering [["project_id","in",[70, 4157, 49]]]

# Maintenance products (product.product):
# 18305 : openerp_enterprise.product_maintenance : Extra Modules: Maintenance
# 2579 : openerp_enterprise.product_custo_maintenance : Maintenance of Customizations
# 11429 : __export__.product_product_11429_c00123b6 : Maintenance (Lines of Code)
# 15051 : / : Maintenance of Partner Apps
# 18306 : / : Maintenance Adjustment
# Customized Apps (27 products)

MAINTENANCE_PRODUCTS = [18305, 2579, 11429, 15051]
MAINTENANCE_ADJUSTMENT = 18306
PREFIX = ['BE', 'IN', 'US', 'HK', 'DU', 'LU']
TAGS = {'BE': 23177, 'IN': 23178, 'US': 23181, 'HK': 23179, 'DU': 23180, 'LU': 23183, 'MAINTENANCE': 23193}
PROJECTS = {'BE': 4157, 'HK': 4578} #TODO Add others 'IN': 4603
STAGES = {'BE': 3271, 'IN': 3272, 'US': 3276, 'HK': 3274, 'DU': 3275, 'LU': 3277, 'STANDARD': 3270}
EXCLUDED_STAGES = env['project.task.type'].search(['|', ('name', 'ilike', 'Cancel'), ('name', 'ilike', 'Done')]).ids
UPGRADE_PROJECT = 4429
UPGRADE_ISSUES_PROJECTS = [70, 4157]
HELP_PROJECT = 49


def has_maintenance(sub):
    #Check Main subscription
    sub_mnt_adjustment_lines = sub.recurring_invoice_line_ids.filtered_domain([('product_id', '=', MAINTENANCE_ADJUSTMENT)])
    sub_mnt_products_lines = sub.recurring_invoice_line_ids.filtered_domain(['|', ('product_id', 'in', MAINTENANCE_PRODUCTS), ('name', 'like', 'Customized')])
    #Check Maintenance subscription
    mnt_sub_mnt_adjustment_lines = sub.maintenance_subscription_id.recurring_invoice_line_ids.filtered_domain([('product_id', '=', MAINTENANCE_ADJUSTMENT)])
    mnt_sub_mnt_products_lines = sub.maintenance_subscription_id.recurring_invoice_line_ids.filtered_domain([('product_id', 'in', MAINTENANCE_PRODUCTS)])

    sub_maintenance_price = sum(sub_mnt_products_lines.mapped('price_subtotal')) + sum(sub_mnt_adjustment_lines.mapped('price_subtotal'))
    mnt_sub_maintenance_price = sum(mnt_sub_mnt_products_lines.mapped('price_subtotal')) + sum(mnt_sub_mnt_adjustment_lines.mapped('price_subtotal'))
    return (sub_maintenance_price + mnt_sub_maintenance_price) > 0


def create_parent_task(task, prefix, tag_ids):
    target_version = db_version = db_hosting = "X"
    if task.mnt_subscription_id.database_count == 1:
        db_version = task.mnt_subscription_id.database_ids.version.replace("+e", "")
        db_hosting = task.mnt_subscription_id.database_ids.hosting.replace("paas", "sh")

    partner_name = task.mnt_subscription_id.enterprise_final_customer_id.commercial_partner_id.name or \
                   task.mnt_subscription_id.partner_id.commercial_partner_id.name

    return env['project.task'].create({
        'name': "[UP] %s [%s->%s] (%s)" % (partner_name, db_version, target_version, db_hosting),
        'partner_id': task.partner_id.id,
        'mnt_subscription_id': task.mnt_subscription_id.id,
        'project_id': UPGRADE_PROJECT,
        'stage_id': STAGES.get(prefix) or STAGES.get('STANDARD'),
        'user_id': False,
        'reviewer_id': False,
        'tag_ids': tag_ids,
        'description': "(Upgrade Task automatically created to group Upgrade Issues together as Subtasks)",
        })



for rec in records:
    if rec.mnt_subscription_id:
        prefix = False
        tag_ids = []
        vals = {}

        # ADD TAGS (HELP AND UPGRADE)
        if has_maintenance(rec.mnt_subscription_id):
            tag_ids = [(4, TAGS.get('MAINTENANCE'))]
            if rec.mnt_subscription_id.team_id:
                for prefix in PREFIX:
                    if rec.mnt_subscription_id.team_id.name.startswith(prefix):
                        tag_ids.append((4,TAGS.get(prefix)))
                        break
            vals['tag_ids'] = tag_ids

        # MOVE TO THE RIGHT PROJECT (UPGRADE ONLY)
        if rec.project_id in UPGRADE_ISSUES_PROJECTS:
            if not rec.user_id:
                vals['project_id'] = PROJECTS.get(prefix) if prefix in PROJECTS else rec.project_id.id

            #3 SET OR CREATE PARENT TASK (UPGRADE ONLY)
            upgrade_parent = env['project.task'].search([('project_id', '=', UPGRADE_PROJECT),
                                                        ('mnt_subscription_id', '=', rec.mnt_subscription_id.id),
                                                        ('id', '!=', rec.id),
                                                        ('stage_id', 'not in', EXCLUDED_STAGES)], limit=1)
            if upgrade_parent:
                vals['user_id'] = rec.user_id.id or upgrade_parent.user_id.id
                vals['reviewer_id'] = rec.reviewer_id.id or upgrade_parent.reviewer_id.id
                vals['parent_id'] = rec.parent_id.id or upgrade_parent.id
            else:
                upgrade_parent = create_parent_task(rec, prefix, tag_ids)
                vals['parent_id'] = upgrade_parent.id

        rec.write(vals)
