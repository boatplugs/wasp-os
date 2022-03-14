
"""Point Counter for GadgetBridge
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. figure:: res/PointCounter.png
        :width: 179

        Screenshot of the Point Counter application

Point Counter:

* Touch: reset/save
* Swipe UPDOWN: increment/decrement step value
* Swipe LEFTRIGHT: decrement/increment total
"""

import wasp
import math

from micropython import const

# 2-bit RLE, 96x64, generated from ../../temp/pointcounter_icon.png, 468 bytes
pointcounter_icon = (
    b'\x02'
    b'`@'
    b'\x0b@\xfdA\x80V\x81\xc0\xfc\xd8@\xffB?\x05\x80'
    b'\xfd\x82\x18\xc2?\x04\x83\x19\xc2?\x03\x82\x1b\xc2?\x01'
    b'\x82\x1c\xc2?\x00\x83\x1d\xc2>\x82\x1f\xc1=\x83\x1f\xc2'
    b'<\x82!\xc2:\x83!\xc2:\x82#\xc28\x82%\xc1'
    b"7\x83%\xc26\x82'\xc24\x83\x1a\xc0\xeb\xc2\x0b@"
    b'\xfcB4\x82\x1b\xc2\x0cB2\x83\x0e\xc2\x08\xc5\rB'
    b'1\x82\x0f\xc2\x08\xc5\rB0\x82\x10\xc2\x0b\xc2\x0eB'
    b'.\x83\x10\xc2\x0b\xc2\x0fA.\x82\x11\xc2\x0b\xc2\x0fB'
    b'-\x80\xff\x82\x0c\xcc\x06\xc2\x0f\xc0\xfd\xc1@VA\x80'
    b'\xfc\x98\xc0\xff\xc1\x14\x82\x0c@\xebL\x06B\x0f\x80\xfd'
    b'\x82\x18\xc0\xfc\xc2\x14\xc2\x10B\x0bB\x0e\x82\x1a\xc2\x13'
    b'\xc2\x10B\x0bB\x0e\x82\x1a\xc2\x14\xc2\x0fB\x08H\n'
    b'\x82\x1c\xc2\x13\xc2\x0fB\x08H\t\x83\x1d\xc1\x14\xc2\x0e'
    b"B\x19\x82\x1e\xc2\x14\xc1(\x83\x1f\xc1\x14\xc2'\x82 "
    b'\xc2\x14\xc2%\x82"\xc2\x13\xc2$\x83"\xc2\x14\xc2#'
    b'\x82$\xc2\x13\xc2"\x83$\xc2\x14\xc2!\x82&\xc2\x13'
    b"\xc2 \x82'\xc2\x14\xc2\x1e\x83\x18F\n\xc2\x13\xc2\x1e"
    b'\x82\x18I\t\xc1\x14\xc2\x1c\x83\x0fB\x07A\x06B\t'
    b'\xc2\x14\xc1\x1c\x82\x10B\x0eB\n\xc1\x14\xc2\x1a\x82\x11'
    b'B\rB\x0b\xc2\x14\xc2\x19\x82\x11B\nD\r\xc2\x13'
    b'\xc2\x18\x82\x12B\nE\x0c\xc2\x14@VA\xd8\x80\xff'
    b'\x82\r\xc0\xeb\xcc\x08\xc3\x0b@\xfdA\x80V\x81-\xc0'
    b'\xfc\xc2\r@\xebL\tB\x0b\x80\xfd\x82.\xc2\x11B'
    b'\x0eB\n\x83/\xc1\x11B\x07A\x05C\n\x820\xc2'
    b'\x10B\x07H\n\x822\xc2\x0fB\x08F\x0b\x822\xc2'
    b"\x0fB\x18\x824\xc2(\x825\xc1'\x826\xc2%\x83"
    b'7\xc2$\x828\xc2#\x839\xc2"\x82:\xc2!\x83'
    b';\xc2 \x82=\xc2\x1e\x82>\xc2\x1e\x82?\x00\xc2\x1c'
    b'\x82?\x01\xc2\x1c\x82?\x02\xc2\x1a\x82?\x04\xc1\x19\x83'
    b'\x12'
)


def hexagon_points(center, size, i):
    deg_angles = 60 * i - 30
    rad_angle = math.pi / 180 * deg_angles
    return (int(center[0] + size * math.cos(rad_angle)),
            int(center[1] + size * math.sin(rad_angle)))


DISPLAY_WIDTH = const(240)
CENTER = const(120)
RTC = wasp.watch.rtc

class PointCounterApp(object):
    """ Point Counter application."""
    NAME = 'Points!'
    ICON = pointcounter_icon

    def __init__(self):
        self._reset = wasp.widgets.Button(0, 0, 240, 240, '')
        self._reset_wait = RTC.time()
        self._step_val = 1
        self._count_val = 0
        self._needs_update = True
        self._text_draw = []
        self._last_tap = None
        # self._text_draw.append(('{}'.format(self._count_val), 0, int(DISPLAY_WIDTH / 2 + 15), DISPLAY_WIDTH))
        self._drawable = wasp.watch.drawable
        self._hexpoints = [hexagon_points((CENTER, CENTER), int(DISPLAY_WIDTH / 5), i) for i in range(6)]

    def foreground(self):
        """Activate the application."""
        self._drawable.fill()
        self._needs_update = True
        self._update()
        wasp.system.request_tick(1000)
        wasp.system.request_event(wasp.EventMask.SWIPE_LEFTRIGHT |
                                  wasp.EventMask.SWIPE_UPDOWN |
                                  wasp.EventMask.TOUCH)

    def background(self):
        """De-activate the application (without losing state)."""
        pass

    def tick(self, ticks):
        wasp.system.keep_awake()
        self._update()

    def swipe(self, event):
        """
        Notify the application of a touchscreen swipe event.
        """
        if event[0] == wasp.EventType.UP:
            self._step_val += 1
        elif event[0] == wasp.EventType.DOWN:
            self._step_val -= 1
        elif event[0] == wasp.EventType.RIGHT:
            self._count_val += self._step_val
        elif event[0] == wasp.EventType.LEFT:
            self._count_val -= self._step_val
        wasp.watch.vibrator.pulse()
        self._needs_update = True

    def touch(self, event):
        print(event)
        wasp.watch.vibrator.pulse()
        if self._reset.touch(event):
            delay = RTC.time() - self._reset_wait
            if RTC.time() - self._reset_wait <= 0.4:
                self._reset_wait = RTC.time()
                self._count_val = 0
                self._needs_update = True
            else:
                self._reset_wait = RTC.time()

    def _draw(self):
        """Redraw the updated zones."""
        if len(self._text_draw):
            #self._reset.draw()
            for d in self._text_draw:
                d_bounds = self._drawable.bounding_box(d[0])
                self._drawable.fill(x=d[1], y=d[2], w=int(d_bounds[0] * 1.5), h=d_bounds[1])
                self._drawable.string(*d)
            for i, p in enumerate(self._hexpoints):
                line_width = 2
                x1, x2 = p
                y1, y2 = self._hexpoints[i + 1 if i + 1 < len(self._hexpoints) else 0]
                self._drawable.line(x1, x2, y1, y2, line_width)
            self._text_draw = []
        self._needs_update = False

    def _update(self):
        if self._needs_update:
            count_bounds = self._drawable.bounding_box(str(self._count_val))
            count = ('{}'.format(self._count_val), 0, 120, DISPLAY_WIDTH)
            step_bounds = self._drawable.bounding_box(str(self._step_val))
            step_str = '+{}' if self._step_val >= 0 else '{}'
            step = (step_str.format(self._step_val), 0, DISPLAY_WIDTH - 50, DISPLAY_WIDTH)
            self._text_draw.append(count)
            self._text_draw.append(step)
        self._draw()
