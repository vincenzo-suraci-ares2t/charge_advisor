"""Define constants for OCPP integration."""

# ----------------------------------------------------------------------------------------------------------------------
# Python packages
# ----------------------------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------------------------
# Home Assistant packages
# ----------------------------------------------------------------------------------------------------------------------

import homeassistant.components.input_number as input_number
from homeassistant.components.sensor import SensorDeviceClass
import homeassistant.const as ha

# ----------------------------------------------------------------------------------------------------------------------
# External packages
# ----------------------------------------------------------------------------------------------------------------------

# pip install git+https://<USERNAME>@bitbucket.org/ares2t/ocpp-central-system.git
# from ocpp_central_system.const import *

# ----------------------------------------------------------------------------------------------------------------------
# Local packages
# ----------------------------------------------------------------------------------------------------------------------

from ocpp_central_system.const import *

# ----------------------------------------------------------------------------------------------------------------------
# Local files
# ----------------------------------------------------------------------------------------------------------------------

from .enums import HAChargePointSensors

# Home Assistant Energy and Power UoM
HA_ENERGY_UNIT = UnitOfMeasure.kwh.value
HA_POWER_UNIT = UnitOfMeasure.kw.value

# Home Assistant Configuration
CONF_HOST = ha.CONF_HOST
CONF_ICON = ha.CONF_ICON
CONF_MODE = ha.CONF_MODE
CONF_MONITORED_VARIABLES = ha.CONF_MONITORED_VARIABLES
CONF_NAME = ha.CONF_NAME
CONF_PASSWORD = ha.CONF_PASSWORD
CONF_PORT = ha.CONF_PORT
CONF_STEP = input_number.CONF_STEP
CONF_UNIT_OF_MEASUREMENT = ha.CONF_UNIT_OF_MEASUREMENT
CONF_USERNAME = ha.CONF_USERNAME

# Home Assistant Platforms
SENSOR = "sensor"
SWITCH = "switch"
NUMBER = "number"
BUTTON = "button"
PLATFORMS = [SENSOR, SWITCH, NUMBER, BUTTON]

# Home Assistant Default UoM
# Where an OCPP unit is not reported and only one possibility assign HA unit on device class
DEFAULT_CLASS_UNITS_HA = {
    SensorDeviceClass.CURRENT: ha.UnitOfElectricCurrent.AMPERE,
    SensorDeviceClass.VOLTAGE: ha.UnitOfElectricPotential.VOLT,
    SensorDeviceClass.FREQUENCY: ha.UnitOfFrequency.HERTZ,
    SensorDeviceClass.BATTERY: ha.PERCENTAGE,
    SensorDeviceClass.POWER: ha.UnitOfPower.KILO_WATT,
    SensorDeviceClass.ENERGY: ha.UnitOfEnergy.KILO_WATT_HOUR,
}

# Home Assistant to OCPP UoM mapping
# Where a HA unit does not exist use Ocpp unit
UNITS_OCCP_TO_HA = {
    UnitOfMeasure.wh: ha.UnitOfEnergy.WATT_HOUR,
    UnitOfMeasure.kwh: ha.UnitOfEnergy.KILO_WATT_HOUR,
    UnitOfMeasure.varh: UnitOfMeasure.varh,
    UnitOfMeasure.kvarh: UnitOfMeasure.kvarh,
    UnitOfMeasure.w: ha.UnitOfPower.WATT,
    UnitOfMeasure.kw: ha.UnitOfPower.KILO_WATT,
    UnitOfMeasure.va: ha.UnitOfApparentPower.VOLT_AMPERE,
    UnitOfMeasure.kva: UnitOfMeasure.kva,
    UnitOfMeasure.var: UnitOfMeasure.var,
    UnitOfMeasure.kvar: UnitOfMeasure.kvar,
    UnitOfMeasure.a: ha.UnitOfElectricCurrent.AMPERE,
    UnitOfMeasure.v: ha.UnitOfElectricPotential.VOLT,
    UnitOfMeasure.celsius: ha.UnitOfTemperature.CELSIUS,
    UnitOfMeasure.fahrenheit: ha.UnitOfTemperature.FAHRENHEIT,
    UnitOfMeasure.k: ha.UnitOfTemperature.KELVIN,
    UnitOfMeasure.percent: ha.PERCENTAGE,
    UnitOfMeasure.hertz: ha.UnitOfFrequency.HERTZ,
}

# Home Assistant Charge Point Diagnostic sensors
HA_CHARGE_POINT_DIAGNOSTIC_SENSORS = [
    HAChargePointSensors.identifier.value,
    HAChargePointSensors.model.value,
    HAChargePointSensors.vendor.value,
    HAChargePointSensors.serial.value,
    HAChargePointSensors.firmware_version.value,
    HAChargePointSensors.features.value,
    HAChargePointSensors.connectors.value,
    HAChargePointSensors.data_response.value,
    HAChargePointSensors.data_transfer.value,
    HAChargePointSensors.config_response.value,
]

DOMAIN = "charge_advisor"
CONFIG = "config"
ICON = "mdi:ev-station"

# source: https://pictogrammers.com/library/mdi/
MEASURAND_ICON = {
    Measurand.energy_active_import_register.value: "mdi:lightning-bolt",
    Measurand.energy_active_import_interval.value: "mdi:lightning-bolt",
    Measurand.energy_reactive_import_register.value: "mdi:lightning-bolt",
    Measurand.energy_reactive_import_interval.value: "mdi:lightning-bolt",

    Measurand.energy_active_export_register.value: "mdi:lightning-bolt",
    Measurand.energy_active_export_interval.value: "mdi:lightning-bolt",
    Measurand.energy_reactive_export_register.value: "mdi:lightning-bolt",
    Measurand.energy_reactive_export_interval.value: "mdi:lightning-bolt",

    Measurand.power_active_import.value: "mdi:flash",
    Measurand.power_reactive_import.value: "mdi:flash",
    Measurand.power_offered.value: "mdi:flash",
    Measurand.power_active_export.value: "mdi:flash",
    Measurand.power_reactive_export.value: "mdi:flash",

    Measurand.power_factor.value: "mdi:angle-acute",

    Measurand.current_import.value: "mdi:current-ac",
    Measurand.current_offered.value: "mdi:current-ac",
    Measurand.current_export.value: "mdi:current-ac",

    Measurand.voltage.value: "mdi:transmission-tower",
    Measurand.frequency.value: "mdi:sine-wave",

    Measurand.rpm.value: "mdi:fan",
    Measurand.soc.value: "mdi:battery-charging",
    Measurand.temperature.value: "mdi:ev-station",
}

# CA SERVER CONFIGURATION




