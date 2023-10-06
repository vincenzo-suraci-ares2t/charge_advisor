"""Representation of a OCCP Entities."""

# ----------------------------------------------------------------------------------------------------------------------
# Python packages
# ----------------------------------------------------------------------------------------------------------------------

from __future__ import annotations
import asyncio
from threading import Thread

# ----------------------------------------------------------------------------------------------------------------------
# External packages
# ----------------------------------------------------------------------------------------------------------------------

# Su PyCharm andare su Python Packages, Add Package e inserire la seguente stringa:
# https://<USERNAME>@bitbucket.org/ares2t/ocpp-central-system.git@master#ocpp-central-system
# from ocpp_central_system.logger import OcppLog
# from ocpp_central_system.charging_station_management_system import ChargingStationManagementSystem

# ----------------------------------------------------------------------------------------------------------------------
# Home Assistant packages
# ----------------------------------------------------------------------------------------------------------------------

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import STATE_OK
from homeassistant.helpers import device_registry




# ----------------------------------------------------------------------------------------------------------------------
# Local packages
# ----------------------------------------------------------------------------------------------------------------------

from ocpp_central_system.charging_station_management_system import ChargingStationManagementSystem

# ----------------------------------------------------------------------------------------------------------------------
# Local files
# ----------------------------------------------------------------------------------------------------------------------

from .metric import HomeAssistantEntityMetrics
from .charge_point import HomeAssistantChargePoint
from .const import *
from .enums import HAChargePointServices
from .logger import OcppLog
from .config import *



class HomeAssistantCentralSystem(ChargingStationManagementSystem, HomeAssistantEntityMetrics):
    
    """Home Assistant representation of a Central System """

    def __init__(
            self,
            hass: HomeAssistant,
            config_entry: ConfigEntry
    ):
        """Instantiate instance of a CentralSystem."""

        """ Home Assistant inizialization """
        self._hass = hass
        self._config_entry = config_entry
        self._adding_entities = False
        self._updating_entities = False
        self.ha_entity_unique_ids: list[str] = []
        self._status = STATE_OK

        """ Central Station Management System inizialization """
        ChargingStationManagementSystem.__init__(self)

        """ Home Assistant Entity Metrics inizialization """
        HomeAssistantEntityMetrics.__init__(self)

    def _get_init_skip_schema_validation(self):
        return self._config_entry.data.get(
            CONF_SKIP_SCHEMA_VALIDATION,
            super()._get_init_skip_schema_validation()
        )

    def _get_default_load_area_id(self):
        return self._hass.config.as_dict().get(
            "location_name",
            super()._get_default_load_area_id()
        )

    def _get_default_event_loop(self):
        return self._hass.loop

    def _get_init_ssl(self):
        return self._config_entry.data.get(
            CONF_SSL,
            super()._get_init_ssl()
        )

    def _get_init_host(self):
        return self._config_entry.data.get(
            CONF_HOST,
            super()._get_init_host()
        )

    def _get_init_port(self):
        return self._config_entry.data.get(
            CONF_PORT,
            super()._get_init_port()
        )

    def _get_init_id(self):
        return self._config_entry.data.get(
            CONF_CSID,
            super()._get_init_id()
        )

    def _get_init_websocket_close_timeout(self):
        return self._config_entry.data.get(
            CONF_WEBSOCKET_CLOSE_TIMEOUT,
            super()._get_init_websocket_close_timeout()
        )

    def _get_init_websocket_ping_tries(self):
        return self._config_entry.data.get(
            CONF_WEBSOCKET_PING_TRIES,
            super()._get_init_websocket_ping_tries()
        )

    def _get_init_websocket_ping_interval(self):
        return self._config_entry.data.get(
            CONF_WEBSOCKET_PING_INTERVAL,
            super()._get_init_websocket_ping_interval()
        )

    def _get_init_websocket_ping_timeout(self):
        return self._config_entry.data.get(
            CONF_WEBSOCKET_PING_TIMEOUT,
            super()._get_init_websocket_ping_timeout()
        )

    def _get_init_subprotocols(self):
        return self._config_entry.data.get(
            CONF_SUBPROTOCOLS,
            super()._get_init_subprotocols()
        )

    #def _start_pusher_communication_handler(self):
    #    self._pusher_communication_handler = CentralSystemCommunicationChannel(self._hass, self)
    #    self._pusher_communication_handler.start()

    @property
    def hass(self):
        return self._hass

    def is_available(self):
        return self._status == STATE_OK

    @staticmethod
    async def get_instance(params = {}):
        hass = params.get("hass")
        entry = params.get("entry")
        return HomeAssistantCentralSystem(hass, entry)

    def async_create_notify_end_of_charge_task(self, data):
        self._hass.async_create_task(
            self._charge_advisor_handler.notify_end_of_charge(data)
        )

    def async_create_notify_start_of_charge_task(self, data):
        self._hass.async_create_task(
            self._charge_advisor_handler.notify_start_of_charge(data)
        )

    def async_create_notify_new_cp_status_task(self, data):
        self._hass.async_create_task(
            self._charge_advisor_handler.notify_new_cp_status(data)
        )

    def async_create_remote_start_transaction_task(self, charge_point, connector_id, id_tag: str | None = None):
        return self._hass.async_create_task(
            charge_point.remote_start_transaction(
                connector_id,
                id_tag
            )
        )

    def async_create_remote_stop_transaction_task(self, charge_point, transaction_id):
        self._hass.async_create_task(
            charge_point.remote_stop_transaction(
                transaction_id
            )
        )

    def async_create_set_max_charge_rate_task(self, conn, limit_list, start_of_schedule):
        self._hass.async_create_task(
            conn.set_max_charge_rate(
                limit_list=limit_list,
                start_of_schedule=start_of_schedule
            )
        )

    # Aggiornamento del 08/02/2023
    # Questa funzione vale a livello d'intera integrazione. Viene chiamata per assicurare che tutte le entità della
    # integrazione vengano aggiunte in Home Assistant per ogni piattaforma: sensor, switch, button o number.
    # Quando viene chiamata la funzione, per ogni piattaforma di Home Assistant supportata dalla integrazione, vengono:
    # a) eliminate TUTTE le entità (funzione "async_forward_entry_unload");
    # b) aggiunte TUTTE le entità (funzione "async_forward_entry_setup").
    # È compito di ogni piattaforma, nel proprio corrispettivo file (sensor.py, switch.py, ecc.) gestire la aggiunta
    # delle entità in base allo stato del sistema (Charge Point e Connector connessi) nela funzione "async_setup_entry"
    async def add_ha_entities(self):

        # Aggiornamento del 08/02/2023
        # Ho aggiunto questo check, nel caso in cui differenti Charge Point richiamino contemporaneamente questa
        # funzione. Nel caso in cui ciò avvenga, le chiamate avvengono in maniera sequenziale
        while self._adding_entities or self._updating_entities:
            await asyncio.sleep(1)

        self._adding_entities = True

        # OcppLog.log_d(f"Removing and adding all platforms' entities (called by {id})...")

        for platform in PLATFORMS:

            await self._hass.config_entries.async_forward_entry_unload(
                self._config_entry, platform
            )

            await self._hass.config_entries.async_forward_entry_setup(
                self._config_entry, platform
            )

        self._adding_entities = False

        # OcppLog.log_d(f"Removed and added all platforms' entities (called by {id})")

    async def get_charge_point_instance(self, cp_id, websocket):
        # Create an instance of HomeAssistantChargePoint class
        hacp = HomeAssistantChargePoint(
            cp_id,
            websocket,
            self._hass,
            self._config_entry,
            self
        )

        # Create Charge Point Device in Home Assistant
        ha_dr = device_registry.async_get(self._hass)
        ha_dr.async_get_or_create(
            config_entry_id=self._config_entry.entry_id,
            identifiers={(DOMAIN, cp_id)},
            name=cp_id,
            default_model="OCPP Charge Point",
            via_device=(DOMAIN, self._id),
        )

        return hacp

    async def call_ha_service(
            self,
            service_name: str,
            state: bool = True,
    ):
        OcppLog.log_d(f"Calling service {service_name}")
        resp = False
        match service_name:
            case HAChargePointServices.service_ems_communication_start.name:
                resp = await self.start_ems_communication()
            case HAChargePointServices.service_ems_communication_stop.name:
                resp = await self.stop_ems_communication()
            case _:
                OcppLog.log_d(f"{service_name} unknown")
        return resp

    async def start_ems_communication(self):

        if self._charge_advisor_thread_rest_api is None:

            self._charge_advisor_thread_rest_api = Thread(
                target=self._start_charge_advisor_handler_rest_api
            )

            self._charge_advisor_thread_rest_api.start()
            self._charge_advisor_thread_rest_api = None
        else:
            self._charge_advisor_handler.stop_api_client()
            self._charge_advisor_thread_rest_api = None

            OcppLog.log_w("Il Thread for the API client is already in execution")
            OcppLog.log_w("Stopping old one ...")
            return True


        if self._charge_advisor_thread_websocket is None:
            self._charge_advisor_thread_websocket = Thread(
                target=self._start_charge_advisor_handler_websocket
            )
            self._charge_advisor_thread_websocket.start()
        else:
            OcppLog.log_w("Il Thread for Websocket communication is already in execution")
            OcppLog.log_w("Stopping old one ...")
            self._charge_advisor_handler.stop_websocket_client()
            self._charge_advisor_thread_websocket = None

            return True

        self.set_metric_value(HAChargePointServices.service_ems_communication_start.value, True)

        return True

    async def stop_ems_communication(self):

        self._charge_advisor_handler.stop_api_client()
        self._charge_advisor_handler.stop_websocket_client()

        self._charge_advisor_thread_rest_api = None
        self._charge_advisor_thread_websocket = None

        self.set_metric_value(HAChargePointServices.service_ems_communication_start.value, False)


        return True

