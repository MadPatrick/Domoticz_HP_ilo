"""
HP Integrated Lights-Out (iLO) - Domoticz Python Plugin
Ported from Home Assistant integration.

Author: Ported from HA hp_ilo integration
Version: 1.0.0

<plugin key="hp_ilo" name="HP Integrated Lights-Out (iLO)" author="hp_ilo_port"
        version="1.0.0" externallink="https://www.home-assistant.io/integrations/hp_ilo">
    <description>
        <h2>HP Integrated Lights-Out (iLO)</h2>
        Leest sensordata uit van een HP iLO interface.
        <h3>Parameters</h3>
        Vul hieronder de verbindingsgegevens in voor uw HP iLO interface.
    </description>
    <params>
        <param field="Address"  label="IP-adres / Hostnaam" width="200px" required="true" default="192.168.1.1"/>
        <param field="Port"     label="Poort"               width="75px"  required="true" default="443"/>
        <param field="Username" label="Gebruikersnaam"      width="150px" required="true" default="Administrator"/>
        <param field="Password" label="Wachtwoord"          width="150px" required="true" default="" password="true"/>
        <param field="Mode1"    label="Poll-interval (sec)" width="75px"  required="true" default="300"/>
        <param field="Mode6"    label="Debug"               width="100px">
            <options>
                <option label="Uit"  value="0" default="true"/>
                <option label="Aan"  value="1"/>
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz  # type: ignore  # alleen beschikbaar binnen Domoticz runtime
import hpilo
from datetime import datetime

# ---------------------------------------------------------------------------
# Apparaat-unit nummers (1-255, uniek per plugin-instantie)
# ---------------------------------------------------------------------------
UNIT_SERVER_NAME         = 1
UNIT_SERVER_FQDN         = 2
UNIT_POWER_STATUS        = 3
UNIT_POWER_READINGS      = 4
UNIT_POWER_ON_TIME       = 5
UNIT_ASSET_TAG           = 6
UNIT_UID_STATUS          = 7
UNIT_HEALTH              = 8
UNIT_NETWORK_SETTINGS    = 9
UNIT_SERVER_HOST_DATA    = 10
UNIT_OA_INFO             = 11

# Definitie: (unit, naam, type, subtype, opties-dict of None)
#   Domoticz type 243 = Algemeen, subtype 19 = Tekst
SENSOR_DEFINITIONS = [
    (UNIT_SERVER_NAME,      "Server Name",                    243, 19, {}),
    (UNIT_SERVER_FQDN,      "Server FQDN",                    243, 19, {}),
    (UNIT_POWER_STATUS,     "Server Power State",             243, 19, {}),
    (UNIT_POWER_READINGS,   "Server Power Readings",          243, 19, {}),
    (UNIT_POWER_ON_TIME,    "Server Power On Time (min)",     243, 31, {}),  # 31 = Custom
    (UNIT_ASSET_TAG,        "Server Asset Tag",               243, 19, {}),
    (UNIT_UID_STATUS,       "Server UID Light",               243, 19, {}),
    (UNIT_HEALTH,           "Server Health",                  243, 19, {}),
    (UNIT_NETWORK_SETTINGS, "Network Settings",               243, 19, {}),
    (UNIT_SERVER_HOST_DATA, "Server Host Data",               243, 19, {}),
    (UNIT_OA_INFO,          "Server OA Info",                 243, 19, {}),
]


class BasePlugin:
    """Hoofd-plugin klasse die door Domoticz wordt aangeroepen."""

    def __init__(self):
        self._ilo = None
        self._poll_interval = 300  # seconden
        self._heartbeat_count = 0
        self._heartbeats_per_poll = 1
        self._debug = False

    # ------------------------------------------------------------------
    # Lifecycle-callbacks
    # ------------------------------------------------------------------

    def onStart(self):
        self._debug = Parameters["Mode6"] == "1"
        if self._debug:
            Domoticz.Debugging(1)
            Domoticz.Log("Debug-modus ingeschakeld")

        # Poll-interval instellen (minimaal 10 sec, maximaal 3600 sec)
        try:
            self._poll_interval = max(10, min(3600, int(Parameters["Mode1"])))
        except ValueError:
            self._poll_interval = 300

        # Domoticz heartbeat is standaard 10 seconden
        heartbeat_sec = 10
        self._heartbeats_per_poll = max(1, self._poll_interval // heartbeat_sec)
        Domoticz.Heartbeat(heartbeat_sec)

        Domoticz.Log(
            f"HP iLO plugin gestart - host={Parameters['Address']}:{Parameters['Port']} "
            f"poll={self._poll_interval}s"
        )

        # Ontbrekende Domoticz-apparaten aanmaken
        self._create_devices()

        # Directe eerste verbinding
        self._connect_and_update()

    def onStop(self):
        Domoticz.Log("HP iLO plugin gestopt.")

    def onHeartbeat(self):
        self._heartbeat_count += 1
        if self._heartbeat_count >= self._heartbeats_per_poll:
            self._heartbeat_count = 0
            self._connect_and_update()

    # ------------------------------------------------------------------
    # Interne hulpfuncties
    # ------------------------------------------------------------------

    def _create_devices(self):
        """Maak ontbrekende Domoticz-apparaten aan."""
        for unit, name, type_num, subtype, options in SENSOR_DEFINITIONS:
            if unit not in Devices:
                Domoticz.Device(
                    Name=name,
                    Unit=unit,
                    Type=type_num,
                    Subtype=subtype,
                    Options=options,
                    Used=1,
                ).Create()
                Domoticz.Log(f"Apparaat aangemaakt: {name} (unit {unit})")

    def _connect_and_update(self):
        """Maak verbinding met iLO en ververs alle sensoren."""
        host     = Parameters["Address"]
        port     = int(Parameters["Port"])
        login    = Parameters["Username"]
        password = Parameters["Password"]

        try:
            ilo = hpilo.Ilo(
                hostname=host,
                login=login,
                password=password,
                port=port,
            )
            self._fetch_and_push(ilo)
        except hpilo.IloLoginFailed as err:
            Domoticz.Error(f"iLO login mislukt: {err}")
        except hpilo.IloCommunicationError as err:
            Domoticz.Error(f"iLO communicatiefout: {err}")
        except hpilo.IloError as err:
            Domoticz.Error(f"iLO fout: {err}")
        except Exception as err:  # noqa: BLE001
            Domoticz.Error(f"Onverwachte fout bij iLO-verbinding: {err}")

    def _fetch_and_push(self, ilo: hpilo.Ilo):
        """Haal iLO-data op en sla op in Domoticz-apparaten."""

        def safe_get(func, *args, default="N/A"):
            """Roep iLO-methode aan en vang fouten op."""
            try:
                result = func(*args)
                return result if result is not None else default
            except Exception as err:  # noqa: BLE001
                Domoticz.Error(f"Fout bij {func.__name__}: {err}")
                return default

        def update(unit, value):
            """Ververs Domoticz-apparaat als het bestaat."""
            if unit in Devices:
                svalue = str(value) if not isinstance(value, str) else value
                Devices[unit].Update(nValue=0, sValue=svalue)
                if self._debug:
                    Domoticz.Log(f"Unit {unit} bijgewerkt: {svalue[:120]}")

        # --- Server naam & FQDN ---
        update(UNIT_SERVER_NAME, safe_get(ilo.get_server_name))
        update(UNIT_SERVER_FQDN, safe_get(ilo.get_server_fqdn))

        # --- Voedingsstatus ---
        power_status = safe_get(ilo.get_host_power_status)
        update(UNIT_POWER_STATUS, power_status)

        # --- Vermogensmetingen ---
        power_readings = safe_get(ilo.get_power_readings)
        if isinstance(power_readings, dict):
            # Formatteer de meest relevante waarden als leesbare tekst
            parts = []
            for key in ("present_power_reading", "average_power_reading",
                        "maximum_power_reading", "minimum_power_reading"):
                if key in power_readings:
                    label = key.replace("_", " ").title()
                    val   = power_readings[key]
                    # Waarde kan een dict zijn met 'value' en 'unit'
                    if isinstance(val, dict):
                        parts.append(f"{label}: {val.get('value', '?')} {val.get('unit', '')}")
                    else:
                        parts.append(f"{label}: {val}")
            update(UNIT_POWER_READINGS, " | ".join(parts) if parts else str(power_readings))
        else:
            update(UNIT_POWER_READINGS, str(power_readings))

        # --- Ingeschakeld sinds (minuten) ---
        power_on_time = safe_get(ilo.get_server_power_on_time, default=0)
        update(UNIT_POWER_ON_TIME, power_on_time)

        # --- Asset tag ---
        update(UNIT_ASSET_TAG, safe_get(ilo.get_asset_tag))

        # --- UID-status ---
        update(UNIT_UID_STATUS, safe_get(ilo.get_uid_status))

        # --- Gezondheid ---
        health = safe_get(ilo.get_embedded_health)
        if isinstance(health, dict):
            # Haal de samenvatting op als die bestaat
            summary = health.get("health_at_a_glance", health)
            update(UNIT_HEALTH, str(summary)[:500])
        else:
            update(UNIT_HEALTH, str(health)[:500])

        # --- Netwerkinstellingen ---
        net = safe_get(ilo.get_network_settings)
        if isinstance(net, dict):
            parts = []
            for key in ("ip_address", "subnet_mask", "gateway_ip_address",
                        "dns_name", "mac_address"):
                if key in net:
                    parts.append(f"{key.replace('_',' ').title()}: {net[key]}")
            update(UNIT_NETWORK_SETTINGS, " | ".join(parts) if parts else str(net)[:500])
        else:
            update(UNIT_NETWORK_SETTINGS, str(net)[:500])

        # --- Host data & OA info ---
        host_data = safe_get(ilo.get_host_data)
        update(UNIT_SERVER_HOST_DATA, str(host_data)[:500])

        oa_info = safe_get(ilo.get_oa_info)
        update(UNIT_OA_INFO, str(oa_info)[:500])

        Domoticz.Log("HP iLO sensoren bijgewerkt.")


# ---------------------------------------------------------------------------
# Domoticz plugin-interface - verplichte globale functies
# ---------------------------------------------------------------------------

_plugin = BasePlugin()


def onStart():
    _plugin.onStart()


def onStop():
    _plugin.onStop()


def onHeartbeat():
    _plugin.onHeartbeat()
