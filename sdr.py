import struct
import operator

N = 512

datarate = 1001.1196136474609

samplerate = 44100

maxsize = int(samplerate / datarate * (2 + 2 + 64 + 2) * 8)
preamblesize = int(samplerate / datarate * 16)
syncsize = int(samplerate / datarate * (16 + 32))
stride = int(samplerate / datarate)

windowsize = preamblesize

SYNC = b'\xd3\x91'

sync_bits = [1, 0] * 8 + list(map(int, '{0:032b}'.format(int.from_bytes(2*SYNC, 'big'))))

def whitening_seq():
	v = 0x1ff
	while True:
		yield v & 0xff
		top = (v & 0x1e0)
		v = (top ^ (top >> 4) ^ (top >> 8) ^ (v << 1) ^ (v << 5)) & 0x1ff

def handle(data):
	assert len(data) == maxsize

	threshold = sum(data[:preamblesize]) / preamblesize

	if [item > threshold for item in data[:syncsize:stride][:48]] != sync_bits:
		return 0

	data = [int(item > threshold) for item in data]
	assert data[:preamblesize:stride] == [1, 0] * 8

	for i in range(stride):
		if data[i:i+preamblesize:stride] != [1, 0] * 8:
			break

	mid = i // 2

	for i in range(24):
		pos = mid + i * stride
		if data[pos:pos+preamblesize:stride] != [1, 0] * 8:
			return 0#pos + preamblesize
		if data[pos:pos+syncsize:stride][:48] == sync_bits:
			print(''.join(map(str, data[mid::stride])))
			data = data[pos::stride]
			break
	else:
		return 0#pos + preamblesize

	while len(data) % 8:
		data.pop()

	data = ''.join(map(str, data))
	data = int(data, 2).to_bytes(len(data) // 8, 'big')

	assert data[:2] == b'\xaa\xaa'
	assert data[2:6] == 2 * SYNC

	data = bytes(map(operator.xor, data[6:], whitening_seq()))
	data = data[:data[0]+1]

	print(data)

	return int(pos + samplerate / datarate * 8 * (6 + len(data)))

def read_vals(f, count):
	data = f.read(2 * count)
	return struct.unpack('<' + str(len(data) // 2) + 'h', data)

def parse_stream(f):
	window = list(read_vals(f, max(N, windowsize)))
	threshold_sum = sum(window[:windowsize])
	threshold_sum -= window[windowsize-1]

	skip = 0
	while True:
		vals = read_vals(f, N)
		if not vals:
			break

		window.extend(vals)

		count = len(window) - windowsize + 1
		for i in range(count):
			threshold_sum += window[i+windowsize-1]
			if skip > 0:
				skip -= 1
			else:
				threshold = int(threshold_sum / windowsize)
				if [item > threshold for item in window[i:i+windowsize:stride]] == [1, 0] * 8:
					if len(window) - i < maxsize:
						window.extend(read_vals(f, maxsize))
					skip = handle(window[i:i+maxsize])
			threshold_sum -= window[i]

		window = window[count:]

if __name__ == '__main__':
	import sys
	with sys.stdin.buffer as f:
		parse_stream(f)

