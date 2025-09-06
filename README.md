FM/MFM decoder for Sigrok/PulseView/DSView
==================

Continuation of original project: https://www.sardis-technologies.com/ufdr/pulseview.htm

###  Changes
* Fixed for modern PulseView and sigrok-cli
* Ported to support DSView
* Added support for hard drives, 32 bit CRCs, custom CRC polynomials
* Extra and suppress channels optional
* Reworked report generation

### Installation
Copy "mfm" subfolder to one of

- C:\Program Files\sigrok\sigrok-cli\share\libsigrokdecode\decoders
- C:\Program Files (x86)\sigrok\sigrok-cli\share\libsigrokdecode\decoders
- C:\Program Files\sigrok\PulseView\share\libsigrokdecode\decoders
- C:\Program Files (x86)\sigrok\PulseView\share\libsigrokdecode\decoders
- C:\Program Files\DSView\decoders
- your linuxy/mac location

or add SIGROKDECODE_DIR environment variable.

Old user instructions are in [documentation](PulseView-MFM-Decoder.wri.md) (needs upating).

### Available sample files
 - [SampleFMdataDig.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/SampleFMdataDig.sr) 3 channels, 15000000 sample rate, 125000 bps, FM encoding, FDD, 256 Sectors, Data CRC 16bit, data poly 0x1021
 - [SampleMFMdataDig.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/SampleMFMdataDig.sr) 3 channels, 15000000 sample rate, 250000 bps, MFM encoding, FDD, 256 Sectors, Data CRC 16bit, data poly 0x1021
 - [MFM_HDDdataDig.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/MFM_HDDdataDig.sr) 3 channels, 100000000 sample rate, 5000000 bps, MFM encoding, HDD, 512 Sectors, Data CRC 32bit, data poly 0xA00805. VAX2000 HDD.
 - [MFM_HDDdataDig.dsl](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/MFM_HDDdataDig.dsl) as above but in DSView format
 - [MFM_HDDdataOneSector.sr](https://github.com/raszpl/sigrok-mfm/raw/refs/heads/main/test/MFM_HDDdataOneSector.sr) one sector (sec=8) from above capture. ID CRC F38D, Data CRC C1847279

### Example sigrok-cli command line usage
- sigrok-cli -D -i MFM_HDDdataOneSector.sr -P mfm -A mfm=bytes:fields
- sigrok-cli -D -i MFM_HDDdataDig.sr -P mfm:report="DAM (Data Address Mark)":report_qty=19 -A mfm=fields:reports
- sigrok-cli -D -i SampleFMdataDig.sr -P mfm:data_rate=125000:encoding=FM:type=FDD:data_crc_bits=16:data_crc_poly=0x1021:sect_len=256 -A mfm=fields
- sigrok-cli -D -i SampleMFMdataDig.sr -P mfm:data_rate=250000:encoding=MFM:type=FDD:data_crc_bits=16:data_crc_poly=0x1021:sect_len=256 -A mfm=fields

## Explanation
- sigrok-cli -D -I csv:logic_channels=3:column_formats=t,l,l,l -i YourHugeSlow.csv -P mfm:option1=value1:option2=value2 -A mfm=annotation1:annotation2

## Options List

### 1. Leading Edge
- **ID**: `leading_edge`
- **Description**: Specifies the edge type for signal detection.
- **Default**: `rising`
- **Values**: `rising`, `falling`

### 2. Data Rate
- **ID**: `data_rate`
- **Description**: Sets the data rate in bits per second (bps).
- **Default**: `5000000`
- **Values**: `125000`, `150000`, `250000`, `300000`, `500000`, `5000000`, `10000000`

### 3. Encoding
- **ID**: `encoding`
- **Description**: Defines the encoding scheme used.
- **Default**: `MFM`
- **Values**: `FM`, `MFM`

### 4. Type
- **ID**: `type`
- **Description**: Specifies the type of disk drive.
- **Default**: `HDD`
- **Values**: `FDD`, `HDD`

### 5. Sector Length
- **ID**: `sect_len`
- **Description**: Sets Sector length in bytes.
- **Default**: `512`
- **Values**: `128`, `256`, `512`, `1024`

### 6. Header Bytes
- **ID**: `header_bytes`
- **Description**: Defines the Header length in bytes.
- **Default**: `8`
- **Values**: `7`, `8`

### 7. Header Field CRC Bits
- **ID**: `header_crc_bits`
- **Description**: Specifies Header CRC size in bits.
- **Default**: `16`
- **Values**: `16`, `32`

### 8. Header Field CRC Polynomial
- **ID**: `header_crc_poly`
- **Description**: Defines the polynomial used for the header field's CRC calculation. The default is the standard CRC-CCITT polynomial (x16 + x12 + x5 + 1).
- **Default**: `0x1021`

### 9. Data Field CRC Bits
- **ID**: `data_crc_bits`
- **Description**: Specifies Data CRC size in bits.
- **Default**: `32`
- **Values**: `16`, `32`, `56`

### 10. Data Field CRC Polynomial
- **ID**: `data_crc_poly`
- **Description**: Defines the polynomial used for the data field's CRC calculation.
- **Default**: `0xA00805`
- **Values**: `0x1021`, `0xA00805`, `0x140a0445`, `0x0104c981`, `0x41044185`

### 11. Custom Data Polynomial
- **ID**: `data_crc_poly_custom`
- **Description**: Allows specification of a custom polynomial for the data field's CRC, overriding the `data_crc_poly` setting.
- **Default**: `` (empty string)

### 12. Display All MFM Prefix Bytes
- **ID**: `dsply_pfx`
- **Description**: Determines whether all MFM prefix bytes (A1, C2) with special clock glitch are displayed.
- **Default**: `no`
- **Values**: `yes`, `no`

### 13. Display Sample Numbers
- **ID**: `dsply_sn`
- **Description**: Controls whether Pulse sample numbers are displayed.
- **Default**: `yes`
- **Values**: `yes`, `no`

### 14. Display Report
- **ID**: `report`
- **Description**: Show report after specific Mark.
- **Default**: `Disabled`
- **Values**: `Disabled`, `IAM (Index Mark)`, `IDAM (ID Address Mark)`, `DAM (Data Address Mark)`, `DDAM (Deleted Data Mark)`

### 15. Report Every X Marks
- **ID**: `report_qty`
- **Description**: How many Marks between reports.
- **Default**: `9`

Available annotations: pulses, windows, prefixes, bits, bytes, fields, errors, reports

## Polynomials
- 0x1021 x16 + x12 + x5 + 1. Good old CRC-CCITT.
- 0xA00805 x32 + x23 + x21 + x11 + x2 + 1. Used by SMSC/SMC HDC9224 in VAXstation 2000 ("VAXSTAR" ). It just so happens to be an official CRC32 algorithm of CCSDS (Consultative Committee for Space Data Systems) used in [Proximity-1 Space Link Protocol](https://ccsds.org/Pubs/211x2b1s.pdf), thats right folks - SPACE!!1
- 0x140a0445 X32 + X28 + X26 + X19 + X17 + X10 + X6 + X2 + 1 WD1003/WD1006/WD1100
- Other good candidates: ?0x41044185
- ?0x0104c981 x32 + x24 + x18 + x15 + x14 + x11 + x8 + x7 + x0  initial value 0xd4d7ca20 OMTI_5510??
- OMTI_5510_Apr85.pdf: ?0x181932081 x32 + x31 + x24 + x23 + x20 + x17 + x16 + x13 + x7 + x0
- 1983_Western_Digital_Components_Catalog.pdf WD1100-06 might have typos claiming:
  - ? 0x140a0405 X32 + X28 + X26 + X19 + X17 + X10 + X2 + 1
  - ? 0x140a0444 X32 + X28 + X26 + X19 + X17 + X10 + X6 + X2 + 0
  - ? (Reciprocal: X32 + X30 + X26 + X22 + X15 + x13 + X6 + X4 + 1)

### How to convert polynomial notations
Lets start with easy one, standard CRC-CCITT x16 + x12 + x5 + 1
1. Write 1 bits for every X, becomes 0b1000100000010000
2. Shift in from the right bit representing that lone +1, becomes	0b10001000000100001 (0x11021)
3. Drop most significant bit, becomes 0b1000000100001
4. Convert to hex, becomes 0x1021

Same CRC-CCITT polynomial might also be written as x16 + x12 + x5 + x0 because any (non-zero number)^0 = 1

Now try CRC32-CCSDS x32 + x23 + x21 + x11 + x2 + 1
1. Write 1 bits for every X, becomes 0b1000000010100000000010000000010
2. Shift in from the right bit representing that lone +1, becomes	0b10000000101000000000100000000101 (0x80A00805)
3. Drop most significant bit, becomes 0b101000000000100000000101
4. Convert to hex, becomes 0xA00805

## Resources
- https://www.sunshine2k.de/coding/javascript/crc/crc_js.html CRC calculator. Set custom CRC-16/32 with appropriately sized initial value 0xFFFF/0xFFFFFFFF. Dont forget to prepend ID/Data Mark bytes (FE, A1FE, A1A1A1FE what have you) to your data.
- https://www.unige.ch/medecine/nouspikel/ti99/disks.htm#Data%20encoding fantastic resouce on FM/MFM modulation and floppy encoding schemes.
- https://map.grauw.nl/articles/low-level-disk/ floppy storage primer
- https://reveng.sourceforge.io/ CRC RevEng: arbitrary-precision CRC calculator and algorithm finder
- https://github.com/dgesswein/mfm and https://www.pdp8online.com/mfm/ BeagleBone based MFM Hard Disk Reader/Emulator
- https://github.com/Tronix286/MFM-Hard-Disk-Dumper Pi Pico MFM Hard Disk Dumper
- https://github.com/MajenkoProjects/RTmFM Pi Pico based MFM Hard Disk Emulator, early work in progress

## Caveats
 - some data sets require modifications to the interval thresholds and
   software PLL coefficients to eliminate or reduce decoding errors;
   ideally there would be a GUI to specify these values, allow saving
   multiple sets of values, and allow selecting which set to use;  currently
   this requires manually modifying the decoder's source code, which is too
   clumsy and error-prone
