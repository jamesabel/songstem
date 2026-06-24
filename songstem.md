# Real-Time Instrument Removal for Apple Music on Windows

## Overview

This project provides a Microsoft Windows GUI application that:

1) Isolates various song performance parts (known as "stems") such as bass, guitar, or vocals.
2) Creates two version of the stem mixes:
   a) Selected stem is "soloed" so that part is isolated.
   b) Selected stem is "muted" so that part is not in the mix.

This uses Apple Music/iTunes on Windows. Given a playlist name, it creates standard music files with the selected instrument both "solo" and "muted". This entire process is 
automated. It can run in "batch" style of processing.

The system is optimized for:

* Instrument (bass, guitar) or vocal practice
* Cover song rehearsal
* Learning bass, guitar, and/or vocal lines
* Home use

Low latency is not a requirement.

---

# Goals

## Functional Goals

* Source is Apple Music/iTunes.
* User provides a Playlist of songs for the program to create stems for.
* Separate audio into stems.
* Provide the isolated ("solo") instrument or vocal stem in a separate file.
* Mute or attenuate the instrument or vocal and write the results to a separate file.
* Allow stem volume adjustments.
* Include an audio player for the files this application outputs.
* Support various stem creation libraries such as (but not limited to) Open-Unmix or Demucs.


## Non-Goals

* DJ performance.
* Professional live sound reinforcement.
* Low latency. Batch mode is OK.
* Mobile platforms.

## Assumptions

* This will be a Python program
* Any library and/or licensing is acceptable, as long as it's in PyPI.
* PySide may be used for the GUI.
* User has an Apple Music/iTunes subscription.
* Apple Music/iTunes is installed on the Windows machine this program will run on 
* Runs on a system with modern and capable hardware.
* An "x86" architecture processor (Intel or AMD)

## Limitations

* **DRM-protected tracks cannot be processed.** Apple Music subscription downloads and older
  protected iTunes Store purchases are `.m4p` files encrypted with Apple FairPlay (`drms`
  audio stream). No decoder can read them, so they cannot be separated into stems. Only
  DRM-free sources work: CD rips, DRM-free purchases (`.m4a`), and MP3s. The iTunes library
  is still used to read playlists and locate files; the subscription itself does not make
  protected tracks usable.
