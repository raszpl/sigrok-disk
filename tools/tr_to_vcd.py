# ugly, but works :-)
import struct
import sys
import os
import argparse

def calculate_crc32(data):
	bits = 32
	offset = 24
	poly = 0x140a0445
	mask = 0xffffffff
	crc = 0xffffffff

	for byte in data:
		crc ^= (byte << offset)
		crc &= mask
		for i in range(8):
			check = crc & (1 << (bits - 1))
			crc = (crc << 1) & mask
			if check:
				crc ^= poly
				crc &= mask
	return crc

def unpack_deltas(data_bytes):
	deltas = []
	i = 0
	while i < len(data_bytes):
		if data_bytes[i] == 255:
			if i + 3 >= len(data_bytes):
				break
			value = data_bytes[i+1] + (data_bytes[i+2] << 8) + (data_bytes[i+3] << 16)
			i += 4
		elif data_bytes[i] == 254:
			if i + 2 >= len(data_bytes):
				break
			value = data_bytes[i+1] + (data_bytes[i+2] << 8)
			i += 3
		else:
			value = data_bytes[i]
			i += 1
		deltas.append(value)
	return deltas

def dump_track_data_vcd(track_data, comment, timestamp, output_file=None, track_idx=None):
	if timestamp == 0:
		write_mode = 'w'
	else:
		write_mode = 'a'

	lines = [
		"$comment",
		comment,
		"$end",
		"$timescale 5 ns $end",
		"$var wire 1 ! 0 $end",
		"$enddefinitions $end",
		f"#{timestamp} 0!"
	]
	deltas = unpack_deltas(track_data)
	for delta in deltas:
		timestamp += delta
		lines.append(f"#{timestamp} 1!")
		lines.append(f"#{timestamp+1} 0!")

	content = "\n".join(lines) + "\n"

	if output_file is None:
		timestamp += 1
		# Clean stdout mode (used with -p)
		sys.stdout.write(content)
	else:
		file, ext = os.path.splitext(output_file)
		print(file, ext, output_file)
		if not ext:
			ext = "vcd"
		file += '.' + ext
		if '{track}' in file:
			file = file.format(track=track_idx)
			timestamp = 0
		else:
			timestamp += 1

		print(f"Writing {file}")
		with open(file, write_mode) as f:
			f.write(content)

	return timestamp

def seek_track(f, target_track, is_emulator, track_header_size, track_data_size, offset_first_track):
	current_track = 0
	current_pos = offset_first_track
	f.seek(offset_first_track)

	if is_emulator:
		while current_track < target_track:
			current_pos += track_header_size + track_data_size
			f.seek(current_pos)
			if current_pos != f.tell():
				return False

			current_track += 1
	else:
		while current_track < target_track:
			current_pos += 8
			f.seek(current_pos)
			if current_pos != f.tell():
				return False

			current_pos += 4
			num_data_bytes_bytes = f.read(4)
			if len(num_data_bytes_bytes) < 4:
				return False

			current_pos += struct.unpack('<I', num_data_bytes_bytes)[0] + 4	 # add data + CRC
			f.seek(current_pos)
			if current_pos != f.tell():
				return False

			current_track += 1

	return True

def print_track_header(f, is_emulator, track_data_size, num_cylinders, num_heads, track_count, track_start_pos):
	if is_emulator:
		# Emulator track header: marker, cylinder, head
		marker = f.read(4)
		if len(marker) < 4:
			# EOF
			return False, None, None, None
		marker_val = struct.unpack('<I', marker)[0]
		if marker_val != 0x12345678:
			print(f"Warning: Invalid track header marker at track {track_count}: {marker_val:08x} (expected 0x12345678)", file=sys.stderr)
			# Continue instead of raise, to handle potential mismatches
		cylinder = struct.unpack('<i', f.read(4))[0]
		head = struct.unpack('<i', f.read(4))[0]
		data_size = track_data_size
	else:
		# Transition track header: cylinder, head, data bytes (12 bytes total)
		cylinder_bytes = f.read(4)
		if len(cylinder_bytes) < 4:
			# EOF
			return False, None, None, None
		cylinder = struct.unpack('<i', cylinder_bytes)[0]
		head_bytes = f.read(4)
		if len(head_bytes) < 4:
			# EOF
			return False, None, None, None
		head = struct.unpack('<i', head_bytes)[0]
		num_data_bytes_bytes = f.read(4)
		if len(num_data_bytes_bytes) < 4:
			# EOF
			return False, None, None, None
		data_size = struct.unpack('<I', num_data_bytes_bytes)[0]

	if cylinder == -1 and head == -1:
		print("End of file marker (cylinder=-1, head=-1)", file=sys.stderr)
		return False, -1, -1, 0

	# Validate track bounds
	if not (0 <= cylinder < num_cylinders and 0 <= head < num_heads):
		print(f"Invalid track bounds at position {track_start_pos}: cyl {cylinder}, head {head} (expected 0-{num_cylinders-1}, 0-{num_heads-1})", file=sys.stderr)
		return False, cylinder, head, data_size

	return True, cylinder, head, data_size

def verify_track_crc(f, track_start_pos, track_header_size, num_data_bytes, silent):
	# Read data + checksum
	data = f.read(num_data_bytes)
	if len(data) != num_data_bytes:
		print("	 Warning: Short data read for CRC verification.", file=sys.stderr)
		return None
	checksum_bytes = f.read(4)
	if len(checksum_bytes) != 4:
		print("	 Warning: Missing checksum for verification.", file=sys.stderr)
		return None
	read_crc = struct.unpack('<I', checksum_bytes)[0]

	# Compute CRC over header (rewind and read) + data
	f.seek(track_start_pos)
	header_plus_data = f.read(track_header_size + num_data_bytes)
	computed_crc = calculate_crc32(header_plus_data)
	if not silent:
		print(f"  Track CRC: read {read_crc:08x}, computed {computed_crc:08x}")
		if computed_crc != read_crc:
			print("	 Warning: Track CRC mismatch", file=sys.stderr)
	return data

def parse_track_range(range_str, max_Range):
	# Parse a string like '5', '3-7', '10-', '-5', '-2,5,10-15,20' into a
	# sorted list of unique integers between 0 and max_Range -1.

	for c in range_str:
		if not (c.isdigit() or c == ',' or c == '-'):
			raise ValueError(f"Invalid argument -t/--track: {range_str}. Expected patterns: '5', '1,5', '3-7', '-5', '10-', '7,3-5,20-35,17,-1', etc")

	track_list = set()

	for part in range_str.split(','):
		if not part or '--' in part or part == '-':
			continue

		if '-' in part:
			# '3-7', '-5', '10-'
			if part.startswith('-'):
				start = 0
				end = int(part[1:])
			elif part.endswith('-'):
				start = int(part[:-1])
				end = max_Range - 1
			else:
				start_str, end_str = part.split('-', 1)
				start = int(start_str)
				end = int(end_str)
		else:
			# single number
			start = end = int(part)

		# clamp
		end = min(max_Range - 1, end)

		if start > end:
			raise ValueError(f"Invalid argument -t/--track: {start} > {end} in {range_str}")

		track_list.update(range(start, end + 1))

	return sorted(track_list)

def process_tracks(filename, track_range=None, list=False, dump=None, pipe=False):
	with open(filename, 'rb') as f:
		header_buf = bytearray()
		# Read header start into buffer
		header_min_size = 16  # Min for ID + version + offset
		header_buf.extend(f.read(header_min_size))
		if len(header_buf) < header_min_size:
			raise ValueError("File too short for header")

		# Read offset to first track (this is also the header size)
		offset_first_track = struct.unpack('<I', header_buf[12:16])[0]

		# Finish reading in whole header
		header_buf.extend(f.read(offset_first_track - header_min_size))

		if len(header_buf) < offset_first_track:
			raise ValueError(f"Short header: read {len(header_buf)}, expected {offset_first_track}")

		# Parse from buffer
		file_id = header_buf[0:8]
		expected_id = b'\xee\x4d\x46\x4d\x0d\x0a\x1a\x00'
		if file_id != expected_id:
			raise ValueError(f"Invalid file ID: expected {expected_id.hex().upper()}, got {file_id.hex().upper()}")

		# Read file type and version (4 bytes, little-endian)
		file_type_version = struct.unpack('<I', header_buf[8:12])[0]
		file_type = (file_type_version >> 24) & 0xFF
		is_emulator = file_type == 2
		file_type_str = "Emulator" if is_emulator else "Transition"
		major_version = (file_type_version >> 16) & 0xFF
		minor_version = (file_type_version >> 8) & 0xFF

		unused = file_type_version & 0xFF
		if unused != 0:
			print(f"Warning: Unused version byte is non-zero: {unused}")

		expected_version = 0x02020200 if is_emulator else 0x01020200
		if file_type_version != expected_version:
			print(f"Warning: Unexpected version for file type {file_type}: {file_type_version:08x} (expected {expected_version:08x})")

		buf_offset = 16
		if is_emulator:
			track_data_size = struct.unpack('<I', header_buf[buf_offset:buf_offset+4])[0]
			buf_offset += 4
		else:
			track_data_size = None

		track_header_size = struct.unpack('<I', header_buf[buf_offset:buf_offset+4])[0]
		buf_offset += 4
		num_cylinders = struct.unpack('<I', header_buf[buf_offset:buf_offset+4])[0]
		buf_offset += 4
		num_heads = struct.unpack('<I', header_buf[buf_offset:buf_offset+4])[0]
		buf_offset += 4
		num_tracks = num_cylinders * num_heads

		# Read bit rate (emulator) or transition count rate (transition)
		bit_rate = struct.unpack('<I', header_buf[buf_offset:buf_offset+4])[0]
		buf_offset += 4
		if not is_emulator and bit_rate != 200_000_000:
			raise ValueError(f"Only 200 MHz Transition count rate currently supported, got {bit_rate} Hz")

		# Read command line
		cmd_line_length = struct.unpack('<I', header_buf[buf_offset:buf_offset+4])[0]
		buf_offset += 4
		command_line_bytes = header_buf[buf_offset:buf_offset + cmd_line_length]
		command_line = command_line_bytes.rstrip(b'\x00').decode('utf-8', errors='replace')
		buf_offset += cmd_line_length

		# Read note
		note_length = struct.unpack('<I', header_buf[buf_offset:buf_offset+4])[0]
		buf_offset += 4
		note_bytes = header_buf[buf_offset:buf_offset + note_length]
		note = note_bytes.rstrip(b'\x00').decode('utf-8', errors='replace')
		buf_offset += note_length

		# Read start time
		start_time_ns = struct.unpack('<I', header_buf[buf_offset:buf_offset+4])[0]
		buf_offset += 4

		computed_crc = None
		read_crc = None
		if not is_emulator:
			computed_crc = calculate_crc32(header_buf[:offset_first_track - 4])
			read_crc = struct.unpack('<I', header_buf[buf_offset:buf_offset+4])[0]

		if not pipe and not args.tch:
			# Print file header info
			print(f"File Type: {file_type} ({file_type_str}), Major Version: {major_version}, Minor Version: {minor_version}")
			print(f"Offset to first track: {offset_first_track} bytes")
			if is_emulator:
				print(f"Track data size: {track_data_size} bytes")
			print(f"Track header size: {track_header_size} bytes")
			print(f"Number of cylinders: {num_cylinders}")
			print(f"Number of heads: {num_heads}")
			print(f"Number of tracks (cylinders*heads): {num_cylinders*num_heads}")
			print(f"{'Bit rate' if is_emulator else 'Transition count rate'}: {bit_rate:,} Hz")
			print(f"Command line: {command_line}")
			print(f"Note: {note}")
			print(f"Start time from index: {start_time_ns} ns")

		# Verify header checksum for transition files (over header excluding checksum)
		if not is_emulator:
			if computed_crc != read_crc:
				print("Warning: Header CRC mismatch", file=sys.stderr)
			if not pipe and not args.tch:
				print(f"Header CRC: read {read_crc:08x}, computed {computed_crc:08x}")

		if list:
			print(f"\nTrack Headers:")
			track_count = 0
			while True:
				track_start_pos = f.tell()
				success, cyl, head, data_size = print_track_header(f, is_emulator, track_data_size, num_cylinders, num_heads, track_count, track_start_pos)
				if not success:
					break

				# Skip to next track header: header + data (+ checksum for transition)
				if is_emulator:
					f.seek(track_start_pos + track_header_size + track_data_size)
				else:
					f.seek(track_start_pos + track_header_size + data_size + 4)

				track_count += 1

		elif track_range:
			tracks = parse_track_range(track_range, num_tracks)
			timestamp = 0

			for track_idx in tracks:
				if not seek_track(f, track_idx, is_emulator, track_header_size, track_data_size, offset_first_track):
					raise ValueError(f"Failed to seek to track {track_idx}")

				track_start_pos = f.tell()
				success, cyl, head, data_size = print_track_header(
					f, is_emulator, track_data_size, num_cylinders, num_heads, track_idx, track_start_pos)
				if not success or (cyl == -1 and head == -1):
					break

				if not pipe:
					print(f"Track {track_idx}: Cylinder {cyl}, Head {head}")
					if args.tch:
						print(bin(track_idx)[2:].zfill(num_tracks.bit_length()), bin(cyl)[2:].zfill(num_cylinders.bit_length()), bin(head)[2:].zfill(num_heads.bit_length()), '\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n')
					if not is_emulator and not args.tch:
						print(f"  Data bytes: {data_size}")

				if not is_emulator:
					if not args.tch:
						track_data = verify_track_crc(f, track_start_pos, track_header_size, data_size, pipe)
				else:
					track_data = f.read(data_size)
					if len(track_data) != data_size:
						raise ValueError(f"Short read on emulator data for track {track_idx}")

				if dump or pipe:
					timestamp = dump_track_data_vcd(track_data, f"Track {track_idx}: Cylinder {cyl}, Head {head}", timestamp, None if pipe else dump, track_idx)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Transitions file (dgesswein/mfm) to VCD converter')
	parser.add_argument('-t', '--track', type=str, help="Track(s) to dump: '5', '3-7', '10-', '-5', '-2,5,10-15,20', etc")
	parser.add_argument('-tch', action='store_true', help='-t only shows "Track Cylinder Head" + its binary encoding. Helpful for decoding unsupported Headers.')

	group = parser.add_mutually_exclusive_group()
	group.add_argument('-l', '--list', action='store_true', help='Show Header and list all tracks')
	group.add_argument('-d', '--dump', type=os.path.abspath, metavar='FILE', help='Dump selected tracks to VCD file. Use {track} in filename to force separate dumps per track')
	group.add_argument('-p', '--pipe', action='store_true', help='Dump selected tracks to stdout in VCD format (for piping into sigrok-cli)')

	parser.add_argument('filename', help='.tr file')

	global args
	args = parser.parse_args()

	if args.list and args.track:
		parser.error("argument -l/--list: not allowed with argument -t/--track")
	if (args.dump or args.pipe) and not args.track:
		parser.error("argument -d/--dump and -p/--pipe require argument -t/--track")

	try:
		process_tracks(args.filename,
							track_range=args.track,
							list=args.list,
							dump=args.dump,
							pipe=args.pipe)
	except Exception as e:
		if not args.pipe:
			import traceback
			traceback.print_exc()
		parser.error(e)
