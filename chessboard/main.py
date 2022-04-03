#!/usr/bin/env python

# Author: Shao Zhang and Phil Saltzman
# Models: Eddie Canaan
# Last Updated: 2015-03-13
#
# This tutorial shows how to determine what objects the mouse is pointing to
# We do this using a collision ray that extends from the mouse position
# and points straight into the scene, and see what it collides with. We pick
# the object with the closest collision

from http.client import OK
from direct.showbase.ShowBase import ShowBase
from panda3d.core import CollisionTraverser, CollisionNode
from panda3d.core import CollisionHandlerQueue, CollisionRay
from panda3d.core import AmbientLight, DirectionalLight, LightAttrib
from panda3d.core import TextNode
from panda3d.core import LPoint3, LVector3, BitMask32
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.DirectObject import DirectObject
from direct.task.Task import Task
import sys

# First we define some constants for the colors
BLACK = (0, 0, 0, 1)
WHITE = (1, 1, 1, 1)
HIGHLIGHT = (0, 1, 1, 1)
VALID = (1, 1, 0, 0)
PIECEBLACK = (.15, .15, .15, 1)

# Now we define some helper functions that we will need later

# This function, given a line (vector plus origin point) and a desired z value,
# will give us the point on the line where the desired z value is what we want.
# This is how we know where to position an object in 3D space based on a 2D mouse
# position. It also assumes that we are dragging in the XY plane.
#
# This is derived from the mathematical of a plane, solved for a given point
def PointAtZ(z, point, vec):
    return point + vec * ((z - point.getZ()) / vec.getZ())

# A handy little function for getting the proper position for a given square1
def SquarePos(i):
    return LPoint3((i % 8) - 3.5, int(i // 8) - 3.5, 0)

# Helper function for determining whether a square should be white or black
# The modulo operations (%) generate the every-other pattern of a chess-board
def SquareColor(i):
    if (i + ((i // 8) % 2)) % 2:
        return BLACK
    else:
        return WHITE


class ChessboardDemo(ShowBase):
    def __init__(self):
        # Initialize the ShowBase class from which we inherit, which will
        # create a window and set up everything we need for rendering into it.
        ShowBase.__init__(self)

        # This code puts the standard title and instruction text on screen
        self.title = OnscreenText(text="Panda3D: Chess",
                                  style=1, fg=(1, 1, 1, 1), shadow=(0, 0, 0, 1),
                                  pos=(0.9, -0.8), scale = .07)
        self.escapeEvent = OnscreenText(
            text="ESC: Quit", parent=base.a2dTopLeft,
            style=1, fg=(1, 1, 1, 1), pos=(0.06, -0.1),
            align=TextNode.ALeft, scale = .05)
        self.mouse1Event = OnscreenText(
            text="Left-click and drag: Pick up and drag piece",
            parent=base.a2dTopLeft, align=TextNode.ALeft,
            style=1, fg=(1, 1, 1, 1), pos=(0.06, -0.16), scale=.05)
        self.mouse2Event = OnscreenText(
            text="Chess game made by Marko & Emily!",
            parent=base.a2dTopLeft, align=TextNode.ALeft,
            style=1, fg=(1, 1, 1, 1), pos=(0.06, -0.22), scale=.05)

        self.accept('escape', sys.exit)  # Escape quits
        self.disableMouse()  # Disble mouse camera control
        camera.setPosHpr(0, -12, 8, 0, -35, 0)  # Set the camera
        self.setupLights()  # Setup default lighting

        # Since we are using collision detection to do picking, we set it up like
        # any other collision detection system with a traverser and a handler
        self.picker = CollisionTraverser()  # Make a traverser
        self.pq = CollisionHandlerQueue()  # Make a handler
        # Make a collision node for our picker ray
        self.pickerNode = CollisionNode('mouseRay')
        # Attach that node to the camera since the ray will need to be positioned
        # relative to it
        self.pickerNP = camera.attachNewNode(self.pickerNode)
        # Everything to be picked will use bit 1. This way if we were doing other
        # collision we could separate it
        self.pickerNode.setFromCollideMask(BitMask32.bit(1))
        self.pickerRay = CollisionRay()  # Make our ray
        # Add it to the collision node
        self.pickerNode.addSolid(self.pickerRay)
        # Register the ray as something that can cause collisions
        self.picker.addCollider(self.pickerNP, self.pq)
        # self.picker.showCollisions(render)

        # Now we create the chess board and its pieces

        # We will attach all of the squares to their own root. This way we can do the
        # collision pass just on the squares and save the time of checking the rest
        # of the scene
        self.squareRoot = render.attachNewNode("squareRoot")

        # For each square
        self.squares = [None for i in range(64)]
        self.pieces = [None for i in range(64)]
        # creates a 2d array for a easier time finding valid moves (for hummans)
        print("\nThe 8x8 board:")
        print("  1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |")
        x = 0
        self.board = [[8*i+j for j in range(8)] for i in range(8)]
        for i in self.board:
            for j in i:
                print(j,end = " ")
            print()
        
        
        for i in range(64):
            # Load, parent, color, and position the model (a single square
            # polygon)
            self.squares[i] = loader.loadModel("models/square")
            self.squares[i].reparentTo(self.squareRoot)
            self.squares[i].setPos(SquarePos(i))
            self.squares[i].setColor(SquareColor(i))
            # Set the model itself to be collideable with the ray. If this model was
            # any more complex than a single polygon, you should set up a collision
            # sphere around it instead. But for single polygons this works
            # fine.
            self.squares[i].find("**/polygon").node().setIntoCollideMask(
                BitMask32.bit(1))
            # Set a tag on the square's node so we can look up what square this is
            # later during the collision pass
            self.squares[i].find("**/polygon").node().setTag('square', str(i))

            # We will use this variable as a pointer to whatever piece is currently
            # in this square

        # The order of pieces on a chessboard from white's perspective. This list
        # contains the constructor functions for the piece classes defined
        # below
        pieceOrder = (Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook)

        for i in range(8, 16):
            # Load the white pawns
            self.pieces[i] = Pawn(i, WHITE)
        for i in range(48, 56):
            # load the black pawns
            self.pieces[i] = Pawn(i, PIECEBLACK)
            self.pieces[i].moves = [(0,-1),(1,-1),(-1,-1)]
        for i in range(8):
            # Load the special pieces for the front row and color them white
            self.pieces[i] = pieceOrder[i](i, WHITE)
            # Load the special pieces for the back row and color them black
            self.pieces[i + 56] = pieceOrder[i](i + 56, PIECEBLACK)

        # This will represent the index of the currently highlited square
        self.hiSq = False
        # This wil represent the index of the square where currently dragged piece
        # was grabbed from
        self.dragging = False

        # Start the task that handles the picking
        self.mouseTask = taskMgr.add(self.mouseTask, 'mouseTask')
        self.accept("mouse1", self.grabPiece)  # left-click grabs a piece
        self.accept("mouse1-up", self.releasePiece)  # releasing places it

    # This function swaps the positions of two pieces
    def swapPieces(self, fr, to):
        temp = self.pieces[fr]
        self.pieces[fr] = self.pieces[to]
        self.pieces[to] = temp
        if self.pieces[fr] and (fr != to):
            if type(self.pieces[fr]) == type(King(-100, WHITE)):
                self.title = OnscreenText(text="Game over!",
                                  style=1, fg=(1, 1, 1, 1), shadow=(0, 0, 0, 1),
                                  pos=(0.3, 0.5), scale = .3)
            
            # removes the piece
            self.pieces[fr].remove()
            self.pieces[fr] = None
            #self.pieces[fr].square = fr
            #self.pieces[fr].obj.setPos(SquarePos(fr))
            
        if self.pieces[to]:
            self.pieces[to].square = to
            self.pieces[to].obj.setPos(SquarePos(to))
    
    def isPieceBetween(self, move, currentPos, targetPos):
        piece_NOT_between = True
        xCurrent = currentPos % 8
        yCurrent = currentPos // 8
        print(f"Index is [{currentPos}] target is {targetPos}")
        currentPos += move[0] + move[1]*8
        while currentPos != targetPos and currentPos>-1 and currentPos<64:
            print(f"Index is {currentPos} target is: {targetPos}, adding: {move[0] + move[1]*8}")
            if self.pieces[currentPos] != None:
                # There is a piece between
                piece_NOT_between = False
            currentPos += move[0] + move[1]*8
        return piece_NOT_between
            
            
    
    # is the position a valid move?
    def isVaidMove(self, piece, currentPos, targetPos):
        valid_move = False
            
        xCurrent = currentPos % 8
        yCurrent = currentPos // 8
        xTarget = targetPos % 8
        yTarget = targetPos // 8
        xDistance = xTarget - xCurrent
        yDistance = yTarget - yCurrent
        for move in piece.moves:
            if (xDistance == move[0]):
                if (yDistance == move[1]):
                    valid_move = True
                elif piece.limit == False and move[1] != 0 and yDistance != 0:
                    if (yDistance % move[1] == 0 and yDistance // move[1] > 0):
                        if xDistance/yDistance == move[0]/move[1]:
                            valid_move = True
            elif piece.limit == False and move[0] != 0:
                if (xDistance % move[0] == 0 and xDistance // move[0] > 0):
                    if (yDistance == move[1]):
                        if yDistance/xDistance == move[1]/move[0]:
                            valid_move = True
                    elif move[1] != 0 and yDistance != 0:
                        if (yDistance % move[1] == 0 and yDistance // move[1] > 0):
                            if xDistance/yDistance == move[0]/move[1]:
                                valid_move = True
            # Checks if there is a piece between where it is moving each move
            if valid_move == True and self.pieces[currentPos].limit == False:
                valid_move = self.isPieceBetween(move, currentPos, targetPos)
                break    # break here
        
        # pieces can't move into the space occupied by a piece of their color
        if self.pieces[targetPos] != None:
            if self.pieces[targetPos].white == piece.white:
                valid_move = False
        
        return valid_move
        
    def mouseTask(self, task):
        # This task deals with the highlighting and dragging based on the mouse

        # First, clear the current highlight
        if self.hiSq is not False:
            for i in range(64):
                self.squares[i].setColor(SquareColor(i))
            self.hiSq = False

        # Check to see if we can access the mouse. We need it to do anything
        # else
        if self.mouseWatcherNode.hasMouse():
            # get the mouse position
            mpos = self.mouseWatcherNode.getMouse()

            # Set the position of the ray based on the mouse position
            self.pickerRay.setFromLens(self.camNode, mpos.getX(), mpos.getY())

            # If we are dragging something, set the position of the object
            # to be at the appropriate point over the plane of the board
            if self.dragging is not False:
                # Gets the point described by pickerRay.getOrigin(), which is relative to
                # camera, relative instead to render
                nearPoint = render.getRelativePoint(
                    camera, self.pickerRay.getOrigin())
                # Same thing with the direction of the ray
                nearVec = render.getRelativeVector(
                    camera, self.pickerRay.getDirection())
                self.pieces[self.dragging].obj.setPos(
                    PointAtZ(.5, nearPoint, nearVec))


            # Highlight valid moves:
            if self.dragging is not False:
                for i in range(64):
                    if self.isVaidMove(self.pieces[self.dragging], self.dragging, i):
                        self.squares[i].setColor(VALID)

            # Do the actual collision pass (Do it only on the squares for
            # efficiency purposes)
            self.picker.traverse(self.squareRoot)
            if self.pq.getNumEntries() > 0:
                # if we have hit something, sort the hits so that the closest
                # is first, and highlight that node
                self.pq.sortEntries()
                i = int(self.pq.getEntry(0).getIntoNode().getTag('square'))
                # Set the highlight on the picked square
                self.squares[i].setColor(HIGHLIGHT)
                self.hiSq = i
                

                

        return Task.cont

    def grabPiece(self):
        # If a square is highlighted and it has a piece, set it to dragging
        # mode
        if self.hiSq is not False and self.pieces[self.hiSq]:
            self.dragging = self.hiSq
            self.hiSq = False

    def releasePiece(self):
        # Letting go of a piece. If we are not on a square, return it to its original
        # position. Otherwise, swap it with the piece in the new square
        # Make sure we really are dragging something
        if self.dragging is not False:
            # We have let go of the piece, but we are not on a square
            if self.hiSq is False or self.isVaidMove(self.pieces[self.dragging], self.dragging, self.hiSq) is False:
                self.pieces[self.dragging].obj.setPos(
                    SquarePos(self.dragging))
                print(f"Moving a white={self.pieces[self.dragging].white} {type(self.pieces[self.dragging])} from {self.dragging} to {self.hiSq} is invalid!")
            else:
                # Otherwise, swap the pieces
                print(f"swapping {self.dragging} and {self.hiSq}")
                # sets first move to False
                self.pieces[self.dragging].is_first_move = False
                self.swapPieces(self.dragging, self.hiSq)

        # We are no longer dragging anything
        self.dragging = False

    def setupLights(self):  # This function sets up some default lighting
        ambientLight = AmbientLight("ambientLight")
        ambientLight.setColor((.8, .8, .8, 1))
        directionalLight = DirectionalLight("directionalLight")
        directionalLight.setDirection(LVector3(0, 45, -45))
        directionalLight.setColor((0.2, 0.2, 0.2, 1))
        render.setLight(render.attachNewNode(directionalLight))
        render.setLight(render.attachNewNode(ambientLight))


# Class for a piece. This just handles loading the model and setting initial
# position and color
class Piece(object):
    def __init__(self, square, color):
        self.obj = loader.loadModel(self.model)
        self.obj.reparentTo(render)
        self.obj.setColor(color)
        self.obj.setPos(SquarePos(square))
        # if the color is PIECEBLACK, white is false
        if color == PIECEBLACK:
            self.white = False
        else:
            self.white = True
        # Checks if the piece has been moved
        self.is_first_move = False
    # Removes a piece
    def remove(self):
        self.obj.detachNode()


# Classes for each type of chess piece
# Obviously, we could have done this by just passing a string to Piece's init.
# But if you wanted to make rules for how the pieces move, a good place to start
# would be to make an isValidMove(toSquare) method for each piece type
# and then check if the destination square is acceptible during ReleasePiece
class Pawn(Piece):
    model = "models/pawn"
    #if Piece.white:
    moves = [(0,1),(1,1),(-1,1)]
    #else:
    #    moves = [(0,-1),(1,-1),(-1,-1)]
    limit = True

class King(Piece):
    model = "models/king"
    moves = [(1,0),(0,1),(-1,0),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)]
    limit = True

class Queen(Piece):
    model = "models/queen"
    moves = [(1,0),(0,1),(-1,0),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)]
    limit = False

class Bishop(Piece):
    model = "models/bishop"
    moves = [(1,1),(-1,1),(1,-1),(-1,-1)]
    limit = False

class Knight(Piece):
    model = "models/knight"
    moves = [(-1,2),(-2,1),(-2,-1),(-1,-2),(1,-2),(2,-1),(2,1),(1,2)]
    limit = True

class Rook(Piece):
    model = "models/rook"
    moves = [(1,0),(0,1),(-1,0),(0,-1)]
    limit = False

# Do the main initialization and start 3D rendering
demo = ChessboardDemo()
demo.run()
