from tools.odoorpc import OdooXR
from tools.password_manager import OePassword
# import re
import sys

url = "https://www.odoo.com"
database = 'openerp'
pm = OePassword()
oxr = OdooXR(database, url, pm)

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
PROJECTS = {'BE': [4157, 1], 'HK': [4578, 5], 'DU': [3147, 14], 'US': [3137, 3]}  # TODO Add 'IN' Company = 2
STAGES = {'BE': 3271, 'IN': 3272, 'US': 3276, 'HK': 3274, 'DU': 3275, 'STANDARD': 3270}
EXCLUDED_STAGES = oxr.search('project.task.type', ['|', ('name', 'ilike', 'Cancel'), ('name', 'ilike', 'Done')])
UPGRADE_PROJECT = 4429
UPGRADE_ISSUES_PROJECTS = [70, 4157]
HELP_PROJECT = 49
EXCLUDED_TASKS = [2486339, 2513205]
DATE = '2021-04-25'


def has_maintenance(sub):
    # Get subscription lines from main and maintenance subcription
    line_ids = sub.get('recurring_invoice_line_ids')
    if sub.get('maintenance_subscription_id'):
        mnt_sub = oxr.search_read('sale.subscription', [('id', '=', sub.get('maintenance_subscription_id'))], ['recurring_invoice_line_ids'])
        line_ids += mnt_sub.get('recurring_invoice_line_ids')

    # Get maintenance related lines amount
    lines = oxr.search_read('sale.subscription.line', [('id', 'in', line_ids)], ['product_id', 'price_subtotal'])
    mnt_amount = 0
    for line in lines:
        if line.get('product_id') and line.get('product_id')[0] == MAINTENANCE_ADJUSTMENT or \
           line.get('product_id')[0] in MAINTENANCE_PRODUCTS or 'Customized' in line.get('product_id')[1]:
            mnt_amount += line.get('price_subtotal')

    return mnt_amount > 0


def create_parent_task(sub, task, prefix, tag_ids):
    target_version = db_version = db_hosting = "X"
    if sub.get('database_count') and sub.get('database_count') == 1:
        db = oxr.search('openerp.enterprise.database', [('subscription_id', '=', sub.get('id'))], ['version', 'hosting'])
        db_version = db.get('version') and db.get('version').replace("+e", "")
        db_hosting = db.get('hosting') and db.get('hosting').replace("paas", "sh")

    partner_name = sub.get('partner_id')[1] if sub.get('partner_id')[1] else False
    if sub.get('enterprise_final_customer_id'):
        partner = oxr.search_read('res.partner', [('id', '=', sub.get('enterprise_final_customer_id')[0])], ['commercial_partner_id'])
        partner_name = partner.get('commercial_partner_id')[1] if partner.get('commercial_partner_id')[1] else partner_name

    return oxr.create('project.task', {
        'name': "[UP] %s [%s->%s] (%s)" % (partner_name, db_version, target_version, db_hosting),
        'partner_id': task.get('partner_id')[0] if task.get('partner_id') else False,
        'mnt_subscription_id': task.mnt_subscription_id.id,
        'project_id': UPGRADE_PROJECT,
        'stage_id': STAGES.get(prefix) or STAGES.get('STANDARD'),
        'user_id': False,
        'reviewer_id': False,
        'tag_ids': tag_ids,
        'description': "(Upgrade Task automatically created to group Upgrade Issues together as Subtasks)",
    })


tasks = oxr.search_read('project.task',
                        [('project_id', 'in', UPGRADE_ISSUES_PROJECTS), ('stage_id', 'not in', EXCLUDED_STAGES),
                         ('create_date', '>', DATE), ('id', 'not in', EXCLUDED_TASKS), ('mnt_subscription_id', '!=', False)],
                         ["partner_id", 'mnt_subscription_id', "description", 'project_id', 'user_id', 'reviewer_id', 'parent_id'])
print(len(tasks))

for task in tasks:
    print("TASK #", task.get('id'))
    if not task.get('mnt_subscription_id'):
        continue

    prefix = False
    tag_ids = []
    vals = {}
    sub = oxr.search_read('sale.subscription', [('id', '=', task.get('mnt_subscription_id')[0])],
                          ['recurring_invoice_line_ids', 'team_id', 'maintenance_subscription_id',
                           'database_count', 'enterprise_final_customer_id', 'partner_id'])[0]

    # ADD TAGS (TODO HELP AND UPGRADE)
    if has_maintenance(sub):
        team = sub.get('team_id')[1] if sub.get('team_id') else "No Team"
        partner = task.get('partner_id')[1] if task.get('partner_id') else "No Customer"
        print("Maintenance on task %s for customer %s. %s" % (task.get('id'), partner, team))

        tag_ids = [(4, TAGS.get('MAINTENANCE'))]
        if sub.get('team_id'):
            for prefix in PREFIX:
                if sub.get('team_id')[1].startswith(prefix):
                    tag_ids.append((4, TAGS.get(prefix)))
                    break
            vals['tag_ids'] = tag_ids

    if task.get('project_id') and task.get('project_id')[0] in UPGRADE_ISSUES_PROJECTS:
        # MOVE TO THE RIGHT PROJECT (UPGRADE ONLY)
        if not task.get('user_id') and prefix in PROJECTS:
            vals['company_id'] = PROJECTS.get(prefix[1])
            vals['project_id'] = PROJECTS.get(prefix[0])
            print("Task %s will be moved into project %s" % (task.get('id'), PROJECTS.get(prefix[0])))

        # SET OR CREATE PARENT TASK (UPGRADE ONLY)
        upgrade_parent = oxr.search_read('project.task',
                                         [('project_id', '=', UPGRADE_PROJECT), ('id', '!=', task.get('id')),
                                          ('mnt_subscription_id', '=', task.get('mnt_subscription_id')[0]), ('stage_id', 'not in', EXCLUDED_STAGES)],
                                         ['user_id', 'reviewer_id'])
        print(upgrade_parent)
        if upgrade_parent and upgrade_parent != []:
            vals['user_id'] = task.get('user_id')[0] if task.get('user_id') else upgrade_parent[0].get('user_id')[0] if upgrade_parent[0].get('user_id') else False
            vals['reviewer_id'] = task.get('reviewer_id')[0] if task.get('reviewer_id') else upgrade_parent[0].get('reviewer_id')[0] if upgrade_parent[0].get('reviewer_id') else False
            vals['parent_id'] = task.get('parent_id')[0] if task.get('parent_id') else upgrade_parent[0].get('id')
        else:
            print("HERE")
            upgrade_parent = create_parent_task(sub, task, prefix, tag_ids)
            print(upgrade_parent)
            #vals['parent_id'] = upgrade_parent
            print("Create parent %s for task %s" % (upgrade_parent, task.get('id')))

    oxr.write('project.task', [task.get('id')], vals)
    print("--------------------------")
