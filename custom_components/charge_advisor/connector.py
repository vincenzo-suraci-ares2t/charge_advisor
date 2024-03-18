"""Representation of a OCCP Entities."""

# ----------------------------------------------------------------------------------------------------------------------
# Python packages
# ----------------------------------------------------------------------------------------------------------------------

from __future__ import annotations
import asyncio

# ----------------------------------------------------------------------------------------------------------------------
# External packages
# ----------------------------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------------------------
# Home Assistant packages
# ----------------------------------------------------------------------------------------------------------------------

from homeassistant.helpers import device_registry, entity_component, entity_registry
from homeassistant.const import UnitOfTime

# ----------------------------------------------------------------------------------------------------------------------
# Local packages
# ----------------------------------------------------------------------------------------------------------------------

from ocpp_central_system.connector import Connector

# ----------------------------------------------------------------------------------------------------------------------
# Local files
# ----------------------------------------------------------------------------------------------------------------------

from .const import DOMAIN
from .metric import HomeAssistantEntityMetrics


class HomeAssistantConnector(Connector, HomeAssistantEntityMetrics):
    """Server side representation of a charger's connector."""

    def __init__(
            self,
            hass,
            charge_point,
            connector_id = 0,
    ):

        self._hass = hass

        # Flag per tenere conto se il Connettore sta aggiungendo le proprie entità
        self._adding_entities = False

        # Flag per tenere conto se il Connettore sta aggiornando le proprie entità
        self._updating_entities = False

        # Lista di entità Home Assistant registrate in fase di setup
        self.ha_entity_unique_ids: list[str] = []

        Connector.__init__(self, charge_point, connector_id)
        HomeAssistantEntityMetrics.__init__(self)

    # ------------------------------------------------------------------------------------------------------------------
    # Overridden Methods
    # ------------------------------------------------------------------------------------------------------------------

    # overridden
    def get_default_session_time_uom(self):
        return UnitOfTime.MINUTES

    # overridden
    def is_available_for_reservation(self):
        return super().is_available_for_reservation() and self.is_available()

    # overridden
    def is_available_for_charging(self):
        return super().is_available_for_charging() and self.is_available()

    # ------------------------------------------------------------------------------------------------------------------
    # Home Assistant Methods
    # ------------------------------------------------------------------------------------------------------------------

    def is_available(self):
        return self._charge_point.is_available()

    async def call_ha_service(
            self,
            service_name: str,
            state: bool = True
    ):
        return await self._charge_point.call_ha_service(
            service_name=service_name,
            state=state,
            connector_id=self._connector_id,
            transaction_id=self.active_transaction_id
        )

    # Updates the Charge Point Home Assistant Entities and its Connectors Home Assistant Entities
    async def update_ha_entities(self):

        while self._adding_entities or self._updating_entities:
            await asyncio.sleep(1)

        self._updating_entities = True

        # Update sensors values in HA
        er = entity_registry.async_get(self._hass)
        dr = device_registry.async_get(self._hass)
        identifiers = {(DOMAIN, self.identifier)}
        conn_dev = dr.async_get_device(identifiers)
        for conn_ent in entity_registry.async_entries_for_device(er, conn_dev.id):
            if conn_ent.unique_id not in self.ha_entity_unique_ids:
                # source: https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/entity_registry.py
                # source: https://dev-docs.home-assistant.io/en/dev/api/helpers.html#module-homeassistant.helpers.entity_registry
                # OcppLog.log_d(f"La entità {conn_ent.unique_id} è registrata in Home Assistant ma non è stata configurata dalla integrazione: verrà eliminata.")
                er.async_remove(conn_ent.entity_id)
            else:
                await entity_component.async_update_entity(self._hass, conn_ent.entity_id)

        self._updating_entities = False
