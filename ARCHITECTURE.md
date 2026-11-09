# LODESTAR PULSAR: Architecture

Imagined and engineered by: Aries Thorne & Todd Steinhauer
for Wolf Reactive Systems (WRS)

Moral Support: Athena the K9

Special thanks to the NTXMESH community, the MeshCore community, and Pat Steinhauer-Scates for their guidance and support.

This document describes how LODESTAR PULSAR is put together: what it changes in MeshCore, how the scoring works, how a firmware image gets built and released, and how the dashboards fit in. It covers the current beta, release line `LODESTAR-PULSAR-<board>-v1.0.0-beta-UD21214`, for every board in the [supported boards table](README.md#supported-boards).

**Test status, stated plainly.** The scoring logic has automated unit tests that run on every push. The patch is checked against current MeshCore on every push. Real-radio field results exist for three boards only: Heltec WiFi LoRa 32 V4 R2 (the main target), Seeed XIAO ESP32S3 + Wio-SX1262, and Seeed SenseCAP Solar Node P1-Pro. **Every other board in the table builds in CI but has not been run on a real board by the makers.** The dashboards have been tested against a simulated repeater only. Sections below say when something is a design intent rather than a verified result.

---

## 1. The shape of the project

PULSAR is not a fork of MeshCore. It is **stock MeshCore plus a small patch**, applied at build time to a fresh clone.

```
 this repo                                 meshcore-dev/MeshCore (fresh clone, latest)
 ---------                                 -------------------------------------------
 lodestar/Lodestar.h  ---copied into--->   src/helpers/Lodestar.h
 tools/apply_lodestar.py ---edits------>   examples/simple_repeater/MyMesh.h
                                           examples/simple_repeater/MyMesh.cpp
 tools/persist_ble_pin.py --edits------>   examples/companion_radio/main.cpp  (if present)
 tools/make_splash.py ---edits--------->   boot-screen sources (screen boards only)
                                                   |
                                                   v
                                           PlatformIO build of the board's
                                           "<board>_repeater" environment
                                                   |
                                                   v
                                           firmware.uf2 / firmware-merged.bin
```

Why a patch and not a fork: MeshCore moves quickly. A patch that must match upstream exactly *once* per edit means a change upstream is caught immediately and loudly, instead of silently producing a half-patched or stale build.

| Path | Role |
|---|---|
| `lodestar/Lodestar.h` | The whole feature. Header-only, no Arduino or MeshCore dependencies, so it can be tested on a PC. |
| `lodestar/test/test_lodestar.cpp` | Unit tests for the scoring, ACK tracking, settings, GPS speed/course and commands. |
| `tools/apply_lodestar.py` | Copies `Lodestar.h` into MeshCore and applies the glue edits to `simple_repeater`. |
| `tools/persist_ble_pin.py` | Makes the companion radio's Bluetooth PIN stable across restarts (see 6). |
| `tools/make_splash.py`, `tools/lodestar_art.py` | Custom boot-screen text and logo for boards with a screen. |
| `tools/build_dashboards.py` | Generates the per-board dashboards from the template. |
| `dashboard/pulsar.template.html` | The single dashboard template. |
| `dashboards/pulsar-<board>.html` | Generated dashboards, one per supported board (12). |
| `.github/workflows/build.yml` | Tests, patch check, firmware build, optional release. |
| `.github/workflows/build-room.yml` | Builds the Hearth room-server firmware (a separate product). |

---

## 2. The patch (`tools/apply_lodestar.py`)

The script refuses to run on a tree that already contains `lodestar`, and it aborts with a message naming the anchor it could not find if any edit does not match **exactly once**. It never leaves a partly patched tree on purpose, but if it aborts midway the checkout should be discarded and re-cloned.

Edits to `examples/simple_repeater/MyMesh.cpp` and `MyMesh.h`:

| Hook point in MeshCore | What PULSAR adds |
|---|---|
| `onRecvPacket` (start) | For every received **flood** packet: take the last hop in its path as "the repeater we just heard directly", update that uplink's link stats, record reach for adverts, check whether this copy is an echo of something we sent (implicit ACK), and, if a strong uplink has already forwarded the same packet, remove our own still-queued retransmit of it. |
| `onAdvertRecv` (after `putNeighbour`) | Feed zero-hop repeater adverts into the uplink table. |
| `logTx` (start) | Remember each flood packet we transmit (hash, path, which uplinks were in range) so its echo can be watched for. |
| `getRetransmitDelay` | Multiply the stock random **flood** retransmit delay by `delayFactor()`. Direct-route delay is untouched. |
| `loop` (after `Mesh::loop`) | Housekeeping tick; write settings to flash if they changed; hand the GPS fix to PULSAR if the build has GPS. |
| `begin` (after `loadPrefs`) | Restore saved settings from `/lodestar.cfg`. |
| `handleCommand` | Route `lodestar ...` to `Lodestar::runCommand`; everything else falls through to MeshCore's own CLI untouched. |

`MyMesh.h` gets one include and one member (`lodestar::Lodestar lodestar`).

Credit text is written at the top of the patched `MyMesh.cpp` as a comment and as a string kept in the firmware image.

**What the patch does not touch:** MeshCore's packet format, routing rules, encryption, authentication, the admin password handling, adverts' content, and the radio drivers. PULSAR changes *when* a flood packet is retransmitted, and may drop a queued duplicate. It does not change *what* is transmitted.

### Staying compatible with upstream

CI job **Patch still applies to current MeshCore** clones MeshCore `main` and runs both patch scripts on every push and pull request (about a minute, no firmware build). The firmware build job records the MeshCore commit it used in `meshcore_commit.txt` and in the release notes.

PULSAR builds against MeshCore's tip at build time, not a pinned commit. That keeps it current, but it also means two builds made on different days can differ in their MeshCore base. The commit hash in each release is the source of truth.

---

## 3. The scoring engine (`lodestar/Lodestar.h`)

### 3.1 State

- **Uplink table**, `LODESTAR_MAX_UPLINKS` entries (24 by default, hard maximum 32 because bit masks are 32-bit). Each entry keeps up to 3 leading bytes of the repeater's key, first/last heard time, smoothed SNR and RSSI, a 16-slot sliding "was it heard" window (20 s per slot, about 5 minutes), an implicit-ACK success average, hit/miss counts, and a smoothed hop figure.
- **Pending table**, 8 entries: flood packets we sent and are still waiting to hear echoed, with which uplinks were in range at the time.
- **Position**: latest GPS fix, derived speed and course. Kept separate from the uplink table, so `lodestar reset` does not erase it.
- All memory is statically sized. Nothing is allocated at run time.

### 3.2 Score

Each uplink gets a score from 0 to 1:

```
score = clamp01( (w_rel * reliability + w_lq * linkQuality + w_hop * hopScore) / (w_rel + w_lq + w_hop) )
        * freshness
```

| Part | Default weight | Meaning |
|---|---|---|
| reliability | 0.5 | Implicit-ACK success (did it re-broadcast what we sent?) blended with how consistently we hear it. |
| linkQuality | 0.3 | Smoothed SNR judged against the LoRa demodulation floor for the current spreading factor, plus RSSI. |
| hopScore | 0.2 | How few hops beyond that repeater its traffic reaches. |
| freshness | n/a | Full credit up to 120 s since last heard, falling to zero at 600 s. An entry is dropped after 1800 s. |

The spreading factor is copied from MeshCore's live preferences on each received packet, so the SNR floor follows `set radio`.

### 3.3 Choosing the best uplink

`evaluate()` runs at most once a second. It computes all scores, builds a top-3 list of those at or above the floor (default 0.25), and picks a **best** uplink with hysteresis: a challenger must beat the current best by 0.08 on **two evaluations in a row** before it takes over. A moving node therefore does not flip its mind on every packet.

### 3.4 The two decisions PULSAR makes

1. **Retransmit delay factor** (`delayFactor`):
   - no usable uplink, or PULSAR switched off: **1.0** (exactly stock behaviour);
   - best uplink score 1.0: **0.4** (transmit sooner);
   - best uplink score at the floor: up to about **1.6** (yield to better-placed repeaters).
   It scales MeshCore's random delay; it never removes the delay, and it never blocks forwarding.
2. **Duplicate cancel** (`onFloodCopy`): if a packet we have queued for retransmit is heard being forwarded by an uplink with score at least 0.60 and link quality at least 0.50, our queued copy is removed and counted. This saves airtime. Defaults can be changed with `lodestar cancel`.

If the table is empty, or PULSAR is off, the node is a stock MeshCore repeater.

### 3.5 GPS (read-only)

When a build has GPS enabled and the module is switched on (`gps on`), the latest fix is passed to PULSAR. Speed is derived over about 3 seconds of fixes, course after at least 8 m of travel, and below 1.5 m/s the node counts as stopped to ignore jitter. **This does not currently influence forwarding.** It is reported only. `gpsStatus` (used in replies that can travel over the mesh) never contains coordinates; `gpsDetail` (with coordinates) is only ever printed to the local serial port.

### 3.6 Persistence

Settings are one text line in `/lodestar.cfg`:

```
LODESTAR1 <enabled> <w_rel> <w_lq> <w_hop> <floor> <cancel_dup> <cancel_min>
```

`loadSettings` validates every field (tag, 0/1 flags, weights non-negative with a sane sum, floor and cancel threshold in range) and **changes nothing if any part is invalid**. Writes only happen when a setting actually changed, using the right file API for the platform (nRF52/STM32, RP2040, ESP32). The uplink table is **not** saved; it is rebuilt from what the node hears after boot.

### 3.7 Command surface

`lodestar` (alone or `table`), `gps`, `weights <rel> <lq> <hop>`, `floor <0..1>`, `cancel on|off|<0..1>`, `on`, `off`, `defaults`, `reset`. Table rows are printed line by line to the serial port; the one-line summary is the reply, which is the only part that goes back over a remote login.

---

## 4. Boards and build environments

Each supported board maps to a MeshCore PlatformIO environment. The build workflow picks the output files by platform.

| Family | Environments | Output | How it is flashed |
|---|---|---|---|
| ESP32 / ESP32-S3 | `heltec_v4_repeater`, `heltec_v4_r8_repeater`, `Heltec_v3_repeater`, `Station_G2_repeater`, `Tbeam_SX1262_repeater`, `Xiao_S3_WIO_repeater` | `firmware-merged.bin` (first flash), `firmware.bin` (update) | flasher.meshcore.io, Custom Firmware |
| nRF52840 | `Xiao_nrf52_repeater`, `SenseCap_Solar_repeater`, `RAK_4631_repeater`, `Heltec_t114_repeater`, `LilyGo_T-Echo_repeater`, `Heltec_mesh_solar_repeater` | `firmware.uf2`, `firmware.zip` | double-tap reset, drag `.uf2` onto the USB drive |

Per-board differences (screen, GPS, flash method) are in the README table. Screen boards get the splash patch; screenless boards ignore the splash inputs.

---

## 5. Build and release pipeline (`build.yml`)

```
push / pull request                      "Run workflow" (manual)
-------------------                      -----------------------
 [Unit tests]                             [Unit tests]
 [Patch still applies]                    [Patch still applies]
                                                  |
                                                  v
                                          [Build firmware]   (about 6 minutes)
                                            clone MeshCore main
                                            apply_lodestar.py + persist_ble_pin.py
                                            make_splash.py (screen boards)
                                            pio run -e <env>
                                            collect outputs + meshcore_commit.txt
                                                  |
                                          publish = true ?
                                                  v
                                          [gh release create <tag>]
```

- **Unit tests:** `g++ -std=c++17 -Wall -Wextra` on `test_lodestar.cpp`, run natively. They test the logic only, not radio behaviour.
- **Permissions:** workflow default is `contents: read`. Only the build job asks for `contents: write`, and only so it can create a Release.
- **Release guard:** the job checks `gh release view` first and stops if the tag already exists, so a published release is never silently overwritten.
- **Release naming:** `LODESTAR-PULSAR-<board>-v<version>`. The dashboard's update check finds a board's newest release by that tag prefix.
- **Release notes** state the board, how to flash, the MeshCore commit, and whether the board has been tested.
- **Not provided:** release files are not signed, and no separate checksum file is published. See [SECURITY.md](SECURITY.md).

---

## 6. Companion Bluetooth PIN patch (`persist_ble_pin.py`)

Stock MeshCore picks a new random pairing PIN each time a companion radio with a screen starts, which breaks the phone's saved pairing after a restart. The patch derives the PIN from the chip's unique ID on ESP32 (`100000 + hash % 900000`, FNV-1a over the six MAC bytes) so it is stable, and nothing is written to flash at boot. `set pin` still overrides it. Other platforms keep the random PIN. It is a no-op on a tree without the companion example, and it prints a warning rather than failing if upstream changed the code it edits.

This affects **companion** builds (LODESTAR NOVA), not the repeater. It lives in this repo because both products share the build tooling. The consequence of a PIN derived from a chip ID is discussed in SECURITY.md.

---

## 7. Dashboards

One template, `dashboard/pulsar.template.html`, becomes 12 files, one per board, by substituting a board profile (`/*BOARD_PROFILE*/`): id, display name, build environment, release key, chip, flash method, and whether the board has Bluetooth and WiFi. Each output is a single self-contained HTML file with no external scripts, fonts or images, so it works from a local file with no network.

```
 browser tab (Chrome / Edge)                         repeater
 ---------------------------                         --------
  UI tiles  <-- state S <-- parsers <-- command queue <-- transport ---- USB serial (Web Serial, 115200)
                                                              |-------- Bluetooth (Nordic UART service)   [dashboard side only]
                                                              '-------- WiFi (ws://<host>/ws)            [dashboard side only]
```

- **Transports.** USB serial is the only link the current Pulsar firmware supports. Bluetooth and WiFi are implemented in the dashboard but the repeater firmware does not yet provide a Bluetooth or WiFi command link, so they will not connect. The buttons appear only for boards that have the hardware.
- **Command engine.** One command in flight at a time, from a queue; the repeater echoes the command, so the echo is stripped; replies are printed as `-> reply`, and multi-line replies (such as `neighbors`) are merged with unprefixed lines.
- **Polling.** Every 5 seconds: `stats-core`, `stats-radio`, `stats-packets` (JSON), `lodestar` (table), `neighbors`, `lodestar gps`.
- **Parsers** turn those replies into state; the UI renders from state only. Values that came from the repeater are HTML-escaped before display.
- **Radar.** Signal strength sets the distance from the centre. A repeater cannot know the direction of a signal, so the angle is spread from a hash of the node ID; it is not a map.
- **Settings.** Name, radio, TX power, position, advert intervals, clock and admin password are sent as the same serial commands you would type, after range checks in the page.
- **Updates.** Reads `dashboard_updates/latest.json` on GitHub for a newer dashboard and the GitHub Releases API for a newer firmware for that board, then links the files. **It does not flash anything.**
- **Demo mode.** `#demo` in the address, or the **Try sample data** button, runs against a simulated repeater with no hardware.

Regenerate every dashboard with `python tools/build_dashboards.py`.

---

## 8. Design decisions worth knowing

- **Scoring never gates forwarding.** The worst case is a changed delay or a dropped duplicate, never a repeater that stops repeating. Both effects have an off switch (`lodestar off` restores stock timing).
- **Header-only, dependency-free core.** That is what makes the PC unit tests possible and keeps the glue small.
- **Fixed memory.** No heap use in the scoring path, so it cannot fragment on a long-running node.
- **No second source of truth for the mesh.** PULSAR reads packets MeshCore already receives; it adds no packet types and no protocol.
- **Position is local.** Coordinates stay on the serial port by design.

## 9. Known limits

- Direction of travel is measured but not yet used to choose uplinks.
- No Bluetooth or WiFi command link in the repeater firmware yet.
- Scoring needs roughly 10 minutes of adverts and traffic to be meaningful after a cold start, because the table is not saved.
- The `lodestar` command, once reached, trusts MeshCore's own login for access control; PULSAR adds no authentication of its own.
- Builds track MeshCore `main`, so a MeshCore regression can reach a PULSAR build; pin a commit in your own fork if you need reproducibility.
- Untested on real hardware: every board except V4 R2, XIAO ESP32S3 + Wio, and SenseCAP Solar; and every dashboard transport other than the simulated one.
