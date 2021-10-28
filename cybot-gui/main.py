import serial.serialutil
import pygame, math, sys, uart, serial, threading, time, numpy
from scipy.optimize import curve_fit

# Constants
BLUE = (25, 25, 200)
PURPLE = (200, 25, 200)
BLACK = (23, 23, 23)
WHITE = (254, 254, 254)
RED = (200, 25, 25)
GREEN = (25, 200, 25)

CM_TO_PX = 1.724
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

move_avg = [14]
turn_avg = [70.12]
ir_cal = [1043, 745, 610, 487, 2191, 1530, 1169, 945, 778, 672, 583, 528, 466, 406, 381, 330, 298, 268, 248, 225, 236, 235, 196, 235, 196, 168, 144, 166, 120]
pg_cal = [16.12, 22.64, 27.04, 31.84, 7.79, 11.29, 14.86, 19.04, 23.14, 26.72, 28.85, 33.23, 36.98, 40.65, 44.12, 48.08, 51.49, 26.79, 33.26, 39.66, 66.9, 1000.0, 1000.0, 1000.0, 1000.0, 64.08, 8.82, 1000.0, 69.69]
COEFF = 3082
PWR = -0.748
IR_RAW = 0

def polar_to_cart(deg, amt):
    """convert polar coordinates to cartesian"""
    x = float(amt) * math.sin(math.radians(int(deg)))
    y = float(amt) * math.cos(math.radians(int(deg)))
    return x,y

def line_of_best_fit():
    """set formula for calculating ir values"""
    def objective(x, a, b):
	    return a * pow(x, b)
    global COEFF, PWR
    popt, _ = curve_fit(objective, ir_cal, pg_cal)
    COEFF, PWR = popt
    print(COEFF, PWR)

def ir_to_cm(val):
    """convert ir values into centimeters"""
    return COEFF * pow(val,PWR)

def get_dist(x1,x2,y1,y2):
    return abs(math.sqrt(pow(x1-x2,2) + pow(y1-y2,2)))

def avg(list):
    return sum(list) / len(list)

class Player():
    """cybot player class"""

    def __init__(self):
        self.x = SCREEN_WIDTH / 2
        self.y = SCREEN_HEIGHT / 2
        self.servo_pos = 0
        self.rot = 90.0
        self.size = 34.8 * CM_TO_PX
        self.rect = pygame.Rect(self.x-30,self.y-30,60,60)
        self.manual = True
        self.bumper = ""
        self.estimating = False

    def update(self, angle, dist):
        """update position info"""
        self.rot += angle

        x, y = polar_to_cart(self.rot, dist * CM_TO_PX)
        self.x += x
        self.y += y
        self.rect = pygame.Rect(self.x-(self.size/2),self.y-(self.size/2),self.size,self.size)

    def calibrate_move_estimation(self):
        """take 10 samples of distance traveled in 1 seconds"""
        print("Now calibrating front and backwards movement...")
        for _ in range(10):
            x, y = self.x, self.y
            cybot_uart.send_data('w')
            time.sleep(1)
            cybot_uart.send_data('w')
            move_avg.append(get_dist(x,self.x,y,self.y))
        print("Complete!")
        self.calibrate_turn_estimation()

    def calibrate_turn_estimation(self):
        """take 10 samples of distance traveled in 1 seconds"""
        print("Now calibrating turning movement...")
        for _ in range(10):
            rot = self.rot
            cybot_uart.send_data('a')
            time.sleep(1)
            cybot_uart.send_data('a')
            turn_avg.append(abs(self.rot - rot))
        print("Calibration Complete!")

    def calibrate_ir(self):
        """calibrate ir sensor w/ ping sensor"""
        print("Calibrating IR sensors...")
        while self.bumper == "":
            cybot_uart.send_data('w')
            time.sleep(0.25)
            cybot_uart.send_data('w') # stop moving

        time.sleep(0.1)
        
        for _ in range(20):
            cybot_uart.send_data('s')
            time.sleep(0.25)
            cybot_uart.send_data('s')
            cybot_uart.send_data('m')
            time.sleep(0.1)
            if ScanData[len(ScanData) - 1].pg[0] >= 500: continue
            ir_cal.append(IR_RAW)
            pg_cal.append(ScanData[len(ScanData) - 1].pg[0])
        print("Complete!")
        print("Recommend: Restart client or clear scan data (k).")
        self.calibrate_move_estimation()

    def forward(self):
        """move forward until not estimating"""
        self.estimating = True
        dist = 0
        cybot_uart.send_data('w')
        while self.estimating:
            self.update(0, avg(move_avg) / 4)
            dist -= avg(move_avg) / 4
            time.sleep(0.25)
        cybot_uart.send_data('w')
        self.update(0, dist)

    def back(self):
        """move backward until not estimating"""
        self.estimating = True
        dist = 0
        cybot_uart.send_data('s')
        while self.estimating:
            self.update(0, (-1)*avg(move_avg) / 4)
            dist += avg(move_avg) / 4
            time.sleep(0.25)
        cybot_uart.send_data('s')
        self.update(0, dist)

    def left(self):
        """turn left until not estimating"""
        self.estimating = True
        angle = 0
        cybot_uart.send_data('a')
        while self.estimating:
            self.update(avg(turn_avg) / 4, 0)
            angle -= avg(turn_avg) / 4
            time.sleep(.25)
        cybot_uart.send_data('a')
        self.update(angle, 0)

    def right(self):
        """turn right until not estimating"""
        self.estimating = True
        angle = 0
        cybot_uart.send_data('d')
        while self.estimating:
            self.update((-1)*avg(turn_avg) / 4, 0)
            angle += avg(turn_avg) / 4
            time.sleep(.25)
        cybot_uart.send_data('d')
        self.update(angle, 0)

    def clear(self):
        self.x = SCREEN_WIDTH / 2
        self.y = SCREEN_HEIGHT / 2
        self.rot = 0
        self.rect = pygame.Rect(self.x-30,self.y-30,60,60)
        ScanData.clear()

    def radial_scan(self):
        """do radial scan"""
        start_theta = self.rot
        while abs(self.rot - start_theta) <= 360:
            cybot_uart.send_data('m')
            cybot_uart.send_data('a')
            time.sleep(.05)
            cybot_uart.waiting = True
            cybot_uart.send_data('a')


    def scan(self,ir,pg):
        """scan 180 degrees infront"""
        global IR_RAW
        IR_RAW = int(ir)  # for calibration
        ir = ir_to_cm(ir)
        irx, iry = polar_to_cart(self.rot, ir * CM_TO_PX)
        pgx, pgy = polar_to_cart(self.rot, pg * CM_TO_PX)
        offsetx, offsety = polar_to_cart(self.rot, float(34.8 / 2) * CM_TO_PX)
        ScanData.append(Point(self.x+irx+offsetx, self.y+iry+offsety, self.x+pgx+offsetx, self.y+pgy+offsety,ir,pg))
        

class Point():
    """class to hold scan data"""

    def __init__(self,irx,iry,pgx,pgy,ir,pg):
        self.ir = [ir,[irx,iry]]
        self.pg = [pg,[pgx,pgy]]

# try to initalize serial connection
try:
    cybot_uart = uart.UartConnection()
    player = Player()
    stream = threading.Thread(target=cybot_uart.data_stream, args=[player])
    stream.daemon = True
    stream.start()
except serial.serialutil.SerialException:
    sys.exit()

# initalize pygame
pygame.init()
font = pygame.font.SysFont('Segoe UI', 30)
screen = pygame.display.set_mode([SCREEN_WIDTH, SCREEN_HEIGHT])
ScanData = []
RenderedScan = []

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            try:
                sys.exit()
            finally:
                main = False

        if event.type == pygame.KEYDOWN:
            if event.key == ord('a'): # turn left
                threading.Thread(target=player.left).start()
            if event.key == ord('d'): # turn right
                threading.Thread(target=player.right).start()
            if event.key == ord('w'): # move forward
                threading.Thread(target=player.forward).start()
            if event.key == ord('s'): # move backwards
                threading.Thread(target=player.back).start()
            if event.key == ord('m'): # scan once
                cybot_uart.send_data("m")
            if event.key == ord('n'): # radial scan
                threading.Thread(target=player.radial_scan).start()
            if event.key == ord('c'): # calibrate
                threading.Thread(target=player.calibrate_ir).start()
            if event.key == ord('f'): # apply calibration settings
                line_of_best_fit()
            if event.key == ord('k'): # clear scan data
                ScanData.clear()
            if event.key == ord('r'): # reset cybot location
                pass
        elif event.type == pygame.KEYUP:
            player.estimating = False

    # fill background
    screen.fill(BLACK)

    # draw cybot
    xe, ye = polar_to_cart(player.rot + player.servo_pos - 90, player.size / 2)
    pygame.draw.circle(screen, WHITE, (player.x, player.y), player.size / 2)
    pygame.draw.arc(screen, GREEN, player.rect, math.radians(player.rot-180), math.radians(player.rot), 10)
    pygame.draw.line(screen, BLUE, (player.x, player.y), (player.x + xe, player.y + ye), 5)
    bump_text = font.render("bumper: " + player.bumper, False, WHITE)
    screen.blit(bump_text,(0,40))
    pos_text = font.render(str(round(player.x - (SCREEN_WIDTH / 2), 2)) + ", " + str(round(player.y - (SCREEN_HEIGHT / 2),2)) + ", " + str(round(player.rot,2)), False, WHITE)
    screen.blit(pos_text,(0,80))

    if player.manual:
        mode_text = font.render("mode: manual", False, WHITE)
    else:
        mode_text = font.render("mode: auto", False, WHITE)
    screen.blit(mode_text,(0,0))

    RenderedScan.clear()
    start = 0
    end = 0
    for x in range(len(ScanData)):
        pygame.draw.circle(screen, RED, ScanData[x].ir[1], 1)
        if ScanData[x].ir[0] < 180 and ScanData[x].pg[0] < 300:
            end = x
        elif (abs(start - end) >= 3):
            RenderedScan.append([ScanData[start].pg[1],ScanData[int((start+end)/2)].pg[1],ScanData[end].pg[1]])
            start = x + 1
            end = x + 1
        else:
            start = x + 1
            end = x + 1
    
    for points in RenderedScan:
        pygame.draw.polygon(screen, WHITE, points, 5)


    pygame.display.flip()