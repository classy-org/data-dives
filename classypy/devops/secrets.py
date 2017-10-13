import os

from ..util.dirs import caller_dir

REGION_MAP = {
    'prod': 'us-east-1',
    'staging': 'us-west-2', }


class Secrets(dict):
    """Class that facilitates hiding the printing of secrets."""
    def __repr__(self):
        return '<%s.%s object at %s>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            hex(id(self))
        )


def _key_prefix(key):
    """Return the string before the first '_'."""
    return key.split('_')[0]


def write_dotenv(env_file, secrets, section_split=""):
    """Create a (sectioned) dotenv file from a secrets dict."""
    keys = secrets.keys()
    if section_split:
        keys = sorted(keys)

    with open(env_file, 'w') as fp:
        prev_prefix = ''
        for key in keys:
            if _key_prefix(key) != prev_prefix:
                prev_prefix = _key_prefix(key)
                if prev_prefix:
                    fp.write(section_split)
            fp.write("%s = %s\n" % (key, secrets[key]))


def filter_dict(d, allowed_keys):
    return {k: v for k, v in d.items()
            if allowed_keys is None or k in allowed_keys}


def find_dotenv(search_path):
    import dotenv

    cur_path = os.getcwd()
    env_file = None
    try:
        os.chdir(search_path)
        env_file = dotenv.find_dotenv(usecwd=True)
    finally:
        os.chdir(cur_path)
    return env_file


def _region_from_credstash_tablename(credstash_table):
    env = credstash_table.split('-')[0]
    return REGION_MAP.get(env)


def find_secrets(env_file=None, credstash_table=None, allowed_keys=None,
                 region=None, verbose=1):
    secrets = Secrets()  # unprintable dict

    # Fill with credstash secrets
    if credstash_table:
        import credstash
        region = region or _region_from_credstash_tablename(credstash_table)
        if verbose > 0:
            print("Fetching secrets from {table}...".format(table=credstash_table))
        new_secrets = credstash.getAllSecrets(table=credstash_table, region=region)
        new_secrets = filter_dict(new_secrets, allowed_keys=allowed_keys)
        secrets.update(new_secrets)

    # Fill with local/.env secrets (override remote)
    env_file = env_file or find_dotenv(search_path=caller_dir(frames_above=1))
    if env_file:
        import dotenv
        dotenv.load_dotenv(env_file, verbose=verbose > 0, override=True)
        new_secrets = filter_dict(os.environ, allowed_keys=allowed_keys)
        secrets.update(new_secrets)

    return secrets
