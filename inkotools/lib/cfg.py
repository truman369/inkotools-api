#!/usr/bin/env python3
# lib/cfg.py

# internal imports
import collections.abc
import logging
import logging.config
import pathlib

# external imports
import netaddr
import yaml
from cryptography.fernet import Fernet

# module logger
log = logging.getLogger(__name__)

# app root path is relative to lib
ROOT_DIR = pathlib.Path(__file__).parents[1]


def cfg_file(cfg_name, default=False):
    sub = 'default' if default else 'user'
    return (ROOT_DIR/'config'/sub).joinpath(cfg_name).with_suffix('.yml')


def load_yml(file):
    """Load dict from yml file"""
    try:
        result = yaml.safe_load(file.read_text())
    except FileNotFoundError:
        return {}
    except Exception as e:
        log.error(f'{file.name}: {e}')
        return None
    else:
        return result


def dict_merge(orig, upd):
    """Recursive dict update"""
    for key, val in upd.items():
        if isinstance(val, collections.abc.Mapping):
            orig[key] = dict_merge(orig.get(key, {}), val)
        else:
            orig[key] = val
    return orig


def load_cfg(cfg_name, force_default=False):
    """Load configuration"""
    # first, load from default
    res_default = load_yml(cfg_file(cfg_name, default=True))
    if force_default:
        return res_default
    # load user config and merge
    res_user = load_yml(cfg_file(cfg_name))
    result = dict_merge(res_default, res_user)
    if not result:
        log.error(f'{cfg_name} failed')
    else:
        log.debug(f'{cfg_name} loaded')
    return result


def write_cfg(cfg_name, data={}):
    """Save cfg to yml file"""
    log.debug(f'Got data: {data}')
    conf = cfg_file(cfg_name)
    try:
        conf.write_text('---\n' + yaml.safe_dump(data) + '...\n')
    except Exception as e:
        log.error(f'{cfg_name} failed: {e}')
    else:
        log.debug(f'{cfg_name} saved')


# load global logger settings
try:
    logging.config.dictConfig(load_cfg('logger'))
except Exception as e:
    logging.config.dictConfig(load_cfg('logger', force_default=True))
    log.error(f'User config caused error: {e}, default cfg file loaded')

# credetials
SECRETS = load_cfg('secrets')

# generate new secret key on first run
if 'secret_key' not in SECRETS.keys():
    log.warning('Generating new secret key')
    SECRETS['secret_key'] = Fernet.generate_key().decode()
    write_cfg('secrets', SECRETS)


# common settings
COMMON = load_cfg('common')

# calculate possible net ranges for switches
NETS = netaddr.IPSet()
for net in COMMON['NETS']:
    NETS.add(netaddr.IPRange(net['start'], net['end']))

# PIP networks
PIP_NETS = list(map(netaddr.IPNetwork, COMMON['PIP_NETS']))
