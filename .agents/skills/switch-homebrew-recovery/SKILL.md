---
name: switch-homebrew-recovery
description: Recover a modded Nintendo Switch whose CFW black-screens (hekate boots but Atmosphère does not), push RCM payloads from macOS, line up hekate/Atmosphère with the console's firmware, and get a valid key dump for game extraction. Use when the console shows a black screen after the hekate menu, when a payload injector fails with a USB error, when Atmosphère needs updating after a firmware bump, or when `prod.keys` is too old to decrypt a title (missing `key_area_key_application_N`).
---

# Switch homebrew recovery

Everything here was established recovering a console that booted hekate but black-screened on CFW, and then
needed a key generation its old dump did not have. The work is diagnostic and ordering, not guesswork: establish
**where** the chain dies, align the versions, and only then touch keys.

## Ground rules

- **The user's own console only.** Keys come from their hardware; never from a mirror, forum or "key pack".
  Lockpick_RCM is under a DMCA takedown — do not fetch or link mirrors of it. If the user's dump is too old,
  they re-dump on their own console after CFW works.
- **Never print, commit or copy key values** into a repository, log or message. Key *names* (`key_area_key_application_15`)
  are fine and are how you diagnose a generation gap.
- **Back up NAND before any write to it**: hekate → Tools → Backup eMMC (boot0, boot1, rawnand) to the SD.
  Payload pushing and SD file updates do not touch NAND; `emuMMC` repair and restores do.

## 1. Find where the chain dies

Ask for the one observable that splits the tree:

| What is on screen | Where it died | Go to |
|---|---|---|
| Nothing at all, no hekate/NyX menu | payload / RCM / SD read | §2 |
| Hekate menu, then black on the CFW entry | chainloader: stale `fusee.bin` or `fssub`/`fss0` to an old `package3` | §3 |
| Atmosphère logo ~1 s, then black | Atmosphère started and died: version mismatch with firmware, stale sysmodule, corrupt emuMMC | §3, §4 |
| OFW also black | firmware/NAND — stop and back up before anything | §4 |

## 2. Payload push from macOS

The console in RCM enumerates as USB **0955:7321** ("NVIDIA Corp." / "APX"), interface class `0xff`, bulk IN
`0x81`, OUT `0x01`, 512-byte packets. `dm/tools/switch_rcm.py` prints the protocol:

```
python3 dm/tools/switch_rcm.py --list              # is an RCM target there?
python3 dm/tools/switch_rcm.py hekate.bin --wait 30
```

Needs `pyusb` (`.venv/bin/pip install pyusb`); the tool says so instead of raising when it is missing.

**Success signal without seeing the screen:** the APX device **disappears and stays gone** — the payload ran
and the console re-enumerated. If it vanishes and returns, the payload was rejected.

Failure modes, in the order they actually happen:

- **`EPIPE` / `Pipe error` on the bulk write, repeatedly** — the console's RCM buffer is wedged (a half-finished
  transfer does it). Only a power cycle clears it: hold **Power ~15 s**, then re-enter RCM (Vol+ held, tap
  Power). Do not keep retrying a wedged console.
- **APX on a hub** — a hub between Mac and console breaks RCM bulk transfers while control transfers still work.
  Plug straight into the Mac. A charge-only cable shows no APX at all.
- **Claims / configuration** — the tool claims interface 0 and retries with a fresh handle; macOS needs no kext.

## 3. Align hekate and Atmosphère with the firmware

The usual black screen after a firmware bump: the pack (KATE, Kosar, HATS, DeepSea…) bundles an Atmosphère older
than the installed firmware. Check the current releases rather than trusting a pack:

```
curl -s https://api.github.com/repos/CTCaer/hekate/releases/latest            | grep -m1 tag_name
curl -s https://api.github.com/repos/Atmosphere-NX/Atmosphere/releases/latest | grep -m1 tag_name
```

As of 2026-11: **hekate v6.5.5**, **Atmosphère 1.12.2** (adds 23.0.0, basic 23.5.0). Atmosphère's notes matter:
`fusee.bin` was re-issued 2026-11-13 (sha256 prefix `E8B8D926D5…`) to fix an nogc patch on 23.5.0 — check the
hash of whatever `fusee.bin` sits on the SD against the release.

SD pass, in this order:

1. Copy `atmosphere-<ver>-master-*.zip` contents over the SD root (`atmosphere/`, `switch/`, `hbmenu.nro`).
2. Overwrite **`sd:/bootloader/payloads/fusee.bin`** with the release's `fusee.bin` (a stale one is the classic
   hekate-menu-then-black).
3. Put `hekate_ctcaer_<ver>.bin` at `sd:/bootloader/update.bin` and flash it once with the injector.
4. Write an explicit `sd:/bootloader/hekate_ipl.ini` (no pack magic):

   ```ini
   [Atmosphere CFW (sysMMC)]
   fss0=atmosphere/package3
   emummc_force_disable=1

   [Atmosphere CFW (emuMMC)]
   fss0=atmosphere/package3
   emummc!=
   ```

5. Rename `sd:/atmosphere/contents` → `contents.off` and `sd:/atmosphere/exefs_patches` → `exefs_patches.off`
   **before the first boot**; stale sysmodules (MissionControl, sys-clk, ftpd, Emuiibo) and stale sigpatches are
   the second-most-common black screen. Re-enable one at a time once CFW boots.
6. Boot. If it works, add back sigpatches (`bootloader/patches.ini` + `exefs_patches`) from a build matching the
   firmware, then the sysmodules.

## 4. When CFW still will not boot

- **Boot OFW (Stock sysNAND) from hekate.** OFW booting proves firmware/NAND are healthy and isolates the fault
  to the CFW files. OFW also failing means stop: back up NAND first.
- **Test sysMMC only** (`emummc_force_disable=1`). A corrupt emuMMC black-screens silently; hekate → Tools →
  emuMMC → Check reports it, and rebuilding from the backup is the fix.
- **Check the card on the Mac**: `diskutil list`, then `fsck_msdos -n /dev/diskXs1`. ExFAT with a dirty bit is a
  frequent cause; FAT32 is the safer format for hekate + Atmosphère.
- **Read the failure**: `sd:/atmosphere/fatal_errors/*.bin` and `sd:/atmosphere/crash_reports/` record the last
  Atmosphère abort even when the screen never lights.

## 5. Keys, only after CFW boots

A dump must contain the title's key generation, or extraction dies on the first NCA:

```
Unhandled exception. LibHac.Common.Keys.MissingKeyException: Unable to decrypt NCA section.
Key Name: key_area_key_application_15
```

Check coverage without printing secrets:

```
grep -o "^key_area_key_application_[0-9]*" prod.keys | sort -t_ -k4 -n | tail -3
```

`key_area_key_application_N` follows the firmware's key revision, so a dump from a console on older firmware
cannot contain a newer title's generation. Fix by updating the console's firmware (with CFW already aligned to
it, §3) and re-dumping with the user's own tool — not by sourcing a key file.

Then, for this repository, the survey is:

```
python3 scripts/build_ipa_from_nsp.py "<NSP folder>" --survey-only -k <user's prod.keys>
```

Keys live in the game's work folder, never in the repo, never in a commit, never printed (`docs/agents/01-extract.md`).

### Keeping a dump current (the "futureproof" procedure)

There is no authoritative public firmware → key-generation table (switchbrew documents 21.0.0's system titles but
not its key revision), and the sites that publish one usually ship firmware or `prod.keys` alongside — do not use
those. Measure instead:

1. **The dumper must be newer than the firmware.** A build that predates the console's system version stops after
   `MMC init` with `unknown package version` / `key generation unknown`. That message is about *the tool*, not the
   console — and a repackaged old build (same version number, fresh zip date) behaves identically, so judge by what
   it prints, not by the download's date. Observed: Lockpick_RCM "2.0.1" packaged 2026-09-10 dumped a 21.0.0 console
   only as far as generation 16.
2. **Read coverage out of every dump.** The highest `master_key_N` / `key_area_key_application_N` is the revision the
   console reported; if it is below the console's firmware era, the dumper is old.
3. **Re-dump after every major firmware update and before starting a new port.** An out-of-date dump only surfaces
   as a `MissingKeyException` halfway through an extraction.
4. **Record provenance beside the dump**: console serial, firmware, date, dumper build, coverage range, and the
   generations *not* covered — so the next person knows exactly what to redo.
5. **Dumps are per-console secrets**: mode 600, out of the repository, off public or syncing locations, never
   pasted into a log, issue or chat. Someone else's key file is not a substitute — it is not the user's console,
   and it is what the takedowns target.

Empirical ground truth beats any table: a dump "covers a title" exactly when that title's NCAs decrypt.

## Checklist

- [ ] `dm/tools/switch_rcm.py --list` shows `0955:7321` before blaming the payload
- [ ] hekate and Atmosphère are the current releases, `fusee.bin` hash matches the release note
- [ ] `hekate_ipl.ini` names `atmosphere/package3` explicitly, sysMMC entry has `emummc_force_disable=1`
- [ ] `contents.off` and `exefs_patches.off` for the first boot
- [ ] OFW boot tested before deeper repairs; NAND backed up before any NAND write
- [ ] `prod.keys` generation covers the title; keys never printed or committed
