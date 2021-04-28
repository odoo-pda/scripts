#!/usr/bin/env python3
import logging
import uuid
import subprocess
import psycopg2

_logger = logging.getLogger(__name__)


def check_table_exists(db, table, column=None):
    with psycopg2.connect("dbname='%s'" % db) as con, con.cursor() as cursor:
        query_args = (db, table) if not column else (db, table, column)
        cursor.execute(
            """
                SELECT EXISTS(SELECT 1 FROM information_schema.columns
                    WHERE table_catalog=%%s AND table_schema='public'
                    AND table_name=%%s %s);
            """
            % ("AND column_name = %s" if column else ""),
            query_args,
        )
        return cursor.fetchone()[0]


def _neuter_essentials(db):
    """
    Returns an SQL query that: Deactivate mail servers, crons, external integration
    and other odoo features that could cause issue to the end user if they are not properlly deactivated.
    These are the changes that are done on test duplicate on odoosh and the saas
    """
    _logger.info("Disabling crons, iap services, oauth and mail servers, etc...")
    new_uuid = str(uuid.uuid4())
    # Generic neutering - start query building
    query = (
        "UPDATE ir_cron SET active=false;"
        "UPDATE ir_mail_server SET active=false;"
        "UPDATE ir_config_parameter SET value = '2042-01-01 00:00:00' WHERE key = 'database.expiration_date';"
        "UPDATE ir_config_parameter SET value = '" + new_uuid + "' WHERE key = 'database.uuid';"
        "DELETE FROM ir_attachment WHERE name like '/web/content/%assets_%';"
        """
                INSERT INTO ir_config_parameter(key, value)
                VALUES ('iap.endpoint', 'https://iap-sandbox.odoo.com')
                ON CONFLICT (key) DO UPDATE SET
                    value = 'https://iap-sandbox.odoo.com';
             """
        "UPDATE ir_config_parameter SET value = 'https://iap-services-test.odoo.com' WHERE key = 'snailmail.endpoint';"
        "UPDATE ir_config_parameter SET value = 'https://iap-services-test.odoo.com' WHERE key = 'reveal.endpoint';"
        "UPDATE ir_config_parameter SET value = 'https://iap-services-test.odoo.com' WHERE key = 'iap.partner_autocomplete.endpoint';"
        "UPDATE ir_config_parameter SET value = 'https://iap-services-test.odoo.com' WHERE key = 'sms.endpoint';"
        "DELETE FROM ir_config_parameter WHERE key='ocn.ocn_push_notification' OR key='odoo_ocn.project_id' OR key='ocn.uuid';"
        "DELETE FROM ir_config_parameter WHERE key='web_map.token_map_box';"
    )
    # Delete domains on websites
    if check_table_exists(db, "website", "domain"):
        query += "UPDATE website SET domain = null;"
    elif check_table_exists(db, "website"):
        logging.warning(
            "UNABLE TO DELETE WEBSITE DOMAINS. MAKE SURE YOU HAVE NOT BEEN REDIRECTED TO THE PROD WHEN DOING WEBSITE RELATED ACTIONS"
        )
    # Neuter Oauth providers
    if check_table_exists(db, "auth_oauth_provider", "enabled"):
        query += "UPDATE auth_oauth_provider SET enabled = false;"
    elif check_table_exists(db, "auth_oauth_provider"):
        _logger.warning(
            "UNABLE TO DISABLE OAUTH PROVIDERS. DOUBLE-CHECK WHY IF YOU NEED SOMETHING IMPLYING OAUTH PROVIDERS"
        )
    # Neuter delivery carriers
    if check_table_exists(db, "delivery_carrier"):
        # prod_environment column was introduced in V10 so it might not exist for (very) old databases
        if check_table_exists(db, "payment_acquirer", "prod_environment"):
            query += "UPDATE delivery_carrier set active='f', prod_environment='f';"
        elif check_table_exists(db, "delivery_carrier", "active"):
            query += "UPDATE delivery_carrier set active='f';"
        else:
            _logger.warning(
                "UNABLE TO DISABLE DELIVERY CARRIERS. DOUBLE-CHECK WHY IF YOU NEED SOMETHING IMPLYING DELIVERY CARRIERS"
            )
    # Set payment acquirers to test modus
    if check_table_exists(db, "payment_acquirer"):
        if check_table_exists(db, "payment_acquirer", "environment"):
            # pre v13
            query += "UPDATE payment_acquirer set environment='test';"
        elif check_table_exists(db, "payment_acquirer", "state"):
            # v13 and later
            query += "UPDATE payment_acquirer set state='test' where state not in  ('test', 'disabled');"
        else:
            _logger.warning(
                "UNABLE TO DISABLE PAYMENT ACQUIRERS. DOUBLE-CHECK WHY IF YOU NEED SOMETHING IMPLYING PAYMENT ACQUIRERS"
            )
        # remove all credentials from all standard payment acquirer as a safety measure
        payment_acquirer_credential_columns = [
            "adyen_merchant_account",
            "adyen_skin_code",
            "adyen_skin_hmac_key",
            "alipay_merchant_partner_id",
            "alipay_md5_signature_key",
            "alipay_seller_email",
            "authorize_login",
            "authorize_transaction_key",
            "authorize_signature_key",
            "authorize_client_key",
            "brq_websitekey",
            "brq_secretkey",
            "ogone_pspid",
            "ogone_userid",
            "ogone_password",
            "ogone_shakey_in",
            "ogone_shakey_out",
            "paypal_email_account",
            "paypal_seller_account",
            "paypal_pdt_token",
            "payulatam_merchant_id",
            "payulatam_account_id",
            "payulatam_api_key",
            "payumoney_merchant_key",
            "payumoney_merchant_salt",
            "sips_merchant_id",
            "sips_secret",
            "stripe_secret_key",
            "stripe_publishable_key",
        ]
        for column in payment_acquirer_credential_columns:
            if check_table_exists(db, "payment_acquirer", column):
                query += "UPDATE payment_acquirer SET %s = 'dummy';" % column
    # Neuter Plaid
    if check_table_exists(db, "account_online_provider", "provider_account_identifier"):
        query += (
            "UPDATE account_online_provider SET provider_account_identifier = NULL;"
        )
    elif check_table_exists(db, "account_online_provider"):
        _logger.warning(
            "UNABLE TO DISABLE PLAID. DOUBLE-CHECK WHY IF YOU NEED SOMETHING IMPLYING PLAID"
        )
    # Neuter Yodlee
    yodlee_columns = [
        "yodlee_access_token",
        "yodlee_user_password",
        "yodlee_user_access_token",
    ]
    yodlee_columns = [
        check_table_exists(db, "res_company", column_name)
        for column_name in yodlee_columns
    ]
    if all(yodlee_columns):
        query += "UPDATE res_company SET yodlee_access_token = NULL, yodlee_user_password = NULL, yodlee_user_access_token = NULL;"
    elif any(yodlee_columns):
        _logger.warning(
            "UNABLE TO DISABLE YODLEE. NOT ALL EXPECTED COLUMNS ARE PRESENT. DOUBLE-CHECK WHY IF YOU NEED SOMETHING IMPLYING YODLEE"
        )
    # Neuter Mexican Accounting SAT connection
    if check_table_exists(db, "res_company", "l10n_mx_edi_pac_test_env"):
        query += "UPDATE res_company SET l10n_mx_edi_pac_test_env = true;"
    elif check_table_exists(db, "l10n_mx_edi_certificate"):
        _logger.warning(
            "UNABLE TO DISABLE PAC CONNECTION (MEXICAN ACCOUNTING). DOUBLE-CHECK WHY IF YOU NEED SOMETHING IMPLYING MEXICAN ACCOUNTING"
        )
    # Neuter Colombian Accounting edi connection
    if check_table_exists(db, "res_company", "l10n_co_edi_test_mode"):
        query += "UPDATE res_company SET l10n_co_edi_test_mode = true;"
    elif check_table_exists(db, "l10n_co_edi_type_code"):
        _logger.warning(
            "UNABLE TO DISABLE EDI CONNECTION (COLOMBIAN ACCOUNTING). DOUBLE-CHECK WHY IF YOU NEED SOMETHING IMPLYING COLUMBIAN ACCOUNTING"
        )
    # Neuter Argentinian Accounting afip connection
    if check_table_exists(
        db, "res_company", "l10n_ar_afip_ws_environment"
    ) and check_table_exists(db, "l10n_ar_afipws_connection", "type"):
        query += "UPDATE res_company SET l10n_ar_afip_ws_environment = 'testing';"
        query += "DELETE FROM ir_attachment WHERE res_model = 'res.company' and res_field in ('l10n_ar_afip_ws_crt', 'l10n_ar_afip_ws_key');"
    elif check_table_exists(db, "l10n_ar_afipws_connection"):
        _logger.warning(
            "UNABLE TO DISABLE AFIP CONNECTION (ARGENTINIAN ACCOUNTING). DOUBLE-CHECK WHY IF YOU NEED SOMETHING IMPLYING ARGENTINIAN ACCOUNTING"
        )
    # Neuter VOIP
    query += "update ir_config_parameter set value = 'demo' where key = 'voip.mode';"
    if check_table_exists(db, "res_config_settings", "mode"):
        query += "update res_config_settings set mode = 'demo';"
    elif check_table_exists(db, "voip_configurator"):
        _logger.warning(
            "UNABLE TO DISABLE THE VOIP. MAKE SURE YOU DON'T ANSWER THE PHONE!"
        )
    if check_table_exists(db, "res_users", "onsip_auth_user"):
        query += "update res_users set onsip_auth_user = 'dummy';"
    # Neuter custom mail servers on mail templates
    if check_table_exists(db, "mail_template", "mail_server_id"):
        query += "UPDATE mail_template SET mail_server_id=null;"
    elif check_table_exists(db, "mail_template"):
        _logger.warning(
            "UNABLE TO DISABLE CUSTOM MAIL SERVER ON MAIL TEMPLATES. DOUBLE-CHECK WHY IF YOU NEED TO SEND TEST MAILS"
        )
    # Neuter Two-Factor Authentification
    if check_table_exists(db, "res_users", "totp_secret"):
        query += "update res_users set totp_secret = NULL;"

    # Neuter Taxcloud Credentials
    if check_table_exists(db, "res_company", "taxcloud_api_id"):
        query += "update res_company set taxcloud_api_id = NULL, taxcloud_api_key = NULL;"

    return query


def _neuter_support_QOL(db):
    """
    Returns an SQL query that: Apply changes that are not strictly necessary for the safety of the end user,
    but are nice to have for the support
    """
    _logger.info(
        "You may use mailcatcher for outgoing emails."
        "You may use logins as passwords for all users."
    )
    # Generic neutering - start query building
    query = (
        "INSERT INTO ir_mail_server(active,name,smtp_host,smtp_port,smtp_encryption) VALUES (true,'mailcatcher','localhost',1025,false);"
        """
                UPDATE res_users SET login='admin'
                    WHERE id IN (
                                SELECT COALESCE (
                                    (SELECT MIN(r.uid)
                                    FROM res_groups_users_rel r
                                    JOIN res_users u ON r.uid = u.id
                                    WHERE u.active
                                    AND r.gid = (SELECT res_id
                                        FROM ir_model_data
                                        WHERE module = 'base'
                                        AND name = 'group_system'))
                                ,1)
                    ) AND NOT EXISTS (SELECT 1 FROM res_users WHERE login='admin');
             """
        "UPDATE res_users SET password=login;"
    )
    # Update website domains using localhost range
    # First website (the one with the smallest id) will be on 127.0.0.1
    # Second website (the second with the smallest id) will be on 127.0.0.2
    # and so on until 127.255.255.255
    if check_table_exists(db, "website", "domain"):
        # Note that it will overflow if there is more than (256^3 - 1) websites
        query += """
        WITH website_n AS (
            SELECT id, row_number() over () as n
            FROM website
            order by id
        )
        UPDATE website
        SET domain = '127.' || (website_n.n / (256*256)) % 256 ||'.'|| (website_n.n / 256) % 256 ||'.'|| website_n.n % 256
        FROM website_n
        WHERE website_n.id = website.id;"""
    return query


def neuter(db, minimal_neuter=False):
    """Render a db inoffensive by deactivating crons, mail servers and setting local passwords."""

    query = _neuter_essentials(db)
    if not minimal_neuter:
        query += _neuter_support_QOL(db)

    cmd = ["psql", "-d", db, "-c", query]
    subprocess.check_output(cmd)
    return True


if __name__ == "__main__":
    from docopt import docopt

    arguments_definition = """
    Usage:
        neuter <database> [--minimal]

    Options:
        --minimal                   Do not apply the Quality Of Life changes that only make sense for support
    """
    opt = docopt(arguments_definition)
    neuter(opt.get("<database>"), opt.get("--minimal"))
