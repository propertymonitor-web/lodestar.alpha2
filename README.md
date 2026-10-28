# LODESTAR PULSAR

### Mobile-repeater firmware for MeshCore, by Wolf Reactive Systems (WRS)

**LODESTAR PULSAR** is the repeater in the LODESTAR family (the companion is [LODESTAR NOVA](https://github.com/propertymonitor-web/lodestar_nova_alpha); the solar repeater, LODESTAR HELIOS, is in development on the SenseCAP Solar Node P1-Pro). **Status: beta testing.** **Boards:** Heltec WiFi LoRa 32 **V4 R2** (with screen) and Seeed Studio **XIAO ESP32S3 + Wio-SX1262 kit** (no screen). See [supported boards](#supported-boards).

A repeater that is moving needs to think differently from one bolted to a tower. The tower never changes its neighbours. A vehicle, a hiker, or a boat is constantly gaining and losing them. LODESTAR is MeshCore repeater firmware with a built-in sense of *which repeaters around it are actually worth relying on right now*, and it uses that to forward traffic more intelligently.

It is free, open, and built for the **Heltec WiFi LoRa 32 V4 R2** (ESP32-S3R2, OLED) and, as a screenless option, the **Seeed Studio XIAO ESP32S3 + Wio-SX1262 kit**.

**At a glance**

- **Who it is for:** anyone running a MeshCore repeater that *moves*: in a vehicle, on a boat, on foot. A fixed repeater whose neighbours never change has less to gain.
- **What it adds to the stock MeshCore repeater:** a live ranking of the repeaters it can hear, used to decide *when* to forward and when to drop a duplicate copy. Everything else is stock MeshCore.
- **What it will not do:** stop forwarding, pick a single "next hop", or read your messages. See the [honest limits](#why-it-makes-a-good-mobile-repeater).

**Words used here.** An *advert* is a short broadcast that announces a node to its neighbours. An *uplink* is a nearby repeater your node relies on to carry its traffic. A *hop* is one repeater-to-repeater step. *SF* is the LoRa spreading factor, one of the radio settings a mesh agrees on.

> **Hardware check before you flash.** Heltec sells the V4 in two versions: **V4 R2** (ESP32-S3R2, 2 MB PSRAM) and **V4-R8** (ESP32-S3R8, 8 MB PSRAM). **This firmware is for the R2 only.** The two boards use different pins for GPS, the LED and external power (Heltec lists the differences on its [V4 product page](https://heltec.org/project/wifi-lora-32-v4/)), so an R2 image on an R8 can leave the GPS unpowered or misbehave. Check the MCU option on your order or listing before flashing. If you have an R8, do not use this build yet.

> **Status: field-test release.** The firmware builds from the Actions tab, and the scoring logic is covered by automated tests that run on every push, but it is new. That is why this README has a testing section. Your drive logs are exactly what will make it better.

## Supported boards

| Board | Build name | Screen | GPS | Notes |
|---|---|---|---|---|
| Heltec WiFi LoRa 32 **V4 R2** | `heltec_v4_repeater` | 128x64 OLED with the LODESTAR splash | Optional (`gps on`) | The main target. Not for the V4-R8 |
| Seeed Studio **SenseCAP Solar Node P1-Pro** (for MeshCore) | `SenseCap_Solar_repeater` | None | Built in (L76K); off until `gps on` | New, **beta, not yet run on a real board by the author**. Solar-powered repeater hardware. Flash a `.uf2`: double-tap RST so a USB drive appears (Xiao-Boot or Solar Node), drag `firmware.uf2` onto it, and see [Seeed's guide](https://wiki.seeedstudio.com/get_started_with_meshcore_solar_node/) for its erase step. Do not power it off while it is transmitting or being configured |
| Seeed Studio **XIAO nRF52840 + Wio-SX1262 kit** | `Xiao_nrf52_repeater` | None | None | New, **beta, not yet run on a real board by the author**. Flash a `.uf2`: double-tap the reset button so a USB drive appears, then drag `firmware.uf2` onto it. Settings persist across updates the same way |
| Seeed Studio **XIAO ESP32S3 + Wio-SX1262 kit** | `Xiao_S3_WIO_repeater` | None | None (MeshCore does not enable GPS on this board) | New, **beta, not yet run on a real board by the author**. Everything is done from the serial console or the MeshCore app |

**On either XIAO:** LODESTAR's scoring, settings and `lodestar` commands work exactly as on the Heltec. Differences: there is no screen, so the splash options in the build form do nothing and no splash preview is attached; there is no GPS, so `lodestar gps` reports no fix (LODESTAR does not need one); and you read the table from the serial console (115200 baud) or by logging in to the repeater from the MeshCore app. To flash it, plug it in with a USB data cable, then hold **BOOT**, tap **RESET**, release **BOOT** if the flasher cannot see the board, and use the same [web flasher](#flashing-with-the-meshcore-web-flasher) with `firmware-merged.bin`. Attach the antenna to the Wio-SX1262 before powering it. The default admin password is `password`: change it first.

## Quick start

1. **Check the board.** A Heltec WiFi LoRa 32 **V4 R2** (see the hardware check above) or a Seeed Studio XIAO ESP32S3 with the Wio-SX1262 kit (see [supported boards](#supported-boards)).
2. **Get the firmware.** Download `firmware-merged.bin` from this repository's [Releases page](https://github.com/propertymonitor-web/lodestar.alpha2/releases), or [build your own](#build-it-yourself-custom-splash-text-or-a-newer-meshcore).
3. **Flash it** at https://flasher.meshcore.io using Chrome or Edge ([step by step](#flashing-with-the-meshcore-web-flasher)).
4. **Set it up.** Open a serial terminal (the console on the flasher page works, or any serial program at 115200 baud). **Set a new admin password first**, then a name and your local mesh's radio settings ([first-time setup](#first-time-setup)).
5. **Watch it work.** Type `lodestar`. Give it about 10 minutes of adverts and traffic first.

---

## What you get

- **Live uplink scoring.** LODESTAR keeps a table of every repeater it can hear directly and ranks them by, in order of importance:
  1. **Reliability.** Does that repeater actually pass along what we send? LODESTAR listens for the repeater re-broadcasting our packets (an *implicit ACK*) and blends that with how consistently we hear it.
  2. **Link quality.** Smoothed SNR (judged against the real LoRa floor for your spreading factor) and RSSI.
  3. **Hop count.** How few hops beyond that repeater its traffic reaches.
- **Smart timing, never blocking.** LODESTAR *always forwards*. It never silences your node. It uses the scores to decide *when*: the best-connected position transmits first, a poorly connected one yields to better-placed repeaters.
- **Duplicate cancel.** If a strong uplink (score of at least 0.60 and link quality of at least 0.50) has already forwarded a packet, LODESTAR drops its own queued copy. That saves airtime for everyone.
- **Anti-flap hysteresis.** As you drive, the best uplink changes. A challenger has to win clearly, more than once in a row, before LODESTAR switches, so it does not bounce between two similar repeaters.
- **Staleness decay.** A repeater you drove away from fades out of the ranking gracefully and is dropped after 30 minutes.
- **Safe fallback.** No usable uplink in range? LODESTAR behaves exactly like the stock MeshCore repeater.
- **Built-in table.** One serial command, `lodestar`, shows you what the node sees.
- **Knows where it is.** LODESTAR tracks its own fix, speed and heading (`lodestar gps`). For now this is display only: no forwarding decision uses it yet. GPS is **off until you switch it on** (`gps on`), because some V4 R2 boards ship with a GNSS module and some do not. See [GPS and position](#gps-and-position).
- **Custom splash.** Boots to a centered LODESTAR PULSAR / BY / WRS screen.
- **Everything else is stock MeshCore.** Admin login, regions, CLI, OTA, adverts: the repeater you know, plus the brain.

## Why it makes a good mobile repeater

| Fixed repeater firmware | LODESTAR PULSAR |
| --- | --- |
| Treats every neighbour the same, all the time | Ranks neighbours by reliability, signal, and reach, and re-ranks continuously |
| Forwards on a random timer regardless of position | Best-placed position goes first, weak position yields |
| Several repeaters repeat the same packet back to back | Drops its own copy when a strong uplink already sent it |
| Keeps old neighbours as if nothing changed | Decays and expires neighbours you have left behind |
| No view into what the node can hear | `lodestar` prints a live, ranked table |

The result you are aiming for is less wasted airtime, faster hand-off between uplinks as you move, and a node that is a good citizen rather than a noise source.

**Honest limits.** MeshCore does not let a repeater hand a flooded packet to one chosen neighbour; flood packets are broadcast, and direct packets are routed by the sender. So LODESTAR cannot "deliver to repeater X". It steers by timing and by cancelling duplicates, which for a moving node achieves much of the same effect. It also cannot read message contents (they are encrypted); it only sees packet headers, paths, and signal quality, which is all it needs.

---

## What you need

- A **Heltec WiFi LoRa 32 V4 R2** (ESP32-S3R2, OLED version) with its LoRa antenna attached. **Never power the radio without an antenna.** Not for the V4-R8: see the hardware check at the top. If your listing says R8, do not flash this.
- Optional: a GNSS module (for example Heltec's L76K) in the board's GNSS connector, for position tracking. LODESTAR works fine without one.
- A USB data cable (not a charge-only cable).
- A computer with **Chrome or Edge** (the flasher uses Web Serial, which Firefox and Safari do not support).
- The `firmware-merged.bin` file for LODESTAR.

## Getting the firmware

### The easy way: download a release (no GitHub account needed)

1. Open this repository's [Releases page](https://github.com/propertymonitor-web/lodestar.alpha2/releases) (also on the right-hand side of the repo's front page).
2. Under the latest release, download **`firmware-merged.bin`**. This is the full image, and it is the file you want for a first flash.
3. Skip ahead to [Flashing](#flashing-with-the-meshcore-web-flasher).

Other files in a release:
- `firmware.bin`: the application only, for updating an existing LODESTAR install.
- `splash_preview.png`: an approximate preview of the boot screen.

### Build it yourself (custom splash text, or a newer MeshCore)

You need a GitHub account and your own **fork** of this repository (the **Fork** button at the top of the page), because only people with write access to a repo can run its builds.

1. In your fork, open the **Actions** tab, enable workflows if GitHub asks, then choose **Build LODESTAR firmware**.
2. Click **Run workflow**. The defaults give the LODESTAR PULSAR / BY / WRS splash. Change the three text lines or the seconds on screen if you like (type `-` to leave a line blank), then click the green button.
3. A build takes about 3 minutes (longer the first time). Refresh the page; a green check means it worked. A red cross means something failed, and the error lines appear on the run's summary page.
4. Open the finished run and scroll to **Artifacts** at the bottom. Download the zip (you must be signed in) and unzip it. It contains the same files as a release, plus `meshcore_commit.txt` (which MeshCore version it was built on). Artifacts are kept for 90 days.

Repository owners can tick **Publish the result as a GitHub Release** in the same form to turn a build into a downloadable release for everyone. Type a **new** tag in the release tag box (for example `v0.2.0-alpha`); the workflow refuses an empty tag or one that already exists, and never overwrites an old release. Publish from `main` so the release matches the code.

Every push, and every pull request into `main`, also runs a quick check (seconds to a minute or so): the unit tests, and a test that the patch still applies to the newest MeshCore. It does not build firmware. Only **Run workflow** does that.

### Build it on your own computer

No GitHub account needed. You need `git`, Python 3 (the build runs on 3.11; it also works on 3.13), a C++ compiler (`g++` or `clang++`) for the tests, and [PlatformIO](https://platformio.org/) for the firmware. On Windows, WSL is the easiest way to get all of these. The first firmware build downloads the ESP32 toolchain, which is a few hundred MB and takes a while; later builds are quicker.

```
pip install platformio pillow numpy
git clone https://github.com/propertymonitor-web/lodestar.alpha2.git lodestar
cd lodestar
```

**1. Run the tests** (quick, and no hardware needed):

```
g++ -std=c++17 -Wall -Wextra -Ilodestar lodestar/test/test_lodestar.cpp -o lodestar_test
./lodestar_test
```

It should end with `all tests passed`.

**2. Get MeshCore and apply LODESTAR to it.** Use a fresh clone every time; the script refuses to patch a checkout that already has LODESTAR in it.

```
git clone --depth 1 https://github.com/meshcore-dev/MeshCore.git
python tools/apply_lodestar.py --meshcore MeshCore
```

If upstream MeshCore has changed enough that a patch no longer fits, the script stops and names the part it could not find, rather than leaving a half-patched tree. If you hit that, let the maintainers know which part it named.

**3. Set the boot splash.** Up to three text lines (use `-` for a blank line), the seconds it stays on screen, and a preview image to check it:

```
python tools/make_splash.py --meshcore MeshCore --line "LODESTAR PULSAR" --line BY --line "WRS" --seconds 5 --preview splash_preview.png
```

**4. Build.**

```
cd MeshCore
pio run -t mergebin -e heltec_v4_repeater
```

The finished files are in `MeshCore/.pio/build/heltec_v4_repeater/`: `firmware-merged.bin` (first flash) and `firmware.bin` (updates). Flash with the web flasher as described below. `git -C MeshCore rev-parse HEAD` tells you which MeshCore version you built on.

## Flashing with the MeshCore web flasher

1. Plug the Heltec V4 R2 into your computer with the USB data cable.
2. In Chrome or Edge, go to **https://flasher.meshcore.io**.
3. Choose **Custom Firmware** and select `firmware-merged.bin`.
4. Click to connect and pick the board's serial port from the browser prompt. (It usually appears as a USB serial or Silicon Labs / Espressif device.)
5. Start the flash and wait for it to finish. Do not unplug the board while it is writing.
6. The board reboots. You should see the **LODESTAR PULSAR / BY / WRS** splash for 5 seconds, then the normal repeater screen.

**If the port will not connect:** put the board in **bootloader mode** (Heltec's documented method): with the USB cable connected, hold **PRG**, tap **RST** once, then release **PRG**. Then try again. Holding PRG while plugging in the cable also works on many boards. If it still will not connect, try a different cable or USB port, and see [Troubleshooting](#troubleshooting) for operating-system notes. When the flash finishes, press **RST** (or unplug and replug) to restart the board.

### Flashing with PlatformIO (if you build on your own computer)

The web flasher is the simplest route. If you built the firmware yourself with the [steps above](#build-it-on-your-own-computer), you can upload straight from the MeshCore folder instead. Put the board in bootloader mode (see above), then:

```
cd MeshCore
pio run -t upload -e heltec_v4_repeater
```

Restart the board when it finishes. To talk to it afterwards, use `pio device monitor -b 115200`. Only one program can use the serial port at a time, so close the monitor (and any browser tab using the flasher) before uploading again.

**First flash vs update:** use `firmware-merged.bin` for a first flash. If the flasher offers an *erase* option, erasing wipes the node's stored identity and settings, so only do that if you want a clean start. For later updates you can usually flash over the top and keep your settings.

---

## First-time setup

Open a serial terminal to the board (the flasher's console, `pio device monitor -b 115200`, or any terminal at 115200 baud), then configure it like any MeshCore repeater. Type `help` for the full list; the usual first steps are:

- **First, change the admin password** from the default (`password <new password>`). Anyone who knows the default can log in as admin, and if you later turn GPS on, read the node's live position.
- Give it a recognisable **name** so other nodes can identify it, for example `set name FR-Lodestar-1`.
- Set the **radio parameters** (frequency, bandwidth, spreading factor, coding rate) to match your local mesh, in the form `set radio <MHz>,<bandwidth kHz>,<SF>,<CR>`. The node answers `OK - reboot to apply`, so type `reboot` afterwards. **Use the settings your local community uses, or a private channel for testing.**
- Send an **advert** (`advert`) so nearby repeaters learn you exist.

**Do not skip the radio settings.** LODESTAR needs to hear the same repeaters your community uses.

That is everything you need to do on the board. The scripts in `tools/` run on your computer *before* you build; there is nothing to run from them after flashing.

### What you can customise, and where

| What | How | Kept after a reboot? |
| --- | --- | --- |
| Node name, radio settings, admin password | MeshCore serial commands (`help` lists them all) | Yes, MeshCore saves them |
| Uplink scoring: on/off, weights, floor, duplicate cancel | `lodestar on` / `off`, `weights`, `floor`, `cancel` (see [Commands](#commands)) | Yes, saved to the board's flash the moment you change them |
| GPS (off by default) | `gps on` / `gps off`, then `lodestar gps` to read it | Yes, saved by MeshCore |
| Boot splash: text, seconds, logo | `tools/make_splash.py` on your computer, or the text boxes in the Actions form | It is part of the firmware, so reflash to change it |
| Patching LODESTAR onto MeshCore | `tools/apply_lodestar.py`, done for you by the Actions build | Build step only |

**Splash options** (`tools/make_splash.py`). Up to 3 lines of text, plain letters, numbers and punctuation only (use `-` for a blank line). `--seconds` is 1 to 30. For a logo, add `--logo path/to/image.png`: any PNG, JPG, GIF, BMP or WEBP is converted to a 1-bit picture for the 128×64 screen. If it comes out inverted add `--invert true`, and `--threshold` (1 to 99, default 20) makes a logo bolder when lower. Always look at the `--preview` image before flashing. The Actions form has no logo option, so use the local build for a logo.

---

## Using LODESTAR

### The table

Type `lodestar` in the serial terminal:

```
*A11111 sc 83 rel 92 lq 89 hp 50 snr  8.0 rssi -85 age  20s ack12/14
+B22222 sc 73 rel 92 lq 56 hp 50 snr -2.0 rssi-105 age  20s ack 9/14
```

| Field | Meaning |
| --- | --- |
| `*` / `+` | `*` is the current best uplink. `+` marks the other top-ranked uplinks. |
| first column | Leading hex of the repeater's identity (the same short hash MeshCore shows in paths). |
| `sc` | Composite score, 0 to 100. This is what ranks the table. |
| `rel` | Reliability, 0 to 100. |
| `lq` | Link quality, 0 to 100. |
| `hp` | Hop score, 0 to 100 (50 means "nothing learned yet"). |
| `snr` / `rssi` | Smoothed signal readings. |
| `age` | Seconds since this repeater was last heard. |
| `ack a/b` | How many times it echoed our packets, out of how many tested. |

The summary line reports the best uplink, how many repeaters are heard, the current delay multiplier, and how many duplicate transmissions have been cancelled.

### Commands

| Command | Effect |
| --- | --- |
| `lodestar` | Print the table and summary |
| `lodestar weights R L H` | Set the weights for reliability, link quality, hops (they are normalised). Default is `5 3 2` |
| `lodestar floor F` | Minimum score to count as a usable uplink, 0 to 1. Default `0.25` |
| `lodestar cancel on` / `off` / `F` | Turn duplicate-cancel on or off, or set its minimum score. Default on, `0.60` |
| `lodestar off` / `on` | Fall back to stock forwarding, or re-enable LODESTAR |
| `lodestar gps` | Show GPS status: fix, satellites, moving or stopped, speed and heading |
| `lodestar defaults` | Put weights, floor and cancel back to the defaults, and turn LODESTAR on |
| `lodestar reset` | Clear the uplink table (settings are kept) |

**Settings are remembered.** Any `lodestar` setting you change (on/off, weights, floor, cancel) is saved to the board's flash straight away and restored at every start, so it survives reboots, reflashing the same firmware, and power loss, with or without a battery. `lodestar defaults` puts everything back to the factory values. The uplink table itself is not saved: it is rebuilt from what the node hears, so give it a few minutes after a restart. Settings are kept in their own small file, so erasing the board's flash (the flasher's *erase* option) removes them.

### GPS and position

The Heltec V4 firmware in MeshCore already supports the board's GNSS connector; and LODESTAR leaves it exactly as MeshCore ships it: **off**. Many V4 R2 boards come with a GNSS module fitted, so if yours does, turn it on once with `gps on` (MeshCore remembers it). LODESTAR then reads the fix.

```
GPS: fix, 9 sats, moving 54 km/h, course 0
pos 32.751485,-97.330000 sats 9 fix age 1s speed 15.0 m/s course 0
```

- The first line is the command's reply. The second line (with coordinates) prints on the **local serial port only**. A reply can travel over the mesh to a remote admin, so it never contains your position.
- Speed and heading are worked out from successive fixes (speed over about 3 seconds, heading after at least 8 m of travel). A parked node, wobbling a couple of metres, is reported as stopped.
- **Privacy: read this before you drive.** Once you turn GPS on, the node knows where it is, and **anyone who logs in as admin can ask the node for its live position** (MeshCore's telemetry request). The default admin password is the word `password`, so **change it first** (`password <new password>`) and do not share it. Guests cannot read the position. Adverts keep using the location stored in the repeater's settings, not the live fix, unless you run `gps advert share`, which broadcasts it; LODESTAR leaves that alone. Two commands to know: `gps setloc` copies the live fix into the stored location that adverts then announce, so do not run it somewhere you do not want to be found. To switch tracking off, run `gps off`.
- **Turning it on.** Run `gps on`, then `gps` to see the hardware state and `gps diag` for detail. These are MeshCore commands. If `gps on` says `gps toggle not found`, no GNSS module was detected at boot (see Troubleshooting).- The GPS needs a clear view of the sky. After a cold start, allow a few minutes for the first fix.

### Getting the most out of it

- **Mount the antenna well.** A good antenna with a clear view matters far more than any firmware. On a vehicle, put it on the roof or high on the glass, away from metal that shadows it.
- **Give it steady power.** A vehicle USB supply or a decent battery pack. A fitted battery rides through short power cuts. A brown-out or flat battery restarts the node, which clears the uplink table (your settings are kept).
- **Let it warm up.** The table needs a few minutes of adverts and traffic before the scores mean much. Reliability numbers firm up as it collects implicit ACKs.
- **Match your community's radio settings** exactly, or it will not hear anyone.
- **Do not stack mobile repeaters in the same spot.** One well-placed mobile repeater helps; five in a convoy mostly add noise.
- **Check the table at stops.** If the best uplink score is low, move a little. Often a few metres changes everything.
- **Start with defaults.** The weights reflect reliability first, link quality second, hops third. Change them only after you have watched the table over a few drives.
- **Use `lodestar off` to compare.** Run the same route with LODESTAR off and on to see the difference for yourself.

---

## Test checklist

If you are one of the people helping to test LODESTAR, here is what is most useful to learn:

1. Does it flash cleanly, and does the splash show **LODESTAR PULSAR / BY / WRS**?
2. Does `lodestar` list the repeaters you know are nearby after about 10 minutes?
3. Drive a route. Do the `*` best-uplink marks follow the repeaters you would expect, and does it switch without flapping?
4. Do the numbers look sensible? For example, is a repeater you can barely hear ranked low?
5. Compare `lodestar on` against `lodestar off` on the same route. Do messages get through better, the same, or worse?
6. Watch the `cancels` count in the summary. Does it climb in busy areas? Does anything seem to go missing when it does? If so, try `lodestar cancel off`.
7. Does it behave sensibly when you leave all coverage and come back?
8. With a GNSS module fitted: does `lodestar gps` get a fix, and does it report `moving` with a sensible speed and heading while you drive, and `stopped` when you park?

Please note your radio settings, spreading factor, location type (city, rural, hills), and anything odd. Screenshots or copy-pastes of the `lodestar` output are very helpful.

## Troubleshooting

| Problem | Try |
| --- | --- |
| Flasher cannot see the board | Use Chrome or Edge, a data cable (not charge-only), a different port, and bootloader mode (hold PRG, tap RST, release PRG) as described under [Flashing](#flashing-with-the-meshcore-web-flasher) |
| "Port busy", or the browser cannot open the port | Only one program can use the serial port. Close other serial monitors, the PlatformIO monitor, and other browser tabs using the flasher, then unplug and replug |
| **Linux:** no port in the list, or "permission denied" | Your user needs access to the port. Check which group owns it (`ls -l /dev/ttyACM0` or `/dev/ttyUSB0`), usually `dialout` (`uucp` on Arch), then `sudo usermod -aG dialout $USER` and log out and back in. On some systems ModemManager grabs new serial devices, so if the port vanishes right after plugging in, stop that service while flashing |
| **macOS:** no port in the list | Try another cable and port. Most boards need no driver. If yours uses a Silicon Labs USB chip, install Silicon Labs' CP210x driver |
| **Windows:** no COM port, or an unknown device in Device Manager | Try another cable and port. Windows 10 and 11 usually recognise the board by themselves. If yours uses a Silicon Labs USB chip, install Silicon Labs' CP210x driver |
| Flash fails part-way | Use a better USB cable, plug straight into the computer rather than a hub, put the board in bootloader mode, and try again |
| Table is empty | Make sure the radio settings match your mesh, wait for adverts, and run `advert` |
| Scores look odd right after boot | Normal. Give it several minutes to build history |
| Everything is ranked low | Check the antenna, the radio settings, and your spreading factor |
| `lodestar gps` says `no fix` | Give it a clear view of the sky and a few minutes. Check that a GNSS module is plugged in, and run `gps` and `gps diag` |
| `gps on` says `gps toggle not found`, or GPS stays off | No GNSS module was detected at boot (MeshCore only looks for one during start-up), or the node has `gps off` saved. Check the module, reboot, then run `gps on` |
| Board will not boot, or the GPS never powers up | Check you have a V4 **R2**. This build is not for the V4-R8. To recover a board that will not boot, hold PRG, tap RST, release PRG, then reflash |
| You want stock behaviour | `lodestar off` |
| Splash still shows the old text | You flashed the wrong file; rebuild and flash `firmware-merged.bin` |

---

## For developers

- `lodestar/Lodestar.h` holds the logic. It is header-only and has no Arduino dependencies, so it can be tested on a PC.
- `lodestar/test/test_lodestar.cpp` has the unit tests. Run them as in [Build it on your own computer](#build-it-on-your-own-computer): `g++ -std=c++17 -Wall -Wextra -Ilodestar lodestar/test/test_lodestar.cpp -o lodestar_test && ./lodestar_test`.
- **Architecture.** `Lodestar.h` knows nothing about MeshCore. The patch script adds a few hooks to the repeater (packet received, packet sent, advert heard, retransmit delay, main loop, GPS fix, CLI) that feed it data and ask it for answers.
- `tools/apply_lodestar.py` patches a MeshCore checkout's `examples/simple_repeater`. Every edit must match exactly once, so it stops with a clear message if upstream MeshCore changes.
- `tools/make_splash.py` generates the boot splash.
- `.github/workflows/build.yml` has three jobs. `test` and `patch-check` run on every push and pull request. `build` runs only when started by hand: it applies the patches, builds the Heltec V4 repeater, and publishes the artifact. See [Build it on your own computer](#build-it-on-your-own-computer) for the same steps run locally.

### How the scoring works, briefly

- **Reliability** blends an implicit-ACK success rate (0.6) with how consistently the repeater has been heard over the last 16 twenty-second windows (0.4). The ACK part is used only after at least 3 tests; before that, consistency alone counts.
- **Link quality** is 0.7 SNR margin above the LoRa demodulation floor for your spreading factor, plus 0.3 RSSI.
- **Hop score** is `1 / (1 + h)` where `h` is how many hops beyond that repeater its flooded adverts reached us. This is a heuristic, because a node cannot see true hop counts to the whole mesh, so it carries the lowest weight.
- The **composite** is the weighted sum, multiplied by a freshness factor that fades from full at 2 minutes to zero at 10 minutes.
- The **delay multiplier** is `0.4 + 1.2 × (1 − best score)` when a usable uplink exists, otherwise `1.0`.

## Credits and responsibility

LODESTAR is built on **MeshCore**, an open-source project; please see the MeshCore repository for its license terms and documentation. LODESTAR is a community give-away from Wolf Reactive Systems (WRS), provided as is, with no warranty.

Builds are not byte-for-byte reproducible: each build uses the newest MeshCore at that moment, and `meshcore_commit.txt` records which one. Transmit only where and how your local regulations allow (frequency, power, duty cycle; the V4's transmit power setting is not the same number as the power at the antenna), and follow your local mesh community's norms before adding a repeater to a shared network. An experimental repeater can disturb a mesh if it misbehaves, so test privately first.

**LODESTAR by Wolf Reactive Systems (WRS)**
