from micropython import const
from machine import SPI, Pin
from time import sleep_ms
import ustruct

# Display resolution
EPD_WIDTH  = const(128)
EPD_HEIGHT = const(250)
# datasheet says 250x122 (increased to 128 to be multiples of 8)

# Display commands
DRIVER_OUTPUT_CONTROL                = const(0x01)
# Gate Driving Voltage Control       0x03
# Source Driving voltage Control     0x04
BOOSTER_SOFT_START_CONTROL           = const(0x0C) # not in datasheet
#GATE_SCAN_START_POSITION             = const(0x0F) # not in datasheet
DEEP_SLEEP_MODE                      = const(0x10)
DATA_ENTRY_MODE_SETTING              = const(0x11)
#SW_RESET                             = const(0x12)
#TEMPERATURE_SENSOR_CONTROL           = const(0x1A)
MASTER_ACTIVATION                    = const(0x20)
#DISPLAY_UPDATE_CONTROL_1             = const(0x21)
DISPLAY_UPDATE_CONTROL_2             = const(0x22)
# Panel Break Detection              0x23
WRITE_RAM                            = const(0x24)
WRITE_VCOM_REGISTER                  = const(0x2C)
# Status Bit Read                    0x2F
WRITE_LUT_REGISTER                   = const(0x32)
SET_DUMMY_LINE_PERIOD                = const(0x3A)
SET_GATE_TIME                        = const(0x3B)
#BORDER_WAVEFORM_CONTROL              = const(0x3C)
SET_RAM_X_ADDRESS_START_END_POSITION = const(0x44)
SET_RAM_Y_ADDRESS_START_END_POSITION = const(0x45)
SET_RAM_X_ADDRESS_COUNTER            = const(0x4E)
SET_RAM_Y_ADDRESS_COUNTER            = const(0x4F)
TERMINATE_FRAME_READ_WRITE           = const(0xFF) # not in datasheet, aka NOOP


class EPD:
    def __init__(self):
        self.spi = SPI(2, baudrate=20000000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(23), miso=Pin(19))
        #self.spi = SPI(1, 10000000, sck=Pin(14), mosi=Pin(13), miso=Pin(12))
        self.spi.init()

        dc = Pin(27)
        cs = Pin(14)
        rst = Pin(33)

        self.cs = cs
        self.dc = dc
        self.rst = rst
        #self.busy = busy
        self.cs.init(self.cs.OUT, value=1)
        self.dc.init(self.dc.OUT, value=0)
        self.rst.init(self.rst.OUT, value=0)
        self.width = EPD_WIDTH
        self.height = EPD_HEIGHT

        self.size = self.width * self.height // 8
        self.buf = bytearray(self.size)

    LUT_FULL_UPDATE    = bytearray(b'\x80\x60\x40\x00\x00\x00\x00\x10\x60\x20\x00\x00\x00\x00\x80\x60\x40\x00\x00\x00\x00\x10\x60\x20\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x03\x00\x00\x02\x09\x09\x00\x00\x02\x03\x03\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x15\x41\xA8\x32\x30\x0A')
    LUT_PARTIAL_UPDATE = bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x80\x00\x00\x00\x00\x00\x00\x40\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0A\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x15\x41\xA8\x32\x30\x0A')

    def clearBuffer(self):
        self._command(b'\x24')
        for i in range(0, len(self.buf)):
            self.buf[i] = 255
            self._data(bytearray([self.buf[i]]))

    def displayBuffer(self, buf):
        self._command(b'\x24')
        for i in range(0, len(buf)):
            self._data(bytearray([buf[i]]))
        self._command(b'\x22')
        self._command(b'\xC7')
        self._command(b'\x20')
        self._command(bytearray([TERMINATE_FRAME_READ_WRITE]))
        self.wait_until_idle()

    def _command(self, command, data=None):
        self.cs(1) # according to LOLIN_EPD
        self.dc(0)
        self.cs(0)
        self.spi.write(command)
        self.cs(1)
        if data is not None:
            self._data(data)

    def _data(self, data):
        self.cs(1) # according to LOLIN_EPD
        self.dc(1)
        self.cs(0)
        self.spi.write(data)
        self.cs(1)

    def init(self):
        self.reset()

        self.wait_until_idle();
        self._command(b'\x12'); # soft reset
        self.wait_until_idle();

        self._command(b'\x74', b'\x54'); #set analog block control
        self._command(b'\x7E', b'\x3B'); #set digital block control
        self._command(b'\x0f', b'\x00'); #set gate scan start position
        self._command(b'\x01', b'\xF9\x00\x00'); #Driver output control  ### CHANGED x00 to x01 ###
        self._command(b'\x11', b'\x03'); #data entry mode    ### CHANGED x01 to x00 ###
        #set Ram-X address start/end position
        self._command(b'\x44', b'\x00\x0F'); #0x0C-->(15+1)*8=128
        #set Ram-Y address start/end position
        self._command(b'\x45', b'\x00\x00\xF9\x00'); # 0xF9-->(249+1)=250   ### CHANGED xF9 to x00 ###

        self._command(b'\x3C', b'\x03'); # BorderWavefrom
        self._command(b'\x2C', b'\x55'); # VCOM Voltage

        self._command(b'\x03', bytes([self.LUT_FULL_UPDATE[70]])); # ??

        self._command(b'\x04')
        self._data(bytes([self.LUT_FULL_UPDATE[71]])); # ??
        self._data(bytes([self.LUT_FULL_UPDATE[72]])); # ??
        self._data(bytes([self.LUT_FULL_UPDATE[73]])); # ??


        self._command(b'\x3A', bytes([self.LUT_FULL_UPDATE[74]])); # Dummy Line
        self._command(b'\x3B', bytes([self.LUT_FULL_UPDATE[75]])); # Gate time

        self.set_lut(self.LUT_FULL_UPDATE)

        self._command(b'\x4E', b'\x00'); # set RAM x address count to 0;
        self._command(b'\x4F', b'\x00\x00'); # set RAM y address count to 0X127;
        self.wait_until_idle()

    def wait_until_idle(self):
        sleep_ms(1000)

    def reset(self):
        self.rst(1)
        sleep_ms(1)

        self.rst(0)
        sleep_ms(10)

        self.rst(1)

    def set_lut(self, lut):
        self._command(bytearray([WRITE_LUT_REGISTER]), lut)

    # put an image in the frame memory
    def set_frame_memory(self, image, x, y, w, h):
        # x point must be the multiple of 8 or the last 3 bits will be ignored
        x = x & 0xF8
        w = w & 0xF8

        if (x + w >= self.width):
            x_end = self.width - 1
        else:
            x_end = x + w - 1

        if (y + h >= self.height):
            y_end = self.height - 1
        else:
            y_end = y + h - 1

        self.set_memory_area(x, y, x_end, y_end)
        self.set_memory_pointer(x, y)
        self._command(bytearray([WRITE_RAM]), image)

    # replace the frame memory with the specified color
    def clear_frame_memory(self, color):
        self.set_memory_area(0, 0, self.width - 1, self.height - 1)
        self.set_memory_pointer(0, 0)
        self._command(bytearray([WRITE_RAM]))
        # send the color data
        for i in range(0, (self.width * self.height)//8):
            self._data(bytearray([color]))

    # draw the current frame memory and switch to the next memory area
    def display_frame(self):
        self._command(bytearray([DISPLAY_UPDATE_CONTROL_2]), b'\xC7')
        self._command(bytearray([MASTER_ACTIVATION]))
        self._command(bytearray([TERMINATE_FRAME_READ_WRITE]))
        self.wait_until_idle()

    # specify the memory area for data R/W
    def set_memory_area(self, x_start, y_start, x_end, y_end):
        self._command(bytearray([SET_RAM_X_ADDRESS_START_END_POSITION]))
        # x point must be the multiple of 8 or the last 3 bits will be ignored
        self._data(bytearray([(x_start >> 3) & 0xFF]))
        self._data(bytearray([(x_end >> 3) & 0xFF]))
        self._command(bytearray([SET_RAM_Y_ADDRESS_START_END_POSITION]), ustruct.pack("<HH", y_start, y_end))

    # specify the start point for data R/W
    def set_memory_pointer(self, x, y):
        self._command(bytearray([SET_RAM_X_ADDRESS_COUNTER]))
        # x point must be the multiple of 8 or the last 3 bits will be ignored
        self._data(bytearray([(x >> 3) & 0xFF]))
        self._command(bytearray([SET_RAM_Y_ADDRESS_COUNTER]), ustruct.pack("<H", y))
        self.wait_until_idle()

    # to wake call reset() or init()
    def sleep(self):
        self._command(bytearray([DEEP_SLEEP_MODE]))
        self.wait_until_idle()