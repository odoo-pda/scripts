import logging
import getpass
import sys

_logger = logging.getLogger(__name__)

try:
    import keyring
    from keyring.errors import KeyringLocked
except ImportError:
    _logger.warning('No password management possible: keyring library not found.')
    keyring = False

PM_TYPE = {
    'odoo':     'Odoo',
    'saas_log': 'Saas-log',
    'odoo-2fa': 'Odoo (2FA)',
}
USER_INPUT_PROMPT = 'Username:'
PASSWORD_INPUT_PROMPT = 'Password:'
APIKEY_INPUT_PROMPT = 'API Key:'
INFO_LOG = 'See ./oe-support.py --help to know how to save the username'
KEYRING_SERVICE_NAME = 'oe-support'


class OePassword:
    _type = 'odoo'

    _user = ''

    @property
    def user(self):
        if not self._user:
            self._user = self._prompt_user()
        return self._user

    @user.setter
    def user(self, value):
        self._user = value

    @property
    def password(self):
        return self._retrieve_password()

    @password.setter
    def password(self, value):
        self._save_password(value, force=True)

    @property
    def magic_password(self):
        return f'{self._user}/{self.password}'

    def remove(self):
        self._delete_password()

    def __init__(self, user: str = None, pm_type: str = 'odoo', password: str = None) -> None:
        """
        :param user: user's name
        :type user: str

        :param pm_type: Optional. Type of manager. Should be in ['odoo', 'saas_log', 'odoo-2fa']
                        Default is 'odoo'
        :type pm_type: str
        :param password: Optional. Password to save without confirmation.
        :type password: str
        """
        if pm_type not in PM_TYPE:
            logging.error(f'Password Manager type incorrect. ({pm_type} - Should be in {PM_TYPE.keys()}')
            sys.exit(1)

        self._type = pm_type
        self._user = user

        if password:
            self._save_password(password, force=True)

    def _prompt_password(self) -> str:
        """
        Let the user input his password

        :return: str
        """
        input_prompt = APIKEY_INPUT_PROMPT if self._type == 'odoo-2fa' else PASSWORD_INPUT_PROMPT
        return getpass.getpass(f"{PM_TYPE[self._type]} {input_prompt}")

    def _prompt_user(self) -> str:
        """
        Let the user input his name

        :return: str
        """
        user = input(f"{PM_TYPE[self._type]} {USER_INPUT_PROMPT}")
        _logger.info(INFO_LOG)
        return user

    def _retrieve_password(self) -> str:
        """
        Retrieve the password from the keyring
        or prompt the user if it is not available
        If needed, store the password in the keyring

        :return: str
        """

        result = ''
        if keyring:
            try:
                result = keyring.get_password(KEYRING_SERVICE_NAME, self._user)
            except KeyringLocked:
                # This exception can occur when cancelling a KWallet dialog, for example
                # because you don't want to use it but the GNOME keyring instead. If
                # `keyring` can't find the password in the GNOME keyring, it will try
                # KWallet next if you have it installed, resulting in the dialog.
                pass

        if not result:
            result = self._prompt_password()
            if result and keyring:
                self._save_password(result)
        return result

    def _save_password(self, value: str, force: bool = False) -> None:
        """
        Ask the user if the password should be saved
        Save the user password

        :param value: The password string
        :type value: str
        :param force: Optional. Save the password without asking for confirmation
               Default is None
        :type force: bool
        """

        result = 'y' if force else ''
        while result not in ['y', 'n']:
            word, name = ('API key', self._user.replace('-2FA', '')) if self._type == 'odoo-2fa' else ('password', self._user)
            result = input(f'Save the {word} for user {name}? [Y,n]: ').lower() or 'y'
        if result == 'y':
            keyring.set_password(KEYRING_SERVICE_NAME, self._user, value)

    def _delete_password(self) -> None:
        """
        Delete the saved password for the user
        """
        try:
            keyring.delete_password(KEYRING_SERVICE_NAME, self._user)
        except keyring.errors.PasswordDeleteError:
            pass
