import operator
import binascii

SYNC = b'\xd3\x91'

def whitening_seq():
	v = 0x1ff
	while True:
		yield v & 0xff
		top = (v & 0x1e0)
		v = (top ^ (top >> 4) ^ (top >> 8) ^ (v << 1) ^ (v << 5)) & 0x1ff

def _crc(degree, poly, crcval, data, data_bits):
	crcval_msb = 1 << degree
	data_msb = 1 << data_bits
	for i in range(data_bits):
		data <<= 1
		crcval <<= 1
		if bool(crcval & crcval_msb) ^ bool(data & data_msb):
			crcval ^= poly
	return crcval

def crc16(data):
	return _crc(16, 0x8005, 0xffff, int(binascii.hexlify(data), 16), 8 * len(data)) & 0xffff

# Default settings + doubled sync-word (IIRC)
def parse(data):
	assert data[:2] == b'\xAA\xAA'
	assert data[2:6] == 2*SYNC
	data = bytes(map(operator.xor, data[6:], whitening_seq()))
	assert crc16(data) == 0
	return data[:-2]

if __name__ == '__main__':
	data = '10101010101010101101001110010001110100111001000111111011001010111110001100100000010100110011101101100100'
	data = int(data, 2).to_bytes(len(data)//8, 'big')
	print(parse(data))

