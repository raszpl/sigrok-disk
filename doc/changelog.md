### Changelog:  
2025-Oct-21  
- New decode_new using SimplePLL
- New options header_crc_init data_crc_init
- Sync pattern Field
- Configurable time_unit
- Added UI pictures and this changelog

2025-Sep-14  
- Even more Enums  
- dsply_sn option also controls Pulse annotation now  

2025-Sep-5  
- annotate_bits() no longer reports clock errors on legit Mark prefixes. (Rasz)  
- Command line usage examples. (Rasz)  

2025-Sep-4  
- Reworked report generation. (Rasz)  

2025-Sep-3  
- Stripped out stderr output and data writing code. (Majenko)  
- Extra and suppress channels optional. (Majenko)  
- Possible support for 7 byte headers (not tested). (Majenko)  
- Enums to make state machine/messages more readable. (Rasz)  
- Array CRC routine, faster than calling per byte. (Rasz)  
- Fixed DSView crashines while zooming during data load/processing. (Rasz)  
- Added DDAM (Deleted Data Address Mark). (Rasz)  

2025-Sep-2  
- Fixed DSView compatibility, still fragile: crashes when zooming in during data load/processing. (Majenko)  
- Fixed sigrok-cli comptibility, metadata() and start() call order is undetermined depending on things like input file size, cant rely on data present from one to another. (Rasz)  
- Added HDD support, 32 bit CRCs, custom CRC polynomials. All only in MFM mode. (Majenko/Rasz)
