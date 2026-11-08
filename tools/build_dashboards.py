#!/usr/bin/env python3
# Imagined and engineered by:
# Aries Thorne & Todd Steinhauer
#
# Moral Support: Athena the K9
"""Builds one LODESTAR PULSAR dashboard per board from dashboard/pulsar.template.html.
Each file is a single page with that board's name, radio options and release name filled in.
Usage: python3 tools/build_dashboards.py [--check]"""
import json, os, sys, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "dashboards")

# id, display name, firmware build name, release name in the tag, chip family, flash method, bluetooth hardware, wifi hardware
BOARDS = [
    ("heltec-v4-r2",   "Heltec WiFi LoRa 32 V4 R2",             "heltec_v4_repeater",          "Heltec-V4",         "esp32", "bin", True,  True),
    ("heltec-v4-r8",   "Heltec WiFi LoRa 32 V4-R8",             "heltec_v4_r8_repeater",       "Heltec-V4-R8",      "esp32", "bin", True,  True),
    ("heltec-v3",      "Heltec WiFi LoRa 32 V3",                "Heltec_v3_repeater",          "Heltec-V3",         "esp32", "bin", True,  True),
    ("xiao-esp32s3",   "Seeed XIAO ESP32S3 + Wio-SX1262",       "Xiao_S3_WIO_repeater",        "XIAO-S3",           "esp32", "bin", True,  True),
    ("station-g2",     "B&Q Station G2",                        "Station_G2_repeater",         "Station-G2",        "esp32", "bin", True,  True),
    ("tbeam-sx1262",   "LilyGo T-Beam (SX1262)",                "Tbeam_SX1262_repeater",       "T-Beam-SX1262",     "esp32", "bin", True,  True),
    ("xiao-nrf52840",  "Seeed XIAO nRF52840 + Wio-SX1262",      "Xiao_nrf52_repeater",         "XIAO-nRF52",        "nrf52", "uf2", True,  False),
    ("sensecap-p1pro", "Seeed SenseCAP Solar Node P1-Pro",      "SenseCap_Solar_repeater",     "SenseCAP-P1Pro",    "nrf52", "uf2", True,  False),
    ("rak4631",        "RAK WisBlock RAK4631",                  "RAK_4631_repeater",           "RAK4631",           "nrf52", "uf2", True,  False),
    ("heltec-t114",    "Heltec Mesh Node T114",                 "Heltec_t114_repeater",        "Heltec-T114",       "nrf52", "uf2", True,  False),
    ("lilygo-t-echo",  "LilyGo T-Echo",                         "LilyGo_T-Echo_repeater",      "LilyGo-T-Echo",     "nrf52", "uf2", True,  False),
    ("heltec-mesh-solar", "Heltec Mesh Solar",                  "Heltec_mesh_solar_repeater",  "Heltec-Mesh-Solar", "nrf52", "uf2", True,  False),
]

def build():
    tpl = open(os.path.join(ROOT, "dashboard", "pulsar.template.html"), encoding="utf-8").read()
    assert tpl.count("/*BOARD_PROFILE*/") == 1
    os.makedirs(OUT, exist_ok=True)
    made = {}
    for bid, name, env, rel, chip, flash, ble, wifi in BOARDS:
        prof = {"id": bid, "dashId": "pulsar-" + bid, "name": name, "env": env, "relKey": rel, "chip": chip, "flash": flash, "ble": ble, "wifi": wifi}
        html = tpl.replace("/*BOARD_PROFILE*/", "const BOARD = " + json.dumps(prof) + ";")
        html = html.replace("<title>LODESTAR PULSAR dashboard</title>", "<title>LODESTAR PULSAR - " + name + "</title>")
        path = os.path.join(OUT, "pulsar-" + bid + ".html")
        made[path] = html
    return made

def main():
    made = build()
    if "--check" in sys.argv:
        bad = [p for p, h in made.items() if not os.path.isfile(p) or open(p, encoding="utf-8").read() != h]
        if bad: sys.exit("out of date: " + ", ".join(os.path.basename(b) for b in bad))
        print("dashboards up to date"); return
    for p, h in made.items():
        with open(p, "w", encoding="utf-8") as f: f.write(h)
        print(os.path.basename(p), len(h.encode()))

if __name__ == "__main__":
    main()
