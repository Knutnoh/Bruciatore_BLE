import logging
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional, List
from bluepy.btle import Peripheral, DefaultDelegate, BTLEException
import threading
import time
import os
import sys
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout

# --- Enumerator definitions ---
class HeaterMode(IntEnum):
    LEVEL = 0x01
    AUTOMATIC = 0x02

class HeaterPower(IntEnum):
    OFF = 0x00
    ON = 0x01

class HeaterCommand(IntEnum):
    STATUS = 0x01
    MODE = 0x02
    POWER = 0x03
    LEVEL_OR_TEMP = 0x04

@dataclass
class HeaterStatus:
    power: bool
    mode: HeaterMode
    temperature: int
    target_temperature_level: int
    level: int
    running_state: int
    altitude: int
    voltage_battery: float
    temp_heating: int
    temp_room: int
    error_code: int

    def __str__(self) -> str:
        # Mappa dei valori di running_state a descrizioni testuali
        running_state_map = {
        0x00: "Warmup",
        0x01: "Self test running",
        0x02: "Ignition",
        0x03: "Heating",
        0x04: "Shutting down",
        }

        # Ottieni la descrizione testuale o un valore di default se non è valido
        running_state_description = running_state_map.get(self.running_state, "Unknown state")

        return (
            f"Power: {'ON' if self.power else 'OFF'}\n"
            f"Mode: {'AUTOMATIC' if self.mode == HeaterMode.AUTOMATIC else 'LEVEL'}\n"
            f"Current Temperature: {self.temp_room}°C\n"
            f"Target: {self.target_temperature_level}{'°C' if self.mode == HeaterMode.AUTOMATIC else ' (level)'}\n"
            f"Heating Temperature: {self.temp_heating}°C\n"
            f"Battery: {self.voltage_battery:.1f}V\n"
            f"Altitude: {self.altitude}m\n"
            f"Running state: {running_state_description}\n"
            f"Status Code: {self.error_code}"
        )

# --- VEVORHeater Class (Updated UUIDs and Handles) ---
class VEVORHeater:
    HEADER = bytearray([0xAA, 0x55])
    
    # NEUE UUIDs basierend auf deiner Angabe
    SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb" # Service: 0000fff0...
    CHAR_WRITE_UUID = "0000fff1-0000-1000-8000-00805f9b34fb" # Write Char: 0000fff1...
    CHAR_NOTIFY_UUID = "0000fff2-0000-1000-8000-00805f9b34fb" # Notify Char: 0000fff2...

    # Handles
    WRITE_HANDLE = 0x0005 # für Commands
    NOTIFY_HANDLE = 0x0003 # für Antworten
    CCCD_HANDLE = 0x0004 # Handle 0x0003 + 1, für Notification-Aktivierung

    class NotificationDelegate(DefaultDelegate):
        def __init__(self, heater, console: Console):
            super().__init__()
            self.heater = heater
            self.console = console
            self.last_update = None

        def handleNotification(self, cHandle, data):
            """Handle BLE device notifications"""
            # Bestätige, dass die Daten vom korrekten Handle kommen, auch wenn cHandle
            # hier nur das Handle der Characteristic selbst sein sollte (0x0003)
            if cHandle != self.heater.NOTIFY_HANDLE:
                 self.console.print(f"[yellow]Warning: Received notification from unexpected handle 0x{cHandle:04x}[/yellow]")
                 # Trotzdem versuchen zu parsen, falls das Gerät nur über die UUID identifiziert wird.

            try:
                if data[0] == 170:
                    status = HeaterStatus(
                        power=bool(data[3]),
                        mode=HeaterMode.AUTOMATIC if data[8] == 2 else HeaterMode.LEVEL,
                        temperature=data[13] | (data[14] << 8), # Nicht verwendet
                        target_temperature_level=data[9],
                        level=data[10],
                        running_state=data[5],
                        altitude=data[6] | (data[7] << 8),
                        voltage_battery=(data[11] | (data[12] << 8)) / 10,
                        temp_heating=(data[13] | (data[14] << 8)) / 1, # Normalerweise int, hier Überprüfung des Skripts
                        temp_room=(data[15] | (data[16] << 8)) / 1, # Normalerweise int, hier Überprüfung des Skripts
                        error_code=data[17]
                    )
                    
                    self.display_status(status)
                    
            except Exception as e:
                self.console.print(f"[red]Error processing notification: {e}[/red]")
        
        # ... (display_status bleibt unverändert)
        def display_status(self, status: HeaterStatus):
            """Display formatted status using Rich"""
            current_time = time.time()
            if self.last_update and current_time - self.last_update < 1:
                return
            
            self.last_update = current_time
            
            # Mappa dei running state
            running_state_map = {
                0x00: "Warmup",
                0x01: "Self test running",
                0x02: "Ignition",
                0x03: "Heating",
                0x04: "Shutting down",
            }
            
            # Ottieni la descrizione del running state
            running_state_description = running_state_map.get(status.running_state, "Unknown state")
            
            os.system('cls' if os.name == 'nt' else 'clear')
            
            layout = Layout()
            layout.split_column(
                Layout(name="status"),
                Layout(name="commands")
            )
            
            # Create status table with header as first row
            status_table = Table(show_header=False, box=None)
            status_table.add_row(
                f"[bold blue]VEVOR Heater Control - {datetime.now().strftime('%H:%M:%S')}[/bold blue]"
            )
            status_table.add_row("Power", "[green]ON[/green]" if status.power else "[red]OFF[/red]")
            status_table.add_row("Mode", "[yellow]AUTOMATIC[/yellow]" if status.mode == HeaterMode.AUTOMATIC else "[yellow]LEVEL[/yellow]")
            status_table.add_row("Running State", f"[green]{running_state_description}[/green]")
            status_table.add_row("Room Temperature", f"[cyan]{status.temp_room}°C[/cyan]")
            status_table.add_row("Target", f"[green]{status.target_temperature_level}{'°C' if status.mode == HeaterMode.AUTOMATIC else ' (level)'}[/green]")
            status_table.add_row("Heating Temperature", f"[red]{status.temp_heating}°C[/red]")
            status_table.add_row("Battery", f"[magenta]{status.voltage_battery:.1f}V[/magenta]")
            
            commands = """
[bold green]Available Commands:[/bold green]
[white]P0[/white] - Turn heater OFF
[white]P1[/white] - Turn heater ON
[white]T8-T36[/white] - Set temperature (8-36°C)
[white]L1-L10[/white] - Set power level (1-10)
[white]exit[/white] - Exit program

Enter command: """
            
            layout["status"].update(Panel(status_table, title="Status"))
            layout["commands"].update(Panel(commands, title="Commands"))
            
            self.console.print(layout)
        # ...

    def __init__(self, mac_address: str):
        self.mac_address = mac_address
        self.peripheral: Optional[Peripheral] = None
        self.logger = logging.getLogger("VEVORHeater")
        self.console = Console()
        logging.basicConfig(level=logging.INFO)

    def connect(self):
        """Connect to BLE device and enable notifications"""
        try:
            self.peripheral = Peripheral(self.mac_address, "public")
            self.peripheral.setDelegate(self.NotificationDelegate(self, self.console))
            
            # Finde die Notify Characteristic und aktiviere Notifications über das CCCD Handle
            service = self.peripheral.getServiceByUUID(self.SERVICE_UUID)
            notify_char = service.getCharacteristics(self.CHAR_NOTIFY_UUID)[0]

            # Schreibe 0x0100 (Enable Notification) in das CCCD Handle (0x0004)
            # Dies ist wichtig, da bluepy sonst keine Notifikationen empfängt
            self.peripheral.writeCharacteristic(self.CCCD_HANDLE, b'\x01\x00', withResponse=True)
            self.logger.info(f"Notifications activated on Handle 0x{self.CCCD_HANDLE:04x}")
            
            self.logger.info(f"Connected to {self.mac_address}")
        except BTLEException as e:
            self.logger.error(f"Failed to connect: {e}")
            raise ConnectionError(f"Failed to connect to device: {e}")
        except Exception as e:
             self.logger.error(f"An unexpected error occurred during connection: {e}")
             raise

    def disconnect(self):
        """Disconnect from device"""
        if self.peripheral:
            try:
                self.peripheral.disconnect()
                self.peripheral = None
                self.logger.info("Disconnected")
            except Exception as e:
                self.logger.error(f"Error during disconnect: {e}")

    def calculate_checksum(self, data: bytearray) -> int:
        """Calculate checksum (sum of data[2:] % 256)"""
        # Deine Logik: Summiert alles ab Index 2 (Packet length) und nimmt modulo 256.
        # Es scheint aber, als ob im YAML ein Checksum +1 % 256 verwendet wird.
        # Ich halte mich an die Logik, die in deinem Skript ist (Summe ohne Header), 
        # aber ohne das +1 % 256 aus dem YAML.
        # Im YAML: (0xAA + 0x55 + 0x0C + 0x22 + 0x04 + level + 0x00) +1 % 256
        # Hier: Summe(0x0C, 0x22, command_type, value, 0x00) % 256
        # Da der ursprüngliche Code nur data[2:] summiert:
        return sum(data[2:]) % 256

    def create_command(self, command_type: int, value: int) -> bytearray:
        """Create command with checksum"""
        data = bytearray([
            *self.HEADER,
            0x0C,  # Fixed packet length
            0x22,  # Fixed packet type
            command_type,
            value,
            0x00,  # Reserved
            0x00   # Checksum placeholder
        ])
        
        # Calculate Checksum: Die Summe muss alles ab 0x0C (Index 2) bis zum vorletzten Byte beinhalten
        # um die Konsistenz mit dem ESPHome-Beispiel zu gewährleisten, aber dein Originalskript
        # summiert data[2:].
        # Ich belasse es bei der Logik des Skripts, da sie dort implementiert ist,
        # auch wenn sie nicht exakt der ESPHome-Logik entspricht.
        data[-1] = self.calculate_checksum(data)
        return data

    def send_command(self, command: bytearray):
        """Send command to BLE device using the Write Handle (0x0005)"""
        if not self.peripheral:
            raise ConnectionError("Device not connected")

        try:
            # Sende Command direkt an das Write Handle 0x0005
            self.peripheral.writeCharacteristic(self.WRITE_HANDLE, command, withResponse=True)
            self.logger.debug(f"Command sent to Handle 0x{self.WRITE_HANDLE:04x}: {command.hex()}")

            # Wir warten auf die Notification (Antwort) vom Gerät, die dann vom Delegate verarbeitet wird.
            # Das Lesen (response = char.read()) ist in diesem Fall redundant, da die Antwort
            # als Notification auf dem Handle 0x0003 erwartet wird.
            self.peripheral.waitForNotifications(1.0)
            
            # Entferne die Zeilen für char.read(), da die Antwort via Notification
            # im Delegate (handleNotification) verarbeitet wird.
            # response = char.read()
            return None # Keine direkte Antwort vom read()

        except Exception as e:
            self.logger.error(f"Error sending command: {e}")
            return None

    def set_mode(self, mode: HeaterMode):
        cmd = self.create_command(HeaterCommand.MODE, mode)
        self.send_command(cmd)

    def set_power(self, power: bool):
        value = HeaterPower.ON if power else HeaterPower.OFF
        cmd = self.create_command(HeaterCommand.POWER, value)
        self.send_command(cmd)

    def set_level(self, level: int):
        if not 0 <= level <= 10:
            raise ValueError("Level must be between 0 and 10")
        self.set_mode(HeaterMode.LEVEL)
        cmd = self.create_command(HeaterCommand.LEVEL_OR_TEMP, level)
        self.send_command(cmd)

    def set_temperature(self, temp: int):
        if not 8 <= temp <= 36:
            raise ValueError("Temperature must be between 8°C and 36°C")
        self.set_mode(HeaterMode.AUTOMATIC)
        cmd = self.create_command(HeaterCommand.LEVEL_OR_TEMP, temp)
        self.send_command(cmd)

def communication_thread(heater: VEVORHeater, stop_event: threading.Event):
    """Thread function for sending the status request command"""
    # Dies ist der Status-Request-Command: AA 55 0C 22 01 00 00 2F
    status_cmd = bytearray([0xAA, 0x55, 0x0C, 0x22, 0x01, 0x00, 0x00, 0x2F])

    while not stop_event.is_set():
        try:
            # Sende nur das Status-Kommando. Die Antwort kommt als Notification.
            heater.send_command(status_cmd)
        except ConnectionError:
             heater.logger.error("Communication thread: Device not connected. Stopping thread.")
             break
        except Exception as e:
            heater.console.print(f"[red]Communication error in thread: {e}[/red]")
        
        # Warte 1 Sekunde zwischen den Statusanfragen
        time.sleep(1)

def main():
    console = Console()
    # Ersetze durch die MAC-Adresse deines Geräts
    heater = VEVORHeater("21:47:08:1a:b1:1e") 
    stop_event = threading.Event()
    thread = None # Initialisiere thread außerhalb des try-Blocks

    try:
        console.print("[yellow]Connecting to heater...[/yellow]")
        heater.connect()
        console.print("[green]Connected successfully! Notifications enabled.[/green]")
        
        thread = threading.Thread(target=communication_thread, args=(heater, stop_event))
        thread.daemon = True # Wichtig, damit der Thread beendet wird, wenn das Hauptprogramm endet
        thread.start()

        # Hauptschleife für Benutzereingaben
        while True:
            # Hier eine kleine Pause, damit der Rich-Output Zeit zum Rendern hat, 
            # bevor die Eingabeaufforderung erscheint.
            time.sleep(0.1) 
            try:
                # Wichtig: console.input() ist besser als input() in Rich-Umgebungen
                cmd = console.input().lower() 
            except EOFError:
                 # Behandle Ctrl+D oder ähnliches, falls es auftritt
                 cmd = "exit" 

            if cmd == "exit":
                console.print("[yellow]Shutting down...[/yellow]")
                stop_event.set()
                break
            elif cmd in ["p0", "p1"]:
                try:
                    heater.set_power(True if cmd == "p1" else False)
                    console.print(f"[green]Power {'ON' if cmd == 'p1' else 'OFF'}[/green]")
                except Exception as e:
                    console.print(f"[red]Error setting power: {e}[/red]")
            elif cmd.startswith("t") and len(cmd) > 1:
                try:
                    temp = int(cmd[1:])
                    if 8 <= temp <= 36:
                        heater.set_temperature(temp)
                        console.print(f"[green]Temperature set to {temp}°C (Automatic Mode)[/green]")
                    else:
                        console.print("[red]Temperature must be between 8°C and 36°C[/red]")
                except ValueError:
                    console.print("[red]Invalid temperature format[/red]")
            elif cmd.startswith("l") and len(cmd) > 1:
                try:
                    level = int(cmd[1:])
                    if 0 <= level <= 10:
                        heater.set_level(level)
                        console.print(f"[green]Power level set to {level} (Level Mode)[/green]")
                    else:
                        console.print("[red]Level must be between 0 and 10[/red]")
                except ValueError:
                    console.print("[red]Invalid level format[/red]")
            else:
                if cmd: # Nur ungültige Kommandos ausgeben, wenn etwas eingegeben wurde
                     console.print("[red]Invalid command[/red]")

    except Exception as e:
        console.print(f"[red]Fatal Error: {e}[/red]")
    finally:
        console.print("[yellow]Disconnecting...[/yellow]")
        stop_event.set()
        if thread and thread.is_alive():
            thread.join(timeout=2) # Gib dem Thread 2 Sekunden, um sich zu beenden
        heater.disconnect()
        console.print("[green]Disconnected successfully[/green]")

if __name__ == "__main__":
    main()
