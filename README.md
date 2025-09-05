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

Available option1=value1:option2=value2 are in options Tuple List in the Decoder class.

Available annotation1:annotation2 are in annotation_rows List of Lists in the Decoder class.

## Caveats
 - some data sets require modifications to the interval thresholds and
   software PLL coefficients to eliminate or reduce decoding errors;
   ideally there would be a GUI to specify these values, allow saving
   multiple sets of values, and allow selecting which set to use;  currently
   this requires manually modifying the decoder's source code, which is too
   clumsy and error-prone
