**MFM Decoder for sigrok PulseView**

**Introduction**

The purpose of the **mfm** module is to decode and display the raw data captured by a logic analyzer while reading a floppy disk, in order to trouble-shoot the data. It can handle data from virtually any floppy disk, as long as the data is encoded as MFM or FM.

Typically when reading old disks, some sectors will have read errors. Floppy disk controller chips usually just report an error, but don't let you see what portions of the data are good or have problems, especially if the problem is in the ID record. This decoder shows all data as best it can, regardless of the errors.

One limitation of this decoder is that it can't display the capture of an entire floppy disk. It works best when displaying one track at a time, otherwise it is too slow and uses too much memory and could crash PulseView.

**Capturing Raw Disk Data with a Logic Analyzer**

The recommended probe/channel configuration when using a logic analyzer to capture raw digital disk data:

*   0: Read Data _(required)_
    
*   1: connect to GND _(required -- is "extra" channel)_
    
*   2: connect to GND _(required -- is "suppress" channel)_
    
*   3: Index Pulse _(optional)_
    
*   4: Side Select _(required if capturing more than one track at a time, otherwise optional)_
    
*   5: Step Pulse _(required if capturing more than one track at a time, otherwise optional)_
    
*   6: _(not used)_
    
*   7: _(not used)_
    
The recommended minimum sample rates are: 16 MS/s for 500 kbps, 8 MS/s for 250 kbps, 4 MS/s for 125 kbps, etc.

  

After the capture has completed, you need to export the logic analyzer data for one track at a time as 8-bit binary samples. Wherever the Side Select level changes, or there is a Step Pulse, this marks the end of the previous track, and the beginning of the next track.

  

**MFM Decoder User Interface**

  

To open an exported binary logic analyzer file, click on the ▼ symbol beside the **Open** icon in PulseView:

*   Import Raw binary...
    
*   select the file to open
    
*   Number of channels:
    
*   3 _(or more, if you want to see the index, side, or step channels)_
    
*   Sample rate:
    
*   specify the sample rate the logic analyzer used to capture the data, e.g., 16000000
    

  

To open a sigrok session (.sr) file, click on the **Open** icon in PulseView, then select the desired .sr file. If the file was created by UFDR, it will also include an analog channel. If the analog signal displays as a thin line, click on **ana** in the left margin, and ensure that 0.5 V/div is selected for Vertical resolution.

  

Use the mouse wheel to zoom in until you can see the individual pulses in channel 0 _('digi')_.

  

The first time you process a file when the disk format is unknown:

*   use the measurement cursor or use the **Timing** decoder to measure the pulse-to-pulse intervals
    
*   if intervals appear to have one of three values, it is probably encoded as MFM:
    
*   if the smallest intervals are approx. 4 usec. (leading edge to leading edge), the data rate is probably 250000, etc.
    
*   if intervals appear to have one of only two values, it is probably encoded as FM:
    
*   if the smallest intervals are approx. 4 usec. (leading edge to leading edge), the data rate is probably 125000, etc.
    

  

Click on the **Decoder** icon in PulseView, then select the **MFM** decoder.

  

Clicking on **MFM** in the left margin brings up the **mfm** decoder options dialog box:

*   Name:
    
*   can be changed if desired
    
*   Colour:
    
*   can be changed to whatever you desire
    
*   Read data (channel 0) \*:
    
*   must always be channel 0 _(or 'digi' for .sr files created by UFDR)_
    
*   Extra pulses (channel 1) \*:
    
*   must always be channel 1 _(or 'extr' for .sr files created by UFDR)_
    
*   this channel allows you to add missing pulses that are messing up the decoding
    
*   need to use some other program to modify this channel
    
*   Suppress pulses (channel 2) \*:
    
*   must always be channel 2 _(or 'supr' for .sr files created by UFDR)_
    
*   this channel allows you to suppress spurious pulses that are messing up the decoding
    
*   need to use some other program to modify this channel
    
*   Leading edge:
    
*   specify 'rising' if the pulses look like \_\_\_┌┐\_\_\_ or 'falling' if they look the opposite
    
*   Data rate (bps):
    
*   125000, 150000, 250000, 300000, or 500000
    
*   Encoding:
    
*   FM or MFM
    
*   Sector length:
    
*   128, 256, 512, or 1024
    
*   if unknown, select 128, then zoom in on a decoded ID Record -- the fourth byte has a code for the sector length:
    

00 = 128, 01 = 256, 02 = 512, 03 = 1024 -- then select this

*   Display all MFM prefix bytes:
    
*   yes = show all places where the bit pattern suggests special marks, no = don't display
    
*   only used for MFM, ignored for FM
    
*   used to find damaged/incomplete Index Marks, ID Address Marks, and Data Address Marks
    
*   Display sample numbers:
    
*   yes = includes sample numbers in the "win" annotation row, no = don't display them (saves memory, and speeds it up)
    
*   Sample # to display report:
    
*   if this value is less than the last enabled leading edge in the file, a summary report will be displayed in the bottom annotation row for all data prior to this point
    
*   defaults to 2111111111, which effectively disables the feature (unless the data has more than that number of samples)
    
*   best to change the Read data channel to "-" before changing this value, then select channel 0 _('digi')_ afterwards
    
*   binary or .sr files created by UFDR have a special code inserted at the end of channel 1 ('extr') that causes the report to always be displayed, regardless of this setting
    
*   Write errors to stderr:
    
*   yes = display various decoding errors to stderr (requires the debug version of PulseView), no = don't display them
    
*   Write decoded data to file:
    
*   yes = write decoded sector data to a file, no = don't write to file
    
*   the folder and file name are currently hardcoded as D:/DCW/UFDR/Decode/diskdata.UFD for Windows
    
*   the file contains a 16-byte file header, and each sector has a 16-byte sector header followed by the sector data
    

  

Zooming in or out works best when using the mouse wheel.

  

**Other**

  

Refer to data sheets for floppy disk controller chips for more information on the encoding of data on floppy disks.

  

The **UFDR** program mentioned above captures analog and digital data from an entire disk using custom hardware, and can extract individual tracks into .sr files. For more information, refer to:

[http://www.sardis-technologies.com/VCF-PNW-2018/Index.htm](http://www.sardis-technologies.com/VCF-PNW-2018/Index.htm)

  

  

  

  

**....FILE: PulseView-MFM-Decoder.wri last modified 2018-Mar-24 18:15 PDT**
