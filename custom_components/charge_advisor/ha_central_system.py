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

from .ha_metric import HomeAssistantEntityMetrics
from .ha_charge_point import HomeAssistantChargePoint
from .const import *
from .enums import HACentralSystemServices
from .logger import OcppLog
from .ha_charging_station_v201 import HomeAssistantChargingStationV201

class HomeAssistantCentralSystem(
    ChargingStationManagementSystem,
    HomeAssistantEntityMetrics
):
    
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

    # Questa funzione fa Overriding della funzione padre, per permette di personalizzare la Load Area Id
    # che deve restituire la Charging Station Management System (ovvero la Central System) al Charge Advisor Backend
    # In particolare, in Home Assistant viene restituita la stringa che viene imputata nella GUI andando nel menù in:
    # Impostazioni > Sistema > Generale, nella casella "Nome"
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

    @property
    def status(self):
        return self._status

    def is_available(self):
        return self.status == STATE_OK

    @staticmethod
    async def get_instance(params = {}):
        hass = params.get("hass")
        entry = params.get("entry")
        return HomeAssistantCentralSystem(hass, entry)

    def async_create_remote_start_transaction_task(
        self,
        charge_point,
        connector_id,
        evse_id=None,
        id_tag: str | None = None,
        parent_id_tag=None,
        reservation_id=None,
        expiry_date=None,
        session_params = None
    ):
        if evse_id is None:
            # ----------------------------------------------------------------------------------------------------------
            # Create a task to remotely start a transaction using OCPP 1.6.
            # ----------------------------------------------------------------------------------------------------------
            task = charge_point.remote_start_transaction(
                connector_id=connector_id,
                id_tag=id_tag,
                session_params=session_params
            )
        else:
            # ----------------------------------------------------------------------------------------------------------
            # Create a task to remotely start a transaction using OCPP 2.0.1.
            # ----------------------------------------------------------------------------------------------------------
            evse = charge_point.get_evse_by_id(evse_id)
            task = evse.remote_start_transaction(
                id_tag=id_tag,
                parent_id_tag=parent_id_tag,
                reservation_id=reservation_id,
                expiry_date=expiry_date,
                session_params=session_params
            )
        # ----------------------------------------------------------------------------------------------------------
        # Perform the created task.
        # ----------------------------------------------------------------------------------------------------------
        return self._hass.async_create_task(task)

    def async_create_remote_stop_transaction_task(
        self,
        charge_point,
        transaction_id
    ):
        self._hass.async_create_task(
            charge_point.remote_stop_transaction(
                transaction_id
            )
        )

    def async_create_set_max_charge_rate_task(
        self,
        conn,
        limit_list,
        start_of_schedule
    ):
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
            msg = f"Central System is already "
            if self._adding_entities:
                msg += "adding"
            elif self._updating_entities:
                msg += "updating"
            msg += f" its own Home Assistant entities > Waiting {HA_UPDATE_ENTITIES_WAITING_SECS} sec"
            OcppLog.log_w(msg)
            await asyncio.sleep(HA_UPDATE_ENTITIES_WAITING_SECS)    
    
            

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
        ha_charge_point = HomeAssistantChargePoint(
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
            model="OCPP 1.6 Charge Point",
            via_device=(DOMAIN, self._id),
        )

        return ha_charge_point

    async def get_charging_station_instance(self, cp_id, websocket):
        #OcppLog.log_w(f"Istanziazione di un Charge Point integrato...")
        # Create an instance of HomeAssistantChargePoint class
        ha_charging_station = HomeAssistantChargingStationV201(
            id=cp_id,
            connection=websocket,
            hass=self._hass,
            config_entry=self._config_entry,
            central=self
        )
        #OcppLog.log_w(f"ID del Charge Point integrato appena istanziato: {cp_id}.")
        #OcppLog.log_w(f"Aggiunta del Charge Point integrato al registro dispositivi...")
        # Create Charge Point Device in Home Assistant
        ha_dr = device_registry.async_get(self._hass)
        ha_dr.async_get_or_create(
            config_entry_id=self._config_entry.entry_id,
            identifiers={(DOMAIN, cp_id)},
            name=cp_id,
            # model=hacp.model,
            model="OCPP 2.0.1 Charging Station",
            via_device=(DOMAIN, self._id)
            # manufacturer=hacp.vendor
        )
        #OcppLog.log_w(f"Aggiunta del Charge Point integrato al registro dispositivi completata.")
        return ha_charging_station

    async def call_ha_service(
            self,
            service_name: str,
            state: bool = True,
    ):
        #OcppLog.log_d(f"Calling service {service_name}")
        resp = False
        match service_name:
            case HACentralSystemServices.service_ems_communication_start.name:
                resp = await self.start_ems_communication()
            case HACentralSystemServices.service_ems_communication_stop.name:
                resp = await self.stop_charge_advisor_backend_communication()
            case _:
                OcppLog.log_w(f"Home Assistant Central System service {service_name} unknown")
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
            await self._charge_advisor_handler.stop_websocket_client()
            self._charge_advisor_thread_websocket = None

            return True

        self.set_metric_value(HACentralSystemServices.service_ems_communication_start.value, True)

        return True

    async def stop_charge_advisor_backend_communication(self):

        self.charge_advisor_handler.stop_api_client()
        await self.charge_advisor_handler.stop_websocket_client()

        self.stop_charge_advisor_threads()

        self.set_metric_value(HACentralSystemServices.service_ems_communication_start.value, False)


        return True

