"""
La classe HomeAssistantMetric si occupa di gestire le metriche di Home Assistant, ovverosia quei valori delle grandezze
che sottendono a definire lo stato delle entità di Home Assistant (Switch, Sensor, Button, Number, ecc.)
"""

# ----------------------------------------------------------------------------------------------------------------------
# Python packages
# ----------------------------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------------------------
# Home Assistant packages
# ----------------------------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------------------------
# External packages
# ----------------------------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------------------------
# Local packages
# ----------------------------------------------------------------------------------------------------------------------

from ocpp_central_system.metric import *

# ----------------------------------------------------------------------------------------------------------------------
# Local files
# ----------------------------------------------------------------------------------------------------------------------
from .logger import OcppLog
from .const import UNITS_OCCP_TO_HA


class HomeAssistantEntityMetrics(EntityMetrics):

    def __init__(self):
        # Home Assistant metrics needed to evaluate the entities (switches, buttons, etc.) states
        self._metrics = defaultdict(lambda: HomeAssistantMetric(None, None))

    # Questa funzione restituisce il valore di una metrica in base alla chiave
    # se la metrica non è trovata, restiuisce None
    def get_metric_ha_unit(self, key):
        metric = self.get_metric(key)
        return metric.ha_unit if metric is not None else None


class HomeAssistantMetric(Metric):
    """Metric class."""

    @property
    def ha_unit(self):
        """Get the home assistant unit of the metric."""
        return UNITS_OCCP_TO_HA.get(self._unit, None)