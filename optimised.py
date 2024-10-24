import numpy as np
from random import randint
import pygame


class Engine:
    def __init__(self, num_objects, constrainrad):
        self.constrainrad = constrainrad
        self.center = np.array([screen_width, screen_height]) // 2
        self.centerofmass = self.center
        self.zoom = 32000 / constrainrad
        self.downpos = None
        self.downtime = 0
        self.pos = np.array([[screen_width // 2, screen_height // 2]],dtype=float)
        self.posold = np.copy(self.pos)
        self.radius = np.array([[10]],dtype=float)
        self.acc = np.array([[0, 0]],dtype=float)
        self.mass = np.array([[1000]],dtype=float)
        self.color = np.array([[randint(0, 255), randint(0, 255), randint(0, 255)]])
        self.break_indices = self.mass != self.mass
        for _ in range(num_objects - 1):
            self.newobject()

    def tick(self, dt):
        for _ in range(16):
            self.collision()
            self.update(dt / 16)
            if np.any(self.break_indices):
                self.break_objects()
            self.merge()
        self.collision()
        self.draw()

    def draw(self):
        screen.fill((128, 128, 128))
        pygame.draw.circle(screen, (0, 0, 0), (((self.centerofmass - self.center) * self.zoom / 100) + self.center), self.constrainrad * self.zoom / 100)
        pygame.draw.circle(screen, (0, 255, 0), pygame.mouse.get_pos(), 10 * self.zoom / 100)
        pygame.draw.circle(screen, (0, 255, 255), (((self.centerofmass - self.center) * self.zoom / 100) + self.center), 5)
        screenpos = ((self.pos - self.center) * self.zoom / 100) + self.center
        screenradius = self.radius * self.zoom / 100
        for i in range(len(screenpos)):
            pygame.draw.circle(screen, [255, 255, 255], screenpos[i], int(screenradius[i])+1)
            pygame.draw.circle(screen, self.color[i], screenpos[i], int(screenradius[i]))
        if self.downpos is not None:
            pygame.draw.line(screen, (0, 0, 255), self.downpos, pygame.mouse.get_pos(), 5)
        pygame.display.flip()

    def update(self, dt):
        if pygame.key.get_pressed()[pygame.K_g]:
            self.gravity()
        change = self.pos - self.posold + self.acc * (dt ** 2)
        self.posold = np.copy(self.pos)
        self.pos += change
        self.acc.fill(0)
        self.constraint()

    def constraint(self):
        disp = self.pos - self.centerofmass
        dist = np.linalg.norm(disp, axis=1) + self.radius
        collisions = dist > self.constrainrad
        if np.any(collisions):
            self.pos[collisions] -= (disp[collisions] * (dist[collisions] - self.constrainrad)[:, None] / self.constrainrad)
            self.posold[collisions] = np.copy(self.pos[collisions])
        disp = self.pos - (((np.array(pygame.mouse.get_pos()) - self.center) * 100 / self.zoom) + self.center)
        dist = np.linalg.norm(disp, axis=1) + 1e-6
        mousecollision = dist < (self.radius + 10)
        if pygame.key.get_pressed()[pygame.K_b]:
            self.break_indices = mousecollision
        elif pygame.key.get_pressed()[pygame.K_p]:
            if np.any(mousecollision):
                change = disp[mousecollision] * (self.radius[mousecollision] + 10)[:, None] / dist[mousecollision][:, None] - disp[mousecollision]
                self.pos[mousecollision] += change

    def collision(self, adjustable=None, gravity=True):
        if adjustable is None:
            adjustable = self.mass == self.mass
        disp = self.pos[:, None, :] - self.pos[None, :, :]
        dist = np.linalg.norm(disp, axis=-1)
        radiisum = self.radius[None, :] + self.radius[:, None]
        collisions = ((dist < radiisum) & (dist > 0))
        noforce = collisions | (dist == 0)
        dist = np.where(dist == 0, 1, dist)  # Avoid division by zero
        if np.any(collisions):
            change = disp * (radiisum - dist)[:, :, None] / dist[:, :, None]
            change[~collisions] = 0
            change *= 0.5  # Each pair is calculated twice, so do only 1/2 change as fix
            totalmass = self.mass[None, :] + self.mass[:, None]
            self.pos[adjustable] += np.sum(change * self.mass[:, None, None] / totalmass[:, :, None], axis=1)[adjustable]
            self.pos[adjustable] += np.sum(change * self.mass[None, :, None] / totalmass[:, :, None], axis=1)[adjustable]
        if np.any(~collisions) and gravity:
            distsq = np.square(dist)
            force = disp * (self.mass[None, :] * self.mass[:, None])[:, :, None] * 0.1 / (distsq * dist)[:, :, None]
            force[noforce] = 0
            self.acc -= np.sum(force / self.mass[None, :, None], axis=1)
            self.acc -= np.sum(force / self.mass[:, None, None], axis=1)

    def merge(self):
        disp = self.pos[:, None, :] - self.pos[None, :, :]
        dist = np.linalg.norm(disp, axis=-1)
        radiisum = self.radius[:, None] + self.radius[None, :]
        merging = (dist < (radiisum * 0.8)) & (dist > 0)
        if np.any(merging):
            merging_pairs = np.argwhere(merging)
            merging_pairs = merging_pairs[merging_pairs[:, 0] < merging_pairs[:, 1]]
            total_mass = self.mass[merging_pairs[:, 0]] + self.mass[merging_pairs[:, 1]]
            new_pos = (self.pos[merging_pairs[:, 0]] * self.mass[merging_pairs[:, 0], None] + self.pos[merging_pairs[:, 1]] * self.mass[merging_pairs[:, 1], None]) / total_mass[:, None]
            new_vel = ((self.pos[merging_pairs[:, 0]] - self.posold[merging_pairs[:, 0]]) * self.mass[merging_pairs[:, 0], None] + (self.pos[merging_pairs[:, 1]] - self.posold[merging_pairs[:, 1]]) * self.mass[merging_pairs[:, 1], None]) / total_mass[:, None]
            new_color = (self.color[merging_pairs[:, 0]] * self.mass[merging_pairs[:, 0], None] + self.color[merging_pairs[:, 1]] * self.mass[merging_pairs[:, 1], None]) / total_mass[:, None]
            self.mass[merging_pairs[:, 0]] = total_mass
            self.radius[merging_pairs[:, 0]] = np.sqrt(total_mass / 10)
            self.pos[merging_pairs[:, 0]] = new_pos
            self.posold[merging_pairs[:, 0]] = new_pos - new_vel
            self.color[merging_pairs[:, 0]] = new_color
            to_delete = np.unique(merging_pairs[:, 1])
            self.pos = np.delete(self.pos, to_delete, axis=0)
            self.posold = np.delete(self.posold, to_delete, axis=0)
            self.radius = np.delete(self.radius, to_delete, axis=0)
            self.mass = np.delete(self.mass, to_delete, axis=0)
            self.acc = np.delete(self.acc, to_delete, axis=0)
            self.color = np.delete(self.color, to_delete, axis=0)
            self.break_indices = self.mass != self.mass

    def break_objects(self):
        pieces = 4
        oldlen = self.mass != self.mass
        num_to_break = np.sum(self.break_indices)
        pos_to_break = self.pos[self.break_indices]
        posold_to_break = self.posold[self.break_indices]
        mass_to_break = self.mass[self.break_indices]
        radius_to_break = self.radius[self.break_indices]
        color_to_break = self.color[self.break_indices]
        new_masses = np.repeat(mass_to_break / pieces, pieces, axis=0)
        new_colors = np.repeat(color_to_break, pieces, axis=0)
        offsets = np.random.uniform(-1, 1, size=(num_to_break * pieces, 2)) * np.repeat(radius_to_break, pieces, axis=0)[:, None]
        new_positions = np.repeat(pos_to_break, pieces, axis=0) + offsets
        self.pos = np.delete(self.pos, np.where(self.break_indices)[0], axis=0)
        self.posold = np.delete(self.posold, np.where(self.break_indices)[0], axis=0)
        self.mass = np.delete(self.mass, np.where(self.break_indices)[0], axis=0)
        self.radius = np.delete(self.radius, np.where(self.break_indices)[0], axis=0)
        self.acc = np.delete(self.acc, np.where(self.break_indices)[0], axis=0)
        self.color = np.delete(self.color, np.where(self.break_indices)[0], axis=0)
        self.pos = np.vstack((self.pos, new_positions))
        self.posold = np.vstack((self.posold, new_positions - np.repeat(posold_to_break, pieces, axis=0)))
        self.mass = np.concatenate((self.mass, new_masses))
        self.radius = np.concatenate((self.radius, np.sqrt(new_masses / 10)))
        self.acc = np.vstack((self.acc, np.zeros((num_to_break * pieces, 2))))
        self.color = np.vstack((self.color, new_colors))
        self.break_indices = self.mass != self.mass
        for _ in range(pieces * 16):
            self.collision(gravity=False, adjustable=np.pad(oldlen, (0, (pieces - 1) * num_to_break), mode='constant', constant_values=True))

    def newobject(self, x=None, y=None, size=None, posold=None):
        if size is None:
            size = randint(100, 150)
        sqside = int(np.floor(self.constrainrad/np.sqrt(2)))
        if x is None:
            x = screen_width // 2 + randint(-sqside + size, sqside - size)
        if y is None:
            y = screen_height // 2 + randint(-sqside + size, sqside - size)
        if posold is None:
            posold = np.array([x, y])
        new_color = [randint(0, 128), randint(0, 255), randint(0, 255)] # Give everything a bluish-greenish tinge
        self.pos = np.vstack([self.pos, np.array([x, y])])
        self.posold = np.vstack([self.posold, posold])
        self.radius = np.append(self.radius, size)
        self.mass = np.append(self.mass, size * size * 10)
        self.acc = np.vstack([self.acc, np.zeros(2)])
        self.color = np.vstack([self.color, new_color])
        self.break_indices = self.mass != self.mass

    def gravity(self):
        disp = self.pos - (((np.array(pygame.mouse.get_pos()) - self.center) * 100 / self.zoom) + self.center)
        distsq = np.square(np.linalg.norm(disp, axis=1)) + 0.001
        self.acc += -10000000 * disp / (distsq[:, None] * np.abs(disp))

    def recenter(self):
        average = np.sum(np.multiply(self.pos, self.mass[:, None]), axis=0) / np.sum(self.mass)
        self.centerofmass = average
        average = (average - self.center) / 2
        self.centerofmass -= average
        self.pos -= average
        self.posold -= average


    def clickdown(self, event):
        self.downpos = np.array(event.dict['pos'])
        self.downtime = pygame.time.get_ticks()

    def clickup(self, event):
        self.downpos = (((self.downpos - self.center) * 100 / self.zoom) + self.center)
        velocitypos = ((((np.array(event.dict['pos']) - self.center) * 100 / self.zoom) + self.center) - self.downpos) / (pygame.time.get_ticks() - self.downtime)
        prevpos = self.downpos - velocitypos
        self.newobject(*list(self.downpos), 10 if event.dict['button'] == 1 else 50, prevpos)
        self.downpos = None
        self.downtime = 0

pygame.init()
screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
clock = pygame.time.Clock()
engine = Engine(200, 4000)
engine.zoom = 32000 / engine.constrainrad
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
        engine.posold = np.copy(engine.pos)
    if pygame.key.get_pressed()[pygame.K_n]:
        engine.newobject(*list((((np.array(pygame.mouse.get_pos()) - engine.center) * 100 / engine.zoom) + engine.center)), 150)
    if len(engine.pos) >= 3:
        engine.recenter()
    engine.zoom = max(min(engine.zoom + zooming * dt, 200), 32000 / engine.constrainrad)
    engine.tick(dt)
