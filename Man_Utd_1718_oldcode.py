# -*- coding: utf-8 -*-
"""
Created on Wed Aug  8 17:31:10 2018

@author: Gerald Lim

Simple web-scraper from Transfermarkt for Man Utd 2017/18 player minutes per game. Also tested successfully
with Arsenal.

"""
#%% Individual Player Match Data
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import re
import networkx as nx
import json

import sys
sys._enablelegacywindowsfsencoding() #Deal with pandas problem with reading file with accents in file path i.e Alexis Sánchez, Victor Lindelöf 


headers = {'User-Agent': 
           'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36'} 
    
def scrapePlayer(pName, link):
    '''
    Function for scraping the information on minutes played for every game of the 17/18 EPL-season for a player
    in a particular team 
    '''
    #Load the player perfomance data page 
    page = link
    #print (page)
    pageTree = requests.get(page, headers=headers)
    pageSoup = BeautifulSoup(pageTree.content, 'html.parser') 
    #Select only the target competition data (EPL in this case)
    allcomps = pageSoup.find_all(class_="table-header img-vat")
    #Find the index in the competition list where EPL is 
    matchday = np.arange(1,39).tolist()
    minutes = [0 for i in range(38)]
    subIn = [0 for i in range(38)]
    subOut = [0 for i in range(38)]
    
    '''
    Still pretty limited here but should be straightforward to copy/paste code to add in options for 
    more competitions.
    '''
    
    pl_index = 0
    for i in allcomps:
        if i.get_text(strip=True) == "Premier League":
            pl_index = allcomps.index(i)
    #print (pl_index)
    #If EPL data is available, scrape match data
    if pl_index != 0:
        results_epl = pageSoup.find_all(class_="responsive-table")[pl_index+1]
        #print (results_epl)
        #match = results_epl.find_all('tr',class_='','bg_rot_20','bg_gelb_20')
        #Find all EPL matches 
        
        #This re.compile method magically works somehow
        match = results_epl.find_all("tr", { "class" : re.compile(r"^(|bg_rot_20|bg_gelb_20)$") })
        #print (match[12].get_text(strip=True))
        #print (len(match))
        
        for j in range(0, len(match)):
            #Check that the guy was playing for Man Utd in this match (For cases like Mr Alexis)
            playerTeam =  match[j].select('td[class="no-border-links "]')[0]
            if playerTeam.find('a').get_text() == "Man Utd":
                if len(match[j].find_all('td')) == 17:
                    #Match Data array length of 17 indicates Player was in the matchday squad
                    minutes[j] = int(match[j].find_all('td')[16].get_text().replace("'",""))  
                    #Check if theres any substitution data for the player
                    a = match[j].find_all('td')[14].get_text(strip=True)
                    if a != "":
                        subIn[j] = int(a.replace("'",""))
                    #Likewise for sub-out data    
                    b = match[j].find_all('td')[15].get_text(strip=True)
                    if b != "":
                        subOut[j] = int(b.replace("'",""))
    eplData = [minutes, subIn, subOut]     
    return eplData               
    #eplData = pd.DataFrame({"Matchday": matchday, "Minutes Played": minutes, "Sub-In": subIn, "Sub-Out": subOut})    
    #eplData.to_csv(pName+'.csv', encoding='utf-8', index=False)            

#%%
def scrapeTeam():
    '''
    Scraping function for EPL teams' player's minutes per-game. Current function doesn't take any arg
    but should in the future take the team name or code (for e.g. Man Utd has a code 985) that will 
    direct the scraper to the correct webpage. 
    '''
    teamData = []
    playerNames = []
    #Default team is Man Utd for now 
    #Variables are the club name "Man Utd" and the id "985" for instance 
    teamPage = "https://www.transfermarkt.co.uk/manchester-united/kader/verein/985/saison_id/2017/plus/1"
    teamPageTree = requests.get(teamPage, headers=headers)
    teamPageSoup = BeautifulSoup(teamPageTree.content, 'html.parser') 
    
    players = teamPageSoup.find_all(class_="spielprofil_tooltip")[::2]
    #Get individual player data
    
    for x in players:
        pName = x.get_text()
        playerNames.append(pName)
        link = 'https://www.transfermarkt.co.uk'+x['href'].replace('profil','leistungsdaten')+'/plus/1?saison=2017'
        teamData.append(scrapePlayer(pName,link))
        
    return teamData, playerNames
        
    
#%%
#Read Scraped Data and Sort the Network
        
def minutesSheet():
    '''
    Saves a csv/spreadsheet of the scraped team's shared minutes between every player in the squad (that
    played at least a minute)
    '''
    global playerNames
    global teamData
    teamData, playerNames = scrapeTeam()
    allData = []    
    
    
    #Remove players that played zero minutes 
    global indices
    indices = []
    for i in range(len(teamData)):
        if sum(teamData[i][0]) == 0:
            indices.append(i)
            
    for j in sorted(indices, reverse = True):
        del teamData[j], playerNames[j]        
            
        
    for x in teamData: #Loop through squad 
        player = x
        #print (player)
        minuteData = []
        for y in teamData: #Second loop to calculate shared min btn players 
            
            teamMate = y
            #print (teamMate)
            sharedMin = 0
            
            for z in range(0, len(player[0])): #Loop through the Matchdays
                if player[1][z] == 0 and teamMate[1][z] == 0:      
                    #print ("Neither Subbed In")
                    sharedMin += min(player[0][z],teamMate[0][z])
                elif player[2][z] == 0 and teamMate[2][z] == 0:   
                    #print ("Neither Subbed Out")
                    sharedMin += min(player[0][z],teamMate[0][z])
                elif player[0][z] == 0 or teamMate[0][z] == 0:
                    #print ("One didnt play")
                    pass
                else:
                    #print ("Others")                    
                    sharedMin += abs(abs(player[2][z]-player[1][z])-abs(teamMate[2][z]-teamMate[1][z]))
            minuteData.append(sharedMin)
        #print (minuteData)
        allData.append(minuteData)
        
    df =pd.DataFrame(allData,columns=playerNames)
    df.insert(loc=0, column='Shared Minutes', value=playerNames) #For neatness sake when viewing csv file
    df.to_csv('Man Utd.csv', encoding='utf-8', index = False)  

#%% Network Plotting        

def teamNetwork():
    '''
    Creates a network/graph using each player as nodes and the shared minutes as weights for edges. 
    Was the original idea, may visualise using a correlation matrix/ something else instead. 
    '''
    allData = pd.read_csv('Man Utd.csv', header = None)
    allNames = allData[0][1:].tolist()     
    global G
    G = nx.Graph()
    G.add_nodes_from([i for i in range(0, len(allNames))])
    for i in range(0,len(allNames)):
        G.nodes[i]['name'] = allNames[i]
        G.nodes[i]['minutes'] = int(allData[i+1][i+1])
    
    #Add Edges between players and the respective weights (shared playing times)
    for j in range(1, len(allData)):
        for k in range(j+1, len(allData)):
            #print (k)
            if float(allData[j+1][k]) != 0:
                G.add_edge(j-1,k-1, weight = round(float(allData[j][k])*0.01,2))
            
    return G
#G.add_nodes_from([i for i in range(0,)])

'''
#For importing to json

from networkx.readwrite import json_graph
data = json_graph.node_link_data(G)
with open('graph.json', 'w') as f:
    json.dump(data, f, indent=4)


'''        
