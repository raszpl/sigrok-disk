## ---------------------------------------------------------------------------
## FILE: decoders\mfm\pd.py
## PURPOSE: Decode floppy and hard disk FM, MFM and RLL pulse stream.
##
## Copyright (C) 2017 David C. Wiens <dcwiens@sardis-technologies.com>
## Copyright (c) 2025 MajenkoProjects
## Copyright (C) 2025 Rasz_pl <https://github.com/raszpl>
## Initial version created 2017-Mar-14.
## ---------------------------------------------------------------------------
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
from array import array
from copy import deepcopy
from types import SimpleNamespace
# ----------------------------------------------------------------------------
# Warning: Python 3.4 Enums are EXTREMELY SLOW. It's been "fixed" in Python 3.5
# such that enum attribute lookup is "only" 3-6x slower than normal, instead of 25-70x! Python 3.4:
# Direct Access d['key']: 3.3710 seconds
# Direct Enum Access d[enum.key]: 157.9954 seconds
# SimpleNamespace class.key access is almost same speed at string lookup
# ----------------------------------------------------------------------------

# Debug print for switching on/off all in one place
def print_(*args):
	pass
	#print(" ".join(map(str, args)))

# ----------------------------------------------------------------------------
# PURPOSE: Signal recoverable errors to DSView GUI and sigrok-cli output.
# PulseView sadly doesnt display those messages :(
# ----------------------------------------------------------------------------

class raise_exception(Exception):
	pass

# ----------------------------------------------------------------------------
# PURPOSE: Subclass and initialize the Decoder class.
# ----------------------------------------------------------------------------

class Decoder(srd.Decoder):
	api_version = 3
	id = 'mfm'
	name = 'MFM'
	longname = 'FM/MFM/RLL decoding'
	desc = 'Decode floppy and hard disk FM, MFM or RLL pulse stream.'
	license = 'gplv3+'
	inputs = ['logic']
	outputs = []
	tags = ['Disk', 'PC', 'Retro computing']
	channels = (
		{'id': 'data', 'name': 'Read data', 'desc': 'channel 0', 'idn':'dec_mfm_chan_data'},
	)
	optional_channels = (
		{'id': 'extra', 'name': 'Extra pulses', 'desc': 'channel 1', 'idn':'dec_mfm_chan_extra'},
		{'id': 'suppress', 'name': 'Suppress pulses', 'desc': 'channel 2', 'idn':'dec_mfm_chan_suppress'},
	)
	annotations = (
		('clk', 'clock'),		# clock half-bit-cell window
		('dat', 'data'),		# data half-bit-cell window
		('byt', 'byte'),
		('bit', 'bit'),
		('syn', 'sync'),
		('mrk', 'mark'),
		('rec', 'record'),
		('crc', 'crc'),
		('cre', 'crc error'),
		('rpt', 'report'),
		('pfx', 'prefix'),
		('pul', 'pulse'),
		('erp', 'bad pulse'),	# out-of-tolerance leading edge
		('erw', 'extra pulse'),	# bad half-bit-cell window
		('unk', 'unknown'),		# unknown half-bit-cell window in unsynced stream
		('erb', 'bad bit'),
		('err', 'error'),
	)
	binary = (
		('id', 'raw ID Records (Header data fields)'),
		('data', 'raw Data Records, order as on track'),
		('iddata', 'combined ID + Data Records, order as on track'),
		('idcrc', 'whole headers including Address Mark and crc'),
		('datacrc', 'whole data field including Address Mark and crc'),
		('tr', 'dgesswein/mfm transitions file format'),
		('ex', 'dgesswein/mfm extract file format'),
	)

	global ann, bnr
	ann = SimpleNamespace(**{key: idx for idx, (key, _) in enumerate(annotations)})
	bnr = SimpleNamespace(**{key: idx for idx, (key, _) in enumerate(binary)})

	annotation_rows = (
		('pulses', 'Pulses', (ann.pul, ann.erp,)),
		('windows', 'Windows', (ann.clk, ann.dat, ann.erw, ann.unk,)),	# half-bit-cell windows
		('prefixes', 'Prefixes', (ann.pfx,)),							# special MFM Synchronisation marks A1/C1
		('bits', 'Bits', (ann.erb, ann.bit,)),
		('bytes', 'Bytes', (ann.byt,)),
		('fields', 'Fields', (ann.syn, ann.mrk, ann.rec, ann.crc, ann.cre,)),
		('errors', 'Errors', (ann.err,)),
		('reports', 'Reports', (ann.rpt,)),
	)
	options = (
		{'id': 'leading_edge', 'desc': 'Leading edge',
			'default': 'rising', 'values': ('rising', 'falling')},
		{'id': 'data_rate', 'desc': 'Data rate (bps)',
			'default': '5000000', 'values': ('125000', '150000',
			'250000', '300000', '500000', '5000000', '7500000', '10000000')},
		{'id': 'format', 'desc': 'Encoding format. Pick preset or custom to define your own',
			'default': 'MFM', 'values': ('FM', 'MFM', 'RLL_Seagate', 'RLL_Adaptec', 'RLL_Adaptec4070', 'RLL_WD', 'RLL_OMTI', 'RLL_DTC7287_unknown', 'custom')},
		{'id': 'header_format', 'desc': 'Header format, defines length in bytes',
			'default': '4', 'values': ('3', '4', 'Seagate', 'OMTI', 'Adaptec', 'Adaptec4070', 'RLL_DTC7287_unknown')},
		{'id': 'sector_size', 'desc': 'Sector payload length in bytes',
			'default': 'auto', 'values': ('auto', '128', '256', '512', '1024', '2048', '4096', '8192', '16384')},
		{'id': 'header_crc_size', 'desc': 'Header field CRC bits',
			'default': '16', 'values': ('16', '32')},
		{'id': 'header_crc_poly', 'desc': 'Header field CRC Polynomial',
			'default': '0x1021'},
		{'id': 'header_crc_init', 'desc': 'Header field CRC init',
			'default': '0xffffffff'},
		{'id': 'data_crc_size', 'desc': 'Data field CRC bits',
			'default': '32', 'values': ('16', '32', '48', '56')},
		{'id': 'data_crc_poly', 'desc': 'Data field CRC Polynomial',
			'default': '0xA00805', 'values': ('0x1021', '0xA00805', '0x140a0445',
			'0x0104c981', '0x41044185', '0x181814503011', '0x140a0445000101')},
		{'id': 'data_crc_poly_custom', 'desc': 'Custom Data Polynomial (overrides above)',
			'default': ''},
		{'id': 'data_crc_init', 'desc': 'Data field CRC init',
			'default': '0xffffffffffffff'},
		{'id': 'time_unit', 'desc': 'Pulse time units/windows',
			'default': 'ns', 'values': ('ns', 'us', 'auto', 'window')},
		{'id': 'dsply_sn', 'desc': 'Display Windows (bit/clock) and Pulses (pul, erp) sample numbers',
			'default': 'no', 'values': ('yes', 'no')},
		{'id': 'report', 'desc': 'Display report after this field',
			'default': 'no', 'values': ('no', 'IAM', 'IDAM', 'DAM', 'DDAM')},
		{'id': 'report_qty', 'desc': 'Report every x Marks',
			'default': '9'},
		{'id': 'decoder', 'desc': 'Decoder',
			'default': 'PLL', 'values': ('PLL', 'legacy')},
		{'id': 'pll_sync_tolerance', 'desc': 'PLL: Initial tolerance when catching synchronization sequence',
			'default': '25%', 'values': ('15%', '20%', '25%', '33%', '50%')},
		{'id': 'pll_kp', 'desc': 'PLL: PI Filter Kp (proportinal)',
			'default': '0.5'},
		{'id': 'pll_ki', 'desc': 'PLL: PI Filter Ki (integral)',
			'default': '0.0005'},
		{'id': 'dsply_pfx', 'desc': 'Legacy decoder: Display all MFM prefix bytes.',
			'default': 'no', 'values': ('yes', 'no')},

		{'id': 'custom_encoder_limits', 'desc': 'Custom encoder: coding',
			'default': 'RLL', 'values': ('FM', 'MFM', 'RLL')},
		{'id': 'custom_encoder_codemap', 'desc': 'Custom encoder: codemap',
			'default': 'IBM', 'values': ('FM/MFM', 'IBM', 'WD')},
		{'id': 'custom_encoder_sync_pulse', 'desc': 'Custom encoder: sync_pulse',
			'default': 4, 'values': (2, 3, 4)},
		{'id': 'custom_encoder_sync_marks', 'desc': 'Custom encoder: sync_marks. Example: [6, 8, 3], [5, 3, 8, 3]',
			'default': ''},
		{'id': 'custom_encoder_shift_index', 'desc': 'Custom encoder: shift_index. Example: 11 or 11, 11',
			'default': ''},
		{'id': 'custom_encoder_IDData_mark', 'desc': 'Custom encoder: IDData_mark. Example: 0xA1',
			'default': ''},
		{'id': 'custom_encoder_ID_mark', 'desc': 'Custom encoder: ID_mark',
			'default': ''},
		{'id': 'custom_encoder_Data_mark', 'desc': 'Custom encoder: Data_mark',
			'default': ''},
		{'id': 'custom_encoder_ID_prefix_mark', 'desc': 'Custom encoder: ID_prefix_mark',
			'default': ''},
		{'id': 'custom_encoder_nop_mark', 'desc': 'Custom encoder: nop_mark',
			'default': ''},
		{'id': 'custom_encoder_nop_A1_mark', 'desc': 'Custom encoder: nop_A1_mark',
			'default': ''},
	)

	# build list of valid options, we will be verifying sigrok-cli command line input
	options_valid = {item['id']: item['values'] for item in options if 'values' in item}

	class Messages(object):
		class MsgTemplate(object):
			__slots__ = ("code", "_template", "_rest", "variant")
			def __init__(self, code, variants):
				self.code = code
				self.variant = [code, variants]
				self._template = variants[0]
				self._rest = variants[1:]

			def __call__(self, *args):
				t = self._template
				if args:
					return [self.code, [self._template % args] + self._rest]
				else:
					return self.variant

		def __init__(self, definitions):
			for name, val in definitions.items():
				tmpl = self.MsgTemplate(*val)
				setattr(self, name, tmpl)

	global message, messageD
	# messageD.xxx are dynamic, slow so used sporadically, makes code more readable
	messageD = Messages({
		'sync'		: (ann.syn, ['Sync pattern %d bytes', 'Sync', 'S']),
		'gap'		: (ann.mrk, ['Gap %d bytes', 'Gap', 'G']),
		'pulse'		: (ann.erw, ['%d%s (extra pulse in win) s%d', 'Extra Pulse', 'EP']),
		'report'	: (ann.rpt, ['Summary: IAM=%d, IDAM=%d, DAM=%d, DDAM=%d, CRC_OK=%d, CRC_err=%d, EiPW=%d, CkEr=%d, OoTI=%d/%d']),
	})
	# message.xxx is static, fast and readable
	message = SimpleNamespace(
		error		= [ann.err, ['Error', 'Err', 'E']],
		errorOoTIs	= [ann.err, ['Pulse too short Error', 'OoTI Error', 'Err', 'E']],
		errorOoTIl	= [ann.err, ['Pulse too long Error', 'OoTI Error', 'Err', 'E']],
		errorUnkByte= [ann.err, ['Unknown byte Error', 'Error', 'Err', 'E']],
		errorClock	= [ann.err, ['Clock Error', 'Error', 'Err', 'E']],
		sync		= [ann.mrk, ['Sync pattern', 'Sync', 'S']],
		gap			= [ann.mrk, ['Gap', 'Gap', 'G']],
		iam			= [ann.mrk, ['Index Mark', 'IAM', 'I']],
		idam		= [ann.mrk, ['ID Address Mark', 'IDAM', 'M']],
		dam			= [ann.mrk, ['Data Address Mark', 'Data Mark', 'DAM', 'M']],
		ddam		= [ann.mrk, ['Deleted Data Address Mark', 'Deleted Data Mark', 'DDAM', 'M']],
		drec		= [ann.rec, ['Data Record', 'Drec', 'R']],
		prefixA1	= [ann.pfx, ['A1']],
		prefixC2	= [ann.pfx, ['C2']],
	)

	global state, field, coding
	state = SimpleNamespace(
		first_C2h_prefix	= 0,
		second_C2h_prefix	= 1,
		third_C2h_prefix	= 2,
		Index_Mark			= 3,
		first_A1h_prefix	= 4,
		second_A1h_prefix	= 5,
		third_A1h_prefix	= 6,
		IDData_Address_Mark	= 7,
		ID_Address_Mark		= 8,
		Data_Address_Mark	= 9,
		ID_Record			= 10,
		ID_Record_CRC		= 11,
		Data_Record			= 12,
		Data_Record_CRC		= 13,
		first_Gap_Byte		= 14,
		sync_mark			= 15,
	)

	field = SimpleNamespace(
		Index_Mark			= 1,
		ID_Address_Mark		= 2,
		Data_Address_Mark	= 3,
		Deleted_Data_Mark	= 4,
		ID_Record			= 5,
		Data_Record			= 6,
		CRC_Ok				= 7,
		CRC_Error			= 8,
		Unknown_Byte		= 9,
		Sync				= 10,
		Gap					= 11,
	)

	coding = SimpleNamespace(
		FM					= 0,
		MFM					= 1,
		RLL_Seagate			= 2,
		RLL_Adaptec 		= 3,
		RLL_Adaptec4070		= 4,
		RLL_WD				= 5,
		RLL_OMTI			= 6,
		RLL_DTC7287_unknown	= 7,
		custom				= 8,

		FM_MFM				= 9,
		RLL					= 10,
		RLL_IBM				= 11,
		GCR					= 12,
		GCR_IBM				= 13,
		GCR_CBM				= 14,
	)

	header_format = {
			'3': (3, 'decode_id_rec_3byte'),
			'4': (4, 'decode_id_rec_4byte'),
			'Seagate': (4, 'decode_id_rec_4byte_Seagate'),
			'OMTI': (4, 'decode_id_rec_4byte_OMTI'),
			'Adaptec': (4, 'decode_id_rec_4byte_Adaptec'),
			'Adaptec4070': (4, 'decode_id_rec_4byte_Adaptec4070'),
			'RLL_DTC7287_unknown': (3, 'decode_id_rec_3byte_RLL_DTC7287'),
	}

	encoding_limits = {
		coding.FM:	(1, 2),				# (0,1) RLL
		coding.GCR:	(1, 3),				# (0,2) RLL
		coding.MFM:	(2, 3, 4),			# (1,3) RLL
		coding.RLL:	(3, 4, 5, 6, 7, 8),	# (2,7) RLL
	}

	decoding_codemap = {
		coding.FM_MFM: {
			'11': '1',
			'10': '0',
			'01': '1',
			'00': '0',
		},
		coding.GCR_IBM: {
			'11001': '0000',
			'11011': '0001',
			'10010': '0010',
			'10011': '0011',
			'11101': '0100',
			'10101': '0101',
			'10110': '0110',
			'10111': '0111',
			'11010': '1000',
			'01001': '1001',
			'01010': '1010',
			'01011': '1011',
			'11110': '1100',
			'01101': '1101',
			'01110': '1110',
			'01111': '1111',
		},
		coding.GCR_CBM: {
			'01010': '0000',
			'01011': '0001',
			'10010': '0010',
			'10011': '0011',
			'01110': '0100',
			'01111': '0101',
			'10110': '0110',
			'10111': '0111',
			'01001': '1000',
			'11001': '1001',
			'11010': '1010',
			'11011': '1011',
			'01101': '1100',
			'11101': '1101',
			'11110': '1110',
			'10101': '1111',
		},
		coding.RLL_IBM: {
			'1000': '11',
			'0100': '10',
			'100100': '010',
			'001000': '011',
			'000100': '000',
			'00100100': '0010',
			'00001000': '0011'
		},
		coding.RLL_WD: {
			'1000': '11',
			'0100': '10',
			'100100': '000',
			'000100': '010',
			'001000': '011',
			'00100100': '0010',
			'00001000': '0011'
		}
	}

	#encoding_codemap = {
	#	coding.GCR_IBM: {
	#		'0000':	'11001',
	#		'0001':	'11011',
	#		'0010':	'10010',
	#		'0011':	'10011',
	#		'0100':	'11101',
	#		'0101':	'10101',
	#		'0110':	'10110',
	#		'0111':	'10111',
	#		'1000':	'11010',
	#		'1001':	'01001',
	#		'1010':	'01010',
	#		'1011':	'01011',
	#		'1100':	'11110',
	#		'1101':	'01101',
	#		'1110':	'01110',
	#		'1111':	'01111',
	#	},
	#	coding.RLL_IBM = {
	#		'11':	'1000',
	#		'10':	'0100',
	#		'011':	'001000',
	#		'000':	'000100',
	#		'010':	'100100',
	#		'0011':	'00001000',
	#		'0010':	'00100100'
	#	}
	#	coding.RLL_WD = {
	#		'11':	'1000',
	#		'10':	'0100',
	#		'011':	'001000',
	#		'010':	'000100',
	#		'000':	'100100',
	#		'0011':	'00001000',
	#		'0010':	'00100100'
	#}

	# format_table holds data for configuring process_byte() and SimplePLL State Machines
	#
	# limits: pulse widths outside reset PLL
	# codemap: code translation map
	# sync_pulse: anything other halts PLLstate.locking phase and triggers reset_pll()
	# sync_marks: used by PLLstate.scanning_sync_mark
	# shift_index: every sync_mark entry has its own offset defining number of valid
	#	halfbit windows already shifted in when sync_marks is matched. Define one common
	#	value or provide list of values for every sync_marks entry.
	# IDData_mark: replaces A1
	# ID_mark: skip straight to decoding Header
	# Data_mark: skip straight to decoding Data
	# ID_prefix_mark: Overrides the meaning of following IDData_mark to mean ID_mark
	# nop_mark: inert mark
	# nop_A1_mark: inert mark that sets A1. Works like IDData_mark but uses custom ID_mark/Data_mark instead of jumping to hardcoded ID/DATA markers
	format_table = {
		coding.FM: {
			'limits_key': coding.FM,
			'codemap_key': coding.FM_MFM,
			'sync_pulse': 2,
			'sync_marks': [[1, 1, 1, 2, 2, 2, 1, 1, 1, 1, 1, 2], [1, 1, 1, 2, 2, 2, 1, 2, 1, 1, 1], [1, 1, 1, 2, 1, 1, 2, 1, 1, 1, 2, 2]],
			'shift_index': [17],
			'ID_mark': [0xFE],
			'Data_mark': [0xFB]
		},
		coding.MFM: {
			'limits_key': coding.MFM,
			'codemap_key': coding.FM_MFM,
			'sync_pulse': 2,
			'sync_marks': [[3, 4, 3, 4, 3], [3, 2, 3, 4, 3, 4]],
			'shift_index': [16, 18],
			'IDData_mark': [0xA1]
		},
		# Seagate ST11M/21M
		coding.RLL_Seagate: {
			'limits_key': coding.RLL,
			'codemap_key': coding.RLL_IBM,
			'sync_pulse': 3,
			'sync_marks': [[4, 3, 8, 3], [5, 6, 8, 3]],
			'shift_index': [18],
			'IDData_mark': [0xA1],
			'ID_prefix_mark': [0x1E],
			'nop_mark': [0xDE]
		},
		# Adaptec ACB-237x, ACB-4070
		coding.RLL_Adaptec: {
			'limits_key': coding.RLL,
			'codemap_key': coding.RLL_IBM,
			'sync_pulse': 3,
			'sync_marks': [[4, 3, 8, 3], [5, 6, 8, 3], [8, 3]],
			'shift_index': [18],
			'ID_mark': [0xA1],
			'IDData_mark': [0xA0],
			'nop_mark': [0x1E, 0x5E, 0xDE]
		},
		# Adaptec ACB-237x, ACB-4070
		coding.RLL_Adaptec4070: {
			'limits_key': coding.RLL,
			'codemap_key': coding.RLL_IBM,
			'sync_pulse': 3,
			'sync_marks': [[4, 3, 8, 3], [5, 6, 8, 3], [8, 3]],
			'shift_index': [18],
			'ID_mark': [0xA1],
			'Data_mark': [0xA0],
			'nop_mark': [0x1E, 0x5E, 0xDE]
		},
		coding.RLL_WD: {
			'limits_key': coding.RLL,
			'codemap_key': coding.RLL_WD,
			'sync_pulse': 3,
			'sync_marks': [[8, 3], [5, 8, 3], [7, 8, 3]],
			'shift_index': [12],
			'IDData_mark': [0xF0],
		},
		# OMTI-8247
		coding.RLL_OMTI: {
			'limits_key': coding.RLL,
			'codemap_key': coding.RLL_IBM,
			'sync_pulse': 4,
			'sync_marks': [[6, 8, 3, 3], [5, 3, 8, 3, 3]],
			'shift_index': [17],
			'IDData_mark': [0x62],
		},
		# PLACEHOLDER! Weird format, almost as if it uses custom decoding_codemap? are those sync marks ESDI like?
		# XORed with 0xFF?
		# Data Technology Corporation DTC7287
		coding.RLL_DTC7287_unknown: {
			'limits_key': coding.RLL,
			'codemap_key': coding.RLL_WD,
			'sync_pulse': 4,
			'sync_marks': [
				[5, 4, 4, 4, 4, 3, 8, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 6, 6, 7],
				[5, 4, 4, 4, 4, 3, 8, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 6, 6, 7],
				[5, 4, 4, 4, 4, 3, 8, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 6, 6, 7]],
			'shift_index': [18],
			'ID_mark': [0x90, 0x91, 0x92, 0x93, 0x95, 0x96, 0x97],
			'Data_mark': [2, 3],
			'nop_mark': [0x36, 0x83],
		},
		# XORed with 0xFF
		#coding.RLL_DTC7287_unknown: {
		#	'limits_key': coding.RLL,
		#	'codemap_key': coding.RLL_WD,
		#	'sync_pulse': 4,
		#	'sync_marks': [
		#		[5, 4, 4, 4, 4, 3, 8, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 6, 6, 7],
		#		[5, 4, 4, 4, 4, 3, 8, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 6, 6, 7],
		#		[5, 4, 4, 4, 4, 3, 8, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 6, 6, 7]],
		#	'shift_index': [18],
		#	'ID_mark': [0x6F, 0x6E, 0x6D, 0x6C, 0x6A, 0x69, 0x68],
		#	'Data_mark': [0xFD, 0xFC],
		#	'nop_mark': [0xC9, 0x7C],
		#},
	}

	# ------------------------------------------------------------------------
	# PURPOSE: Class constructor/initializer.
	# ------------------------------------------------------------------------

	def __init__(self):
		self.reset()

	def reset(self):
		# Initialize pre-defined variables.
		self.samplerate = None
		self.last_samplenum = None
		self.chunks = 0

		# Define (and initialize) various custom variables.
		self.byte_start = 0			# start of byte (sample number)
		self.byte_end = 0			# end of byte (sample number)
		self.field_start = 0		# start of field (sample number)
		self.pb_state = state.sync_mark # init process_byte() State Machine
		self.byte_cnt = 0			# number of bytes left to process in field (1024/512/256/128/4/2..0)
		self.IDcyl = 0				# cylinder number field in ID record (0..244)
		self.IDsid = 0				# side number field in ID record (0..1)
		self.IDsec = 0				# sector number field in ID record (0..244)
		self.IDlenc = 0				# sector length code field in ID record (0..3)
		self.IDlenv = 0				# sector length (from code field) in ID record (128/256/512/1024)

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
		self.crc_accum = 0

		self.report_start = 0
		self.reports_called = 0

		# used by process_byte() for CRC calculations.
		self.A1 = []
		self.IDmark = []
		self.DRmark = []

	# ------------------------------------------------------------------------
	# PURPOSE: Various initialization when decoder started.
	# ------------------------------------------------------------------------

	def start(self):
		self.out_ann = self.register(srd.OUTPUT_ANN)
		self.out_binary = self.register(srd.OUTPUT_BINARY)
		#self.out_meta = self.register(srd.OUTPUT_META, meta=(int, 'meta', 'meta meta?'))

		# Validate user provided command-line options.
		for key, value in self.options.items():
			if key in self.options_valid:
				if value not in self.options_valid[key]:
					print("Error: '" + value + "' is not an allowed value for '" + key + "'.")
					print('Allowed values are: {' + ', '.join(self.options_valid[key]) + '}.')
					raise raise_exception("Error: '" + value + "' is not an allowed value for '" + key + "'. Allowed values are: {" + ', '.join(self.options_valid[key]) + '}.')

		# Initialize user options.
		self.rising_edge = True if self.options['leading_edge'] == 'rising' else False
		self.data_rate = float(self.options['data_rate'])
		self.format = getattr(coding, self.options['format'])
		self.header_size, header_format = self.header_format[self.options['header_format']]
		self.decode_id_rec = getattr(self, header_format)
		self.IDrec = bytearray(self.header_size)	# ID record (3-4 bytes)
		self.sector_size = 0 if self.options['sector_size'] == 'auto' else int(self.options['sector_size'])
		self.DRrec = bytearray(self.sector_size)	# Data record (128-16384 bytes)
		self.sector_size_auto = True if self.options['sector_size'] == 'auto' else False
		self.header_crc_size = int(self.options['header_crc_size'])
		self.header_crc_bytes = self.header_crc_size // 8
		self.header_crc_mask = (1 << self.header_crc_size) -1
		self.header_crc_poly = int(self.options['header_crc_poly'], 0) & self.header_crc_mask
		self.header_crc_init = int(self.options['header_crc_init'], 0) & self.header_crc_mask
		self.data_crc_size = int(self.options['data_crc_size'])
		self.data_crc_bytes = self.data_crc_size // 8
		self.data_crc_mask = (1 << self.data_crc_size) -1
		self.data_crc_poly = int(self.options['data_crc_poly'], 0)
		self.data_crc_init = int(self.options['data_crc_init'], 0) & self.data_crc_mask
		if self.options['data_crc_poly_custom']:
			self.data_crc_poly = int(self.options['data_crc_poly_custom'], 0) & self.data_crc_mask
		self.header_crc_table = [0] * 256
		self.data_crc_table = [0] * 256

		self.time_unit = self.options['time_unit']
		self.show_sample_num = True if self.options['dsply_sn'] == 'yes' else False

		self.report = {	'no':	'no',
						'IAM':	field.Index_Mark,
						'IDAM':	field.ID_Address_Mark,
						'DAM':	field.Data_Address_Mark,
						'DDAM':	field.Deleted_Data_Mark,
					}[self.options['report']]
		self.report_qty = int(self.options['report_qty'])
		self.report_start = 0
		self.reports_called = 0

		self.decoder_legacy = True if self.options['decoder'] == 'legacy' else False
		self.pll_kp = float(self.options['pll_kp'])
		self.pll_ki = float(self.options['pll_ki'])
		self.pll_sync_tolerance = int(self.options['pll_sync_tolerance'][:-1]) * 0.01
		self.dsply_pfx = True if self.options['dsply_pfx'] == 'yes' else False

		class helper_mock_all:
			# Data mocking helper, pretends to contain all of the items for the 'in' operator.
			def __contains__(self, item):
				# handle 'if val in ...'
				return True
			def __str__(self):
				# handle print(...)
				return '*'
			def __repr__(self):
				# what to show in REPL/debugger
				return "<helper_mock_all (matches all, prints as '*')>"

		# sigrok-cli command line input doesnt support "" escaped strings nor commas.
		# Have to resort to stupid parsing tricks:
		#  '8-3-5_5-8-3-5_7-8-3-5' to [[8, 3, 5], [5, 8, 3, 5], [7, 8, 3, 5]]
		#  '8-3-5' to [[8, 3, 5]]
		# Also accept various formats thru the GUI like:
		#  '8,3,5' to [[8, 3, 5]]
		#  [8, 3, 5], [5, 8, 3, 5] to [[8, 3, 5], [5, 8, 3, 5]]
		def helper_list_of_lists(s):
			s = s.strip().replace(' ', '')
			if any(c in s for c in '[,]'):
				s = s.replace('],[', '_').replace('][', '_').replace('[', '').replace(']', '').replace(',', '-')
			return [[int(x, 0) for x in part.split('-') if x] for part in s.split('_') if part]

		# custom_encoder_ marks and index are single lists, reuse above code for parsing then strip outer []
		# Supports data mocking, entering * wildcard will match all 'in' operations
		def helper_list(s):
			if '*' in s:
				return helper_mock_all()
			s = helper_list_of_lists(s)
			return s[0] if len(s) == 1 else []

		if self.format == coding.custom:
			format_current = {
				'limits_key':		{	'FM':	coding.FM,
										'MFM':	coding.MFM,
										'RLL':	coding.RLL,
									}[self.options['custom_encoder_limits']],
				'codemap_key':		{	'FM/MFM':	coding.FM_MFM,
										'IBM':		coding.RLL_IBM,
										'WD':		coding.RLL_WD,
									}[self.options['custom_encoder_codemap']],
				'sync_pulse':		self.options['custom_encoder_sync_pulse'],
				'sync_marks':		helper_list_of_lists(self.options['custom_encoder_sync_marks']),
				'shift_index':		helper_list(self.options['custom_encoder_shift_index']),
				'IDData_mark':		helper_list(self.options['custom_encoder_IDData_mark']),
				'ID_mark':			helper_list(self.options['custom_encoder_ID_mark']),
				'Data_mark':		helper_list(self.options['custom_encoder_Data_mark']),
				'ID_prefix_mark':	helper_list(self.options['custom_encoder_ID_prefix_mark']),
				'nop_mark':			helper_list(self.options['custom_encoder_nop_mark']),
				'nop_A1_mark':			helper_list(self.options['custom_encoder_nop_A1_mark']),
			}
			if format_current['limits_key'] in [coding.FM, coding.MFM]:
				format_current['codemap_key'] = coding.FM_MFM
		else:
			format_current = {
				'IDData_mark':		[],
				'ID_mark':			[],
				'Data_mark':		[],
				'ID_prefix_mark':	[],
				'nop_mark':			[],
				'nop_A1_mark':		[],
			}
			format_current.update(deepcopy(self.format_table[self.format]))
			# Support nop_mark * wildcard for reverse engineering new formats.
			if '*' in format_current['nop_mark']:
				format_current['nop_mark'] = helper_mock_all()

		format_current['limits'] = self.encoding_limits[format_current['limits_key']]
		format_current['codemap'] = self.decoding_codemap[format_current['codemap_key']]
		format_current['format'] = self.format

		# Let user define just one common shift_index for all sync_marks.
		# Detect this case and automagically populate matching number of slots.
		# Correct offset by subtracting last sync_marks pulse because PLLstate.decoding
		# adds self.halfbit_cells before processing byte.
		if len(format_current['shift_index']) == 1:
			format_current['shift_index'] = [format_current['shift_index'][0] - format_current['sync_marks'][0][-1]] * len(format_current['sync_marks'])
		elif len(format_current['sync_marks']) != len(format_current['shift_index']):
			raise raise_exception('Mistmatched number of shift_index defined. Requires either one common or equal number to sync_marks variants.')
		else:
			for i in range (0, len(format_current['sync_marks'])):
				format_current['shift_index'][i] = format_current['shift_index'][i] - format_current['sync_marks'][i][-1]
		self.format_current = SimpleNamespace(**format_current)

	# ------------------------------------------------------------------------
	# PURPOSE: Get the data sample rate entered by the user.
	# ------------------------------------------------------------------------

	def metadata(self, key, value):
		if key == srd.SRD_CONF_SAMPLERATE:
			self.samplerate = value
			self.samplerateMSps = self.samplerate / 1000000.0

	# ------------------------------------------------------------------------
	# PLL
	# ------------------------------------------------------------------------

	class SimplePLL:
		global PLLstate
		PLLstate = SimpleNamespace(
			locking				= 0,
			scanning_sync_mark	= 1,
			decoding			= 2,
		)
		__slots__ = ('cells_allowed_max', 'cells_allowed_min', 'code_0b000100', 'code_0b100100', 'decode', 'format', 'format_current', 'halfbit', 'halfbit_cells', 'halfbit_nom', 'halfbit_nom05', 'halfbit_nom15', 'integrator', 'ki', 'kp', 'last_last_samplenum', 'last_samplenum', 'limits_key', 'owner', 'phase_ref', 'pll_sync_tolerance', 'pulse_ticks', 'ring_ptr', 'ring_size', 'ring_we', 'ring_ws', 'ring_wv', 'shift', 'shift_byte', 'shift_decoded', 'shift_decoded_1', 'shift_decoded_s', 'shift_index', 'state', 'sync_lock_count', 'sync_lock_threshold', 'sync_marks', 'sync_marks_len', 'sync_marks_try', 'sync_pulse', 'sync_start', 'unsync_after_decode', 'codemap')

		def __init__(self, owner, halfbit_ticks, kp, ki, pll_sync_tolerance, format_current):
			self.owner = owner
			self.halfbit_nom = halfbit_ticks
			self.halfbit_nom05 = 0.5 * halfbit_ticks
			self.halfbit_nom15 = 1.5 * halfbit_ticks
			self.kp = kp
			self.ki = ki

			self.format_current = format_current
			self.format = format_current.format
			self.limits_key = format_current.limits_key
			self.codemap = format_current.codemap
			self.code_0b000100 = {
				coding.FM_MFM: 0,
				coding.RLL_IBM: 0,
				coding.RLL_WD: 2,
			}[format_current.codemap_key]
			self.code_0b100100 = {
				coding.FM_MFM: 0,
				coding.RLL_IBM: 2,
				coding.RLL_WD: 0,
			}[format_current.codemap_key]
			self.decode = {
				coding.FM_MFM: self.fm_mfm_decode,
				coding.RLL_IBM: self.rll_decode,
				coding.RLL_WD: self.rll_decode,
			}[format_current.codemap_key]
			self.sync_pulse = format_current.sync_pulse
			# Standard in literature seems to be 16 bit transitions (32 halfbit windows) as enough to lock PLO
			self.sync_lock_threshold = round(32 / self.sync_pulse)
			# pll_sync_tolerance: fractional percentage of tolerated deviations during initial PLL sync lock
			self.pll_sync_tolerance = halfbit_ticks * pll_sync_tolerance
			self.cells_allowed_min = min(format_current.limits)
			self.cells_allowed_max = max(format_current.limits)

			self.sync_marks = self.format_current.sync_marks
			self.sync_marks_len = len(self.sync_marks)

			# Ring buffer for storing info on individual halfbit windows, used by annotate_bits()
			# We need 16 halfbit windows + max shift_index possible (14+8) so we can rewind to
			# annotate already shifted data at the moment of Sync Mark match. Hardcoded for now
			# with safe margin.
			self.ring_ptr = 0
			self.ring_size = 40											# in halfbit windows
			self.ring_wv = [(0, 0, 0) for _ in range(self.ring_size)]

			# PLL state
			self.state = PLLstate.locking
			self.phase_ref = 0				# float: reference sample for half-bit 0
			self.halfbit = halfbit_ticks	# current half-bit estimate
			self.halfbit_cells = 0
			self.integrator = 0.0
			self.sync_lock_count = 0
			self.sync_marks_try = []
			self.unsync_after_decode = False
			self.sync_start = None
			self.shift = 0
			self.shift_byte = 0
			self.shift_decoded = 0
			self.shift_decoded_s = ''
			self.shift_decoded_1 = 0
			self.shift_index = 0
			self.pulse_ticks = 0
			self.last_samplenum = 0
			self.last_last_samplenum = 0

		def ring_write(self, win_start, win_end, value):
			self.ring_ptr = (self.ring_ptr + 1) % self.ring_size
			self.ring_wv[self.ring_ptr] = (win_start, win_end, value)

		def ring_read_offset(self, offset):
			return self.ring_wv[(self.ring_ptr + offset) % self.ring_size]

		def reset_pll(self):
			print_('pll reset_pll', self.last_samplenum)
			self.phase_ref = 0
			self.halfbit = self.halfbit_nom
			self.integrator = 0.0

			self.state = PLLstate.locking
			self.sync_lock_count = 0
			self.sync_marks_try = []
			self.unsync_after_decode = False
			self.sync_start = None
			self.shift = 0
			self.shift_decoded = 0
			self.shift_decoded_s = ''
			self.shift_decoded_1 = 0
			# reset Decoder variables directly FIXME: mixing contexts is UGLY and bad
			self.owner.pb_state = state.sync_mark
			self.owner.A1 = []
			self.owner.IDmark = []
			self.owner.DRmark = []

		def fm_mfm_decode(self):
			# Pseudo SWAR, same speed as LUT in python 3.4
			self.shift_index -= 16
			shift_byte = (self.shift >> self.shift_index) & 0x5555
			# compress pairs
			shift_byte = (shift_byte + (shift_byte >> 1)) & 0x3333
			# compress nibbles
			shift_byte = (shift_byte + (shift_byte >> 2)) & 0x0F0F
			# final packed byte
			self.shift_byte = (shift_byte + (shift_byte >> 4)) & 0x00FF
			return True

		def rll_decode(self):
			top_bits = 0
			while True:
				#print(bin(self.shift & ((1 << self.shift_index) - 1))[2:].zfill(self.shift_index), self.shift_index, self.shift_decoded_1, bin(self.shift_decoded)[2:].zfill(self.shift_decoded_1), 'rll_decode w')
				if self.shift_decoded_1 >= 16:
					self.shift_decoded_1 -= 16
					self.shift_byte = (self.shift_decoded >> (self.shift_decoded_1//2)) & 0xff
					self.shift_decoded &= 0xF
					return True

				elif self.shift_index >= 8:
					top_bits = (self.shift >> self.shift_index - 8) & 0xff
					if top_bits == 0b00100100:
						self.shift_decoded = (self.shift_decoded << 4) + 0b0010
						self.shift_decoded_1 += 8
						self.shift_index -= 8
						continue

					elif top_bits == 0b00001000:
						self.shift_decoded = (self.shift_decoded << 4) + 0b0011
						self.shift_decoded_1 += 8
						self.shift_index -= 8
						continue

					top_bits = top_bits & 0b11111100
					if top_bits == 0b10010000:
						self.shift_decoded = (self.shift_decoded << 3) + self.code_0b100100
						self.shift_decoded_1 += 6
						self.shift_index -= 6
						continue

					elif top_bits == 0b00100000:
						self.shift_decoded = (self.shift_decoded << 3) + 0b011
						self.shift_decoded_1 += 6
						self.shift_index -= 6
						continue

					elif top_bits == 0b00010000:
						self.shift_decoded = (self.shift_decoded << 3) + self.code_0b000100
						self.shift_decoded_1 += 6
						self.shift_index -= 6
						continue

					top_bits = top_bits & 0b11110000
					if top_bits == 0b10000000:
						self.shift_decoded = (self.shift_decoded << 2) + 0b11
						self.shift_decoded_1 += 4
						self.shift_index -= 4
						continue

					elif top_bits == 0b01000000:
						self.shift_decoded = (self.shift_decoded << 2) + 0b10
						self.shift_decoded_1 += 4
						self.shift_index -= 4
						continue

					# TODO: figure out a way to send signal about error upstream to try ECC correction
					#print("ERROR: no matches, skip whole byte")
					self.shift_index -= 16 - self.shift_decoded_1
					self.shift_decoded_1 = 0
					return False

				elif self.shift_index >= 6:
					top_bits = (self.shift >> self.shift_index - 6) & 0b111111
					if top_bits == 0b100100:
						self.shift_decoded = (self.shift_decoded << 3) + self.code_0b100100
						self.shift_decoded_1 += 6
						self.shift_index -= 6
						continue

					elif top_bits == 0b001000:
						self.shift_decoded = (self.shift_decoded << 3) + 0b011
						self.shift_decoded_1 += 6
						self.shift_index -= 6
						continue

					elif top_bits == 0b000100:
						self.shift_decoded = (self.shift_decoded << 3) + self.code_0b000100
						self.shift_decoded_1 += 6
						self.shift_index -= 6
						continue

					top_bits = top_bits & 0b111100
					if top_bits == 0b100000:
						self.shift_decoded = (self.shift_decoded << 2) + 0b11
						self.shift_decoded_1 += 4
						self.shift_index -= 4
						continue

					elif top_bits == 0b010000:
						self.shift_decoded = (self.shift_decoded << 2) + 0b10
						self.shift_decoded_1 += 4
						self.shift_index -= 4
						continue

				elif self.shift_index >= 4:
					top_bits = (self.shift >> self.shift_index - 4) & 0b1111
					if top_bits == 0b1000:
						self.shift_decoded = (self.shift_decoded << 2) + 0b11
						self.shift_decoded_1 += 4
						self.shift_index -= 4
						continue

					elif top_bits == 0b0100:
						self.shift_decoded = (self.shift_decoded << 2) + 0b10
						self.shift_decoded_1 += 4
						self.shift_index -= 4
						continue

				return False
			return False

		def rll_decode_string(self):
			RLL_TABLE = self.codemap
			shift_win = self.shift & (2 ** self.shift_index -1)

			#print_('RLL_1', bin(self.shift)[1:], self.shift_index, bin(shift_win)[2:].zfill(self.shift_index))
			binary_str = bin(shift_win)[2:].zfill(self.shift_index)
			binary_str_len = len(binary_str)
			decoded = self.shift_decoded_s
			i = 0
			while len(decoded) < 8:
				#print_('RLL input', bin(shift_win)[1:], binary_str, self.shift_index, self.shift_decoded_11, self.shift_decodedd)
				matched = False
				for pattern_length in [8, 6, 4]:
					if i + pattern_length <= binary_str_len:
						pattern = binary_str[i:i + pattern_length]
						if pattern in RLL_TABLE:
							decoded += RLL_TABLE[pattern]
							i += pattern_length
							self.shift_index -= pattern_length
							self.shift_decoded_1 += pattern_length
							#print_("RLL() decoded:", decoded, 'raw:', pattern, 'match:', RLL_TABLE[pattern], self.shift_index, self.shift_decoded_11)
							matched = True
							break
				if not matched:
					if binary_str_len - i > 7:
						# TODO: Emit whatever and signal upstream we got decoder fail
						# but try to keep synced and handle bad data upstream using ECC?
						# For now just raise exception? or not
						#print_("rll_decode catastrophic fail, Max codeword length reached without match, resetting!", self.shift_decoded_1, binary_str_len, i, decoded, self.codemap_key, binary_str, pattern)
						#raise raise_exception("rll_decode catastrophic fail! Max codeword length reached without match. Exception raised.")
						print_("RLL not matched and binary_str_len - i > 7", binary_str[i:], decoded, i)
						self.reset_pll()
						return False
					#print_("RLL not matched", binary_str[i:], decoded, i)
					self.shift_decoded_s = decoded
					return False

			#print_('RLL_shift', bin(self.shift)[1:], decoded[:8], self.shift_index, self.shift_decoded_1, self.last_samplenum)
			self.shift_byte = int(decoded[:8], 2)
			self.shift_decoded_s = decoded[8:]
			self.shift_decoded_1 -= 16
			return True

		def edge(self, edge_samplenum):
			# edge_samplenum: sample index of rising edge (flux transition)
			# State Machine with 3 stages:
			# - PLLstate.locking looks for sync_lock_threshold number of sync_pulse pulses
			# - PLLstate.scanning_sync_mark keeps scanning for either sync_pulse or self.format_current.sync_marks, anything else resets PLL.
			# - PLLstate.decoding

			#print_('pll edge', edge_samplenum, pulse_ticks, '%.4f' % abs(pulse_ticks - 2.0 * self.halfbit), '%.4f' % self.halfbit)

			if self.unsync_after_decode:
				self.reset_pll()

			last_samplenum = self.last_last_samplenum
			self.last_samplenum = last_samplenum
			self.last_last_samplenum = edge_samplenum
			# pulse_ticks: distance from previous edge (samples)
			pulse_ticks = edge_samplenum - last_samplenum
			self.pulse_ticks = pulse_ticks

			# halfbit_cells: number of halfbit cells that pulse span
			self.halfbit_cells = round(pulse_ticks / self.halfbit)

			# Sync pattern detection using pulse width
			if self.state == PLLstate.locking:
				#print_('PLLstate.locking', abs(pulse_ticks - self.halfbit * self.sync_pulse), abs(pulse_ticks - self.halfbit * self.sync_pulse) <= self.pll_sync_tolerance, self.last_samplenum)
				#print_('PLLstate.locking2', pulse_ticks * (1000000000 / self.owner.samplerate), self.halfbit * self.sync_pulse * (1000000000 / self.owner.samplerate), self.pll_sync_tolerance, self.pll_sync_tolerance * (1000000000 / self.owner.samplerate), self.halfbit, '=', self.halfbit * (1000000000 / self.owner.samplerate), self.halfbit_cells, self.last_samplenum)
				if abs(pulse_ticks - self.halfbit * self.sync_pulse) <= self.pll_sync_tolerance:
					self.sync_lock_count += 1
					#print_('pll sync', pulse_ticks, self.halfbit, self.last_samplenum)
					#print_('lock_count', self.sync_lock_count)
					if self.sync_lock_count == 1:
						# remember start of sync and set initial phase reference
						self.sync_start = edge_samplenum - pulse_ticks - round(self.halfbit * 0.5)
						self.phase_ref = edge_samplenum
						#print_('sync_start', edge_samplenum - pulse_ticks - round(self.halfbit * 0.5), edge_samplenum, pulse_ticks, round(self.halfbit * 0.5), self.last_samplenum)
						return False
					elif self.sync_lock_count >= self.sync_lock_threshold:
						# seen enough clock pulses, PLL locked in
						self.state = PLLstate.scanning_sync_mark
						print_('pll locked', self.sync_start, self.last_samplenum)
						#self.sync_lock_count -= 1 # it will be incremented again lower down
				elif self.sync_lock_count:
					#print_('pll sync pattern interrupted -> reset')
					self.reset_pll()
					return False
				else:
					return False

			# check pulse constraints
			if self.halfbit_cells < self.cells_allowed_min:
				print_("pll pulse out-of-tolerance, too short", pulse_ticks, self.halfbit_cells, edge_samplenum)
				self.reset_pll()
				return False
			elif self.halfbit_cells > self.cells_allowed_max:
				print_("pll pulse out-of-tolerance, too long", pulse_ticks, self.halfbit_cells, edge_samplenum)
				#print_(self.halfbit_cells, self.cells_allowed_max, pulse_ticks, self.halfbit, pulse_ticks / self.halfbit)
				# now handle special case of pulse too long but covering end of last good byte
				if self.state == PLLstate.decoding and self.shift_index + self.halfbit_cells >= 16:
					# unsync_after_decode will trigger pll.reset_pll() on next impulse, that way we can still decode end of last good byte
					print_("self.unsync_after_decode")
					self.unsync_after_decode = True
				else:
					print_("pll pulse out-of-tolerance, not in cells_allowed")
					self.reset_pll()
					return False

			# PLL PI Filter ------------------------------------------------------------
			# expected clock position for this transition
			self.phase_ref = self.phase_ref + self.halfbit_cells * self.halfbit

			# PHASE ERROR: positive -> edge arrived after expected clock (we're late)
			phase_err = edge_samplenum - self.phase_ref

			#print_('phase_err', pulse_ticks, self.halfbit_cells, '%.4f' % self.halfbit, '%.4f' % self.phase_ref, '%.4f' % phase_err)

			# Proportional: nudge phase_ref toward the edge
			self.phase_ref += self.kp * phase_err

			# Integral: accumulate small frequency correction
			norm_err = phase_err / self.halfbit_nom
			self.integrator += self.ki * norm_err
			self.halfbit += self.integrator

			#print_('pll phase_ref %.4f' % self.phase_ref, 'inte %.4f' % self.integrator, 'halfbit %.4f' % self.halfbit)
			# ------------------------------------------------------------

			# clamp halfbit within reasonable 0.5-1.5 bounds
			if self.halfbit < self.halfbit_nom05:
				print_('pll -ERRR!!!!!!!!!!!!!!!!!!!!!!!!!!', self.halfbit, self.halfbit_nom, self.halfbit_nom05)
				self.halfbit = self.halfbit_nom05
			elif self.halfbit > self.halfbit_nom15:
				print_('pll +ERRR!!!!!!!!!!!!!!!!!!!!!!!!!!', self.halfbit, self.halfbit_nom, self.halfbit_nom15)
				self.halfbit = self.halfbit_nom15

			#print_('byyyte', pulse_ticks, self.halfbit_cells, self.halfbit, self.last_samplenum, edge_samplenum)
			halfbit = (edge_samplenum - last_samplenum) / self.halfbit_cells
			_, x, _ = self.ring_wv[self.ring_ptr]
			y = last_samplenum + 1.5 * halfbit
			for _ in range (0, self.halfbit_cells-1):
				self.ring_write(int(round(x)), int(round(y)), False)
				x = y
				y += halfbit
			y = edge_samplenum + 0.5 * halfbit
			self.ring_write(int(round(x)), int(round(y)), True)

			self.shift = ((self.shift << self.halfbit_cells) + 1) & 0xffffffff
			#print_('pll_shift', bin(self.shift)[1:], self.halfbit_cells, self.last_samplenum)

			if self.state == PLLstate.scanning_sync_mark:
				# just another sync pulse
				if not self.sync_marks_try and self.halfbit_cells == self.sync_pulse:
					self.sync_lock_count += 1

				# scan for start of sync mark
				else:
					#print_('scanning_sync_mark', self.sync_marks_try, self.last_samplenum)
					partial_sync_marks_match = False
					self.shift_index = self.format_current.shift_index
					for sequence_number in range (0, self.sync_marks_len):
						#print_('scanning_sync_mark_', sequence_number, self.sync_marks_try)
						if self.sync_marks_try + [self.halfbit_cells] == self.sync_marks[sequence_number][:len(self.sync_marks_try) + 1]:
							# partial sync_marks match
							partial_sync_marks_match = True
							self.sync_marks_try += [self.halfbit_cells]
							if self.sync_marks_try == self.sync_marks[sequence_number]:
								# full sync_marks match
								self.state = PLLstate.decoding
								self.shift_index = self.shift_index[sequence_number]
								print_('pll byte_synced', self.last_samplenum)
							break

					if not partial_sync_marks_match:
						self.reset_pll()
						return False

					# Partial sync_marks match at this point
					# if RLL then scan for illegal sequence to rewrite. We rewrite it so rll_decode() doesnt choke on it.
					if self.halfbit_cells == 8 and self.limits_key == coding.RLL:
						if self.format == coding.RLL_OMTI:
							# OMTI special rule "At SAM time a 2 of 7 pattern is searched for
							# consisting of a nrz 62 with a pulse one clock delayed."
							#print_('RLL_OMTI rewrite mark', bin(self.shift)[1:], bin(self.shift ^ (1 << 7))[1:])
							self.shift = self.shift ^ 3
						else:
							#print_('RLL rewrite mark', bin(self.shift)[1:], bin(self.shift ^ (1 << 7))[1:])
							self.shift = self.shift ^ 16

			if self.state == PLLstate.decoding:
				# accumulate at least 16 bits, only return 16 bits at a time.
				self.shift_index += self.halfbit_cells
				#print_('pll_shift1', bin(self.shift)[1:], self.shift_index, self.halfbit_cells, self.shift_index +self.halfbit_cells)
				if self.shift_index + self.shift_decoded_1 >= 16:
					return self.decode()
			return False

	# ------------------------------------------------------------------------
	# PURPOSE: Calculate CRC of a bytearray.
	# IN: bytearray
	# OUT: self.crc_accum updated
	# ------------------------------------------------------------------------

	def make_crc_table(self, crc_table, crc_poly, crc_bits):
		mask = (1 << crc_bits) - 1
		topbit = 1 << (crc_bits - 1)
		crc_table_ = crc_table
		crc_poly_ = crc_poly

		for i in range(256):
			crc = i << (crc_bits - 8)
			for _ in range(8):
				if crc & topbit:
					crc = ((crc << 1) ^ crc_poly_) & mask
				else:
					crc = (crc << 1) & mask

			crc_table_[i] = crc

	def calculate_crc_header(self, all_arrays):
		#self.calculate_crc(all_arrays, self.header_crc_init, self.header_crc_size, self.header_crc_mask, self.header_crc_poly)
		self.calculate_crc_table(all_arrays, self.header_crc_table, self.header_crc_init, self.header_crc_size, self.header_crc_mask)

	def calculate_crc_data(self, all_arrays):
		#self.calculate_crc(all_arrays, self.data_crc_init, self.data_crc_size, self.data_crc_mask, self.data_crc_poly)
		self.calculate_crc_table(all_arrays, self.data_crc_table, self.data_crc_init, self.data_crc_size, self.data_crc_mask)

	def calculate_crc(self, all_arrays, crc_accum, crc_bits, crc_mask, crc_poly):
		crc_offset = crc_bits - 8
		crc_topbit = 1 << (crc_bits -1)
		# hoisted local variables, supposedly faster, stupid python
		crc_mask_ = crc_mask
		crc_accum_ = crc_accum
		crc_poly_ = crc_poly
		all_arrays_ = all_arrays

		for arr in all_arrays_:
			for byte in arr:
				crc_accum_ = (crc_accum_ ^ (byte << crc_offset)) & crc_mask_
				for _ in range(8):
					if crc_accum_ & crc_topbit:
						crc_accum_ = ((crc_accum_ << 1) ^ crc_poly_) & crc_mask_
					else:
						crc_accum_ = (crc_accum_ << 1) & crc_mask_
					# Alternative no comparisons version of above 4 lines. Much faster in C, actually slower in python :=). Credit luasoft10
					#crc_accum_ = ((crc_accum_ << 1) ^ (-(crc_accum_ >> (crc_bits -1)) & crc_poly_)) & crc_mask_

		self.crc_accum = crc_accum_

	# Table version is 8 times faster than calculate_crc
	def calculate_crc_table(self, all_arrays, crc_table, crc_accum, crc_bits, crc_mask):
		all_arrays_ = all_arrays
		crc_table_ = crc_table
		crc_accum_ = crc_accum
		shift = crc_bits - 8
		crc_mask_ = crc_mask

		for arr in all_arrays_:
			for byte in arr:
				idx = ((crc_accum_ >> shift) ^ byte) & 0xFF
				crc_accum_ = ((crc_accum_ << 8) ^ crc_table_[idx]) & crc_mask_

		self.crc_accum = crc_accum_

	# ------------------------------------------------------------------------
	# PURPOSE: Annotate single half-bit-cell window.
	# IN: target		target window
	#	  start, end	sample numbers
	#	  value			number of pulses
	# ------------------------------------------------------------------------

	def annotate_window(self, target, start, end, value):
		dataclock = {
						ann.dat:	' d',
						ann.clk:	' c',
						ann.erw:	'',
						ann.unk:	'',
					}[target]

		if value > 1:
			# no need to emit error message, it was already caught by out-of-tolerance leading edge (OoTI) detector inside PLL
			if self.show_sample_num:
				self.put(start, end, self.out_ann, [ann.erw, ['%d%s (extra pulse in win) s%d' % (value, dataclock, start), '%d' % value]])
			else:
				self.put(start, end, self.out_ann, [ann.erw, ['%d%s (extra pulse in win)' % (value, dataclock), '%d' % value]])
		else:
			if self.show_sample_num:
				self.put(start, end, self.out_ann, [target, ['%d%s s%d' % (value, dataclock, start), '%d' % value]])
			else:
				self.put(start, end, self.out_ann, [target, ['%d%s' % (value, dataclock), '%d' % value]])

	# ------------------------------------------------------------------------
	# PURPOSE: Annotate 8 bits and 16 windows of one byte using pll.ring_buffer.
	# NOTES:
	#	Synchronisation marks implemented by omitting some clock pulses.
	#	FM:
	#		FCh with D7h (11010111) clock	IAM		Index Mark
	#		FEh with C7h (11000111) clock	IDAM	ID Address Mark
	#		FBh with C7h (11000111) clock	DAM		Data Address Mark
	#		F8h..FAh C7h (11000111) clock	DDAM	Deleted Data Address Mark
	#	MFM:
	#		C2h no clock between bits 3/4
	#		A1h no clock between bits 2/3
	# IN: special_clock	True = don't generate error on clock gritches
	#					False = normal clocking, generate error
	# OUT: self.byte_start, self.byte_end	updated
	# ------------------------------------------------------------------------

	def annotate_bits_FM_MFM(self, special_clock):
		win_start = 0			# start of window (sample number)
		win_end = 0				# end of window (sample number)
		win_val = 0				# window value (Bool)
		bit_start = 0			# start of bit (sample number)
		bit_end = 0				# end of bit (sample number)
		shift3 = 0				# 3-bit shift register of window values
		bitn = 7				# starting bit
		offset = - self.pll.shift_index

		# MFM error checking requires 3 consecutive windows, initialize shift3 with last bit of
		# previous byte. Initialize self.byte_start with byte_end of last bit of previous byte.
		_, self.byte_start, shift3 = self.pll.ring_read_offset(offset - 16)

		while bitn >= 0:
			# Display annotation for first (clock) half-bit-cell window of a pair.
			win_start, win_end, win_val = self.pll.ring_read_offset(offset - bitn * 2 - 1)
			bit_start = win_start

			shift3 = (shift3 << 1) + win_val

			#print_(ann.clk, win_start, win_end, win_val, - bitn * 2 - 1 - pll.shift_index, pll.shift_index)
			self.annotate_window(ann.clk, win_start, win_end, win_val)

			# Display annotation for second (data) half-bit-cell window of a pair.
			win_start, win_end, win_val = self.pll.ring_read_offset(offset - bitn * 2)

			shift3 = (shift3 << 1) + win_val

			#print_(ann.dat, win_start, win_end, win_val, - bitn * 2 - pll.shift_index)
			self.annotate_window(ann.dat, win_start, win_end, win_val)
			#print_(ann.dat, pll.fifo_wv, pll.fifo_ws, pll.fifo_we)

			#print_(bit_start, win_end, win_val)
			# Display annotation for bit using value from data window.
			if (self.format == coding.MFM and (shift3 & 0b111) in (0b000, 0b011, 0b110, 0b111)) \
				or (self.format == coding.FM and not (shift3 & 0b10)):
				if not special_clock:
					self.put(bit_start, win_end, self.out_ann, message.errorClock)
					self.CkEr += 1
				self.put(bit_start, win_end, self.out_ann, [ann.erb, ['%d (clock error)' % win_val, '%d' % win_val]])
			else:
				self.put(bit_start, win_end, self.out_ann, [ann.bit, ['%d' % win_val]])

			bitn -= 1

		self.byte_end = win_end

	# ------------------------------------------------------------------------
	# PURPOSE: Annotate 8 bits and 16 windows of one byte using pll.ring_buffer.
	# NOTES:
	#	Synchronisation marks implemented by emitting illegal 0b100000001001 sequence.
	#	PLLstate.scanning_sync_mark overrides those into 0b100010001001 creating:
	#	RLL_Seagate:
	#		1Eh ID_prefix_mark
	#		DEh nop_mark
	#	RLL_WD:
	#		F0h IDData_mark
	#	etc ...
	# IN: special_clock	True = mark clock glitch
	#					False = skip clock glitch checking
	# OUT: self.byte_start, self.byte_end	updated
	# ------------------------------------------------------------------------

	def annotate_bits_RLL(self, val, special_clock):
		win_start = 0			# start of window (sample number)
		win_end = 0				# end of window (sample number)
		win_val1 = 0			# window 1 value (Bool)
		win_val2 = 0			# window 2 value (Bool)
		bit_val = 0				# bit value (Bool)
		bit_start = 0			# start of bit (sample number)
		bit_end = 0				# end of bit (sample number)
		bitn = 7				# starting bit
		offset = self.pll.shift_decoded_1 + self.pll.shift_index

		# binary_str is the raw bitstream with overwritten Sync Mark illegal pattern
		# use it to mark illegal windows/bits
		shift_win = (self.pll.shift >> offset) & 0xffff

		# Initialize self.byte_start with byte_end of last bit of previous byte.
		_, self.byte_start, _ = self.pll.ring_read_offset(- offset - 16)

		while bitn >= 0:
			win_start, win_end, win_val1 = self.pll.ring_read_offset(- offset - bitn * 2 - 1)
			bit_start = win_start

			self.annotate_window(ann.dat, win_start, win_end, win_val1)

			win_start, win_end, win_val2 = self.pll.ring_read_offset(- offset - bitn * 2)

			self.annotate_window(ann.dat, win_start, win_end, win_val2)

			# Display annotation for bit using passed val, that way we dont need to decode RLL again
			bit_val = val >> bitn & 1
			if special_clock and ((win_val1 ^ shift_win >> (bitn * 2 + 1) & 1 ) | (win_val2 ^ shift_win >> (bitn * 2) & 1 )):
				self.put(bit_start, win_end, self.out_ann, [ann.erb, ['%d (clock error)' % bit_val, '%d' % bit_val]])
			else:
				self.put(bit_start, win_end, self.out_ann, [ann.bit, ['%d' % bit_val]])

			bitn -= 1

		self.byte_end = win_end

	# ------------------------------------------------------------------------
	# PURPOSE: Annotate one byte and its 8 bits/16 windows.
	# IN: val	byte value (00h..FFh)
	#	special_clock	True = special clocking, don't generate error
	#					False or omitted = normal clocking, generate error
	# OUT: self.byte_start, self.byte_end	updated
	# ------------------------------------------------------------------------

	def annotate_byte(self, val, special_clock = False):
		# Display annotations for bits and windows of this byte.
		#print_('annotate_bits',hex(val), special_clock)
		if self.format in (coding.FM, coding.MFM):
			self.annotate_bits_FM_MFM(special_clock)
		else:
			self.annotate_bits_RLL(val, special_clock)

		# Display annotation for this byte.
		short_ann = '%02X' % val
		if val >= 32 and val < 127:
			long_ann = '%02X \'%c\'' % (val, val)
		else:
			long_ann = short_ann

		self.put(self.byte_start, self.byte_end, self.out_ann,
				 [ann.byt, [long_ann, short_ann]])

	# ------------------------------------------------------------------------
	# Display an annotation for a field.
	# IN: typ	Enum like field
	#	  self.field_start, self.byte_end
	# OUT: self.field_start	updated
	# ------------------------------------------------------------------------

	def display_field(self, typ):
		if typ == field.Index_Mark:
			self.IAMs += 1
			self.put(self.field_start, self.byte_end, self.out_ann, message.iam)
			self.report_last = field.Index_Mark
			if self.report == field.Index_Mark:
				self.reports_called = self.IAMs
				self.display_report()

		elif typ == field.ID_Address_Mark:
			self.IDAMs += 1
			self.put(self.field_start, self.byte_end, self.out_ann, message.idam)
			self.report_last = field.ID_Address_Mark
			if self.report == field.ID_Address_Mark:
				self.reports_called = self.IDAMs
				self.display_report()

		elif typ == field.Data_Address_Mark:
			# DDAMs only on ancient FM floppies
			if self.format == coding.FM and self.DRmark[0] in (0xF8, 0xF9, 0xFA):
				self.DDAMs += 1
				self.put(self.field_start, self.byte_end, self.out_ann, message.ddam)
				self.report_last = field.Deleted_Data_Mark
				if self.report == field.Deleted_Data_Mark:
					self.reports_called = self.DDAMs
			else:
				self.DAMs += 1
				self.put(self.field_start, self.byte_end, self.out_ann, message.dam)
				self.report_last = field.Data_Address_Mark
				if self.report == field.Data_Address_Mark:
					self.reports_called = self.DAMs

		elif typ == field.ID_Record:
			self.put(self.field_start, self.byte_end, self.out_ann,
					 [ann.rec, ['ID Record: cyl=%d, sid=%d, sec=%d, len=%d' %
						  (self.IDcyl, self.IDsid, self.IDsec, self.IDlenv),
						  'ID Record', 'Irec', 'R']])

		elif typ == field.Data_Record:
			self.put(self.field_start, self.byte_end, self.out_ann, message.drec)

		elif typ == field.CRC_Ok:
			self.CRC_OK += 1
			self.put(self.field_start, self.byte_end, self.out_ann,
					 [ann.crc, ['CRC OK %02X' % self.crc_accum, 'CRC OK', 'CRC', 'C']])
			if self.report_last in (field.Deleted_Data_Mark, field.Data_Address_Mark):
				# display_report called in CRC message so we know when Data_Mark ended
				self.display_report()

		elif typ == field.CRC_Error:
			self.CRC_err += 1
			self.put(self.byte_end - 1, self.byte_end, self.out_ann, message.error)
			self.put(self.field_start, self.byte_end, self.out_ann,
					 [ann.cre, ['CRC error %02X' % self.crc_accum, 'CRC error', 'CRC', 'C']])
			if self.report_last in (field.Deleted_Data_Mark, field.Data_Address_Mark):
				self.display_report() # called in CRC message so we know when Data_Mark ended

		elif typ == field.Unknown_Byte:
			self.put(self.byte_start, self.byte_end, self.out_ann, message.errorUnkByte)

		elif typ == field.Sync:
			if self.pll.sync_start:
				self.put(self.pll.sync_start, self.byte_start, self.out_ann, messageD.sync((self.pll.sync_lock_count * 2) // 16))
				self.pll.sync_start = False
				self.field_start = self.byte_start
			return

		elif typ == field.Gap:
			gap_len = (self.byte_end - self.gap_start) // round(self.pll.halfbit*16)
			self.put(self.gap_start, self.byte_end, self.out_ann, messageD.gap(gap_len))

		self.field_start = self.byte_end

	# ------------------------------------------------------------------------
	# PURPOSE: Decode ID Record subfields.
	# ------------------------------------------------------------------------

	def decode_id_rec_3byte(self, IDrec):
		if self.IDmark == []:
			raise raise_exception('decode_id_rec_3byte: Cant have empty IDmark here, wrong encoding or header_format selected')
		# IDmark encodes 3 bits of Cylinder upper byte
		# IDmark & 0b0001 = 9th bit
		# (IDmark & 0b0010) ^ 0b0010 = 10th bit
		# (IDmark & 0b1000) ^ 0b1000 = 11th bit
		msb = (self.IDmark[0] ^ 0xE) & 0x0F
		# IDrec[0] holds Cylinder lower byte
		self.IDcyl = ((msb & 0b11) << 8) + ((msb & 0b1000) << 7) + IDrec[0]
		self.IDsid = IDrec[1] & 0x0F
		self.IDsec = IDrec[2]
		self.IDlenc = IDrec[1] >> 4
		self.IDlenv = 128 << (self.IDlenc & 7)

	def decode_id_rec_4byte(self, IDrec):
		self.IDcyl = IDrec[0]
		self.IDsid = IDrec[1]
		self.IDsec = IDrec[2]
		self.IDlenc = IDrec[3]
		self.IDlenv = 128 << (IDrec[3] & 7)

	def decode_id_rec_4byte_Seagate(self, IDrec):
		self.IDcyl = ((IDrec[0] & 0b11000000) << 2) + IDrec[1]
		self.IDsid = IDrec[0] & 0xF
		# Quirks: spare unused sector marked as IDsec == 254
		self.IDsec = IDrec[2]
		#self.IDlenc = IDrec[3]
		#self.IDlenv = 512 << (IDrec[3] & 7) probably not :), hardcode 512 for now
		self.IDlenc = 2
		self.IDlenv = 512

	def decode_id_rec_4byte_OMTI(self, IDrec):
		self.IDcyl = (IDrec[0] << 8) + IDrec[1]
		self.IDsid = IDrec[2]
		self.IDsec = IDrec[3]
		# no space for encoding Sector size, hardcode 512
		self.IDlenc = 2
		self.IDlenv = 512

	def decode_id_rec_4byte_Adaptec(self, IDrec):
		self.IDcyl = ((IDrec[1] & 0xF0) << 4) + IDrec[0]
		self.IDsid = IDrec[1] & 0xF
		self.IDsec = IDrec[2]
		# hardcoded 512
		self.IDlenc = 2
		self.IDlenv = 512

	# Adaptek RLL to SCSI bridge, stores LBA in headers
	def decode_id_rec_4byte_Adaptec4070(self, IDrec):
		LBA = (IDrec[0] << 16) + (IDrec[1] << 8) + IDrec[2]
		track = LBA // 26
		self.IDcyl = track // 6
		self.IDsid = track - self.IDcyl * 6
		self.IDsec = LBA - track * 26
		# hardcoded 512, 6 heads, 26 sectors/track
		self.IDlenc = 2
		self.IDlenv = 512

	def decode_id_rec_3byte_RLL_DTC7287(self, IDrec):
		rec = bytes([b ^ 0xff for b in IDrec])
		mark = self.IDmark[0] ^ 0xff
		print(''.join("{:08b}".format(byte) for byte in (bytes([self.IDmark[0] ^ 0xff]) + rec)))
		msb = (mark ^ 0x0c) & 0x0F
		#print(hex(mark), hex(msb), hex(mark ^ 0xc), hex(((msb & 0b11) << 8)), hex(((msb & 0b1000) << 7)), hex(rec[0]), hex(rec[0] >> 1))
		# IDrec[0] holds Cylinder lower byte
		self.IDcyl = ((msb & 0b11) << 8) + ((msb & 0b1000) << 7) + (rec[0] >> 1)
		self.IDsid = (rec[1] & 0x0F) >> 1
		if self.IDsid == 7:
			self.IDsid = 5
		#print(bin(rec), hex(msb), hex(mark ^ 0xc), hex(((msb & 0b11) << 8)), hex(((msb & 0b1000) << 7)), hex(rec[0]), hex(rec[0] >> 1))
		#self.IDsec = ((rec[2] & 0b101110) >> 1) #+  (((rec[2] ^ 1) & 1) << 3)
		self.IDsec = ((rec[2] & 0b111110) >> 1) #+  (((rec[2] ^ 1) & 1) << 3)
		#bit_16 = 1 if (rec[2] & 0b100000) else 0
		#bit_8  = 1 if (rec[2] & 0b010000) else 0
		#bit_4  = 1 if (rec[2] & 0b001000) else 0
		#raw_bit_2 = 1 if (rec[2] & 0b000100) else 0
		#bit_1  = 1 if (rec[2] & 0b000010) else 0
		#bit_2 = raw_bit_2 ^ (bit_4 & bit_1)
		#self.IDsec = (bit_16 * 16) + (bit_8 * 8) + (bit_4 * 4) + (bit_2 * 2) + bit_1
		#bit_16 = 1 if (rec[2] & 0b100000) else 0
		#bit_8  = 1 if (rec[2] & 0b010000) else 0
		#bit_4  = 1 if (rec[2] & 0b001000) else 0
		#raw_bit_2 = 1 if (rec[2] & 0b000100) else 0
		#bit_1  = 1 if (rec[2] & 0b000010) else 0
		#bit_2 = raw_bit_2 ^ (bit_4 & bit_1)
		#self.IDsec = (bit_16 * 16) + (bit_8 * 8) + (bit_4 * 4) + (bit_2 * 2) + bit_1
		# hardcoded 512
		self.IDlenc = 2
		self.IDlenv = 512
		# unless special header, then bizzarre 64byte data leftover with hardcoded sector number 254
		if rec[1] & 0b00000001:
			self.IDlenv = 64
			self.IDsec = 254

	# ------------------------------------------------------------------------
	# PURPOSE: State machine to process one byte extracted from pulse stream.
	# IN: val
	# OUT: True		= OK, get next byte
	#	   False	= start of Gap or error, resync
	# ------------------------------------------------------------------------

	def process_byte(self, val):
		if self.pb_state == state.sync_mark:
			self.annotate_byte(val, special_clock = True)
			self.display_field(field.Sync)
			self.byte_cnt = 0
			self.IDcrc = 0
			self.DRcrc = 0
			if val in self.format_current.IDData_mark:
				self.A1 = [0xA1]
				self.pb_state = state.IDData_Address_Mark
				if self.IDmark:
					self.IDmark = []
					self.display_field(field.ID_Address_Mark)
					self.pb_state = state.ID_Record
			elif val in self.format_current.ID_mark:
				self.IDmark = [val]
				self.display_field(field.ID_Address_Mark)
				self.pb_state = state.ID_Record
			elif val in self.format_current.Data_mark:
				self.DRmark = [val]
				self.display_field(field.Data_Address_Mark)
				self.pb_state = state.Data_Record
			elif val in self.format_current.ID_prefix_mark:
				self.IDmark = [val]
			elif val in self.format_current.nop_mark:
				pass
			elif val in self.format_current.nop_A1_mark:
				self.A1 = [0xA1]
			# FM Index Mark
			elif val == 0xFC:
				self.display_field(field.Index_Mark)
				self.pb_state = state.first_Gap_Byte
			# MFM FDD Index Mark
			elif val == 0xC2:
				self.pb_state = state.second_C2h_prefix
			else:
				self.display_field(field.Unknown_Byte)
				return False

		elif self.pb_state == state.IDData_Address_Mark:
			# MFM FDD second or third A1
			# Abusing state.IDData_Address_Mark for MFM floppy triple
			# A1 Sync Mark detection. Ugly, but less ugly than keeping
			# separate MFM_FDD and MFM_HDD options.
			if val == 0xA1:
				self.annotate_byte(val, special_clock = True)
				self.A1.append(0xA1)
				return True
			self.annotate_byte(val)
			self.display_field(field.Sync)
			if (val & 0xF4) == 0xF4:
				# FC-FFh ID Address Mark
				# & 0xF4 because id_rec_3byte stores 3 bits of Cylinder High in Address Mark
				self.IDmark = [val]
				self.display_field(field.ID_Address_Mark)
				self.pb_state = state.ID_Record
			elif val >= 0xF8 and val <= 0xFB:
				# F8h..FBh Data Address Mark
				self.DRmark = [val]
				self.display_field(field.Data_Address_Mark)
				self.pb_state = state.Data_Record
			else:
				self.display_field(field.Unknown_Byte)
				return False

		elif self.pb_state == state.ID_Record:
			self.annotate_byte(val)
			self.IDrec[self.byte_cnt] = val
			self.byte_cnt += 1
			if self.byte_cnt == self.header_size:
				self.decode_id_rec(self.IDrec)
				self.display_field(field.ID_Record)
				self.put(self.field_start, self.byte_end, self.out_binary, [bnr.id, bytes(self.IDrec)])
				if self.sector_size_auto and self.sector_size != self.IDlenv:
					self.sector_size = self.IDlenv
					self.DRrec = bytearray(self.sector_size)
				self.byte_cnt = 0
				self.pb_state = state.ID_Record_CRC

		elif self.pb_state == state.ID_Record_CRC:
			self.annotate_byte(val)
			self.IDcrc <<= 8
			self.IDcrc += val
			self.byte_cnt += 1
			if self.byte_cnt == self.header_crc_bytes:
				self.calculate_crc_header((self.A1, self.IDmark, self.IDrec))
				self.put(self.field_start, self.byte_end, self.out_binary, [bnr.idcrc, bytes(self.A1 + self.IDmark) + bytes(self.IDrec) + self.IDcrc.to_bytes(self.header_crc_bytes, 'big')])
				if self.crc_accum == self.IDcrc:
					self.display_field(field.CRC_Ok)
				else:
					self.display_field(field.CRC_Error)
				self.pb_state = state.first_Gap_Byte

		elif self.pb_state == state.Data_Record:
			self.annotate_byte(val)
			if self.byte_cnt >= self.sector_size:
				raise raise_exception("Error: Data_Record DRrec allocation too small to fit incoming data. Switch 'Sector payload length' from Auto to fixed size.")
			self.DRrec[self.byte_cnt] = val
			self.byte_cnt += 1
			if self.byte_cnt == self.sector_size:
				self.display_field(field.Data_Record)
				self.byte_cnt = 0
				self.pb_state = state.Data_Record_CRC

		elif self.pb_state == state.Data_Record_CRC:
			self.annotate_byte(val)
			self.DRcrc <<= 8
			self.DRcrc += val
			self.byte_cnt += 1
			if self.byte_cnt == self.data_crc_bytes:
				self.calculate_crc_data((self.A1, self.DRmark, self.DRrec))
				DRrec = bytes(self.DRrec)
				self.put(self.field_start, self.byte_end, self.out_binary, [bnr.data, bytes(self.DRrec)])
				self.put(self.field_start, self.byte_end, self.out_binary, [bnr.iddata, bytes(self.IDrec + self.DRrec)])
				self.put(self.field_start, self.byte_end, self.out_binary, [bnr.datacrc, bytes(self.A1 + self.DRmark) + bytes(self.DRrec) + self.DRcrc.to_bytes(self.data_crc_bytes, 'big')])
				if self.crc_accum == self.DRcrc:
					self.display_field(field.CRC_Ok)
				else:
					self.display_field(field.CRC_Error)
				self.pb_state = state.first_Gap_Byte

		elif self.pb_state in (state.second_C2h_prefix, state.third_C2h_prefix):
			self.annotate_byte(val, special_clock = True)
			if val == 0xC2:
				if self.pb_state == state.second_C2h_prefix:
					self.pb_state = state.third_C2h_prefix
				elif self.pb_state == state.third_C2h_prefix:
					self.pb_state = state.Index_Mark
			else:
				self.display_field(field.Unknown_Byte)
				return False

		elif self.pb_state == state.Index_Mark:
			self.annotate_byte(val)
			if val == 0xFC:
				self.display_field(field.Index_Mark)
				self.pb_state = state.first_Gap_Byte
			else:
				self.display_field(field.Unknown_Byte)
				return False

		elif self.pb_state == state.first_Gap_Byte:
			self.annotate_byte(val)
			return False						# done, unsync

		else:
			return False

		return True

	# ------------------------------------------------------------------------
	# PURPOSE: Display summary every x Headers.
	# ------------------------------------------------------------------------

	def display_report(self):
		if self.reports_called < self.report_qty:
			return

		self.put(self.report_start, self.byte_start, self.out_ann, messageD.report(self.IAMs, self.IDAMs, self.DAMs, self.DDAMs, self.CRC_OK, self.CRC_err, self.EiPW, self.CkEr, self.OoTI, self.Intrvls))

		# clear all report markers
		(self.IAMs, self.IDAMs, self.DAMs, self.DDAMs, self.CRC_OK, self.CRC_err, self.EiPW, self.CkEr, self.OoTI, self.Intrvls) = (0,0,0,0,0,0,0,0,0,0)

		self.report_start = self.byte_end
		self.reports_called = 0

	# ------------------------------------------------------------------------
	# PURPOSE: Main protocol decoding loop.
	# NOTES:
	#  - It automatically terminates when self.wait() requests termination
	#	 due to end-of-data reached before specified condition found.
	# ------------------------------------------------------------------------

	def decode_PLL(self):
		# --- Verify that a sample rate was specified.
		if not self.samplerate:
			raise raise_exception('Cannot decode without samplerate.')

		# --- Initialize CRC Tables
		self.make_crc_table(self.header_crc_table, self.header_crc_poly, self.header_crc_size)
		if self.header_crc_poly == self.data_crc_poly:
			self.data_crc_table = self.header_crc_table
		else:
			self.make_crc_table(self.data_crc_table, self.data_crc_poly, self.data_crc_size)

		# --- Initialize (half-)bit-cell-window
		# Cant put it in start() or metadata() becaue we cant be sure of order those
		# two are called, one initializes (samplerate) the other user options (data_rate)
		bc10N = self.samplerate / self.data_rate	# nominal 1.0 bit cell window size (in fractional samples)
		window_size = bc10N / 2.0	# current half-bit-cell window size (in fractional samples)

		interval = 0				# current interval (in samples, 1..n)
		ret_val = 0
		pll_ret = False
		last_samplenum = 0
		cells_allowed = self.format_current.limits

		self.pll = self.SimplePLL(owner=self, halfbit_ticks=window_size, kp=self.pll_kp, ki=self.pll_ki, pll_sync_tolerance=self.pll_sync_tolerance, format_current=self.format_current)

		# all this pain below to support dynamic Interval/window annotation
		interval_multi = {
			'ns':		1000000000 / self.samplerate,
			'us':		1000000 / self.samplerate,
			'auto':		(1000000 / self.samplerate) if (1000000000 / self.samplerate) * window_size > 1000 else (1000000000 / self.samplerate),
			'window':	0
						}[self.time_unit]

		interval_unit = {
			'ns':		'ns',
			'us':		'us',
			'auto':		'us' if interval_multi == (1000000 / self.samplerate) else 'ns',
			'window':	''
						}[self.time_unit]

		def interval_time_func(interval):
			return str(round(interval * interval_multi)) + interval_unit

		def interval_window_func(interval):
			return str(round(interval / window_size))

		interval_func = {
			'ns':		interval_time_func,
			'us':		interval_time_func,
			'auto':		interval_time_func,
			'window':	interval_window_func
						}[self.time_unit]

		# Quirk: DTC7287 appears to XOR all data with 0xFF
		xor_ed = False if self.format_current.format != coding.RLL_DTC7287_unknown else True
		xor_ed = False

		# --- Process all input data.
		while True:
			self.Intrvls += 1

			# Wait for leading edge (rising or falling) on channel 0.  Also handle
			# extra pulses on channel 1, and disable/suppress signal on channel 2.
			if self.rising_edge:
				(data_pin, extra_pin, suppress_pin) = self.wait([{0: 'r', 2: 'l'}, {1: 'r', 2: 'l'}])
			else:
				(data_pin, extra_pin, suppress_pin) = self.wait([{0: 'f', 2: 'l'}, {1: 'r', 2: 'l'}])

			pll_ret = self.pll.edge(self.samplenum)
			interval = self.pll.pulse_ticks
			last_samplenum = self.pll.last_samplenum
			#last_samplenum, interval = pll.read()

			#print_('main:', self.last_samplenum, self.samplenum, interval, str(round(interval * interval_multi)) + interval_unit, pll_ret)

			# Annotate Pulses, leading-edge to leading-edge.
			# Interval in interval_unit and optional sample number.
			interval_annotation = interval_func(interval)
			if self.pll.halfbit_cells in cells_allowed:
				if self.show_sample_num:
					self.put(last_samplenum, self.samplenum, self.out_ann,	[ann.pul, ['%s s%d - %d' % (interval_annotation, last_samplenum, self.samplenum), '%s' % interval_annotation]])
				else:
					self.put(last_samplenum, self.samplenum, self.out_ann,	[ann.pul, ['%s' % interval_annotation]])
			else:
				self.OoTI += 1
				if self.pll.halfbit_cells < self.pll.cells_allowed_min:
					self.put(last_samplenum, self.samplenum, self.out_ann, message.errorOoTIs)
				else:
					self.put(last_samplenum, self.samplenum, self.out_ann, message.errorOoTIl)
				if self.show_sample_num:
					self.put(last_samplenum, self.samplenum, self.out_ann,	[ann.erp, ['%s out-of-tolerance leading edge s%d' % (interval_annotation, last_samplenum), '%s OoTI s%d' % (interval_annotation, last_samplenum), '%s OoTI' % interval_annotation, 'OoTI']])
				else:
					self.put(last_samplenum, self.samplenum, self.out_ann,	[ann.erp, ['%s out-of-tolerance leading edge' % interval_annotation, '%s OoTI' % interval_annotation, 'OoTI']])

			if pll_ret:
				ret_val = self.pll.shift_byte ^ 0xff if xor_ed else self.pll.shift_byte
				if not self.process_byte(ret_val):
					print_('not byte_sync')
					self.pll.reset_pll()

				print_('data_byte', hex(ret_val), self.pb_state)

	# ------------------------------------------------------------------------
	# Legacy decoder below
	# ------------------------------------------------------------------------

	# ------------------------------------------------------------------------
	# PURPOSE: Increment FIFO read pointer and decrement entry count.
	# ------------------------------------------------------------------------

	def inc_fifo_rp(self):
		self.fifo_rp = (self.fifo_rp + 1) % self.fifo_size
		self.fifo_cnt -= 1
		if self.fifo_cnt < 0:
			self.fifo_cnt = 0
			raise raise_exception('FIFO below 0!!')

	# ------------------------------------------------------------------------
	# PURPOSE: Increment FIFO write pointer and increment entry count.
	# ------------------------------------------------------------------------

	def inc_fifo_wp(self):
		self.fifo_wp = (self.fifo_wp + 1) % self.fifo_size
		self.fifo_cnt += 1
		if self.fifo_cnt > self.fifo_size:
			self.fifo_cnt = self.fifo_size
			raise raise_exception('FIFO over 33!!')

	def annotate_bits_legacy(self, special_clock):
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
				self.annotate_window(ann.dat, win_start, win_end, win_val)

			bit_end = win_end
			bit_val = 1 if win_val > 1 else win_val

			# Display annotation for bit using value in data window.  The last
			# bit for the previous byte has already been displayed previously.

			if bitn < 8:
				if (self.format == coding.MFM and (shift3 == 0 or shift3 == 3 or shift3 == 6 or shift3 == 7)) \
				 or (self.format == coding.FM and (shift3 == 0 or shift3 == 1 or shift3 == 4 or shift3 == 5)):
					if not special_clock:
						self.put(bit_end - 1, bit_end, self.out_ann, message.error)
						self.CkEr += 1
					self.put(bit_start, bit_end, self.out_ann, [ann.erb, ['%d (clock error)' % bit_val, '%d' % bit_val]])
				else:
					self.put(bit_start, bit_end, self.out_ann, [ann.bit, ['%d' % bit_val]])

			if bitn == 0:
				break

			# Display annotation for first (clock) half-bit-cell window of a pair.

			win_start = self.fifo_ws[self.fifo_rp]
			win_end = self.fifo_we[self.fifo_rp]
			win_val = self.fifo_wv[self.fifo_rp]
			self.inc_fifo_rp()

			shift3 = ((shift3 & 0x03) << 1) + (1 if win_val > 1 else win_val)

			if bitn > 0:
				self.annotate_window(ann.clk, win_start, win_end, win_val)

			bit_start = win_start
			if self.byte_start == -1:
				self.byte_start = bit_start

			bitn -= 1

			# end while

		self.byte_end = bit_end

	def annotate_byte_legacy(self, val, special_clock = False):
		# Display annotations for bits and windows of this byte.
		self.annotate_bits_legacy(special_clock)

		# Display annotation for this byte.
		short_ann = '%02X' % val
		if val >= 32 and val < 127:
			long_ann = '%02X \'%c\'' % (val, val)
		else:
			long_ann = short_ann

		self.put(self.byte_start, self.byte_end, self.out_ann,
				 [ann.byt, [long_ann, short_ann]])

	def process_byteFM_legacy(self, val):
		if val == 0x1FE:
			self.pb_state = state.ID_Address_Mark
		elif val >= 0x1F8 and val <= 0x1FB:
			val &= 0x0FF
			self.pb_state = state.Data_Address_Mark
		elif val == 0x1FC:
			self.pb_state = state.Index_Mark

		if self.pb_state == state.ID_Address_Mark:
			self.IDmark = [(val & 0x0FF)]
			self.annotate_byte_legacy(0x00)
			self.annotate_byte_legacy(0xFE, special_clock = True)
			self.field_start = self.byte_start
			self.display_field(field.ID_Address_Mark)
			self.IDcrc = 0
			self.byte_cnt = self.header_size
			self.pb_state = state.ID_Record

		elif self.pb_state == state.ID_Record:
			self.annotate_byte_legacy(val)
			self.IDrec[self.header_size - self.byte_cnt] = val
			self.byte_cnt -= 1
			if self.byte_cnt == 0:
				self.decode_id_rec(self.IDrec)
				self.display_field(field.ID_Record)
				if self.sector_size_auto and self.sector_size != self.IDlenv:
					self.sector_size = self.IDlenv
					self.DRrec = bytearray(self.sector_size)
				self.byte_cnt = self.header_crc_bytes
				self.pb_state = state.ID_Record_CRC

		elif self.pb_state == state.ID_Record_CRC:
			self.annotate_byte_legacy(val)
			self.IDcrc <<= 8
			self.IDcrc += val
			self.byte_cnt -= 1
			if self.byte_cnt == 0:
				self.calculate_crc_header((self.IDmark, self.IDrec))
				if self.crc_accum == self.IDcrc:
					self.display_field(field.CRC_Ok)
				else:
					self.display_field(field.CRC_Error)
				self.pb_state = state.first_Gap_Byte

		elif self.pb_state == state.Data_Address_Mark:
			self.annotate_byte_legacy(0x00)
			self.annotate_byte_legacy(val, special_clock = True)
			self.DRmark = [val]
			self.field_start = self.byte_start
			self.display_field(field.Data_Address_Mark)
			self.DRcrc = 0
			self.byte_cnt = self.sector_size
			self.pb_state = state.Data_Record

		elif self.pb_state == state.Data_Record:
			self.annotate_byte_legacy(val)
			self.DRrec[self.sector_size - self.byte_cnt] = val
			self.byte_cnt -= 1
			if self.byte_cnt == 0:
				self.display_field(field.Data_Record)
				self.byte_cnt = self.data_crc_bytes
				self.pb_state = state.Data_Record_CRC

		elif self.pb_state == state.Data_Record_CRC:
			self.annotate_byte_legacy(val)
			self.DRcrc <<= 8
			self.DRcrc += val
			self.byte_cnt -= 1
			if self.byte_cnt == 0:
				self.calculate_crc_data((self.DRmark, self.DRrec))
				if self.crc_accum == self.DRcrc:
					self.display_field(field.CRC_Ok)
				else:
					self.display_field(field.CRC_Error)
				self.pb_state = state.first_Gap_Byte

		elif self.pb_state == state.Index_Mark:
			self.annotate_byte_legacy(0x00)
			self.annotate_byte_legacy(0xFC, special_clock = True)
			self.field_start = self.byte_start
			self.display_field(field.Index_Mark)
			self.pb_state = state.first_Gap_Byte

		elif self.pb_state == state.first_Gap_Byte:	# process first gap byte after CRC or Index Mark
			self.annotate_byte_legacy(val)
			return -1								# done, unsync

		else:
			return -1

		return 0

	def process_byteMFM_legacy(self, val):
		if val == 0x1A1:
			self.pb_state = state.first_A1h_prefix
		elif val == 0x1C2:
			self.pb_state = state.first_C2h_prefix

		if self.pb_state == state.first_A1h_prefix:
			self.A1 = [0xA1]
			self.annotate_byte_legacy(0x00)
			self.annotate_byte_legacy(0xA1, special_clock = True)
			self.field_start = self.byte_start
			self.pb_state = state.second_A1h_prefix

		elif self.pb_state in (state.second_A1h_prefix, state.third_A1h_prefix):
			if val == 0x2A1:
				self.A1.append(0xA1)
				self.annotate_byte_legacy(0xA1, special_clock = True)
				if self.pb_state == state.second_A1h_prefix:
					self.pb_state = state.third_A1h_prefix
				elif self.pb_state == state.third_A1h_prefix:
					self.pb_state = state.IDData_Address_Mark
			else:
				self.display_field(field.Unknown_Byte)
				return -1

		elif self.pb_state == state.IDData_Address_Mark:
			if (self.header_size == 4 and val == 0xFE) or \
			   (self.header_size == 3 and (val & 0xFC) == 0xFC):	# FEh FC-FFh ID Address Mark
				self.IDmark = [val]
				self.annotate_byte_legacy(val)
				self.display_field(field.ID_Address_Mark)
				self.IDcrc = 0
				self.byte_cnt = self.header_size
				self.pb_state = state.ID_Record
			elif val >= 0xF8 and val <= 0xFB:						# F8h..FBh Data Address Mark
				self.DRmark = [val]
				self.annotate_byte_legacy(val)
				self.display_field(field.Data_Address_Mark)
				self.DRcrc = 0
				self.byte_cnt = self.sector_size
				self.pb_state = state.Data_Record
			else:
				self.display_field(field.Unknown_Byte)
				return -1

		elif self.pb_state == state.ID_Record:
			self.annotate_byte_legacy(val)
			self.IDrec[self.header_size - self.byte_cnt] = val
			self.byte_cnt -= 1
			if self.byte_cnt == 0:
				self.decode_id_rec(self.IDrec)
				self.display_field(field.ID_Record)
				if self.sector_size_auto and self.sector_size != self.IDlenv:
					self.sector_size = self.IDlenv
					self.DRrec = bytearray(self.sector_size)
				self.byte_cnt = self.header_crc_bytes
				self.pb_state = state.ID_Record_CRC

		elif self.pb_state == state.ID_Record_CRC:
			self.annotate_byte_legacy(val)
			self.IDcrc <<= 8
			self.IDcrc += val
			self.byte_cnt -= 1
			if self.byte_cnt == 0:
				self.calculate_crc_header((self.A1, self.IDmark, self.IDrec))
				if self.crc_accum == self.IDcrc:
					self.display_field(field.CRC_Ok)
				else:
					self.display_field(field.CRC_Error)
				self.pb_state = state.first_Gap_Byte

		elif self.pb_state == state.Data_Record:
			self.annotate_byte_legacy(val)
			self.DRrec[self.sector_size - self.byte_cnt] = val
			self.byte_cnt -= 1
			if self.byte_cnt == 0:
				self.display_field(field.Data_Record)
				self.byte_cnt = self.data_crc_bytes
				self.pb_state = state.Data_Record_CRC

		elif self.pb_state == state.Data_Record_CRC:
			self.annotate_byte_legacy(val)
			self.DRcrc <<= 8
			self.DRcrc += val
			self.byte_cnt -= 1
			if self.byte_cnt == 0:
				self.calculate_crc_data((self.A1, self.DRmark, self.DRrec))
				if self.crc_accum == self.DRcrc:
					self.display_field(field.CRC_Ok)
				else:
					self.display_field(field.CRC_Error)
				self.pb_state = state.first_Gap_Byte

		elif self.pb_state == state.first_C2h_prefix:
			self.annotate_byte_legacy(0x00)
			self.annotate_byte_legacy(0xC2, special_clock = True)
			self.field_start = self.byte_start
			self.pb_state = state.second_C2h_prefix

		elif self.pb_state in (state.second_C2h_prefix, state.third_C2h_prefix):
			if val == 0x2C2:
				self.annotate_byte_legacy(0xC2, special_clock = True)
				if self.pb_state == state.second_C2h_prefix:
					self.pb_state = state.third_C2h_prefix
				elif self.pb_state == state.third_C2h_prefix:
					self.pb_state = state.Index_Mark
			else:
				self.display_field(field.Unknown_Byte)
				return -1

		elif self.pb_state == state.Index_Mark:
			if val == 0xFC:
				self.annotate_byte_legacy(val)
				self.display_field(field.Index_Mark)
				self.pb_state = state.first_Gap_Byte
			else:
				self.display_field(field.Unknown_Byte)
				return -1

		elif self.pb_state == state.first_Gap_Byte:	# process first gap byte after CRC or Index Mark
			self.annotate_byte_legacy(val)
			return -1								# done, unsync

		else:
			return -1

		return 0

	def decode_legacy(self):
		# --- Verify that a sample rate was specified.

		if not self.samplerate:
			raise raise_exception('Cannot decode without samplerate.')

		# --- Initialize CRC Tables
		self.make_crc_table(self.header_crc_table, self.header_crc_poly, self.header_crc_size)
		if self.header_crc_poly == self.data_crc_poly:
			self.data_crc_table = self.header_crc_table
		else:
			self.make_crc_table(self.data_crc_table, self.data_crc_poly, self.data_crc_size)

		# Calculate maximum number of samples allowed between ID and Data Address Marks.
		# Cant put it in start() or metadata() becaue we cant be sure of order those
		# two are called, one initializes (samplerate) the other user options (data_rate)

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
		cell_window = ann.clk					# current half-bit-cell window, can be ann.clk or ann.dat
		v = 0									# 1 = edge in current window, 0 = no edge
		shift31 = 0								# 31-bit pattern shift register (of half-bit-cells)

		data_byte = 0							# 8-bit data byte shift register (of bit cells)
		bit_cnt = 0								# number of bits processed in current byte (0..8)
		byte_sync = False						# True = bit/byte-sync'd, False = not sync'd
		win_sync = False						# True = half-bit-cell window sync'd re ann.clk vs. ann.dat ?

		interval = 0							# current interval (in samples, 1..n)

		# FIFO (using circular buffers) of starting/ending sample numbers
		# and data values for 33 half-bit-cell windows. Data values are
		# number of leading edges per window (0..n).
		self.fifo_size = 100
		self.fifo_ws = array('l', [0 for _ in range(self.fifo_size)])
		self.fifo_we = array('l', [0 for _ in range(self.fifo_size)])
		self.fifo_wv = array('l', [0 for _ in range(self.fifo_size)])

		self.fifo_wp = -1			# index where last FIFO entry was written (0..32)
		self.fifo_rp = 0			# index where to read next FIFO entry (0..32)
		self.fifo_cnt = 0			# number of entries currently in FIFO (0..33)

		# --- Process all input data.

		while True:

			# Wait for leading edge (rising or falling) on channel 0.  Also handle
			# extra pulses on channel 1, and disable/suppress signal on channel 2.

			if self.rising_edge:
				(data_pin, extra_pin, suppress_pin) = self.wait([{0: 'r', 2: 'l'}, {1: 'r', 2: 'l'}])
			else:
				(data_pin, extra_pin, suppress_pin) = self.wait([{0: 'f', 2: 'l'}, {1: 'r', 2: 'l'}])

			# Calculate interval since previous leading edge.


			if self.last_samplenum is None:
				interval = int(bc10N)
			else:
				interval = self.samplenum - self.last_samplenum

			if self.last_samplenum is not None:
				interval_nsec = int(((interval * 1000) + (self.samplerateMSps / 2)) / self.samplerateMSps)

			self.chunks += 1
			self.Intrvls += 1

			# Update averaged half-bit-cell window size if interval within tolerance.
			# Also display leading-edge to leading-edge annotation, showing starting
			# sample number, and interval in nsec.

			if self.format == coding.FM:
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
					if self.show_sample_num:
						annotate = ['s%d i%dns' % (self.last_samplenum, interval_nsec), '%dns' % interval_nsec]
					else:
						annotate = ['%dns' % interval_nsec]
					self.put(self.last_samplenum, self.samplenum, self.out_ann,	[ann.pul, annotate])
			else:
				if self.last_samplenum is not None:
					self.put(self.samplenum - 1, self.samplenum, self.out_ann, message.error)
					if self.show_sample_num:
						annotate = ['s%d i%dns out-of-tolerance leading edge' % (self.last_samplenum, interval_nsec), 's%d i%dns OoTI' % (self.last_samplenum, interval_nsec), 's%d OoTI' % self.last_samplenum, 'OoTI']
					else:
						annotate = ['%dns out-of-tolerance leading edge' % interval_nsec, '%dns OoTI' % interval_nsec, 'OoTI']
					self.put(self.last_samplenum, self.samplenum, self.out_ann,	[ann.erp, annotate])

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

				win_start = int(round(window_start))
				win_end = int(round(window_end))

				# Display all MFM mC2h and mA1h prefix bytes to help with locating damaged records.

				if self.format == coding.MFM and self.dsply_pfx:
					if (shift31 & 0xFFFF) == 0x4489:
						self.put(win_start, win_end, self.out_ann, message.prefixA1)
					elif (shift31 & 0xFFFF) == 0x5224:
						self.put(win_start, win_end, self.out_ann, message.prefixC2)

				# Store start/end of current window and its value into FIFO.

				self.inc_fifo_wp()
				self.fifo_ws[self.fifo_wp] = win_start
				self.fifo_we[self.fifo_wp] = win_end
				self.fifo_wv[self.fifo_wp] = v

				# Not sync'd yet, look for sync pattern.
				# The FIFO must have exactly 33 entries in it.

				if (not byte_sync) and (self.fifo_cnt == 33):

					# Process FM patterns.
					if self.format == coding.FM:

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

						if self.format == coding.FM:
							self.process_byteFM_legacy(data_byte)
						else:
							self.process_byteMFM_legacy(data_byte)

						cell_window = ann.dat
						bit_cnt = 0

				# Already sync'd, process next data bit.
				elif cell_window == ann.dat:

					data_byte = ((data_byte & 0x7F) << 1) + v
					bit_cnt += 1

					# Process and display next complete data byte.
					# The FIFO must have exactly 17 entries in it.
					if bit_cnt == 8 and self.fifo_cnt == 17:

						# Process FM byte.
						if self.format == coding.FM:

							if self.process_byteFM_legacy(data_byte) == 0:
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

							if self.process_byteMFM_legacy(data_byte) == 0:
								bit_cnt = 0
							else:
								shift31 = 0
								byte_sync = False

				# Display one half-bit-cell window annotation.	(If not sync'd,
				# annotate_bits() won't be called to pull entries from the FIFO,
				# but it needs to have 33-1+1 entries for self.process_byteFM/MFM().)

				# We are annotating garbage or last bit of "first gap byte after CRC or Index Mark".
				# win_sync = True can only happen if its last bit of "first gap byte after CRC or Index Mark"
				# Its because annotate_bits() starts "with the data window of the last bit of the previous byte.
				# The last window of the current byte is read but not removed from the FIFO, and isn't displayed."
				# win_sync = False - unknown bits in unsynced space
				# Maybe there is a better way than processing 7 bits of current byte and one bit of previous one??

				if self.fifo_cnt >= 33:

					win_start = self.fifo_ws[self.fifo_rp]
					win_end = self.fifo_we[self.fifo_rp]
					win_val = self.fifo_wv[self.fifo_rp]
					self.inc_fifo_rp()

					if win_sync:
						self.annotate_window(ann.dat, win_start, win_end, win_val)
						win_sync = False
					else:
						self.annotate_window(ann.unk, win_start, win_end, win_val)

				# Toggle clock vs. data state.
				if cell_window == ann.dat:
					cell_window = ann.clk
				else:
					cell_window = ann.dat

				# Calculate next half-bit-cell window location.
				window_start = window_end
				window_end += window_size

				# If edge processed in current window, get next edge.
				if v == 1:	break

				#--- end while


			# Store data for next round.
			self.last_samplenum = self.samplenum

	def decode(self):
		if self.decoder_legacy:
			self.decode_legacy()
		else:
			self.decode_PLL()
