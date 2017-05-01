import subprocess
import struct

import parse

N = 1024

class SDRConfig:
	def __init__(self, ppm=0, lo=0, gain=0):
		self.ppm = ppm
		self.lo = lo
		self.gain = gain

class FMConfig:
	def __init__(self, freq, samplerate, resamplerate=None):
		self.freq = freq
		self.samplerate = samplerate
		self.resamplerate = resamplerate or samplerate

class RawSamples:
	def __init__(self, f, size, byteorder, signed):
		self.f = f
		self.size = size
		self.byteorder = byteorder
		self.signed = signed
		self.fmt = {1: 'B', 2: 'H', 4: 'I', 8: 'L'}[size]
		if signed:
			self.fmt = self.fmt.lower()
		self.fmtprefix = {'little': '<', 'big': '>'}[byteorder]

	def read(self, count):
		data = self.f.read(self.size * count)
		fmt = self.fmtprefix + str(len(data) // self.size) + self.fmt
		return struct.unpack(fmt, data)

def open_fm_stream(sdr, fm):
	args = [
		'rtl_fm',
		'-f', round(fm.freq - sdr.lo),
		'-s', round(fm.samplerate),
	]

	if fm.resamplerate != fm.samplerate:
		args.extend(['-r', round(fm.resamplerate)])

	if sdr.gain is not None:
		args.extend(['-g', round(sdr.gain)])

	if sdr.ppm:
		args.extend(['-p', round(sdr.ppm)])

	args = list(map(str, args))
	p = subprocess.Popen(args, stdout=subprocess.PIPE)

	return p, RawSamples(p.stdout, 2, 'little', True)

def binarify(data):
	"""Binary representation of bytes, similar to hexlify()"""
	return '{0:0{1}b}'.format(int.from_bytes(data, 'big'), len(data) * 8)

def unbinarify(data):
	"""Bytes of binary representation, similar to unhexlify()"""
	return int(data, 2).to_bytes(len(data) // 8, 'big')

def parse_stream(f, conf, sdr, fm):
	# Create search pattern
	preamble, sync_word = parse.get_sync_data(conf)
	pattern = list(map(int, binarify(preamble + sync_word)))

	base_size, parse_packet = parse.make_parser(conf)

	stride = round(round(fm.resamplerate) / conf.param.drate)
	thsize = len(preamble) * 8 * stride
	patsize = len(pattern) * stride
	maxsize = (len(pattern) + (2 + 255 + 2) * 8) * stride

	# Initialize window and sliding average (aka. the threshold)
	window = list(f.read(patsize))
	assert len(window) >= patsize >= thsize
	threshold_sum = sum(window[:thsize-1])

	while True:
		vals = f.read(N)
		# The while loop can grow the buffer, so there might still be unhandled data in the buffer even if there's no more in the stream
		if not vals and len(window) < patsize:
			break

		window.extend(vals)

		# Count is static so that we always drop the old data at some point
		pos = 0
		count = len(window) - patsize + 1
		while pos < count:
			# Update the sliding average
			threshold_sum += window[pos+thsize-1]
			threshold = int(threshold_sum / patsize)

			# Look for a match
			if all((value > threshold) == bit for value, bit in zip(window[pos:pos+patsize:stride], pattern)):
				# Assure that there's enough data for a full packet
				if len(window) - pos < maxsize:
					window.extend(f.read(maxsize))

				# Find middle point of stride
				data = [int(item > threshold) for item in window[pos:pos+patsize]]
				for i in range(1, stride):
					if data[i:i+patsize:stride] != pattern:
						break

				mid = i // 2

				# Extract bytes from [binary] window
				data = window[pos+mid:pos+mid+maxsize:stride]
				data = [int(item > threshold) for item in data]
				data = ''.join(map(str, data))
				data = unbinarify(data)

				# Parse packet and calculate skip
				try:
					addr, payload = parse_packet(data)
					yield (addr, payload)
				except:
					payload = b''

				skip = (base_size + len(payload)) * 8
				pos += skip

				# Sliding window recalculation will go south if this isn't met,
				# but above window extension should ensure it always is
				assert pos + thsize <= len(window)

				# Update sliding window if we skipped some data
				if skip > thsize // 2:
					threshold_sum = sum(window[pos:pos+thsize])
				elif skip:
					threshold_sum -= sum(window[pos-skip:pos])
					threshold_sum += sum(window[pos-skip+thsize:pos+thsize])

			threshold_sum -= window[pos]
			pos += 1

		window = window[count:]

def build_fm_conf(conf):
	# XXX: These would need to be taken account in freq
	assert conf.param.freqoff == 0
	assert conf.field.CHAN == 0

	# XXX: Sample rate adjustments are pretty arbitrary
	freq = conf.param.freq
	samplerate = 1.5 * conf.param.chanbw
	resamplerate = 3 * conf.param.drate
	if resamplerate > samplerate:
		samplerate = resamplerate
		resamplerate = None

	return FMConfig(freq, samplerate, resamplerate)

def dump_stream(conf, sdr):
	fm = build_fm_conf(conf)
	p, s = open_fm_stream(sdr, fm)

	try:
		for addr, payload in parse_stream(s, conf, sdr, fm):
			print(addr, payload)
	except KeyboardInterrupt:
		p.terminate()
		p.wait()

if __name__ == '__main__':
	from optparse import OptionParser
	import config

	parser = OptionParser(usage = 'usage: %prog [options] [CC2500-config]')

	parser.add_option('-l', '--lo', dest='lo', type='float', help='Downconverter LO frequency')
	parser.add_option('-g', '--gain', dest='gain', type='float', help='RTL-SDR tuner gain')
	parser.add_option('-p', '--ppm', dest='ppm', type='float', help='RTL-SDR ppm error')

	parser.set_defaults(lo=0, gain=0, ppm=0)

	opts, args = parser.parse_args()

	# Note: With RTL-SDR you *need* a downconverter to reach 2.4GHz
	sdr = SDRConfig(opts.ppm, opts.lo, opts.gain)
	if not args:
		conf = config.CC2500Config()
	else:
		conf = config.CC2500Config.fromhex(*args)

	dump_stream(conf, sdr)

