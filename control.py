import binascii
import serial
import time

class SerialSPI:
	def __init__(self, ser):
		self.ser = ser

	def xfer(self, data, log=True):
		data = binascii.hexlify(data)
		size = len(data) + 4

		self.ser.write(data + b'\r')

		tx = self.ser.read(size)
		if log:
			print(tx)

		assert tx.lower() == b'< ' + data + b'\r\n'

		rx = self.ser.read(size)
		if log:
			print(rx)

		assert len(rx) == size
		assert rx[:2] == b'> '
		assert rx[-2:] == b'\r\n'

		return binascii.unhexlify(rx[2:-2])

class CC2500Control:
	def __init__(self, spi):
		self.spi = spi

	def xfer(self, data, log=True):
		return self.spi.xfer(data, log=log)

	def initialize(self):
		# Reset chip
		self.xfer(b'\x30')
		time.sleep(0.1)

		# CRC_AUTOFLUSH=1, APPEND_STATUS=0
		self.xfer(b'\x07\x08')

		# Calibrate frequency synthesizer
		self.xfer(b'\x33')
		time.sleep(0.1)

	def tx(self, data):
		# SIDLE; SFTX; WFIFO
		self.xfer(b'\x36\x3B\x7F' + bytes([len(data)]) + data)
		# STX
		self.xfer(b'\x35')

		# RTXBYTES
		tmp = self.xfer(b'\xFA\x00')
		while tmp[0] & 0x70 == 0x20:
			tmp = self.xfer(b'\xFA\x00', log=False)

		return tmp

	def rx_once(self, end_time=None):
		# SIDLE; SFRX; SRX
		self.xfer(b'\x36\x3A\x34')

		# RRXBYTES
		tmp = self.xfer(b'\xFB\x00')
		while tmp[0] & 0x70 == 0x10 and (end_time is None or time.time() < end_time):
			tmp = self.xfer(b'\xFB\x00', log=False)

		if tmp[0] & 0x70 != 0x10 and 0 < tmp[1] <= 64:
			# RFIFO
			return self.xfer(b'\xFF' + tmp[1] * b'\x00')[1:]

	def rx(self, end_time=None, filter=None):
		while (end_time is None or time.time() < end_time):
			ret = self.rx_once(end_time)
			if ret and (filter is None or filter(ret)):
				return ret

	def rx_many(self, count=1, end_time=None, filter=None):
		while count > 0 and (end_time is None or time.time() < end_time):
			ret = self.rx_once(end_time)
			if ret and (filter is None or filter(ret)):
				count -= 1
				yield ret

if __name__ == '__main__':
	c = CC2500Control(SerialSPI(serial.Serial('/dev/ttyUSB0', 115200, parity='N', stopbits=1, timeout=1)))
	c.initialize()

	for i in range(2):
		c.tx(b'\xCA\xFE\xBA\xBE')

	for ret in c.rx_many(2):
		print(ret)

