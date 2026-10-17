# LODESTAR

### Mobile-repeater firmware for MeshCore, by FEAR REACTIVE

**Version v0.1.0-alpha** (alpha test release, **Heltec WiFi LoRa 32 V4 R2 only**)

A repeater that is moving needs to think differently from one bolted to a tower. The tower never changes its neighbours. A vehicle, a hiker, or a boat is constantly gaining and losing them. LODESTAR is MeshCore repeater firmware with a built-in sense of *which repeaters around it are actually worth relying on right now*, and it uses that to forward traffic more intelligently.

It is free, open, and built for the **Heltec WiFi LoRa 32 V4 R2** (ESP32-S3R2, OLED).

> **Hardware check before you flash.** Heltec sells the V4 in two versions: **V4 R2** (ESP32-S3R2, 2 MB PSRAM) and **V4-R8** (ESP32-S3R8, 8 MB PSRAM). **This firmware is for the R2 only.** The two boards use different pins for GPS, the LED and external power, so an R2 image on an R8 can leave the GPS unpowered or misbehave. Check the MCU option on your order or listing before flashing. If you have an R8, do not use this build yet.

> **Status: field-test release.** The firmware compiles, and the scoring logic is covered by automated tests, but it is new. That is why this README has a testing section. Your drive logs are exactly what will make it better.

---

## What you get

- **Live uplink scoring.** LODESTAR keeps a table of every repeater it can hear directly and ranks them by, in order of importance:
  1. **Reliability.** Does that repeater actually pass along what we send? LODESTAR listens for the repeater re-broadcasting our packets (an *implicit ACK*) and blends that with how consistently we hear it.
  2. **Link quality.** Smoothed SNR (judged against the real LoRa floor for your spreading factor) and RSSI.
  3. **Hop count.** How few hops beyond that repeater its traffic reaches.
- **Smart timing, never blocking.** LODESTAR *always forwards*. It never silences your node. It uses the scores to decide *when*: the best-connected position transmits first, a poorly connected one yields to better-placed repeaters.
- **Duplicate cancel.** If a strong uplink has already forwarded a packet, LODESTAR drops its own queued copy. That saves airtime for everyone.
- **Anti-flap hysteresis.** As you drive, the best uplink changes. A challenger has to win clearly, more than once in a row, before LODESTAR switches, so it does not bounce between two similar repeaters.
- **Staleness decay.** A repeater you drove away from fades out of the ranking gracefully and is dropped after 30 minutes.
- **Safe fallback.** No usable uplink in range? LODESTAR behaves exactly like the stock MeshCore repeater.
- **Built-in table.** One serial command, `lodestar`, shows you what the node sees.
- **Knows where it is.** GPS is on by default. LODESTAR tracks its own fix, speed and heading (`lodestar gps`). This is groundwork for position-aware features; for now it is read-only and changes nothing about how packets are forwarded.
- **Custom splash.** Boots to a centered LODESTAR / BY / FEAR REACTIVE screen.
- **Everything else is stock MeshCore.** Admin login, regions, CLI, OTA, adverts: the repeater you know, plus the brain.

## Why it makes a good mobile repeater

| Fixed repeater firmware | LODESTAR |
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

- A **Heltec WiFi LoRa 32 V4 R2** (ESP32-S3R2, OLED version) with its LoRa antenna attached. **Never power the radio without an antenna.** This is the standard V4. It is **not** for the V4-R8 (ESP32-S3R8), which uses different GPS, LED and power pins and needs its own build. If your listing says R8, do not flash this.
- Optional: a GNSS module (for example Heltec's L76K) in the board's GNSS connector, for position tracking. LODESTAR works fine without one.
- A USB data cable (not a charge-only cable).
- A computer with **Chrome or Edge** (the flasher uses Web Serial, which Firefox and Safari do not support).
- The `firmware-merged.bin` file for LODESTAR.

## Getting the firmware

### The easy way: download a release (no GitHub account needed)

1. Open this repository's **Releases** page (on the right-hand side of the repo's front page, or add `/releases` to the repo address).
2. Under the latest release, download **`firmware-merged.bin`**. This is the full image, and it is the file you want for a first flash.
3. Skip ahead to [Flashing](#flashing-with-the-meshcore-web-flasher).

Other files in a release:
- `firmware.bin`: the application only, for updating an existing LODESTAR install.
- `splash_preview.png`: an approximate preview of the boot screen.

### Build it yourself (custom splash text, or a newer MeshCore)

You need a GitHub account and your own **fork** of this repository (the **Fork** button at the top of the page), because only people with write access to a repo can run its builds.

1. In your fork, open the **Actions** tab, enable workflows if GitHub asks, then choose **Build LODESTAR firmware**.
2. Click **Run workflow**. The defaults give the LODESTAR / BY / FEAR REACTIVE splash. Change the three text lines or the seconds on screen if you like (type `-` to leave a line blank), then click the green button.
3. A build takes about 6 minutes. Refresh the page; a green check means it worked. A red cross means something failed, and the error lines appear on the run's summary page.
4. Open the finished run and scroll to **Artifacts** at the bottom. Download the zip (you must be signed in) and unzip it. It contains the same files as a release, plus `meshcore_commit.txt` (which MeshCore version it was built on). Artifacts are kept for 90 days.

Repository owners can tick **Publish the result as a GitHub Release** in the same form to turn a build into a downloadable release for everyone.

Every push and pull request also runs a quick check (about a minute): the unit tests, and a test that the patch still applies to the newest MeshCore. It does not build firmware. Only **Run workflow** does that.

### Build it on your own computer

No GitHub account needed. You need `git`, Python 3 (the build runs on 3.11; it also works on 3.13), a C++ compiler (`g++` or `clang++`) for the tests, and [PlatformIO](https://platformio.org/) for the firmware. On Windows, WSL is the easiest way to get all of these. The first firmware build downloads the ESP32 toolchain, which is a few hundred MB and takes a while; later builds are quicker.

```
pip install platformio pillow numpy
git clone <address of this repository> lodestar
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
python tools/make_splash.py --meshcore MeshCore --line LODESTAR --line BY --line "FEAR REACTIVE" --seconds 5 --preview splash_preview.png
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
6. The board reboots. You should see the **LODESTAR / BY / FEAR REACTIVE** splash for 5 seconds, then the normal repeater screen.

**If the port will not connect:** hold the board's **PRG / BOOT** button while plugging in the USB cable, then try again. If it still will not connect, try a different cable or USB port.

**First flash vs update:** use `firmware-merged.bin` for a first flash. If the flasher offers an *erase* option, erasing wipes the node's stored identity and settings, so only do that if you want a clean start. For later updates you can usually flash over the top and keep your settings.

---

## First-time setup

Open a serial terminal to the board (the flasher's console, or any terminal at 115200 baud), then configure it like any MeshCore repeater. Type `help` for the full list; the usual first steps are:

- Give it a recognisable **name** so other nodes can identify it, for example `set name FR-Lodestar-1`.
- Set the **radio parameters** (frequency, bandwidth, spreading factor, coding rate) to match your local mesh. **Use the settings your local community uses, or a private channel for testing.**
- Change the **admin password** from the default.
- Send an **advert** (`advert`) so nearby repeaters learn you exist.

**Do not skip the radio settings.** LODESTAR needs to hear the same repeaters your community uses.

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
| `lodestar reset` | Clear the uplink table |

Settings are not saved across reboots; LODESTAR starts with its defaults each time.

### GPS and position

The Heltec V4 firmware in MeshCore already supports the board's GNSS connector; stock repeaters just ship with it switched off. LODESTAR switches it **on by default** and reads the fix.

```
GPS: fix, 9 sats, moving 54 km/h, course 0
pos 32.751485,-97.330000 sats 9 fix age 1s speed 15.0 m/s course 0
```

- The first line is the command's reply. The second line (with coordinates) prints on the **local serial port only**. A reply can travel over the mesh to a remote admin, so it never contains your position.
- Speed and heading are worked out from successive fixes (speed over about 3 seconds, heading after at least 8 m of travel). A parked node, wobbling a couple of metres, is reported as stopped.
- **What it does not do.** It does not change who can see where you are. Adverts keep using the location you set in the repeater's settings (MeshCore's default), not the live fix. `gps advert share` is the setting that would broadcast it, and LODESTAR leaves it alone.
- **Already used this node?** The default only applies to fresh installs. If the node saved `gps off` earlier, run `gps on` once; it is remembered. `gps` shows the hardware state and `gps diag` shows more detail. These are MeshCore commands.
- The GPS needs a clear view of the sky. After a cold start, allow a few minutes for the first fix.

### Getting the most out of it

- **Mount the antenna well.** A good antenna with a clear view matters far more than any firmware. On a vehicle, put it on the roof or high on the glass, away from metal that shadows it.
- **Give it steady power.** A vehicle USB supply or a decent battery pack. Brown-outs reboot the node and clear its table.
- **Let it warm up.** The table needs a few minutes of adverts and traffic before the scores mean much. Reliability numbers firm up as it collects implicit ACKs.
- **Match your community's radio settings** exactly, or it will not hear anyone.
- **Do not stack mobile repeaters in the same spot.** One well-placed mobile repeater helps; five in a convoy mostly add noise.
- **Check the table at stops.** If the best uplink score is low, move a little. Often a few metres changes everything.
- **Start with defaults.** The weights reflect reliability first, link quality second, hops third. Change them only after you have watched the table over a few drives.
- **Use `lodestar off` to compare.** Run the same route with LODESTAR off and on to see the difference for yourself.

---

## Test checklist

If you are one of the people helping to test LODESTAR, here is what is most useful to learn:

1. Does it flash cleanly, and does the splash show **LODESTAR / BY / FEAR REACTIVE**?
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
| Flasher cannot see the board | Use Chrome or Edge, a data cable, a different port, and the PRG / BOOT button trick above |
| Table is empty | Make sure the radio settings match your mesh, wait for adverts, and run `advert` |
| Scores look odd right after boot | Normal. Give it several minutes to build history |
| Everything is ranked low | Check the antenna, the radio settings, and your spreading factor |
| `lodestar gps` says `no fix` | Give it a clear view of the sky and a few minutes. Check that a GNSS module is plugged in, and run `gps` and `gps diag` |
| `gps on` says `gps toggle not found`, or GPS stays off | No GNSS module was detected at boot (MeshCore only looks for one during start-up), or the node saved `gps off` earlier. Check the module, reboot, then run `gps on` |
| Board will not boot, or the GPS never powers up | Check you have a V4 **R2**. This build is not for the V4-R8. To recover a board that will not boot, hold PRG, tap RST, release PRG, then reflash |
| You want stock behaviour | `lodestar off` |
| Splash still shows the old text | You flashed the wrong file; rebuild and flash `firmware-merged.bin` |

---

## For developers

- `lodestar/Lodestar.h` holds the logic. It is header-only and has no Arduino dependencies, so it can be tested on a PC.
- `lodestar/test/test_lodestar.cpp` has the unit tests (`g++ -std=c++17 -Ilodestar lodestar/test/test_lodestar.cpp`).
- `tools/apply_lodestar.py` patches a MeshCore checkout's `examples/simple_repeater`. Every edit must match exactly once, so it stops with a clear message if upstream MeshCore changes.
- `tools/make_splash.py` generates the boot splash.
- `.github/workflows/build.yml` has three jobs. `test` and `patch-check` run on every push and pull request. `build` runs only when started by hand: it applies the patches, builds the Heltec V4 repeater, and publishes the artifact. See [Build it on your own computer](#build-it-on-your-own-computer) for the same steps run locally.

### How the scoring works, briefly

- **Reliability** blends an implicit-ACK success rate (0.6) with how consistently the repeater has been heard over the last 16 twenty-second windows (0.4).
- **Link quality** is 0.7 SNR margin above the LoRa demodulation floor for your spreading factor, plus 0.3 RSSI.
- **Hop score** is `1 / (1 + h)` where `h` is how many hops beyond that repeater its flooded adverts reached us. This is a heuristic, because a node cannot see true hop counts to the whole mesh, so it carries the lowest weight.
- The **composite** is the weighted sum, multiplied by a freshness factor that fades from full at 2 minutes to zero at 10 minutes.
- The **delay multiplier** is `0.4 + 1.2 × (1 − best score)` when a usable uplink exists, otherwise `1.0`.

## Credits and responsibility

LODESTAR is built on **MeshCore**, an open-source project; please see the MeshCore repository for its license terms and documentation. LODESTAR is a community give-away from FEAR REACTIVE, provided as is, with no warranty.

Transmit only where and how your local regulations allow (frequency, power, duty cycle), and follow your local mesh community's norms before adding a repeater to a shared network. An experimental repeater can disturb a mesh if it misbehaves, so test privately first.

**LODESTAR by FEAR REACTIVE**
