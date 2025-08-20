import subprocess
import time
import winreg

startupinfo = subprocess.STARTUPINFO()
startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

def disable_services():
    """Disables selected services."""
    services = [
        "bthserv",  # Bluetooth Support Service
        "TermService",  # Remote Desktop Services
        "RemoteAccess",  # Routing and Remote Access
        "WFDSConMgrSvc",  # Wi-Fi Direct Services
        "xbgm",  # Xbox Game Monitoring
        "XblAuthManager",  # Xbox Live Auth Manager
        "XboxNetApiSvc",  # Xbox Live Networking Service
        "XblGameSave",  # Xbox Live Game Save
    ]
    
    disabled_services = []
    failed_services = []
    
    for service in services:
        result = subprocess.run(
            ["sc", "config", service, "start=", "disabled"],
            capture_output=True,
            text=True,
            startupinfo=startupinfo
        )
        if "SUCCESS" in result.stdout:
            disabled_services.append(service)
        else:
            failed_services.append(service)
    
    return disabled_services, failed_services

def enable_services():
    """Enables and starts selected services."""
    services = [
        "bthserv",
        "TermService",
        "RemoteAccess",
        "WFDSConMgrSvc",
        "xbgm",
        "XblAuthManager",
        "XboxNetApiSvc",
        "XblGameSave"
    ]

    enabled_services = []
    failed_services = []

    for service in services:
        try:
            config_result = subprocess.run(
                ["sc", "config", service, "start=", "auto"],
                capture_output=True,
                text=True,
                timeout=10,
                startupinfo=startupinfo
            )

            if "SUCCESS" not in config_result.stdout:
                failed_services.append(f"{service} (config failed)")
                continue

            subprocess.run(
                ["sc", "start", service],
                capture_output=True,
                text=True,
                timeout=10,
                startupinfo=startupinfo
            )

            for _ in range(5):
                time.sleep(1)
                status_check = subprocess.run(
                    ["sc", "query", service],
                    capture_output=True,
                    text=True,
                    startupinfo=startupinfo
                )
                if "RUNNING" in status_check.stdout:
                    enabled_services.append(service)
                    break
            else:
                failed_services.append(f"{service} (didn't confirm running)")

        except Exception as e:
            failed_services.append(f"{service} (error: {e})")

    return enabled_services, failed_services

def check_services_status():
    services = {
        "bthserv": "Bluetooth Support Service",
        "TermService": "Remote Desktop Services",
        "RemoteAccess": "Routing and Remote Access",
        "WFDSConMgrSvc": "Wi-Fi Direct Services",
        "xbgm": "Xbox Game Monitoring",
        "XblAuthManager": "Xbox Live Auth Manager",
        "XboxNetApiSvc": "Xbox Live Networking Service",
        "XblGameSave": "Xbox Live Game Save"
    }

    statuses = {}

    for service, service_name in services.items():
        config_result = subprocess.run(
            ["sc", "qc", service],
            capture_output=True,
            text=True,
            startupinfo=startupinfo
        )
        if "DISABLED" in config_result.stdout:
            statuses[service_name] = "Disabled"
            continue

        result = subprocess.run(
            ["sc", "query", service],
            capture_output=True,
            text=True,
            startupinfo=startupinfo
        )
        
        if "RUNNING" in result.stdout:
            statuses[service_name] = "Running"
        elif "STOPPED" in result.stdout:
            statuses[service_name] = "Stopped"
        else:
            statuses[service_name] = "Unknown"
    
    return statuses

def disable_netbios_over_tcpip():
    """Disables NetBIOS over TCP/IP for all network adapters."""
    disabled = []
    failed = []

    try:
        path = r"SYSTEM\CurrentControlSet\Services\NetBT\Parameters\Interfaces"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as interfaces:
            for i in range(100):  # up to 100 adapters
                try:
                    adapter = winreg.EnumKey(interfaces, i)
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path + "\\" + adapter, 0, winreg.KEY_SET_VALUE) as key:
                        winreg.SetValueEx(key, "NetbiosOptions", 0, winreg.REG_DWORD, 2)
                        disabled.append(adapter)
                except OSError:
                    break
    except Exception as e:
        failed.append(f"Error: {e}")

    return disabled, failed

def disable_critical_network_ports():
    disabled_services, failed_services = disable_services()
    netbios_disabled, netbios_failed = disable_netbios_over_tcpip()

    return {
        "services_disabled": disabled_services,
        "services_failed": failed_services,
        "netbios_disabled": netbios_disabled,
        "netbios_failed": netbios_failed
    }

def check_netbios_status():
    """Checks NetBIOS over TCP/IP status and maps to adapter friendly names."""
    import winreg

    disabled = []
    enabled = []
    failed = []

    try:
        interfaces_path = r"SYSTEM\CurrentControlSet\Services\NetBT\Parameters\Interfaces"
        connection_path = r"SYSTEM\CurrentControlSet\Control\Network\{4D36E972-E325-11CE-BFC1-08002BE10318}"

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, interfaces_path) as interfaces:
            for i in range(100):
                try:
                    adapter_reg_name = winreg.EnumKey(interfaces, i)

                    # Try getting NetBIOS setting
                    try:
                        with winreg.OpenKey(interfaces, adapter_reg_name) as key:
                            value, _ = winreg.QueryValueEx(key, "NetbiosOptions")
                    except FileNotFoundError:
                        value = 0  # Default (enabled)

                    # Friendly name mapping
                    adapter_guid = adapter_reg_name.split("\\")[-1].replace("Tcpip_", "")
                    try:
                        connection_key = f"{connection_path}\\{adapter_guid}\\Connection"
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, connection_key) as conn:
                            name, _ = winreg.QueryValueEx(conn, "Name")
                    except:
                        name = adapter_guid  # fallback

                    # Status classification
                    if value == 2:
                        disabled.append(name)
                    else:
                        enabled.append(name)

                except OSError:
                    break
    except Exception as e:
        failed.append(f"Error: {e}")

    return {
        "disabled_adapters": disabled,
        "enabled_adapters": enabled,
        "failed": failed
    }


 
