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

        for vegstrekning in tqdm.tqdm(vegstrekninger):
            self.temp_df = self.df[self.df['vegstrekning'].apply(lambda x: vegstrekning in x)]
            if vegstrekning[0] in ["F", "E", "R"]:
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
        db.commit()
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
        try:
            module = __import__(f'flaskr.kvalitetskontroller.{kvalitetselement.get("kv_1")}.{kvalitetselement.get("kv_2")}.{kvalitetselement.get("kv_3").replace(" ","_")}', fromlist=[''])
            function = getattr(module, kvalitetselement.get("kv_1")+"_"+kvalitetselement.get("kv_2")+"_"+kvalitetselement.get("kv_3").replace(" ","_")+"_kvalitet")
        except:
            return False
        self.kvalitetsmåling, self.referanseverdi = function(self.temp_temp_df, self.egenskapstyper)
        db = get_db()
        vegstrekning_id = db.execute(
            "SELECT id FROM vegstrekning WHERE fylke_id = ? AND kommune_id = ? AND navn = ?",
            (fylke if kommune == 0 else (int(str(kommune)[:2]) if int(str(kommune)[:2]) != 30 else int(str(kommune)[:1])), kommune, vegstrekning)
        ).fetchone()
        if vegstrekning_id:
            vegstrekning_id = vegstrekning_id[0]
            self.registrer_kvalitet(kvalitetselement['id'], vegstrekning_id)
        else:
            vegstrekning_id = None
        
        
    def registrer_kvalitet(self, kvalitetselement_id, vegstrekning_id):
        db = get_db()
        if isinstance(self.kvalitetsmåling, int):
            #Hvis kvaliteten er på vegobjektnivå
            db.execute(
                "INSERT INTO kvalitetsmåling (kvalitetselement_id, vegobjekttype_id, verdi, ref_verdi, vegstrekning_id) VALUES (?, ?, ?, ?, ?)",
                (kvalitetselement_id, self.vegobjekttype_id, self.kvalitetsmåling, self.referanseverdi, vegstrekning_id)
                )
        elif isinstance(self.kvalitetsmåling, dict):
            #Hvis kvaliteten er på egenskapstypenivå
            for egenskapstype_id, verdi in self.kvalitetsmåling.items():
                db.execute(
                    "INSERT INTO kvalitetsmåling (kvalitetselement_id, vegobjekttype_id, egenskapstype_id, verdi, ref_verdi, vegstrekning_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (kvalitetselement_id, self.vegobjekttype_id, egenskapstype_id, verdi, self.referanseverdi, vegstrekning_id)
                    )
        return True

if __name__ == "__main__":
    kvalitet = Automatisk_registrer_kvalitet(470)