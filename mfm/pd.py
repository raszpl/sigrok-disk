## ---------------------------------------------------------------------------
## FILE: decoders\mfm\pd.py
## PURPOSE: Decode floppy and hard disk FM or MFM pulse stream.
##
## Copyright (C) 2017 David C. Wiens <dcwiens@sardis-technologies.com>
## Copyright (c) 2025 MajenkoProjects
## Copyright (C) 2025 Rasz_pl <https://github.com/raszpl>
## Initial version created 2017-Mar-14.
## Last modified 2025-Sep-5
## ---------------------------------------------------------------------------
## Example sigrok-cli command line usage:
## sigrok-cli -D -i MFM_HDDdataOneSector.sr -P mfm -A mfm=bytes:fields
## sigrok-cli -D -i MFM_HDDdataDig.sr -P mfm:report="DAM (Data Address Mark)":report_qty=19 -A mfm=fields:reports
## sigrok-cli -D -i SampleFMdataDig.sr -P mfm:data_rate=125000:encoding=FM:type=FDD:data_crc_bits=16:data_crc_poly=0x1021:sect_len=256 -A mfm=fields
## sigrok-cli -D -i SampleMFMdataDig.sr -P mfm:data_rate=250000:encoding=MFM:type=FDD:data_crc_bits=16:data_crc_poly=0x1021:sect_len=256 -A mfm=fields
##
## Explanation
## sigrok-cli -D -I csv:logic_channels=3:column_formats=t,l,l,l -i YourHugeSlow.csv -P mfm:option1=value1:option2=value2 -A mfm=annotation1:annotation2
## Available option1=value1:option2=value2 are in options Tuple List in the Decoder class.
## Available annotation1:annotation2 are in annotation_rows List of Lists in the Decoder class.
## ---------------------------------------------------------------------------
## Changelog:
## 2025-Sep-5
##	- display_bits() no longer reports clock errors on legit Mark prefixes. (Rasz)
##	- Command line usage examples. (Rasz)
## 2025-Sep-4
##	- Reworked report generation. (Rasz)
## 2025-Sep-3
##	- Stripped out stderr output and data writing code. (Majenko)
##	- Extra and suppress channels optional. (Majenko)
##	- Possible support for 7 byte headers (not tested). (Majenko)
##	- Enums to make state machine/messages more readable. (Rasz)
##	- Array CRC routine, faster than calling per byte. (Rasz)
##	- Fixed DSView crashines while zooming during data load/processing. (Rasz)
##	- Added DDAM (Deleted Data Address Mark). (Rasz)
## 2025-Sep-2
##	- Fixed DSView compatibility, still fragile: crashes when zooming in during data
##	  load/processing. (Majenko)
##	- Fixed sigrok-cli comptibility, metadata() and start() call order is undetermined
##	  depending on things like input file size, cant rely on data present from one to another. (Rasz)
##	- Added HDD support, 32 bit CRCs, custom CRC polynomials. All only in MFM mode. (Majenko/Rasz)
## ---------------------------------------------------------------------------
## To Do:
##	- create more user instructions
##	- include test files and related information for regression testing
## Suggested enhancements:
##	- support MMFM
## ---------------------------------------------------------------------------
##
## This file is part of the libsigrokdecode project.
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <https://www.gnu.org/licenses/>.
##

import sigrokdecode as srd
from collections import deque
from array import *
from struct import *
from enum import Enum#, auto not supported in python34 :|
import sys
import os
import binascii	# only for debugging

# ----------------------------------------------------------------------------
# Enums
# Sadly those need to be up here, otherwise one has to use self. prefix
# ----------------------------------------------------------------------------

class state(Enum):
	first_mC2h_prefix	= 0		#auto()
	second_mC2h_prefix	= 1		#auto()
	third_mC2h_prefix	= 2		#auto()
	FCh_Index_Mark		= 3		#auto()
	first_mA1h_prefix	= 4		#auto()
	second_mA1h_prefix	= 5		#auto()
	third_mA1h_prefix	= 6		#auto()
	IDData_Address_Mark	= 7		#auto()
	ID_Address_Mark		= 8		#auto()
	Data_Address_Mark	= 9		#auto()
	ID_Record			= 10	#auto()
	ID_Record_CRC		= 11	#auto()
	Data_Record			= 12	#auto()
	Data_Record_CRC		= 13	#auto()
	first_gap_Byte		= 14	#auto()

class crc(Enum):
	Header	= 0		#auto()
	Data	= 1		#auto()

class field(Enum):
	FCh_Index_Mark		= 1		#auto()
	ID_Address_Mark		= 2		#auto()
	Data_Address_Mark	= 3		#auto()
	Deleted_Data_Mark	= 4		#auto()
	ID_Record			= 5		#auto()
	Data_Record			= 6		#auto()
	CRC_Ok				= 7		#auto()
	CRC_Error			= 8		#auto()
	Unknown_Byte		= 9		#auto()

# ----------------------------------------------------------------------------
# PURPOSE: Handle missing sample rate.
# ----------------------------------------------------------------------------

class SamplerateError(Exception):
	pass

# ----------------------------------------------------------------------------
# PURPOSE: Subclass and initialize the Decoder class.
# ----------------------------------------------------------------------------

class Decoder(srd.Decoder):
	api_version = 3
	id = 'mfm'
	name = 'MFM'
	longname = 'FM/MFM decoding'
	desc = 'Decode floppy and hard disk FM or MFM pulse stream.'
	license = 'gplv2+'
	inputs = ['logic']
	outputs = ['mfm']
	tags = ['Disk', 'PC']
	channels = (
		{'id': 'data', 'name': 'Read data', 'desc': 'channel 0', 'idn':'dec_mfm_chan_data'},
	)
	optional_channels = (
		{'id': 'extra', 'name': 'Extra pulses', 'desc': 'channel 1', 'idn':'dec_mfm_chan_extra'},
		{'id': 'suppress', 'name': 'Suppress pulses', 'desc': 'channel 2', 'idn':'dec_mfm_chan_suppress'},
	)
	annotations = (
		('erw', 'erw'),
		('unk', 'unknown'),
		('clk', 'clock'),
		('dat', 'data'),
		('erb', 'erb'),
		('bit', 'bit'),
		('byt', 'byte'),
		('mrk', 'mark'),
		('rec', 'record'),
		('cre', 'crc error'),
		('crc', 'crc'),
		('rpt', 'report'),
		('pfx', 'prefix'),
		('pul', 'pulse'),
		('erp', 'report'),
		('err', 'error'),
	)
	annotation_rows = (
		('pulses', 'Pulses', (13, 14,)),
		('windows', 'Windows', (0, 1, 2, 3,)),
		('prefixes', 'Prefixes', (12,)),
		('bits', 'Bits', (4, 5,)),
		('bytes', 'Bytes', (6,)),
		('fields', 'Fields', (7, 8, 9, 10,)),
		('errors', 'Errors', (15,)),
		('reports', 'Reports', (11,)),
	)
	options = (
		{'id': 'leading_edge', 'desc': 'Leading edge',
			'default': 'rising', 'values': ('rising', 'falling')},
		{'id': 'data_rate', 'desc': 'Data rate (bps)',
			'default': '5000000', 'values': ('125000', '150000',
			'250000', '300000', '500000', '5000000', '10000000')},
		{'id': 'encoding', 'desc': 'Encoding',
			'default': 'MFM', 'values': ('FM', 'MFM')},
		{'id': 'type', 'desc': 'Type',
			'default': 'HDD', 'values': ('FDD', 'HDD')},
		{'id': 'sect_len', 'desc': 'Sector length',
			'default': '512', 'values': ('128', '256', '512', '1024')},
		{'id': 'header_bytes', 'desc': 'Header bytes',
			'default': '8', 'values': ('7', '8')},
		{'id': 'header_crc_bits', 'desc': 'Header field CRC bits',
			'default': '16', 'values': ('16', '32')},
		{'id': 'header_crc_poly', 'desc': 'Header field CRC Polynomial',
			'default': '0x1021'},		# x16 + x12 + x5 + 1 standard CRC-CCITT
		{'id': 'data_crc_bits', 'desc': 'Data field CRC bits',
			'default': '32', 'values': ('16', '32', '56')},
		{'id': 'data_crc_poly', 'desc': 'Data field CRC Polynomial',
			'default': '0xA00805', 'values': ('0x1021', '0xA00805', '0x140a0445',
			'0x0104c981', '0x41044185')},
		{'id': 'data_crc_poly_custom', 'desc': 'Custom Data Poly (overrides above)',
			'default': ''},
		{'id': 'dsply_pfx', 'desc': 'Display all MFM prefix bytes',
			'default': 'no', 'values': ('yes', 'no')},
		{'id': 'dsply_sn', 'desc': 'Display sample numbers',
			'default': 'yes', 'values': ('yes', 'no')},
		{'id': 'report', 'desc': 'Display report after',
			'default': 'Disabled', 'values': ('Disabled', 'IAM (Index Mark)', 'IDAM (ID Address Mark)', 'DAM (Data Address Mark)', 'DDAM (Deleted Data Mark)')},
		{'id': 'report_qty', 'desc': 'Report every x Marks',
			'default': '9'},
	)

	# ------------------------------------------------------------------------
	# PURPOSE: Class constructor/initializer.
	# ------------------------------------------------------------------------

	def __init__(self):
		self.reset()

	def reset(self):
		# Initialize pre-defined variables.

		self.samplerate = None
		self.last_samplenum = None
		self.last_n = deque()
		self.chunks = 0

		# Define (and initialize) various custom variables.

		self.byte_start = 0			# start of byte (sample number)
		self.byte_end = 0			# end of byte (sample number)
		self.field_start = 0		# start of field (sample number)
		self.pb_state = 0			# processing byte state = 1..10
		self.byte_cnt = 0			# number of bytes left to process in field (1024/512/256/128/4/2..0)
		self.IDlastAM = -1			# sample number of most recent ID Address Mark, -1 = not found or not valid
		self.max_id_data_gap = 0	# maximum gap between ID Address Mark and following Data Address Mark (samples)
		self.IDcyl = 0				# cylinder number field in ID record (0..244)
		self.IDsid = 0				# side number field in ID record (0..1)
		self.IDsec = 0				# sector number field in ID record (0..244)
		self.IDlenc = 0				# sector length code field in ID record (0..3)
		self.IDlenv = 0				# sector length (from code field) in ID record (128/256/512/1024)

		self.IDrec = array('B', [0 for i in range(8)])		# ID record (7-8 bytes)
		self.DRrec = array('B', [0 for i in range(1024)])	# Data record (128/256/512/1024 bytes)

		# FIFO (using circular buffers) of starting/ending sample numbers
		# and data values for 33 half-bit-cell windows.  Data values are
		# number of leading edges per window (0..n).

		self.fifo_ws = array('l', [0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
								   0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
								   0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
								   0, 0, 0,])

		self.fifo_we = array('l', [0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
								   0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
								   0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
								   0, 0, 0,])

		self.fifo_wv = array('i', [0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
								   0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
								   0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
								   0, 0, 0,])

		self.fifo_wp = -1			# index where last FIFO entry was written (0..32)
		self.fifo_rp = 0			# index where to read next FIFO entry (0..32)
		self.fifo_cnt = 0			# number of entries currently in FIFO (0..33)

		# Define and zero statistics counters.

		self.IAMs	= 0				# number of Index Marks
		self.IDAMs	= 0				# number of ID Address Marks
		self.DAMs	= 0				# number of Data Address Marks
		self.DDAMs	= 0				# number of Deleted Data Address Marks
		self.CRC_OK	= 0				# number of OK CRCs
		self.CRC_err = 0			# number of error CRCs
		self.EiPW = 0				# number of leading edges found in a previous window
		self.CkEr = 0				# number of bits with clocking errors
		self.OoTI = 0				# number of out-of-tolerance leading edge intervals
		self.Intrvls = 0			# number of leading edge intervals

		self.report_start = 0
		self.reports_called = 0

	# ------------------------------------------------------------------------
	# PURPOSE: Various initialization when decoder started.
	# ------------------------------------------------------------------------

	def start(self):
		self.out_ann = self.register(srd.OUTPUT_ANN)

		# Initialize options selected by the user in the dialog box.

		self.rising_edge = True if self.options['leading_edge'] == 'rising' else False
		self.data_rate = float(self.options['data_rate'])
		self.encodingFM = True if self.options['encoding'] == 'FM' else False
		self.fdd = True if self.options['type'] == 'FDD' else False
		self.sector_len = int(self.options['sect_len'])
		self.header_bytes = int(self.options['header_bytes'])
		self.header_crc_bits = int(self.options['header_crc_bits'])
		self.header_crc_poly = int(self.options['header_crc_poly'], 0) & ((1 << int(self.options['header_crc_bits'])) -1)
		self.data_crc_bits = int(self.options['data_crc_bits'])
		self.data_crc_poly = int(self.options['data_crc_poly'], 0)
		if self.options['data_crc_poly_custom']:
			self.data_crc_poly = int(self.options['data_crc_poly_custom'], 0) & ((1 << int(self.options['data_crc_bits'])) -1)
		self.dsply_pfx = True if self.options['dsply_pfx'] == 'yes' else False
		self.dsply_sn = True if self.options['dsply_sn'] == 'yes' else False

		self.report = {'Disabled':'nope', 
						'IAM (Index Mark)':field.FCh_Index_Mark,
						'IDAM (ID Address Mark)':field.ID_Address_Mark,
						'DAM (Data Address Mark)':field.Data_Address_Mark,
						'DDAM (Deleted Data Mark)':field.Deleted_Data_Mark}[self.options['report']]
		self.report_qty = int(self.options['report_qty'])
		self.reports_called = 0

		# precompute crc constants
		self.header_crc_bytes = self.header_crc_bits // 8
		self.header_crc_offset = self.header_crc_bits - 8
		self.header_crc_mask = (1 << self.header_crc_bits) -1
		self.data_crc_bytes = self.data_crc_bits // 8
		self.data_crc_offset = self.data_crc_bits - 8
		self.data_crc_mask = (1 << self.data_crc_bits) -1

		# Other initialization.
		self.initial_pins = [1 if self.rising_edge == True else 0]

	# ------------------------------------------------------------------------
	# PURPOSE: Get the data sample rate entered by the user.
	# ------------------------------------------------------------------------

	def metadata(self, key, value):
		if key == srd.SRD_CONF_SAMPLERATE:
			self.samplerate = value
			self.samplerateMSps = self.samplerate / 1000000.0

			# Calculate number of samples in 30 usec.
			self.samples30usec = int(self.samplerate / 1000000.0 * 30.0)

	# ------------------------------------------------------------------------
	# PURPOSE: Calculate CRC of a bytearray.
	# NOTES:
	#  - Special CRC-16-CCITT case processes 4 bits at a time using lookup
	#	 table. Faster in theory, havent measured actual speed or if it even
	#	 matters :)
	#  IN: bytearray
	#	   type		True = calculate Header CRC
	#				False = calculate Data CRC
	# ------------------------------------------------------------------------
	CRC16CCITT_tab = array('I', [0x0000, 0x1021, 0x2042, 0x3063,
							   0x4084, 0x50A5, 0x60C6, 0x70E7,
							   0x8108, 0x9129, 0xA14A, 0xB16B,
							   0xC18C, 0xD1AD, 0xE1CE, 0xF1EF])

	def calculate_crc(self, bytearray, type):
		if type == crc.Header:
			crc_accum	= self.header_crc_mask
			crc_bits	= self.header_crc_bits
			crc_offset	= self.header_crc_offset
			crc_mask	= self.header_crc_mask
			crc_poly	= self.header_crc_poly
		else:
			crc_accum	= self.data_crc_mask
			crc_bits	= self.data_crc_bits
			crc_offset	= self.data_crc_offset
			crc_mask	= self.data_crc_mask
			crc_poly	= self.data_crc_poly

		#self.put(0, 0, self.out_ann, [9, ['bytearray ' + binascii.hexlify(bytearray).decode('ascii')]])

		if crc_poly == 0x1021 and crc_bits == 16:
			# fast lookup table for CRC-16-CCITT
			for byte in bytearray:
				crc_accum = (self.CRC16CCITT_tab[((crc_accum >> 12) ^ (byte >>	4)) & 0x0F]
								^ (crc_accum << 4)) & 0xFFFF
				crc_accum = (self.CRC16CCITT_tab[((crc_accum >> 12) ^ (byte & 0x0F)) & 0x0F]
								^ (crc_accum << 4)) & 0xFFFF
		else: 
			for byte in bytearray:
				crc_accum ^= (byte << crc_offset)
				crc_accum &= crc_mask
				for i in range(8):
					check = crc_accum & (1 << (crc_bits -1))
					crc_accum <<= 1
					crc_accum &= crc_mask
					if check:
						crc_accum ^= crc_poly
						crc_accum &= crc_mask

		#self.put(0, 0, self.out_ann, [9, ['crc_accum afte %02X' % crc_accum]])
		#self.put(0, 0, self.out_ann, [9, ['self.IDcrc %02X' % self.IDcrc]])
		self.crc_accum = crc_accum

	# ------------------------------------------------------------------------
	# PURPOSE: Increment FIFO read pointer and decrement entry count.
	# ------------------------------------------------------------------------

	def inc_fifo_rp(self):
		self.fifo_rp += 1
		if self.fifo_rp > 32:
			self.fifo_rp -= 33
		self.fifo_cnt -= 1

	# ------------------------------------------------------------------------
	# PURPOSE: Increment FIFO write pointer and increment entry count.
	# ------------------------------------------------------------------------

	def inc_fifo_wp(self):
		self.fifo_wp += 1
		if self.fifo_wp > 32:
			self.fifo_wp -= 33
		self.fifo_cnt += 1

	# ------------------------------------------------------------------------
	# PURPOSE: Display annotations for 16 windows and 8 bits of one byte, using
	#	FIFO data.
	# NOTES:
	#  - On entry the FIFO must have exactly 33 or 17 entries in it, and on
	#	 exit the FIFO will have 16 fewer entries in it (17 or 1).
	#  - Half-bit-cell windows are processed in time order from the last window
	#	 of the previous byte, to the second last window of the current byte.
	#  - Bits are processed in time order from the first bit (msb, bit 7) to
	#	 the last bit (lsb, bit 0) of the current byte.
	#  - Need to use a while loop instead of a for loop due to some strange bug,
	#	 possibly in Python itself?
	# IN: spclk	 True = special clocking, don't display clock errors to stderr
	#			 False = normal clocking, display clock errors to stderr
	#	  self.fifo_rp, self.fifo_cnt
	# OUT: self.byte_start, self.byte_end, self.fifo_rp, self.fifo_cnt updated
	# ------------------------------------------------------------------------

	def display_bits(self, spclk):
		# Define (and initialize) function variables.

		win_start = 0			# start of window (sample number)
		win_end = 0				# end of window (sample number)
		win_val = 0				# window value (0..n)
		bit_start = 0			# start of bit (sample number)
		bit_end = 0				# end of bit (sample number)
		bit_val = 0				# bit value (0..1)
		shift3 = 0				# 3-bit shift register of window values
		self.byte_start = -1	# start of byte (sample number, -1 = not set yet)

		# Process each of the 8 data bits and 17 windows in turn.
		# Start with bit 8, which is bit 0 of the previous byte.

		bitn = 8

		while True:

			# Display annotation for second (data) half-bit-cell window of a pair,
			# starting with the data window of the last bit of the previous byte.
			# The last window of the current byte is read but not removed from the
			# FIFO, and isn't displayed.

			win_start = self.fifo_ws[self.fifo_rp]
			win_end = self.fifo_we[self.fifo_rp]
			win_val = self.fifo_wv[self.fifo_rp]
			if bitn > 0:
				self.inc_fifo_rp()

			shift3 = ((shift3 & 0x03) << 1) + (1 if win_val > 1 else win_val)

			if bitn > 0:
				if self.dsply_sn:
					if win_val > 1:
						self.put(win_end - 1, win_end, self.out_ann, [15, ['Err']])
						self.put(win_start, win_end, self.out_ann,
								[0, ['%d d (extra pulse in win) s%d' % (win_val, win_start), '%d' % win_val]])
					else:
						self.put(win_start, win_end, self.out_ann,
								[3, ['%d d s%d' % (win_val, win_start), '%d' % win_val]])
				else:
					if win_val > 1:
						self.put(win_end - 1, win_end, self.out_ann, [15, ['Err']])
						self.put(win_start, win_end, self.out_ann,
								[0, ['%d d (extra pulse in win)' % win_val, '%d' % win_val]])
					else:
						self.put(win_start, win_end, self.out_ann,
								[3, ['%d d' % win_val, '%d' % win_val]])

			bit_end = win_end
			bit_val = 1 if win_val > 1 else win_val

			# Display annotation for bit using value in data window.  The last
			# bit for the previous byte has already been displayed previously.

			if bitn < 8:
				if ((not self.encodingFM) and (shift3 == 0 or shift3 == 3 or shift3 == 6 or shift3 == 7)) \
				 or (	 self.encodingFM  and (shift3 == 0 or shift3 == 1 or shift3 == 4 or shift3 == 5)):
					if not spclk:
						self.put(bit_end - 1, bit_end, self.out_ann, [15, ['Err']])
						self.CkEr += 1
					self.put(bit_start, bit_end, self.out_ann, [4, ['%d (clock error)' % bit_val, '%d' % bit_val]])
				else:
					self.put(bit_start, bit_end, self.out_ann, [5, ['%d' % bit_val]])

			if bitn == 0:
				break

			# Display annotation for first (clock) half-bit-cell window of a pair.

			win_start = self.fifo_ws[self.fifo_rp]
			win_end = self.fifo_we[self.fifo_rp]
			win_val = self.fifo_wv[self.fifo_rp]
			self.inc_fifo_rp()

			shift3 = ((shift3 & 0x03) << 1) + (1 if win_val > 1 else win_val)

			if self.dsply_sn:
				if win_val > 1:
					self.put(win_end - 1, win_end, self.out_ann, [15, ['Err']])
					self.put(win_start, win_end, self.out_ann,
							 [0, ['%d c (extra pulse in win) s%d' % (win_val, win_start), '%d' % win_val]])
				else:
					self.put(win_start, win_end, self.out_ann,
							 [2, ['%d c s%d' % (win_val, win_start), '%d' % win_val]])
			else:
				if win_val > 1:
					self.put(win_end - 1, win_end, self.out_ann, [15, ['Err']])
					self.put(win_start, win_end, self.out_ann,
							 [0, ['%d c (extra pulse in win)' % win_val, '%d' % win_val]])
				else:
					self.put(win_start, win_end, self.out_ann,
							 [2, ['%d c' % win_val, '%d' % win_val]])

			bit_start = win_start
			if self.byte_start == -1:
				self.byte_start = bit_start

			bitn -= 1

			# end while

		self.byte_end = bit_end

	# ------------------------------------------------------------------------
	# PURPOSE: Display annotations for one byte and its 8 bits and 16 windows.
	# NOTES:
	#  - On entry the FIFO must have exactly 33 or 17 entries in it, and on
	#	 exit the FIFO will have 16 fewer entries in it (17 or 1).
	# IN: val  byte value (00h..FFh)
	#	  spclk	 True = special clocking, don't display clock errors to stderr
	#			 False = normal clocking, display clock errors to stderr
	#	  self.fifo_rp
	# OUT: self.byte_start, self.byte_end, self.fifo_rp	 updated
	# ------------------------------------------------------------------------

	def display_byte(self, val, spclk):
		# Display annotations for windows and bits of this byte.

		self.display_bits(spclk)

		# Display annotation for this byte.

		short_ann = '%02X' % val
		if val >= 32 and val < 127:
			long_ann = '%02X \'%c\'' % (val, val)
		else:
			long_ann = short_ann

		self.put(self.byte_start, self.byte_end, self.out_ann,
				 [6, [long_ann, short_ann]])

	# ------------------------------------------------------------------------
	# Display an annotation for a field.
	# IN: typ  type of field = 'x'/'i'/'I'/'d'/'D'/'e'/'c'
	#	  self.field_start, self.byte_end
	# OUT: self.field_start	 updated
	# ------------------------------------------------------------------------

	def display_field(self, typ, val=0):
		if typ == field.FCh_Index_Mark:
			self.IAMs += 1
			self.put(self.field_start, self.byte_end, self.out_ann,
					 [7, ['Index Mark', 'IAM', 'I']])
			self.report_last = field.FCh_Index_Mark
			if self.report == field.FCh_Index_Mark:
				self.reports_called = self.IAMs
				self.display_report()

		elif typ == field.ID_Address_Mark:
			self.IDAMs += 1
			self.put(self.field_start, self.byte_end, self.out_ann,
					 [7, ['ID Address Mark', 'IDAM', 'M']])
			self.report_last = field.ID_Address_Mark
			if self.report == field.ID_Address_Mark:
				self.reports_called = self.IDAMs
				self.display_report()

		elif typ == field.Data_Address_Mark:
			if self.fdd and self.DRmark in (0xF8, 0xF9, 0xFA): 
				self.DDAMs += 1
				self.put(self.field_start, self.byte_end, self.out_ann,
						[7, ['Deleted Data Address Mark', 'Deleted Data Mark', 'DDAM', 'M']])
				self.report_last = field.Deleted_Data_Mark
				if self.report == field.Deleted_Data_Mark:
					self.reports_called = self.DDAMs
			else:
				self.DAMs += 1
				self.put(self.field_start, self.byte_end, self.out_ann,
						[7, ['Data Address Mark', 'Data Mark', 'DAM', 'M']])
				self.report_last = field.Data_Address_Mark
				if self.report == field.Data_Address_Mark:
					self.reports_called = self.DAMs

		elif typ == field.ID_Record:
			self.put(self.field_start, self.byte_end, self.out_ann,
					 [8, ['ID Record: cyl=%d, sid=%d, sec=%d, len=%d' %
						  (self.IDcyl, self.IDsid, self.IDsec, self.IDlenv),
						  'ID Record', 'Irec', 'R']])

		elif typ == field.Data_Record:
			self.put(self.field_start, self.byte_end, self.out_ann,
					 [8, ['Data Record', 'Drec', 'R']])

		elif typ == field.CRC_Ok:
			self.CRC_OK += 1
			self.put(self.field_start, self.byte_end, self.out_ann,
					 [10, ['CRC OK %02X' % self.crc_accum, 'CRC OK', 'CRC', 'C']])
			if self.report_last in (field.Deleted_Data_Mark, field.Data_Address_Mark):
				self.display_report()

		elif typ == field.CRC_Error:
			self.CRC_err += 1
			self.put(self.byte_end - 1, self.byte_end, self.out_ann, [15, ['Error', 'Err', 'E']])
			self.put(self.field_start, self.byte_end, self.out_ann,
					 [9, ['CRC error %02X' % self.crc_accum, 'CRC error', 'CRC', 'C']])
			if self.report_last in (field.Deleted_Data_Mark, field.Data_Address_Mark):
				self.display_report()

		elif typ == field.Unknown_Byte:
			self.put(self.byte_end - 1, self.byte_end, self.out_ann, [15, ['Error', 'Err', 'E']])

		self.field_start = self.byte_end

	# ------------------------------------------------------------------------
	# PURPOSE: Decode the ID Record subfields.
	# IN: fld_code	4 = cylinder, 3 = side, 2 = sector, 1 = length code
	#	  val  8-bit subfield value (00h..FFh)
	# ------------------------------------------------------------------------

	def decode_id_rec(self, fld_code, val):
		if self.header_bytes == 7:
			self.decode_id_rec_7byte(fld_code, val)
		else:
			self.decode_id_rec_8byte(fld_code,val)

	def decode_id_rec_7byte(self, fld_code, val):
		if fld_code == 3:
			msb = self.IDmark ^ 0xFE
			self.IDcyl = val | (msb << 8)
		elif fld_code == 2:
			self.IDsid = val & 0x0F
			self.IDlenc = 512
			if val & 0xF0 == 0:
				self.IDlenv = 128
			elif val & 0xF0 == 0x10:
				self.IDlenv = 256
			elif val & 0xF0 == 0x20:
				self.IDlenv = 512
			elif val & 0xF0 == 0x30:
				self.IDlenv = 1024
			else:
				self.IDlenv = 0
			if self.IDlenv != self.sector_len:
				self.IDlastAM = -1
		elif fld_code == 1:
			self.IDsec = val

	def decode_id_rec_8byte(self, fld_code, val):
		if fld_code == 4:
			self.IDcyl = val
		elif fld_code == 3:
			self.IDsid = val
		elif fld_code == 2:
			self.IDsec = val
		elif fld_code == 1:
			self.IDlenc = val
			if val == 0:
				self.IDlenv = 128
			elif val == 1:
				self.IDlenv = 256
			elif val == 2:
				self.IDlenv = 512
			elif val == 3:
				self.IDlenv = 1024
			else:
				self.IDlenv = 0
			if self.IDlenv != self.sector_len:
				self.IDlastAM = -1

	# ------------------------------------------------------------------------
	# PURPOSE: Process one byte extracted from FM pulse stream.
	# NOTES:
	#  - Index/Address Mark prefixes are preceded by a 00h byte.
	#  - When called with 0x1FC/0x1FE/0x1F8..0x1FB values, the FIFO must have
	#	 exactly 33 entries in it, otherwise it must have exactly 17 entries.
	#	 On exit the FIFO will have exactly 1 entry in it.
	# IN: val  00h..FFh	 normal byte
	#		   1FCh = 00h + FCh with D7h clock = Index Mark
	#		   1FEh = 00h + FEh with C7h clock = ID Address Mark
	#		   1FBh = 00h + FBh with C7h clock = normal Data Address Mark
	#		   1F8h..1FAh = 00h + F8h..FAh with C7h clock = deleted Data Address Mark
	# RETURNS: 0 = OK, get next byte
	#		   -1 = resync (end of Index Mark, end of ID/Data Record, or error)
	# ------------------------------------------------------------------------

	def process_byteFM(self, val):
		if val == 0x1FE:
			self.pb_state = state.ID_Address_Mark
		elif val >= 0x1F8 and val <= 0x1FB:
			val &= 0x0FF
			self.pb_state = state.Data_Address_Mark
		elif val == 0x1FC:
			self.pb_state = state.FCh_Index_Mark

		if self.pb_state == state.ID_Address_Mark:
			self.display_byte(0x00, False)
			self.display_byte(0xFE, True)
			self.IDmark = (val & 0x0FF)
			self.field_start = self.byte_start
			self.display_field(field.ID_Address_Mark)
			self.IDlastAM = self.field_start
			self.IDcrc = 0
			self.byte_cnt = self.header_bytes - 4
			self.pb_state = state.ID_Record

		elif self.pb_state == state.ID_Record:
			self.display_byte(val, False)
			self.IDrec[self.header_bytes - 4 - self.byte_cnt] = val
			self.decode_id_rec(self.byte_cnt, val)
			self.byte_cnt -= 1
			if self.byte_cnt == 0:
				self.display_field(field.ID_Record)
				self.byte_cnt = self.header_crc_bytes
				self.pb_state = state.ID_Record_CRC

		elif self.pb_state == state.ID_Record_CRC:
			self.display_byte(val, False)
			self.IDcrc <<= 8
			self.IDcrc += val
			self.byte_cnt -= 1
			if self.byte_cnt == 0:
				self.calculate_crc(bytes([self.IDmark]) + self.IDrec[:self.header_bytes -4], crc.Header)
				if self.crc_accum == self.IDcrc:
					self.display_field(field.CRC_Ok)
				else:
					self.IDlastAM = -1
					self.display_field(field.CRC_Error)
				self.pb_state = state.first_gap_Byte

		elif self.pb_state == state.Data_Address_Mark:
			self.display_byte(0x00, False)
			self.display_byte(val, True)
			self.DRmark = val
			self.field_start = self.byte_start
			self.display_field(field.Data_Address_Mark)
			if self.IDlastAM > 0 \
			 and (self.field_start - self.IDlastAM) > self.max_id_data_gap:
				self.IDlastAM = -1
			self.DRcrc = 0
			self.byte_cnt = self.sector_len
			self.pb_state = state.Data_Record

		elif self.pb_state == state.Data_Record:
			self.display_byte(val, False)
			self.DRrec[self.sector_len - self.byte_cnt] = val
			self.byte_cnt -= 1
			if self.byte_cnt == 0:
				self.display_field(field.Data_Record)
				self.byte_cnt = self.data_crc_bytes
				self.pb_state = state.Data_Record_CRC

		elif self.pb_state == state.Data_Record_CRC:
			self.display_byte(val, False)
			self.DRcrc <<= 8
			self.DRcrc += val
			self.byte_cnt -= 1
			if self.byte_cnt == 0:
				self.calculate_crc(bytes([self.DRmark]) + self.DRrec[:self.sector_len], crc.Data)
				if self.crc_accum == self.DRcrc:
					self.display_field(field.CRC_Ok)
				else:
					self.display_field(field.CRC_Error)
				self.pb_state = state.first_gap_Byte

		elif self.pb_state == state.FCh_Index_Mark:
			self.display_byte(0x00, False)
			self.display_byte(0xFC, True)
			self.field_start = self.byte_start
			self.display_field(field.FCh_Index_Mark)
			self.pb_state = state.first_gap_Byte

		elif self.pb_state == state.first_gap_Byte:	# process first gap byte after CRC or Index Mark
			self.display_byte(val, False)
			return -1								# done, unsync

		else:
			return -1

		return 0

	# ------------------------------------------------------------------------
	# PURPOSE: Process one byte extracted from MFM pulse stream.
	# NOTES:
	#  - Index/Address Mark prefixes are preceded by a 00h byte.
	#  - When called with 0x1C2/0x1A1 values, the FIFO must have exactly 33
	#	 entries in it, otherwise it must have exactly 17 entries.	On exit the
	#	 FIFO will have exactly 1 entry in it, unless there is an error, in which
	#	 case it will still have 17 entries.
	# IN: val  00h..FFh	 normal byte
	#		   1C2h	 00h + first mC2h prefix byte (no clock between bits 3/4)
	#		   2C2h	 subsequent mC2h prefix byte (no clock between bits 3/4)
	#		   1A1h	 00h + first mA1h prefix byte (no clock between bits 4/5)
	#		   2A1h	 subsequent mA1h prefix byte (no clock between bits 4/5)
	# RETURNS: 0 = OK, get next byte
	#		   -1 = resync (end of Index Mark, end of ID/Data Record, or error)
	# ------------------------------------------------------------------------

	def process_byteMFM(self, val):
		if val == 0x1A1:
			self.pb_state = state.first_mA1h_prefix
		elif val == 0x1C2:
			self.pb_state = state.first_mC2h_prefix

		if self.pb_state == state.first_mA1h_prefix:
			self.display_byte(0x00, False)
			self.display_byte(0xA1, True)
			self.A1 = [0xA1]
			self.field_start = self.byte_start
			if self.fdd:
				self.pb_state = state.second_mA1h_prefix
			else:
				self.pb_state = state.IDData_Address_Mark

		elif self.pb_state in (state.second_mA1h_prefix, state.third_mA1h_prefix):
			if val == 0x2A1:
				self.display_byte(0xA1, True)
				self.A1.append(0xA1)
				if self.pb_state == state.second_mA1h_prefix:
					self.pb_state = state.third_mA1h_prefix
				elif self.pb_state == state.third_mA1h_prefix:
					self.pb_state = state.IDData_Address_Mark
			else:
				self.display_field(field.Unknown_Byte, val)
				return -1

		elif self.pb_state == state.IDData_Address_Mark:
			if (self.header_bytes == 8 and val == 0xFE) or \
			   (self.header_bytes == 7 and (val & 0xFC) == 0xFC):	# FEh FC-FFh ID Address Mark
				self.display_byte(val, False)
				self.IDmark = val
				self.display_field(field.ID_Address_Mark)
				self.IDlastAM = self.field_start
				self.IDcrc = 0
				self.byte_cnt = self.header_bytes - 4
				self.pb_state = state.ID_Record
			elif val >= 0xF8 and val <= 0xFB:						# F8h..FBh Data Address Mark
				self.display_byte(val, False)
				self.DRmark = val
				self.display_field(field.Data_Address_Mark)
				if self.IDlastAM > 0 \
				 and (self.field_start - self.IDlastAM) > self.max_id_data_gap:
					self.IDlastAM = -1
				self.DRcrc = 0
				self.byte_cnt = self.sector_len
				self.pb_state = state.Data_Record
			else:
				self.display_field(field.Unknown_Byte, val)
				return -1

		elif self.pb_state == state.ID_Record:
			self.display_byte(val, False)
			self.IDrec[self.header_bytes - 4 - self.byte_cnt] = val
			self.decode_id_rec(self.byte_cnt, val)
			self.byte_cnt -= 1
			if self.byte_cnt == 0:
				self.display_field(field.ID_Record)
				self.byte_cnt = self.header_crc_bytes
				self.pb_state = state.ID_Record_CRC

		elif self.pb_state == state.ID_Record_CRC:
			self.display_byte(val, False)
			self.IDcrc <<= 8
			self.IDcrc += val
			self.byte_cnt -= 1
			if self.byte_cnt == 0:
				self.calculate_crc(bytes(self.A1 + [self.IDmark]) + self.IDrec[:self.header_bytes -4], crc.Header)
				if self.crc_accum == self.IDcrc:
					self.display_field(field.CRC_Ok)
				else:
					self.IDlastAM = -1
					self.display_field(field.CRC_Error)
				self.pb_state = state.first_gap_Byte

		elif self.pb_state == state.Data_Record:
			self.display_byte(val, False)
			self.DRrec[self.sector_len - self.byte_cnt] = val
			self.byte_cnt -= 1
			if self.byte_cnt == 0:
				self.display_field(field.Data_Record)
				self.byte_cnt = self.data_crc_bytes
				self.pb_state = state.Data_Record_CRC

		elif self.pb_state == state.Data_Record_CRC:
			self.display_byte(val, False)
			self.DRcrc <<= 8
			self.DRcrc += val
			self.byte_cnt -= 1
			if self.byte_cnt == 0:
				self.calculate_crc(bytes(self.A1 + [self.DRmark]) + self.DRrec[:self.sector_len], crc.Data)
				if self.crc_accum == self.DRcrc:
					self.display_field(field.CRC_Ok)
				else:
					self.display_field(field.CRC_Error)
				self.pb_state = state.first_gap_Byte

		elif self.pb_state == state.first_mC2h_prefix:
			self.display_byte(0x00, False)
			self.display_byte(0xC2, True)
			self.field_start = self.byte_start
			self.pb_state = state.second_mC2h_prefix

		elif self.pb_state in (state.second_mC2h_prefix, state.third_mC2h_prefix):
			if val == 0x2C2:
				self.display_byte(0xC2, True)
				if self.pb_state == state.second_mC2h_prefix:
					self.pb_state = state.third_mC2h_prefix
				elif self.pb_state == state.third_mC2h_prefix:
					self.pb_state = state.FCh_Index_Mark
			else:
				self.display_field(field.Unknown_Byte, val)
				return -1

		elif self.pb_state == state.FCh_Index_Mark:
			if val == 0xFC:
				self.display_byte(val, False)
				self.display_field(field.FCh_Index_Mark)
				self.pb_state = state.first_gap_Byte
			else:
				self.display_field(field.Unknown_Byte, val)
				return -1

		elif self.pb_state == state.first_gap_Byte:	# process first gap byte after CRC or Index Mark
			self.display_byte(val, False)
			return -1								# done, unsync

		else:
			return -1

		return 0

	# ------------------------------------------------------------------------
	# PURPOSE: Display summary every x Headers.
	# ------------------------------------------------------------------------

	def display_report(self):
		if self.reports_called < self.report_qty:
			return

		self.put(self.report_start, self.byte_end, self.out_ann,
			[11, ["Summary: IAM=%d, IDAM=%d, DAM=%d, DDAM=%d, CRC_OK=%d, "\
				"CRC_err=%d, EiPW=%d, CkEr=%d, OoTI=%d/%d" \
				% (self.IAMs, self.IDAMs, self.DAMs, self.DDAMs, self.CRC_OK,\
				self.CRC_err, self.EiPW, self.CkEr, self.OoTI, self.Intrvls)]])
		(self.IAMs, self.IDAMs, self.DAMs, self.DDAMs, self.CRC_OK,\
				self.CRC_err, self.EiPW, self.CkEr, self.OoTI, self.Intrvls) = (0,0,0,0,0,0,0,0,0,0)
		self.report_start = self.byte_end
		self.reports_called = 0

	# ------------------------------------------------------------------------
	# PURPOSE: Handle processing when end-of-data reached.
	# NOTES:
	#  - PulseView doesn't call this optional method yet.
	# ------------------------------------------------------------------------

	def decode_end(self):
		pass

	# ------------------------------------------------------------------------
	# PURPOSE: Main protocol decoding loop.
	# NOTES:
	#  - It automatically terminates when self.wait() requests termination
	#	 due to end-of-data reached before specified condition found.
	# ------------------------------------------------------------------------

	def decode(self):
		# --- Verify that a sample rate was specified.

		if not self.samplerate:
			raise SamplerateError('Cannot decode without samplerate.')

		# Calculate maximum number of samples allowed between ID and Data Address Marks.
		# Cant put it in start() or metadata() becaue we cant be sure of order those
		# two are called, one initializes (samplerate) the other user options (data_rate)
		if self.encodingFM:
			self.max_id_data_gap = (self.samplerate / self.data_rate) * 8 * (1 + 4 + 2 + 30 + 10)
		else:
			self.max_id_data_gap = (self.samplerate / self.data_rate) * 8 * (4 + 4 + 2 + 43 + 15)

		# --- Initialize various (half-)bit-cell-window and other variables.

		bc10N = self.samplerate / self.data_rate		# nominal 1.0 bit cell window size (in fractional samples)

		bc05L = (bc10N * 0.5) - (bc10N * 0.25 * 0.80)	# lower/upper limits of 0.5 bit cell window size
		bc05U = (bc10N * 0.5) + (bc10N * 0.25 * 0.80)
		bc10L = (bc10N * 1.0) - (bc10N * 0.25 * 0.80)	# lower/upper limits of 1.0 bit cell window size
		bc10U = (bc10N * 1.0) + (bc10N * 0.25 * 0.80)
		bc15L = (bc10N * 1.5) - (bc10N * 0.25 * 0.80)	# lower/upper limits of 1.5 bit cell window size
		bc15U = (bc10N * 1.5) + (bc10N * 0.25 * 0.80)
		bc20L = (bc10N * 2.0) - (bc10N * 0.25 * 0.80)	# lower/upper limits of 2.0 bit cell window size
		bc20U = (bc10N * 2.0) + (bc10N * 0.25 * 0.80)

		window_size = bc10N / 2.0						# current half-bit-cell window size (in fractional samples)
		window_size_filter_accum = window_size * 32.0	# averaging filter accumulator for window size (in fractional samples)
		hbcpi = 0.0								# number of half-bit-cell windows per leading edge interval
		window_start = 0.0						# start of current half-bit-cell window (fractional sample number)
		window_end = window_start + window_size	# end of current half-bit-cell window (fractional sample number)
		window_adj = 0.0						# adjustment to window_end (in fractional samples)
		clock_cell = 'c'
		data_cell = 'd'
		clock_data = clock_cell					# current half-bit-cell window is clock_cell vs. data_cell
		v = 0									# 1 = edge in current window, 0 = no edge
		shift31 = 0								# 31-bit pattern shift register (of half-bit-cells)

		data_byte = 0							# 8-bit data byte shift register (of bit cells)
		bit_cnt = 0								# number of bits processed in current byte (0..8)
		byte_sync = False						# True = bit/byte-sync'd, False = not sync'd
		win_sync = False						# True = half-bit-cell window sync'd re clock_cell vs. data_cell ?

		last_interval = 0						# previous interval (in samples, 1..n)
		interval = 0							# current interval (in samples, 1..n)


		# --- Process all input data.

		while True:

			# Wait for leading edge (rising or falling) on channel 0.  Also handle
			# extra pulses on channel 1, and disable/suppress signal on channel 2.

			if self.rising_edge:
				(data_pin, extra_pin, suppress_pin) = self.wait([{0: 'r', 2: 'l'}, {1: 'r', 2: 'l'}])
			else:
				(data_pin, extra_pin, suppress_pin) = self.wait([{0: 'f', 2: 'l'}, {1: 'r', 2: 'l'}])

			# Display summary report on last annotation row.  Reporting
			# sample number must be on or before last leading edge.

			# Calculate interval since previous leading edge.

			last_interval = interval

			if self.last_samplenum is None:
				interval = int(bc10N)
			else:
				interval = self.samplenum - self.last_samplenum

			if self.last_samplenum is not None:
				interval_nsec = int(((interval * 1000) + (self.samplerateMSps / 2)) / self.samplerateMSps)

			self.chunks += 1
			self.Intrvls += 1

			# Inter-track quiet gap resets ID/Data record matching.

			if interval > self.samples30usec:
				self.IDlastAM = -1

			# Update averaged half-bit-cell window size if interval within tolerance.
			# Also display leading-edge to leading-edge annotation, showing starting
			# sample number, and interval in nsec.

			if self.encodingFM:
				if interval >= bc05L and interval <= bc05U:
					hbcpi = 1.0
				elif interval >= bc10L and interval <= bc10U:
					hbcpi = 2.0
				else:
					self.OoTI += 1
					hbcpi = 0.0
			else:		# MFM
				if interval >= bc10L and interval <= bc10U:
					hbcpi = 2.0
				elif interval >= bc15L and interval <= bc15U:
					hbcpi = 3.0
				elif interval >= bc20L and interval <= bc20U:
					hbcpi = 4.0
				else:
					self.OoTI += 1
					hbcpi = 0.0

			if hbcpi > 0.1:
				window_size_filter_accum -= (window_size * hbcpi)
				window_size_filter_accum += interval
				window_size = window_size_filter_accum / 32.0
				if self.last_samplenum is not None:
					self.put(self.last_samplenum, self.samplenum, self.out_ann,
							 [13, ['s%d i%dns' % (self.last_samplenum, interval_nsec), 'i%dns' % (interval_nsec)]])
			else:
				if self.last_samplenum is not None:
					self.put(self.last_samplenum, self.samplenum, self.out_ann,
							 [14, ['s%d i%dns OoTI' % (self.last_samplenum, interval_nsec)]])
					self.put(self.samplenum - 1, self.samplenum, self.out_ann, [15, ['Error', 'Err', 'E']])

			# --- Process half-bit-cell windows until current edge falls inside.

			while True:

				# Process half-bit-cell window with an edge in it.

				if self.samplenum >= window_start and self.samplenum < window_end:

					v = 1						# window value is '1'

					# Shift position of window to put edge closer to centre.

					window_adj = (self.samplenum - ((window_start + window_end) / 2.0)) / 1.75	#//DEBUG - use better algorithm?
					if window_adj > (window_size / 4.0):	#//DEBUG - use better algorithm?
						window_adj = window_size / 4.0
					window_end += window_adj

				# Edge fell in previous window, discard and resync.

				elif self.samplenum < window_start:

					self.fifo_wv[self.fifo_wp] += 1		# incr. number of leading edges in window
					self.EiPW += 1
					byte_sync = False
					shift31 = 0
					break

				# Process window with no edge in it.

				else:

					v = 0						# window value is '0'

					# end if

				# Shift current window value into lsb position of pattern shift register.

				shift31 = ((shift31 & 0x3FFFFFFF) << 1) + v

				# Display all MFM mC2h and mA1h prefix bytes to help with locating damaged records.

				win_start = int(round(window_start))
				win_end = int(round(window_end))

				if (not self.encodingFM) and self.dsply_pfx:
					if (shift31 & 0xFFFF) == 0x4489:
						self.put(win_start, win_end, self.out_ann, [12, ['A1']])
					elif (shift31 & 0xFFFF) == 0x5224:
						self.put(win_start, win_end, self.out_ann, [12, ['C2']])

				# Store start/end of current window and its value into FIFO.

				self.inc_fifo_wp()
				self.fifo_ws[self.fifo_wp] = win_start
				self.fifo_we[self.fifo_wp] = win_end
				self.fifo_wv[self.fifo_wp] = v

				# Not sync'd yet, look for sync pattern.
				# The FIFO must have exactly 33 entries in it.

				if (not byte_sync) and (self.fifo_cnt == 33):

					# Process FM patterns.

					if self.encodingFM:

						# FM ID Address Mark pattern found.

						if shift31 == 0x2AAAF57E:	# 00h,mFEh bytes
							data_byte = 0x1FE
							byte_sync = True
							win_sync = True

						# FM Data Address Mark pattern found.

						elif shift31 == 0x2AAAF56F:	# 00h,mFBh bytes
							data_byte = 0x1FB
							byte_sync = True
							win_sync = True

						elif shift31 == 0x2AAAF56A:	# 00h,mF8h bytes
							data_byte = 0x1F8
							byte_sync = True
							win_sync = True

						elif shift31 == 0x2AAAF56B:	# 00h,mF9h bytes
							data_byte = 0x1F9
							byte_sync = True
							win_sync = True

						elif shift31 == 0x2AAAF56E:	# 00h,mFAh bytes
							data_byte = 0x1FA
							byte_sync = True
							win_sync = True

						# FM Index Mark pattern found.

						elif shift31 == 0x2AAAF77A:	# 00h,mFCh bytes
							data_byte = 0x1FC
							byte_sync = True
							win_sync = True

					# Process MFM patterns.

					else:

						# MFM ID or Data Address Mark initial pattern found.

						if shift31 == 0x2AAA4489:	# initial 00h,mA1h prefix bytes
							data_byte = 0x1A1
							byte_sync = True
							win_sync = True

						# MFM Index Mark initial pattern found.

						elif shift31 == 0x2AAA5224:	# initial 00h,mC2h prefix bytes
							data_byte = 0x1C2
							byte_sync = True
							win_sync = True

					# Process and display (initial) mark pattern.

					if byte_sync:

						if self.encodingFM:
							self.process_byteFM(data_byte)
						else:
							self.process_byteMFM(data_byte)

						clock_data = data_cell
						bit_cnt = 0

				# Already sync'd, process next data bit.

				elif clock_data == data_cell:

					data_byte = ((data_byte & 0x7F) << 1) + v
					bit_cnt += 1

					# Process and display next complete data byte.
					# The FIFO must have exactly 17 entries in it.

					if bit_cnt == 8 and self.fifo_cnt == 17:

						# Process FM byte.

						if self.encodingFM:

							if self.process_byteFM(data_byte) == 0:
								bit_cnt = 0
							else:
								shift31 = 0
								byte_sync = False

						# Process MFM byte.

						else:

							if (shift31 & 0xFFFF) == 0x4489:	# mA1h prefix byte
								data_byte = 0x2A1
							elif (shift31 & 0xFFFF) == 0x5224:	# mC2h prefix byte
								data_byte = 0x2C2

							if self.process_byteMFM(data_byte) == 0:
								bit_cnt = 0
							else:
								shift31 = 0
								byte_sync = False

				# Display one half-bit-cell window annotation.	(If not sync'd,
				# display_bits() won't be called to pull entries from the FIFO,
				# but it needs to have 33-1+1 entries for self.process_byteFM/MFM().)

				if self.fifo_cnt >= 33:

					win_start = self.fifo_ws[self.fifo_rp]
					win_end = self.fifo_we[self.fifo_rp]
					win_val = self.fifo_wv[self.fifo_rp]
					self.inc_fifo_rp()

					if win_sync:
						if self.dsply_sn:
							if win_val > 1:
								self.put(win_start, win_end, self.out_ann,
										[0, ['%d d (extra pulse in win) s%d' % (win_val, win_start), '%d' % win_val]])
							else:
								self.put(win_start, win_end, self.out_ann,
										[3, ['%d d s%d' % (win_val, win_start), '%d' % win_val]])
						else:
							if win_val > 1:
								self.put(win_start, win_end, self.out_ann,
										[0, ['%d d (extra pulse in win)' % win_val, '%d' % win_val]])
							else:
								self.put(win_start, win_end, self.out_ann,
										[3, ['%d d' % win_val, '%d' % win_val]])
						win_sync = False
					else:
						if self.dsply_sn:
							if win_val > 1:
								self.put(win_start, win_end, self.out_ann,
										[0, ['%d (extra pulse in win) s%d' % (win_val, win_start), '%d' % win_val]])
							else:
								self.put(win_start, win_end, self.out_ann,
										[1, ['%d s%d' % (win_val, win_start), '%d' % win_val]])
						else:
							if win_val > 1:
								self.put(win_start, win_end, self.out_ann,
										[0, ['%d (extra pulse in win)' % win_val, '%d' % win_val]])
							else:
								self.put(win_start, win_end, self.out_ann,
										[1, ['%d' % win_val]])

				# Toggle clock vs. data state.

				if clock_data == data_cell:
					clock_data = clock_cell
				else:
					clock_data = data_cell

				# Calculate next half-bit-cell window location.

				window_start = window_end
				window_end += window_size

				# If edge processed in current window, get next edge.

				if v == 1:	break

				#--- end while


			# Store data for next round.

			self.last_samplenum = self.samplenum

			#--- end while