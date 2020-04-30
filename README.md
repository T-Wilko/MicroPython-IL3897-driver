# micropython-IL3897-driver
The driver file for an ePaper display driver IC (IL3897) with parameters selected for a 250x122 Lolin 2.13 inch EPD.

This is adapted from Mcauser's Waveshare ePaper driver series https://github.com/mcauser/micropython-waveshare-epaper/blob/master/epaper2in13.py and has been modified to work with Lolin 2.13 inch EPD.


## Example Usage
### Vertical/portrait

```
import epaper
  
width = 128
height = 250

e = epaper.EPD()
e.init()
e.clearBuffer()

import framebuf
buf = bytearray(width*height // 8)
fb = framebuf.FrameBuffer(buf, width, height, framebuf.MONO_HLSB)
black = 0
white = 1
fb.fill(white)
fb.text('Hello',0,20,black)
fb.text('World',0,40,black)
e.displayBuffer(buf)
```

See [MicroPython FrameBuffer Class](https://docs.micropython.org/en/latest/library/framebuf.html) for more info on framebuffer usage
