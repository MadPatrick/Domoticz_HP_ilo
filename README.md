# HP Integrated Lights-Out (iLO) – Domoticz Plugin

A Domoticz Python plugin to read sensor data from an HP iLO interface.

---

## Requirements

- Domoticz with Python plugin support (version 2020.2 or newer recommended)
- Python 3
- The `python-hpilo` Python library

### Install the Python library

```bash
pip3 install python-hpilo
```

---

## Installation

1. Navigate to the Domoticz plugins directory:

   ```bash
   cd /home/<user>/domoticz/plugins
   ```

2. Create a directory for the plugin and place `plugin.py` in it:

   ```bash
   mkdir HP_ilo
   cd HP_ilo
   # Copy plugin.py into this directory, or clone the repository:
   git clone https://github.com/MadPatrick/HP_ilo.git .
   ```

3. Restart Domoticz:

   ```bash
   sudo systemctl restart domoticz
   ```

---

## Configuration

In Domoticz, go to **Settings → Hardware** and add a new hardware device of type **HP Integrated Lights-Out (iLO)**.

| Parameter | Description | Default |
|-----------|-------------|-----------|
| IP Address / Hostname | The IP address or hostname of the iLO interface | `192.168.1.1` |
| Port | TCP port of the iLO interface | `443` |
| Username | iLO login username | `Administrator` |
| Password | iLO login password | *(empty)* |
| Poll Interval (sec) | How often data is retrieved (10–3600 sec) | `300` |
| Debug | Enable or disable verbose logging | `Off` |

---

## Created devices

After the first successful connection, the following Domoticz devices are created automatically:

| Unit | Name | Description |
|------|------|-------------|
| 1 | Server Name | Name of the server |
| 2 | Server FQDN | Fully qualified domain name |
| 3 | Server Power State | Power status (on/off) |
| 4 | Server Power Readings | Current, average, max, and min power |
| 5 | Server Power On Time (min) | Time powered on in minutes |
| 6 | Server Asset Tag | Server asset tag |
| 7 | Server UID Light | UID light status |
| 8 | Server Health | Hardware health overview |
| 9 | Network Settings | IP address, subnet mask, gateway, DNS, and MAC |
| 10 | Server Host Data | Raw host data |
| 11 | Server OA Info | Onboard Administrator information |

---

## Troubleshooting

- **iLO login failed** – Verify the username and password.
- **iLO communication error** – Check the IP address, port, and whether iLO is reachable from the Domoticz server.
- Enable **Debug** in hardware settings for detailed log messages in the Domoticz log.

---

## License

This project was ported from the [Home Assistant HP iLO integration](https://www.home-assistant.io/integrations/hp_ilo).
