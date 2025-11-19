# FM/MFM/RLL decoder for Sigrok/PulseView/DSView
This [plugin](https://github.com/sigrokproject/libsigrokdecode) lets you explore and analyze data stored on floppy disks and MFM/RLL hard drives at the very low level using [Sigrok](https://sigrok.org)/[Sigrok-cli](https://sigrok.org/wiki/Sigrok-cli)([github](https://github.com/sigrokproject/sigrok-cli))/[PulseView](https://sigrok.org/wiki/PulseView)([github](https://github.com/sigrokproject/pulseview))/[DSView](https://github.com/DreamSourceLab/DSView) Logic Analyzer software.  

Start by loading one of available [test sample files](#available-test-sample-files) or capture you own data using Logic Analyzer hardware. Aim for 20x oversampling for best results.

- Floppy drive requires at least ~12MHz sampling rate meaning something like ~$60 Hantek 6022 or $5 CY7C68013A https://sigrok.org/wiki/Lcsoft_Mini_Board dev board (aliexpress/ebay/amazon) as thats pretty much whats inside the Hantek/original Saleae.  
- Hard drives operate at 5-15Mbit flux rate and demand sampling rate of at least 200MHz. Commercial LAs start around $200, saner options are 200Ms/s Pico based [MFM-Hard-Disk-Dumper](https://github.com/Tronix286/MFM-Hard-Disk-Dumper) by Tronix286 or not so greatly named but outstandingly capable Pico/Pico2 based 400Ms/s [LogicAnalyzer](https://github.com/gusmanb/logicanalyzer). Both of those Open Source hardware LA solutions are vastly cheaper while delivering great results.

<hr>

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
  - [Converting polynomial notations](#converting-polynomial-notations)
  - [CRC](#crc)
  - [Tutorials](#tutorials)
  - [Patents](#patents)
  - [Datasheets](#datasheets)
  - [Miscellaneous](#miscellaneous)
  - [Emulation](#emulation)
- [Authors](#authors)
- [Changelog](#changelog)
- [Todo](#todo)
</details>

<hr>

## Screenshots
#### Full Track view
![Full Track Decode](doc/pulseview_track.png)  
Typical track on MFM encoded hard drive.

#### Sector Header close-up
![Sector Close-Up](doc/pulseview_idrecord.png)  
This is a spare/unused sector created at the end of every track on MFM drive by Seagate ST21 controller. Notice the weird Sector number 254 and absence of GAP3 between end of Header and start of Sync pattern. Without GAP3 writing to this sector would causes corruption giving us a hint that this special Sector is not meant to ever be used. Every MFM/RLL drive I looked at so far wasted precious space either leaving enought unused disk surface for one more sector per track of having one dummy sector at the end like this one. That translates to never using 6% of MFM and 4% of RLL disk you paid for, about 2.5MB on typical 40MB MFM drive. I know of only DEC RQDX1/2 controllers using all 18 sectors, but DECs next [RQDX3](https://gunkies.org/wiki/RQDX3_MFM_Disk_%26_Floppy_QBUS_Controller#Version_details) controller went back to 17. For comparison 15 years later transition to 4K Sectors (88->97% efficiency gain) was the result of HDD manufacturers fighting for every scrap of capacity.

<hr>

## Available test sample files
 - [fdd_fm.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/fdd_fm.sr) 15MHz sample rate. FDD, 5:1 interleave. 125000 bps, FM encoding, 256 Byte Sectors, Data CRC 16bit, Data poly 0x1021

 - [fdd_mfm.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/fdd_mfm.sr) 15MHz sample rate. FDD, 5:1 interleave. Cylinder 1, Head 0. 250000 bps, MFM encoding, 256 Byte Sectors, Data CRC 16bit, Data poly 0x1021

 - [hdd_mfm_RQDX3.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_mfm_RQDX3.sr) 100MHz sample rate. 5000000 bps, MFM encoding, 512 Byte Sectors, Data CRC 32bit, Data poly 0xA00805.<br>DEC RD54 (re-branded Maxtor XT-2190) containing VMS. Paired to build-in SMC HDC9224 (RQDX3 compatible?) disk controller in [VAXstation2000](https://gunkies.org/wiki/KA410_MicroVAX_2000/VAXstation_2000_System_Module). Note: Drive had rather [spectacularly blown Index pulse generator captured on video.](https://www.youtube.com/watch?v=rvOJJcxFEO4&t=2699)
 - [hdd_mfm_RQDX3.dsl](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_mfm_RQDX3.dsl) as above but in DSView format
 - [hdd_mfm_RQDX3_sector.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_mfm_RQDX3_sector.sr) one sector (sec=8) from above capture. ID CRC F38D, Data CRC C1847279
 - [hdd_mfm_AMS1100M4.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_mfm_AMS1100M4.sr) 200MHz sample rate. Cylinder 622, Head 1. Bad Sector 9. 5000000 bps, MFM encoding, Header size 3, data poly 0x140a0445.<br>Seagate ST-251 formatted using American Multisource (AMS) 1100M4 (AIC-6060/CL-SH260, SSI 32D534)
 - [hdd_mfm_EV346.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_mfm_EV346.sr) 200MHz sample rate. Cylinder 819, Head 2. 5000000 bps, MFM encoding, Header size 3, Data poly 0x140a0445.<br>Seagate ST-251 formatted using Everex EV-346 (CL-SH260, SSI 32D534)
 - [hdd_mfm_WD1003V-MM2.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_mfm_WD1003V-MM2.sr) 200MHz sample rate. 5000000 bps, MFM encoding,  Header size 3, data poly 0x140a0445.<br>Seagate ST-278R formatted using WD1003V-MM2 (WD42C22A, WD10C22B)
 - [hdd_mfm_WD1003V-MM2_int.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_mfm_WD1003V-MM2_int.sr) 200MHz sample rate. 2:1 interleave. 5000000 bps, MFM encoding, Header size 3, data poly 0x140a0445.<br>Seagate ST-251 formatted using WD1003V-MM2 (WD42C22A, WD10C22B)
 - [hdd_mfm_NDC5525.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_mfm_NDC5525.sr) 200MHz sample rate. 2:1 interleave. 5000000 bps, MFM encoding, Header size 3, data poly 0x140a0445.<br>Seagate ST-251 formatted using NCL America Computer NDC5525 (NEC Z80, various NCL chips)
 - [hdd_mfm_OMTI8240.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_mfm_OMTI8240.sr) 200MHz sample rate. Track 4919: Cylinder 819, Head 5. 5000000 bps, MFM encoding, Header format unknown, Header CRC 32bit, other Header CRC parameters unknownm, Data poly 0x0104c981, Data CRC init 0xd4d7ca20.<br>Seagate ST-251 on Scientific Micro Systems Inc. OMTI 8240 (Z8 micro, OMTI 20516 aka OMTI 5098, OMTI 20507 aka 5070)
 - [hdd_mfm_ST21M.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_mfm_ST21M.sr) 200MHz sample rate. Track 6, Cylinder 1, Head 0. 5000000 bps, MFM encoding, Header format semi unknown, Header CRC 32bit, Header poly 0x41044185, Header CRC init 0, Data poly 0x41044185, Data CRC init 0.<br>Seagate ST-251 on Seagate ST21M (custom Seagate VLSI)
 - [hdd_mfm_ST21M_2.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_mfm_ST21M_2.sr) 200MHz sample rate. Track 6, Cylinder 1, Head 0. 5000000 bps, MFM encoding, Header format semi unknown, Header CRC 32bit, Header poly 0x41044185, Header CRC init 0, Data poly 0x41044185, Data CRC init 0.<br>Seagate ST-278R on Seagate ST21M (custom Seagate VLSI)
 - [hdd_mfm_ST21M_service2.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_mfm_ST21M_service2.sr) 200MHz sample rate. Cylinder 0, Head 0. 5000000 bps, MFM encoding, Header format unknown, Header CRC 32bit, other CRC parameters unknown.<br>Seagate ST-278R on Seagate ST21M (custom Seagate/Cirrus Logic controller). Tracks 0-5 are occupied by this service area.

 - [hdd_mfm_ST21M_service.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_mfm_ST21M_service.sr) 200MHz sample rate. 2:1 interleave. Cylinder 0, Head 0. 7500000 bps, RLL_Adaptec encoding, Header format semi unknown, First track Header CRC init 0, Data ECC 48bit, other CRC parameters unknown.<br>Seagate ST-251 on Seagate ST21M (custom Seagate VLSI). Tracks 0-5 are occupied by this RLL_Adaptec encoded service area despite running in MFM mode.
 - [hdd_rll_ACB4070.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_rll_ACB4070.sr) 200MHz sample rate. 2:1 interleave. 7500000 bps, RLL_Adaptec encoding, Header format unknown, Header CRC 32bit, Header poly 0x41044185, Header CRC init 0, Data poly 0x41044185, Data CRC init 0. Requires more aggressive pll_kp=1 due to wobly timings.<br>Seagate ST251 on Adaptec ACB-4070 RLL to SCSI bridge (AIC-300F, AIC-010F) from [Mattis Linds ABC1600 containing DNIX 5.3 (UNIX SVR3)](https://forum.vcfed.org/index.php?threads/rll-drive-sampling-project.1209575/#post-1209655)
 - [hdd_rll_ACB2370A.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_rll_ACB2370A.sr) 200MHz sample rate. 7500000 bps, RLL_Adaptec encoding, Header format semi unknown, Header CRC init 0, Data ECC 56bit, other CRC parameters unknown.<br>Seagate ST251 on Adaptec ACB-2370A (AIC-610F, AIC-280L, AIC-270L, AIC-6225)
 - [hdd_rll_ACB2372.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_rll_ACB2372.sr) 200MHz sample rate. 7500000 bps, RLL_Adaptec encoding, Header format semi unknown, Header CRC init 0, Data ECC 56bit, other CRC parameters unknown.<br>Seagate ST-278R on Adaptec ACB-2372 (AIC-610F, AIC-280L, AIC-270L, AIC-6225)
 - [hdd_rll_ST21R.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_rll_ST21R.sr) 200MHz sample rate. 7500000 bps, RLL_Sea encoding, Header format semi unknown, Header CRC 32bit, Header poly 0x41044185, Header CRC init 0, Data poly 0x41044185, Data CRC init 0.<br>Seagate ST-278R on Seagate ST21R (custom Seagate VLSI)
 - [hdd_rll_WD1003V-SR1.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_rll_WD1003V-SR1.sr) 200MHz sample rate. 7500000 bps, RLL_WD encoding, Header size 3, Data ECC 56bit, Data poly 0x140a0445000101.<br>Seagate ST-278R WD1003V-SR1 (WD42C22A, WD10C22B)
 - [hdd_rll_WD1003V-SR1int.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_rll_WD1003V-SR1int.sr) 200MHz sample rate. 2:1 interleave. 7500000 bps, RLL_WD encoding, Header size 3, Data ECC 56bit, Data poly 0x140a0445000101.<br>Seagate ST-251 WD1003V-SR1 (WD42C22A, WD10C22B)
 - [hdd_rll_WD1006V-SR2.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_rll_WD1006V-SR2.sr) 200MHz sample rate. 7500000 bps, RLL_WD encoding, Header size 3, Data ECC 56bit, Data poly 0x140a0445000101.<br>Seagate ST-251 WD1006V-SR2 (WD42C22A, WD10C22B)
 - [hdd_rll_OMTI8247.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_rll_OMTI8247.sr) 200MHz sample rate. 7500000 bps, RLL_OMTI encoding, Header format unknown, Header poly unknown, Data ECC 48bit, Data poly unknown.<br>Seagate ST-251 on Scientific Micro Systems Inc. OMTI 8247 (Z8 micro, OMTI 20516 aka OMTI 5098, OMTI 20527 aka 5027)
 - [hdd_rll_DTC7287.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_rll_DTC7287.sr)
 - [hdd_rll_DTC7287_track0](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_rll_DTC7287_track0.sr)
 - [hdd_rll_DTC7287_track1](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_rll_DTC7287_track1.sr)
 - [hdd_rll_DTC7287_track4919](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_rll_DTC7287_track4919.sr)<br>DTC7287 captures 200MHz sample rate. 7500000 bps, Broken unknown RLL_DTC7287_unknown encoding, Header size 3?<br>ST-251 on [Data Technology Corporation DTC-7287](https://www.vogonswiki.com/index.php/DTC_7287) Format looks very ESDI like. Help deciphering appreciated.

Huge thanks to Al Kossow for providing majority of the [samples hosted by bitsavers](http://bitsavers.org/projects/hd_samples).
<hr>

## Example sigrok-cli command line usage
<details><summary><code>sigrok-cli -D -i hdd_mfm_RQDX3_sector.sr -P mfm -A mfm=bytes:fields</code></summary>
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
<details><summary><code>sigrok-cli -D -i hdd_mfm_RQDX3.sr -P mfm:report=DAM:report_qty=17 -A mfm=fields:reports</code></summary>
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
<details><summary><code>sigrok-cli -D -i fdd_fm.sr -P mfm:data_rate=125000:encoding=FM:data_crc_bits=16:data_crc_poly=0x1021:sector_size=256 -A mfm=fields</code></summary>
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
<details><summary><code>sigrok-cli -D -i fdd_mfm.sr -P mfm:data_rate=250000:encoding=MFM:data_crc_bits=16:data_crc_poly=0x1021:sector_size=256 -A mfm=fields</code></summary>
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
<details><summary><code>Dirty cut|tr hack to extrack strings:
sigrok-cli.exe -D -i hdd_mfm_RQDX3_sector.sr -P mfm -A mfm=bytes | cut -c 12 | tr -d '\n'</code></summary>
<pre>
N = @. BYTES SKIP/SPACE COUNT (SKIP/SPACE @p. TAPE MARKS/REC
MESSAGE BUFFER NOT VALID MESSAGE BUFFER XSTAT1 XSTAT2 (DEAD TRACK CHANNEL
. (DEAD TRACK PARITY CHANNEL XSTAT3 (MICRO DIAGNOSTIC ERROR CODE
MASSBUS0DAIGNOSTIC MODEABA/B MF CS1 (@l (@ (@ (@ MF IS (@ (@ry
</pre>
</details>
<code>sigrok-cli -D -I csv:logic_channels=3:column_formats=t,l,l,l -i YourHugeSlow.csv -P mfm:option1=value1:option2=value2 -A mfm=annotation1:annotation2</code>

### Options

`leading_edge` Leading Edge specifies edge type for signal detection.  
**Default**: `rising` **Values**: `rising`, `falling`  

`data_rate` Data Rate in bits per second (bps).  
**Default**: `5000000` **Values**: `125000`, `150000`, `250000`, `300000`, `500000`, `5000000`, `7500000`, `10000000`

`encoding` Encoding schemes available. 'custom' lets you build own decoder interactively in the GUI fully controlling its behavior.  
**Default**: `MFM` **Values**: `FM`, `MFM`, `RLL_Sea`, `RLL_Adaptec`, `RLL_WD`, `RLL_OMTI`, `custom`

`header_size` Header payload length in bytes.  
**Default**: `4` **Values**: `3`, `4`

`sector_size` Sector payload length in bytes.  
**Default**: `512` **Values**: `128`, `256`, `512`, `1024`

`header_crc_bits` Header field CRC size in bits.  
**Default**: `16` **Values**: `16`, `32`

`header_crc_poly` Polynomial used in Header field CRC calculation. Default is the standard CRC-CCITT polynomial (x16 + x12 + x5 + 1).  
**Default**: `0x1021` (CRC-CCITT)

`header_crc_init` Initial value for Header field CRC calculation.  
**Default**: `0xffffffff`

`data_crc_bits` Data field CRC size in bits.  
**Default**: `32` **Values**: `16`, `32`, `48`, `56`

`data_crc_poly` Polynomial used in Data field CRC calculation.  
**Default**: `0xA00805` **Values**: `0x1021` (CRC-CCITT), `0xA00805` (CRC32-CCSDS), `0x140a0445`, `0x0104c981`, `0x41044185`, `0x140a0445000101`

`data_crc_init` Initial value for Data field CRC calculation.  
**Default**: `0xffffffffffffff`

`data_crc_poly_custom` Custom Data field Polynomial, overrides `data_crc_poly` setting.  
**Default**: `` (empty string)

`time_unit` Select Pulse time units or number of half-bit windows.
**Default**: `ns` **Values**: `ns`, `us`, `auto`, `window`

`dsply_sn` Display additonal sample numbers for Pulses (pul, erp) and Windows (bit/clock).  
**Default**: `no` **Values**: `yes`, `no`

`report` Display report after encountering specified field type.  
**Default**: `no` **Values**: `no`, `IAM` (Index Mark), `IDAM` (ID Address Mark), `DAM` (Data Address Mark), `DDAM` (Deleted Data Address Mark)

`report_qty` Number of Marks (specified above) between reports. This is a workaround for lack of sigrok/pulseview capability to signal end_of_capture.  
**Default**: `9` **Example**: `9` for floppies, `17` for MFM hdd, `26` for RLL drives

`decoder` Choice between PI Loop Filter based PLL, or 'legacy' with hardcoded immediate andustments.  
**Default**: `PLL` **Values**: `PLL`, `legacy`

`pll_sync_tolerance` PLL: Initial tolerance when catching synchronization sequence.  
**Default**: `25%` **Values**: `15%`, `20%`, `25%`, `33%`, `50%`

`pll_kp` PLL: PI Filter proportinal constant (Kp).  
**Default**: `0.5`

`pll_ki` PLL: PI Filter integral constant (Ki).  
**Default**: `0.0005`

`dsply_pfx` Legacy decoder: Display all MFM C2 and A1 prefix bytes (encoded with special glitched clock) to help with locating damaged records.  
**Default**: `no` **Values**: `yes`, `no`

`encoding=custom` activates custom_encoder_ options.

`custom_encoder_limits` Coding.  
**Default**: `RLL` **Values**: `FM`, `MFM`, `RLL`

`custom_encoder_codemap` Code translation map.  
**Default**: `IBM` **Values**: `FM/MFM`, `IBM`, `WD`

`custom_encoder_sync_pattern` Width of pulses used in a repeating sequence (called PLO sync field or preamble) to train PLL and aquire initial lock.  
**Default**: `4` **Values**: `2`, `3`, `4`

*Warning!* All custom_encoder_ options below must obey stupid rules when used from command line. sigrok-cli command line input doesnt support "" escaped strings nor commas. We have to resort to custom escaping with `,` becoming `-` and `_` used to separate lists:  
&nbsp;&nbsp;&nbsp;&nbsp;for `[8, 3, 5], [5, 8, 3, 5], [7, 8, 3, 5]` pass `8-3-5_5-8-3-5_7-8-3-5`  
&nbsp;&nbsp;&nbsp;&nbsp;for `[8, 3, 5]` pass `8-3-5`  
&nbsp;&nbsp;&nbsp;&nbsp;for `11, 12` pass `11-12`  
&nbsp;&nbsp;&nbsp;&nbsp;for `0x1E, 0x5E, 0xDE` pass `0x1E-0x5E-0xDE` or `30-95-222`  

PulseView/DSView GUI is much more flexible and allows omitting outer brackets, all of those are allowed:  
&nbsp;&nbsp;&nbsp;&nbsp;`8-3-5`  
&nbsp;&nbsp;&nbsp;&nbsp;`8,3,5`  
&nbsp;&nbsp;&nbsp;&nbsp;`[8, 3, 5]`  
&nbsp;&nbsp;&nbsp;&nbsp;`[[8, 3, 5]]`  
&nbsp;&nbsp;&nbsp;&nbsp;`[8, 3, 5], [5, 8, 3, 5]`  
&nbsp;&nbsp;&nbsp;&nbsp;`[[8, 3, 5], [5, 8, 3, 5]]`  
&nbsp;&nbsp;&nbsp;&nbsp;`8-3-5_5-8-3-5_7-8-3-5`  

`custom_encoder_sync_seqs` Special (often invalid on purpose) sequences of pulses used to distinguish Synchronization Marks.  
**Default**: `` (empty string) **Example**: `[[8, 3, 5], [5, 8, 3, 5], [7, 8, 3, 5]]` used by RLL_WD

`custom_encoder_shift_index` Every sync_sequences entry has its own offset defining number of valid halfbit windows already shifted in (minus last entry because PLLstate.decoding adds self.halfbit_cells) at the moment of matched Sync Sequence. Define one common value or provide list of values for every sync_sequences entry.  
**Default**: `` (empty string) **Example**: `11` or `11, 11` for RLL_OMTI

All custom_encoder_ _mark options below support * wildcard, useful when debugging new format and unsure of proper values. For example setting custom_encoder_nop_mark=* will start decoding bytes as soon as custom_encoder_sync_seqs is matched. After that you can manipulate custom_encoder_shift_index to arrive at proper bit alignment. Greatly simplifies adding new encoding formats.

`custom_encoder_IDData_mark` IDData_mark is usually 0xA1 for MFM FDD and HDD.   
**Default**: `` (empty string) **Example**: `0xA1`

`custom_encoder_ID_mark` ID_mark makes decoder skip straight to decoding Header.  
**Default**: `` (empty string) **Example**: `0xFE` used by original FM floppies

`custom_encoder_Data_mark` Data_mark makes decoder skip straight to decoding Data.  
**Default**: `` (empty string) **Example**: `0xFB` used by original FM floppies

`custom_encoder_ID_prefix_mark` ID_prefix_mark is a Header Mark to be followed by IDData_mark.  
**Default**: `` (empty string) **Example**: `0x1E` weird arrangement used by RLL_Sea

`custom_encoder_nop_mark` nop_mark is an inert Mark.  
**Default**: `` (empty string) **Example**: `0x1E, 0x5E, 0xDE` for RLL_Adaptec

### Annotations
Can use groupings like 'fields' or individual ones for example just 'crc'.  
`pulses` includes `pul` (pulse), `erp` (bad pulse = out-of-tolerance leading edge)  
`windows` includes `clk` (clock), `dat` (data), `erw` (extra pulse in win), `unk`  
`prefixes` includes `pfx` (A1, C1 MFM synchronization prefixes)  
`bits` includes `erb` (bad bit = encoded using glitched clock with some omitted pulses, usually in synchronization Marks), `bit`  
`bytes` includes `byt` (byte)  
`fields` includes `syn` (sync), `mrk` (mark), `rec` (record), `crc` (crc ok), `cre` (crc bad)  
`errors` includes `err` (error)  
`reports` includes `rpt` (report)  

Lets say you want to just display CRC fields, both good and bad, and nothing more:

```
sigrok-cli -D -i test\hdd_mfm_RQDX3_sector.sr -P mfm:data_crc_poly_custom=0xbad -A mfm=crc:cre
mfm-1: CRC OK F38D
mfm-1: CRC error 115E0390
```

<hr>

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

<hr>

## Resources
### Polynomials
- 0x1021 x16 + x12 + x5 + 1. Good old CRC-CCITT.
- 0xA00805 x32 + x23 + x21 + x11 + x2 + 1. Used by SMSC/SMC HDC9224 in VAXstation 2000 ("VAXSTAR" ). It just so happens to be an official CRC32 algorithm of CCSDS (Consultative Committee for Space Data Systems) used in [Proximity-1 Space Link Protocol](https://ccsds.org/Pubs/211x2b1s.pdf). Thats right - [the one place that hasn't been corrupted by capitalism: SPACE!](https://www.youtube.com/watch?v=g1Sq1Nr58hM)
- 0x140a0445 X32 + X28 + X26 + X19 + X17 + X10 + X6 + X2 + 1 WD1003/WD1006/WD1100 CRC32
- 0x41044185 x32 + x30 + x24 + x18 + x14 + x8 + x7 + x2 + 1 (0 init) Seagate ST11/21 header/data CRC32
- 0x0104c981 x32 + x24 + x18 + x15 + x14 + x11 + x8 + x7 + 1 (0xd4d7ca20 init) OMTI 8240/?5510?
- 0x140a0445000101 X56 + X52 + X50 + X43 + X41 + X34 + X30 + X26 + X24 + X8 + 1 WD40C22/etc ECC56
- 0x4440a051 X32 + X30 + X26 + X22 + X15 + x13 + X6 + X4 + 1 WD1003/WD1006/WD1100 CRC32 reciprocal
- 0x100004440a051 X56 + X48 + X32 + X30 + X26 + X22 + X15 + X13 + X6 + X4 + 1 WD40C22/etc 56bit ecc reciprocal
- OMTI_5510_Apr85.pdf: ?0x40c99041 x32 + x31 + x24 + x23 + x20 + x17 + x16 + x13 + x7 + 1?
- 1983_Western_Digital_Components_Catalog.pdf WD1100-06 most likely typos claiming:
  - ? 0x140a0405 X32 + X28 + X26 + X19 + X17 + X10 + X2 + 1
  - ? 0x140a0444 X32 + X28 + X26 + X19 + X17 + X10 + X6 + X2 + 0
### Converting polynomial notations
Lets start with easy one, standard CRC-CCITT x16 + x12 + x5 + 1. This CRC-CCITT polynomial can also be written as x16 + x12 + x5 + x0 because any (non-zero number)^0 is 1. We will use that second representation.
1. Write 1 in position of every X, becomes 0b10001000000100001 (0x11021)
2. Drop most significant bit, becomes 0b1000000100001 (0x1021)
3. Thats it, you now have 0x1021 hex representation, its that easy.

Now try CRC32-CCSDS x32 + x23 + x21 + x11 + x2 + 1
1. Write 1 in position of every X, becomes 0b10000000101000000000100000000101 (0x80A00805)
2. Drop most significant bit, becomes 0b101000000000100000000101 (0xA00805)
3. 0xA00805, done!
### CRC
- [CRC Calculator (Javascript)](https://www.sunshine2k.de/coding/javascript/crc/crc_js.html) Set custom CRC-16/32 with appropriately sized initial value 0xFFFF/0xFFFFFFFF. Dont forget to prepend ID/Data Mark bytes (FE, A1FE, A1A1A1FE what have you) to your data.
- [Online CRC Calculation](https://www.ghsi.de/pages/subpages/online_crc_calculation/) [Cyclic Redundancy Check (CRC) Step-by-Step Calculator](https://rndtool.info/CRC-step-by-step-calculator/) Useful for converting binary Polynomial to x^ notation.
- [CRC RevEng: arbitrary-precision CRC calculator and algorithm finder](https://reveng.sourceforge.io/)
### Tutorials
- Thierry Nouspikel [The TI floppy disk controller card]( https://www.unige.ch/medecine/nouspikel/ti99/disks.htm#Data%20encoding) Award winning resouce on FM/MFM modulation and floppy encoding schemes.
- Wouter Vermaelen [Low-level disk storage](https://map.grauw.nl/articles/low-level-disk/)
- Michael Haardt, Alain Knaff, David C. Niemi [The floppy user guide](https://www.grimware.org/lib/exe/fetch.php/documentations/hardware/manuals/floppy.user.guide.pdf)
- [Hard Disk Geometry and Low-Level Data Structures](https://www.viser.edu.rs/uploads/2018/03/Predavanje%2002c%20-%20Hard%20disk%20geometrija.pdf) by School of Electrical and Computer Engineering of Applied Studies in Belgrade (VISER)
- Artem Rubtsov (creator of HDDScan) [HDD from Inside: Hard Drive Main Parts](https://hddscan.com/doc/HDD_from_inside.html)
- Artem Rubtsov (creator of HDDScan) [HDD inside: Tracks and Zones](https://hddscan.com/doc/HDD_Tracks_and_Zones.html)
- [Bit Banging a 3.5" Floppy Drive](https://floppy.cafe/)
### Patents
- [US3794987 Mfm readout with assymetrical data window](https://patents.google.com/patent/US3794987)
- [US5062011A Address mark generating method and its circuit in a data memory](https://patents.google.com/patent/US5062011A)
### Datasheets
- [SMC HDC9224 Universal Disk Controller (MFM)](https://theretroweb.com/chip/documentation/smscs01132-1-678a7bb556eae279963995.pdf)
- [WD1100-06 (MFM)](https://bitsavers.org/components/westernDigital/_dataBooks/1983_Western_Digital_Components_Catalog.pdf)
- [WD10C22B Self-Adjusting Data Separator (MFM/RLL)](https://bitsavers.org/components/westernDigital/_dataSheets/WD10C22B_Self-Adjusting_Data_Separator_1988.pdf)
- [WD42C22A Winchester Disk Subsystem Controller (MFM/RLL/NRZ)](https://www.ardent-tool.com/datasheets/WD_WD42C22A.pdf)
- [WD50C12 Winchester Disk Controller (MFM/RLL/NRZ)](https://bitsavers.org/components/westernDigital/_dataSheets/WD50C12_Winchester_Disk_Controller_198803.pdf)
- [Adaptec AIC-270 2,7 RLL Endec](http://www.bitsavers.org/pdf/adaptec/asic/AIC-270_RLL_Encoder_Decoder.pdf)
- AIC-6225 33-Mbit/second (1,7 RLL) Data Separator. Datasheet missing.
- [Adaptec AIC-6060 Storage Controller](http://www.bitsavers.org/pdf/adaptec/asic/AIC-6060_brochure.pdf) pin and function compatible with Cirrus Logic CL-SH260
- [Cirrus Logic CL-SH260](https://bitsavers.org/components/cirrusLogic/_dataSheets/CL-SH260_Enhanced_PC_XT-AT_Disk_Controller_Jan1991.pdf)
- [SSI 32D5321/5322, 32D535/5351, 32D5362 2,7 RLL Endec](https://bitsavers.org/pdf/maxtor/ata/1990_7080AT/data_synchronizer_appnote.pdf)
- [SSI 32D534 Data Synchronizer/MFM ENDEC in 1989_Silicon_Systems_Microperipheral_Products](https://bitsavers.trailing-edge.com/components/siliconSystems/_dataBooks/1989_Silicon_Systems_Microperipheral_Products.pdf) (page 271)
- [National Semiconductor DP8463B 2,7 RLL Endec](https://ftpmirror.your.org/pub/misc/bitsavers/components/national/_dataBooks/1989_National_Mass_Storage_Handbook/1989_Mass_Storage_Handbook_02.pdf) (2-85)
- [OMTI 5070 MFM Data Seperator](http://www.bitsavers.org/pdf/sms/asic/OMTI_5070_Encode_Decode_May84.pdf)
- [OMTI 5027C 2,7 RLL Endec](https://theretroweb.com/chip/documentation/omti-5027c-rll-vco-encode-decode-dec86-68d1200a21030170193849.pdf)
- [OMTI 7xX0/3500](http://www.bitsavers.org/pdf/sms/omti_7x00/3001546_7x00_3500_Ref_Feb88.pdf)
### Controllers
- [WD1003V-MM1/2 WD1006V-MM1/2](https://theretroweb.com/expansioncard/documentation/wd1003v-mmx-mfm-disk-controller-1989-675a13c5c5cfd722800431-688faa8bf369c709553426.pdf)
- [WD1003V-SR1/2 WD1006V-SR1/2](https://www.minuszerodegrees.net/manuals/Western%20Digital/WD1006V-SR1%20and%20SR2%20-%20Users%20Guide.pdf)

WD1003V versions have 2KB buffer, WD1006V 8KB. Afaik MM1/2 and SM1/2 is same base hardware with minor component configuration differences (crystals). SR1/2 adds Option ROM with shadowing SRAM and most likely different microcontroller firmware for RLL support. The only reason those MM/SM models didnt support RLL was WD playing market segmentation games.
### Miscellaneous
- Herb Johnson ["Classic" hard drives: controllers, cabinets, disks, docs & hints](https://www.retrotechnology.com/herbs_stuff/s_hard.html)
- [Help with HDD data encoding puzzle: RLL or ... what? (Iomega Alpha-10 / 10H / 20  proprietary RLL(1,8) 2/3 RLLC)](https://forum.vcfed.org/index.php?threads/help-with-hdd-data-encoding-puzzle-rll-or-what.1250316/)
### Emulation
- David Gesswein [BeagleBone based MFM Hard Disk Reader/Emulator](https://www.pdp8online.com/mfm/)/[github](https://github.com/dgesswein/mfm)
- Tronix286 [Pi Pico MFM Hard Disk Dumper](https://github.com/Tronix286/MFM-Hard-Disk-Dumper)
- Matt Jenkins [Pi Pico based MFM Hard Disk Emulator](https://github.com/MajenkoProjects/RTmFM) early work in progress

<hr>

## Authors
Original project by David C. Wiens: https://www.sardis-technologies.com/ufdr/pulseview.htm  
Matt Jenkins [Majenko Technologies](https://github.com/MajenkoProjects/sigrok-mfm) (3byte headers, hard drive support, optional channels, DSView support)  
Rasz_pl

<hr>

## Changelog
Full [Changelog](doc/changelog.md). Biggest changes from original:
* Modern PulseView and sigrok-cli fixes
* DSView support
* Hard drives, 32 bit CRC, 48/56 bit ECC, custom polynomials
* Extra and suppress channels optional
* Reworked report generation
* New PI Loop Filter based PLL Decoder
* Flexible custom encoder mode with live GUI control
* RLL support

<hr>

## Todo
- [x] RLL decoding
- [x] more Test samples
- [ ] annotate reason of PLL reset
- [ ] dont reset PLL on data decode error, try to recover with ECC
- [ ] Binary Decoder Output
- [ ] more `auto` modes
    - [ ] `auto` data_rate detection
    - [ ] `auto` sect_len mode using Sector length value from the Header
    - [ ] `auto` header_bytes detection
    - [ ] `auto` CRC modes
		- [ ] `auto` header_crc_bits detection
		- [ ] `auto` header_crc_poly/header_crc_init detection
		- [ ] `auto` data_crc_bits detection
		- [ ] `auto` data_crc_poly/data_crc_init detection
    - [ ] `auto` encoding detection - this is a BIG one
- [ ] Rename Errors annotation field to more general Status
- [ ] Figure out crazy RLL_DTC7287 format
- [ ] GCR
- [ ] ESDI?
- [ ] SMD??? :-)
