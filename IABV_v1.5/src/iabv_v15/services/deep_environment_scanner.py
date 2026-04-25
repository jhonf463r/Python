"""Deep Environment Scanner — descubrimiento exhaustivo del entorno completo.

Escanea las capas que EnvironmentSelfAwarenessService y
full_system_metacognition.py NO cubren:
  - BIOS/Firmware/Placa base
  - Periféricos USB conectados
  - Impresoras (locales y de red)
  - Dispositivos de audio (entrada y salida)
  - Bluetooth (dispositivos pareados)
  - Monitores (resolución, DPI, disposición, marca)
  - Adaptadores de red (WiFi, Ethernet, VPN)
  - Seguridad (firewall, antivirus, permisos)
  - Servicios del OS (corriendo/detenidos)

Usa WMI (Win32_*) en Windows y /sys + /proc en Linux.
No requiere dependencias externas.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_WMI_TIMEOUT = 8


def _wmi_query(wmi_class: str, fields: list[str], *, timeout: int = _WMI_TIMEOUT) -> list[dict[str, str]]:
    """Run a WMI query via PowerShell and return parsed results."""
    field_str = ', '.join(fields)
    script = f"Get-CimInstance -ClassName {wmi_class} | Select-Object {field_str} | ConvertTo-Json -Compress"
    try:
        r = subprocess.run(
            ['powershell', '-NoProfile', '-Command', script],
            capture_output=True, text=True, timeout=timeout,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return []
        data = json.loads(r.stdout.strip())
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return [d for d in data if isinstance(d, dict)]
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    except Exception as exc:
        logger.debug('WMI query %s failed: %s', wmi_class, exc)
    return []


def _linux_read(path: str) -> str:
    """Read a /sys or /proc file safely."""
    try:
        return Path(path).read_text(encoding='utf-8', errors='replace').strip()
    except Exception:
        return ''


# ──────────────────────────────────────────────────────────────
# BIOS / Firmware / Motherboard
# ──────────────────────────────────────────────────────────────

def scan_bios_firmware() -> dict[str, Any]:
    """Scan BIOS/UEFI, motherboard, and chipset information."""
    result: dict[str, Any] = {'available': False}

    if os.name == 'nt':
        bios = _wmi_query('Win32_BIOS', ['Manufacturer', 'SMBIOSBIOSVersion', 'ReleaseDate', 'SerialNumber'])
        if bios:
            b = bios[0]
            result['available'] = True
            result['bios_manufacturer'] = b.get('Manufacturer', '')
            result['bios_version'] = b.get('SMBIOSBIOSVersion', '')
            result['bios_release_date'] = b.get('ReleaseDate', '')

        board = _wmi_query('Win32_BaseBoard', ['Manufacturer', 'Product', 'SerialNumber'])
        if board:
            bb = board[0]
            result['motherboard_manufacturer'] = bb.get('Manufacturer', '')
            result['motherboard_model'] = bb.get('Product', '')

        chipset = _wmi_query('Win32_SystemEnclosure', ['Manufacturer', 'ChassisTypes'])
        if chipset:
            result['chassis_manufacturer'] = chipset[0].get('Manufacturer', '')
            result['chassis_types'] = chipset[0].get('ChassisTypes', [])
    else:
        # Linux: /sys/class/dmi/id/
        dmi = Path('/sys/class/dmi/id')
        if dmi.exists():
            result['available'] = True
            result['bios_vendor'] = _linux_read(str(dmi / 'bios_vendor'))
            result['bios_version'] = _linux_read(str(dmi / 'bios_version'))
            result['bios_date'] = _linux_read(str(dmi / 'bios_date'))
            result['board_vendor'] = _linux_read(str(dmi / 'board_vendor'))
            result['board_name'] = _linux_read(str(dmi / 'board_name'))

    return result


# ──────────────────────────────────────────────────────────────
# USB Devices
# ──────────────────────────────────────────────────────────────

def scan_usb_devices() -> list[dict[str, Any]]:
    """Detect all USB devices connected to the system."""
    devices: list[dict[str, Any]] = []

    if os.name == 'nt':
        pnp = _wmi_query(
            'Win32_PnPEntity',
            ['Name', 'Manufacturer', 'DeviceID', 'Status', 'PNPClass'],
            timeout=12,
        )
        for d in pnp:
            device_id = str(d.get('DeviceID', ''))
            if 'USB' in device_id.upper():
                devices.append({
                    'name': d.get('Name', ''),
                    'manufacturer': d.get('Manufacturer', ''),
                    'device_id': device_id[:80],
                    'status': d.get('Status', ''),
                    'class': d.get('PNPClass', ''),
                })
    else:
        try:
            r = subprocess.run(['lsusb'], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                for line in r.stdout.strip().splitlines():
                    m = re.match(r'Bus (\d+) Device (\d+): ID (\S+) (.+)', line)
                    if m:
                        devices.append({
                            'bus': m.group(1),
                            'device': m.group(2),
                            'id': m.group(3),
                            'name': m.group(4),
                        })
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return devices


# ──────────────────────────────────────────────────────────────
# Printers
# ──────────────────────────────────────────────────────────────

def scan_printers() -> list[dict[str, Any]]:
    """Detect all installed printers (local and network)."""
    printers: list[dict[str, Any]] = []

    if os.name == 'nt':
        raw = _wmi_query('Win32_Printer', ['Name', 'DriverName', 'PortName', 'PrinterStatus', 'Default', 'Network'])
        for p in raw:
            printers.append({
                'name': p.get('Name', ''),
                'driver': p.get('DriverName', ''),
                'port': p.get('PortName', ''),
                'status': p.get('PrinterStatus', ''),
                'is_default': bool(p.get('Default')),
                'is_network': bool(p.get('Network')),
            })
    else:
        try:
            r = subprocess.run(['lpstat', '-a'], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                for line in r.stdout.strip().splitlines():
                    parts = line.split()
                    if parts:
                        printers.append({'name': parts[0], 'status': ' '.join(parts[1:])})
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return printers


# ──────────────────────────────────────────────────────────────
# Audio Devices
# ──────────────────────────────────────────────────────────────

def scan_audio_devices() -> list[dict[str, Any]]:
    """Detect audio input/output devices."""
    devices: list[dict[str, Any]] = []

    if os.name == 'nt':
        raw = _wmi_query('Win32_SoundDevice', ['Name', 'Manufacturer', 'Status', 'DeviceID'])
        for d in raw:
            devices.append({
                'name': d.get('Name', ''),
                'manufacturer': d.get('Manufacturer', ''),
                'status': d.get('Status', ''),
                'type': 'sound_device',
            })
        # Also check audio endpoints via PowerShell
        try:
            r = subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 'Get-CimInstance -Namespace root/cimv2 -ClassName Win32_SoundDevice | '
                 'Select-Object Name, Status | ConvertTo-Json -Compress'],
                capture_output=True, text=True, timeout=5,
            )
        except Exception:
            pass
    else:
        # Linux: check /proc/asound or aplay
        try:
            r = subprocess.run(['aplay', '-l'], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                for line in r.stdout.strip().splitlines():
                    if line.startswith('card'):
                        devices.append({'name': line.strip(), 'type': 'output'})
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        try:
            r = subprocess.run(['arecord', '-l'], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                for line in r.stdout.strip().splitlines():
                    if line.startswith('card'):
                        devices.append({'name': line.strip(), 'type': 'input'})
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return devices


# ──────────────────────────────────────────────────────────────
# Bluetooth
# ──────────────────────────────────────────────────────────────

def scan_bluetooth_devices() -> dict[str, Any]:
    """Detect Bluetooth adapter and paired devices."""
    result: dict[str, Any] = {'adapter_present': False, 'paired_devices': []}

    if os.name == 'nt':
        adapters = _wmi_query('Win32_PnPEntity', ['Name', 'Status', 'DeviceID'])
        bt_adapters = [a for a in adapters if 'bluetooth' in str(a.get('Name', '')).lower()]
        if bt_adapters:
            result['adapter_present'] = True
            result['adapter_name'] = bt_adapters[0].get('Name', '')
            result['adapter_status'] = bt_adapters[0].get('Status', '')
        # Paired devices via PowerShell BluetoothDevice
        try:
            r = subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 'Get-PnpDevice -Class Bluetooth | Select-Object FriendlyName, Status | ConvertTo-Json -Compress'],
                capture_output=True, text=True, timeout=8,
            )
            if r.returncode == 0 and r.stdout.strip():
                data = json.loads(r.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for d in data:
                    if isinstance(d, dict) and d.get('FriendlyName'):
                        result['paired_devices'].append({
                            'name': d['FriendlyName'],
                            'status': d.get('Status', ''),
                        })
        except Exception:
            pass
    else:
        try:
            r = subprocess.run(['bluetoothctl', 'devices'], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                result['adapter_present'] = True
                for line in r.stdout.strip().splitlines():
                    parts = line.split(maxsplit=2)
                    if len(parts) >= 3:
                        result['paired_devices'].append({'mac': parts[1], 'name': parts[2]})
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return result


# ──────────────────────────────────────────────────────────────
# Monitors (Deep)
# ──────────────────────────────────────────────────────────────

def scan_monitors_deep() -> list[dict[str, Any]]:
    """Detect all monitors with resolution, refresh rate, DPI, and model."""
    monitors: list[dict[str, Any]] = []

    if os.name == 'nt':
        raw = _wmi_query(
            'Win32_DesktopMonitor',
            ['Name', 'ScreenHeight', 'ScreenWidth', 'MonitorManufacturer', 'MonitorType', 'DeviceID'],
        )
        for m in raw:
            monitors.append({
                'name': m.get('Name', ''),
                'width': m.get('ScreenWidth'),
                'height': m.get('ScreenHeight'),
                'manufacturer': m.get('MonitorManufacturer', ''),
                'type': m.get('MonitorType', ''),
            })
        # Supplement with video controller for refresh rate
        vc = _wmi_query('Win32_VideoController', ['Name', 'CurrentRefreshRate', 'CurrentHorizontalResolution',
                                                    'CurrentVerticalResolution', 'AdapterRAM'])
        for v in vc:
            monitors.append({
                'gpu_name': v.get('Name', ''),
                'current_resolution': f"{v.get('CurrentHorizontalResolution', '?')}x{v.get('CurrentVerticalResolution', '?')}",
                'refresh_rate_hz': v.get('CurrentRefreshRate'),
                'adapter_ram_bytes': v.get('AdapterRAM'),
                'source': 'video_controller',
            })
    else:
        try:
            r = subprocess.run(['xrandr', '--query'], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                current_monitor: dict[str, Any] | None = None
                for line in r.stdout.splitlines():
                    if ' connected' in line:
                        parts = line.split()
                        current_monitor = {'name': parts[0], 'connected': True}
                        monitors.append(current_monitor)
                    elif current_monitor and '*' in line:
                        res = line.strip().split()[0]
                        current_monitor['active_resolution'] = res
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return monitors


# ──────────────────────────────────────────────────────────────
# Network Adapters (Deep)
# ──────────────────────────────────────────────────────────────

def scan_network_adapters() -> list[dict[str, Any]]:
    """Detect all network adapters with type, speed, and IP configuration."""
    adapters: list[dict[str, Any]] = []

    if os.name == 'nt':
        raw = _wmi_query(
            'Win32_NetworkAdapterConfiguration',
            ['Description', 'IPEnabled', 'IPAddress', 'MACAddress',
             'DHCPEnabled', 'DefaultIPGateway', 'DNSServerSearchOrder'],
            timeout=10,
        )
        for a in raw:
            if not a.get('IPEnabled'):
                continue
            adapters.append({
                'name': a.get('Description', ''),
                'ip_enabled': True,
                'ip_addresses': a.get('IPAddress', []),
                'mac_address': a.get('MACAddress', ''),
                'dhcp_enabled': bool(a.get('DHCPEnabled')),
                'gateway': a.get('DefaultIPGateway', []),
                'dns_servers': a.get('DNSServerSearchOrder', []),
                'type': _classify_adapter(str(a.get('Description', ''))),
            })
    else:
        try:
            r = subprocess.run(['ip', '-j', 'addr'], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                for iface in json.loads(r.stdout):
                    if iface.get('operstate') == 'UP':
                        addrs = [a['local'] for a in iface.get('addr_info', []) if 'local' in a]
                        adapters.append({
                            'name': iface.get('ifname', ''),
                            'type': _classify_adapter(str(iface.get('ifname', ''))),
                            'ip_addresses': addrs,
                            'mac_address': iface.get('address', ''),
                        })
        except Exception:
            pass

    return adapters


def _classify_adapter(name: str) -> str:
    """Classify a network adapter as WiFi, Ethernet, VPN, etc."""
    n = name.lower()
    if any(kw in n for kw in ('wi-fi', 'wifi', 'wireless', 'wlan', 'wl')):
        return 'wifi'
    if any(kw in n for kw in ('ethernet', 'eth', 'realtek', 'intel(r) ethernet', 'lan')):
        return 'ethernet'
    if any(kw in n for kw in ('vpn', 'tunnel', 'tun', 'tap', 'wireguard', 'openvpn')):
        return 'vpn'
    if any(kw in n for kw in ('bluetooth', 'bn')):
        return 'bluetooth'
    if 'loopback' in n or n == 'lo':
        return 'loopback'
    return 'other'


# ──────────────────────────────────────────────────────────────
# Security (Firewall, Antivirus, Permissions)
# ──────────────────────────────────────────────────────────────

def scan_security_state() -> dict[str, Any]:
    """Scan firewall, antivirus, and user permission state."""
    result: dict[str, Any] = {'firewall': {}, 'antivirus': [], 'user_permissions': {}}

    if os.name == 'nt':
        # Firewall
        try:
            r = subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 'Get-NetFirewallProfile | Select-Object Name, Enabled | ConvertTo-Json -Compress'],
                capture_output=True, text=True, timeout=8,
            )
            if r.returncode == 0 and r.stdout.strip():
                data = json.loads(r.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                result['firewall'] = {
                    'profiles': [{
                        'name': p.get('Name', ''),
                        'enabled': bool(p.get('Enabled')),
                    } for p in data if isinstance(p, dict)],
                }
        except Exception:
            result['firewall'] = {'error': 'could_not_query'}

        # Antivirus via Security Center
        av = _wmi_query('AntiVirusProduct', ['displayName', 'productState'],
                         timeout=5)
        if not av:
            # Try WMI namespace root/SecurityCenter2
            try:
                r = subprocess.run(
                    ['powershell', '-NoProfile', '-Command',
                     'Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct | '
                     'Select-Object displayName, productState | ConvertTo-Json -Compress'],
                    capture_output=True, text=True, timeout=8,
                )
                if r.returncode == 0 and r.stdout.strip():
                    av_data = json.loads(r.stdout.strip())
                    if isinstance(av_data, dict):
                        av_data = [av_data]
                    for a in av_data:
                        if isinstance(a, dict):
                            result['antivirus'].append({
                                'name': a.get('displayName', ''),
                                'state': a.get('productState', ''),
                            })
            except Exception:
                pass
        else:
            for a in av:
                result['antivirus'].append({
                    'name': a.get('displayName', ''),
                    'state': a.get('productState', ''),
                })

        # User permissions
        try:
            import ctypes
            result['user_permissions']['is_admin'] = bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            result['user_permissions']['is_admin'] = None

        try:
            r = subprocess.run(['whoami', '/groups'], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                result['user_permissions']['is_elevated'] = 'S-1-16-12288' in r.stdout
        except Exception:
            pass
    else:
        # Linux
        try:
            result['user_permissions']['uid'] = os.getuid()
            result['user_permissions']['is_root'] = os.getuid() == 0
        except Exception:
            pass
        try:
            r = subprocess.run(['ufw', 'status'], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                result['firewall']['ufw'] = r.stdout.strip()[:200]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return result


# ──────────────────────────────────────────────────────────────
# OS Services
# ──────────────────────────────────────────────────────────────

def scan_os_services() -> dict[str, Any]:
    """Scan running/stopped services relevant to IABV."""
    result: dict[str, Any] = {'relevant_services': [], 'total_running': 0}

    relevant_keywords = [
        'ollama', 'docker', 'postgresql', 'mysql', 'redis', 'mongodb',
        'ssh', 'nginx', 'apache', 'iis', 'cloudflare', 'openvpn',
        'wireguard', 'bluetooth', 'audio', 'print', 'spooler',
    ]

    if os.name == 'nt':
        raw = _wmi_query('Win32_Service', ['Name', 'DisplayName', 'State', 'StartMode'], timeout=12)
        running_count = sum(1 for s in raw if s.get('State') == 'Running')
        result['total_running'] = running_count
        result['total_services'] = len(raw)
        for s in raw:
            name = str(s.get('DisplayName', '') or s.get('Name', '')).lower()
            if any(kw in name for kw in relevant_keywords):
                result['relevant_services'].append({
                    'name': s.get('DisplayName', ''),
                    'state': s.get('State', ''),
                    'start_mode': s.get('StartMode', ''),
                })
    else:
        try:
            r = subprocess.run(
                ['systemctl', 'list-units', '--type=service', '--state=running', '--no-pager', '--plain'],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                lines = r.stdout.strip().splitlines()
                result['total_running'] = len([l for l in lines if '.service' in l])
                for line in lines:
                    name = line.split()[0] if line.split() else ''
                    if any(kw in name.lower() for kw in relevant_keywords):
                        result['relevant_services'].append({
                            'name': name, 'state': 'running',
                        })
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return result


# ──────────────────────────────────────────────────────────────
# COMPLETE DEEP SCAN
# ──────────────────────────────────────────────────────────────

def deep_environment_scan() -> dict[str, Any]:
    """Run ALL deep environment scans and return a unified report.

    This covers the blind spots that EnvironmentSelfAwarenessService and
    full_system_metacognition.py don't cover.
    """
    report: dict[str, Any] = {}
    scan_errors: list[str] = []

    scans = [
        ('bios_firmware', scan_bios_firmware),
        ('usb_devices', scan_usb_devices),
        ('printers', scan_printers),
        ('audio_devices', scan_audio_devices),
        ('bluetooth', scan_bluetooth_devices),
        ('monitors_deep', scan_monitors_deep),
        ('network_adapters', scan_network_adapters),
        ('security', scan_security_state),
        ('os_services', scan_os_services),
    ]

    for key, fn in scans:
        try:
            report[key] = fn()
        except Exception as exc:
            report[key] = {'error': str(exc)[:200]}
            scan_errors.append(f'{key}: {exc!r}'[:100])

    def _safe_list(key: str) -> list:
        """Return scan result as list, or [] if it's an error dict."""
        val = report.get(key, [])
        return val if isinstance(val, list) else []

    def _safe_dict(key: str) -> dict:
        """Return scan result as dict, or {} if it failed."""
        val = report.get(key, {})
        if not isinstance(val, dict) or 'error' in val:
            return {}
        return val

    # Summary
    usb_count = len(_safe_list('usb_devices'))
    printer_count = len(_safe_list('printers'))
    audio_count = len(_safe_list('audio_devices'))
    bt_paired = len(_safe_dict('bluetooth').get('paired_devices', []))
    monitor_count = len([m for m in _safe_list('monitors_deep') if isinstance(m, dict) and m.get('source') != 'video_controller'])
    net_count = len(_safe_list('network_adapters'))
    service_count = _safe_dict('os_services').get('total_running', 0)

    report['summary'] = {
        'usb_devices': usb_count,
        'printers': printer_count,
        'audio_devices': audio_count,
        'bluetooth_paired': bt_paired,
        'monitors': monitor_count,
        'network_adapters': net_count,
        'services_running': service_count,
        'bios_available': bool(_safe_dict('bios_firmware').get('available')),
        'scan_errors': len(scan_errors),
        'coverage_estimate': _estimate_coverage(report),
    }
    if scan_errors:
        report['scan_errors'] = scan_errors

    return report


def _estimate_coverage(report: dict[str, Any]) -> float:
    """Estimate what percentage of the environment was successfully scanned."""
    total = 9  # 9 scan categories

    def _has_data(key: str) -> bool:
        val = report.get(key)
        if val is None:
            return False
        if isinstance(val, dict) and 'error' in val:
            return False
        if isinstance(val, list) and len(val) == 0:
            return False
        return True

    non_empty = 0
    if isinstance(report.get('usb_devices'), list) and report['usb_devices']:
        non_empty += 1
    if isinstance(report.get('printers'), list) and report['printers']:
        non_empty += 1
    if isinstance(report.get('audio_devices'), list) and report['audio_devices']:
        non_empty += 1
    bt = report.get('bluetooth')
    if isinstance(bt, dict) and 'error' not in bt and bt.get('adapter_present'):
        non_empty += 1
    if isinstance(report.get('monitors_deep'), list) and report['monitors_deep']:
        non_empty += 1
    if isinstance(report.get('network_adapters'), list) and report['network_adapters']:
        non_empty += 1
    bios = report.get('bios_firmware')
    if isinstance(bios, dict) and 'error' not in bios and bios.get('available'):
        non_empty += 1
    sec = report.get('security')
    if isinstance(sec, dict) and 'error' not in sec and sec.get('firewall'):
        non_empty += 1
    svc = report.get('os_services')
    if isinstance(svc, dict) and 'error' not in svc and svc.get('total_running', 0) > 0:
        non_empty += 1

    return round(non_empty / max(total, 1), 2)


def format_deep_scan_report(scan: dict[str, Any]) -> str:
    """Format deep scan results for the auto-analysis report."""
    lines: list[str] = []
    summary = scan.get('summary', {})

    lines.append('== DESCUBRIMIENTO PROFUNDO DEL ENTORNO ==')

    # BIOS
    bios = scan.get('bios_firmware', {})
    if bios.get('available'):
        mfr = bios.get('bios_manufacturer') or bios.get('bios_vendor', '')
        ver = bios.get('bios_version', '')
        board_mfr = bios.get('motherboard_manufacturer') or bios.get('board_vendor', '')
        board_model = bios.get('motherboard_model') or bios.get('board_name', '')
        lines.append(f'  BIOS: {mfr} {ver}')
        if board_mfr:
            lines.append(f'  Placa base: {board_mfr} {board_model}')

    # USB
    usb_count = summary.get('usb_devices', 0)
    if usb_count > 0:
        lines.append(f'  USB: {usb_count} dispositivos conectados')
        for d in scan.get('usb_devices', [])[:5]:
            lines.append(f'    - {d.get("name", "?")} ({d.get("class", d.get("id", ""))})')

    # Printers
    printer_count = summary.get('printers', 0)
    if printer_count > 0:
        lines.append(f'  Impresoras: {printer_count}')
        for p in scan.get('printers', []):
            default = ' [DEFAULT]' if p.get('is_default') else ''
            net = ' [RED]' if p.get('is_network') else ''
            lines.append(f'    - {p.get("name", "?")}{default}{net}')

    # Audio
    audio_count = summary.get('audio_devices', 0)
    if audio_count > 0:
        lines.append(f'  Audio: {audio_count} dispositivos')
        for d in scan.get('audio_devices', []):
            lines.append(f'    - {d.get("name", "?")}')

    # Bluetooth
    bt = scan.get('bluetooth', {})
    if bt.get('adapter_present'):
        lines.append(f'  Bluetooth: adaptador presente ({bt.get("adapter_name", "?")})')
        for d in bt.get('paired_devices', []):
            lines.append(f'    - {d.get("name", "?")} [{d.get("status", "")}]')
    else:
        lines.append('  Bluetooth: no detectado')

    # Monitors
    monitors = [m for m in scan.get('monitors_deep', []) if m.get('source') != 'video_controller']
    if monitors:
        lines.append(f'  Monitores: {len(monitors)}')
        for m in monitors:
            res = f'{m.get("width", "?")}x{m.get("height", "?")}' if m.get('width') else m.get('active_resolution', '?')
            lines.append(f'    - {m.get("name", "?")} {res} ({m.get("manufacturer", "")})')

    # Network
    net_adapters = scan.get('network_adapters', [])
    if net_adapters:
        lines.append(f'  Red: {len(net_adapters)} adaptadores activos')
        for a in net_adapters:
            ips = ', '.join(str(ip) for ip in (a.get('ip_addresses') or [])[:2])
            lines.append(f'    - [{a.get("type", "?")}] {a.get("name", "?")[:50]} ({ips})')

    # Security
    sec = scan.get('security', {})
    fw_profiles = (sec.get('firewall', {}) or {}).get('profiles', [])
    if fw_profiles:
        active = sum(1 for p in fw_profiles if p.get('enabled'))
        lines.append(f'  Firewall: {active}/{len(fw_profiles)} perfiles activos')
    avs = sec.get('antivirus', [])
    if avs:
        lines.append(f'  Antivirus: {", ".join(a.get("name", "?") for a in avs)}')
    perms = sec.get('user_permissions', {})
    if perms.get('is_admin') is not None:
        lines.append(f'  Permisos: {"Admin" if perms["is_admin"] else "Usuario normal"}')

    # Services
    svc = scan.get('os_services', {})
    if svc.get('total_running'):
        lines.append(f'  Servicios: {svc["total_running"]} corriendo')
        for s in svc.get('relevant_services', []):
            lines.append(f'    - {s.get("name", "?")} [{s.get("state", "")}]')

    # Coverage
    lines.append(f'  Cobertura del escaneo profundo: {summary.get("coverage_estimate", 0):.0%}')

    return '\n'.join(lines)
