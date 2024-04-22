"""Charge Advisor integration for Charging Stations that support the Open Charge Point Protocol v1.6 or v2.0.1"""
# ----------------------------------------------------------------------------------------------------------------------
# Python packages
# ----------------------------------------------------------------------------------------------------------------------

import asyncio
import logging
import subprocess
import platform
from distutils.version import LooseVersion

# ----------------------------------------------------------------------------------------------------------------------
# Importing dinamico del package ocpp-central-system
# ----------------------------------------------------------------------------------------------------------------------
from .config import *
if INTEGRATION_TYPE == INTEGRATION_TYPE_PROD:
    # ------------------------------------------------------------------------------------------------------------------
    # PRODUCTION
    # ------------------------------------------------------------------------------------------------------------------
    args = [
        "apk add --update --no-cache --virtual .tmp-build-deps gcc libc-dev linux-headers postgresql-dev",
        "apk add libffi-dev"
    ]
    sub_proc = subprocess.run(
        args=args,
        shell=True,
        capture_output=True
    )
    if sub_proc.returncode == 0:
        logging.info(sub_proc)
    else:
        logging.error(sub_proc)
    # Installazione del package ocpp_central_system da bitbucket con chiave privata
    # Path assoluto alla chiave per accedere al repository di ocpp_central_system
    key_path = "/config/ssh-keys/ocpp-central-system-key"
    # Url al repository git (bitbucket) di ocpp_central_system
    package_url = "git+ssh://git@bitbucket.org/a2t-smartcity/ocpp-central-system.git"
    args = [
        "eval `ssh-agent -s` ",
        f"ssh-add {key_path}" +
        "ssh -o StrictHostKeyChecking=no -T git@bitbucket.org",
        f"pip install {package_url} --upgrade"
    ]
    sub_proc = subprocess.run(
        args=args,
        shell=True,
        capture_output=True
    )
    if sub_proc.returncode == 0:
        logging.info(sub_proc)
    else:
        logging.error(sub_proc)
elif INTEGRATION_TYPE == INTEGRATION_TYPE_DEV:
    # ------------------------------------------------------------------------------------------------------------------
    # DEVELOPER
    # ------------------------------------------------------------------------------------------------------------------
    # Aggiornamento del 08/04/2024
    # Dalla versione di python 3.12 il comando pip è deprecato e può dare questo errore:
    # AttributeError: module 'pkgutil' has no attribute 'ImpImporter'. Did you mean: 'zipimporter'?
    # La soluzione è descritta in questo articolo:
    # source: https://ubuntuhandbook.org/index.php/2023/10/fix-broken-pip-python-312-ubuntu/
    # Installazione del package da locale, modalità DEV
    pip_command = "pip"
    # Ottieni la versione corrente di Python
    versione_python = platform.python_version()
    # Confronta la versione corrente con 3.12
    if LooseVersion(versione_python) >= LooseVersion('3.12'):
        args = [
            "python3.12 -m ensurepip --upgrade"
        ]
        sub_proc = subprocess.run(
            args=args,
            shell=True,
            capture_output=True
        )
        if sub_proc.returncode == 0:
            logging.info(sub_proc)
            pip_command = "python3.12 -m pip"
        else:
            logging.error(sub_proc)
    local_package_name = "./custom_components/charge_advisor/ocpp_central_system"
    args = [
        f"{pip_command} install --upgrade --force-reinstall -e {local_package_name}"
    ]
    sub_proc = subprocess.run(
        args=args,
        shell=True,
        capture_output=True
    )
    if sub_proc.returncode == 0:
        logging.info(sub_proc)
    else:
        logging.error(sub_proc)
else:
    logging.error("Invalid INTEGRATION_TYPE: " + INTEGRATION_TYPE)

# ----------------------------------------------------------------------------------------------------------------------
# Home Assistant packages
# ----------------------------------------------------------------------------------------------------------------------

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant
from homeassistant.helpers import device_registry
import homeassistant.helpers.config_validation as cv

# ----------------------------------------------------------------------------------------------------------------------
# External packages
# ----------------------------------------------------------------------------------------------------------------------

# pip install voluptuous
import voluptuous as vol

from ocpp.v16.enums import AuthorizationStatus

# ----------------------------------------------------------------------------------------------------------------------
# Local packages
# ----------------------------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------------------------
# Local files
# ----------------------------------------------------------------------------------------------------------------------

from .ha_central_system import HomeAssistantCentralSystem
from .const import *


# ----------------------------------------------------------------------------------------------------------------------
# Home Assistant Voluptuous SCHEMAS
# ----------------------------------------------------------------------------------------------------------------------


# ----------------------------------------------------------------------------------------------------------------------
#Come usare il submodule ocpp_central_system
# 1) Scaricare la repository ocpp
# 2) Eseguire il comando git submodule add <url bitbucket>
# 3) Entrare nel submodule ed eseguire: git checkout master
# 4) Eseguire anche: git config core.filemode false
AUTH_LIST_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ID_TAG): cv.string,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_AUTH_STATUS): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_DEFAULT_AUTH_STATUS, default=AuthorizationStatus.accepted.value
        ): cv.string,
        vol.Optional(CONF_AUTH_LIST, default={}): vol.Schema(
            {cv.string: AUTH_LIST_SCHEMA}
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

# ----------------------------------------------------------------------------------------------------------------------
# Home Assistant Functions
# ----------------------------------------------------------------------------------------------------------------------

async def async_setup(hass: HomeAssistant, config: Config):

    """Read configuration from yaml."""

    ocpp_config = config.get(DOMAIN, {})
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN][CONFIG] = ocpp_config

    # OcppLog.log_d(f"Read configuration from yaml: {ocpp_config}")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):

    """Set up this integration from config entry."""

    # OcppLog.log_d("Integration setup from config entry")

    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})

    params = { "hass": hass, "entry":entry }
    cs = await HomeAssistantCentralSystem.create(params)

    dr = device_registry.async_get(hass)

    # Create Central System Device
    # source: https://developers.home-assistant.io/docs/device_registry_index/
    dr.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.data.get(CONF_CSID, DEFAULT_CSID))},
        name=entry.data.get(CONF_CSID, DEFAULT_CSID),
        model=DEFAULT_CENTRAL_SYSTEM_MODEL,
        manufacturer=DEFAULT_CENTRAL_SYSTEM_VENDOR
    )

    # Register Central System Device
    hass.data[DOMAIN][entry.entry_id] = cs

    for platform in PLATFORMS:
        await hass.config_entries.async_forward_entry_setup(
            entry, platform
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:

    """Handle removal of an entry."""

    # OcppLog.log_d("Central System entry removal")

    central_sys = hass.data[DOMAIN][entry.entry_id]

    central_sys.websocket_server.close()
    await central_sys.websocket_server.wait_closed()

    unloaded = True
    if len(central_sys.charge_points) > 0:
        unloaded = all(
            await asyncio.gather(
                *(
                    hass.config_entries.async_forward_entry_unload(entry, platform)
                    for platform in PLATFORMS
                )
            )
        )

    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:

    """Reload config entry."""

    # OcppLog.log_d("Reload config entry")

    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
