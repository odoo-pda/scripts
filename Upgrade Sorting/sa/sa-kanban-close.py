 ####NEXT SHOULD GO INTO ANOTHER SA (automated, every day?). Cause doesn't apply only on selected records.


        #4 ADAPT KANBAN STATE OF PARENT
        upgrades = env['project.task'].search([('project_id', '=', UPGRADE_PROJECT), ('stage_id', 'not in', EXCLUDED_STAGES)])
        excluded_stages = env['project.task.type'].search(['|', ('name', 'ilike', 'Cancel'), ('name', 'ilike', 'Done')])

        for upgrade in upgrades:
            subtasks = env['project.task'].search([('parent_id', '=', upgrade.id), ('stage_id', 'not in', excluded_stages.ids)])
            #Green (done) : Opened subtasks, Red (blocked): No opened subtasks
            upgrade['kanban_state'] = 'done'  if subtasks else 'blocked'

            #5 CLOSE PARENT TASK WHEN UPGRADED TODO
            # if upgrade.kanban_state == 'blocked':
            #     #Compare target version in task's name ([current->target]), exclude "X" target == sub.database_ids.version.replace("+e", "")? Then Close.



        # TODO in script : update create date of parent task as create date of first opened ticket for the customer
        # TODO Complete projects : US? DU? LU?
        # INFO Not covered : Client without a subscription -> Filter by Subscription field not set
