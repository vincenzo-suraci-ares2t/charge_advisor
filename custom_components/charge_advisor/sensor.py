"""Sensor platform for ocpp."""

# ----------------------------------------------------------------------------------------------------------------------
# Python packages
# ----------------------------------------------------------------------------------------------------------------------

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from typing import Final
from datetime import timedelta

# ----------------------------------------------------------------------------------------------------------------------
# Home Assistant packages
# ----------------------------------------------------------------------------------------------------------------------

import homeassistant
from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
import homeassistant.const as ha

# ----------------------------------------------------------------------------------------------------------------------
# External packages
# ----------------------------------------------------------------------------------------------------------------------

from ocpp.v16.enums import ChargePointStatus
from ocpp.v201.enums import ConnectorStatusType


# ----------------------------------------------------------------------------------------------------------------------
# Local packages
# ----------------------------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------------------------
# Local files
# ----------------------------------------------------------------------------------------------------------------------

from .const import *
from .enums import *
from .logger import OcppLog

from ocpp_central_system.ComponentsV201.enums_v201 import TierLevel

SCAN_INTERVAL = timedelta(seconds=DEFAULT_METER_INTERVAL)

# Questo insieme contiene gli stati del connettore che rendono i sensori dipsonibili nella plancia di HA
CONNECTOR_CHARGING_SESSION_SENSORS_AVAILABILTY_SET: Final = [
    ChargePointStatus.preparing.value,
    ChargePointStatus.finishing.value,
    ChargePointStatus.charging.value,
    ChargePointStatus.suspended_evse.value,
    ChargePointStatus.suspended_ev.value,
]

V201_CONNECTOR_CHARGING_SESSION_SENSORS_AVAILABILTY_SET: Final = [
    ConnectorStatusType.occupied.value
]


@dataclass
class OcppSensorDescription(SensorEntityDescription):
    """Class to describe a Sensor entity."""

    scale: int = 1  # used for rounding metric
    metric_key: str | None = None
    connector_id: int | None = None
    evse_id: int | None = None
    availability_set: list | None = None
    extra_attributes: dict | None =  field(default_factory=dict)
    visible_by_default: bool | None = False
    native_uom: str | None = None
    native_value: any | None = None


class OcppSensor:

    # Aggiornamento del 09/04/2024
    # Utilizzare questo metodo per attribuire a specifiche metriche delle unità di misura di default personalizzate
    @staticmethod
    def get_native_uom_by_metric_key(metric_key):
        native_uom = None
        match metric_key:
            case [ HAChargePointSensors.latency_ping, HAChargePointSensors.latency_pong ]:
                native_uom = ha.UnitOfTime.MILLISECONDS
                OcppLog.log_d(f"Debug >>> Unità di misura di {metric_key}: {native_uom}")
        return native_uom

    # Aggiornamento del 09/04/2024
    # Utilizzare questo metodo per attribuire a specifiche metriche dei valori di default personalizzati
    @staticmethod
    def get_native_value_by_metric_key(metric_key):
        return None

    # Metodo per il recupero delle entità di tipo Sensore per uno specifico Charge Point
    @staticmethod
    def get_charge_point_entities(
        hass,
        charge_point: ChargePoint
    ):

        # Recupero della Central System
        central_system = charge_point.central_system

        # --------------------------------------------------------------------------------------------------------------
        # Sensori associati al Charge Point
        # --------------------------------------------------------------------------------------------------------------

        # Array contenente tutti i sensori che dovranno essere registrati in Home Assistant
        sensors = []

        for metric_key in list(HAChargePointSensors):
            if metric_key in HA_CHARGE_POINT_DIAGNOSTIC_SENSORS:
                sensors.append(
                    OcppSensorDescription(
                        key=metric_key.lower(),
                        name=metric_key.replace(".", " "),
                        metric_key=metric_key,
                        entity_category=EntityCategory.DIAGNOSTIC,
                        native_uom=OcppSensor.get_native_uom_by_metric_key(metric_key),
                        native_value=OcppSensor.get_native_value_by_metric_key(metric_key)
                    )
                )
            else:
                sensors.append(
                    OcppSensorDescription(
                        key=metric_key.lower(),
                        name=metric_key.replace(".", " "),
                        metric_key=metric_key,
                        native_uom=OcppSensor.get_native_uom_by_metric_key(metric_key),
                        native_value=OcppSensor.get_native_value_by_metric_key(metric_key)
                    )
                )

        # --------------------------------------------------------------------------------------------------------------
        # Sensori associati a ciascun Connettore del Charge Point - OCPP 1.6
        # --------------------------------------------------------------------------------------------------------------

        if charge_point.connection_ocpp_version == SubProtocol.OcppV16.value:
            for connector_id in range(1, charge_point.num_connectors + 1):
                for metric_key in list(HAConnectorSensors):
                    sensors.append(
                        OcppSensorDescription(
                            key=metric_key.lower(),
                            name=metric_key.replace(".", " "),
                            metric_key=metric_key,
                            connector_id=connector_id,
                            native_uom=OcppSensor.get_native_uom_by_metric_key(metric_key),
                            native_value=OcppSensor.get_native_value_by_metric_key(metric_key)
                        )
                    )
                for metric_key in list(HAConnectorChargingSessionSensors):
                    sensors.append(
                        OcppSensorDescription(
                            key=metric_key.lower(),
                            name=metric_key.replace(".", " "),
                            metric_key=metric_key,
                            connector_id=connector_id,
                            availability_set=CONNECTOR_CHARGING_SESSION_SENSORS_AVAILABILTY_SET,
                            native_uom=OcppSensor.get_native_uom_by_metric_key(metric_key),
                            native_value=OcppSensor.get_native_value_by_metric_key(metric_key)
                        )
                    )
                for metric_key in charge_point.measurands:
                    #OcppLog.log_w(f"Adding measurand "
                    #              f"{metric_key} to Connector #"
                    #              f"{connector_id} of Charge Point "
                    #              f"{charge_point.id}")
                    sensors.append(
                        OcppSensorDescription(
                            key=metric_key,
                            name=metric_key.replace(".", " "),
                            metric_key=metric_key,
                            connector_id=connector_id,
                            availability_set=CONNECTOR_CHARGING_SESSION_SENSORS_AVAILABILTY_SET,
                            native_uom=OcppSensor.get_native_uom_by_metric_key(metric_key),
                            native_value=OcppSensor.get_native_value_by_metric_key(metric_key)
                        )
                    )

        # --------------------------------------------------------------------------------------------------------------
        # Sensori associati a ciascun Connettore di ciascun EVSE del Charging Station - OCPP 2.0.1
        # --------------------------------------------------------------------------------------------------------------

        elif charge_point.connection_ocpp_version == SubProtocol.OcppV201.value:

            def create_sensors_from_include_components(include_components_obj, sensors):
                components_list = include_components_obj.componentsList
                #OcppLog.log_e(f"Lista dei components... {components_list}")
                for component_name in components_list:

                    component = include_components_obj.get_component(component_name)
                    component_name = component.name

                    for variable_name in list(component.get_variables()):
                        # OcppLog.log_w(f"Istanze di variabile in esame in esame: {variable} - {component._variables.get(variable)}.")

                        for variable_instance_name in component.get_variable_instances(variable_name):

                            variable = component.get_variable(variable_name, variable_instance_name)

                            for variable_attribute_type in variable.variable_attributes:

                                metric_key = component.tier.compose_metric_key(
                                    component_name=component_name,
                                    component_instance=component.instance,
                                    variable_name=variable.name,
                                    variable_instance=variable.instance,
                                    attribute_type=variable_attribute_type
                                )

                                match component.tier.tier_level:
                                    case TierLevel.ChargingStation:
                                        connector_id = None
                                        evse_id = None
                                    case TierLevel.EVSE:
                                        connector_id = None
                                        evse_id = component.tier.id
                                    case TierLevel.Connector:
                                        connector_id = component.tier.id
                                        evse_id = component.tier.evse_id
                                        #OcppLog.log_d(f"Adding to Connector ID {connector_id} on EVSE {evse_id}")
                                    case _:
                                        connector_id = None
                                        evse_id = None


                                if "Ctrlr" not in component_name:
                                    sensors.append(
                                        OcppSensorDescription(
                                            key=metric_key.lower(),
                                            #name=metric_key.replace(".", " "),
                                            name=" ".join(metric_key.split(".")),
                                            metric_key=metric_key,
                                            connector_id=connector_id,
                                            evse_id=evse_id,
                                            entity_category=EntityCategory.DIAGNOSTIC,
                                            native_uom=OcppSensor.get_native_uom_by_metric_key(metric_key),
                                            native_value=OcppSensor.get_native_value_by_metric_key(metric_key)
                                        )
                                    )

            def create_sensors_from_tier_level(tier_level, sensors):

                connector_id = None
                evse_id = None

                match tier_level.tier_level:
                    case TierLevel.EVSE:
                        evse_id = tier_level.id
                    case TierLevel.Connector:
                        connector_id = tier_level.connector_id
                        evse_id = tier_level.id
                        #OcppLog.log_d(f"Adding Connector ID {connector_id} on EVSE {evse_id}")

                for metric_key in tier_level.measurands_list:
                    #OcppLog.log_e(f"Adding measurand .....{metric_key}")
                    sensors.append(
                        OcppSensorDescription(
                            key=metric_key.lower(),
                            name=metric_key.replace(".", " "),
                            metric_key=metric_key,
                            evse_id=evse_id,
                            availability_set=V201_CONNECTOR_CHARGING_SESSION_SENSORS_AVAILABILTY_SET,
                            native_uom=OcppSensor.get_native_uom_by_metric_key(metric_key),
                            native_value=OcppSensor.get_native_value_by_metric_key(metric_key)
                        )
                    )

            create_sensors_from_include_components(charge_point, sensors)
            create_sensors_from_tier_level(charge_point, sensors)

            evse_sensors = set(list(V201HAConnectorChargingSessionSensors)) | set(list(HAConnectorChargingSessionSensors))
            for evse in charge_point.evses:
                #OcppLog.log_e(f"Adding evseeeee {evse}")
                create_sensors_from_include_components(evse, sensors)
                create_sensors_from_tier_level(evse, sensors)
                for metric_key in list(evse_sensors):
                    sensors.append(
                        OcppSensorDescription(
                            key=metric_key.lower(),
                            name=metric_key.replace(".", " "),
                            metric_key=metric_key,
                            evse_id=evse.id,
                            availability_set=V201_CONNECTOR_CHARGING_SESSION_SENSORS_AVAILABILTY_SET,
                            native_uom=OcppSensor.get_native_uom_by_metric_key(metric_key),
                            native_value=OcppSensor.get_native_value_by_metric_key(metric_key)
                        )
                    )
                for connector in evse.connectors:
                    create_sensors_from_include_components(connector, sensors)
                    create_sensors_from_tier_level(connector, sensors)

        # --------------------------------------------------------------------------------------------------------------
        # Entità associate ai sensori del Charge Point
        # --------------------------------------------------------------------------------------------------------------

        entities = []

        if charge_point.connection_ocpp_version == SubProtocol.OcppV16.value:
            for sensor in sensors:
                if sensor.connector_id is None:
                    entities.append(
                        ChargePointMetric(
                            hass,
                            central_system,
                            charge_point,
                            sensor
                        )
                    )
                else:
                    connector = charge_point.get_connector_by_id(sensor.connector_id)
                    entities.append(
                        ChargePointConnectorMetric(
                            hass,
                            central_system,
                            charge_point,
                            connector,
                            sensor
                        )
                    )
        elif charge_point.connection_ocpp_version == SubProtocol.OcppV201.value:
            for sensor in sensors:
                connector_id = sensor.connector_id
                evse_id = sensor.evse_id

                if connector_id is None and evse_id is None:
                    entities.append(
                        ChargePointMetric(
                            hass,
                            central_system,
                            charge_point,
                            sensor
                        )
                    )
                elif evse_id is not None and connector_id is None:
                    evse = charge_point.get_evse_by_id(int(evse_id))
                    entities.append(
                        EVSEMetric(
                            hass,
                            central_system,
                            charge_point,
                            evse,
                            sensor
                        )
                    )
                elif evse_id is not None and connector_id is not None:
                    evse = charge_point.get_evse_by_id(int(evse_id))
                    connector = evse.get_connector_by_id(int(connector_id))
                    entities.append(
                        EVSEConnectorMetric(
                            hass,
                            central_system,
                            charge_point,
                            evse,
                            connector,
                            sensor,
                        )
                    )

        return entities


# Static Sensor Platform entities registration done at CONFIG TIME (not at RUNTIME)
# A workaround to do it at runtime: https://community.home-assistant.io/t/adding-entities-at-runtime/200855/2
async def async_setup_entry(hass, entry, async_add_devices):

    #OcppLog.log_i("Sensor async_setup_entry called!")

    # Configure the sensor platform
    central_system: CentralSystem = hass.data[DOMAIN][entry.entry_id]

    entities = []

    for cp_id in central_system.charge_points:
        charge_point = central_system.charge_points[cp_id]
        for charge_point_entity in OcppSensor.get_charge_point_entities(hass, charge_point):
            entities.append(charge_point_entity)

    # Aggiungiamo gli unique_id di ogni entità registrata in fase di setup al
    # Charge Point o al Connector
    for entity in entities:
        entity.append_entity_unique_id()

    async_add_devices(entities, False)


# source: https://developers.home-assistant.io/docs/core/entity/sensor?_highlight=restoresensor#restoring-sensor-states
class ChargePointMetric(RestoreSensor, SensorEntity):
    # Individual sensor for charge point metrics.

    _attr_has_entity_name = True
    entity_description: OcppSensorDescription

    def __init__(
        self,
        hass,
        central_system,
        charge_point,
        description: OcppSensorDescription,
    ):
        # Instantiate instance of a ChargePointMetrics.
        self._central_system = central_system
        self._charge_point = charge_point
        self.entity_description = description
        self._hass = hass
        self._extra_attr = self.entity_description.extra_attributes
        self._last_reset = homeassistant.util.dt.utc_from_timestamp(0)
        self._attr_unique_id = ".".join([
            SENSOR_DOMAIN,
            DOMAIN,
            self._charge_point.id,
            self.entity_description.key
        ])
        self._attr_name = self.entity_description.name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._charge_point.id)},
            via_device=(DOMAIN, self._central_system.id),
        )
        self._attr_native_unit_of_measurement = description.native_uom
        self._attr_native_value = description.native_value
        self._visible_by_default = self.entity_description.visible_by_default

    @property
    def target(self):
        return self._charge_point

    @property
    def entity_registry_visible_default(self):
        return True

    @property
    def _metric_key(self):
        return self.entity_description.metric_key

    # source: https://developers.home-assistant.io/docs/core/entity/#property-function
    @property
    def icon(self) -> str | None:
        # Icon of the entity.
        if self._metric_key in MEASURAND_ICON:
            return MEASURAND_ICON[self._metric_key]
        return ICON

    @property
    def available(self) -> bool:
        # Return if sensor is available.
        if self.target.is_available is None:
            return False
        else:
            return self.target.is_available

    @property
    def should_poll(self):
        # Return True if entity has to be polled for state.
        # False if entity pushes its state to HA.
        return True

    @property
    def force_update(self):

        return True

    @property
    def extra_state_attributes(self):
        # Return the state attributes.
        return self.target.get_metric_extra_attr(self._metric_key)

    @property
    def state_class(self):
        # Return the state class of the sensor.
        state_class = None
        #OcppLog.log_w(f"Device Class del sensore {self._attr_name}: {self.device_class}.")
        #OcppLog.log_w(f"Unità di misura nativa di {self._attr_name}: {self.native_unit_of_measurement}.")
        if self.device_class is SensorDeviceClass.ENERGY:
            state_class = SensorStateClass.TOTAL_INCREASING
        elif self.device_class in [
            SensorDeviceClass.CURRENT,
            SensorDeviceClass.VOLTAGE,
            SensorDeviceClass.POWER,
            SensorDeviceClass.TEMPERATURE,
            SensorDeviceClass.BATTERY,
            SensorDeviceClass.FREQUENCY,
            SensorDeviceClass.DURATION
        ] or self._metric_key in [
            HAChargePointSensors.latency_ping.value,
            HAChargePointSensors.latency_pong.value,
        ]:
            state_class = SensorStateClass.MEASUREMENT

        return state_class

    def append_entity_unique_id(self):
        if self.unique_id not in self.target.ha_entity_unique_ids:
            self.target.ha_entity_unique_ids.append(self.unique_id)

    # Aggiornamento del 08/02/2023
    # I measurand di Energia e Potenza REATTIVA non hanno in Home Assistant una unità di misura standardizzata.
    # Home Assistant supporta solo W, kW, Wh e kWh.
    #
    # Pertanto, impostando Energia e Potenza REATTIVA con le loro unità di misura (var, kvar per la potenza e
    # varh, kvarh per la energia) nelle classi Home Assistant SensorDeviceClass.ENERGY e SensorDeviceClass.POWER
    # dà i seguenti errori:
    # a) WARNING(MainThread)[homeassistant.components.sensor] Entity sensor.charge_point_1_1_energy_reactive_export_interval
    #    (<class 'custom_components.ocpp.sensor.ChargePointConnectorMetric'> ) is using native unit of measurement
    #    'UnitOfMeasure.kvarh' which is not a valid unit for the device
    # b) WARNING(MainThread)[homeassistant.components.sensor] Entity sensor.charge_point_1_1_power_reactive_import
    #    (<class 'custom_components.ocpp.sensor.ChargePointConnectorMetric'> ) is using native unit of measurement
    #    'UnitOfMeasure.kvar' which is not a valid unit for the device
    #
    # Per ovviare al problema, evitiamo di attribuire tali classi ai sensori di Energia e Potenza REATTIVA

    @property
    def device_class(self):
        # Return the device class of the sensor.
        device_class = None
        mk = self._metric_key.lower()
        if mk.startswith("current."):
            device_class = SensorDeviceClass.CURRENT
        elif mk.startswith("voltage"):
            device_class = SensorDeviceClass.VOLTAGE
        elif mk.startswith("energy."):
            device_class = SensorDeviceClass.ENERGY
        elif self._metric_key in [
                Measurand.frequency.value,
                Measurand.rpm.value,
            ] or mk.startswith("frequency"):
            device_class = SensorDeviceClass.FREQUENCY
        elif mk.startswith(tuple(["power.active", "power.offered"])):
            device_class = SensorDeviceClass.POWER
        elif mk.startswith("power.reactive"):
            device_class = SensorDeviceClass.REACTIVE_POWER
        elif mk.startswith("temperature."):
            device_class = SensorDeviceClass.TEMPERATURE
        elif mk.startswith("session.time") or mk.startswith("latency"):
            device_class = SensorDeviceClass.DURATION
        elif mk.startswith("session.energy"):
            device_class = SensorDeviceClass.ENERGY
        elif mk.startswith("timestamp.") or self._metric_key in [
                HAChargePointSensors.config_response.value,
                HAChargePointSensors.data_response.value,
                HAChargePointSensors.heartbeat.value,
            ]:
            device_class = SensorDeviceClass.TIMESTAMP
        elif mk.startswith("soc"):
            device_class = SensorDeviceClass.BATTERY
        return device_class

    @property
    def native_value(self):
        # Return the state of the sensor, rounding if a number.
        value = self.target.get_metric_value(self._metric_key)
        if isinstance(value, float):
            value = round(value, self.entity_description.scale)
        if value is not None:
            self._attr_native_value = value
        # OcppLog.log_d(f"{self._attr_unique_id} value: {self._attr_native_value}")
        return self._attr_native_value

    @property
    def native_unit_of_measurement(self):
        # Return the native unit of measurement.
        uom = self.target.get_metric_ha_unit(self._metric_key)
        if uom is not None:
            self._attr_native_unit_of_measurement = uom
        else:
            self._attr_native_unit_of_measurement = DEFAULT_CLASS_UNITS_HA.get(
                self.device_class
            )
        return self._attr_native_unit_of_measurement

    """
    Restoring sensor states
    Sensors which restore the state after restart or reload should not extend RestoreEntity because that does not store 
    the native_value, but instead the state which may have been modifed by the sensor base entity. Sensors which restore 
    the state should extend RestoreSensor and call await self.async_get_last_sensor_data from async_added_to_hass to get 
    access to the stored native_value and native_unit_of_measurement.
    source: https://developers.home-assistant.io/docs/core/entity/sensor?_highlight=restoresensor#restoring-sensor-states
    """
    async def async_added_to_hass(self) -> None:
        # Handle entity which will be added.
        await super().async_added_to_hass()

        if restored := await self.async_get_last_sensor_data():
            # Recuperiamo il valore solo se i sensori sono di categoria DIAGNOSTIC
            if self.entity_description.entity_category == EntityCategory.DIAGNOSTIC:
                self._attr_native_value = restored.native_value
            self._attr_native_unit_of_measurement = restored.native_unit_of_measurement

        async_dispatcher_connect(
            self._hass, DATA_UPDATED, self._schedule_immediate_update
        )

    @callback
    def _schedule_immediate_update(self):
        self.async_schedule_update_ha_state(True)

class ChargePointConnectorMetric(ChargePointMetric):

    def __init__(
        self,
        hass: HomeAssistant,
        central_system: CentralSystem,
        charge_point: ChargePoint,
        connector: Connector,
        description: OcppSensorDescription
    ):
        super().__init__(hass, central_system, charge_point, description)
        self._connector = connector
        self._attr_unique_id = ".".join([
            SENSOR_DOMAIN,
            DOMAIN,
            self._charge_point.id,
            str(self._connector.id),
            self.entity_description.key
        ])
        self._extra_attr = self.entity_description.extra_attributes
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._connector.identifier)},
            via_device=(DOMAIN, charge_point),
        )

        # OcppLog.log_d(f"Adding {self._attr_unique_id} entity")

    @property
    def target(self):
        return self._connector

    @property
    def available(self) -> bool:
        # Return if sensor is available
        available = False
        if self.entity_description.availability_set is not None:
            value = self._connector.get_metric_value(HAConnectorSensors.status.value)
            if value in self.entity_description.availability_set:
                available = super().available
        else:
            available = super().available
        return available


class EVSEMetric(ChargePointMetric):

    def __init__(
        self,
        hass: HomeAssistant,
        central_system: CentralSystem,
        charge_point: ChargePoint,
        evse: EVSE,
        description: OcppSensorDescription,
    ):
        super().__init__(hass, central_system, charge_point, description)
        self._evse = evse
        self._attr_unique_id = ".".join([
            SENSOR_DOMAIN,
            DOMAIN,
            self._charge_point.id,
            str(self._evse.id),
            self.entity_description.key
        ])
        self._extra_attr = self.entity_description.extra_attributes
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._evse.identifier)},
            #via_device=(DOMAIN, self._charge_point.id),
        )

        # OcppLog.log_d(f"Adding {self._attr_unique_id} entity")

    @property
    def target(self):
        return self._evse

    @property
    def available(self) -> bool:

        # Return if sensor is available
        available = False
        if self.entity_description.availability_set is not None:
            value = self._evse.get_metric_value("EVSE.AvailabilityState")
            if value in self.entity_description.availability_set:
                available = super().available
        else:
            available = super().available
        return available

class EVSEConnectorMetric(EVSEMetric):

    def __init__(
        self,
        hass: HomeAssistant,
        central_system: CentralSystem,
        charge_point: ChargePoint,
        evse: EVSE,
        connector: Connector,
        description: OcppSensorDescription,

    ):
        super().__init__(hass, central_system, charge_point, evse, description)
        self._evse = evse
        self._connector = connector
        self._attr_unique_id = ".".join([
            SENSOR_DOMAIN,
            DOMAIN,
            self._charge_point.id,
            str(self._evse.id),
            str(self._connector.connector_id),
            self.entity_description.key
        ])
        #OcppLog.log_e(f"Adding Connector sensor {self._attr_unique_id} with identifier {self._connector.identifier}")
        self._extra_attr = self.entity_description.extra_attributes
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._connector.identifier)}
        )
        # OcppLog.log_d(f"Adding {self._attr_unique_id} entity")

    @property
    def target(self):
        return self._connector

    @property
    def available(self) -> bool:

        # Return if sensor is available
        available = False
        if self.entity_description.availability_set is not None:
            value = self._connector.get_metric_value("Connector.AvailabilityState")
            if value in self.entity_description.availability_set:
                available = super().available
        else:
            available = super().available
        return available