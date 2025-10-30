# FM/MFM/RLL decoder for Sigrok/PulseView/DSView
This [plugin](https://github.com/sigrokproject/libsigrokdecode) lets you explore and analyze data stored on floppy disks and MFM/RLL hard drives at a low level using [Sigrok](https://sigrok.org)/[Sigrok-cli](https://sigrok.org/wiki/Sigrok-cli)([github](https://github.com/sigrokproject/sigrok-cli))/[PulseView](https://sigrok.org/wiki/PulseView)([github](https://github.com/sigrokproject/pulseview))/[DSView](https://github.com/DreamSourceLab/DSView) Logic Analyzer software.   
Start by loading one of available [test sample files](#available-test-sample-files) or capture you own data using Logic Analyzer hardware.

- Floppy drive requires at least ~12MHz sampling rate meaning ~$60 Hantek 6022 or $5 CY7C68013A dev board (aliexpress/ebay/amazon) as thats pretty much whats inside the Hantek/original Saleae https://sigrok.org/wiki/Lcsoft_Mini_Board.   
- Hard drives are more demanding (5-15Mbit flux rate) requiring at least 200MHz sampling rate with commercial LAs starting around $200 ... or try your luck with $5 Pico/Pico2 board using open source https://github.com/gusmanb/logicanalyzer.

<details open>
<summary><h2>Table of Contents</h2></summary>

- [Screenshots](#screenshots)
- [Test samples](#available-test-sample-files)
- [Command line usage](#example-sigrok-cli-command-line-usage)
  - [Options](#options)
  - [Annotations](#annotations)
- [Installation](#installation)
- [Resources](#resources)
  - [Polynomials](#polynomials)
  - [Converting polynomial notations](#how-to-convert-polynomial-notations)
  - [CRC](#crc)
  - [Tutorials](#tutorials)
  - [Patents](#patents)
  - [Datasheets](#datasheets)
  - [Anecdotes](#anecdotes)
  - [Emulation](#emulation)
- [Authors](#authors)
- [Changelog](#changelog)
</details>

## Screenshots
#### Full Track view
![Full Track Decode](doc/pulseview_track.png)  
Typical track on MFM encoded hard drive.

#### Sector Header close-up
![Sector Close-Up](doc/pulseview_idrecord.png)  
This is a spare/unused sector created at the end of every track on MFM drive by Seagate ST21 controller. Notice the weird Sector number 254 (0b11111110, for easier hardware filtering?) and absence of GAP3 between end of Header and start of Sync pattern. Without GAP3 this sector is unwriteable without corruption. Every MFM/RLL drive I looked at so far wasted precious space leaving enought unwritten disk surface for one more sector per track. This translates to never using 6% of the MFM and 3% of RLL disk you paid for, about 2.5MB on typical 40MB MFM drive.

## Available test sample files
 - [fdd_fm.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/fdd_fm.sr) 3 channels, 15000000 sample rate, FDD, FM encoding, 125000 bps, 256 Sectors, Data CRC 16bit, data poly 0x1021
 - [fdd_mfm.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/fdd_mfm.sr) 3 channels, 15000000 sample rate, FDD, MFM encoding, 250000 bps, 256 Sectors, Data CRC 16bit, data poly 0x1021
 - [hdd_mfm.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_mfm.sr) 3 channels, 100000000 sample rate, HDD, MFM encoding, 5000000 bps, 512 Sectors, Data CRC 32bit, data poly 0xA00805. VAX2000 HDD.
 - [hdd_mfm.dsl](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_mfm.dsl) as above but in DSView format
 - [hdd_mfm_sector.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_mfm_sector.sr) one sector (sec=8) from above capture. ID CRC F38D, Data CRC C1847279

## Example sigrok-cli command line usage
<details><summary><code>sigrok-cli -D -i hdd_mfm_sector.sr -P mfm -A mfm=bytes:fields</code></summary>
<pre>
mfm-1: A1
mfm-1: Sync pattern 13 bytes
mfm-1: FE
mfm-1: ID Address Mark
mfm-1: 00
mfm-1: 00
mfm-1: 08
mfm-1: 02
mfm-1: ID Record: cyl=0, sid=0, sec=8, len=512
mfm-1: F3
mfm-1: 8D
mfm-1: CRC OK F38D
mfm-1: 4E 'N'
mfm-1: A1
mfm-1: Sync pattern 13 bytes
mfm-1: FB
mfm-1: Data Address Mark
mfm-1: 20 ' '
mfm-1: 3D '='
mfm-1: 20 ' '
mfm-1: 98
mfm-1: 40 '@'
mfm-1: A1
mfm-1: 90
mfm-1: 00
mfm-1: 00
mfm-1: 0F
mfm-1: 07
mfm-1: 2E '.'
mfm-1: 20 ' '
mfm-1: 42 'B'
mfm-1: 59 'Y'
mfm-1: 54 'T'
mfm-1: 45 'E'
mfm-1: 53 'S'
mfm-1: 04
mfm-1: 0F
mfm-1: 01
mfm-1: 20 ' '
mfm-1: 0D
mfm-1: 08
mfm-1: 0F
mfm-1: 10
mfm-1: 53 'S'
mfm-1: 4B 'K'
mfm-1: 49 'I'
mfm-1: 50 'P'
mfm-1: 2F '/'
mfm-1: 53 'S'
mfm-1: 50 'P'
mfm-1: 41 'A'
mfm-1: 43 'C'
mfm-1: 45 'E'
mfm-1: 20 ' '
mfm-1: 43 'C'
mfm-1: 4F 'O'
mfm-1: 55 'U'
mfm-1: 4E 'N'
mfm-1: 54 'T'
mfm-1: 0D
mfm-1: 18
mfm-1: 1C
mfm-1: 08
mfm-1: 04
mfm-1: 04
mfm-1: 0F
mfm-1: 01
mfm-1: 20 ' '
mfm-1: 0D
mfm-1: 28 '('
mfm-1: 0F
mfm-1: 0B
mfm-1: 53 'S'
mfm-1: 4B 'K'
mfm-1: 49 'I'
mfm-1: 50 'P'
mfm-1: 2F '/'
mfm-1: 53 'S'
mfm-1: 50 'P'
mfm-1: 41 'A'
mfm-1: 43 'C'
mfm-1: 45 'E'
mfm-1: 20 ' '
mfm-1: 98
mfm-1: 40 '@'
mfm-1: 70 'p'
mfm-1: 90
mfm-1: 00
mfm-1: 00
mfm-1: 0F
mfm-1: 10
mfm-1: 2E '.'
mfm-1: 20 ' '
mfm-1: 54 'T'
mfm-1: 41 'A'
mfm-1: 50 'P'
mfm-1: 45 'E'
mfm-1: 20 ' '
mfm-1: 4D 'M'
mfm-1: 41 'A'
mfm-1: 52 'R'
mfm-1: 4B 'K'
mfm-1: 53 'S'
mfm-1: 2F '/'
mfm-1: 52 'R'
mfm-1: 45 'E'
mfm-1: 43 'C'
mfm-1: 04
mfm-1: 0F
mfm-1: 01
mfm-1: 20 ' '
mfm-1: 0F
mfm-1: 18
mfm-1: 4D 'M'
mfm-1: 45 'E'
mfm-1: 53 'S'
mfm-1: 53 'S'
mfm-1: 41 'A'
mfm-1: 47 'G'
mfm-1: 45 'E'
mfm-1: 20 ' '
mfm-1: 42 'B'
mfm-1: 55 'U'
mfm-1: 46 'F'
mfm-1: 46 'F'
mfm-1: 45 'E'
mfm-1: 52 'R'
mfm-1: 20 ' '
mfm-1: 4E 'N'
mfm-1: 4F 'O'
mfm-1: 54 'T'
mfm-1: 20 ' '
mfm-1: 56 'V'
mfm-1: 41 'A'
mfm-1: 4C 'L'
mfm-1: 49 'I'
mfm-1: 44 'D'
mfm-1: 05
mfm-1: 04
mfm-1: 05
mfm-1: 0F
mfm-1: 01
mfm-1: 20 ' '
mfm-1: 0F
mfm-1: 0E
mfm-1: 4D 'M'
mfm-1: 45 'E'
mfm-1: 53 'S'
mfm-1: 53 'S'
mfm-1: 41 'A'
mfm-1: 47 'G'
mfm-1: 45 'E'
mfm-1: 20 ' '
mfm-1: 42 'B'
mfm-1: 55 'U'
mfm-1: 46 'F'
mfm-1: 46 'F'
mfm-1: 45 'E'
mfm-1: 52 'R'
mfm-1: 05
mfm-1: 04
mfm-1: 0F
mfm-1: 01
mfm-1: 20 ' '
mfm-1: 0D
mfm-1: 08
mfm-1: 0F
mfm-1: 06
mfm-1: 58 'X'
mfm-1: 53 'S'
mfm-1: 54 'T'
mfm-1: 41 'A'
mfm-1: 54 'T'
mfm-1: 31 '1'
mfm-1: 0D
mfm-1: 18
mfm-1: 1C
mfm-1: 08
mfm-1: 04
mfm-1: 04
mfm-1: 0F
mfm-1: 01
mfm-1: 20 ' '
mfm-1: 0D
mfm-1: 08
mfm-1: 0F
mfm-1: 06
mfm-1: 58 'X'
mfm-1: 53 'S'
mfm-1: 54 'T'
mfm-1: 41 'A'
mfm-1: 54 'T'
mfm-1: 32 '2'
mfm-1: 0D
mfm-1: 18
mfm-1: 1C
mfm-1: 08
mfm-1: 04
mfm-1: 04
mfm-1: 0F
mfm-1: 01
mfm-1: 20 ' '
mfm-1: 0D
mfm-1: 28 '('
mfm-1: 0F
mfm-1: 13
mfm-1: 44 'D'
mfm-1: 45 'E'
mfm-1: 41 'A'
mfm-1: 44 'D'
mfm-1: 20 ' '
mfm-1: 54 'T'
mfm-1: 52 'R'
mfm-1: 41 'A'
mfm-1: 43 'C'
mfm-1: 4B 'K'
mfm-1: 20 ' '
mfm-1: 43 'C'
mfm-1: 48 'H'
mfm-1: 41 'A'
mfm-1: 4E 'N'
mfm-1: 4E 'N'
mfm-1: 45 'E'
mfm-1: 4C 'L'
mfm-1: 20 ' '
mfm-1: 18
mfm-1: 01
mfm-1: 0F
mfm-1: 01
mfm-1: 2E '.'
mfm-1: 04
mfm-1: 0F
mfm-1: 01
mfm-1: 20 ' '
mfm-1: 0D
mfm-1: 28 '('
mfm-1: 0F
mfm-1: 19
mfm-1: 44 'D'
mfm-1: 45 'E'
mfm-1: 41 'A'
mfm-1: 44 'D'
mfm-1: 20 ' '
mfm-1: 54 'T'
mfm-1: 52 'R'
mfm-1: 41 'A'
mfm-1: 43 'C'
mfm-1: 4B 'K'
mfm-1: 20 ' '
mfm-1: 50 'P'
mfm-1: 41 'A'
mfm-1: 52 'R'
mfm-1: 49 'I'
mfm-1: 54 'T'
mfm-1: 59 'Y'
mfm-1: 20 ' '
mfm-1: 43 'C'
mfm-1: 48 'H'
mfm-1: 41 'A'
mfm-1: 4E 'N'
mfm-1: 4E 'N'
mfm-1: 45 'E'
mfm-1: 4C 'L'
mfm-1: 04
mfm-1: 0F
mfm-1: 01
mfm-1: 20 ' '
mfm-1: 0D
mfm-1: 08
mfm-1: 0F
mfm-1: 06
mfm-1: 58 'X'
mfm-1: 53 'S'
mfm-1: 54 'T'
mfm-1: 41 'A'
mfm-1: 54 'T'
mfm-1: 33 '3'
mfm-1: 0D
mfm-1: 18
mfm-1: 1C
mfm-1: 08
mfm-1: 04
mfm-1: 04
mfm-1: 0F
mfm-1: 01
mfm-1: 20 ' '
mfm-1: 0D
mfm-1: 28 '('
mfm-1: 0F
mfm-1: 1C
mfm-1: 4D 'M'
mfm-1: 49 'I'
mfm-1: 43 'C'
mfm-1: 52 'R'
mfm-1: 4F 'O'
mfm-1: 20 ' '
mfm-1: 44 'D'
mfm-1: 49 'I'
mfm-1: 41 'A'
mfm-1: 47 'G'
mfm-1: 4E 'N'
mfm-1: 4F 'O'
mfm-1: 53 'S'
mfm-1: 54 'T'
mfm-1: 49 'I'
mfm-1: 43 'C'
mfm-1: 20 ' '
mfm-1: 45 'E'
mfm-1: 52 'R'
mfm-1: 52 'R'
mfm-1: 4F 'O'
mfm-1: 52 'R'
mfm-1: 20 ' '
mfm-1: 43 'C'
mfm-1: 4F 'O'
mfm-1: 44 'D'
mfm-1: 45 'E'
mfm-1: 20 ' '
mfm-1: 1A
mfm-1: 03
mfm-1: 03
mfm-1: 04
mfm-1: 0F
mfm-1: 01
mfm-1: 20 ' '
mfm-1: 07
mfm-1: 04
mfm-1: 00
mfm-1: 00
mfm-1: 05
mfm-1: 00
mfm-1: 00
mfm-1: 00
mfm-1: 01
mfm-1: 00
mfm-1: 00
mfm-1: 00
mfm-1: 00
mfm-1: 00
mfm-1: 00
mfm-1: 00
mfm-1: 02
mfm-1: 00
mfm-1: 00
mfm-1: 00
mfm-1: 08
mfm-1: 00
mfm-1: 00
mfm-1: 00
mfm-1: 0B
mfm-1: 00
mfm-1: 00
mfm-1: 00
mfm-1: 06
mfm-1: 00
mfm-1: 00
mfm-1: 00
mfm-1: 04
mfm-1: 00
mfm-1: 00
mfm-1: 00
mfm-1: 10
mfm-1: 00
mfm-1: 00
mfm-1: 00
mfm-1: 0E
mfm-1: 00
mfm-1: 00
mfm-1: 00
mfm-1: 0A
mfm-1: 00
mfm-1: 00
mfm-1: 00
mfm-1: 03
mfm-1: 00
mfm-1: 00
mfm-1: 00
mfm-1: 0F
mfm-1: 00
mfm-1: 00
mfm-1: 00
mfm-1: 0C
mfm-1: 00
mfm-1: 00
mfm-1: 00
mfm-1: 07
mfm-1: 00
mfm-1: 00
mfm-1: 00
mfm-1: 4D 'M'
mfm-1: 41 'A'
mfm-1: 53 'S'
mfm-1: 53 'S'
mfm-1: 42 'B'
mfm-1: 55 'U'
mfm-1: 53 'S'
mfm-1: 00
mfm-1: 30 '0'
mfm-1: 00
mfm-1: 44 'D'
mfm-1: 41 'A'
mfm-1: 49 'I'
mfm-1: 47 'G'
mfm-1: 4E 'N'
mfm-1: 4F 'O'
mfm-1: 53 'S'
mfm-1: 54 'T'
mfm-1: 49 'I'
mfm-1: 43 'C'
mfm-1: 20 ' '
mfm-1: 4D 'M'
mfm-1: 4F 'O'
mfm-1: 44 'D'
mfm-1: 45 'E'
mfm-1: 41 'A'
mfm-1: 42 'B'
mfm-1: 41 'A'
mfm-1: 2F '/'
mfm-1: 42 'B'
mfm-1: 05
mfm-1: 0F
mfm-1: 01
mfm-1: 20 ' '
mfm-1: 0D
mfm-1: 08
mfm-1: 0F
mfm-1: 06
mfm-1: 4D 'M'
mfm-1: 46 'F'
mfm-1: 20 ' '
mfm-1: 43 'C'
mfm-1: 53 'S'
mfm-1: 31 '1'
mfm-1: 0D
mfm-1: 18
mfm-1: 1C
mfm-1: 08
mfm-1: 08
mfm-1: 04
mfm-1: 0F
mfm-1: 01
mfm-1: 20 ' '
mfm-1: 0D
mfm-1: 28 '('
mfm-1: 95
mfm-1: 40 '@'
mfm-1: 6C 'l'
mfm-1: AA
mfm-1: 00
mfm-1: 00
mfm-1: 04
mfm-1: 0F
mfm-1: 01
mfm-1: 20 ' '
mfm-1: 0D
mfm-1: 28 '('
mfm-1: 95
mfm-1: 40 '@'
mfm-1: 82
mfm-1: AA
mfm-1: 00
mfm-1: 00
mfm-1: 04
mfm-1: 0F
mfm-1: 01
mfm-1: 20 ' '
mfm-1: 0D
mfm-1: 28 '('
mfm-1: 95
mfm-1: 40 '@'
mfm-1: 98
mfm-1: AA
mfm-1: 00
mfm-1: 00
mfm-1: 04
mfm-1: 0F
mfm-1: 01
mfm-1: 20 ' '
mfm-1: 0D
mfm-1: 28 '('
mfm-1: 95
mfm-1: 40 '@'
mfm-1: AE
mfm-1: AA
mfm-1: 00
mfm-1: 00
mfm-1: 04
mfm-1: 0F
mfm-1: 01
mfm-1: 20 ' '
mfm-1: 0D
mfm-1: 08
mfm-1: 0F
mfm-1: 05
mfm-1: 4D 'M'
mfm-1: 46 'F'
mfm-1: 20 ' '
mfm-1: 49 'I'
mfm-1: 53 'S'
mfm-1: 0D
mfm-1: 18
mfm-1: 1C
mfm-1: 08
mfm-1: 08
mfm-1: 04
mfm-1: 0F
mfm-1: 01
mfm-1: 20 ' '
mfm-1: 0D
mfm-1: 28 '('
mfm-1: 95
mfm-1: 40 '@'
mfm-1: B2
mfm-1: AA
mfm-1: 00
mfm-1: 00
mfm-1: 04
mfm-1: 0F
mfm-1: 01
mfm-1: 20 ' '
mfm-1: 0D
mfm-1: 28 '('
mfm-1: 95
mfm-1: 40 '@'
mfm-1: C8
mfm-1: AA
mfm-1: 00
mfm-1: 00
mfm-1: 04
mfm-1: Data Record
mfm-1: C1
mfm-1: 84
mfm-1: 72 'r'
mfm-1: 79 'y'
mfm-1: CRC OK C1847279
mfm-1: 00
</pre>
</details>
<details><summary><code>sigrok-cli -D -i hdd_mfm.sr -P mfm:report=DAM:report_qty=17 -A mfm=fields:reports</code></summary>
<pre>
mfm-1: Sync pattern 13 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=6, len=512
mfm-1: CRC OK D082
mfm-1: Sync pattern 13 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK A4882EBA
mfm-1: Sync pattern 13 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=7, len=512
mfm-1: CRC OK E3B3
mfm-1: Sync pattern 13 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK FBAA689E
mfm-1: Sync pattern 13 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=8, len=512
mfm-1: CRC OK F38D
mfm-1: Sync pattern 13 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK C1847279
mfm-1: Sync pattern 13 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=9, len=512
mfm-1: CRC OK C0BC
mfm-1: Sync pattern 13 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 58BA64F1
mfm-1: Sync pattern 13 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=10, len=512
mfm-1: CRC OK 95EF
mfm-1: Sync pattern 13 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK A42689FD
mfm-1: Sync pattern 13 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=11, len=512
mfm-1: CRC OK A6DE
mfm-1: Sync pattern 13 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK D600DA6F
mfm-1: Sync pattern 13 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=12, len=512
mfm-1: CRC OK 3F49
mfm-1: Sync pattern 13 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 1FDAFC47
mfm-1: Sync pattern 13 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=13, len=512
mfm-1: CRC OK C78
mfm-1: Sync pattern 13 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 99BCAE39
mfm-1: Sync pattern 13 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=14, len=512
mfm-1: CRC OK 592B
mfm-1: Sync pattern 13 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK D1042AD6
mfm-1: Sync pattern 13 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=15, len=512
mfm-1: CRC OK 6A1A
mfm-1: Sync pattern 13 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 3A01EE5D
mfm-1: Sync pattern 13 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=16, len=512
mfm-1: CRC OK 7957
mfm-1: Sync pattern 13 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 3D977406
mfm-1: Sync pattern 13 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=0, len=512
mfm-1: CRC OK 7A24
mfm-1: Sync pattern 13 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 7A06E528
mfm-1: Sync pattern 13 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=1, len=512
mfm-1: CRC OK 4915
mfm-1: Sync pattern 13 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 7A06E528
mfm-1: Sync pattern 13 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=2, len=512
mfm-1: CRC OK 1C46
mfm-1: Sync pattern 13 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 7A06E528
mfm-1: Sync pattern 13 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=3, len=512
mfm-1: CRC OK 2F77
mfm-1: Sync pattern 13 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 925DAC29
mfm-1: Sync pattern 13 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=4, len=512
mfm-1: CRC OK B6E0
mfm-1: Sync pattern 13 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK B82BC0C7
mfm-1: Sync pattern 13 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=5, len=512
mfm-1: CRC OK 85D1
mfm-1: Sync pattern 13 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 6CD9E3F1
mfm-1: Summary: IAM=0, IDAM=17, DAM=17, DDAM=0, CRC_OK=34, CRC_err=0, EiPW=0, CkEr=0, OoTI=12/74987
mfm-1: Sync pattern 13 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=6, len=512
mfm-1: CRC OK D082
mfm-1: Sync pattern 13 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK A4882EBA
mfm-1: Sync pattern 13 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=7, len=512
mfm-1: CRC OK E3B3
mfm-1: Sync pattern 13 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK FBAA689E
mfm-1: Sync pattern 13 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=8, len=512
mfm-1: CRC OK F38D
mfm-1: Sync pattern 13 bytes
mfm-1: Data Address Mark
</pre>
</details>
<details><summary><code>sigrok-cli -D -i fdd_fm.sr -P mfm:data_rate=125000:encoding=FM:type=FDD:data_crc_bits=16:data_crc_poly=0x1021:sect_len=256 -A mfm=fields</code></summary>
<pre>
mfm-1: Sync pattern 6 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=3, len=256
mfm-1: CRC OK A480
mfm-1: Sync pattern 5 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 9B8F
mfm-1: Sync pattern 6 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=5, len=256
mfm-1: CRC OK E26
mfm-1: Sync pattern 6 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK A730
mfm-1: Sync pattern 6 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=7, len=256
mfm-1: CRC OK 6844
mfm-1: Sync pattern 6 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK F1F3
mfm-1: Sync pattern 6 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=9, len=256
mfm-1: CRC OK 4B4B
mfm-1: Sync pattern 5 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 116E
mfm-1: Sync pattern 6 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=2, len=256
mfm-1: CRC OK 97B1
mfm-1: Sync pattern 6 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 3D09
mfm-1: Sync pattern 6 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=4, len=256
mfm-1: CRC OK 3D17
mfm-1: Sync pattern 6 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 57A
mfm-1: Sync pattern 6 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=6, len=256
mfm-1: CRC OK 5B75
mfm-1: Sync pattern 5 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK FB20
mfm-1: Sync pattern 6 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=8, len=256
mfm-1: CRC OK 787A
mfm-1: Sync pattern 6 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK EEAC
mfm-1: Sync pattern 6 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=10, len=256
mfm-1: CRC OK 1E18
mfm-1: Sync pattern 6 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK CF39
mfm-1: Sync pattern 6 bytes
mfm-1: Index Mark
mfm-1: Sync pattern 6 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=1, len=256
mfm-1: CRC OK C2E2
mfm-1: Sync pattern 6 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 219F
mfm-1: Sync pattern 6 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=3, len=256
mfm-1: CRC OK A480
mfm-1: Sync pattern 5 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 9B8F
mfm-1: Sync pattern 6 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=0, sid=0, sec=5, len=256
mfm-1: CRC OK E26
mfm-1: Sync pattern 6 bytes
mfm-1: Data Address Mark
</pre>
</details>
<details><summary><code>sigrok-cli -D -i fdd_mfm.sr -P mfm:data_rate=250000:encoding=MFM:type=FDD:data_crc_bits=16:data_crc_poly=0x1021:sect_len=256 -A mfm=fields</code></summary>
<pre>
mfm-1: Sync pattern 8 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=1, sid=0, sec=8, len=256
mfm-1: CRC OK 3620
mfm-1: Sync pattern 12 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK C4E
mfm-1: Sync pattern 8 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=1, sid=0, sec=10, len=256
mfm-1: CRC OK 5042
mfm-1: Sync pattern 12 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 15DF
mfm-1: Sync pattern 8 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=1, sid=0, sec=12, len=256
mfm-1: CRC OK FAE4
mfm-1: Sync pattern 12 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 6F4B
mfm-1: Sync pattern 8 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=1, sid=0, sec=14, len=256
mfm-1: CRC OK 9C86
mfm-1: Sync pattern 12 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 2A4F
mfm-1: Sync pattern 8 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=1, sid=0, sec=16, len=256
mfm-1: CRC OK BCFA
mfm-1: Sync pattern 12 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK D688
mfm-1: Sync pattern 8 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=1, sid=0, sec=18, len=256
mfm-1: CRC OK DA98
mfm-1: Sync pattern 11 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 8E61
mfm-1: Sync pattern 12 bytes
mfm-1: Index Mark
mfm-1: Sync pattern 8 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=1, sid=0, sec=1, len=256
mfm-1: CRC OK 8CB8
mfm-1: Sync pattern 12 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 9D
mfm-1: Sync pattern 8 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=1, sid=0, sec=3, len=256
mfm-1: CRC OK EADA
mfm-1: Sync pattern 12 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 7B83
mfm-1: Sync pattern 8 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=1, sid=0, sec=5, len=256
mfm-1: CRC OK 407C
mfm-1: Sync pattern 12 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK DE8E
mfm-1: Sync pattern 8 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=1, sid=0, sec=7, len=256
mfm-1: CRC OK 261E
mfm-1: Sync pattern 12 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 2EDE
mfm-1: Sync pattern 8 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=1, sid=0, sec=9, len=256
mfm-1: CRC OK 511
mfm-1: Sync pattern 12 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK C38D
mfm-1: Sync pattern 8 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=1, sid=0, sec=11, len=256
mfm-1: CRC OK 6373
mfm-1: Sync pattern 12 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 8E87
mfm-1: Sync pattern 8 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=1, sid=0, sec=13, len=256
mfm-1: CRC OK C9D5
mfm-1: Sync pattern 12 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 51A2
mfm-1: Sync pattern 8 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=1, sid=0, sec=15, len=256
mfm-1: CRC OK AFB7
mfm-1: Sync pattern 12 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 7A32
mfm-1: Sync pattern 8 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=1, sid=0, sec=17, len=256
mfm-1: CRC OK 8FCB
mfm-1: Sync pattern 12 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 51F
mfm-1: Sync pattern 8 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=1, sid=0, sec=2, len=256
mfm-1: CRC OK D9EB
mfm-1: Sync pattern 12 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 816E
mfm-1: Sync pattern 8 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=1, sid=0, sec=4, len=256
mfm-1: CRC OK 734D
mfm-1: Sync pattern 13 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 6EFD
mfm-1: Sync pattern 8 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=1, sid=0, sec=6, len=256
mfm-1: CRC OK 152F
mfm-1: Sync pattern 13 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 94BF
mfm-1: Sync pattern 8 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=1, sid=0, sec=8, len=256
mfm-1: CRC OK 3620
mfm-1: Sync pattern 12 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK C4E
mfm-1: Sync pattern 8 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=1, sid=0, sec=10, len=256
mfm-1: CRC OK 5042
mfm-1: Sync pattern 12 bytes
mfm-1: Data Address Mark
mfm-1: Data Record
mfm-1: CRC OK 15DF
mfm-1: Sync pattern 8 bytes
mfm-1: ID Address Mark
mfm-1: ID Record: cyl=1, sid=0, sec=12, len=256
mfm-1: CRC OK FAE4
mfm-1: Sync pattern 12 bytes
mfm-1: Data Address Mark
</pre>
</details>

### Options

`leading_edge` Leading Edge specifies edge type for signal detection.  
**Default**: `rising` **Values**: `rising`, `falling`  

`data_rate` Data Rate in bits per second (bps).  
**Default**: `5000000` **Values**: `125000`, `150000`, `250000`, `300000`, `500000`, `5000000`, `7500000`, `10000000`

`encoding` Encoding scheme.  
**Default**: `MFM` **Values**: `FM`, `MFM`, `MFM_FD`, `MFM_HD`, `RLL_SEA`, `RLL_WD`

`type` Type of disk drive.  
**Default**: `HDD` **Values**: `FDD`, `HDD`

`sect_len` Sector Length in bytes.  
**Default**: `512` **Values**: `128`, `256`, `512`, `1024`

`header_bytes` Header length in bytes.  
**Default**: `8` **Values**: `7`, `8`

`header_crc_bits` Header Field CRC size in bits.  
**Default**: `16` **Values**: `16`, `32`

`header_crc_poly` Polynomial used in Header Field CRC calculation. Default is the standard CRC-CCITT polynomial (x16 + x12 + x5 + 1).  
**Default**: `0x1021` (CRC-CCITT)

`header_crc_init` Initial value for Header Field CRC calculation.  
**Default**: `0xffffffff`

`data_crc_bits` Data Field CRC size in bits.  
**Default**: `32` **Values**: `16`, `32`, `56`

`data_crc_poly` Polynomial used in Data Field CRC calculation.  
**Default**: `0xA00805` **Values**: `0x1021` (CRC-CCITT), `0xA00805` (CRC32-CCSDS), `0x140a0445`, `0x0104c981`, `0x41044185`

`data_crc_init` Initial value for Data Field CRC calculation.  
**Default**: `0xffffffff`

`data_crc_poly_custom` Custom Data Field Polynomial, overrides `data_crc_poly` setting.  
**Default**: `` (empty string)

`time_unit` Displayed time units.  
**Default**: `ns` **Values**: `ns`, `us`, `auto`

`dsply_sn` Display Sample Numbers controls whether Windows (bit/clock) and Pulses (pul, erp) sample numbers are displayed.  
**Default**: `no` **Values**: `yes`, `no`

`dsply_pfx` Display all MFM C2 and A1 prefix bytes (encoded with special glitched clock) to help with locating damaged records.  
**Default**: `no` **Values**: `yes`, `no`

`report` Generate Report after specific Mark.  
**Default**: `no` **Values**: `no`, `IAM` (Index Mark), `IDAM` (ID Address Mark), `DAM` (Data Address Mark), `DDAM` (Deleted Data Mark)

`report_qty` Report Every X Marks specifies number of Marks between reports.  
**Default**: `9`

`decoder` Choice between New PLL based one, or Legacy with hardcoded timings.  
**Default**: `new` **Values**: `new`, `legacy`

### Annotations
Can use groupings like 'fields' or individual ones for example just 'crc'.  
`pulses` includes `pul` (pulse), `erp` (bad pulse = out-of-tolerance leading edge)  
`windows` includes `clk` (clock), `dat` (data), `erw` (extra pulse in win), `unk`  
`prefixes` includes `pfx` (A1, C1 MFM synchronization prefixes)  
`bits` includes `erb` (bad bit = encoded using glitched clock with some omitted pulses, usually in synchronization Marks), `bit`  
`bytes` includes `byt` (byte)  
`fields` includes `mrk` (mark), `rec` (record), `crc` (crc ok), `cre` (crc bad)  
`errors` includes `err` (error)  
`reports` includes `rpt` (report)  

Lets say you want to just display CRC fields, both good and bad, and nothing more:

```
sigrok-cli -D -i test\hdd_mfm_sector.sr -P mfm -A mfm=crc:cre
mfm-1: CRC OK F38D
mfm-1: CRC OK C1847279
```
 
## Installation
Copy "mfm" subfolder to one of

- C:\Program Files\sigrok\sigrok-cli\share\libsigrokdecode\decoders
- C:\Program Files (x86)\sigrok\sigrok-cli\share\libsigrokdecode\decoders
- C:\Program Files\sigrok\PulseView\share\libsigrokdecode\decoders
- C:\Program Files (x86)\sigrok\PulseView\share\libsigrokdecode\decoders
- C:\Program Files\DSView\decoders
- your linuxy/mac location

or add SIGROKDECODE_DIR environment variable.
Old user instructions are in [documentation](doc/PulseView-MFM-Decoder.wri.md)

## Resources
### Polynomials
- 0x1021 x16 + x12 + x5 + 1. Good old CRC-CCITT.
- 0xA00805 x32 + x23 + x21 + x11 + x2 + 1. Used by SMSC/SMC HDC9224 in VAXstation 2000 ("VAXSTAR" ). It just so happens to be an official CRC32 algorithm of CCSDS (Consultative Committee for Space Data Systems) used in [Proximity-1 Space Link Protocol](https://ccsds.org/Pubs/211x2b1s.pdf). Thats right folks - SPACE!!1
- 0x140a0445 X32 + X28 + X26 + X19 + X17 + X10 + X6 + X2 + 1 WD1003/WD1006/WD1100 CRC32
- 0x140a0445000101 X56 + X52 + X50 + X43 + X41 + X34 + X30 + X26 + X24 + X8 + 1 WD40C22/etc ECC56
- 0x41044185 x32 + x30 + x24 + x18 + x14 + x8 + x7 + x2 + 1 (0 init) Seagate ST11/21 header/data CRC32
- ?0x0104c981 x32 + x24 + x18 + x15 + x14 + x11 + x8 + x7 + 1 (0xd4d7ca20 init) OMTI_5510?
- OMTI_5510_Apr85.pdf: ?0x81932081 x32 + x31 + x24 + x23 + x20 + x17 + x16 + x13 + x7 + 1?
- 0x4440a051 X32 + X30 + X26 + X22 + X15 + x13 + X6 + X4 + 1 WD1003/WD1006/WD1100 CRC32 reciprocal
- 0x100004440a051 X56 + X48 + X32 + X30 + X26 + X22 + X15 + X13 + X6 + X4 + 1 WD40C22/etc 56bit ecc reciprocal
- 1983_Western_Digital_Components_Catalog.pdf WD1100-06 might have typos claiming:
  - ? 0x140a0405 X32 + X28 + X26 + X19 + X17 + X10 + X2 + 1
  - ? 0x140a0444 X32 + X28 + X26 + X19 + X17 + X10 + X6 + X2 + 0
### How to convert polynomial notations
Lets start with easy one, standard CRC-CCITT x16 + x12 + x5 + 1. This CRC-CCITT polynomial can also be written as x16 + x12 + x5 + x0 because any (non-zero number)^0 is 1. We will use that second representation.
1. Write 1 in position of every X, becomes 0b10001000000100001 (0x11021)
2. Drop most significant bit, becomes 0b1000000100001 (0x1021)
3. Thats it, you now have 0x1021 hex representation, its that easy.

Now try CRC32-CCSDS x32 + x23 + x21 + x11 + x2 + 1
1. Write 1 in position of every X, becomes 0b10000000101000000000100000000101 (0x80A00805)
2. Drop most significant bit, becomes 0b101000000000100000000101 (0xA00805)
3. 0xA00805, done!
### CRC
- https://www.sunshine2k.de/coding/javascript/crc/crc_js.html CRC calculator. Set custom CRC-16/32 with appropriately sized initial value 0xFFFF/0xFFFFFFFF. Dont forget to prepend ID/Data Mark bytes (FE, A1FE, A1A1A1FE what have you) to your data.
- https://www.ghsi.de/pages/subpages/online_crc_calculation/ https://rndtool.info/CRC-step-by-step-calculator/ two CRC calculators for converting binary Polynomial to x^ notation.
- https://reveng.sourceforge.io/ CRC RevEng: arbitrary-precision CRC calculator and algorithm finder
### Tutorials
- https://www.unige.ch/medecine/nouspikel/ti99/disks.htm#Data%20encoding fantastic resouce on FM/MFM modulation and floppy encoding schemes.
- https://map.grauw.nl/articles/low-level-disk/ As above, floppy storage primer.
- Hard Disk Geometry and Low-Level Data Structures https://www.viser.edu.rs/uploads/2018/03/Predavanje%2002c%20-%20Hard%20disk%20geometrija.pdf by School of Electrical and Computer Engineering of Applied Studies in Belgrade (VISER)
### Patents
- Mfm readout with assymetrical data window patent https://patents.google.com/patent/US3794987
- Address mark generating method and its circuit in a data memory https://patents.google.com/patent/US5062011A
### Datasheets
- Adaptec AIC-270 2,7 RLL Endec http://www.bitsavers.org/pdf/adaptec/asic/AIC-270_RLL_Encoder_Decoder.pdf
- SSI 32D5321/5322, 32D535/5351, 32D5362 2,7 RLL Endec https://bitsavers.org/pdf/maxtor/ata/1990_7080AT/data_synchronizer_appnote.pdf https://bitsavers.trailing-edge.com/components/siliconSystems/_dataBooks/1989_Silicon_Systems_Microperipheral_Products.pdf (3-23)
- WD1100-06 https://bitsavers.org/components/westernDigital/_dataBooks/1983_Western_Digital_Components_Catalog.pdf
- WD50C12 Winchester Disk Controller (MFM/RLL/NRZ) https://bitsavers.org/components/westernDigital/_dataSheets/WD50C12_Winchester_Disk_Controller_198803.pdf
### Anecdotes
- Help with HDD data encoding puzzle: RLL or ... what? (Iomega Alpha-10 / 10H / 20  proprietary RLL(1,8) 2/3 RLLC) https://forum.vcfed.org/index.php?threads/help-with-hdd-data-encoding-puzzle-rll-or-what.1250316/
### Emulation
- https://github.com/dgesswein/mfm and https://www.pdp8online.com/mfm/ BeagleBone based MFM Hard Disk Reader/Emulator
- https://github.com/Tronix286/MFM-Hard-Disk-Dumper Pi Pico MFM Hard Disk Dumper
- https://github.com/MajenkoProjects/RTmFM Pi Pico based MFM Hard Disk Emulator, early work in progress

## Authors
Original project by David C. Wiens: https://www.sardis-technologies.com/ufdr/pulseview.htm    
Updates Majenko Technologies https://github.com/MajenkoProjects/sigrok-mfm    
Rasz_pl

## Changelog
Full [Changelog](doc/changelog.md). Biggest changes from original:
* Fixed for modern PulseView and sigrok-cli
* Ported to support DSView
* Added support for hard drives, 32 bit CRC, 56 bit ECC, custom polynomials
* Extra and suppress channels optional
* Reworked report generation
* Added new PLL based Decoder
* Preliminary RLL support
