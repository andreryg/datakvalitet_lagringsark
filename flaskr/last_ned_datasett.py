# -*- coding: utf-8 -*-
"""
Created on Fri Jan 17 13:12:57 2025

@author: andryg
"""
import requests
import pandas as pd
import time

def hent_datasett(nvdbid, query):
    antall_hentet = 0
    antall_totalt = 0
    statistikk_url = f"https://nvdbapiles.atlas.vegvesen.no/vegobjekter/{nvdbid}/statistikk?{query}"
    r = requests.get(statistikk_url)
    if r.status_code == 200:
        antall_totalt = r.json().get('antall')
    print(antall_totalt)
    nvdb_url = f"https://nvdbapiles.atlas.vegvesen.no/vegobjekter/{nvdbid}?{query}"
    df_list = []
    while antall_hentet < antall_totalt:
        t = requests.get(nvdb_url)
        if t.status_code == 200:
            t = t.json()
            antall_hentet += t.get('metadata').get('returnert')
            df_list += [pd.json_normalize(t['objekter'])]
            nvdb_url = t.get('metadata').get('neste').get('href')
            print(antall_hentet, "/", antall_totalt)
        else:
            print("Error, prøver på nytt om 5 sekunder")
            time.sleep(5)
    df = pd.concat(df_list, ignore_index=True)
    return df

def main():
    df = hent_datasett(470, "inkluder=alle&alle_versjoner=false&vegsystemreferanse=E,R,F,K")
    df.to_excel("test.xlsx", index=False)
    
if __name__ == "__main__":
    main()