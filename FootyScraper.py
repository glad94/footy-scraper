# -*- coding: utf-8 -*-
"""
Created on Wed Aug  8 17:31:10 2018

# Updated on Wed Jan 9 2019 

# Updated again on Fri 15/5/2020

--------------------------------------
Known Issues:
    
    - Norwich and Newcastle's 17 Aug 2019 match has been wrongly listed as 16 Aug on their team page, but not indiv player pages
    - Bundesliga players have an additional column "Rating" for their league matches only (as far as 11/12). So the row length check to see if 
    if they were in the match squad or not should be 18 instead of the usual 17. 
    - Lines ~114-115, for 'playerTeam' above, for some reason for Bundesliga it fetches e.g. 'Bayern Munich ' 
    hence it will never match with the 'team' arg and for loop ends here for each player. Need to [:-1] the string to match

    - Amdy Faye Stoke 09/10 data is messed up on the site 


@author: Gerald Lim

Simple web-scraper from Transfermarkt for any team's player minutes for a selected season 
in any competition or all competitions 

"""
#%% Individual Player Match Data
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import re
import networkx as nx
import json
import itertools
import sys
sys._enablelegacywindowsfsencoding() #Deal with pandas problem with reading file with accents in file path i.e Alexis Sánchez, Victor Lindelöf 


headers = {'User-Agent': 
           'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36'} 
    
def scrapePlayer(pName, link, comp, team, ms, sI, sO, compNames, gN):
    '''
    Function for scraping the information on minutes played for every game of the 17/18 EPL-season for a player
    in a particular team 
    
    Parameters:
            comp: str
                The competition to scrap data from {"Premier League", "UEFA Champions League", "FA Cup", etc.} *Gotta be precise with this 
            team: str
                Team of interest {"Man Utd", "Arsenal", etc.}
            link: str
                Link/URL to the player's detailed Transfermarkt stats page 
            ms: list 
                Initial empty list (per player) to store their minutes played per list index
            sI: list
                Initial empty list (per player) to store their minute subbed in per list index
            sO: list
                Initial empty list (per player) to store their minute subbed out per list index
            compNames:
                
            gN: list
                
            
    '''
    #Load the player perfomance data page 
    page = link
    #print (page)
    pageTree = requests.get(page, headers=headers)
    pageSoup = BeautifulSoup(pageTree.content, 'html.parser') 
    #Select only the target competition data (EPL in this case)
    allcomps = pageSoup.find_all(class_="table-header img-vat")

    
    '''
    Still pretty limited here but should be straightforward to copy/paste code to add in options for 
    more competitions.
    
    Jan edit: Ability to specify competition and also scrape for all competitions. 
    '''
    
    
    
    if comp != "all":
        
        minutes = np.zeros_like(ms).tolist()
        subIn = np.zeros_like(sI).tolist()
        subOut = np.zeros_like(sO).tolist() 
        
        
        
        comp_index = 100
        for i in allcomps:
            if i.get_text(strip=True) == comp:
                comp_index = allcomps.index(i)
        #print (comp_index)
        
        #####Screws up here due to Axel Tuanzebe not having any champs league/PL in 2018/19 data?? 13/5/2020
        if comp_index == 100: # Player was not registered for that season (e.g. been on loan)
            minData = [minutes, subIn, subOut] # Zero arrays for that player returned 
            
        else:
            
            results_comp = pageSoup.find_all(class_="responsive-table")[comp_index+1]
            #print (results_comp)
            #match = results_comp.find_all('tr',class_='','bg_rot_20','bg_gelb_20')
            
            #This re.compile method magically works somehow
            match = results_comp.find_all("tr", { "class" : re.compile(r"^(|bg_rot_20|bg_gelb_20)$") })
         
            for j in range(0, len(match)):
                #Check that the guy was playing for Man Utd in this match (For cases like Mr Alexis)
                #print (match[j].select('td[class="no-border-links"]'))
                playerTeam =  match[j].select('td[class="no-border-links"]')[0]
                
                # For playerTeam above, for some reason for Bundesliga it fetches many e.g. 'Bayern Munich' 
                # strings hence it will never match with the 'team' arg and for loop ends here for each player 
                
                '''
                Remove the [:-1] if not for German teams...web bug? 
                '''
                if playerTeam.find('a').get_text() == team:
                    #print (True)
                    
                    if len(match[j].find_all('td')) == 17:
                        
                        #Match Data array length of 17 indicates Player was in the matchday squad
                        
                        #Proper matching of matchdays to array by date
                        gamedate = match[j].find_all('td')[1].get_text(strip=True)
                
                        gameID = gN.index(gamedate)
                        
                        minutes[gameID] = int(match[j].find_all('td')[-1].get_text().replace("'",""))  
                        #Check if theres any substitution data for the player
                        a = match[j].find_all('td')[14].get_text(strip=True)
                        if a != "":
                            subIn[gameID] = int(a.replace("'",""))
                        #Likewise for sub-out data    
                        b = match[j].find_all('td')[15].get_text(strip=True)
                        if b != "":
                            subOut[gameID] = int(b.replace("'",""))
                        #Also check if the player got a red card and we can take this as a sub out 
                        c = match[j].find_all('td')[13].get_text(strip=True)
                        if c != "":
                            subOut[gameID] = int(c.replace("'",""))
            minData = [minutes, subIn, subOut]
            #print (pName, minData)
        
    
    elif comp == "all": 
    
        minutes = [np.zeros_like(b).tolist() for b in ms]
        #print (minutes)
        subIn = [np.zeros_like(b).tolist() for b in sI]
        subOut = [np.zeros_like(b).tolist() for b in sO]
    
        # Loop through each competition and scrape the game data 
        for i in allcomps:
            if i.get_text(strip=True) in compNames:
            
                comp_index = allcomps.index(i)
                team_index = compNames.index(i.get_text(strip=True))
        
                results = pageSoup.find_all(class_="responsive-table")[comp_index+1]
                #print (results)
                #match = results.find_all('tr',class_='','bg_rot_20','bg_gelb_20')
                #Find all EPL matches 
                
                #This re.compile method magically works somehow
                match = results.find_all("tr", { "class" : re.compile(r"^(|bg_rot_20|bg_gelb_20)$") })
                
                #print (match[12].get_text(strip=True))
                #print (len(match))
                    
                    
                
                for j in range(0, len(match)):
                    #Check that the guy was playing for Man Utd in this match (For cases like Mr Alexis)
                    playerTeam =  match[j].select('td[class="no-border-links "]')[0]
                    if playerTeam.find('a').get_text() == team:
                        if len(match[j].find_all('td')) == 17:
                            
                            #Proper matching of matchdays to array
                            gamedate = match[j].find_all('td')[1].get_text(strip=True)
                            gameID = gN[team_index].index(gamedate)
                            
                            #Match Data array length of 17 indicates Player was in the matchday squad
                            
                            ## Cmon Scholesly mate..website bugs for their 98/99 data
                            if match[j].find_all('td')[-1].get_text() == "" and pName == "Paul Scholes" :
                                minutes[team_index][gameID] = 8
                            elif match[j].find_all('td')[-1].get_text() == "" and pName == "Ole Gunnar Solskjaer" :
                                minutes[team_index][gameID] = 22
                                
                            else:
                                
                                minutes[team_index][gameID] = int(match[j].find_all('td')[-1].get_text().replace("'",""))  
                            
                            #Check if theres any substitution data for the player
                            a = match[j].find_all('td')[14].get_text(strip=True)
                            if a != "":
                                subIn[team_index][gameID] = int(a.replace("'",""))
                            #Likewise for sub-out data    
                            b = match[j].find_all('td')[15].get_text(strip=True)
                            if b != "":
                                subOut[team_index][gameID] = int(b.replace("'",""))
                            #Also check if the player got a red card and we can take this as a sub out 
                            c = match[j].find_all('td')[13].get_text(strip=True)
                            if c != "":
                                subOut[team_index][gameID] = int(c.replace("'",""))
               
                
        #Flatten lists 
        minutes = list(itertools.chain.from_iterable(minutes))
        subIn = list(itertools.chain.from_iterable(subIn))
        subOut = list(itertools.chain.from_iterable(subOut))
        
                            
        minData = [minutes, subIn, subOut]     
        
    #print (minutes)    
    return minData               
    #allData = pd.DataFrame({"Matchday": matchday, "Minutes Played": minutes, "Sub-In": subIn, "Sub-Out": subOut})    
    #allData.to_csv(pName+'.csv', encoding='utf-8', index=False)            

#%%
def scrapeTeam(comp, team, teamNum, seas):
    '''
    Scraping function for EPL teams' player's minutes per-game. Current function doesn't take any arg
    but should in the future take the team name or code (for e.g. Man Utd has a code 985) that will 
    direct the scraper to the correct webpage. 
    '''
    teamData = [] # Minutes/Sub-in/Sub-out Data
    playerNames = [] # Names
    playerPos = [] # Positions
    playerSpos = [] # Sub-positions
    #Default team is Man Utd for now 
    #Variables are the club name "Man Utd" and the id "985" for instance 
    # Note that only the team number controls the page, i.e. manchester-united and 131 directs to the FC Barca page anyway 
    teamPage = f"https://www.transfermarkt.co.uk/manchester-united/kader/verein/{teamNum}/saison_id/{seas}/plus/1"
    teamPageTree = requests.get(teamPage, headers=headers)
    teamPageSoup = BeautifulSoup(teamPageTree.content, 'html.parser') 
    
    players = teamPageSoup.find_all(class_="spielprofil_tooltip")[::2]
    
    # Get info on player's positions (Defender, Forward)
    regex = re.compile('.*zentriert rueckennummer.*')
    player_pos = teamPageSoup.find_all("td", {"class" : regex})
    
    # Get info such as sub-position (CB, LB, CF)
    player_subpos = teamPageSoup.find_all(class_="inline-table")
    
    
    #Get the team's match data from that season (how many matches were played in each competition etc.)
    teamPage0 = f"https://www.transfermarkt.co.uk/manchester-united/spielplan/verein/{teamNum}/saison_id/{seas}"
    teamPageTree0 = requests.get(teamPage0, headers=headers)
    teamPageSoup0 = BeautifulSoup(teamPageTree0.content, 'html.parser') 
    
    #Find all comps the team participated in that year 
    allcomps = teamPageSoup0.find_all(class_="table-header")[1:-1]
    #print(allcomps)
    compNames = [] #Store the names of those competitions, so that when scraping a player's data, only the relevant matches are taken 
                    # i.e. if i'm getting Zlatan's data for Man Utd, the LAG match data will be ignored 
    
    if comp != "all":
        comp_index = 100
        for i in allcomps:
            if i.get_text(strip=True) == comp:
                comp_index = allcomps.index(i)
        #print (comp_index)
        
        results_comp = teamPageSoup0.find_all(class_="responsive-table")[comp_index]
        #print (results_comp)
        #match = results_comp.find_all('tr',class_='','bg_rot_20','bg_gelb_20')
        
        #This re.compile method magically works somehow
        matches = results_comp.find_all("tbody")
        match = matches[0].find_all("tr")
        
        gN = []
        for x in range(len(match)):
                #print(match[x].find_all('td')[1].get_text(strip=True))
                gamenum = match[x].find_all('td')[1].get_text(strip=True)[4:]
                
                # This EXTRA line here for Newcastle n Norwich because of wrong data on website
                #if gamenum == 'Aug 16, 2019':
                #    gamenum = 'Aug 17, 2019'
                
                gN.append(gamenum)
        ms = [0 for i in range(len(match))]
        sI = [0 for i in range(len(match))]
        sO = [0 for i in range(len(match))]
    
    elif comp == "all":
        
        ms = []
        sI = []
        sO = []
        gN = []
        
        for i in allcomps:
            comp_index = allcomps.index(i)
            compNames.append(i.get_text(strip=True)) 
            
            results = teamPageSoup0.find_all(class_="responsive-table")[comp_index]
            matches = results.find_all("tbody")
            match = matches[0].find_all("tr")
            #Get matchday (e.g. Matchday 1, RO16, Quarter Final Replay)
            
            gamenames = []
            for x in range(len(match)):
                gamenum = match[x].find_all('td')[1].get_text(strip=True)[4:]
                
                # This EXTRA line here for Newcastle n Norwich because of wrong data on website
                #if gamenum == 'Aug 16, 2019':
                #    gamenum = 'Aug 17, 2019'
                
                gamenames.append(gamenum)
                
            
            ms_comp = [0 for i in range(len(match))]
            sI_comp = [0 for i in range(len(match))]
            sO_comp = [0 for i in range(len(match))]
            
            ms.append(ms_comp)
            sI.append(sI_comp)
            sO.append(sO_comp)
            gN.append(gamenames)
        #print (gN)       
    #print (players)
    #Get individual player data
    for x in players:
        pName = x.get_text()
        print (pName)
        playerNames.append(pName) #Names
        pPos = player_pos[players.index(x)]['title']
        playerPos.append(pPos)
        pSpos = player_subpos[players.index(x)].find_all('td')[-1].get_text() #Sub-Positions
        playerSpos.append(pSpos)
        #print (pName)
        link = 'https://www.transfermarkt.co.uk'+x['href'].replace('profil','leistungsdaten')+f'/plus/1?saison={seas}'
        #print (link)
        teamData.append(scrapePlayer(pName,link,comp,team, ms, sI, sO, compNames, gN))
    #Save the indiv player min per game data into npy file 
    np.save(f"{team}.npy", teamData)
    return teamData, playerNames, playerPos, playerSpos
    
    
#%%
#Read Scraped Data and Sort the Network
        
def minutesSheet(title, comp, team, teamNum, seas):
    '''
    Saves a csv/spreadsheet of the scraped team's shared minutes between every player in the squad (that
    played at least a minute)
    '''
    global playerNames
    global teamData
    teamData, playerNames, playerPos, playerSpos = scrapeTeam(comp, team, teamNum, seas)
    allData = []    
    
    
    #Remove players that played zero minutes 
    global indices
    indices = []
    for i in range(len(teamData)):
        if sum(teamData[i][0]) == 0:
            indices.append(i)
            
    for j in sorted(indices, reverse = True):
        del teamData[j], playerNames[j], playerPos[j], playerSpos[j]         
            
        
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
                
                # One player played the full game, other had subs 
                elif player[1][z] == 0 and player[2][z] == 0:
                    sharedMin += min(player[0][z],teamMate[0][z])
                elif teamMate[1][z] == 0 and teamMate[2][z] == 0:
                    sharedMin += min(player[0][z],teamMate[0][z])
                
                #diagonal 0s one wasn't subbed in, one wasn't subbed out 
                elif (player[1][z] == 0  and teamMate[2][z] == 0):
                    if player[2][z] - teamMate[1][z] > 0:
                        sharedMin += player[2][z] - teamMate[1][z] 
                elif (player[2][z] == 0  and teamMate[1][z] == 0):
                    if teamMate[2][z] - player[1][z] > 0:
                        sharedMin += teamMate[2][z] - player[1][z]
                
                #Only one zero 
                elif (player[1][z] == 0 or teamMate[2][z] == 0):
                    if player[2][z] - teamMate[1][z] > 0:
                        sharedMin += player[2][z] - teamMate[1][z]
                elif (player[2][z] == 0 or teamMate[1][z] == 0):
                    if teamMate[2][z] - player[1][z] > 0:
                        sharedMin += teamMate[2][z] - player[1][z]
                
                else:
                    #Check for playtime overlap. Do the subIn/Out diff have same sign
                    if np.sign(player[1][z] - teamMate[1][z]) == np.sign(player[2][z] - teamMate[2][z]):
                        check = min(player[2][z] - teamMate[1][z], teamMate[2][z] - player[1][z])
                        if check > 0:
                            sharedMin += check
                        else:
                            pass
                    else:
                        sharedMin += min(player[2][z] - player[1][z], teamMate[2][z] - teamMate[1][z])
                    # THIS IS FLAWEDDD
                    #print ("Others")                    
                    #sharedMin += abs(abs(player[2][z]-player[1][z])-abs(teamMate[2][z]-teamMate[1][z]))
            minuteData.append(sharedMin)
        #print (minuteData)
        allData.append(minuteData)
        
    df =pd.DataFrame(allData,columns=playerNames)
    df.insert(loc=0, column='Shared Minutes', value=playerNames) #For neatness sake when viewing csv file
    df.to_csv(f'{title}.csv', encoding='utf-8', index = False)
    
    # Tests
    print (team)
    #print (playerPos)
    #print (playerSpos)
    
    df1 = pd.DataFrame({'Name':playerNames, 'Position':playerPos,'Sub-position':playerSpos})
    df1.to_csv(f'{title}_positions.csv', encoding='utf-8', index = False)

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
#%%
# Getting the Team Numbers from any League 

def scrapeTeamNum(link):
    '''
    Scraping function for EPL teams' player's minutes per-game. Current function doesn't take any arg
    but should in the future take the team name or code (for e.g. Man Utd has a code 985) that will 
    direct the scraper to the correct webpage. 
    '''
    #Default team is Man Utd for now 
    #Variables are the club name "Man Utd" and the id "985" for instance 
    # Note that only the team number controls the page, i.e. manchester-united and 131 directs to the FC Barca page anyway 
    compPage = link
    compPageTree = requests.get(compPage, headers=headers)
    compPageSoup = BeautifulSoup(compPageTree.content, 'html.parser')
    
    teams = compPageSoup.find_all(class_="hauptlink no-border-links show-for-small show-for-pad")
    
    teamNames = [teams[x].find('a').get_text() for x in range(len(teams))]
    teamNums = [teams[x].find('a')['id'] for x in range(len(teams))]
    
    return teamNames, teamNums


teamNames, teamNums = scrapeTeamNum('https://www.transfermarkt.co.uk/premier-league/startseite/wettbewerb/GB1/plus/?saison_id=2009')
for team,ids in zip(teamNames[14:15], teamNums[14:15]):
    minutesSheet("Output/"+team+"_0910", "Premier League", team, ids, '2009')
  
