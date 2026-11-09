# LODESTAR PULSAR: Security

Imagined and engineered by: Aries Thorne & Todd Steinhauer
for Wolf Reactive Systems (WRS)

Moral Support: Athena the K9

Special thanks to the NTXMESH community, the MeshCore community, and Pat Steinhauer-Scates for their guidance and support.

This covers the current beta of LODESTAR PULSAR (release line `v1.0.0-beta-UD21214`) on every supported board. It says what PULSAR protects, what it leaves to MeshCore, what you must do yourself, and what has **not** been checked. It does not promise more than that.

**Read this first.** PULSAR is beta firmware. It has had no independent security review or penetration test. Most boards have not been run on real hardware by the makers (see the [architecture notes](ARCHITECTURE.md)). Treat it as you would any new radio firmware: do not use it where a failure would endanger anyone.

---

## 1. Reporting a vulnerability

Please report privately, not in a public issue.

- **Preferred:** GitHub private vulnerability reporting on this repository: **Security tab, then "Report a vulnerability"** (https://github.com/propertymonitor-web/lodestar.alpha2/security/advisories/new).
- Include: the board and release tag, what you did, what you saw, and whether you can reproduce it. Do not include your admin password, private keys, or your location.

This is a small volunteer project. We will read reports and answer as quickly as we can, but we do not offer a guaranteed response time, a bounty, or legal safe harbour. Credit in the fix notes is offered if you want it.

Problems in MeshCore itself (packet format, encryption, login) belong with [meshcore-dev/MeshCore](https://github.com/meshcore-dev/MeshCore). If you are unsure which side a problem is on, report it here and we will route it.

## 2. Supported versions

Only the newest release for each board is supported. The project is in beta; older beta tags do not get fixes.

---

## 3. What PULSAR is, from a security point of view

PULSAR is MeshCore repeater firmware with one added feature (uplink scoring). It **does not change** MeshCore's encryption, authentication, packet format or admin login. Everything security-relevant below that is MeshCore behaviour is inherited, and PULSAR's security is MeshCore's security plus the small amount of new code described here.

The new code:

- reads packets MeshCore already received;
- changes the delay before a flood packet is retransmitted, and can drop a queued duplicate;
- stores a few settings in `/lodestar.cfg`;
- adds one command family, `lodestar ...`;
- on GPS builds, reads the position MeshCore's GPS driver already provides.

It adds **no** network listener, no new radio packet type, no Bluetooth or WiFi service, and no cloud connection.

## 4. Threat model

| Who or what | Capability assumed | What we try to protect |
|---|---|---|
| Anyone on the radio channel | Can hear and send LoRa packets in range | Repeater availability and correct forwarding |
| Someone with physical access | Can plug in USB, press reset | Not defended (see 4.1) |
| Someone who knows or guesses the admin password | Can log in as admin over the mesh or serial | Settings, and the node's live position |
| A malicious or broken neighbouring repeater | Can send adverts and forward packets oddly | Scoring should degrade gracefully, never stop forwarding |
| A compromised download or build | Can alter the firmware or dashboard you flash/open | Integrity of what you run |
| A malicious web page or network on the dashboard side | Can serve altered update data | The person using the dashboard |

### 4.1 Out of scope

- **Physical access.** Anyone with the board can read or change settings over USB serial, reflash it, or erase it. There is no secure boot, flash encryption, or serial lock enabled by PULSAR. Whether your chip supports those and how to enable them is a board-level choice we have not tested.
- **Traffic analysis and RF-level attacks** (jamming, replay at the radio layer, direction finding). LoRa transmissions can be located by anyone with the right equipment.
- **Message confidentiality.** A repeater forwards packets it cannot read. Encryption of message content is MeshCore's job, and PULSAR neither adds to it nor weakens it.

---

## 5. What you must do

1. **Change the admin password before the repeater goes on the air.** The default is the word `password`. Anyone who knows it can log in as admin over the mesh, change settings, and (if GPS is on) read the live position. Use `password <new>` over serial, or the dashboard's **Change** button. Choose something long and do not reuse it.
2. **Keep GPS off unless you need it.** On GPS builds it is off until you run `gps on`. Turn it off with `gps off`.
3. **Do not run `gps advert share` or `gps setloc` somewhere you do not want to be found.** Those MeshCore commands publish or store location that adverts then announce. PULSAR does not run them.
4. **Download firmware only from this repository's Releases page**, and flash with the official [flasher.meshcore.io](https://flasher.meshcore.io) or the board's USB drive method.
5. **Keep the USB cable and the board under your control** when the admin password is not changed.

---

## 6. Security properties, one at a time

### 6.1 Admin access
Controlled entirely by MeshCore's login. The `lodestar` command is routed the same way as other CLI commands, so it is reachable by whoever MeshCore lets run CLI commands. PULSAR adds no authentication of its own. If you can run `lodestar weights`, `off` or `reset`, you are already an admin.

### 6.2 What an attacker with admin can do through PULSAR
Turn scoring off or give it odd weights (reducing forwarding efficiency, or raising/lowering retransmit delay), clear the uplink table, or change duplicate-cancel thresholds. The worst case from PULSAR itself is **degraded efficiency**: it has no command that stops forwarding. (Admin can of course do more through MeshCore's own commands, such as changing radio settings or turning repeating off.)

### 6.3 Location privacy
- Coordinates are **never** included in `lodestar` replies that can travel over the mesh. The remote reply says only: fix or no fix, satellite count, stopped or moving, and (when moving) speed and course.
- Coordinates are printed **only to the local serial port**, by `lodestar gps`.
- Speed and course are reported to an admin. That alone says something about where the vehicle is going.
- MeshCore's own behaviour still applies: an admin can request the live position by MeshCore's telemetry request while GPS is on. This is not changed by PULSAR.

### 6.4 Handling of untrusted radio input
PULSAR reads path bytes, hashes and signal levels from received packets and keeps them in fixed-size tables. All its storage is statically sized, with no run-time allocation. It copies path data into a fixed 64-byte buffer for pending packets and is sized to match MeshCore's maximum. We have not fuzzed the patch or run it under a sanitizer on target hardware; the unit tests cover the logic, not malformed-input robustness. **Treat memory safety against hostile packets as unverified.**

A hostile neighbour could try to make itself look like the best uplink (by sending good-looking adverts, or by echoing packets), which would bias the delay factor and the duplicate-cancel decision toward it. The effect is limited to retransmit timing and dropping duplicates your node would have sent. Real SNR/RSSI are measured by your own radio, which limits what a distant attacker can fake, but a nearby attacker with a transmitter can influence them. We have not measured how effective such manipulation would be.

### 6.5 Stored settings
`/lodestar.cfg` holds scoring settings only. It holds no key, password or position. `loadSettings` rejects anything malformed and keeps the existing values. A modified file (needs physical access or an admin session) can change weights within the validated ranges, not crash-inducing formats we know of; the parser is a bounded `sscanf` into fixed variables.

### 6.6 Companion Bluetooth PIN (affects NOVA builds, not the repeater)
`tools/persist_ble_pin.py` derives the Bluetooth pairing PIN from the ESP32's unique chip ID instead of a fresh random number at each start. Be aware of the trade-off: the PIN is now **predictable to anyone who knows the chip ID**, and the algorithm is public in this repository. It is a 6-digit PIN either way, so it was never strong, but a random-per-boot PIN gave an attacker only one chance per boot. Use `set pin` to set your own PIN if that matters to you. The repeater builds have no Bluetooth service, so they are not affected.

---

## 7. The dashboards

The dashboards are single HTML files that run entirely in your browser.

- **Local only.** They load no external scripts, fonts or images. There is no analytics and no account. They send commands only to the repeater you connect.
- **Network use:** only the **Check for updates** button makes internet requests, to `raw.githubusercontent.com` (the `dashboard_updates` repository) and `api.github.com` (this repository's releases). It sends no repeater data; the request itself reveals your IP address to GitHub.
- **Display safety:** values that come from the repeater or from GitHub (names, versions, release tags) are HTML-escaped before display, because a repeater's name is set by whoever configures it.
- **Update integrity.** `latest.json` lists a size and SHA-256 for each dashboard, but **the dashboard does not verify a download against it**, and the firmware download links point to GitHub release assets with no checksum or signature to compare. If someone gained write access to the `dashboard_updates` repository or to this repository's releases, they could offer you altered files. Download only from the links the update dialog shows, over HTTPS, and compare the SHA-256 in `latest.json` by hand if you want to be sure.
- **USB serial** is protected by the browser's own permission prompt: a page can only use a port you pick from the list.
- **WiFi (`ws://`)** is plain, unencrypted WebSocket. Anything sent over it, including a password you set, can be read by anyone on that network. The current repeater firmware does not serve it, so today nobody can use it, but do not enable such a link on a network you do not trust when it exists.
- **Setting the admin password from the dashboard** sends `password <new>` over the chosen link. Over USB that stays on the cable.
- **Not tested on real hardware.** The dashboards were tested against a simulated repeater only. Bluetooth and WiFi paths are untested.
- The Matrix+MNA Android app is a separate product. Its sideload build is signed with a keystore whose password is committed to its repository, so **the signature proves nothing about who built it**. Install it only from the official release.

---

## 8. Build and supply chain

| Item | Current state |
|---|---|
| MeshCore source | Cloned from `meshcore-dev/MeshCore` `main` at build time, **not pinned**. The commit used is written to `meshcore_commit.txt` and the release notes. |
| Patch safety | Each edit must match upstream exactly once or the build fails. This catches upstream moves, not malicious upstream changes. |
| Third-party actions | `actions/checkout@v4`, `actions/setup-python@v5`, `actions/upload-artifact@v4`, referenced by version tag, **not pinned to a commit hash**. |
| PlatformIO and libraries | Fetched at build time by PlatformIO as MeshCore specifies; not locked or mirrored by this project. |
| Workflow permissions | Default `contents: read`; only the build job holds `contents: write`, to create a Release. A release never overwrites an existing tag. |
| Release files | **Not code-signed.** No checksum file is attached. Built in a fresh GitHub-hosted runner, with the MeshCore commit recorded, so a build can be reproduced approximately but is not guaranteed bit-for-bit identical. |
| Manual trigger | Only people with write access to the repository can run the build and publish workflow. |

Improvements we have not done yet: pin MeshCore and the Actions to commit hashes, publish SHA-256 files with each release, have the dashboard verify them, and sign releases.

---

## 9. Known weaknesses, plainly

1. Default admin password is `password` until changed (MeshCore behaviour, documented loudly here).
2. No integrity check on downloads beyond HTTPS to GitHub.
3. Builds follow MeshCore `main`; a regression or compromise upstream would reach a PULSAR build.
4. No fuzzing or sanitizer run of the patch against malformed packets.
5. Scoring can be influenced by a nearby hostile transmitter; the size of that effect is unmeasured.
6. No flash encryption, secure boot or serial lock configured.
7. Dashboard WiFi link (not yet usable) would be unencrypted.
8. Most boards: compiled in CI only, not run on a real board by the makers.

## 10. What we deliberately do not do

- No remote logging, telemetry, or phone-home from the firmware or dashboards.
- No remote update mechanism. Updates are always something you download and flash yourself.
- No broadcast of your coordinates by PULSAR.
- No hidden accounts, keys or back doors. If you find one, that is a vulnerability: please report it.
