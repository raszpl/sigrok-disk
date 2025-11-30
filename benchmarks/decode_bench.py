import random
import timeit
import sys, os
from array import array
import platform

class Decoder(object):
	__slots__ = ('cells_allowed_max', 'cells_allowed_min', 'code_0b000100', 'code_0b100100', 'decode', 'format', 'format_current', 'halfbit', 'halfbit_cells', 'halfbit_nom', 'halfbit_nom05', 'halfbit_nom15', 'integrator', 'ki', 'kp', 'last_last_samplenum', 'last_samplenum', 'limits_key', 'owner', 'phase_ref', 'pll_sync_tolerance', 'pulse_ticks', 'ring_ptr', 'ring_size', 'no_match', 'RLL_TABLE', 'codemap', 'shift', 'shift_byte', 'shift_decoded', 'shift_decoded_1', 'shift_decodedd', 'shift_decoded_11', 'shift_index', 'state', 'sync_lock_count', 'sync_lock_threshold', 'sync_marks', 'LUT', 'aLUT', 'DICK', 'memoryview', 'barray')
	def __init__(self):
		self.shift_byte = 0
		self.shift = 0
		self.shift_index = 0
		self.LUT = [0] * (0x5556)
		self.aLUT = array('H', [0 for _ in range(0x5556)])
		self.DICK = {}
		self.barray = bytearray(0x5556)
		self.memoryview = memoryview(self.barray)
		
		self.codemap = {
			'1000': '11',
			'0100': '10',
			'100100': '010',
			'001000': '011',
			'000100': '000',
			'00100100': '0010',
			'00001000': '0011'
		}
		self.RLL_TABLE = {
			0b00100001000: 0b11,
			0b00100000100: 0b10,
			0b01000100100: 0b000,
			0b01000000100: 0b010,
			0b01000001000: 0b011,
			0b10000100100: 0b0010,
			0b10000001000: 0b0011
		}
		self.shift_decodedd = ''
		self.shift_decoded = 0
		self.shift_decoded_1 = 0
		self.no_match = 0
# - FM ----------------------------------------------------------------------
class DecoderBitwise(Decoder):
	def decode(self):
		self.shift_index -= 16
		self.shift_byte = (self.shift >> self.shift_index) & 0x5555
		self.shift_byte = ((self.shift_byte & 0b100000000000000) >> 7) \
						| ((self.shift_byte & 0b1000000000000) >> 6) \
						| ((self.shift_byte & 0b10000000000) >> 5) \
						| ((self.shift_byte & 0b100000000) >> 4) \
						| ((self.shift_byte & 0b1000000) >> 3) \
						| ((self.shift_byte & 0b10000) >> 2) \
						| ((self.shift_byte & 0b100) >> 1) \
						| (self.shift_byte & 1)
		return True
class DecoderBitwiseAd(Decoder):
	def decode(self):
		self.shift_index -= 16
		self.shift_byte = (self.shift >> self.shift_index) & 0x5555
		self.shift_byte = ((self.shift_byte & 0b100000000000000) >> 7) \
						+ ((self.shift_byte & 0b1000000000000) >> 6) \
						+ ((self.shift_byte & 0b10000000000) >> 5) \
						+ ((self.shift_byte & 0b100000000) >> 4) \
						+ ((self.shift_byte & 0b1000000) >> 3) \
						+ ((self.shift_byte & 0b10000) >> 2) \
						+ ((self.shift_byte & 0b100) >> 1) \
						+ (self.shift_byte & 1)
		return True
class DecoderSWAR(Decoder):
	def decode(self):
		self.shift_index -= 16
		self.shift_byte = (self.shift >> self.shift_index) & 0x5555
		self.shift_byte = (self.shift_byte + (self.shift_byte >> 1)) & 0x3333
		self.shift_byte = (self.shift_byte + (self.shift_byte >> 2)) & 0x0F0F
		self.shift_byte = (self.shift_byte + (self.shift_byte >> 4)) & 0x00FF
		return True
class DecoderSWARlocal(Decoder):
	def decode(self):
		self.shift_index -= 16
		shift_byte = (self.shift >> self.shift_index) & 0x5555
		shift_byte = (shift_byte + (shift_byte >> 1)) & 0x3333
		shift_byte = (shift_byte + (shift_byte >> 2)) & 0x0F0F
		self.shift_byte = (shift_byte + (shift_byte >> 4)) & 0x00FF
		return True
class DecoderLUT(Decoder):
	def decode(self):
		self.shift_index -= 16
		self.shift_byte = self.LUT[(self.shift >> self.shift_index) & 0x5555]
		return True
class DecoderarrayLUT(Decoder):
	def decode(self):
		self.shift_index -= 16
		self.shift_byte = self.aLUT[(self.shift >> self.shift_index) & 0x5555]
		return True
class DecoderbarrayLUT(Decoder):
	def decode(self):
		self.shift_index -= 16
		self.shift_byte = self.barray[(self.shift >> self.shift_index) & 0x5555]
		return True
class DecodermemoryviewLUT(Decoder):
	def decode(self):
		self.shift_index -= 16
		self.shift_byte = self.memoryview[(self.shift >> self.shift_index) & 0x5555]
		return True
class DecoderDICK(Decoder):
	def decode(self):
		self.shift_index -= 16
		self.shift_byte = self.DICK[(self.shift >> self.shift_index) & 0x5555]
		return True
# - RLL ----------------------------------------------------------------------
class DecoderSTR(Decoder):
	def decode(self):
		RLL_TABLE = self.codemap
		shift_win = self.shift & (2 ** self.shift_index -1)

		#print('RLL_1', bin(self.shift)[1:], self.shift_index, bin(shift_win)[2:])
		#print('RLL_1', bin(self.shift)[1:], self.shift_index, bin(shift_win)[2:].zfill(self.shift_index))
		binary_str = bin(shift_win)[2:].zfill(self.shift_index)
		#print('RLL input', bin(shift_win)[1:], binary_str)
		binary_str_len = len(binary_str)
		decoded = self.shift_decodedd
		i = 0
		while len(decoded) < 8:
			matched = False
			for pattern_length in [8, 6, 4]:
				if i + pattern_length <= binary_str_len:
					pattern = binary_str[i:i + pattern_length]
					if pattern in RLL_TABLE:
						decoded += RLL_TABLE[pattern]
						i += pattern_length
						self.shift_index -= pattern_length
						self.shift_decoded_1 += pattern_length
						#print_("RLL() decoded:", decoded, 'pattern:', RLL_TABLE[pattern], 'raw:', pattern, 'i', i)
						matched = True
						break
			if not matched:
				if binary_str_len - i > 7:
					# TODO: Emit whatever and signal upstream we got decoder fail
					# but try to keep synced and handle bad data upstream using ECC?
					# For now just raise exception? or not
					#print_("rll_decode catastrophic fail, Max codeword length reached without match, resetting!", self.shift_decoded_1, binary_str_len, i, decoded, self.codemap_key, binary_str, pattern)
					#raise raise_exception("rll_decode catastrophic fail! Max codeword length reached without match. Exception raised.")
					self.no_match += 1
					return False
				#print_("RLL not matched", binary_str[i:], decoded, i)
				self.shift_decodedd = decoded
				return False

		#print_('RLL_shift', bin(self.shift)[1:], decoded[:8], self.shift_index, self.shift_decoded_1, self.last_samplenum)
		self.shift_byte = int(decoded[:8], 2)
		self.shift_decodedd = decoded[8:]
		self.shift_decoded_1 -= 16
		return True
class DecoderBIN(Decoder):
	def decode(self):
		top_bits = 0
		while True:
			#print(bin(self.shift & ((1 << self.shift_index) - 1))[2:].zfill(self.shift_index), self.shift_index, self.shift_decoded_1, bin(self.shift_byte), 'rll_decode')
			#top_bits = (self.shift >> self.shift_index - 8) & 0xff

			if self.shift_decoded_1 >= 16:
				self.shift_decoded_1 -= 16
				self.shift_byte = (self.shift_decoded >> (self.shift_decoded_1 // 2)) & 0xff
				self.shift_decoded &= 0xF
				return True

			if self.shift_index >= 8:
				top_bits = (self.shift >> self.shift_index - 8) & 0xff
				#print(bin(top_bits)[2:].zfill(8), self.shift_index, self.shift_decoded_1, bin(self.shift_byte), 'rll_decode8')
				if top_bits == 0b00100100:
					#print('00100100 match 0010')
					self.shift_decoded = (self.shift_decoded << 4) + 0b0010
					self.shift_decoded_1 += 8
					self.shift_index -= 8
					continue
				
				elif top_bits == 0b00001000:
					#print('00001000 match 0011')
					self.shift_decoded = (self.shift_decoded << 4) + 0b0011
					self.shift_decoded_1 += 8
					self.shift_index -= 8
					continue

			if self.shift_index >= 6:
				top_6bits = (self.shift >> self.shift_index - 6) & 0b111111
				#print(bin(top_6bits)[2:].zfill(6), self.shift_index, self.shift_decoded_1, bin(self.shift_byte), 'rll_decode6')
				#top_6bits = top_bits >> 2
				if top_6bits == 0b100100:
					#print('100100 match 010')
					self.shift_decoded = (self.shift_decoded << 3) + 0b010
					self.shift_decoded_1 += 6
					self.shift_index -= 6
					continue
	
				elif top_6bits == 0b001000:
					#print('001000 match 011')
					self.shift_decoded = (self.shift_decoded << 3) + 0b011
					self.shift_decoded_1 += 6
					self.shift_index -= 6
					continue
	
				elif top_6bits == 0b000100:
					#print('000100 match 000')
					self.shift_decoded = self.shift_decoded << 3
					self.shift_decoded_1 += 6
					self.shift_index -= 6
					continue

			if self.shift_index >= 4:
				top_4bits = (self.shift >> self.shift_index - 4) & 0b1111
				#print(bin(top_4bits)[2:].zfill(4), self.shift_index, self.shift_decoded_1, bin(self.shift_byte), 'rll_decode4')
				#top_4bits = top_bits >> 4
				if top_4bits == 0b1000:
					#print('1000 match 11')
					self.shift_decoded = (self.shift_decoded << 2) + 0b11
					self.shift_decoded_1 += 4
					self.shift_index -= 4
					continue
	
				elif top_4bits == 0b0100:
					#print('0100 match 10')
					self.shift_decoded = (self.shift_decoded << 2) + 0b10
					self.shift_decoded_1 += 4
					self.shift_index -= 4
					continue
	
			if self.shift_index >= 8:
				print("ERROR: no matches, skip whole byte")
				self.shift_index -= 16 - shift_decoded_1
				#print(hex(self.shift_byte), bin(self.shift_byte), self.shift_index, self.shift_decoded_1)
				break
			break
		return False
class DecoderBINunrolled(Decoder):
	def decode(self):
		top_bits = 0
		while True:
			if self.shift_decoded_1 >= 16:
				self.shift_decoded_1 -= 16
				self.shift_byte = (self.shift_decoded >> (self.shift_decoded_1 // 2)) & 0xff
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
					
				#top_bits = top_bits >> 2
				top_bits = top_bits & 0b11111100
				if top_bits == 0b10010000:
					self.shift_decoded = (self.shift_decoded << 3) + 0b010
					self.shift_decoded_1 += 6
					self.shift_index -= 6
					continue
	
				elif top_bits == 0b00100000:
					self.shift_decoded = (self.shift_decoded << 3) + 0b011
					self.shift_decoded_1 += 6
					self.shift_index -= 6
					continue
	
				elif top_bits == 0b00010000:
					self.shift_decoded = self.shift_decoded << 3
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
				
				print("ERROR: no matches, skip whole byte")
				self.shift_index -= 16 - shift_decoded_1
				self.shift_decoded_1 = 0
				return False
	
			elif self.shift_index >= 6:
				top_bits = (self.shift >> self.shift_index - 6) & 0b111111
				if top_bits == 0b100100:
					self.shift_decoded = (self.shift_decoded << 3) + 0b010
					self.shift_decoded_1 += 6
					self.shift_index -= 6
					continue
	
				elif top_bits == 0b001000:
					self.shift_decoded = (self.shift_decoded << 3) + 0b011
					self.shift_decoded_1 += 6
					self.shift_index -= 6
					continue
	
				elif top_bits == 0b000100:
					self.shift_decoded = self.shift_decoded << 3
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
class DecoderBINloop(Decoder):
	def decode(self):
		RLL_TABLE = self.RLL_TABLE
		while self.shift_decoded_1 < 16:
			matched = False
			for pattern_length, mask, adder in [
						(8, 255, 1024),
						(6, 63,  512),
						(4, 15,  256),
			]:
				if self.shift_index >= pattern_length:
					pattern = ((self.shift >> self.shift_index - pattern_length) & mask) + adder
					#print(bin(self.shift)[1:])
					#print('pattern', bin(pattern), self.shift_index, pattern_length, self.shift_index - pattern_length, pattern in RLL_TABLE)
					if pattern in RLL_TABLE:
						self.shift_index -= pattern_length
						self.shift_decoded = (self.shift_decoded << pattern_length) + RLL_TABLE[pattern]
						self.shift_decoded_1 += pattern_length
						matched = True
						break
			if not matched:
				if self.shift_index >= 8:
					print("RLL not matched and self.shift_index - i > 7", self.shift_index, self.shift_decoded, i)
					return False
				return False

		#print('decoded=', decoded, decoded[:8])
		self.shift_decoded_1 -= 16
		self.shift_byte = (self.shift_decoded >> (self.shift_decoded_1 // 2)) & 0xff
		self.shift_decoded &= 0xF
		#print('decoded:', self.shift_byte)
		return True
# -----------------------------------------------------------------------
def build_FM_LUT():
	decoderSWAR = DecoderSWAR()
	decoderLUT = DecoderLUT()
	decoderarrayLUT = DecoderarrayLUT()
	decoderDICK = DecoderDICK()
	decoderbarrayLUT = DecoderbarrayLUT()
	decodermemoryviewLUT = DecodermemoryviewLUT()
	

	for index in range(0x5556):
		x = index & 0x5555
		decoderSWAR.shift = x
		decoderSWAR.shift_index += 16
		decoderSWAR.decode()
		x = decoderSWAR.shift
		decoderLUT.LUT[x] = decoderSWAR.shift_byte
		decoderarrayLUT.aLUT[x] = decoderSWAR.shift_byte
		decoderDICK.DICK[x] = decoderSWAR.shift_byte
		# bytearray lookup table idea taken from greaseweazle
		decoderbarrayLUT.barray[x] = decoderSWAR.shift_byte
		decodermemoryviewLUT.barray[x] = decoderSWAR.shift_byte

	return decoderLUT, decoderarrayLUT, decoderDICK, decoderbarrayLUT, decodermemoryviewLUT

def build_random_data(symbol, pulse_count):
	start = timeit.default_timer()

	random.seed(42)
	random_list = bytearray()

	current_sum = 0
	total_mib = pulse_count / (1024.0 * 1024.0)

	filename = "data_{}.bin".format(symbol)
	if os.path.exists(filename) and os.path.getsize(filename) >= pulse_count:
		try:
			with open(filename, 'rb') as f:
				random_list = f.read(pulse_count)
			elapsed = timeit.default_timer() - start
			print("%.2f MiB of random %s Pulse data loaded from %s: %3.3f seconds" % (total_mib, symbol, filename, elapsed), '\n')
			return random_list

		except Exception as e:
			print("Error loading cache, regenerating: %s" % e)

	if symbol in ('FM', 'MFM'):
		encoding = {
			"FM":	(1, 2),	# (0,1) RLL
			#"GCR":	(1, 3),	# (0,2) RLL
			"MFM":	(2, 4),	# (1,3) RLL
			#"RLL":	(3, 8),	# (2,7) RLL
		}
		min_value, max_value = encoding[symbol]
		population = range(min_value, max_value + 1)
		avg_per_item = (min_value + max_value) / 2 * 1.5
		if hasattr(random, 'choices'):
			while current_sum < pulse_count:
				need = pulse_count - current_sum
				approx_items = min(10000, int(need / avg_per_item) + 1000)
			
				batch = random.choices(population, k=approx_items)
				random_list.extend(batch)
				current_sum += sum(batch)
			
				if current_sum >= pulse_count:
					excess = current_sum - pulse_count
					while excess > 0 and random_list:
						last = random_list.pop()
						if last <= excess:
							excess -= last
						else:
							random_list.append(last - excess)
							excess = 0
			
			del random_list[pulse_count:]
		else:
			random_number = 0
			max_value += 1
			while current_sum < pulse_count:
				random_number = random.randrange(min_value, max_value)
				random_list.append(random_number)
				current_sum += random_number
	elif symbol == 'RLL':
			RLL_IBM = [
				([1],	 3),	#(0b1000,		3), 
				([2],	 2),	#(0b0100,		3), 
				([3],	 3),	#(0b001000,		5), 
				([4],	 2),	#(0b000100,		5), 
				([1, 3], 2),	#(0b100100,		5), 
				([5],	 3),	#(0b00001000,	7), 
				([3, 3], 2),	#(0b00100100,	7)	
			]
			pending_zeros = 0
			i = 0
			while i < pulse_count:
				pulses, pending_zero = RLL_IBM[random.randrange(7)]
				#print("pulses:", pulses)
				
				for pulse in pulses:
					random_list.append(pulse + pending_zeros)
					#print("pulse:", pulse + pending_zeros)
					pending_zeros = 0
					i += 1
				
				pending_zeros = pending_zero

				if i > 2011111111111111111111:
					exit()

	elapsed = timeit.default_timer() - start

	print("%.2f MiB of random %s Pulse data creation: %3.3f seconds" % (total_mib, symbol, elapsed), '\n')

	if not os.path.exists(filename) or os.path.getsize(filename) < pulse_count:
		try:
			with open(filename, "wb") as f:
				f.write(bytearray(random_list))
		except:
			pass

	return random_list

def build_LUT():
	start = timeit.default_timer()

	decode_list = bytearray()
	for x in range(0x5555+1):
		y = 0
		for i in range(16):
			if x&(1<<(i*2)):
				y |= 1<<i
		decode_list.append(y)

	elapsed = timeit.default_timer() - start
	print("greaseweazle LUT creation:	%9.3f seconds" % elapsed)

	start = timeit.default_timer()

	barray = bytearray(0x5556)
	for x in range(0x5556):
		# bytearray lookup table idea from greaseweazle
		index = x & 0x5555
		y = (index + (index >> 1)) & 0x3333
		y = (y + (y >> 2)) & 0x0F0F
		y = (y + (y >> 4)) & 0x00FF
		barray[index] = y

	elapsed = timeit.default_timer() - start
	print("SWAR LUT creation:		%9.3f seconds" % elapsed)

def run_benchmark(decoder, name, calls, data):
	start = timeit.default_timer()

	byte_decoded = 0
	i = 0
	max = len(data)
	while True:
	#for i in range(len(data)):
		decoder.shift = ((decoder.shift << data[i]) + 1) & 0xffffffffff
		decoder.shift_index += data[i]
		if decoder.shift_index + decoder.shift_decoded_1 >= 16:
			if decoder.decode():
				byte_decoded += 1
			
			#print("decode:", bin(decoder.shift), decoder.shift_index, decoder.shift_decoded_1)
			#if decoder.decode():
			#	print(i, hex(decoder.shift_byte))
			#print("decod_:", decoder.shift_index, decoder.shift_decoded_1, hex(decoder.shift_byte))

		i += 1
		if i >= max:
			break

	elapsed = timeit.default_timer() - start
	
	total_mib = byte_decoded / (1024.0 * 1024.0)
	
	mb_per_sec = total_mib / elapsed if elapsed > 0 else 0
	print("%-30s : %9.3f seconds  ->  %6.2f MiB/s" % (name, elapsed, mb_per_sec))

def main():
	
	pulse_count = 1048576 // 1 * 1
	total_mib = pulse_count / (1024.0 * 1024.0)

	print("Python version:", platform.python_version())
	print("Benchmark decoding {:.2f} MiB of raw datastream\n".format(total_mib))

	print("-- RLL decoding -----------------------------------")
	random_data = build_random_data('RLL', pulse_count)
	run_benchmark(DecoderSTR(), "RLL string shifts", pulse_count, random_data)
	run_benchmark(DecoderBIN(), "RLL binary shifts", pulse_count, random_data)
	run_benchmark(DecoderBINunrolled(), "RLL binary shifts unrolled", pulse_count, random_data)
	run_benchmark(DecoderBINloop(), "RLL binary shift loop", pulse_count, random_data)

	print("-- FM decoding -----------------------------------")
	random_data = build_random_data('FM', pulse_count)

	decoderLUT, decoderarrayLUT, decoderDICK, decoderbarrayLUT, decodermemoryviewLUT = build_FM_LUT()

	print(" List		: {:8.2f} KiB".format(sys.getsizeof(decoderLUT.LUT) / 1024.0))
	print(" Array		: {:8.2f} KiB".format(sys.getsizeof(decoderarrayLUT.aLUT) / 1024.0))
	print(" DICK		: {:8.2f} KiB".format(sys.getsizeof(decoderDICK.DICK) / 1024.0), "doent account for keys and values, so add 22KB")
	print(" bytearray	: {:8.2f} KiB".format(sys.getsizeof(decoderbarrayLUT.barray) / 1024.0))
	print("-" * 50)
	build_LUT()
	print("-" * 50)
	print("%-18s   time			speed" % "Method")
	print("-" * 50)
	run_benchmark(DecoderBitwise(), "Bitwise", pulse_count, random_data)
	run_benchmark(DecoderBitwiseAd(), "BitwiseAd", pulse_count, random_data)
	run_benchmark(DecoderSWAR(), "SWAR", pulse_count, random_data)
	run_benchmark(DecoderSWARlocal(), "SWAR local", pulse_count, random_data)
	run_benchmark(decoderLUT, "LUT", pulse_count, random_data)
	run_benchmark(decoderarrayLUT, "array LUT", pulse_count, random_data)
	run_benchmark(decoderDICK, "DICK LUT", pulse_count, random_data)
	run_benchmark(decoderbarrayLUT, "bytearray LUT", pulse_count, random_data)
	run_benchmark(decodermemoryviewLUT, "memoryview LUT", pulse_count, random_data)

"""
# i7-4790 results:

Python version: 3.4.0
Benchmark decoding 1.00 MiB of raw datastream

-- RLL decoding -----------------------------------
1.00 MiB of random RLL Pulse data loaded from data_RLL.bin: 0.001 seconds

RLL string shifts              :     2.418 seconds  ->    0.12 MiB/s
RLL binary shifts              :     1.773 seconds  ->    0.16 MiB/s
RLL binary shifts unrolled     :     1.609 seconds  ->    0.18 MiB/s
RLL binary shift loop          :     2.106 seconds  ->    0.14 MiB/s
-- FM decoding -----------------------------------
1.00 MiB of random FM Pulse data loaded from data_FM.bin: 0.001 seconds

 List           :    85.37 KiB
 Array          :    42.70 KiB
 DICK           :     6.05 KiB doent account for keys and values, so add 22KB
 bytearray      :    21.36 KiB
--------------------------------------------------
greaseweazle LUT creation:          0.066 seconds
SWAR LUT creation:                  0.011 seconds
--------------------------------------------------
Method               time                       speed
--------------------------------------------------
Bitwise                        :     0.745 seconds  ->    0.13 MiB/s
BitwiseAd                      :     0.731 seconds  ->    0.13 MiB/s
SWAR                           :     0.690 seconds  ->    0.14 MiB/s
SWAR local                     :     0.654 seconds  ->    0.14 MiB/s
LUT                            :     0.625 seconds  ->    0.15 MiB/s
array LUT                      :     0.626 seconds  ->    0.15 MiB/s
DICK LUT                       :     0.632 seconds  ->    0.15 MiB/s
bytearray LUT                  :     0.628 seconds  ->    0.15 MiB/s
memoryview LUT                 :     0.629 seconds  ->    0.15 MiB/s

===================================================================================

Python version: 3.14.0
Benchmark decoding 1.00 MiB of raw datastream

-- RLL decoding -----------------------------------
1.00 MiB of random RLL Pulse data loaded from data_RLL.bin: 0.000 seconds

RLL string shifts              :     1.041 seconds  ->    0.28 MiB/s
RLL binary shifts              :     0.676 seconds  ->    0.43 MiB/s
RLL binary shifts unrolled     :     0.592 seconds  ->    0.49 MiB/s
RLL binary shift loop          :     0.830 seconds  ->    0.35 MiB/s
-- FM decoding -----------------------------------
1.00 MiB of random FM Pulse data loaded from data_FM.bin: 0.001 seconds

 List           :   170.73 KiB
 Array          :    42.75 KiB
 DICK           :     9.09 KiB doent account for keys and values, so add 22KB
 bytearray      :    21.39 KiB
--------------------------------------------------
greaseweazle LUT creation:          0.032 seconds
SWAR LUT creation:                  0.005 seconds
--------------------------------------------------
Method               time                       speed
--------------------------------------------------
Bitwise                        :     0.299 seconds  ->    0.31 MiB/s
BitwiseAd                      :     0.299 seconds  ->    0.31 MiB/s
SWAR                           :     0.288 seconds  ->    0.33 MiB/s
SWAR local                     :     0.284 seconds  ->    0.33 MiB/s
LUT                            :     0.264 seconds  ->    0.36 MiB/s
array LUT                      :     0.265 seconds  ->    0.35 MiB/s
DICK LUT                       :     0.267 seconds  ->    0.35 MiB/s
bytearray LUT                  :     0.264 seconds  ->    0.36 MiB/s
memoryview LUT                 :     0.265 seconds  ->    0.35 MiB/s
"""

if __name__ == "__main__":
	main()