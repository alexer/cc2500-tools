import binascii

reg_data = """
IOCFG2   7: 6:GDO2_INV 5-0:GDO2_CFG
IOCFG1   7:GDO_DS 6:GDO1_INV 5-0:GDO1_CFG
IOCFG0   7:TEMP_SENSOR_ENABLE 6:GDO0_INV 5-0:GDO0_CFG
FIFOTHR  7-4: 3-0:FIFO_THR
SYNC1    7-0:SYNC|15-8
SYNC0    7-0:SYNC
PKTLEN   7-0:PACKET_LENGTH
PKTCTRL1 7-5:PQT 4: 3:CRC_AUTOFLUSH 2:APPEND_STATUS 1-0:ADR_CHK
PKTCTRL0 7: 6:WHITE_DATA 5-4:PKT_FORMAT 3:CC2400_EN 2:CRC_EN 1-0:LENGTH_CONFIG
ADDR     7-0:DEVICE_ADDR
CHANNR   7-0:CHAN
FSCTRL1  7-5: 4-0:FREQ_IF
FSCTRL0  7-0:FREQOFF
FREQ2    7-6:FREQ|23-22 5-0:FREQ|21-16
FREQ1    7-0:FREQ|15-8
FREQ0    7-0:FREQ
MDMCFG4  7-6:CHANBW_E 5-4:CHANBW_M 3-0:DRATE_E
MDMCFG3  7-0:DRATE_M
MDMCFG2  7:DEM_DCFILT_OFF 6-4:MOD_FORMAT 3:MANCHESTER_EN 2-0:SYNC_MODE
MDMCFG1  7:FEC_EN 6-4:NUM_PREAMBLE 3-2: 1-0:CHANSPC_E
MDMCFG0  7-0:CHANSPC_M
DEVIATN  7: 6-4:DEVIATION_E 3: 2-0:DEVIATION_M
MCSM2    7-5: 4:RX_TIME_RSSI 3:RX_TIME_QUAL 2-0:RX_TIME
MCSM1    7-6: 5-4:CCA_MODE 3-2:RXOFF_MODE 1-0:TXOFF_MODE
MCSM0    7-6: 5-4:FS_AUTOCAL 3-2:PO_TIMEOUT 1:PIN_CTRL_EN 0:XOSC_FORCE_ON
FOCCFG   7-6: 5:FOC_BS_CS_GATE 4-3:FOC_PRE_K 2:FOC_POST_K 1-0:FOC_LIMIT
BSCFG    7-6:BS_PRE_KI 5-4:BS_PRE_KP 3:BS_POST_KI 2:BS_POST_KP 1-0:BS_LIMIT
AGCCTRL2 7-6:MAX_DVGA_GAIN 5-3:MAX_LNA_GAIN 2-0:MAGN_TARGET
AGCCTRL1 7: 6:AGC_LNA_PRIORITY 5-4:CARRIER_SENSE_REL_THR 3-0:CARRIER_SENSE_ABS_THR
AGCCTRL0 7-6:HYST_LEVEL 5-4:WAIT_TIME 3-2:AGC_FREEZE 1-0:FILTER_LENGTH
WOREVT1  7-0:EVENT0|15-8
WOREVT0  7-0:EVENT0
WORCTRL  7:RC_PD 6-4:EVENT1 3:RC_CAL 2: 1-0:WOR_RES
FREND1   7-6:LNA_CURRENT 5-4:LNA2MIX_CURRENT 3-2:LODIV_BUF_CURRENT_RX 1-0:MIX_CURRENT
FREND0   7-6: 5-4:LODIV_BUF_CURRENT_TX 3: 2-0:PA_POWER
FSCAL3   7-6:FSCAL|23-22 5-4:CHP_CURR_CAL_EN 3-0:FSCAL|21-18
FSCAL2   7-6: 5:VCO_CORE_H_EN 4-0:FSCAL|17-13
FSCAL1   7-6: 5-0:FSCAL|12-7
FSCAL0   7: 6-0:FSCAL
RCCTRL1  7: 6-0:RCCTRL1
RCCTRL0  7: 6-0:RCCTRL0

FSTEST   7-0:FSTEST
PTEST    7-0:PTEST
AGCTEST  7-0:AGCTEST
TEST2    7-0:TEST2
TEST1    7-0:TEST1
TEST0    7-2:TEST0|6-1 1:VCO_SEL_CAL_EN 0:TEST0
"""

dfl_values = binascii.unhexlify('29 2E 3F 07 D3 91 FF 04 45 00 00 0F 00 5E C4 EC 8C 22 02 22 F8 47 07 30 04 76 6C 03 40 91 87 6B F8 56 10 A9 0A 20 0D 41 00 59 7F 3F 88 31 0B'.replace(' ', ''))

# Functions for parsing reg_data

def parse_bitrange(s, check=True):
	if '-' in s:
		msb, lsb = map(int, s.split('-'))
		assert not check or (msb in range(8) and lsb in range(8) and msb > lsb)
		return (msb, lsb)
	else:
		bit = int(s)
		assert not check or bit in range(8)
		return (bit, bit)

def expand_bitrange(bits):
	msb, lsb = bits
	return list(range(lsb, msb + 1))

def parse_reg_defs(reg_data):
	reg_defs = []
	field_defs = {}
	for line in reg_data.strip().split('\n'):
		# Ignore comments, skip empty lines
		line = line.split('#')[0].strip()
		if not line:
			continue

		reg_name, *reg_field_defs = line.split()

		reg_fields = []
		used_bits = []
		for reg_field_def in reg_field_defs:
			reg_bits, field_name = reg_field_def.split(':')
			reg_bits = parse_bitrange(reg_bits)

			used_bits.extend(expand_bitrange(reg_bits))

			# Reserved
			if not field_name:
				continue

			if '|' in field_name:
				field_name, field_bits = field_name.split('|')
				field_bits = parse_bitrange(field_bits, check=False)
				# Check that field and register sizes agree
				assert field_bits[0] - field_bits[1] == reg_bits[0] - reg_bits[1]
			else:
				field_bits = (reg_bits[0] - reg_bits[1], 0)

			reg_fields.append((reg_bits, field_name, field_bits))
			field_defs.setdefault(field_name, []).append((field_bits, reg_name, reg_bits))

		# Check that all bits of registers are defined
		assert sorted(used_bits) == list(range(8))

		reg_defs.append((reg_name, reg_fields))

	# Check that there is no overlap or holes in field bit definitions
	for field_name, fields in field_defs.items():
		used_bits = []
		for field_bits, reg_name, reg_bits in fields:
			used_bits.extend(expand_bitrange(field_bits))
		used_bits.sort()
		assert used_bits == list(range(used_bits[-1] + 1))

	return reg_defs, field_defs

# Parse reg_data
reg_defs, field_defs = parse_reg_defs(reg_data)
reg2addr = {name: addr for addr, (name, fields) in enumerate(reg_defs)}

# Functions for extracting field values from register values

def extract_field(field_parts, values):
	width = max(field_bits[0] for field_bits, reg_name, reg_bits in field_parts) + 1
	ret = [None] * width
	for field_bits, reg_name, reg_bits in field_parts:
		reg_addr = reg2addr[reg_name]
		value = values[reg_addr]
		for bit in range(reg_bits[0] - reg_bits[1] + 1):
			field_bit = field_bits[1] + bit
			reg_bit = reg_bits[1] + bit
			ret[field_bit] = str((value >> reg_bit) & 1)
	return int(''.join(reversed(ret)), 2)

def extract_fields(reg_values):
	values = {}
	for field_name, fields in field_defs.items():
		value = extract_field(fields, reg_values)
		values[field_name] = value
	return values

# Functions for formatting things for output

def format_bitrange(bits):
	msb, lsb = bits
	if msb == lsb:
		return str(msb)
	return '%d:%d' % (msb, lsb)

def format_masked_value(value, bits, width=8):
	ret = ['.'] * width
	for bit in range(width):
		if bit in bits:
			ret[bit] = str((value >> bit) & 1)
	return ''.join(reversed(ret))

def format_masked_values(old_value, new_value, bits, width=8):
	old = format_masked_value(old_value, bits, width)
	new = format_masked_value(new_value, bits, width)
	colors = [(32 if old_char == new_char else 31) if bit in bits else 0 for bit, (old_char, new_char) in enumerate(reversed(list(zip(old, new))))][::-1]
	colors = ['\x1b[%dm' % color for color in colors]
	old = ''.join(item for pair in zip(colors, old) for item in pair) + '\x1b[m'
	new = ''.join(item for pair in zip(colors, new) for item in pair) + '\x1b[m'
	return ' '.join([old, new])

# Functions for output

def dump_regs(reg_values):
	for addr, ((reg_name, reg_fields), reg_value) in enumerate(zip(reg_defs, reg_values)):
		print('0x%02X %s 0x%02X' % (addr, reg_name, reg_value))
		for reg_bits, field_name, field_bits in reg_fields:
			print('     %s %s[%s]' % (format_masked_value(reg_value, expand_bitrange(reg_bits)), field_name, format_bitrange(field_bits)))

def dump_regdiff(old_values, new_values):
	for addr, ((reg_name, reg_fields), (dfl_value, new_value)) in enumerate(zip(reg_defs, zip(old_values, new_values))):
		print('0x%02X %s 0x%02X -> 0x%02X' % (addr, reg_name, dfl_value, new_value))
		for reg_bits, field_name, field_bits in reg_fields:
			print('     %s %s[%s]' % (format_masked_values(dfl_value, new_value, expand_bitrange(reg_bits)), field_name, format_bitrange(field_bits)))

def dump_derived(vals):
	fxosc = fxtal = 26e6

	fif = fxosc / 2**10 * vals['FREQ_IF']
	freqoff = fxtal / 2**14 * ((vals['FREQOFF'] & 0x7f) - (vals['FREQOFF'] & 0x80))
	fcarrier = fxosc / 2**16 * vals['FREQ']
	bwchannel = fxosc / (8 * (4 + vals['CHANBW_M']) * 2**vals['CHANBW_E'])
	rdata = (256 + vals['DRATE_M']) * 2**vals['DRATE_E'] / 2**28 * fxosc
	dfchannel = fxosc / 2**18 * (256 + vals['CHANSPC_M']) * 2**vals['CHANSPC_E']
	fdev = fxosc / 2**17 * (8 + vals['DEVIATION_M']) * 2**vals['DEVIATION_E']

	print('fif:', fif / 1e3)
	print('freqoff:', freqoff / 1e3)
	print('fcarrier:', fcarrier / 1e6)
	print('bwchannel:', bwchannel / 1e3)
	print('rdata:', rdata)
	print('dfchannel:', dfchannel)
	print('fdev:', fdev)

def dump(reg_values):
	dump_regs(reg_values)
	print()

	regs = extract_fields(reg_values)
	for field_name in sorted(field_defs):
		print(field_name, regs[field_name])
	print()

	dump_derived(regs)
	print()

def dump_diff(old_values, new_values):
	dump_regdiff(old_values, new_values)
	print()

	olds = extract_fields(old_values)
	news = extract_fields(new_values)

	for field_name in sorted(field_defs):
		print(field_name, olds[field_name], '->', news[field_name])
	print()

	for vals in [olds, news]:
		dump_derived(vals)
		print()

if __name__ == '__main__':
	import sys

	def handle_arg(arg):
		if arg in {'default', 'dfl'}:
			return dfl_values
		else:
			return binascii.unhexlify(arg.replace(' ', ''))

	if len(sys.argv) == 1:
		dump(dfl_values)
	elif len(sys.argv) == 2:
		reg_values = handle_arg(sys.argv[1])
		dump(reg_values)
	else:
		old_values, new_values = map(handle_arg, sys.argv[1:])
		dump_diff(old_values, new_values)

