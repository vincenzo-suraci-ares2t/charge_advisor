"""Switch platform for ocpp."""

# ----------------------------------------------------------------------------------------------------------------------
# Python packages
# ----------------------------------------------------------------------------------------------------------------------

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Final

# ----------------------------------------------------------------------------------------------------------------------
# Home Assistant packages
# ----------------------------------------------------------------------------------------------------------------------

from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.const import UnitOfPower
from homeassistant.helpers.entity import DeviceInfo

# ----------------------------------------------------------------------------------------------------------------------
# External packages
# ----------------------------------------------------------------------------------------------------------------------

from ocpp.v16.enums import ChargePointStatus, Measurand, AvailabilityType
from ocpp.v201.enums import OperationalStatusType, ConnectorStatusType

# ----------------------------------------------------------------------------------------------------------------------
# Local packages
# ----------------------------------------------------------------------------------------------------------------------

from .const import DOMAIN, ICON
from .enums import HAChargePointServices, HAChargePointSensors, HAConnectorSensors, SubProtocol, HAEVSESensors
from .logger import OcppLog

# Switch configuration definitions
# At a minimum define switch name and on service call,
# metric and condition combination can be used to drive switch state, use default to set initial state to True
@dataclass
class OcppSwitchDescription(SwitchEntityDescription):
    """Class to describe a Switch entity."""

    on_action_service_name: str | None = None
    off_action_service_name: str | None = None
    metric_key: str | None = None
    metric_condition: str | None = None
    default_state: bool = False


"""
Gli switch sono aggiunti "staticamente" dall'integrazione.
Vengono aggiunti 2 switch:
1) Availability > dovrebbe essere uno per ogni connettore!
2) Charge_Control > dovrebbe essere uno per ogni connettore! 
"""
# Switch della Central System.
CENTRAL_SYSTEM_SWITCHES: Final = [
    OcppSwitchDescription(
        key="energy_control_communication",
        name="EMS Communication",
        icon=ICON,
        on_action_service_name=HAChargePointServices.service_ems_communication_start.name, # service name (not value)
        off_action_service_name=HAChargePointServices.service_ems_communication_stop.name, # service name (not value)
        metric_key=HAChargePointServices.service_ems_communication_start.value,
        metric_condition=[
            True #Questa è hard coded per il momento, solo provvisorio
        ],
        default_state=False,
    ),
]

# Switch del Charge Point. Sono gli stessi per OCPP 1.6 e 2.0.1.
# Nota: AvailabilityType è però un'enumerazione esclusiva di 1.6, il corrispettivo in 2.0.1 è OperationalStatusType.
CHARGE_POINT_SWITCHES: Final = [
    OcppSwitchDescription(
        key="availability",
        name="Availability",
        icon=ICON,
        on_action_service_name=HAChargePointServices.service_availability.name, # service name (not value)
        off_action_service_name=HAChargePointServices.service_availability.name, # service name (not value)
        metric_key="ChargingStation.AvailabilityState",
        metric_condition=[
            ConnectorStatusType.available.value,
            ConnectorStatusType.reserved.value,
            ConnectorStatusType.occupied.value
        ],
        default_state=False
    ),
]

# Switch dei connettori 1.6.
CHARGE_POINT_CONNECTOR_SWITCHES: Final = [
    OcppSwitchDescription(
        key="charge_control",
        name="Charge Control",
        icon=ICON,
        on_action_service_name=HAChargePointServices.service_charge_start.name,
        off_action_service_name=HAChargePointServices.service_charge_stop.name,
        metric_key=HAConnectorSensors.status.value,
        metric_condition=[
            ChargePointStatus.preparing.value,
            ChargePointStatus.charging.value,
            ChargePointStatus.suspended_evse.value,
            ChargePointStatus.suspended_ev.value,
        ],
        default_state=False,
    ),
    OcppSwitchDescription(
        key="availability",
        name="Availability",
        icon=ICON,
        on_action_service_name=HAChargePointServices.service_availability.name,
        off_action_service_name=HAChargePointServices.service_availability.name,
        metric_key=HAConnectorSensors.availability.value,
        metric_condition=[
            AvailabilityType.operative.value
        ],
        default_state=AvailabilityType.inoperative.value,
    ),
]

# Switch degli EVSE 2.0.1.
CHARGE_POINT_EVSE_SWITCHES: Final = [
    OcppSwitchDescription(
        key="charge_control",
        name="Charge Control",
        icon=ICON,
        on_action_service_name=HAChargePointServices.service_charge_start.name,
        off_action_service_name=HAChargePointServices.service_charge_stop.name,
        metric_key="EVSE.AvailabilityState",
        metric_condition=[
            ConnectorStatusType.occupied.value
        ],
        default_state=False,
    ),
    OcppSwitchDescription(
        key="availability",
        name="Availability",
        icon=ICON,
        on_action_service_name=HAChargePointServices.service_availability.name,
        off_action_service_name=HAChargePointServices.service_availability.name,
        metric_key="EVSE.AvailabilityState",
        metric_condition=[
            ConnectorStatusType.available.value,
            ConnectorStatusType.reserved.value,
            ConnectorStatusType.occupied.value
        ],
        default_state=OperationalStatusType.operative.value,
    ),
]

# Switch dei connettori 2.0.1.
EVSE_CONNECTOR_SWITCHES: Final = [
    OcppSwitchDescription(
        key="availability",
        name="Availability",
        icon=ICON,
        on_action_service_name=HAChargePointServices.service_availability.name,
        off_action_service_name=HAChargePointServices.service_availability.name,
        metric_key="Connector.AvailabilityState",
        metric_condition=[
            ConnectorStatusType.available.value,
            ConnectorStatusType.reserved.value,
            ConnectorStatusType.occupied.value
        ],
        default_state=OperationalStatusType.operative.value,
    )
]


async def async_setup_entry(hass, entry, async_add_devices):
    """Configure the switch platform."""

    # Get the Central system instance
    central_system = hass.data[DOMAIN][entry.entry_id]    

    entities = []
    entities.append(CentralSystemSwitchEntity(central_system, CENTRAL_SYSTEM_SWITCHES[0]))
    # Per ogni ID Charge Point...
    for cp_id in central_system.charge_points:
        # Recuperare il Charge Point vero e proprio.
        charge_point = central_system.charge_points[cp_id]
        OcppLog.log_w(f"CHARGE POINT IN ESAME: {charge_point}.")
        OcppLog.log_w(f"Tipo del charge point in esame: {type(charge_point)}.")
        # Per ogni switch da aggiungere al Charge Point.
        for desc in CHARGE_POINT_SWITCHES:
            # Creare un oggetto di tipo ChargePointSwitchEntity sulla base della descrizione che si trova nella
            # lista CHARGE_POINT_SWITCHES e aggiungere tale oggetto alle entità del Charge Point in esame.
            entities.append(ChargePointSwitchEntity(central_system, charge_point, desc))
        # Se la versione di OCPP in uso è la 1.6...
        if charge_point.connection_ocpp_version == SubProtocol.OcppV16.value:
            OcppLog.log_i(f"Versione protocollo OCPP: 1.6.")
            # Aggiungere i connettori direttamente al Charge Point.
            for connector in charge_point.connectors:
                for ent in CHARGE_POINT_CONNECTOR_SWITCHES:
                    entities.append(
                        ChargePointConnectorSwitchEntity(
                            central_system,
                            charge_point,
                            connector,
                            ent
                        )
                    )
        # Altrimenti, se la versione usata è la 2.0.1...
        # elif charge_point.connection_ocpp_version == SubProtocol.OcppV201.value:
        else:
            # Scorrere gli switch per gli EVSE del Charge Point e aggiungerli alle entità.
            OcppLog.log_i(f"Versione protocollo OCPP: 2.0.1.")
            OcppLog.log_i(f"EVSE disponibili: {charge_point.evses}.")
            # Per ogni EVSE...
            for evse in charge_point.evses:
                OcppLog.log_w(f"EVSE in esame: {evse}.")
                OcppLog.log_w(f"Tipo dell'EVSE in esame: {type(evse)}.")
                # Per ogni switch da aggiungere all'EVSE...
                # OcppLog.log_w(f"Descrizioni di switch disponibili per gli EVSE: {CHARGE_POINT_EVSE_SWITCHES}")
                for desc in CHARGE_POINT_EVSE_SWITCHES:
                    OcppLog.log_w(f"Nome switch in esame: {desc.name}. Per EVSE {evse.id} con identificatore {evse.identifier}.")
                    # Inserire lo switch tra le entità dell'EVSE, usando la descrizione fornita dalla lista
                    # CHARGE_POINT_EVSE_SWITCHES per creare un oggetto di tipo EVSESwitchEntity.
                    OcppLog.log_w(f"Inserimento switch EVSE...")
                    entities.append(
                        EVSESwitchEntity(
                            central_system,
                            charge_point,
                            evse,
                            desc
                        )
                    )
                    # Aggiungere gli switch dei connettori relativi all'EVSE in esame.
                    for connector in evse.connectors:
                        OcppLog.log_w(f"Connector in esame: {connector}.")
                        for conn_desc in EVSE_CONNECTOR_SWITCHES:
                            OcppLog.log_w(f"Descrizione switch per connector: {conn_desc}.")
                            entities.append(
                                EVSEConnectorSwitchEntity(
                                    central_system,
                                    charge_point,
                                    evse,
                                    connector,
                                    conn_desc
                                )
                            )

    OcppLog.log_w(f"Entità switch aggiunte: {entities}.")
    # Aggiungiamo gli unique_id di ogni entità registrata in fase di setup al
    # Charge Point o al Connector
    for entity in entities:
        entity.append_entity_unique_id()
        OcppLog.log_w(f"Entità aggiunta e suo ID: {entity.name}, {entity.entity_id}.")
        OcppLog.log_w(f"Tipo entità aggiunta: {type(entity)}.")

    async_add_devices(entities, False)
    OcppLog.log_w(f"Inserimento terminato.")

class CentralSystemSwitchEntity(SwitchEntity):
    _attr_has_entity_name = True
    entity_description: OcppSwitchDescription

    def __init__(
        self,
        central_system: CentralSystem,
        description: OcppSwitchDescription,
    ):
        self._central_system = central_system
        self.entity_description = description
        self._state = self.entity_description.default_state
        self._attr_unique_id = ".".join([
            SWITCH_DOMAIN,
            DOMAIN,
            self._central_system.id,
            self.entity_description.key
            ])
        self._attr_name = self.entity_description.name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._central_system.id)}
        )
        # OcppLog.log_d(f"{self._attr_unique_id} switch created!")
        OcppLog.log_w(f"Central system ID: {self._central_system.id}.")
        OcppLog.log_w(f"Tipo central system in esame: {type(self._central_system)}.")
        OcppLog.log_w(f"Central System attr_unique_id: {self._attr_unique_id}.")

    @property
    def target(self):
        return self._central_system

    @property
    def available(self) -> bool:
        # Return if switch is available.
        return self.target.is_available()

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        """Test metric state against condition if present"""
        resp = self.target.get_metric_value(self.entity_description.metric_key)
        if resp is not None:
            if resp in self.entity_description.metric_condition:
                self._state = True
            else:
                self._state = False
        # OcppLog.log_d(f"{self._attr_unique_id} is_on: {self._state}")
        return self._state  # type: ignore [no-any-return]


    async def async_turn_off(self, **kwargs: Any) -> None:
        # Turn the switch off.
        """Response is True if successful but State is False"""
        if self.entity_description.off_action_service_name is None:
            resp = True
        elif self.entity_description.off_action_service_name == self.entity_description.on_action_service_name:
            resp = await self.target.call_ha_service(
                service_name=self.entity_description.off_action_service_name,
                state=False
            )
        else:
            resp = await self.target.call_ha_service(
                service_name=self.entity_description.off_action_service_name,
            )
        self._state = not resp

    async def async_turn_on(self, **kwargs: Any) -> None:
        # Turn the switch on.
        # OcppLog.log_d(f"{self.entity_description.on_action_service_name} service called")
        self._state = await self.target.call_ha_service(
            service_name=self.entity_description.on_action_service_name,
            state=True
        )

    def append_entity_unique_id(self):
        if self.unique_id not in self.target.ha_entity_unique_ids:
            self.target.ha_entity_unique_ids.append(self.unique_id)



class ChargePointSwitchEntity(SwitchEntity):
    """Individual switch for charge point."""

    _attr_has_entity_name = True
    entity_description: OcppSwitchDescription

    def __init__(
        self,
        central_system: CentralSystem,
        charge_point: ChargePoint,
        description: OcppSwitchDescription,
    ):
        self._charge_point = charge_point
        self._central_system = central_system
        self.entity_description = description
        self._state = self.entity_description.default_state
        self._attr_unique_id = ".".join([
            SWITCH_DOMAIN,
            DOMAIN,
            self._charge_point.id,
            self.entity_description.key
            ])
        self._attr_name = self.entity_description.name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._charge_point.id)},
            via_device=(DOMAIN, self._central_system.id),
        )
        # OcppLog.log_d(f"{self._attr_unique_id} switch created!")

    @property
    def target(self):
        return self._charge_point

    @property
    def available(self) -> bool:
        # Return if sensor is available.
        if self.target.is_available is None:
            return False
        else:
            return self.target.is_available

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        """Test metric state against condition if present"""
        resp = self.target.get_metric_value(self.entity_description.metric_key)
        if resp is not None:
            if resp in self.entity_description.metric_condition:
                self._state = True
            else:
                self._state = False
        # OcppLog.log_d(f"{self._attr_unique_id} is_on: {self._state}")
        return self._state  # type: ignore [no-any-return]


    async def async_turn_on(self, **kwargs: Any) -> None:
        # Turn the switch on.
        # OcppLog.log_d(f"{self.entity_description.on_action_service_name} service called")
        self._state = await self.target.call_ha_service(
            service_name=self.entity_description.on_action_service_name,
            state=True
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        # Turn the switch off.
        """Response is True if successful but State is False"""
        if self.entity_description.off_action_service_name is None:
            resp = True
        elif self.entity_description.off_action_service_name == self.entity_description.on_action_service_name:
            resp = await self.target.call_ha_service(
                service_name=self.entity_description.off_action_service_name,
                state=False
            )
        else:
            resp = await self.target.call_ha_service(
                service_name=self.entity_description.off_action_service_name,
            )
        self._state = not resp

    @property
    def current_power_w(self) -> Any:
        """Return the current power usage in W."""
        if self.entity_description.key == "charge_control":
            value = self.target.get_metric_value(Measurand.power_active_import.value)
            ha_unit = self.target.get_metric_ha_unit(Measurand.power_active_import.value)
            if ha_unit == UnitOfPower.KILO_WATT:
                value = value * 1000
            return value
        return None

    def append_entity_unique_id(self):
        if self.unique_id not in self.target.ha_entity_unique_ids:
            self.target.ha_entity_unique_ids.append(self.unique_id)

class ChargePointConnectorSwitchEntity(ChargePointSwitchEntity):
    """Individual switch for charge point."""

    _attr_has_entity_name = True
    entity_description: OcppSwitchDescription

    def __init__(
        self,
        central_system: CentralSystem,
        charge_point: ChargePoint,
        connector: Connector,
        description: OcppSwitchDescription,
    ):
        super().__init__(central_system, charge_point, description)
        self._connector = connector
        self._attr_unique_id = ".".join([
            SWITCH_DOMAIN,
            DOMAIN,
            self._charge_point.id,
            str(self._connector.id),
            self.entity_description.key
            ])
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._connector.identifier)},
            via_device=(DOMAIN, self._charge_point.id),
        )

    @property
    def target(self):
        return self._connector

class EVSESwitchEntity(ChargePointSwitchEntity):

    _attr_has_entity_name = True
    entity_description: OcppSwitchDescription

    def __init__(
            self,
            central_system: CentralSystem,
            charge_point: ChargePoint,
            evse: EVSE,
            description: OcppSwitchDescription,
    ):
        super().__init__(central_system, charge_point, description)
        self._charge_point = charge_point
        self._evse = evse
        self.entity_description = description
        self._state = self.entity_description.default_state
        self._attr_unique_id = ".".join([
            SWITCH_DOMAIN,
            DOMAIN,
            self._evse.identifier,
            self.entity_description.key
        ])
        self._attr_name = self.entity_description.name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._evse.identifier)},
            #via_device=(DOMAIN, self._charge_point.id),
        )
        OcppLog.log_w(f"EVSE VIA DEVICE: ({DOMAIN}, {self._charge_point.id}).")
        OcppLog.log_w(f"EVSE ID attr_unique_id: {self._attr_unique_id}.")
        OcppLog.log_w(f"EVSE description key: {self.entity_description.key}.")

    @property
    def target(self):
        return self._evse

    @property
    def available(self) -> bool:
        # Return if switch is available.
        return self.target.is_available

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        """Test metric state against condition if present"""
        resp = self.target.get_metric_value(self.entity_description.metric_key)
        if resp is not None:
            if resp in self.entity_description.metric_condition:
                self._state = True
            else:
                self._state = False
        # OcppLog.log_d(f"{self._attr_unique_id} is_on: {self._state}")
        return self._state  # type: ignore [no-any-return]

    async def async_turn_on(self, **kwargs: Any) -> None:
        # Turn the switch on.
        # OcppLog.log_d(f"{self.entity_description.on_action_service_name} service called")
        self._state = await self.target.call_ha_service(
            service_name=self.entity_description.on_action_service_name,
            state=True
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        # Turn the switch off.
        """Response is True if successful but State is False"""
        if self.entity_description.off_action_service_name is None:
            resp = True
        elif self.entity_description.off_action_service_name == self.entity_description.on_action_service_name:
            resp = await self.target.call_ha_service(
                service_name=self.entity_description.off_action_service_name,
                state=False
            )
        else:
            resp = await self.target.call_ha_service(
                service_name=self.entity_description.off_action_service_name,
            )
        self._state = not resp

    @property
    def current_power_w(self) -> Any:
        """Return the current power usage in W."""
        if self.entity_description.key == "charge_control":
            value = self.target.get_metric_value(Measurand.power_active_import.value)
            ha_unit = self.target.get_metric_ha_unit(Measurand.power_active_import.value)
            if ha_unit == UnitOfPower.KILO_WATT:
                value = value * 1000
            return value
        return None

    def append_entity_unique_id(self):
        if self.unique_id not in self.target.ha_entity_unique_ids:
            self.target.ha_entity_unique_ids.append(self.unique_id)

class EVSEConnectorSwitchEntity(EVSESwitchEntity):

    _attr_has_entity_name = True
    entity_description: OcppSwitchDescription

    def __init__(
        self,
        central_system: CentralSystem,
        charge_point: ChargePoint,
        evse: EVSE,
        connector: Connector,
        description: OcppSwitchDescription
    ):
        super().__init__(central_system, charge_point, evse, description)
        self._evse = evse
        self._connector = connector
        self.entity_description = description
        self._attr_unique_id = ".".join([
            SWITCH_DOMAIN,
            DOMAIN,
            self._charge_point.id,
            self._evse.identifier,
            str(self._connector.identifier),
            self.entity_description.key
            ])
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._connector.identifier)},
            #via_device=(DOMAIN, self._evse.identifier),
        )
        OcppLog.log_w(f"TIPO CONNECTOR: {type(self.target)}.")
        OcppLog.log_w(f"Connector VIA DEVICE: ({DOMAIN}, {self._evse.identifier}).")
        OcppLog.log_w(f"Connector ID attr_unique_id: {self._attr_unique_id}.")
        OcppLog.log_w(f"Connector description key: {self.entity_description.key}.")

    @property
    def target(self):
        return self._connector

    @property
    def available(self) -> bool:
        # Return if switch is available.
        return self.target.is_available

    async def async_turn_off(self, **kwargs: Any) -> None:
        OcppLog.log_w(f"SWITCH CONNECTOR TURN OFF")
        OcppLog.log_w(f"self.entity_description.off_action_Service_name: {self.entity_description.off_action_service_name}.")
        # Turn the switch off.
        """Response is True if successful but State is False"""
        if self.entity_description.off_action_service_name is None:
            resp = True
        elif self.entity_description.off_action_service_name == self.entity_description.on_action_service_name:
            resp = await self.target.call_ha_service(
                service_name=self.entity_description.off_action_service_name,
                state=False
            )
        else:
            resp = await self.target.call_ha_service(
                service_name=self.entity_description.off_action_service_name,
            )
        self._state = not resp

    async def async_turn_on(self, **kwargs: Any) -> None:
        OcppLog.log_w(f"SWITCH CONNECTOR TURN ON")
        OcppLog.log_w(f"self.entity_description.on_action_Service_name: {self.entity_description.on_action_service_name}.")
        # Turn the switch on.
        self._state = await self.target.call_ha_service(
            service_name=self.entity_description.on_action_service_name,
            state=True
        )

    def append_entity_unique_id(self):
        if self.unique_id not in self.target.ha_entity_unique_ids:
            self.target.ha_entity_unique_ids.append(self.unique_id)
