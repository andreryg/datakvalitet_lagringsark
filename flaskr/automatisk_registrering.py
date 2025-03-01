import requests
from flaskr.db import get_db
from flaskr.last_ned_datasett import hent_datasett
import tqdm
import ast
import pandas as pd

class Automatisk_registrer_kvalitet():
    pd.options.mode.chained_assignment = None  # default='warn'
    def __init__(self, vegobjekttype_id):
        self.vegobjekttype_id = vegobjekttype_id
        db = get_db()
        print(self.vegobjekttype_id, type(self.vegobjekttype_id))
        self.egenskapstyper = db.execute(
            "SELECT * FROM egenskapstype WHERE vegobjekttype_id = ?",
            (self.vegobjekttype_id,)
        ).fetchall()
        self.egenskapstyper = [dict(row) for row in self.egenskapstyper]

        kvalitetselementer = db.execute(
            """select kvalitetselement.id, lower(kvalitetsnivå_1.navn) as kv_1, lower(kvalitetsnivå_2.navn) as kv_2, lower(kvalitetselement.navn) as kv_3 from kvalitetselement
            join kvalitetsnivå_1 on kvalitetselement.kvalitetsnivå_1 = kvalitetsnivå_1.id
            join kvalitetsnivå_2 on kvalitetselement.kvalitetsnivå_2 = kvalitetsnivå_2.id"""
        ).fetchall()
        kvalitetselementer = [dict(row) for row in kvalitetselementer]

        self.df = hent_datasett(vegobjekttype_id, 'inkluder=alle&vegsystemreferanse=E,R,F,K')
        self.df = self.df.rename(columns={"lokasjon.fylker":"fylke",
                                          "lokasjon.kommuner":"kommune",
                                          "lokasjon.vegsystemreferanser":"vegsystemreferanse", 
                                          "relasjoner.foreldre":"foreldre", 
                                          "relasjoner.barn":"barn"})

        self.df['vegstrekning'] = self.df['vegsystemreferanse'].apply(lambda x: [i.get('kortform').split("D")[0] for i in x])
        vegstrekninger = self.df['vegstrekning'].explode().unique().tolist()

        for vegstrekning in vegstrekninger:
            self.temp_df = self.df[self.df['vegstrekning'].apply(lambda x: vegstrekning in x)]
            if vegstrekning[0] == "F":
                fylker = self.temp_df['fylke'].explode().unique().tolist()
                for fylke_id in fylker:
                    self.temp_temp_df = self.temp_df[self.temp_df['fylke'].apply(lambda x: fylke_id in x)]
                    for kvalitetselement in kvalitetselementer:
                        self.hent_kvalitet(kvalitetselement, vegstrekning, fylke_id, 0)
            elif vegstrekning[0] == "K":
                kommuner = self.temp_df['kommune'].explode().unique().tolist()
                for kommune_id in kommuner:
                    self.temp_temp_df = self.temp_df[self.temp_df['kommune'].apply(lambda x: kommune_id in x)]
                    for kvalitetselement in kvalitetselementer:
                        self.hent_kvalitet(kvalitetselement, vegstrekning, 0, kommune_id)
            else:
                self.temp_temp_df = self.temp_df
                for kvalitetselement in kvalitetselementer:
                    self.hent_kvalitet(kvalitetselement, vegstrekning, 0, 0)

        #Se på hvilke vegstrekninger som inngår i self.df
        #for hver vegstrekning i self.df: 
            #filtrer self.df på vegstrekningen
            #for hver kvalitetselement:
                #Lagre referanseverdi
                #Finn kvaliteten ved å hente funksjonen som tilsvarer kvalitetselementet.
                #(Funksjoner returnerer en verdi hvis kvalitet lagres på objekttypenivå)
                #(Funksjoner returnerer en dictionary hvis kvalitet lagres på egenskapstypenivå (et_id er key, kvalitet er value))
                #Lagre kvaliteten
        #Lagre kvalitetene i databasen

        #Et problem her at jeg må finne riktig strekning id mtp fylke og kommune.
    def hent_kvalitet(self, kvalitetselement, vegstrekning, fylke, kommune):
        self.referanseverdi = self.temp_temp_df.shape[0]
        try:
            module = __import__(f'flaskr.kvalitetskontroller.{kvalitetselement.get("kv_1")}.{kvalitetselement.get("kv_2")}.{kvalitetselement.get("kv_3")}', fromlist=[''])
            function = getattr(module, kvalitetselement.get("kv_1")+"_"+kvalitetselement.get("kv_2")+"_"+kvalitetselement.get("kv_3")+"_kvalitet")
        except:
            return False
        self.kvalitetsmåling = function(self.temp_temp_df, self.egenskapstyper)
        db = get_db()
        vegstrekning_id = db.execute(
            "SELECT id FROM vegstrekning WHERE fylke_id = ? AND kommune_id = ? AND navn = ?",
            (fylke if kommune == 0 else (int(str(kommune)[:2]) if int(str(kommune)[:2]) != 30 else int(str(kommune)[:1])), kommune, vegstrekning)
        ).fetchone()
        if vegstrekning_id:
            vegstrekning_id = vegstrekning_id[0]
        else:
            vegstrekning_id = None
        if vegstrekning_id == None:
            print(vegstrekning, fylke, kommune)
        #print(kvalitetselement['id'], vegstrekning_id, self.referanseverdi, self.kvalitetsmåling)
        #self.registrer_kvalitet(kvalitetselement['id'], vegstrekning_id, 0)

    def hent_kvalitetsmåling(self):
        db = get_db()
        kvalitetselementer = db.execute(
            "SELECT * FROM kvalitetselement"
        ).fetchall()
        kvalitetselementer = [dict(row) for row in kvalitetselementer]
        områder = db.execute(
        "SELECT * FROM område JOIN vegsystem ON område.vegsystem_id = vegsystem.id JOIN vegkategori ON vegsystem.vegkategori_id = vegkategori.id WHERE fylke_id IS NOT NULL AND vegsystem_id > 2"
        ).fetchall()
        områder = [dict(row) for row in områder]
        for kvalitetselement in tqdm.tqdm(kvalitetselementer):
            for område in områder:
                vegkategori = område['kortnavn']
                vegnummer = område['vegnummer']
                fylke = område['fylke_id']
                if (vegkategori == 'E' or vegkategori == 'R') and not vegnummer: #E og R veg håndteres i aggregering.
                    continue
                self.temp_df = self.df[self.df['fylke'].apply(lambda x: fylke in x)]
                self.temp_df = self.temp_df[self.temp_df['vegsystemreferanse'].apply(lambda x: any(d['vegsystem']['vegkategori'] == vegkategori for d in x))]
                if vegnummer:
                    self.temp_df = self.temp_df[self.temp_df['vegsystemreferanse'].apply(lambda x: any(d['vegsystem']['nummer'] == vegnummer for d in x))]
                self.referanseverdi = self.temp_df.shape[0]
                if kvalitetselement['id'] == 13: #Egenskaper.Fullstendighet.Generell
                    for egenskapstype in self.egenskapstyper:
                        self.antall = int(self.temp_df['egenskaper'].apply(lambda x: any(d.get('id') == egenskapstype['id'] for d in x)).sum())
                        self.registrer_kvalitet(kvalitetselement['id'], område['id'], egenskapstype['id'])
                if kvalitetselement['id'] == 14: #Egenskaper.Fullstendighet.Påkrevd egenskapsverdi
                    for egenskapstype in self.egenskapstyper:
                        if egenskapstype['viktighet'] == "PÅKREVD_IKKE_ABSOLUTT" or egenskapstype['viktighet'] == "PÅKREVD_ABSOLUTT":
                            self.antall = int(self.temp_df['egenskaper'].apply(lambda x: any(d.get('id') == egenskapstype['id'] for d in x)).sum())
                            self.registrer_kvalitet(kvalitetselement['id'], område['id'], egenskapstype['id'])
                if kvalitetselement['id'] == 15: #Egenskaper.Fullstendighet.Betinga egenskapsverdi
                    for egenskapstype in self.egenskapstyper:
                        if egenskapstype['viktighet'] == "BETINGET":
                            self.antall = int(self.temp_df['egenskaper'].apply(lambda x: any(d.get('id') == egenskapstype['id'] for d in x)).sum())
                            self.registrer_kvalitet(kvalitetselement['id'], område['id'], egenskapstype['id'])
                if kvalitetselement['id'] == 29: #Egengeometri.Fullstendighet.Linjegeometri
                    self.antall = -1
                    for egenskapstype in self.egenskapstyper:
                        if egenskapstype['navn'] == "Geometri, punkt":
                            self.antall = int(self.temp_df['egenskaper'].apply(lambda x: any(d.get('id') == egenskapstype['id'] for d in x)).sum())
                    self.registrer_kvalitet(kvalitetselement['id'], område['id'], 0)
                if kvalitetselement['id'] == 30: #Egengeometri.Fullstendighet.Linjegeometri
                    self.antall = -1
                    for egenskapstype in self.egenskapstyper:
                        if egenskapstype['navn'] == "Geometri, linje":
                            self.antall = int(self.temp_df['egenskaper'].apply(lambda x: any(d.get('id') == egenskapstype['id'] for d in x)).sum())
                    self.registrer_kvalitet(kvalitetselement['id'], område['id'], 0)
                if kvalitetselement['id'] == 31: #Egengeometri.Fullstendighet.Linjegeometri
                    self.antall = -1
                    for egenskapstype in self.egenskapstyper:
                        if egenskapstype['navn'] == "Geometri, flate":
                            self.antall = int(self.temp_df['egenskaper'].apply(lambda x: any(d.get('id') == egenskapstype['id'] for d in x)).sum())
                    self.registrer_kvalitet(kvalitetselement['id'], område['id'], 0)
                if kvalitetselement['id'] == 58: #Relasjon.Fullstendighet.Generell
                    self.antall = int(self.temp_df[['foreldre', 'barn']].notnull().any(axis=1).sum())
                    self.registrer_kvalitet(kvalitetselement['id'], område['id'], 0)
                if kvalitetselement['id'] == 59: #Relasjon.Fullstendighet.Morobjekt
                    self.antall = int(self.temp_df['foreldre'].notnull().sum())
                    self.registrer_kvalitet(kvalitetselement['id'], område['id'], 0)
                if kvalitetselement['id'] == 62: #Relasjon.Fullstendighet.Datterobjekt
                    self.antall = int(self.temp_df['barn'].notnull().sum())
                    self.registrer_kvalitet(kvalitetselement['id'], område['id'], 0)

    def hent_kvalitest(self):
        # Hente kvalitet fra api
        if self.kvalitetselement_id == 1: #Har egenskapsverdi
            # Har egenskapsverdi
            t = requests.get(f"https://nvdbapiles-v3.atlas.vegvesen.no/vegobjekter/{self.vegobjekttype_id}/statistikk?fylke={self.fylke_id}&vegsystemreferanse={self.vegsystem}&egenskap='{self.egenskapstype_id}!=null'")
            if t.status_code == 200:
                self.antall = t.json()["antall"]
            else:
                self.antall = -1

        elif self.kvalitetselement_id == 2: #Har påkrevd egenskapsverdi
            db = get_db()
            self.antall = db.execute(
                """SELECT verdi
                FROM kvalitetsmåling
                JOIN egenskapstype
                ON egenskapstype_id = egenskapstype.id
                WHERE kvalitetselement_id = 1 AND (egenskapstype.viktighet = "PÅKREVD_IKKE_ABSOLUTT" OR egenskapstype.viktighet = "PÅKREVD_ABSOLUTT")
                AND område_id = ? AND kvalitetsmåling.vegobjekttype_id = ? AND egenskapstype_id = ?
                """, (self.område_id, self.vegobjekttype_id, self.egenskapstype_id)
            ).fetchall()
            if self.antall:
                self.antall = [dict(row) for row in self.antall][0].get('verdi')
            else:
                self.antall = -1

        elif self.kvalitetselement_id == 7: #Har Linjegeometri
            db = get_db()
            self.antall = db.execute(
                """SELECT verdi
                FROM kvalitetsmåling
                JOIN egenskapstype
                ON egenskapstype_id = egenskapstype.id
                WHERE kvalitetselement_id = 1 AND egenskapstype.navn = 'Geometri, linje'
                AND område_id = ? AND kvalitetsmåling.vegobjekttype_id = ?
                """, (self.område_id, self.vegobjekttype_id)
            ).fetchall()
            if self.antall:
                self.antall = [dict(row) for row in self.antall][0].get('verdi')
            else:
                self.antall = -1

        else:
            return False

    def hent_referanseverdi(self):
        # Hente referanseverdi fra api
        if self.kvalitetselement_id == 1:
            # Har egenskapsverdi
            t = requests.get(f"https://nvdbapiles-v3.atlas.vegvesen.no/vegobjekter/{self.vegobjekttype_id}/statistikk?fylke={self.fylke_id}&vegsystemreferanse={self.vegsystem}")
            if t.status_code == 200:
                self.referanseverdi = t.json()["antall"]
            else:
                self.referanseverdi = -1

        elif self.kvalitetselement_id == 2: #Har påkrevd egenskapsverdi
            db = get_db()
            self.referanseverdi = db.execute(
                """SELECT verdi
                FROM referanseverdi
                WHERE kvalitetselement_id = 1
                AND område_id = ? AND referanseverdi.vegobjekttype_id = ?
                """, (self.område_id, self.vegobjekttype_id)
            ).fetchall()
            if self.referanseverdi:
                self.referanseverdi = [dict(row) for row in self.referanseverdi][0].get('verdi')
            else:
                self.referanseverdi = -1

        elif self.kvalitetselement_id == 7: #Har Linjegeometri
            db = get_db()
            self.referanseverdi = db.execute(
                """SELECT verdi
                FROM referanseverdi
                WHERE kvalitetselement_id = 1
                AND område_id = ? AND referanseverdi.vegobjekttype_id = ?
                """, (self.område_id, self.vegobjekttype_id)
            ).fetchall()
            if self.referanseverdi:
                self.referanseverdi = [dict(row) for row in self.referanseverdi][0].get('verdi')
            else:
                self.referanseverdi = -1
        
        else:
            return False
        
    def registrer_kvalitet(self, kvalitetselement_id, område_id, egenskapstype_id):
        if self.antall == -1 or self.referanseverdi == -1:
            return False
        db = get_db()
        db.execute(
            "INSERT INTO kvalitetsmåling (kvalitetselement_id, vegobjekttype_id, egenskapstype_id, verdi, område_id) VALUES (?, ?, ?, ?, ?)",
            (kvalitetselement_id, self.vegobjekttype_id, egenskapstype_id, self.antall, område_id)
            )
        sjekk = db.execute(
            "SELECT * FROM referanseverdi WHERE kvalitetselement_id = ? AND område_id = ? AND vegobjekttype_id = ?",
            (kvalitetselement_id, område_id, self.vegobjekttype_id)
            ).fetchone()
        if not sjekk:
            db.execute(
                "INSERT INTO referanseverdi (kvalitetselement_id, vegobjekttype_id, verdi, område_id) VALUES (?, ?, ?, ?)",
                (kvalitetselement_id, self.vegobjekttype_id, self.referanseverdi, område_id)
                )
        return True

if __name__ == "__main__":
    kvalitet = Automatisk_registrer_kvalitet(470)