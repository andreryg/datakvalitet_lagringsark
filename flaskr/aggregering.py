from flaskr.db import get_db
import pandas as pd

def aggreger_vegstrekninger(kvalitetsmålinger, referanseverdier, vegstrekninger):
    vegstrekninger_df = pd.DataFrame(vegstrekninger)
    """Aggregerer data for vegstrekninger."""
    kvalitetselementer = list(set([i.get('kv_id') for i in kvalitetsmålinger]))
    for kv_id in kvalitetselementer:
        temp_kvalitetsmålinger_df = pd.DataFrame([i for i in kvalitetsmålinger if i.get('kv_id') == kv_id])
        temp_referanseverdier_df = pd.DataFrame([i for i in referanseverdier if i.get('kv_id') == kv_id])

        #Vegkategori
        temp_kvalitetsmålinger_df = pd.merge(temp_kvalitetsmålinger_df, vegstrekninger_df, left_on="vegstrekning_id", right_on="id")
        temp_referanseverdier_df = pd.merge(temp_referanseverdier_df, vegstrekninger_df, left_on="vegstrekning_id", right_on="id")
        print(temp_kvalitetsmålinger_df)


def aggreger_område(kv_id):
    """Aggregerer data for område."""
    db = get_db()
    områder = db.execute(
        "SELECT * FROM område LEFT JOIN vegsystem ON område.vegsystem_id = vegsystem.id"
        ).fetchall()
    
    # Convert to pandas DataFrame
    df_områder = pd.DataFrame(områder, columns=["id", "navn", "fylke_id", "kommune_id", "vegsystem_id", "vegsystem_id_id", "vegkategori_id", "fase", "vegnummer"])
    vt_et = db.execute(
                """SELECT vegobjekttype.navn, vegobjekttype.id, egenskapstype.navn AS et_navn, egenskapstype.id AS et_id
                FROM vegobjekttype
                LEFT JOIN egenskapstype ON vegobjekttype.id = egenskapstype.vegobjekttype_id
                UNION 
                SELECT vegobjekttype.navn, vegobjekttype.id, NULL AS et_navn, NULL AS et_id
                FROM vegobjekttype
                ORDER BY vegobjekttype.id, et_id"""
            ).fetchall()
    
    for row in vt_et:
        et_id = row["et_id"] if row["et_id"] else 0
        målinger = db.execute(
            """
            SELECT kvalitetsmåling.område_id, kvalitetsmåling.verdi, område.fylke_id, vegsystem.vegkategori_id, vegsystem.vegnummer
            FROM kvalitetsmåling 
            JOIN område ON kvalitetsmåling.område_id = område.id
            JOIN vegsystem ON område.vegsystem_id = vegsystem.id
            WHERE vegobjekttype_id = ? AND egenskapstype_id = ? AND kvalitetselement_id = ?
            """,
            (row["id"], et_id, kv_id)
            ).fetchall()
        referanseverdier = db.execute(
            """
            SELECT referanseverdi.område_id, referanseverdi.verdi, område.fylke_id, vegsystem.vegkategori_id, vegsystem.vegnummer
            FROM referanseverdi 
            JOIN område ON referanseverdi.område_id = område.id
            JOIN vegsystem ON område.vegsystem_id = vegsystem.id
            WHERE vegobjekttype_id = ? AND kvalitetselement_id = ?
            """,
            (row["id"], kv_id)
            ).fetchall()
        if målinger:
            målinger_df = pd.DataFrame(målinger, columns=["område_id", "verdi", "fylke_id", "vegkategori_id", "vegnummer"])
            #print(målinger_df)
            #Aggreger til Fylke+Vegkategori
            sum_verdi = målinger_df.groupby(["fylke_id", "vegkategori_id"])["verdi"].sum().reset_index()
            for _, sum_row in sum_verdi.iterrows():
                område_id = int(df_områder[(df_områder["fylke_id"] == sum_row["fylke_id"]) & (df_områder["vegkategori_id"] == sum_row["vegkategori_id"]) & (df_områder["vegnummer"].isna())]["id"].values[0])
                verdi = int(sum_row["verdi"])
                sjekk = db.execute(
                    "SELECT * FROM kvalitetsmåling WHERE kvalitetselement_id = ? AND område_id = ? AND vegobjekttype_id = ? AND egenskapstype_id = ?",
                    (kv_id, område_id, row['id'], et_id)
                ).fetchone()
                if not sjekk:
                    db.execute(
                        "INSERT INTO kvalitetsmåling (kvalitetselement_id, vegobjekttype_id, egenskapstype_id, verdi, område_id) VALUES (?, ?, ?, ?, ?)",
                        (kv_id, row['id'], et_id, verdi, område_id)
                    )
            referanseverdier_df = pd.DataFrame(referanseverdier, columns=["område_id", "verdi", "fylke_id", "vegkategori_id", "vegnummer"])
            sum_verdi = referanseverdier_df.groupby(["fylke_id", "vegkategori_id"])["verdi"].sum().reset_index()
            for _, sum_row in sum_verdi.iterrows():
                område_id = int(df_områder[(df_områder["fylke_id"] == sum_row["fylke_id"]) & (df_områder["vegkategori_id"] == sum_row["vegkategori_id"]) & (df_områder["vegnummer"].isna())]["id"].values[0])
                verdi = int(sum_row["verdi"])
                sjekk = db.execute(
                    "SELECT * FROM referanseverdi WHERE kvalitetselement_id = ? AND område_id = ? AND vegobjekttype_id = ?",
                    (kv_id, område_id, row['id'])
                ).fetchone()
                if not sjekk:
                    db.execute(
                        "INSERT INTO referanseverdi (kvalitetselement_id, vegobjekttype_id, verdi, område_id) VALUES (?, ?, ?, ?)",
                        (kv_id, row['id'], verdi, område_id)
                    )
            
            #Aggreger til Veg
            sum_verdi = målinger_df.groupby(["vegkategori_id", "vegnummer"])["verdi"].sum().reset_index()
            for _, sum_row in sum_verdi.iterrows():
                område_id = int(df_områder[(df_områder["vegnummer"] == sum_row["vegnummer"]) & (df_områder["vegkategori_id"] == sum_row["vegkategori_id"]) & (df_områder["fylke_id"].isna())]["id"].values[0])
                verdi = int(sum_row["verdi"])
                sjekk = db.execute(
                    "SELECT * FROM kvalitetsmåling WHERE kvalitetselement_id = ? AND område_id = ? AND vegobjekttype_id = ? AND egenskapstype_id = ?",
                    (kv_id, område_id, row['id'], et_id)
                ).fetchone()
                if not sjekk:
                    db.execute(
                        "INSERT INTO kvalitetsmåling (kvalitetselement_id, vegobjekttype_id, egenskapstype_id, verdi, område_id) VALUES (?, ?, ?, ?, ?)",
                        (kv_id, row['id'], et_id, verdi, område_id)
                    )

            sum_verdi = referanseverdier_df.groupby(["vegkategori_id", "vegnummer"])["verdi"].sum().reset_index()
            for _, sum_row in sum_verdi.iterrows():
                område_id = int(df_områder[(df_områder["vegnummer"] == sum_row["vegnummer"]) & (df_områder["vegkategori_id"] == sum_row["vegkategori_id"]) & (df_områder["fylke_id"].isna())]["id"].values[0])
                verdi = int(sum_row["verdi"])
                sjekk = db.execute(
                    "SELECT * FROM referanseverdi WHERE kvalitetselement_id = ? AND område_id = ? AND vegobjekttype_id = ?",
                    (kv_id, område_id, row['id'])
                ).fetchone()
                if not sjekk:
                    db.execute(
                        "INSERT INTO referanseverdi (kvalitetselement_id, vegobjekttype_id, verdi, område_id) VALUES (?, ?, ?, ?)",
                        (kv_id, row['id'], verdi, område_id)
                    )
    db.commit()

    for row in vt_et:
        et_id = row["et_id"] if row["et_id"] else 0
        målinger = db.execute(
            """
            SELECT kvalitetsmåling.område_id, kvalitetsmåling.verdi, område.fylke_id, vegsystem.vegkategori_id, vegsystem.vegnummer
            FROM kvalitetsmåling 
            JOIN område ON kvalitetsmåling.område_id = område.id
            JOIN vegsystem ON område.vegsystem_id = vegsystem.id
            WHERE vegobjekttype_id = ? AND egenskapstype_id = ? AND kvalitetselement_id = ? AND fylke_id IS NOT NULL AND vegnummer IS NULL
            """,
            (row["id"], et_id, kv_id)
            ).fetchall()
        referanseverdier = db.execute(
            """
            SELECT referanseverdi.område_id, referanseverdi.verdi, område.fylke_id, vegsystem.vegkategori_id, vegsystem.vegnummer
            FROM referanseverdi 
            JOIN område ON referanseverdi.område_id = område.id
            JOIN vegsystem ON område.vegsystem_id = vegsystem.id
            WHERE vegobjekttype_id = ? AND kvalitetselement_id = ? AND fylke_id IS NOT NULL AND vegnummer IS NULL
            """,
            (row["id"], kv_id)
            ).fetchall()
        if målinger:
            målinger_df = pd.DataFrame(målinger, columns=["område_id", "verdi", "fylke_id", "vegkategori_id", "vegnummer"])
            referanseverdier_df = pd.DataFrame(referanseverdier, columns=["område_id", "verdi", "fylke_id", "vegkategori_id", "vegnummer"])
            #Aggreger til Vegkategori
            sum_verdi = målinger_df.groupby(["vegkategori_id"])["verdi"].sum().reset_index()
            for _, sum_row in sum_verdi.iterrows():
                område_id = int(df_områder[(df_områder["vegnummer"].isna()) & (df_områder["vegkategori_id"] == sum_row["vegkategori_id"]) & (df_områder["fylke_id"].isna())]["id"].values[0])
                verdi = int(sum_row["verdi"])
                sjekk = db.execute(
                    "SELECT * FROM kvalitetsmåling WHERE kvalitetselement_id = ? AND område_id = ? AND vegobjekttype_id = ? AND egenskapstype_id = ?",
                    (kv_id, område_id, row['id'], et_id)
                ).fetchone()
                if not sjekk:
                    db.execute(
                        "INSERT INTO kvalitetsmåling (kvalitetselement_id, vegobjekttype_id, egenskapstype_id, verdi, område_id) VALUES (?, ?, ?, ?, ?)",
                        (kv_id, row['id'], et_id, verdi, område_id)
                    )

            sum_verdi = referanseverdier_df.groupby(["vegkategori_id"])["verdi"].sum().reset_index()
            for _, sum_row in sum_verdi.iterrows():
                område_id = int(df_områder[(df_områder["vegnummer"].isna()) & (df_områder["vegkategori_id"] == sum_row["vegkategori_id"]) & (df_områder["fylke_id"].isna())]["id"].values[0])
                verdi = int(sum_row["verdi"])
                sjekk = db.execute(
                    "SELECT * FROM referanseverdi WHERE kvalitetselement_id = ? AND område_id = ? AND vegobjekttype_id = ?",
                    (kv_id, område_id, row['id'])
                ).fetchone()
                if not sjekk:
                    db.execute(
                        "INSERT INTO referanseverdi (kvalitetselement_id, vegobjekttype_id, verdi, område_id) VALUES (?, ?, ?, ?)",
                        (kv_id, row['id'], verdi, område_id)
                    )
            #Aggreger til Fylke
            sum_verdi = målinger_df.groupby(["fylke_id"])["verdi"].sum().reset_index()
            for _, sum_row in sum_verdi.iterrows():
                område_id = int(df_områder[(df_områder["vegnummer"].isna()) & (df_områder["fylke_id"] == sum_row["fylke_id"]) & (df_områder["vegkategori_id"].isna())]["id"].values[0])
                verdi = int(sum_row["verdi"])
                sjekk = db.execute(
                    "SELECT * FROM kvalitetsmåling WHERE kvalitetselement_id = ? AND område_id = ? AND vegobjekttype_id = ? AND egenskapstype_id = ?",
                    (kv_id, område_id, row['id'], et_id)
                ).fetchone()
                if not sjekk:
                    db.execute(
                        "INSERT INTO kvalitetsmåling (kvalitetselement_id, vegobjekttype_id, egenskapstype_id, verdi, område_id) VALUES (?, ?, ?, ?, ?)",
                        (kv_id, row['id'], et_id, verdi, område_id)
                    )

            sum_verdi = referanseverdier_df.groupby(["fylke_id"])["verdi"].sum().reset_index()
            for _, sum_row in sum_verdi.iterrows():
                område_id = int(df_områder[(df_områder["vegnummer"].isna()) & (df_områder["fylke_id"] == sum_row["fylke_id"]) & (df_områder["vegkategori_id"].isna())]["id"].values[0])
                verdi = int(sum_row["verdi"])
                sjekk = db.execute(
                    "SELECT * FROM referanseverdi WHERE kvalitetselement_id = ? AND område_id = ? AND vegobjekttype_id = ?",
                    (kv_id, område_id, row['id'])
                ).fetchone()
                if not sjekk:
                    db.execute(
                        "INSERT INTO referanseverdi (kvalitetselement_id, vegobjekttype_id, verdi, område_id) VALUES (?, ?, ?, ?)",
                        (kv_id, row['id'], verdi, område_id)
                    )
            #Aggreger til Norge
            verdi = int(målinger_df["verdi"].sum())
            område_id = int(df_områder[(df_områder["vegnummer"].isna()) & (df_områder["fylke_id"].isna()) & (df_områder["vegkategori_id"].isna())]["id"].values[0])
            sjekk = db.execute(
                "SELECT * FROM kvalitetsmåling WHERE kvalitetselement_id = ? AND område_id = ? AND vegobjekttype_id = ? AND egenskapstype_id = ?",
                (kv_id, område_id, row['id'], et_id)
            ).fetchone()
            if not sjekk:
                db.execute(
                    "INSERT INTO kvalitetsmåling (kvalitetselement_id, vegobjekttype_id, egenskapstype_id, verdi, område_id) VALUES (?, ?, ?, ?, ?)",
                    (kv_id, row['id'], et_id, verdi, område_id)
                )

            verdi = int(referanseverdier_df["verdi"].sum())
            område_id = int(df_områder[(df_områder["vegnummer"].isna()) & (df_områder["fylke_id"].isna()) & (df_områder["vegkategori_id"].isna())]["id"].values[0])
            sjekk = db.execute(
                "SELECT * FROM referanseverdi WHERE kvalitetselement_id = ? AND område_id = ? AND vegobjekttype_id = ?",
                (kv_id, område_id, row['id'])
            ).fetchone()
            if not sjekk:
                db.execute(
                    "INSERT INTO referanseverdi (kvalitetselement_id, vegobjekttype_id, verdi, område_id) VALUES (?, ?, ?, ?)",
                    (kv_id, row['id'], verdi, område_id)
                )
    db.commit()

def aggreger_vegobjekttype(kv_id):
    """Aggregerer data for vegobjekttype."""
    db = get_db()
    vt = db.execute(
                """SELECT vegobjekttype.navn, vegobjekttype.id FROM vegobjekttype"""
            ).fetchall()
    
    for row in vt:
        målinger = db.execute(
            """
            SELECT kvalitetsmåling.område_id, kvalitetsmåling.verdi
            FROM kvalitetsmåling 
            WHERE vegobjekttype_id = ? AND kvalitetselement_id = ?
            """,
            (row["id"], kv_id)
        )
        referanseverdier = db.execute(
            """
            SELECT referanseverdi.område_id, referanseverdi.verdi
            FROM referanseverdi 
            WHERE vegobjekttype_id = ? AND kvalitetselement_id = ?
            """,
            (row["id"], kv_id)
        )
        
        if målinger:
            målinger_df = pd.DataFrame(målinger, columns=["område_id", "verdi"])
            #referanseverdier_df = pd.DataFrame(referanseverdier, columns=["område_id", "verdi"])
            sum_verdi = målinger_df.groupby(["område_id"])["verdi"].mean().reset_index()
            for _, sum_row in sum_verdi.iterrows():
                område_id = int(sum_row["område_id"])
                verdi = int(sum_row["verdi"])
                sjekk = db.execute(
                    "SELECT * FROM kvalitetsmåling WHERE kvalitetselement_id = ? AND område_id = ? AND vegobjekttype_id = ? AND egenskapstype_id = ?",
                    (kv_id, område_id, row['id'], None)
                ).fetchone()
                if not sjekk:
                    db.execute(
                        "INSERT INTO kvalitetsmåling (kvalitetselement_id, vegobjekttype_id, egenskapstype_id, verdi, område_id) VALUES (?, ?, ?, ?, ?)",
                        (kv_id, row['id'], None, verdi, område_id)
                    )

            """ sum_verdi = referanseverdier_df.groupby(["område_id"])["verdi"].sum().reset_index()
            for _, sum_row in sum_verdi.iterrows():
                område_id = int(sum_row["område_id"])
                verdi = int(sum_row["verdi"])
                sjekk = db.execute(
                    "SELECT * FROM referanseverdi WHERE kvalitetselement_id = ? AND område_id = ? AND vegobjekttype_id = ? AND egenskapstype_id = ?",
                    (kv_id, område_id, row['id'], None)
                ).fetchone()
                if not sjekk:
                    db.execute(
                        "INSERT INTO referanseverdi (kvalitetselement_id, vegobjekttype_id, egenskapstype_id, verdi, område_id) VALUES (?, ?, ?, ?, ?)",
                        (kv_id, row['id'], None, verdi, område_id)
                    ) """
    db.commit()

if __name__ == "__main__":
    aggreger_område()