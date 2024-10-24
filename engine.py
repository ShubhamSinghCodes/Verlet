from math import sqrt
from random import randint
import pygame


class Vec2:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __mul__(self, other):
        return Vec2(self.x * other, self.y * other)

    def __truediv__(self, other):
        return Vec2(self.x / other, self.y / other)

    def __floordiv__(self, other):
        return Vec2(self.x // other, self.y // other)

    def __add__(self, other):
        assert isinstance(other, Vec2)
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        assert isinstance(other, Vec2)
        return Vec2(self.x - other.x, self.y - other.y)

    def __abs__(self):
        return Vec2(abs(self.x), abs(self.y))

    def squaresum(self):
        return self.x ** 2 + self.y ** 2

    def pair(self):
        return self.x, self.y


class Circle:
    def __init__(self, pos, radius, colour, mass, posold=None):
        self.pos = pos
        if posold is None:
            posold = pos
        self.posold = posold
        self.radius = radius
        self.colour = colour
        self.acc = Vec2(0, 0)
        self.mass = mass


    def update(self, dt):
        change = self.pos - self.posold + self.acc * (dt ** 2)
        self.posold = self.pos
        self.pos += change
        if dt != 0:
            self.colour = [max(min((change / dt).squaresum() * 64, 255), 150), 0, 0]
        self.acc = Vec2(0, 0)

    def draw(self, zoom, center):
        pygame.draw.circle(screen, self.colour, (((self.pos - center) * zoom / 100) + center).pair(), self.radius * zoom / 100)

    def force(self, force):
        self.acc += force / self.mass

class Engine:
    def __init__(self, num_objects, constrainrad):
        self.objects = []
        for _ in range(num_objects):
            self.newobject()
        self.constrainrad = constrainrad
        self.center = Vec2(screen_width, screen_height) // 2
        self.centerofmass = self.center
        self.zoom = 100
        self.downpos = None
        self.downtime = 0

    def tick(self, dt):
        for _ in range(16):
            self.update(dt / 16)
            self.collision()
        self.draw()

    def draw(self):
        screen.fill((128, 128, 128))
        pygame.draw.circle(screen, (0, 0, 0), (((self.centerofmass - self.center) * self.zoom / 100) + self.center).pair(), self.constrainrad * self.zoom / 100)
        pygame.draw.circle(screen, (0, 255, 0), pygame.mouse.get_pos(), 10 * self.zoom / 100)
        pygame.draw.circle(screen, (0, 255, 255), (((self.centerofmass - self.center) * self.zoom / 100) + self.center).pair(), 5)
        for obj in self.objects:
            obj.draw(self.zoom, self.center)
        if self.downpos is not None:
            pygame.draw.line(screen, (0, 0, 255), self.downpos.pair(), pygame.mouse.get_pos(), 5)
        pygame.display.flip()

    def update(self, dt):
        for obj in self.objects:
            #self.gravity(obj)
            obj.update(dt)
            self.constraint(obj)

    def constraint(self, obj):
        disp = obj.pos - self.centerofmass
        dist = sqrt(disp.squaresum()) + obj.radius
        if dist > self.constrainrad:
            obj.pos -= disp * (dist - self.constrainrad) / self.constrainrad
            obj.posold = obj.pos
        disp = obj.pos - (((Vec2(*pygame.mouse.get_pos()) - self.center) * 100 / self.zoom) + self.center)
        distsq = disp.squaresum() + 0.001
        dist = sqrt(distsq)
        if dist < obj.radius + 10:
            change = disp * (obj.radius + 10 - dist) / dist
            obj.pos += change

    def collision(self):
        for obj1 in self.objects:
            for obj2 in self.objects:
                if obj1 == obj2:
                    continue
                disp = obj1.pos - obj2.pos
                distsq = disp.squaresum()
                dist = sqrt(distsq)
                if dist < obj1.radius + obj2.radius:
                    change = disp * (obj1.radius + obj2.radius - dist) / dist
                    totalmass = obj1.mass + obj2.mass
                    obj1.pos += change * obj2.mass / totalmass
                    obj2.pos -= change * obj1.mass / totalmass
                else:
                    obj1.force(disp * -.1 * obj1.mass * obj2.mass / (distsq * sqrt(distsq))) # Will run twice for every pair of objects
                    obj2.force(disp * 0.1 * obj1.mass * obj2.mass / (distsq * sqrt(distsq))) # but it doesn't matter

    def newobject(self, x=None, y=None, size=None, posold=None):
        if x is None:
            x = screen_width // 2 + randint(-100, 100)
        if y is None:
            y = screen_height // 2 + randint(-100, 100)
        if size is None:
            size = randint(10, 50)
        self.objects.append(Circle(Vec2(x, y), size, (255, 0, 0), size * size * 10, posold))

    def gravity(self, obj):
        disp = obj.pos - (((Vec2(*pygame.mouse.get_pos()) - self.center) * 100 / self.zoom) + self.center)
        distsq = disp.squaresum() + 0.001
        if distsq > 100:
            obj.force(disp * -1000 * obj.mass / (distsq * sqrt(distsq)))

    def recenter(self):
        average = None
        count = 0
        for obj in self.objects:
            if average is None:
                average = obj.pos * obj.mass
            else:
                average += obj.pos * obj.mass
            count += obj.mass
        average /= count
        self.centerofmass = average
        average -= self.center
        average /= 10
        self.centerofmass -= average
        for obj in self.objects:
            obj.pos -= average
            obj.posold -= average

    def clickdown(self, event):
        self.downpos = Vec2(*event.dict['pos'])
        self.downtime = pygame.time.get_ticks()

    def clickup(self, event):
        self.downpos = (((self.downpos - self.center) * 100 / self.zoom) + self.center)
        velocitypos = ((((Vec2(*event.dict['pos']) - self.center) * 100 / self.zoom) + self.center) - self.downpos) / (pygame.time.get_ticks() - self.downtime)
        prevpos = self.downpos - velocitypos
        self.newobject(*self.downpos.pair(), 10 if event.dict['button'] == 1 else 50, prevpos)
        self.downpos = None
        self.downtime = 0

pygame.init()
screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
clock = pygame.time.Clock()
engine = Engine(0, 1000)
zooming = 0
while True:
    dt = clock.tick() / 5
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            quit()
        elif event.type == pygame.MOUSEBUTTONUP:
            engine.clickup(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            engine.clickdown(event)
        elif event.type == pygame.KEYDOWN and event.dict['key'] == pygame.K_UP:
            zooming = 1
        elif event.type == pygame.KEYDOWN and event.dict['key'] == pygame.K_DOWN:
            zooming = -1
        elif event.type == pygame.KEYUP and event.dict['key'] in [pygame.K_DOWN, pygame.K_UP]:
            zooming = 0
    if pygame.key.get_pressed()[pygame.K_SPACE]:
        for obj in engine.objects:
            obj.posold = obj.pos
    if len(engine.objects) > 1:
        engine.recenter()
    engine.zoom = max(min(engine.zoom + zooming * dt, 200), 32000 / engine.constrainrad)
    engine.tick(dt)
