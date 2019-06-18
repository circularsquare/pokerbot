#!/usr/bin/env python

from threading import Thread
from bottle    import get, post, run, request
from time      import sleep
from dotenv    import load_dotenv
from sys       import exit

import requests
import os

import numpy as np
import random
import matplotlib.pyplot as plt

import sys

load_dotenv()

port          = 3000
username      = os.getenv('USERNAME')
api_token     = os.getenv('API_TOKEN')
bot_endpoint  = os.getenv('BOT_ENDPOINT')
notifications = True

suitDict = {0:"diamonds", 1:"clubs", 2:"hearts", 3:"spades"}
valDict = {'deuce':0, 'three':1, 'four':2, 'five':3, 'six':4, 'seven':5, 'eight':6, 'nine':7, 'ten':8, 'jack':9, 'queen':10, 'king':11, 'ace':12}
bvalDict = {v: k for k, v in valDict.items()}

def randomCard(banned): #returns a random card that isn't a banned one
    suit = suitDict[random.randint(0, 3)]
    rank = bvalDict[random.randint(0, 12)]
    if {'rank': rank, 'suit':suit} not in banned:
        return ({'rank': rank, 'suit': suit})
    return randomCard(banned)

def cardToText(cards):
    rankTextDict = {'deuce':'2', 'three':'3', 'four':'4', 'five':'5', 'six':'6', 'seven':'7', 'eight':'8', 'nine':'9', 'ten':'T', 'jack':'J', 'queen':'Q', 'king':'K', 'ace':'A'}
    suitTextDict = {'diamonds':'d', 'clubs':'c', 'hearts':'h', 'spades':'s'}
    return str([(rankTextDict[card['rank']]+suitTextDict[card['suit']]) for card in cards])

def score(cards):
    if len(cards)<5:
        return -1
    if len(cards)>5:
        return max([score(cards[0:i]+cards[i+1:])] for i in range(len(cards)))[0]
    points = 0
    valList = [0]*13 #2s, 3s, ... 10s, Js, Qs, Ks, As
    for i in range(5):
        valList[valDict[cards[i]['rank']]] += 1
    if ((cards[0]['suit'] == cards[1]['suit']) & (cards[1]['suit']==cards[2]['suit']) & (cards[2]['suit']==cards[3]['suit']) & (cards[3]['suit']==cards[4]['suit'])):
        points += 2000 #flush score
    for i in range(len(valList)):
        if valList[i]==4:
            return 3000 + i #four of a kind (3000-3012)
        if valList[i]==3:
            for j in range(len(valList)):
                if valList[j]==2:
                    return 2500 + i #house (2500-2512)
            return 500+i #triple (500-512)
    for i in range(len(valList)-4):
        if (valList[i]==1 & valList[i+1]==1 & valList[i+2]==1 & valList[i+3]==1 & valList[i+4]==1):
            points += 1500 + i #straight score (1500-1508, or if straight flush, 3500-3508)
            return points
    for i in range(len(valList)):
        if valList[i]==2:
            for j in range(i, len(valList)):
                if valList[j]==2:
                    return 200 + (j*13) + i #two pair (200-369)
            return 100 + i #one pair (100-110)
    for i in range(0, len(valList), -1):
        if(valList[i])==1:
            return i
        if(valList[i])>1:
            return -1000
    return points

def equity(table, yours, numOtherPlayers): #fill in the 7 with random cards
    originalCards = yours+table
    numWins = 0
    numGuesses = 1000
    for i in range(numGuesses):
        your7 = [x for x in originalCards]
        their7 = [x for x in table]
        while len(your7) < 7:
            your7.append(randomCard(your7))
        while len(their7) < 7:
            their7.append(randomCard(your7+their7))
        if score(your7)>score(their7):
            numWins += 1
    return (numWins/(numGuesses))**numOtherPlayers

'''table = [{'rank':'ace', 'suit':'spades'}, {'rank':'king', 'suit':'hearts'}, {'rank':'deuce', 'suit':'spades'}]
yours = [{'rank': 'ace', 'suit':'diamonds'}, {'rank':'king', 'suit':'diamonds'}]
print(equity(table, yours, 6))'''


def bet(chips, info):
    if info["canCallOrRaise"]:
        return {"action":"raise", "chips":max(info['minRaise'], min(chips, info["yourChips"]))}
    if info["canCheckOrBet"]:
        return {"action":"check", "chips":max(info['minBet'], min(chips, info["yourChips"]))}
def call(info):
    if info["canCallOrRaise"]:
        return {"action":"call"}
    if info["canCheckOrBet"]:
        return {"action":"check"}
def fold():
    if info["canCheckOrBet"]:
        return{"action":"check"}
    return{"action":"fold"}

def preflop(info):
    card = [0, 0]
    card[0] = valDict[info["yourCards"][0]['rank']]
    card[1] = valDict[info["yourCards"][1]['rank']]
    print("preflop cards are " + cardToText(info["yourCards"]))
    chips = info["yourChips"]
    if (card[0]==card[1]):
        if (card[0]==12):
            print("AA: fourth in")
            return bet(chips/4, info)
        if (card[0]==11):
            print("KK: eighth in")
            return bet(chips/8, info)
        else:
            print("pair: call")
            return call(info)
    if ((card[0]+card[1]>15) or (card[0]>10) or (card[1]>10)):
        print("highish: call")
        return call(info)
    print("bad: fold")
    return fold()

@post('/pokerwars.io/play')
def play():
    info = request.json
    print('Game info received for tournament ' + str(info["tournamentId"]) + ' and round ' + str(info["roundId"]))
    print('Current round turn is ' + str(info["roundTurn"]))
    #print('Cards on the table are ' + str(game_info["tableCards"]))
    table = info["tableCards"]
    #print('Your bot cards are ' + str(game_info["yourCards"]))
    yours = info["yourCards"]
    chips = info["yourChips"]
    '''    print('The value of small blind now is ' + str(game_info["smallBlindValue"]))'''
    numPlayers = len([player for player in info["players"] if player["chips"]>0])
    numUnfolded = len([player for player in info["players"] if player["folded"]==False])
    print("num players is " + str(numPlayers))
    if(info["roundTurn"]=='pre_flop'):
        return preflop(info)
    print('score:')
    eq = equity(table, yours, numPlayers-1)
    print("your cards are " + cardToText(yours))
    print("table cards are " + cardToText(table))
    if(eq > .49):
        print("equity " + str(eq) + ", bet " + str(info['yourPot']*2))
        return bet(info['yourPot']*2, info)
    if(eq > .15):
        print("equity " + str(eq) + ", bet " + str(info['yourPot']*1))
        return bet(info['yourPot']*1, info)
    if(eq > .05):
        print("equity " + str(eq) + ", called")
        return call(info)
    print("equity " + str(eq) + ", (check)feld")
    return fold()

@get('/pokerwars.io/ping')
def ping():
    print('Received ping from pokerwars.io, responding with a pong')
    return {"pong": True}

@post('/pokerwars.io/notifications')
def notifications():
    print('Received notification')
    print(request.json)
    return

def subscribe():
    down = True
    while down:
        try:
            print('Trying to subscribe to pokerwars.io ...')
            r = requests.get(bot_endpoint + '/pokerwars.io/ping')
            print(r.status_code)
            if r.status_code == 200:
                down = False
                r = requests.post('https://play.pokerwars.io/v1/pokerwars/subscribe', json={'username': 'andrewxinchen', 'token': api_token, 'botEndpoint': bot_endpoint, 'notifications': bool(notifications)})
                print('Subscription --> Status code: ' + str(r.status_code))
                print('Subscription --> Body: ' + str(r.json()))
                if r.status_code != 202:
                    print('Failed to subscribe, aborting ...')
                    exit()
        except:
            exit()
        sleep(2)

if __name__ == '__main__':
    s = Thread(target=subscribe)
    s.daemon = True
    s.start()
    run(port=port)
