import pygame
import random
import numpy as np


GAME_MODE_NORMAL = 0
GAME_MODE_EXT_ACTION = 1

ACTION_NONE = 0
ACTION_SHOOT = 1

ACTION_LIST_INFO = [(ACTION_NONE, 'No action'), (ACTION_SHOOT, 'Shoot')]

_SHAPE_RECTANGLE = 0
_SHAPE_CIRCLE = 1

_OBJ_TYPE_CANYON = 0
_OBJ_TYPE_AIRCRAFT = 1
_OBJ_TYPE_BULLET = 2
_OBJ_TYPE_EXPLOSION = 3

_KEY_INDEX_JUMP = 0

_POSSIBLE_KEYS = []

_POSSIBLE_KEYS.append((pygame.K_SPACE, 0x1))

_KILLED_NOT = 0
_KILLED_WASTED = 1
_KILLED_BINGO = 2
_KILLED_NEUTRAL = 3

_DIFFICULTY_AIRCRAFT_WIDTH = 48
_DIFFICULTY_BULLET_SPEED = 30
_DIFFICULTY_AIRCRAFT_LINE_HEIGHTS = 10
_DIFFICULTY_RELOAD_TIME_BULLET = 20

_DIFFICULTY_TOTAL_DESTROYED_AIRCRAFTS = 30

_ROUND_TIME_S = 120
_EXPECTED_FPS = 60
_TIME_PER_CYCLE = 1/_EXPECTED_FPS
_ROUND_CYCLES = _ROUND_TIME_S * _EXPECTED_FPS

_SCREEN_SIZE = [1280, 720]
_OUTPUT_SIZE_FACTOR = 8

#Xmin,XMax - X axis Region of interest of screen in pixels
_REGION_OF_INTEREST = [384,896]

#Output in X will be reduced according to factor
_OUTPUT_NP_X_LENGHT = (_REGION_OF_INTEREST[1] - _REGION_OF_INTEREST[0]) // _OUTPUT_SIZE_FACTOR

#Mlp will be used and not an image, Y axis is = number of aircraft lanes
_OUTPUT_NP_Y_LENGTH = _DIFFICULTY_AIRCRAFT_LINE_HEIGHTS

_OUTPUT_TRAIL_LOSS_RATIO = 3.0/5.0;


class GameInstance:
    def __init__(self, caption, mode, render_mode):
        self.Caption = caption
        self.Mode = mode
        self.render_mode = render_mode

        if(not pygame.get_init()):
            pygame.init()
            pygame.display.set_caption(self.Caption)
            self.Screen = pygame.display.set_mode((_SCREEN_SIZE[0], _SCREEN_SIZE[1]))
            self.Clock = pygame.time.Clock()
            self.Font = pygame.font.SysFont(None, 24)
            self.OK = True
        else:
            print('Pygame already running')
            self.OK = False


    def reset(self, seed = 0):

        random.seed(seed)

        if(self.OK):
            self.GameObjects = []

            #Objects are pooled to avoid new memory alloc during run, this avoids creating new instances after this point
            self.AircraftPool = []
            self.BulletPool = []
            self.ExplosionPool = []

            for i in range(64):
                self.AircraftPool.append(_Aircraft())
                self.BulletPool.append(_Bullet())
                self.ExplosionPool.append(_Explosion())

            self.ActiveAircrafts = []
            self.ActiveBullets = []
            self.AircraftHeightUsed = [False] * _DIFFICULTY_AIRCRAFT_LINE_HEIGHTS
            self.AircraftHeightsUsed = 0
            self.ElapsedTime = 0.0
            self.OutputObs = np.zeros((_OUTPUT_NP_Y_LENGTH, _OUTPUT_NP_X_LENGHT))

            
            self.Running = True
            self.DestroyedAircrafts = 0
            self.MissedAircrafts = 0
            self.MissedBullets = 0
            self.Score = 0
            self.DownKeys = 0x0

            self.AircraftTimeout = random.randint(30, 150)
            self.ReloadTimeout = 0
            self.BulletReady = True
        
            self.CanyonInstance = _Canyon('white', pygame.Vector2(self.Screen.get_width() / 2, self.Screen.get_height() - 32/2))
            self.GameObjects.append(self.CanyonInstance)

            self.Screen.fill('black')
            pygame.display.flip()

            return self.OutputObs
        else:
            raise Exception("Game cannot start")
        

    def isRunning(self):
        return self.Running

    def close(self):
        if(self.Running):
            self.Running = False

        if(pygame.get_init()):
            pygame.quit()

    def _KeyDetection(self):
        keys = pygame.key.get_pressed()

        actualDownKeys = 0x0
        
        for i in range(len(_POSSIBLE_KEYS)):
            if keys[_POSSIBLE_KEYS[i][0]]:
                actualDownKeys |= _POSSIBLE_KEYS[i][1]

        keyDiff = (self.DownKeys ^ actualDownKeys)
        pressedKeys = keyDiff & actualDownKeys
        releasedKeys = keyDiff & self.DownKeys

        if(pressedKeys & _POSSIBLE_KEYS[_KEY_INDEX_JUMP][1]):
            outAction = ACTION_SHOOT
        else:
            outAction = ACTION_NONE

        self.DownKeys = actualDownKeys

        return outAction

    def _Shoot(self):
        if(self.BulletReady):
            if(len(self.BulletPool)>0):
                newBullet = self.BulletPool.pop(0)
                newBullet.ReCreate(pygame.Vector2(self.Screen.get_width() / 2, self.Screen.get_height() - 32), pygame.Vector2(0, -_DIFFICULTY_BULLET_SPEED))
                self.GameObjects.append(newBullet)
                self.ActiveBullets.append(newBullet)
    
                self.BulletReady = False
                self.ReloadTimeout = _DIFFICULTY_RELOAD_TIME_BULLET
            else:
                print('Critical Error, bullet pool exhausted')
                self.Running = False

    def _ShootReload(self):
        if(self.ReloadTimeout > 0):
            self.ReloadTimeout -= 1
            if(self.ReloadTimeout == 0):
                self.BulletReady = True

    def _AircraftReload(self):
        if(self.AircraftTimeout > 0):
            self.AircraftTimeout -= 1

        if(self.AircraftTimeout == 0):
            #Between 0 and 1 with decimals (float)
            if(self.AircraftHeightsUsed < _DIFFICULTY_AIRCRAFT_LINE_HEIGHTS):
                randHeight = random.randint(0, _DIFFICULTY_AIRCRAFT_LINE_HEIGHTS - 1)

                while(self.AircraftHeightUsed[randHeight]):
                    randHeight = (randHeight + 1)%_DIFFICULTY_AIRCRAFT_LINE_HEIGHTS

                self.AircraftHeightsUsed += 1
                self.AircraftHeightUsed[randHeight] = True


                
                #Speed and direction will be decided if > 0.5 or not
                randNumber = random.random()
                randNumber = (randNumber - 0.5)*10.0
                
                if(randNumber < 0):
                    speed = pygame.Vector2(min(-2, randNumber), 0)
                    position = pygame.Vector2(self.Screen.get_width(), 30*(randHeight+1))
                else:
                    speed = pygame.Vector2(max(2, randNumber), 0)
                    position = pygame.Vector2(0, 30*(randHeight+1))
    
                if(len(self.AircraftPool) > 0):
                    newAircraft = self.AircraftPool.pop(0)
                    newAircraft.ReCreate('blue', position, speed, 0, self.Screen.get_width(), randHeight)
                    self.GameObjects.append(newAircraft)
                    self.ActiveAircrafts.append(newAircraft)
                else:
                    print('Critical Error, aircraft pool exhausted')
                    self.Running = False
            
            self.AircraftTimeout = random.randint(30, 80)

    def step(self, extAction = ACTION_NONE):
        #obs, dones, info
        info = {}

        quited = False
        trimmed = False

        if(self.Running and (self.render_mode == 'human')):
            # poll for events
            # pygame.QUIT event means the user clicked X to close your window    
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.Running = False
                    quited = True
                    break

        if(self.Running):
            # RENDER YOUR GAME HERE
        
            if(self.Mode == GAME_MODE_NORMAL):
                inputAction = self._KeyDetection()
            else:
                inputAction = extAction
        
            self._AircraftReload()
            self._ShootReload()
                
            if(inputAction == ACTION_SHOOT):
                self._Shoot()

            #Clear virtual output
            #self.OutputObs.fill(0.0)
            self.OutputObs = self.OutputObs * _OUTPUT_TRAIL_LOSS_RATIO
                
            for gObject in self.GameObjects:
                if(gObject.killed != _KILLED_NOT):
                    self.GameObjects.remove(gObject)
                    if(gObject.objType == _OBJ_TYPE_AIRCRAFT):
                        if(gObject.killed == _KILLED_WASTED):
                            self.MissedAircrafts += 1
                                
                        elif(gObject.killed == _KILLED_BINGO):
                            self.DestroyedAircrafts += 1
                            self.Score += 100
                        self.AircraftHeightsUsed -= 1
                        self.AircraftHeightUsed[gObject.height] = False
                        self.AircraftPool.append(gObject)
                        self.ActiveAircrafts.remove(gObject)
                            
                    elif(gObject.objType == _OBJ_TYPE_BULLET):
                        self.BulletPool.append(gObject)
                        self.ActiveBullets.remove(gObject)
        
                        if(gObject.killed == _KILLED_WASTED):
                            self.MissedBullets += 1
                    elif(gObject.objType == _OBJ_TYPE_EXPLOSION):
                        self.ExplosionPool.append(gObject)
                else:
                    gObject.Update()

                    if(gObject.objType == _OBJ_TYPE_AIRCRAFT):
                        for bullet in self.ActiveBullets:
                            if(gObject.rect.colliderect(bullet.rect)):
                                gObject.Kill(_KILLED_BINGO)
                                bullet.setWasUseful()
        
                                if(len(self.ExplosionPool) > 0):
                                    newExplosion = self.ExplosionPool.pop(0)
                                    newExplosion.ReCreate(gObject.position)
                                    self.GameObjects.append(newExplosion)
                                else:
                                    print('Critical Error, explosion pool exhausted')
                                    self.Running = False
                                    
                                break
                        if((gObject.killed == _KILLED_NOT)and(gObject.position.x > _REGION_OF_INTEREST[0])and(gObject.position.x < _REGION_OF_INTEREST[1])):
                            virtualwidth = int(gObject.shapeSize.x /_OUTPUT_SIZE_FACTOR)
                            virtualpos = int((gObject.position.x - _REGION_OF_INTEREST[0]) / _OUTPUT_SIZE_FACTOR)
                            
                            virtualmin = max(0,virtualpos - virtualwidth//2)
                            virtualmax = min(_OUTPUT_NP_X_LENGHT-1, virtualpos + virtualwidth//2) + 1

                            self.OutputObs[gObject.height,virtualmin:virtualmax] = 1.0
        
            

            self.ElapsedTime +=_TIME_PER_CYCLE

            #End game when time is over
            if(self.ElapsedTime >= _ROUND_TIME_S):
                self.Running =False
                trimmed = True
        
        #Game is truncated if losbullets >= Target total aircrafts/3. Otherwise is ended
        if(self.DestroyedAircrafts >= _DIFFICULTY_TOTAL_DESTROYED_AIRCRAFTS):
            self.Running = False
            if(self.MissedBullets >= (_DIFFICULTY_TOTAL_DESTROYED_AIRCRAFTS//3)):
                trimmed = True

        done = not self.Running and not trimmed
         
        info['DestroyedAircrafts'] = self.DestroyedAircrafts
        info['MissedAircrafts'] = self.MissedAircrafts
        info['MissedBullets'] = self.MissedBullets

        

        if(quited):
            trimmed = True
            self.close()
                
        return self.OutputObs, done, trimmed, info

    def render(self):
        if(self.Running):
            # fill the screen with a color to wipe away anything from last frame
            self.Screen.fill('black')

            # Render objects with their own custom function
            for gObject in self.GameObjects:
                gObject.Draw(self.Screen)

            img = self.Font.render('SCORE: '+str(self.Score), True, 'white')
            self.Screen.blit(img, (10, 10))
            img = self.Font.render('DESTROYED AIRCRAFTS: '+str(self.DestroyedAircrafts), True, 'white')
            self.Screen.blit(img, (10, 50))
            img = self.Font.render('MISSED AIRCRAFTS: '+str(self.MissedAircrafts), True, 'white')
            self.Screen.blit(img, (10, 70))
            img = self.Font.render('MISSED BULLETS: '+str(self.MissedBullets), True, 'white')
            self.Screen.blit(img, (10, 90))
            img = self.Font.render('REMAINING TIME: '+str(_ROUND_TIME_S - int(self.ElapsedTime)), True, 'white')
            self.Screen.blit(img, (10, 110))
        
            # flip() the display to put your work on screen
            pygame.display.flip()

            # limits FPS to 60
            self.Clock.tick(_EXPECTED_FPS)  


class _GameObject:
    def __init__(self, shapeType, shapeColor, shapeSize, objType):
        self.objType = objType 

        self.shapeType = shapeType
        self.shapeColor = shapeColor
        self.shapeSize = shapeSize
        self.position = pygame.Vector2(0, 0)
        self.speed = pygame.Vector2(0, 0)
        self.rect = pygame.Rect(self.position.x, self.position.y, self.shapeSize.x, self.shapeSize.y)
        self.killed = _KILLED_NOT

    def ReCreate(self, shapeType, shapeColor, shapeSize):
        self.shapeType = shapeType
        self.shapeColor = shapeColor
        self.shapeSize = shapeSize
        self.position = pygame.Vector2(0, 0)
        self.speed = pygame.Vector2(0, 0)
        self.rect = pygame.Rect(self.position.x, self.position.y, self.shapeSize.x, self.shapeSize.y)
        self.killed = _KILLED_NOT
        
    def Update(self):
        self.position.x += self.speed.x
        self.position.y += self.speed.y

        self.rect.width = self.shapeSize.x
        self.rect.height = self.shapeSize.y
        
        self.rect.left = self.position.x - self.rect.width/2
        self.rect.top = self.position.y - self.rect.height/2

    def Kill(self, reason):
        self.killed = reason 

    def Draw(self, surface):
        if(self.shapeType == _SHAPE_CIRCLE):
            pygame.draw.circle(surface, self.shapeColor, self.position, self.shapeSize.x)
        else:
            pygame.draw.rect(surface, self.shapeColor, self.rect)


class _Canyon(_GameObject):
    def __init__(self, shapeColor, position):
        super().__init__(_SHAPE_RECTANGLE, shapeColor, pygame.Vector2(16,32), _OBJ_TYPE_CANYON)
        self.position = position

class _Aircraft(_GameObject):
    def __init__(self):
        super().__init__(_SHAPE_RECTANGLE, 'white', pygame.Vector2(_DIFFICULTY_AIRCRAFT_WIDTH,16), _OBJ_TYPE_AIRCRAFT)
        self.minX = 0
        self.maxX = 0
        self.height = 0

    def ReCreate(self, shapeColor, position, initialSpeed, minX, maxX, height):
        super().ReCreate(_SHAPE_RECTANGLE, shapeColor, pygame.Vector2(_DIFFICULTY_AIRCRAFT_WIDTH,16))

        self.minX = minX
        self.maxX = maxX
        self.height = height
        self.position = position
        self.speed = initialSpeed

    def Update(self):
        super().Update()

        if((self.speed.x < 0)and(self.position.x < self.minX)):
            self.Kill(_KILLED_WASTED)
        elif((self.speed.x > 0)and(self.position.x > self.maxX)):
            self.Kill(_KILLED_WASTED)

class _Bullet(_GameObject):
    def __init__(self):
        super().__init__(_SHAPE_CIRCLE, 'red', pygame.Vector2(4,4), _OBJ_TYPE_BULLET)
        self.WasUseful = False

    def ReCreate(self, position, initialSpeed):
        super().ReCreate(_SHAPE_CIRCLE, 'red', pygame.Vector2(4,4))
        self.WasUseful = False

        self.position = position
        self.speed = initialSpeed

    def Update(self):
        super().Update()
        if(self.position.y < 0):
            if(self.WasUseful):
                self.Kill(_KILLED_NEUTRAL)
            else:
                self.Kill(_KILLED_WASTED)

    def setWasUseful(self):
        self.WasUseful = True


class _Explosion(_GameObject):
    def __init__(self):
        super().__init__(_SHAPE_CIRCLE, 'yellow', pygame.Vector2(2,2), _OBJ_TYPE_EXPLOSION)
        self.Timeout = 0

    def ReCreate(self, position):
        super().ReCreate(_SHAPE_CIRCLE, 'yellow', pygame.Vector2(2,2))

        self.Timeout = 30
        self.position = position

    def Update(self):
        super().Update()
        self.Timeout -= 1
        if(self.Timeout <= 0):
            self.Kill(_KILLED_NEUTRAL)
        else:
            radius = (30 - self.Timeout) * 10 / 30
            self.shapeSize = pygame.Vector2(radius,radius)





