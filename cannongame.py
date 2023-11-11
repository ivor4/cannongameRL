import pygame
import random


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
_DIFFICULTY_BULLET_SPEED = 10
_DIFFICULTY_AIRCRAFT_LINE_HEIGHTS = 10
_DIFFICULTY_RELOAD_TIME_BULLET = 20

_ROUND_TIME_S = 60
_EXPECTED_FPS = 60
_TIME_PER_CYCLE = 1/_EXPECTED_FPS
_ROUND_CYCLES = _ROUND_TIME_S * _EXPECTED_FPS


class GameInstance:
    def __init__(self, caption, mode):
        self.Caption = caption
        self.Mode = mode

        if(not pygame.get_init()):
            pygame.init()
            pygame.display.set_caption(self.Caption)
            self.Screen = pygame.display.set_mode((1280, 720))
            self.Clock = pygame.time.Clock()
            self.Font = pygame.font.SysFont(None, 24)
            self.OK = True
        else:
            print('Pygame already running')
            self.OK = False


    def reset(self, seed = 0):
        if(self.OK):
            self.GameObjects = []
            self.AircraftPool = []
            self.BulletPool = []
            self.ExplosionPool = []
            self.ActiveAircrafts = []
            self.ActiveBullets = []
            self.AircraftHeightUsed = []
            self.AircraftHeightsUsed = 0
            self.ElapsedTime = 0.0
            self.OutputObs = []

            for i in range(_DIFFICULTY_AIRCRAFT_LINE_HEIGHTS):
                self.AircraftHeightUsed.append(False)
                tupla = []
                tupla.append(0)
                tupla.append(0.0)
                tupla.append(0.0)
                self.OutputObs.append(tupla)

            for i in range(64):
                self.AircraftPool.append(_Aircraft())
                self.BulletPool.append(_Bullet())
                self.ExplosionPool.append(_Explosion())
            
            self.Running = True
            self.DestroyedAircrafts = 0
            self.MissedAircrafts = 0
            self.MissedBullets = 0
            self.Score = 0
            self.DownKeys = 0x0

            self.AircraftTimeout = random.randint(60, 180)
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
                self.OutputObs[randHeight][0] = 1


                
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

        if(self.Running):
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
                        self.OutputObs[gObject.height][0] = 0
                        self.OutputObs[gObject.height][1] = 0.0
                        self.OutputObs[gObject.height][2] = 0.0
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
        
            for aircraft in self.ActiveAircrafts:
                self.OutputObs[aircraft.height][0] = 1
                self.OutputObs[aircraft.height][1] = aircraft.position.x / self.Screen.get_width()
                self.OutputObs[aircraft.height][2] = (aircraft.speed.x + 5.0) / 10.0
                    
                for bullet in self.ActiveBullets:
                    if(aircraft.rect.colliderect(bullet.rect)):
                        aircraft.Kill(_KILLED_BINGO)
                        bullet.setWasUseful()
        
                        if(len(self.ExplosionPool) > 0):
                            newExplosion = self.ExplosionPool.pop(0)
                            newExplosion.ReCreate(aircraft.position)
                            self.GameObjects.append(newExplosion)
                        else:
                            print('Critical Error, explosion pool exhausted')
                            self.Running = False
                                    
                        break
            

            self.ElapsedTime +=_TIME_PER_CYCLE

            #End game when time is over
            self.Running &= (self.ElapsedTime < _ROUND_TIME_S)
        
        done = not self.Running

        info['DestroyedAircrafts'] = self.DestroyedAircrafts
        info['MissedAircrafts'] = self.MissedAircrafts
        info['MissedBullets'] = self.MissedBullets

        if(quited):
            self.close()
                
        return self.OutputObs, done, info

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





