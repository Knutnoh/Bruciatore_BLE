ESPHome – Vevor Diesel Standheizung (BLE)

Dieses Projekt integriert eine Vevor Diesel-Standheizung mit Bluetooth (BLE) in ESPHome
.
Damit lässt sich die Heizung über Home Assistant oder die ESPHome-Weboberfläche komfortabel steuern und überwachen.

Unterschiede zu anderen Projekten

Im Gegensatz zum Projekt Bruciatore_BLE
, das mit einer einzigen Service-UUID arbeitet, nutzt diese Implementierung drei UUIDs:

fff0 – Service UUID

fff1 – Characteristic (Empfang, Notify)

fff2 – Characteristic (Senden, Write)

👉 Diese Werte sind im Code definiert und können bei Bedarf angepasst werden. Dadurch ist die Lösung flexibler und auch für verschiedene Modellvarianten der Vevor-Heizung nutzbar.

Features

🔥 Heizung Ein/Aus schalten

🌡️ Zieltemperatur einstellen (Automatik-Modus)

💨 Gebläsestufen regeln (Manuell-Modus)

🔄 Modus-Wechsel: Automatik ↔ Manuell

🌬️ Lüftermodus separat aktivieren

🏔️ Höhenmodus (High Altitude Mode)

📊 Sensoren für:

Betriebsmodus (Manuell/Automatik)

Heizungsstatus (inkl. Phasen: Aufwärmen, Zündung, Heizen etc.)

Raumtemperatur

Schalentemperatur

Batteriespannung

Aktuellen Zielwert

Voraussetzungen

ESP32-Board (z. B. esp32dev)

Installiertes ESPHome

Zugang zu deinem Home Assistant (optional)

Vevor Diesel-Standheizung mit Bluetooth (BLE)

Installation

Repository klonen oder die YAML-Datei in dein ESPHome-Projekt übernehmen.

Passe die Substitutions in der YAML an:

substitutions:
  name: bt-vevor-ble
  friendly_name: Diesel_Standheizung
  heater_mac: "XX:XX:XX:XX:XX:XX"   # MAC-Adresse deiner Heizung eintragen
  service_uuid: "0000fff0-0000-1000-8000-00805f9b34fb"
  char_fff1_uuid: "0000fff1-0000-1000-8000-00805f9b34fb"
  char_fff2_uuid: "0000fff2-0000-1000-8000-00805f9b34fb"


👉 Hier können die UUIDs an dein Heizungsmodell angepasst werden.

WLAN-Zugangsdaten in secrets.yaml eintragen:

wifi_ssid: "DEIN-WLAN"
wifi_password: "DEIN-PASSWORT"


Firmware mit ESPHome flashen und Gerät starten.

In Home Assistant taucht die Heizung automatisch als Gerät mit allen Entitäten auf.

Steuerung

Schalter

Heizung Ein/Aus

Lüfter

Höhenmodus

Buttons

Modus Wechseln

Temperatur/Gebläse +

Temperatur/Gebläse -

Slider

Zieltemperatur (Automatik-Modus: 8–36 °C)

Gebläsestufe (Manuell-Modus: 1–6)

Sensoren

Raumtemperatur, Batteriespannung, Schalentemperatur

Betriebsmodus (Manuell/Automatik)

Heizungsstatus (inkl. Detailphasen)

Hinweise

Die BLE-Kommunikation basiert auf den Befehlen der originalen Vevor-App.

UUIDs (fff0, fff1, fff2) sind im Code flexibel anpassbar.

Logging (logger.level: DEBUG) ist standardmäßig aktiv, um die BLE-Kommunikation beim Testen sichtbar zu machen.
