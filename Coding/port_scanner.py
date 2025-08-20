import subprocess
import re

# ✅ Define well-known ports to always show
COMMON_PORTS = {
    "21": "FTP", "22": "SSH", "23": "Telnet", "25": "SMTP", "53": "DNS",
    "80": "HTTP", "135": "RPC", "139": "NetBIOS", "443": "HTTPS",
    "445": "SMB", "3389": "RDP", "5353": "mDNS", "1900": "UPnP"
}

# ✅ Known UDP Services (Well-Known Ports)
KNOWN_UDP_PORTS = {
    "123": "NTP", "500": "ISAKMP", "3702": "WS-Discovery", "53": "DNS",
    "67": "DHCP Server", "68": "DHCP Client", "161": "SNMP", "162": "SNMP Trap",
    "137": "NetBIOS Name", "138": "NetBIOS Datagram", "1900": "UPnP", "5353": "mDNS"
}

# ✅ Critical Ports That Should Be Closed
CRITICAL_PORTS_TO_CLOSE = {
    "22": "SSH", "53": "DNS", "137": "NetBIOS Name", "138": "NetBIOS Datagram",
    "139": "NetBIOS Session", "445": "SMB", "161": "SNMP", "3389": "RDP"
}

def format_port(port, protocol, service_dict):
    return f"Port {port} ({protocol}) - {service_dict.get(port, 'Unknown')}"

def check_critical(port):
    return port in CRITICAL_PORTS_TO_CLOSE

def get_open_ports():
    try:
        tcp_result = subprocess.run(
            ["powershell", "Get-NetTCPConnection | Select-Object LocalPort, State"],
            capture_output=True, text=True, shell=True
        )

        tcp_ports = set()
        critical_open_ports = []

        for line in tcp_result.stdout.strip().split("\n")[3:]:
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1].lower() == "listen":
                port = parts[0]
                if port in COMMON_PORTS or len(tcp_ports) < 5:
                    tcp_ports.add(format_port(port, "TCP", COMMON_PORTS))
                if check_critical(port):
                    critical_open_ports.append(f"{port} ({CRITICAL_PORTS_TO_CLOSE[port]}) is OPEN")

        udp_result = subprocess.run(
            ["powershell", "Get-NetUDPEndpoint | Select-Object LocalAddress, LocalPort, OwningProcess"],
            capture_output=True, text=True, shell=True
        )

        udp_ports = {}
        for line in udp_result.stdout.strip().split("\n")[3:]:
            parts = re.split(r"\s+", line.strip())
            if len(parts) >= 3:
                _, port, pid = parts[:3]
                if port in KNOWN_UDP_PORTS or len(udp_ports) < 5:
                    udp_ports[port] = udp_ports.get(port, []) + [pid]
                if check_critical(port):
                    critical_open_ports.append(f"{port} ({CRITICAL_PORTS_TO_CLOSE[port]}) is OPEN")

        udp_list = [
            f"Port {port} (UDP) - {KNOWN_UDP_PORTS.get(port, 'Unknown')} - PIDs: {', '.join(set(pids))}"
            for port, pids in udp_ports.items()
        ]

        if critical_open_ports:
            critical_open_ports.insert(0, "Critical Ports Found OPEN (Should be Closed):")

        return {
            "tcp": list(tcp_ports) if tcp_ports else ["No open TCP ports detected."],
            "udp": udp_list if udp_list else ["No active UDP services detected."],
            "critical": critical_open_ports if critical_open_ports else ["No critical ports open."]
        }

    except Exception as e:
        return {
            "tcp": [f"Error retrieving TCP ports: {e}"],
            "udp": [f"Error retrieving UDP services: {e}"],
            "critical": ["Could not determine critical port status."]
        }

if __name__ == "__main__":
    from pprint import pprint
    pprint(get_open_ports())
