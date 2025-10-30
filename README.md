# FM/MFM/RLL decoder for Sigrok/PulseView/DSView

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

#### Sector Header close-up
![Sector Close-Up](doc/pulseview_idrecord.png)

## Available test sample files
 - [fdd_fm.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/fdd_fm.sr) 3 channels, 15000000 sample rate, FDD, FM encoding, 125000 bps, 256 Sectors, Data CRC 16bit, data poly 0x1021
 - [fdd_mfm.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/fdd_mfm.sr) 3 channels, 15000000 sample rate, FDD, MFM encoding, 250000 bps, 256 Sectors, Data CRC 16bit, data poly 0x1021
 - [hdd_mfm.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_mfm.sr) 3 channels, 100000000 sample rate, HDD, MFM encoding, 5000000 bps, 512 Sectors, Data CRC 32bit, data poly 0xA00805. VAX2000 HDD.
 - [hdd_mfm.dsl](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_mfm.dsl) as above but in DSView format
 - [hdd_mfm_sector.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/hdd_mfm_sector.sr) one sector (sec=8) from above capture. ID CRC F38D, Data CRC C1847279

## Example sigrok-cli command line usage
```sigrok-cli -D -i hdd_mfm_sector.sr -P mfm -A mfm=bytes:fields```  
```sigrok-cli -D -i hdd_mfm.sr -P mfm:report=DAM:report_qty=17 -A mfm=fields:reports```  
```sigrok-cli -D -i fdd_fm.sr -P mfm:data_rate=125000:encoding=FM:type=FDD:data_crc_bits=16:data_crc_poly=0x1021:sect_len=256 -A mfm=fields```  
```sigrok-cli -D -i fdd_mfm.sr -P mfm:data_rate=250000:encoding=MFM:type=FDD:data_crc_bits=16:data_crc_poly=0x1021:sect_len=256 -A mfm=fields```  
```sigrok-cli -D -I csv:logic_channels=3:column_formats=t,l,l,l -i YourHugeSlow.csv -P mfm:option1=value1:option2=value2 -A mfm=annotation1:annotation2```

### Options

`leading_edge` Leading Edge specifies edge type for signal detection.  
**Default**: `rising` **Values**: `rising`, `falling`  

`data_rate` Data Rate in bits per second (bps).  
**Default**: `5000000` **Values**: `125000`, `150000`, `250000`, `300000`, `500000`, `5000000`, `10000000`

`encoding` Encoding scheme.  
**Default**: `MFM` **Values**: `FM`, `MFM`

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
- 0x140a0445000101 X56 + X48 + X32 + X30 + X26 + X22 + X15 + X13 + X15 + X6 + X4 + 1 WD40C22/etc 56bit ecc reciprocal
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
* Added support for hard drives, 32 bit CRCs, custom CRC polynomials
* Extra and suppress channels optional
* Reworked report generation
* Added new PLL based Decoder
* Preliminary RLL support
